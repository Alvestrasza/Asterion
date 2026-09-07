# Companion sculpture production contract

The seven existing companion PNGs in `public/assets/companions/` are the design
authority for this collection. They are single views; hidden surfaces must be
anatomically coherent interpretations, not claimed exact reconstructions.
Asterion's accepted sculpt and all existing 2D artwork remain unchanged.

Each builder provides `build(g, kind)` and returns a specification dictionary.
The coordinator calls it inside a fresh Blender scene. `g` exposes the existing
Asterion geometric toolkit: `M`, `ASSET`, `material`, `color`, `uv`, `mesh`,
`sweep`, `loft`, `line`, `fuse`, `active`, `apply`, `disk`. Materials must be
added to `g.M`; every mesh must be registered through these functions or
`g.register(obj,name,material,part)`. No studio objects belong in `g.ASSET`.

Coordinates: X lateral, front negative Y, Z up. Ground is Z=0. Give each pet a
natural neutral pose, visible real volume and recognizable species anatomy.
Use physical, curved anatomy and sculpted hair/fur, not piles of disconnected
balls. Target 100k–600k useful triangles; a denser model is allowed when its
detail is visible. Four views must work. No input-image billboards or reliefs.

`common.eye(g,name,center,normal,width,height,iris,skin,side,head=None)` supplies
one curved almond eye, recessed by a Boolean when `head` is supplied, plus its
closed-lid mesh. `side` is L or R. `skin` is a key in g.M. The eye uses the head
bone. Eyelids use `lid.L` and `lid.R`, automatically added by the common rig.

The returned spec must contain:

```python
{
    'name': 'Liora', 'kind': 'rabbit', 'family': 'quadruped',
    'bones': [
        ('body', (0,0,1.3), (0,0,2), None),
        ('neck', (0,-.5,2), (0,-.6,2.5), 'body'),
        ('head', (0,-.6,2.5), (0,-.6,3.5), 'neck'),
        ('leg.FL', (.4,-.6,1.4), (.4,-.6,.2), 'body'),
        ('leg.FR', (-.4,-.6,1.4), (-.4,-.6,.2), 'body'),
        ('leg.HL', (.4,.6,1.4), (.4,.6,.2), 'body'),
        ('leg.HR', (-.4,.6,1.4), (-.4,.6,.2), 'body'),
        ('tail', (0,.7,1.5), (0,1.4,1.7), 'body'),
    ],
    'notes': ['Distinct identity features and inferred unseen anatomy.'],
}
```

Every object's `ast_part` must match a declared bone name; body/head are common.
Use `arm.L`, `arm.R`, `leg.L`, `leg.R` for bipeds; `wing.L/R`, `ear.L/R` and
`tail` are optional. Give long curved parts multiple bones if needed and assign
each mesh to its closest relevant segment. Joined anatomical meshes may supply
their own vertex-group weights. The common rig preserves existing normalized
groups. The shared rig creates gentle nine-clip motions, but these are stylized
presentation gestures, not a physically simulated gait or facial performance.

Builders own separate source files. Coordinator owns common.py, build_collection.py,
validation, app integration, reports and final packaging. Do not edit Asterion's
existing files or another builder. Use Blender privately for drafts; all final
artifacts are copied only after visual and fresh-import checks.
