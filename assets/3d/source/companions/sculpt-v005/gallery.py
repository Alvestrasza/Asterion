"""Read-only image composition of approved facial crops and actual GLB renders.

This only lays out existing images, never generates artwork, retouches them or
projects a portrait onto a model. Original reference and render bytes are fixed.
"""
import argparse
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
from PIL import Image, ImageDraw, ImageFont, ImageOps
import contract

REPO, ROOT, KINDS = contract.REPO, contract.ROOT, contract.KINDS
OUT = REPO/'assets/3d/reference/companions/sculpt-v005'
spec=importlib.util.spec_from_file_location('face_gallery_writer',ROOT.parent/'sculpt-v002/deliver.py')
staged=importlib.util.module_from_spec(spec);sys.modules[spec.name]=staged;spec.loader.exec_module(staged)
CROPS = {
    'asterion': (1280,235,1600,455), 'pony': (280,320,680,670),
    'rabbit': (265,455,735,785), 'cat': (185,390,725,755),
    'dog': (245,310,800,690), 'orc': (310,290,905,670),
    'fairy': (405,285,785,560), 'elf': (450,165,815,440),
}
RENDER_CROPS = {
    'asterion': (150,340,1060,970),
    'pony': (200,380,1010,1030), 'rabbit': (190,320,1140,1050),
    'cat': (170,390,1130,1090), 'dog': (190,320,1060,1060),
    'orc': (60,160,1140,1050), 'fairy': (100,190,1120,1050),
    'elf': (100,190,1120,1050),
}


def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def picture(path, size, crop):
    source=Image.open(path).convert('RGBA')
    if not (0<=crop[0]<crop[2]<=source.width and 0<=crop[1]<crop[3]<=source.height):
        raise ValueError('Facial review crop outside image: '+Path(path).name)
    source=source.crop(crop)
    base=Image.new('RGBA',source.size,'#eae7e0');base.alpha_composite(source)
    return ImageOps.contain(base.convert('RGB'),size)


def build_artifacts():
    artifacts=[];entries=[]
    def add_image(path, value):
        stream=io.BytesIO();value.save(stream,format='JPEG',quality=95)
        item=staged.Artifact(path.resolve(),stream.getvalue());artifacts.append(item)
        return item.checksum
    font=ImageFont.load_default(size=23)
    overview=Image.new('RGB',(1800,1610),'#eae7e0');od=ImageDraw.Draw(overview)
    for index,kind in enumerate(KINDS):
        mp=REPO/f'assets/3d/source/{kind}/{contract.revision(kind)}/manifest.json'
        m=json.loads(mp.read_text(encoding='utf-8'))
        ref=REPO/m['reference']
        old=m['baseline_renders']['face-hero'];new=m['import_renders']['face-hero']
        previous,current=REPO/old['file'],REPO/new['file']
        for path,sha in ((ref,m['reference_sha256']),(previous,old['sha256']),(current,new['sha256'])):
            if digest(path)!=sha: raise ValueError('Reference or actual GLB render changed')
        sheet=Image.new('RGB',(1800,680),'#eae7e0');draw=ImageDraw.Draw(sheet)
        for col,path,label,crop in ((0,ref,'Approved 2D face',CROPS[kind]),
                (1,previous,'Previous 3D face',RENDER_CROPS[kind]),
                (2,current,'New 3D face',RENDER_CROPS[kind])):
            draw.text((col*600+15,18),m['name']+' | '+label,font=font,fill='#203445')
            p=picture(path,(580,570),crop)
            sheet.paste(p,(col*600+(600-p.width)//2,64+(570-p.height)//2))
        draw.text((20,648),'Independent framing. Actual geometry; no projected artwork. Not 100% identity acceptance.',font=ImageFont.load_default(size=17),fill='#455664')
        target=OUT/(kind+'-face-comparison.jpg');comparison_sha=add_image(target,sheet)
        row,col=divmod(index,4);x,y=col*450,row*805
        od.text((x+15,y+14),m['name']+' | 2D / new 3D',font=font,fill='#203445')
        for slot,path,crop in ((0,ref,CROPS[kind]),(1,current,RENDER_CROPS[kind])):
            p=picture(path,(435,350),crop)
            overview.paste(p,(x+(450-p.width)//2,y+56+slot*370+(350-p.height)//2))
        entries.append(dict(kind=kind,manifest=mp.relative_to(REPO).as_posix(),manifest_sha256=digest(mp),
            reference=m['reference'],reference_sha256=digest(ref),reference_crop=CROPS[kind],
            previous=old['file'],previous_sha256=digest(previous),current=new['file'],current_sha256=digest(current),
            render_crop=RENDER_CROPS[kind],comparison=target.relative_to(REPO).as_posix(),comparison_sha256=comparison_sha))
    target=OUT/'face-comparison.jpg'
    value=dict(schema='asterion-face-comparison-v1',gallery=target.relative_to(REPO).as_posix(),
        sha256=add_image(target,overview),figures=entries,source_files_modified=False,independent_framing=True,
        likeness_accepted=False,assembly_script_sha256=digest(__file__))
    artifacts.append(staged.Artifact((OUT/'gallery-manifest.json').resolve(),staged.json_bytes(value)))
    return tuple(artifacts),value


def preflight(artifacts,value,replace_verified=False):
    prior={};receipt=OUT/'gallery-manifest.json'
    if replace_verified:
        old=json.loads(receipt.read_bytes())
        if old.get('schema')!='asterion-face-comparison-v1' or [e['kind'] for e in old['figures']]!=list(KINDS):
            raise ValueError('Invalid preceding face gallery receipt')
        for entry in old['figures']:
            path=OUT/(entry['kind']+'-face-comparison.jpg')
            if entry['comparison']!=path.relative_to(REPO).as_posix(): raise ValueError('Unexpected comparison target')
            prior[path.resolve()]=entry['comparison_sha256']
        path=OUT/'face-comparison.jpg'
        if old['gallery']!=path.relative_to(REPO).as_posix(): raise ValueError('Unexpected overview target')
        prior[path.resolve()]=old['sha256'];prior[receipt.resolve()]=digest(receipt)
        for path,sha in prior.items():
            if staged.existing_hash(path)!=sha: raise ValueError('Preceding gallery bytes changed')
    observed={}
    for item in artifacts:
        if item.target.parent!=OUT.resolve(): raise ValueError('Gallery destination outside fixed directory')
        actual=staged.existing_hash(item.target);observed[item.target]=actual
        if actual is not None and actual!=item.checksum and actual!=prior.get(item.target):
            raise FileExistsError('Different existing gallery content: '+item.target.name)
    return staged.DeliveryPlan(REPO,artifacts,value,observed)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--replace-verified',action='store_true')
    args=parser.parse_args();artifacts,value=build_artifacts()
    staged.execute_delivery(preflight(artifacts,value,args.replace_verified))
    print(OUT/'face-comparison.jpg')
