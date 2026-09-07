"""Hash-checked review layouts from actual renders and unchanged approved art.

Resizing/cropping is only for review layout, never a texture or model projection.
"""
import hashlib
import argparse
import importlib.util
import io
import json
from pathlib import Path
import sys
from PIL import Image,ImageDraw,ImageFont,ImageOps

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[4]
KINDS=('asterion','pony','rabbit','cat','dog','orc','fairy','elf')
OUT=REPO/'assets/3d/reference/companions/sculpt-v004'
spec=importlib.util.spec_from_file_location('gallery_staged_delivery',ROOT.parent/'sculpt-v002/deliver.py')
staged=importlib.util.module_from_spec(spec);sys.modules[spec.name]=staged;spec.loader.exec_module(staged)

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()

def picture(path,size,crop=None):
    source=Image.open(path).convert('RGBA')
    if crop:source=source.crop(crop)
    base=Image.new('RGBA',source.size,'#ebe8e1');base.alpha_composite(source)
    return ImageOps.contain(base.convert('RGB'),size)

def build_artifacts():
    artifacts=[]
    def add_image(path,value):
        buffer=io.BytesIO();value.save(buffer,format='JPEG',quality=95)
        item=staged.Artifact(path.resolve(),buffer.getvalue());artifacts.append(item)
        return item.checksum
    overview=Image.new('RGB',(1800,1960),'#ebe8e1')
    draw=ImageDraw.Draw(overview);font=ImageFont.load_default(size=23)
    entries=[]
    for index,kind in enumerate(KINDS):
        version='sculpt-v005' if kind=='asterion' else 'sculpt-v004'
        mp=REPO/'assets/3d/source'/kind/version/'manifest.json'
        m=json.loads(mp.read_text(encoding='utf-8'))
        reference=REPO/m['reference'];current=REPO/m['import_renders']['hero']['file']
        previous=(REPO/'assets/3d/reference/asterion/sculpt-v004/import-review/asterion-sculpt-hero.png' if kind=='asterion'
                  else REPO/'assets/3d/reference'/kind/'sculpt-v003/import'/(kind+'-hero.png'))
        if digest(reference)!=m['reference_sha256'] or digest(current)!=m['import_renders']['hero']['sha256']:
            raise ValueError('Render or reference changed')
        crop=(1260,110,1719,740) if kind=='asterion' else None
        sheet=Image.new('RGB',(1800,670),'#ebe8e1');labels=ImageDraw.Draw(sheet)
        for column,(path,label,region) in enumerate(((reference,'Approved 2D art',crop),(previous,'Previous 3D',None),(current,'New 3D | '+version,None))):
            labels.text((column*600+18,17),m['name']+' | '+label,font=font,fill='#243345')
            p=picture(path,(590,590),region)
            sheet.paste(p,(column*600+(600-p.width)//2,65+(590-p.height)//2))
        target=OUT/(kind+'-comparison.jpg')
        comparison_sha=add_image(target,sheet)
        row,col=divmod(index,4)
        # Each of two figure rows has approved art directly above the new GLB.
        x=col*450;y=row*980
        draw.text((x+15,y+13),m['name']+' | 2D / new 3D',font=font,fill='#243345')
        for slot,path,region in ((0,reference,crop),(1,current,None)):
            p=picture(path,(440,440),region)
            overview.paste(p,(x+(450-p.width)//2,y+52+slot*456+(440-p.height)//2))
        entries.append(dict(kind=kind,manifest=mp.relative_to(REPO).as_posix(),manifest_sha256=digest(mp),
            reference=m['reference'],reference_sha256=digest(reference),reference_review_crop=crop,
            previous=previous.relative_to(REPO).as_posix(),previous_sha256=digest(previous),
            current=current.relative_to(REPO).as_posix(),current_sha256=digest(current),
            comparison=target.relative_to(REPO).as_posix(),comparison_sha256=comparison_sha))
    target=OUT/'reference-comparison.jpg';receipt=OUT/'gallery-manifest.json'
    value=dict(schema='asterion-likeness-comparison-v1',gallery=target.relative_to(REPO).as_posix(),
        sha256=add_image(target,overview),figures=entries,source_files_modified=False,independent_framing=True,
        likeness_accepted=False,assembly_script_sha256=digest(__file__))
    artifacts.append(staged.Artifact(receipt.resolve(),staged.json_bytes(value)))
    return tuple(artifacts),value


def preflight(artifacts,value,replace_verified=False):
    prior={};receipt=OUT/'gallery-manifest.json'
    if replace_verified:
        # The preceding receipt authorizes only its exact layout bytes, never
        # arbitrary existing images. Models, portraits and older revisions are
        # not replacement targets. The shared writer also detects later races.
        old=json.loads(receipt.read_bytes())
        if old.get('schema')!='asterion-likeness-comparison-v1' or [e['kind'] for e in old['figures']]!=list(KINDS):
            raise ValueError('Invalid preceding gallery receipt')
        for entry in old['figures']:
            path=OUT/(entry['kind']+'-comparison.jpg')
            if entry['comparison']!=path.relative_to(REPO).as_posix():raise ValueError('Unexpected comparison target')
            prior[path.resolve()]=entry['comparison_sha256']
        path=OUT/'reference-comparison.jpg'
        if old['gallery']!=path.relative_to(REPO).as_posix():raise ValueError('Unexpected overview target')
        prior[path.resolve()]=old['sha256'];prior[receipt.resolve()]=digest(receipt)
        for path,expected in prior.items():
            if staged.existing_hash(path)!=expected:raise ValueError('Preceding gallery bytes changed: '+path.name)
    observed={}
    for item in artifacts:
        if item.target.parent!=OUT.resolve():raise ValueError('Gallery destination outside fixed directory')
        actual=staged.existing_hash(item.target);observed[item.target]=actual
        if actual is not None and actual!=item.checksum and actual!=prior.get(item.target):
            raise FileExistsError('Different existing gallery content: '+item.target.name)
    return staged.DeliveryPlan(REPO,artifacts,value,observed)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--replace-verified',action='store_true',help='Replace only exact layout bytes bound by the preceding gallery receipt')
    args=parser.parse_args()
    artifacts,value=build_artifacts()
    staged.execute_delivery(preflight(artifacts,value,args.replace_verified))
    print(OUT/'reference-comparison.jpg')

if __name__=='__main__':main()
