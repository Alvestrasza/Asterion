"""Independent Liora v002 GLB motion diagnostics and six-view contact sheet.

Run in Blender, for example:
  blender --background --factory-startup --python inspect_motion.py --
    --glb /absolute/rabbit-sculpt-v002.glb --output /absolute/new/private/review

This samples fully evaluated world-space mesh vertices, not just bone matrices.
Finite coordinates and loop equality do not establish collision-free motion,
anatomical gait, ground contact, or human acceptance of the likeness.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
import zlib

import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
COMMON_ROOT = ROOT.parents[1] / 'companions' / 'sculpt-v001'
sys.path.insert(0, str(COMMON_ROOT))
import common

SAMPLES = [('idle', 1), ('blink', 10), ('happy', 31),
           ('eat', 46), ('sleep', 61), ('walk', 13)]
LOOPS = ('idle', 'sleep', 'walk')
LOOP_TOLERANCE = 1e-4


def activate(rig, action, frame):
    rig.animation_data_create()
    rig.animation_data.action = action
    if getattr(action, 'slots', None):
        rig.animation_data.action_slot = action.slots[0]
    whole = math.floor(frame)
    bpy.context.scene.frame_set(whole, subframe=frame - whole)
    bpy.context.view_layer.update()


def evaluated_vertices(meshes):
    """Return every evaluated vertex in world space; release temporary meshes."""
    graph = bpy.context.evaluated_depsgraph_get()
    result = {}
    for obj in meshes:
        evaluated = obj.evaluated_get(graph)
        mesh = evaluated.to_mesh()
        try:
            flat = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
            mesh.vertices.foreach_get('co', flat)
            points = flat.reshape((-1, 3)).astype(np.float64)
            matrix = np.asarray(evaluated.matrix_world, dtype=np.float64)
            result[obj.name] = points @ matrix[:3, :3].T + matrix[:3, 3]
        finally:
            evaluated.to_mesh_clear()
    return result


def geometry_summary(points):
    count = sum(len(value) for value in points.values())
    nonfinite = sum(int(np.count_nonzero(~np.isfinite(value).all(axis=1))) for value in points.values())
    lows, highs = [], []
    for value in points.values():
        finite = value[np.isfinite(value).all(axis=1)]
        if len(finite):
            lows.append(finite.min(axis=0)); highs.append(finite.max(axis=0))
    return {
        'evaluated_meshes': len(points), 'evaluated_vertices': count,
        'nonfinite_vertices': nonfinite, 'finite': nonfinite == 0 and count > 0,
        'bounds_min': np.min(lows, axis=0).tolist() if lows else None,
        'bounds_max': np.max(highs, axis=0).tolist() if highs else None,
    }


def compare_loop(meshes, rig, action):
    start, end = map(float, action.frame_range)
    activate(rig, action, start)
    before = evaluated_vertices(meshes)
    activate(rig, action, end)
    after = evaluated_vertices(meshes)
    same_topology = set(before) == set(after) and all(before[k].shape == after[k].shape for k in before)
    first, last = geometry_summary(before), geometry_summary(after)
    finite = first['finite'] and last['finite']
    maximum = None
    per_mesh = {}
    if same_topology and finite:
        for key, value in before.items():
            distance = np.linalg.norm(value - after[key], axis=1)
            per_mesh[key] = float(distance.max()) if len(distance) else 0.0
        maximum = max(per_mesh.values(), default=0.0)
    return {
        'start_frame': start, 'end_frame': end,
        'same_evaluated_vertex_layout': same_topology,
        'finite_start_and_end': finite,
        'compared_vertices': first['evaluated_vertices'],
        'max_vertex_distance': maximum,
        'per_mesh_max_vertex_distance': per_mesh,
        'tolerance_world_units': LOOP_TOLERANCE,
        'within_tolerance': same_topology and finite and maximum is not None and maximum <= LOOP_TOLERANCE,
    }


def read_png_rgb(path):
    """Decode the 8-bit RGB/RGBA PNGs rendered here without external libraries."""
    data = path.read_bytes()
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('Not PNG: ' + str(path))
    pos, chunks = 8, []
    width = height = channels = None
    while pos < len(data):
        length = struct.unpack_from('>I', data, pos)[0]
        kind = data[pos + 4:pos + 8]; payload = data[pos + 8:pos + 8 + length]
        if kind == b'IHDR':
            width, height, depth, color, compression, filtering, interlace = struct.unpack('>IIBBBBB', payload)
            if depth != 8 or color not in (2, 6) or interlace:
                raise ValueError('Contact sheet expects noninterlaced 8-bit RGB/RGBA PNGs')
            channels = 3 if color == 2 else 4
        elif kind == b'IDAT': chunks.append(payload)
        elif kind == b'IEND': break
        pos += length + 12
    if not width or not height or channels is None:
        raise ValueError('Missing PNG header')
    stride = width * channels
    packed = zlib.decompress(b''.join(chunks))
    if len(packed) != height * (stride + 1):
        raise ValueError('Unexpected PNG scanline length')
    rows = np.empty((height, stride), dtype=np.uint8)
    previous = np.zeros(stride, dtype=np.uint8)
    offset = 0
    for y in range(height):
        mode = packed[offset]; offset += 1
        raw = np.frombuffer(packed, np.uint8, stride, offset).astype(np.int32); offset += stride
        if mode == 0:
            current = raw.astype(np.uint8)
        elif mode == 1:
            current = np.cumsum(raw.reshape((-1, channels)), axis=0).astype(np.uint8).reshape(-1)
        elif mode == 2:
            current = (raw + previous.astype(np.int32)).astype(np.uint8)
        elif mode in (3, 4):
            current = np.empty(stride, dtype=np.uint8)
            for x in range(stride):
                a = int(current[x - channels]) if x >= channels else 0
                b = int(previous[x]); c = int(previous[x - channels]) if x >= channels else 0
                if mode == 3:
                    prediction = (a + b) // 2
                else:
                    q = a + b - c
                    da, db, dc = abs(q - a), abs(q - b), abs(q - c)
                    prediction = a if da <= db and da <= dc else b if db <= dc else c
                current[x] = (int(raw[x]) + prediction) & 255
        else:
            raise ValueError('Unsupported PNG filter')
        rows[y] = current; previous = current
    image = rows.reshape((height, width, channels))
    if channels == 4:
        alpha = image[:, :, 3:4].astype(np.float32) / 255
        return np.rint(image[:, :, :3] * alpha + 238 * (1 - alpha)).astype(np.uint8)
    return image


def write_png(path, pixels):
    height, width, channels = pixels.shape
    if channels != 3: raise ValueError('Expected RGB')
    def chunk(kind, payload):
        return struct.pack('>I', len(payload)) + kind + payload + struct.pack('>I', zlib.crc32(kind + payload) & 0xffffffff)
    raw = b''.join(b'\x00' + pixels[y].tobytes() for y in range(height))
    data = b'\x89PNG\r\n\x1a\n'
    data += chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
    data += chunk(b'sRGB', b'\x00')
    data += chunk(b'IDAT', zlib.compress(raw, 7)) + chunk(b'IEND', b'')
    path.write_bytes(data)


FONT = {
    'A': ('01110','10001','10001','11111','10001','10001','10001'),
    'B': ('11110','10001','10001','11110','10001','10001','11110'),
    'D': ('11110','10001','10001','10001','10001','10001','11110'),
    'E': ('11111','10000','10000','11110','10000','10000','11111'),
    'F': ('11111','10000','10000','11110','10000','10000','10000'),
    'H': ('10001','10001','10001','11111','10001','10001','10001'),
    'I': ('11111','00100','00100','00100','00100','00100','11111'),
    'K': ('10001','10010','10100','11000','10100','10010','10001'),
    'L': ('10000','10000','10000','10000','10000','10000','11111'),
    'N': ('10001','11001','11001','10101','10011','10011','10001'),
    'P': ('11110','10001','10001','11110','10000','10000','10000'),
    'S': ('01111','10000','10000','01110','00001','00001','11110'),
    'T': ('11111','00100','00100','00100','00100','00100','00100'),
    'W': ('10001','10001','10001','10101','10101','11011','10001'),
    'Y': ('10001','10001','01010','00100','00100','00100','00100'),
    '0': ('01110','10001','10011','10101','11001','10001','01110'),
    '1': ('00100','01100','00100','00100','00100','00100','01110'),
    '2': ('01110','10001','00001','00010','00100','01000','11111'),
    '3': ('11110','00001','00001','01110','00001','00001','11110'),
    '4': ('00010','00110','01010','10010','11111','00010','00010'),
    '5': ('11111','10000','10000','11110','00001','00001','11110'),
    '6': ('01110','10000','10000','11110','10001','10001','01110'),
    '7': ('11111','00001','00010','00100','01000','01000','01000'),
    '8': ('01110','10001','10001','01110','10001','10001','01110'),
    '9': ('01110','10001','10001','01111','00001','00001','01110'),
}


def contact_sheet(output, renders):
    images = [read_png_rgb(Path(item['image'])) for item in renders]
    h, w = images[0].shape[:2]
    if any(image.shape[:2] != (h, w) for image in images):
        raise ValueError('Inconsistent contact-sheet image sizes')
    margin, header, scale = 14, 38, 3
    canvas = np.full((2 * (h + header) + 3 * margin, 3 * w + 4 * margin, 3), 238, np.uint8)
    for i, (item, image) in enumerate(zip(renders, images)):
        row, col = divmod(i, 3)
        x, y = margin + col * (w + margin), margin + row * (h + header + margin)
        canvas[y + header:y + header + h, x:x + w] = image
        label = item['clip'].upper() + ' F' + str(item['frame'])
        for j, char in enumerate(label):
            glyph = FONT.get(char)
            if glyph is None: continue
            for gy, bits in enumerate(glyph):
                for gx, bit in enumerate(bits):
                    if bit == '1':
                        yy, xx = y + 8 + gy * scale, x + 12 + (j * 6 + gx) * scale
                        canvas[yy:yy + scale, xx:xx + scale] = (47, 48, 52)
    path = output / 'rabbit-v002-motion-contact-sheet.png'
    write_png(path, canvas)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--glb', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--resolution', type=int, default=600)
    parser.add_argument('--samples', type=int, default=32)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    source, output = Path(args.glb), Path(args.output)
    if not source.is_absolute() or not output.is_absolute():
        raise ValueError('Both source and output must be absolute paths')
    source, output = source.resolve(), output.resolve()
    if not source.is_file(): raise FileNotFoundError(source)
    if output.exists() and any(output.iterdir()):
        raise FileExistsError('Choose a new or empty diagnostic output directory')
    if args.resolution < 128 or args.samples < 1:
        raise ValueError('Resolution must be >=128; samples must be positive')
    output.mkdir(parents=True, exist_ok=True)
    document = common.glb_json(source)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    # Import maps animation seconds to frames using the PRE-IMPORT frame rate.
    scene.render.fps = 30; scene.render.fps_base = 1.0
    bpy.ops.import_scene.gltf(filepath=str(source))
    rigs = [obj for obj in scene.objects if obj.type == 'ARMATURE']
    if len(rigs) != 1: raise ValueError('Expected exactly one imported armature')
    rig = rigs[0]
    helper_shapes = {bone.custom_shape for bone in rig.pose.bones if bone.custom_shape is not None}
    meshes = sorted([obj for obj in scene.objects if obj.type == 'MESH' and obj not in helper_shapes], key=lambda obj: obj.name)
    for obj in helper_shapes: obj.hide_render = True
    if not meshes: raise ValueError('No imported character mesh')
    actions = {action.name: action for action in bpy.data.actions}
    required = {name for name, _ in SAMPLES} | set(LOOPS)
    missing = required - set(actions)
    if missing: raise ValueError('Missing imported actions: ' + ', '.join(sorted(missing)))
    sample_reports, lows, highs = [], [], []
    for name, frame in SAMPLES:
        start, end = actions[name].frame_range
        if not start <= frame <= end:
            raise ValueError(f'Requested {name} frame {frame} outside imported range {(start, end)}')
        activate(rig, actions[name], frame)
        report = geometry_summary(evaluated_vertices(meshes))
        report.update({'clip': name, 'frame': frame})
        sample_reports.append(report)
        if report['bounds_min'] is not None:
            lows.append(report['bounds_min']); highs.append(report['bounds_max'])
    loops = {name: compare_loop(meshes, rig, actions[name]) for name in LOOPS}
    checks = {
        'nonempty_evaluated_meshes': all(item['evaluated_vertices'] > 0 for item in sample_reports),
        'all_six_full_mesh_samples_finite': all(item['finite'] for item in sample_reports),
        'idle_sleep_walk_vertex_loops': all(item['within_tolerance'] for item in loops.values()),
    }
    report = {
        'source_glb': str(source), 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest().upper(),
        'blender': bpy.app.version_string, 'fps_at_import': 30,
        'authored_clips': [a.get('name') for a in document.get('animations', [])],
        'imported_frame_ranges': {name: list(map(float, action.frame_range)) for name, action in actions.items()},
        'included_meshes': [obj.name for obj in meshes],
        'excluded_armature_visualization_helpers': [obj.name for obj in helper_shapes],
        'samples': sample_reports, 'loop_comparisons': loops, 'checks': checks,
        'passed': all(checks.values()), 'renders': [],
        'diagnostic_scope': 'Full evaluated mesh finiteness at six frames and loop endpoint vertex equality only.',
        'collision_free_verified': False, 'ground_contact_verified': False,
        'human_visual_review_required': True,
    }
    report_path = output / 'motion-inspection.json'
    # Preserve actual numerical failures even if rendering must be skipped.
    if not lows or not all(item['finite'] for item in sample_reports):
        report_path.write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')
        raise RuntimeError('Nonfinite/empty evaluated geometry; see motion-inspection.json')
    lo, hi = Vector(np.min(lows, axis=0)), Vector(np.max(highs, axis=0))
    center, span = (lo + hi) * .5, hi - lo
    g = common.toolkit()
    if scene.world is None: scene.world = bpy.data.worlds.new('Independent motion review')
    cam, _, _ = common.configure_stage(g, meshes, args.resolution, args.samples)
    ground = bpy.data.objects.get('STUDIO_ground')
    ground.location.z = lo.z - .008
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.image_settings.color_depth = '8'
    for item in sample_reports:
        activate(rig, actions[item['clip']], item['frame'])
        name = f"rabbit-{item['clip']}-f{item['frame']:03d}"
        path = common.render_views(g, cam, center, span, output, name, ['hero'])['hero']
        report['renders'].append({'clip': item['clip'], 'frame': item['frame'], 'image': path})
    report['contact_sheet'] = str(contact_sheet(output, report['renders']))
    report_path.write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')
    print(json.dumps({'motion_diagnostic_complete': True, 'passed': report['passed'],
                      'report': str(report_path), 'contact_sheet': report['contact_sheet'],
                      'loop_max_distances': {name: item['max_vertex_distance'] for name, item in loops.items()}}, indent=2), flush=True)
    if not report['passed']:
        raise RuntimeError('Motion numerical diagnostic failed; inspect report and renders')


if __name__ == '__main__':
    main()
