"""Caelo's sculpt-v002 mane and tail, built from closed curling hair volumes.

The approved pony portrait governs the sky-blue/lavender palette, asymmetrical
forelock and plush, hooked wave silhouette. Hidden surfaces are inferred.
No projected artwork, texture files, hair cards, or loose curve strands are used.

API: ``build(g) -> list[Object]``. The existing Asterion geometry toolkit supplies
``mesh``, ``material``, ``color``, ``M`` and ``ASSET``. Every returned object is
already registered and has one of the stable parts ``head``, ``neck``, ``tail``.
Continuous painted colors use the export-supported AST_eye_color attribute.
"""
from __future__ import annotations

import math

from mathutils import Vector


TAU = math.tau


def _palette(g):
    key = 'ch_painted_wave'
    if key not in g.M:
        mat = g.material('Caelo_painted_sky_hair', '7096D1', 0, .54)
        bsdf = mat.node_tree.nodes.get('Principled BSDF')
        bsdf.inputs['Specular IOR Level'].default_value = .23
        bsdf.inputs['Coat Weight'].default_value = .012
        bsdf.inputs['Coat Roughness'].default_value = .42
        vertex = mat.node_tree.nodes.new('ShaderNodeVertexColor')
        vertex.layer_name = 'AST_eye_color'
        mat.node_tree.links.new(vertex.outputs['Color'], bsdf.inputs['Base Color'])
        g.M[key] = mat
    return tuple(g.color(h) for h in ('25386C', '4F6EAA', '7BA6DC', 'BBDDF2'))


def _mix(a, b, t):
    t = max(0., min(1., t))
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def _profile(knots, t):
    """One analytic rounded-root / full-body / pointed-tip envelope."""
    rise, shoulder, fall = knots
    return .0018 + math.sqrt(1.-math.exp(-rise*t))*max(0., 1.-t**shoulder)**fall


def _path(points, count):
    """Clamped cubic B-spline: C2 continuity, no interpolating-knot elbows."""
    points = [Vector(p) for p in points]
    n = len(points)-1
    degree = min(3,n)
    knots = ([0.]*(degree+1)+[i/(n-degree+1) for i in range(1,n-degree+1)]
             +[1.]*(degree+1))
    result = []
    for sample in range(count+1):
        t = sample/count
        span = n if sample==count else next(
            i for i in range(degree,n+1) if knots[i]<=t<knots[i+1])
        d = [points[span-degree+j].copy() for j in range(degree+1)]
        for r in range(1,degree+1):
            for j in range(degree,r-1,-1):
                a = knots[j+span-degree]
                b = knots[j+1+span-r]
                f = (t-a)/(b-a) if b>a else 0.
                d[j] = d[j-1]*(1.-f)+d[j]*f
        result.append(d[degree])
    return result


_TAPER = (26., 2.8, 1.35)


def _frames(centers, normal):
    previous = Vector(normal).normalized()
    frames = []
    for i in range(len(centers)):
        tangent = (centers[min(len(centers)-1,i+1)]-centers[max(0,i-1)]).normalized()
        n = previous-tangent*previous.dot(tangent)
        if n.length<1.e-6:
            fallback = Vector((0,0,1)) if abs(tangent.z)<.9 else Vector((0,1,0))
            n = fallback-tangent*fallback.dot(tangent)
        n.normalize(); previous=n
        frames.append((tangent,tangent.cross(n).normalized(),n))
    return frames


def _safe_radii(centers, width, depth, profile, frames):
    """Uniformly scale the analytic envelope, never clamp individual samples.

    Local curvature determines one global conservative gain for the entire
    lock. Consequently a control point cannot create a bead or waist. Ellipse
    support is measured only in the actual bend direction, not the unrelated
    transverse thickness of a broad plume.
    """
    radii = [_profile(profile,i/(len(centers)-1)) for i in range(len(centers))]
    maximum = 0.
    for i in range(1,len(centers)-1):
        a = centers[i]-centers[i-1]; b = centers[i+1]-centers[i]
        denominator = a.length*b.length*(a+b).length
        if denominator>1.e-12:
            curvature = 2*a.cross(b).length/denominator
            bend = b.normalized()-a.normalized()
            if bend.length>1.e-7:
                bend.normalize()
                _,u,n = frames[i]
                support = math.sqrt((width*u.dot(bend))**2+(depth*n.dot(bend))**2)
                maximum = max(maximum,curvature*support*radii[i])
    gain = min(1.,.67/maximum) if maximum else 1.
    return [r*gain for r in radii],gain


def _lock(g, palette, name, points, width, depth, part, normal,
          seed=0., steps=76, sides=56, profile=_TAPER, tone=0.):
    """One manifold, fully rounded waved lock with carved, flowing channels.

    Broad shoulders form the plush silhouette. Shallow negative channels are
    integrated into the same surface and taper out before the pointed tip.
    A transported frame prevents flips when a curling tip turns toward its root.
    """
    centers = _path(points, steps)
    frames = _frames(centers,normal)
    radii,gain = _safe_radii(centers, width, depth, profile, frames)
    verts, faces, colors = [], [], []
    shadow, blue, sky, ice = palette
    for i, c in enumerate(centers):
        t = i/steps
        tangent,u,n = frames[i]
        radius = radii[i]
        w, d = width*radius, depth*radius
        fade = math.sin(math.pi*t)**.6
        twist = .19*math.sin(math.pi*t)+seed*.11
        for j in range(sides):
            angle = TAU*j/sides
            a = angle+twist
            # Three quiet broad lobes, plus narrow cut-in strand troughs. These
            # remain geometry under any lighting; no detached decorative ribs.
            broad = .062*math.cos(3*a+.4*math.sin(t*math.pi))
            channel = ((.5+.5*math.cos(9*a+.65*math.sin(t*2.4)+seed))**12)
            micro = .006*math.cos(19*a+1.6*t+seed)
            sculpt = 1.+fade*(broad-.054*channel+micro)
            side = math.cos(angle)
            outward = math.sin(angle)
            # Elliptic but plump: even the underside is a curved solid surface.
            p = c+u*(w*side*sculpt)+n*(d*outward*sculpt)
            verts.append(tuple(p))

            light = max(0., outward)
            base = _mix(shadow, blue, .39+.25*light+.12*math.sin(t*math.pi))
            base = _mix(base, sky, .11+.54*light**1.30+tone)
            # Wide, smoothly painted ribbon following the curl, not pinstripes.
            stripe_center = .27+.075*math.sin(t*4.2+seed)
            ribbon = math.exp(-((side-stripe_center)/.32)**2)
            ribbon *= light**1.5*(.27+.55*math.sin(math.pi*t)**2)
            base = _mix(base, ice, .44*ribbon)
            base = _mix(base, shadow, .20*channel*fade)
            colors.append(base[:3]+(1.,))
    for i in range(steps):
        for j in range(sides):
            a = i*sides+j
            b = i*sides+(j+1)%sides
            faces.append((a, a+sides, b+sides, b))
    # Explicit cap fans give a closed manifold without degenerate pole rings.
    root = len(verts)
    verts.append(tuple(centers[0])); colors.append(colors[0])
    tip = len(verts)
    verts.append(tuple(centers[-1])); colors.append(colors[-2])
    for j in range(sides):
        k = (j+1)%sides
        faces.append((root, j, k))
        faces.append((tip, steps*sides+k, steps*sides+j))
    obj = g.mesh('Caelo_hair_'+name, verts, faces, 'ch_painted_wave', part)
    attribute = obj.data.color_attributes.new(name='AST_eye_color',
                                               type='FLOAT_COLOR', domain='POINT')
    attribute.data.foreach_set('color', [c for rgba in colors for c in rgba])
    obj['hair_construction'] = 'Closed curl; sculpted troughs; painted vertex ribbons'
    obj['hair_reference'] = 'public/assets/companions/pony.png'
    obj['hair_uniform_curvature_gain'] = gain
    return obj


def _foundation(g,palette,name,sections,part,steps=100,sides=72):
    """A closed fitted hair mass under the locks, not a detached cap or card."""
    section_path = _path(sections,steps)
    verts,faces,colors = [],[],[]
    for i,(z,y,rx,ry) in enumerate(section_path):
        for j in range(sides):
            a = TAU*j/sides
            ripple = 1.+.015*math.cos(7*a+z*1.7)
            verts.append((rx*math.cos(a)*ripple,y+ry*math.sin(a)*ripple,z))
            rear = .5+.5*math.sin(a)
            col = _mix(palette[0],palette[1],.46+.34*rear)
            col = _mix(col,palette[2],.12+.18*rear)
            colors.append(col[:3]+(1.,))
    for i in range(steps):
        for j in range(sides):
            a = i*sides+j; b = i*sides+(j+1)%sides
            faces.append((a,b,b+sides,a+sides))
    faces.append(tuple(reversed(range(sides))))
    faces.append(tuple(steps*sides+j for j in range(sides)))
    obj = g.mesh('Caelo_hair_'+name,verts,faces,'ch_painted_wave',part)
    attr = obj.data.color_attributes.new(name='AST_eye_color',type='FLOAT_COLOR',domain='POINT')
    attr.data.foreach_set('color',[c for rgba in colors for c in rgba])
    obj['hair_construction']='Closed fitted hair foundation under continuous locks'
    return obj


def build(g):
    """Build Caelo's new mane/tail and return the registered editable meshes."""
    palette = _palette(g)
    made = []

    # The bases penetrate the skull/neck gently and overlap each other. They
    # provide a coherent blue underlayer from every angle, including the rear.
    made.append(_foundation(g,palette,'fitted_rear_scalp',[
        (3.10,-.54,.23,.13),(3.29,-.55,.50,.29),
        (3.59,-.66,.61,.38),(3.83,-.84,.54,.38),
        (4.00,-1.01,.34,.30),(4.06,-1.04,.04,.04)],'head'))
    made.append(_foundation(g,palette,'fitted_neck_underwave',[
        (2.05,-.23,.035,.035),(2.20,-.24,.30,.21),
        (2.57,-.25,.43,.25),(2.96,-.34,.50,.30),
        (3.31,-.47,.52,.30),(3.50,-.55,.25,.13)],'neck'))

    def lock(name, points, width, depth, part='head', normal=(0, -1, 0), **kw):
        if name.startswith(('forelock_', 'crown_')):
            # Lower only the high crest, retaining brow/eye/star clearance.
            points = [(x,y,3.86+(z-3.86)*.61 if z>3.86 else z)
                      for x,y,z in points]
        obj = _lock(g, palette, name, points, width, depth, part, normal,
                    seed=len(made)*.73, **kw)
        made.append(obj)

    # Forelock: a diagonal broad wave, with independent crescent tips turning
    # upward outside the left temple. The star/central brow remains uncovered.
    lock('forelock_main', [(.34,-1.12,3.92),(.02,-1.34,4.10),
         (-.38,-1.51,4.00),(-.72,-1.57,3.81),(-.95,-1.56,3.90)], .245,.183)
    lock('forelock_upper', [(.32,-.85,3.99),(-.04,-1.05,4.23),
         (-.43,-1.24,4.22),(-.77,-1.40,4.08),(-1.01,-1.43,4.15)], .232,.181)
    lock('forelock_lower_hook', [(.19,-1.38,3.91),(-.13,-1.54,4.00),
         (-.46,-1.65,3.85),(-.68,-1.66,3.64),(-.88,-1.66,3.74)], .185,.153,
         tone=.025)
    lock('crown_rising_wave', [(.36,-.57,3.81),(.20,-.63,4.06),
         (-.05,-.82,4.25),(-.37,-1.02,4.29),(-.61,-1.12,4.34)], .225,.192)
    lock('crown_rear_curl', [(.30,-.40,3.70),(.24,-.36,3.95),
         (.03,-.45,4.15),(-.22,-.55,4.24),(-.35,-.67,4.30)], .202,.182,
         normal=(0,1,0), tone=-.035)
    lock('crown_left_flick', [(-.20,-.82,3.93),(-.46,-1.00,4.05),
         (-.70,-1.19,4.00),(-.93,-1.33,3.96),(-1.05,-1.35,4.07)], .154,.135)
    lock('right_parting_curl', [(.17,-1.14,3.92),(.38,-1.31,3.90),
         (.57,-1.41,3.76),(.68,-1.39,3.68),(.72,-1.38,3.79)], .146,.123)

    # Soft temple flicks sit laterally, never in front of the eyes. Their roots
    # overlap the main forelock/ear bases; tips have different curl lengths.
    for s, side in ((-1, 'R'), (1, 'L')):
        lock('temple_'+side+'_upper', [(s*.43,-.90,3.76),
             (s*.66,-1.00,3.65),(s*.77,-1.00,3.46),
             (s*.79,-.92,3.34),(s*.81,-.79,3.31)], .169,.131,
             normal=(s,0,0), steps=64, sides=48)
        lock('temple_'+side+'_lower', [(s*.52,-.67,3.59),
             (s*.72,-.78,3.43),(s*.80,-.80,3.23),
             (s*.80,-.69,3.09),(s*.77,-.52,3.13)], .173,.124,
             normal=(s,0,0), steps=64, sides=48, tone=-.03)

    # Three continuous shoulder-length S-locks per side. Their roots all begin
    # at the scalp; no short oval units are chained down the neck.
    mane_levels = [
        [(.38,-.38,3.68),(.61,-.12,3.48),(.68,-.07,3.07),
         (.60,-.03,2.65),(.57,.13,2.30),(.45,.38,2.40)],
        [(.45,-.55,3.73),(.68,-.31,3.48),(.72,-.27,3.08),
         (.62,-.36,2.70),(.53,-.21,2.29),(.39,.09,2.28)],
        [(.46,-.70,3.60),(.70,-.51,3.31),(.70,-.52,2.98),
         (.52,-.56,2.62),(.44,-.36,2.24),(.29,-.09,2.33)],
    ]
    for s, side in ((-1, 'R'), (1, 'L')):
        for i, points in enumerate(mane_levels):
            # Very small left/right variation avoids a machined mirrored stack.
            path = [(s*x, y+(.012*i if s<0 else 0), z+(.023 if s<0 else 0))
                    for x,y,z in points]
            lock('mane_'+side+'_long_%02d'%i, path, .295-i*.015, .179-i*.010,
                 part='neck', normal=(s,.16,0), steps=112, sides=64,
                 profile=(25.,3.8,1.25), tone=-.018*i)
        # Short outer flicks add the reference's feathered silhouette but do
        # not carry the main mane mass. Their roots disappear into long locks.
        for i,z in enumerate((3.64,3.12,2.69)):
            x=.39-i*.06
            lock('mane_'+side+'_flick_%02d'%i,
                 [(s*x,-.29,z),(s*(x+.23),-.04,z-.21),
                  (s*(x+.33),.21,z-.30),(s*(x+.25),.43,z-.13)],
                 .206-i*.010,.136-i*.008,part='neck',normal=(s,.16,0),
                 steps=80,sides=56,profile=(23.,2.9,1.25))

    # Two full-length waves flow across the fitted rear mass, with their
    # parting hidden below the scalp rather than exposed as round root ends.
    lock('dorsal_sweep_R',[(-.12,-.29,3.57),(-.31,.00,3.30),
         (-.23,.13,2.97),(.07,.13,2.58),(.17,.14,2.28),(.37,.21,2.27)],
         .275,.147,part='neck',normal=(0,1,0),steps=112,sides=64,
         profile=(24.,3.3,1.25),tone=-.05)
    lock('dorsal_sweep_L',[(.19,-.19,3.59),(.37,.10,3.24),
         (.27,.22,2.92),(-.03,.21,2.64),(-.16,.16,2.37),(-.38,.21,2.39)],
         .246,.144,part='neck',normal=(0,1,0),steps=112,sides=64,
         profile=(24.,3.3,1.25),tone=-.02)

    # A single full plume carries the tail silhouette and closes the spaces
    # between deck locks. Four asymmetric overlapping outer waves replace nine
    # almost equal-width parallel pipes. The core has real transverse volume.
    tail_profile = (21.,4.6,1.10)
    lock('tail_full_plume',[(0,1.21,1.87),(0,1.62,2.49),(0,2.16,2.78),
         (0,2.66,2.35),(0,2.79,1.68),(0,2.73,1.02),
         (0,2.49,.55),(0,2.16,.68)],.410,.480,
         part='tail',normal=(1,0,0),steps=144,sides=80,
         profile=tail_profile,tone=-.09)
    lock('tail_L_high_wave',[(.16,1.34,2.02),(.39,1.84,2.70),
         (.50,2.40,2.54),(.49,2.65,1.97),(.43,2.72,1.41),
         (.31,3.10,1.16),(.19,3.30,1.44)],.305,.178,
         part='tail',normal=(1,0,0),steps=128,sides=72,
         profile=(23.,3.7,1.20))
    lock('tail_R_long_wave',[(-.16,1.39,2.08),(-.36,2.01,2.69),
         (-.48,2.51,2.25),(-.45,2.66,1.65),(-.36,2.62,1.01),
         (-.24,2.40,.62),(-.16,2.06,.73)],.320,.198,
         part='tail',normal=(-1,0,0),steps=128,sides=72,
         profile=(23.,3.7,1.20),tone=-.02)
    lock('tail_L_lower_sweep',[(.24,2.06,2.35),(.43,2.39,1.91),
         (.49,2.49,1.41),(.43,2.77,.91),(.28,2.61,.50),
         (.10,2.17,.53)],.310,.174,
         part='tail',normal=(1,0,0),steps=120,sides=72,
         profile=(23.,3.3,1.20),tone=-.015)
    lock('tail_back_lift',[(.04,2.20,2.48),(-.05,2.65,2.36),
         (.09,2.91,1.92),(.14,3.08,1.57),(.12,3.37,1.63)],.235,.212,
         part='tail',normal=(0,1,0),steps=104,sides=64,
         profile=(24.,2.9,1.25),tone=.015)
    lock('tail_crest_L',[(.05,1.31,1.98),(.14,1.64,2.52),
         (.13,2.11,2.81),(.07,2.57,2.80)],.242,.176,
         part='tail',normal=(1,0,0),steps=104,sides=64,tone=.02)
    lock('tail_crest_R',[(-.22,1.34,1.99),(-.28,1.60,2.41),
         (-.22,1.91,2.76),(-.13,2.24,2.91)],.209,.157,
         part='tail',normal=(-1,0,0),steps=104,sides=64,tone=.025)

    return made
