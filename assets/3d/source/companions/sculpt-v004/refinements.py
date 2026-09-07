"""Route species-owned likeness edits without touching historical authored files."""
from pathlib import Path
import importlib
import common

ROOT = Path(__file__).resolve().parent
NAMES = dict(asterion='Asterion', pony='Caelo', rabbit='Liora', cat='Nyra', dog='Fenn', orc='Brumo', fairy='Selya', elf='Aelira')
MODULES = dict(pony='equine_lapine', rabbit='equine_lapine', cat='feline_canine', dog='feline_canine', orc='folk', fairy='folk', elf='folk')

def dependencies(kind):
    if kind == 'asterion':
        return [ROOT.parent.parent / 'asterion/sculpt-v005/likeness.py']
    module = importlib.import_module(MODULES[kind])
    return [ROOT / (MODULES[kind] + '.py')] + list(getattr(module, 'DEPENDENCIES', []))

def apply(g, rig, kind):
    if kind == 'asterion':
        module = common.load_file('asterion_v5_likeness', dependencies(kind)[0])
    else:
        module = importlib.import_module(MODULES[kind])
    changes = module.apply(g, rig, kind)
    groups = {'body': [], 'armor': []}
    for obj in g.ASSET:
        component = obj.get('asterion_component')
        if component not in groups:
            raise ValueError('Unclassified authored object: ' + obj.name)
        groups[component].append(obj)
    changes.setdefault('added_base_clothing', [])
    changes['equipment_source_objects'] = [o.name for o in groups['armor']]
    changes['body_source_objects'] = [o.name for o in groups['body']]
    return groups, changes

