"""Render the five remaining v002 GLB figures together; no image planes or compositing."""
import argparse
import math
from pathlib import Path
import sys
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'sculpt-v001'))
import common


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    source=Path(args.input).resolve();output=Path(args.output).resolve();output.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if (output/'companions-gallery.png').exists():raise FileExistsError('Fresh gallery output required')
    scene=bpy.context.scene;scene.world=bpy.data.worlds.new('Collection gallery')
    g=common.toolkit();cam=g.stage(3200,64)
    scene.render.resolution_y=1000
    scene.render.fps=30
    # The larger studio covers the complete row with identical neutral lighting.
    for obj in scene.objects:
        if obj.type=='LIGHT':
            obj.location.x*=3;obj.location.y*=2;obj.location.z*=1.7
            obj.data.energy*=5;obj.data.size*=2.5;g.point_at(obj,(0,0,2.3))
    bpy.data.objects['STUDIO_ground'].location.z=-.025
    bpy.data.objects['STUDIO_ground'].scale=(10,10,10)
    names=[('cat','Nyra'),('orc','Brumo'),('fairy','Selya'),('dog','Fenn'),('elf','Aelira')]
    for index,(kind,name) in enumerate(names):
        previous=set(scene.objects);previous_actions=set(bpy.data.actions)
        bpy.ops.import_scene.gltf(filepath=str(source/kind/(kind+'-sculpt-v002.glb')))
        objects=set(scene.objects)-previous;rig=next(o for o in objects if o.type=='ARMATURE')
        helpers={b.custom_shape for b in rig.pose.bones if b.custom_shape is not None}
        meshes=[o for o in objects if o.type=='MESH' and o not in helpers]
        for obj in objects:
            if obj.type=='MESH' and obj not in meshes:obj.hide_render=True
        action=next(a for a in set(bpy.data.actions)-previous_actions if a.name.split('.')[0]=='idle')
        common.activate(rig,action)
        lo,hi=common.bounds(meshes);center=(lo+hi)*.5;scale=4.45/(hi.z-lo.z)
        carrier=bpy.data.objects.new(name+'_display',None);scene.collection.objects.link(carrier)
        for obj in objects:
            if obj.parent is None:obj.parent=carrier
        # Center before rotating, without touching source vertices or rig transforms.
        rig.location-=Vector((center.x,center.y,lo.z))
        carrier.scale=(scale,)*3;carrier.rotation_euler.z=math.radians(-18)
        carrier.location.x=(index-2)*4.6
        label_curve=bpy.data.curves.new(name+'_label','FONT');label_curve.body=name
        label_curve.align_x='CENTER';label_curve.size=.29
        label=bpy.data.objects.new(name+'_label',label_curve);scene.collection.objects.link(label)
        label.location=((index-2)*4.6,-2.7,.01)
        label.rotation_euler=(math.radians(78),0,0)
        label.data.materials.append(g.material(name+'_label_ink','42495A',0,.65))
    cam.location=(0,-35,10);g.point_at(cam,(0,0,2.05));cam.data.ortho_scale=24.0
    scene.render.filepath=str(output/'companions-gallery.png')
    bpy.ops.render.render(write_still=True)


if __name__=='__main__':main()
