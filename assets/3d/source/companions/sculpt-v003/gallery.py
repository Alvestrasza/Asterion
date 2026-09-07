"""Assemble unchanged, hash-verified imported renders into a local review sheet."""
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[4]
KINDS = ('pony', 'rabbit', 'cat', 'dog', 'orc', 'fairy', 'elf')
OUT = REPO / 'assets/3d/reference/companions/sculpt-v003'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / 'companions-gallery.jpg'
    receipt = OUT / 'gallery-manifest.json'
    if target.exists() or receipt.exists():
        raise FileExistsError('Gallery already exists')
    cell, header = 440, 54
    canvas = Image.new('RGB', (cell * 4, (cell + header) * 4), '#ebe8e1')
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default(size=19)
    entries = []
    for index, kind in enumerate(KINDS):
        manifest_path = REPO / 'assets/3d/source' / kind / 'sculpt-v003/manifest.json'
        m = json.loads(manifest_path.read_text(encoding='utf-8'))
        row, column = divmod(index, 2)
        for offset, (view, label) in enumerate((('hero', 'Outer outfit'), ('body-hero', 'Base body'))):
            record = m['import_renders'][view]; path = REPO / record['file']
            if sha(path) != record['sha256']:
                raise ValueError('Imported render changed')
            picture = ImageOps.contain(Image.open(path).convert('RGB'), (cell, cell))
            x, y = (column * 2 + offset) * cell, row * (cell + header)
            draw.text((x + 16, y + 16), m['name'] + ' | ' + label, font=font, fill='#26313c')
            canvas.paste(picture, (x, y + header))
        entries.append({'kind': kind, 'manifest': manifest_path.relative_to(REPO).as_posix(),
            'manifest_sha256': sha(manifest_path), 'source_images': m['import_renders'],
            'triangles': m['triangles'], 'bytes': m['bytes']})
    draw.multiline_text((cell * 2 + 28, 3 * (cell + header) + 95),
        'Modular companions | sculpt-v003\n\nActual Blender GLB-import renders.\nSeparate outer outfits; original nine clips.\n\nDisplay heights normalized independently.\nNot a shared body-scale chart.\n\nOriginal portraits and earlier files retained.\nLikeness and mobile acceptance pending.',
        font=font, fill='#26313c', spacing=12)
    canvas.save(target, quality=94)
    receipt.write_text(json.dumps({'schema': 'asterion-companion-review-gallery-v1',
        'gallery': target.relative_to(REPO).as_posix(), 'sha256': sha(target), 'figures': entries,
        'source_images_modified': False, 'shared_physical_scale': False,
        'assembly_script_sha256': sha(Path(__file__))}, indent=2) + '\n', encoding='utf-8')
    print(target)


if __name__ == '__main__':
    main()
