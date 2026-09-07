"""Volumetric Caelo and Selya sculptures derived from their approved artwork.

No source image is projected onto the geometry. The unseen sides are coherent
anatomical interpretations of the existing single-view companion illustrations.
"""
from __future__ import annotations

import math
from mathutils import Vector
from common import eye


def _palette(g):
    colors = {
        'sf_cream': ('EEE8D4', 0, .60), 'sf_muzzle': ('F0DDCC', 0, .57),
        'sf_ear': ('DCA997', 0, .59), 'sf_shadow': ('8F6C5E', 0, .62),
        'sf_blue': ('72A6DD', .08, .41), 'sf_blue_light': ('A8D9EE', .05, .40),
        'sf_blue_mid': ('5D82C5', .06, .45), 'sf_blue_dark': ('4566A9', .06, .46),
        'sf_armor_blue': ('8CB8E9', .25, .35), 'sf_gold': ('DCA34E', .7, .34),
        'sf_gold_light': ('F2CC83', .65, .30), 'sf_gold_dark': ('AA7235', .7, .38),
        'sf_gem_blue': ('68BFF0', .35, .24), 'sf_gem_blue_dark': ('386DC2', .35, .27),
        'sf_skin': ('D99552', 0, .59), 'sf_skin_light': ('E5A66C', 0, .57),
        'sf_skin_shadow': ('B87342', 0, .59), 'sf_lip': ('CD754B', 0, .51),
        'sf_coral': ('E47367', .03, .48), 'sf_coral_light': ('F09C7E', .03, .44),
        'sf_coral_mid': ('CD666A', .02, .51), 'sf_coral_dark': ('A84554', .02, .55),
        'sf_mint': ('91BBA6', .10, .48), 'sf_mint_light': ('BED9BF', .08, .42),
        'sf_petals_ivory': ('E7D9B4', .10, .48), 'sf_wing': ('D9E6C8', .10, .34),
        'sf_wing_mint': ('B4D9C8', .12, .33), 'sf_teal': ('48AD98', .30, .25),
        'sf_teal_dark': ('247B76', .30, .27),
    }
    for name, values in colors.items():
        if name not in g.M:
            g.M[name] = g.material(name, *values)


def _bezier(points, t):
    a, b, c, d = map(Vector, points)
    q = 1-t
    center = q*q*q*a+3*q*q*t*b+3*q*t*t*c+t*t*t*d
    tangent = (3*q*q*(b-a)+6*q*t*(c-b)+3*t*t*(d-c)).normalized()
    return center, tangent


def _leaf(g, name, points, width, mat, part, normal=(0, -1, 0),
          trim=None, veins=0, bulge=.045, thickness=.012, steps=36):
    """A closed, curved, pointed leaf with modeled edges and optional veins."""
    n0 = Vector(normal).normalized()
    verts, faces, sections = [], [], []
    columns = 12
    for index in range(steps+1):
        t = index/steps
        center, tangent = _bezier(points, t)
        n = n0-tangent*n0.dot(tangent)
        if n.length < .001:
            n = Vector((0, 1, .1))-tangent*tangent.dot(Vector((0, 1, .1)))
        n.normalize()
        u = tangent.cross(n).normalized()
        radius = max(.0005, width*math.sin(math.pi*t)**.72*(.86+.14*t))
        sections.append((center, n, u, radius, t))
    for layer in (1, -1):
        for center, n, u, radius, t in sections:
            for column in range(columns+1):
                v = 2*column/columns-1
                height = thickness+bulge*(1-v*v)*math.sin(math.pi*t)
                verts.append(center+u*(radius*v)+n*(height*layer))
    offset = (steps+1)*(columns+1)
    for row in range(steps):
        for column in range(columns):
            a = row*(columns+1)+column
            b = a+columns+1
            faces.extend([(a,a+1,b+1,b), (a+offset,b+offset,b+1+offset,a+1+offset)])
    boundary = list(range(columns+1))
    boundary += [r*(columns+1)+columns for r in range(1,steps+1)]
    boundary += [steps*(columns+1)+c for c in range(columns-1,-1,-1)]
    boundary += [r*(columns+1) for r in range(steps-1,0,-1)]
    for i,a in enumerate(boundary):
        b = boundary[(i+1)%len(boundary)]
        faces.append((a,b,b+offset,a+offset))
    result = g.mesh(name, verts, faces, mat, part)
    if trim:
        rim = [c-u*w+n*(thickness+.003) for c,n,u,w,t in sections]
        rim += [c+u*w+n*(thickness+.003) for c,n,u,w,t in reversed(sections)]
        g.line(name+'_gold_edge', rim+[rim[0]], .011, trim, part, resolution=3)
    if veins:
        for surface in ((1,-1) if 'wing' in name else (1,)):
            central = [c+n*(surface*(thickness+bulge*math.sin(math.pi*t)+.006))
                       for c,n,u,w,t in sections[2:-2:3]]
            g.line(name+'_central_vein_'+str(surface), central, .008, 'sf_gold', part, resolution=4)
            for k in range(1,veins+1):
                t = .18+.64*k/(veins+1)
                index = round(t*steps)
                c,n,u,w,_ = sections[index]
                tip_index = min(steps-2,index+max(2,steps//8))
                cc,nn,uu,ww,tt = sections[tip_index]
                for sign in (-1,1):
                    g.line(name+'_vein_'+str(k)+'_'+str(sign)+'_'+str(surface),
                           [c+n*(surface*(thickness+bulge*math.sin(math.pi*t)+.009)),
                            (c+cc)*.5+u*(w*.43*sign)+n*(surface*(thickness+bulge*.65)),
                            cc+uu*(ww*.91*sign)+nn*(surface*(thickness+.008))], .006,
                           'sf_gold_light',part,resolution=5)
    return result


def _basis(normal):
    n = Vector(normal).normalized()
    u = Vector((1,0,0))-n*n.x
    if u.length < .01:
        u = Vector((0,1,0))-n*n.y
    u.normalize()
    return n,u,n.cross(u).normalized()


def _star(g,name,center,normal,radius,part):
    c=Vector(center);n,u,v=_basis(normal)
    perimeter=[]
    for j in range(10):
        angle=math.pi/2+math.tau*j/10
        radius2=radius if j%2==0 else radius*.43
        perimeter.append(c+(u*math.cos(angle)+v*math.sin(angle))*radius2)
    verts=[c+n*.035]+perimeter+[c-n*.012]
    faces=[(0,1+j,1+(j+1)%10) for j in range(10)]
    faces += [(11,1+(j+1)%10,1+j) for j in range(10)]
    obj=g.mesh(name,verts,faces,'sf_gold',part,smooth=False)
    obj.data.materials.append(g.M['sf_gold_light'])
    for polygon in obj.data.polygons[:10]:
        polygon.material_index=polygon.index%2
    return obj


def _gem(g,name,center,normal,radius,part,blue=True):
    c=Vector(center);n,u,v=_basis(normal)
    vertices=[]
    for height,scale in ((0,1),(.06,.74)):
        for j in range(6):
            angle=math.pi/2+math.tau*j/6
            vertices.append(c+n*height+(u*math.cos(angle)+v*math.sin(angle))*radius*scale)
    vertices.append(c+n*.075)
    faces=[(j,(j+1)%6,6+(j+1)%6,6+j) for j in range(6)]
    faces += [(12,6+j,6+(j+1)%6) for j in range(6)]
    obj=g.mesh(name,vertices,faces,'sf_gem_blue' if blue else 'sf_teal',part,smooth=False)
    obj.data.materials.append(g.M['sf_gem_blue_dark' if blue else 'sf_teal_dark'])
    for face in obj.data.polygons:
        face.material_index=1 if face.index%3==0 else 0
    rim=[c+(u*math.cos(math.pi/2+math.tau*j/6)+v*math.sin(math.pi/2+math.tau*j/6))*radius*1.08 for j in range(6)]
    g.line(name+'_setting',rim+[rim[0]],.026,'sf_gold',part,resolution=5)
    return obj


def _band(g,name,center,radii,z,part,mat='sf_gold',radius=.018):
    x,y=center
    points=[(x+radii[0]*math.cos(math.tau*j/20),y+radii[1]*math.sin(math.tau*j/20),z) for j in range(21)]
    return g.line(name,points,radius,mat,part,resolution=4)


def _scored_lock(g,name,points,widths,depths,mat,part,normal,accent,steps=48):
    """One continuous flowing hair mass with fine longitudinal sculpt lines."""
    obj=g.sweep(name,points,widths,depths,mat,part,normal=normal,steps=steps,sides=28,ridge=.009)
    control=list(map(Vector,points)); n0=Vector(normal).normalized()
    def sample(t):
        value=t*(len(control)-1);i=min(int(value),len(control)-2);f=value-i
        a,b,c,d=control[max(i-1,0)],control[i],control[i+1],control[min(i+2,len(control)-1)]
        return .5*((2*b)+(-a+c)*f+(2*a-5*b+4*c-d)*f*f+(-a+3*b-3*c+d)*f*f*f)
    def value(values,t):
        x=t*(len(values)-1);i=min(int(x),len(values)-2);f=x-i
        return values[i]*(1-f)+values[i+1]*f
    for fraction in (-.42,.10,.52):
        line=[]
        for j in range(4,46,3):
            t=j/48;c=sample(t);tangent=(sample(min(.999,t+.002))-sample(max(.001,t-.002))).normalized()
            n=(n0-tangent*n0.dot(tangent)).normalized();u=tangent.cross(n).normalized()
            line.append(c+u*(value(widths,t)*fraction)+n*(value(depths,t)*math.sqrt(1-fraction*fraction)+.003))
        g.line(name+'_flow_'+str(fraction),line,.0045,accent,part,resolution=4)
    return obj


def _hoof(g,name,center,part):
    x,y=center;vertices=[];faces=[];sides=64
    for z,scale in ((.03,.93),(.055,1.0),(.12,1.02),(.205,.91),(.275,.78)):
        for j in range(sides):
            angle=math.tau*j/sides
            vertices.append((x+.226*scale*math.cos(angle),y+.279*scale*math.sin(angle),z))
    for layer in range(4):
        for j in range(sides):
            a=layer*sides+j;b=layer*sides+(j+1)%sides
            faces.append((a,b,b+sides,a+sides))
    faces.extend([tuple(reversed(range(sides))),tuple(range(4*sides,5*sides))])
    return g.mesh(name,vertices,faces,'sf_blue_mid',part)


def _blend_neck(mesh):
    groups={name:mesh.vertex_groups.new(name=name) for name in ('body','neck')}
    for vertex in mesh.data.vertices:
        z=(mesh.matrix_world@vertex.co).z
        t=max(0,min(1,(z-1.94)/.65));t=t*t*(3-2*t)
        if t<1:groups['body'].add([vertex.index],1-t,'REPLACE')
        if t>0:groups['neck'].add([vertex.index],t,'REPLACE')


def _pony(g):
    body_parts=[g.uv('caelo_ribcage',(0,.13,1.56),(.55,.94,.53),'sf_cream'),
                g.uv('caelo_rump',(0,.79,1.54),(.55,.57,.55),'sf_cream'),
                g.uv('caelo_chest',(0,-.55,1.57),(.51,.48,.62),'sf_cream'),
                g.uv('caelo_neck_base',(0,-.68,2.01),(.39,.43,.70),'sf_cream'),
                g.uv('caelo_neck_arch',(0,-1.00,2.53),(.39,.39,.62),'sf_cream')]
    torso=g.fuse('caelo_continuous_neck_and_body',body_parts,'body',voxel=.039,subdiv=1)
    _blend_neck(torso)
    head_parts=[g.uv('caelo_cranium',(0,-1.14,3.27),(.65,.59,.66),'sf_cream','head'),
                g.uv('caelo_cheeks',(0,-1.38,3.02),(.57,.53,.40),'sf_cream','head'),
                g.uv('caelo_equine_muzzle',(0,-1.78,2.96),(.42,.44,.31),'sf_cream','head')]
    head=g.fuse('caelo_sculpted_equine_head',head_parts,'head',voxel=.026,subdiv=1)
    for sign in (-1,1):
        side='L' if sign>0 else 'R'
        eye(g,'caelo_eye_'+side,(sign*.375,-1.667,3.30),(sign*.30,-.954,.05),.456,.58,'409CD9','sf_cream',side,head=head)
        g.uv('caelo_nostril_'+side,(sign*.205,-2.159,3.00),(.053,.015,.023),'sf_shadow','head',seg=24,rings=16)
        g.line('caelo_smile_'+side,[(0,-2.193,2.803),(sign*.16,-2.156,2.810),(sign*.28,-2.077,2.86)],.012,'sf_shadow','head',resolution=9)
        points=[(sign*.44,-.98,3.64),(sign*.55,-.96,3.97),(sign*.67,-.88,4.28),(sign*.61,-.99,4.43)]
        _leaf(g,'caelo_tall_ear_'+side,points,.21,'sf_cream','ear.'+side,normal=(0,-1,0),bulge=.082,thickness=.020)
        inside=[(sign*.45,-1.037,3.73),(sign*.54,-1.048,3.99),(sign*.65,-1.017,4.24),(sign*.61,-1.027,4.32)]
        _leaf(g,'caelo_inner_ear_'+side,inside,.132,'sf_ear','ear.'+side,normal=(0,-1,0),bulge=.013,thickness=.003,steps=28)
        for end,y in (('F',-.61),('H',.79)):
            part='leg.'+end+side;x=sign*.415
            knee_y=y-.035 if end=='F' else y+.18
            foot_y=y-.13
            parts=[g.uv('caelo_leg_root_'+part,(x,y,1.27),(.24,.29,.47),'sf_cream',part),
                   g.uv('caelo_leg_shaft_'+part,(x,knee_y,.73),(.15,.17,.48),'sf_cream',part),
                   g.uv('caelo_fetlock_'+part,(x,foot_y,.36),(.175,.195,.22),'sf_cream',part)]
            g.fuse('caelo_anatomical_'+part,parts,part,voxel=.026,subdiv=1)
            _hoof(g,'caelo_blue_hoof_'+part,(x,foot_y-.035),part)
            for z in (.39,.49):
                _band(g,'caelo_gold_anklet_'+part+str(z),(x,foot_y),(.18,.21),z,part,radius=.021)
            _gem(g,'caelo_anklet_gem_'+part,(x,foot_y-.222,.445),(0,-1,0),.097,part)
        g.line('caelo_cheek_tiara_'+side,[(0,-1.712,3.605),(sign*.37,-1.674,3.657),(sign*.62,-1.386,3.555),(sign*.63,-1.15,3.60)],.026,'sf_gold','head')
        _star(g,'caelo_temple_star_'+side,(sign*.631,-1.405,3.56),(sign*.65,-.76,0),.132,'head')
        _leaf(g,'caelo_shoulder_armor_'+side,[(sign*.34,-.54,2.30),(sign*.57,-.67,2.22),(sign*.71,-.76,1.97),(sign*.56,-.86,1.73)],
              .285,'sf_armor_blue','body',normal=(sign*.65,-.75,.10),trim='sf_gold',bulge=.04)
        _star(g,'caelo_shoulder_star_'+side,(sign*.558,-.792,2.067),(sign*.65,-.75,.1),.12,'body')
        _leaf(g,'caelo_starry_saddle_'+side,[(sign*.35,.36,2.07),(sign*.56,.34,2.10),(sign*.72,.71,1.97),(sign*.63,.97,1.77)],
              .36,'sf_armor_blue','body',normal=(sign*.94,0,.22),trim='sf_gold',bulge=.055)
        _star(g,'caelo_saddle_star_'+side,(sign*.695,.66,2.04),(sign*.96,0,.28),.145,'body')
        g.line('caelo_saddle_girth_'+side,[(sign*.51,.29,2.02),(sign*.565,.27,1.53),(sign*.38,.25,1.13)],.032,'sf_gold','body')
    _star(g,'caelo_forehead_star',(0,-1.743,3.595),(0,-1,.06),.17,'head')
    collar=[(.43*math.cos(math.tau*j/24),-.92+.47*math.sin(math.tau*j/24),
             2.25+.05*math.sin(math.tau*j/24)) for j in range(25)]
    g.line('caelo_star_collar',collar,.026,'sf_gold','neck')
    # The medallion follows the forward-raking throat. A vertical disc here
    # would bury its upper half inside the curved neck volume.
    _gem(g,'caelo_chest_jewel',(0,-1.302,1.940),(0,-.928,-.371),.24,'body')
    _star(g,'caelo_chest_star',(0,-1.422,2.208),(0,-.965,-.26),.102,'neck')
    # Broad overlapping locks follow a continuous equine crest and flow rearward.
    g.uv('caelo_mane_foundation',(0,-.84,3.55),(.55,.43,.40),'sf_blue_dark','head',seg=56,rings=32)
    for i in range(4):
        x=.27-i*.09
        points=[(x,-1.03,3.94-i*.023),(x-.26,-1.47,3.97-i*.040),
                (x-.57,-1.71,3.69-i*.080),(x-.72,-1.59,3.35-i*.045)]
        _scored_lock(g,'caelo_swept_forelock_'+str(i),points,[.045,.235,.18,.001],[.028,.092,.079,.001],
                'sf_blue','head',(0,-1,.25),'sf_blue_mid',steps=50)
    for sign in (-1,1):
        for i in range(4):
            x=sign*(.23+i*.075)
            points=[(x,-.64,3.84-i*.04),(x+sign*.12,-.46,3.36-i*.09),
                    (x+sign*.08,-.52,2.91-i*.11),(x+sign*.16,-.44,2.49-i*.10),
                    (x-sign*.06,-.59,2.25-i*.08)]
            _scored_lock(g,'caelo_cascading_mane_'+str(sign)+'_'+str(i),points,[.06,.20,.21,.15,.001],[.04,.105,.095,.075,.001],
                    'sf_blue','head' if i==0 else 'neck',(sign*.72,-.2,.05),'sf_blue_mid',steps=58)
    tail_points=[(0,1.22,1.86),(0,1.79,2.32),(0,2.39,1.92),(0,2.39,.89),(0,2.63,.73)]
    _scored_lock(g,'caelo_tail_plume_core',tail_points,[.06,.30,.34,.22,.001],[.07,.29,.30,.23,.001],
                'sf_blue','tail',(1,0,0),'sf_blue_mid',steps=64)
    for i in range(7):
        angle=math.tau*i/7
        x=.21*math.cos(angle);dy=.14*math.sin(angle)
        points=[(x*.25,1.31,1.95),(x,1.79+dy,2.37),(x*1.28,2.41+dy,1.94),
                (x*.88,2.46+dy,1.01),(x*.7,2.65+dy,.76+.10*math.sin(angle))]
        _scored_lock(g,'caelo_tail_flow_'+str(i),points,[.018,.12,.12,.09,.001],[.018,.06,.06,.047,.001],
                    'sf_blue_light' if i in (1,4) else 'sf_blue','tail',(math.cos(angle),math.sin(angle),.15),'sf_blue_mid',steps=60)
    return {'name':'Caelo','kind':'pony','family':'quadruped','bones':[
        ('body',(0,.15,1.5),(0,.15,2),None),('neck',(0,-.65,2.0),(0,-1.01,2.85),'body'),
        ('head',(0,-1.03,2.87),(0,-1.13,3.83),'neck'),
        ('ear.L',(.44,-.98,3.68),(.61,-.99,4.39),'head'),('ear.R',(-.44,-.98,3.68),(-.61,-.99,4.39),'head'),
        ('leg.FL',(.415,-.61,1.40),(.415,-.74,.22),'body'),('leg.FR',(-.415,-.61,1.40),(-.415,-.74,.22),'body'),
        ('leg.HL',(.415,.79,1.40),(.415,.66,.22),'body'),('leg.HR',(-.415,.79,1.40),(-.415,.66,.22),'body'),
        ('tail',(0,1.20,1.85),(0,2.3,1.25),'body')],
        'notes':['Ivory equine anatomy, actual four hooves, sky-blue flowing mane and plumed tail, blue eyes and gold-star tack.',
                 'Unseen rear mane and saddle construction are coherent interpretations of the approved single-view pony artwork.']}


def _fairy(g):
    parts=[g.uv('selya_torso',(0,.015,2.11),(.38,.255,.52),'sf_skin','body'),
           g.uv('selya_hips',(0,.04,1.74),(.41,.265,.30),'sf_skin','body')]
    g.fuse('selya_continuous_torso',parts,'body',voxel=.032,subdiv=1)
    g.uv('selya_neck',(0,0,2.67),(.16,.15,.23),'sf_skin','neck',seg=40,rings=28)
    head=g.fuse('selya_sculpted_face',[
        g.uv('selya_cranium',(0,0,3.30),(.70,.535,.70),'sf_skin','head'),
        g.uv('selya_lower_face',(0,-.105,2.994),(.51,.425,.31),'sf_skin','head'),
        g.uv('selya_soft_cheeks',(0,-.165,3.17),(.61,.42,.33),'sf_skin','head')],
        'head',voxel=.025,subdiv=1)
    for sign in (-1,1):
        side='L' if sign>0 else 'R'
        eye(g,'selya_eye_'+side,(sign*.302,-.558,3.238),(sign*.15,-.988,.025),.432,.516,'4AAB94','sf_skin',side,head=head)
        g.line('selya_brow_'+side,[(sign*.14,-.526,3.579),(sign*.29,-.543,3.620),(sign*.48,-.482,3.58)],.025,'sf_coral_dark','head',resolution=10)
        _leaf(g,'selya_pointed_ear_'+side,[(sign*.58,-.02,3.19),(sign*.78,-.055,3.23),(sign*.96,-.005,3.39),(sign*1.015,.025,3.47)],
              .135,'sf_skin','head',normal=(0,-1,.03),bulge=.050,thickness=.015)
        _leaf(g,'selya_inner_ear_'+side,[(sign*.64,-.070,3.21),(sign*.78,-.106,3.26),(sign*.89,-.058,3.36),(sign*.965,-.025,3.43)],
              .07,'sf_skin_shadow','head',normal=(0,-1,0),bulge=.012,thickness=.003,steps=24)
        _star(g,'selya_sun_earring_'+side,(sign*.69,-.16,3.05),(0,-1,0),.116,'head')
        _gem(g,'selya_earring_drop_'+side,(sign*.69,-.20,3.06),(0,-1,0),.060,'head',blue=False)
    g.uv('selya_button_nose',(0,-.606,3.042),(.060,.061,.064),'sf_skin_light','head',seg=32,rings=20)
    g.line('selya_gentle_smile',[(-.17,-.524,2.94),(0,-.559,2.900),(.17,-.524,2.942)],.012,'sf_skin_shadow','head',resolution=12)
    g.sweep('selya_lower_lip',[(-.12,-.551,2.922),(0,-.578,2.899),(.12,-.551,2.922)],
            [.004,.020,.004],[.004,.008,.004],'sf_lip','head',normal=(0,-1,0),steps=20,sides=12)
    for sign in (-1,1):
        side='L' if sign>0 else 'R';part='leg.'+side
        leg=g.fuse('selya_leg_'+side,[g.uv('selya_thigh_'+side,(sign*.22,.025,1.11),(.18,.18,.41),'sf_skin',part),
             g.uv('selya_calf_'+side,(sign*.245,-.008,.59),(.139,.15,.35),'sf_skin',part)],part,voxel=.025,subdiv=1)
        g.uv('selya_foot_'+side,(sign*.245,-.125,.16),(.15,.255,.13),'sf_skin',part,seg=40,rings=26)
        sole=g.uv('selya_sandal_sole_'+side,(sign*.245,-.135,.065),(.165,.278,.048),'sf_gold_dark',part,seg=48,rings=20)
        for toe in range(4):
            g.uv('selya_toe_'+side+str(toe),(sign*.245+(toe-1.5)*.056,-.327,.145),(.035,.051,.044),'sf_skin_light',part,seg=20,rings=14)
        for depth,z in ((-.24,.207),(-.01,.272)):
            g.line('selya_sandal_strap_'+side+str(z),[(sign*.245-.137,depth,z-.04),(sign*.245,depth-.025,z+.022),(sign*.245+.137,depth,z-.04)],.020,'sf_gold',part,resolution=8)
        _band(g,'selya_anklet_'+side,(sign*.245,0),(.14,.155),.405,part,radius=.023)
        _gem(g,'selya_anklet_jewel_'+side,(sign*.245,-.161,.398),(0,-1,0),.083,part,blue=False)
        for petal in range(3):
            a=petal-1
            _leaf(g,'selya_ankle_petal_'+side+str(petal),[(sign*.245+a*.015,-.15,.40),(sign*.245+a*.08,-.17,.52),
                (sign*.245+a*.105,-.12,.62),(sign*.245+a*.16,-.09,.66)],.065,'sf_coral' if petal!=1 else 'sf_gold_light',part,normal=(0,-1,0),trim='sf_gold',bulge=.014,steps=24)
        part='arm.'+side
        arm=g.sweep('selya_shaped_arm_'+side,[(sign*.34,0,2.34),(sign*.53,-.01,2.13),(sign*.69,-.025,1.88),(sign*.91,-.05,1.63)],
                    [.145,.142,.105,.073],[.14,.132,.096,.068],'sf_skin',part,normal=(0,-1,0),steps=44,sides=28)
        g.uv('selya_open_palm_'+side,(sign*.985,-.072,1.58),(.12,.077,.102),'sf_skin',part,seg=32,rings=22)
        for finger in range(4):
            fy=-.112+finger*.038
            z=1.591+(finger-1.5)*.025
            g.sweep('selya_finger_'+side+str(finger),[(sign*1.034,fy,z),(sign*1.13,fy-.025,z-.006),
                (sign*(1.19-abs(finger-1.4)*.017),fy-.043,z-.023)], [.030,.025,.007],[.024,.019,.006],
                'sf_skin',part,normal=(0,-1,0),steps=18,sides=14)
        g.sweep('selya_thumb_'+side,[(sign*.951,-.126,1.58),(sign*.996,-.18,1.49),(sign*1.052,-.19,1.465)],
                [.038,.029,.007],[.029,.023,.006],'sf_skin',part,normal=(0,-1,0),steps=22,sides=14)
        g.line('selya_wrist_cuff_'+side,[(sign*.85,-.108,1.765),(sign*.91,-.141,1.748),(sign*.983,-.099,1.735)],.025,'sf_gold',part)
        _leaf(g,'selya_wrist_leaf_'+side,[(sign*.89,-.15,1.76),(sign*.82,-.18,1.90),(sign*.84,-.14,2.02),(sign*.79,-.12,2.08)],
              .078,'sf_coral',part,normal=(0,-1,0),trim='sf_gold',bulge=.024,steps=24)
    # Bodice and every skirt tier are closed, independently modeled petals.
    g.uv('selya_mint_bodice',(0,-.002,2.18),(.392,.279,.355),'sf_mint','body',seg=56,rings=36)
    for sign in (-1,1):
        _leaf(g,'selya_coral_bodice_'+str(sign),[(sign*.08,-.297,1.94),(sign*.22,-.302,2.19),(sign*.25,-.25,2.44),(sign*.31,-.18,2.52)],
              .145,'sf_coral','body',normal=(0,-1,0),trim='sf_gold',veins=3,bulge=.028)
    _band(g,'selya_leaf_belt',(0,.012),(.405,.287),1.94,'body',radius=.035)
    _gem(g,'selya_waist_emerald',(0,-.319,1.96),(0,-1,0),.17,'body',blue=False)
    g.line('selya_necklace',[(-.18,-.117,2.58),(0,-.215,2.55),(.18,-.117,2.58)],.024,'sf_gold','neck')
    _gem(g,'selya_heart_pendant',(0,-.227,2.535),(0,-1,0),.105,'neck',blue=False)
    for layer,(count,top,bottom,radius,material) in enumerate(((10,1.88,.62,.78,'sf_mint'),(9,1.94,.89,.79,'sf_petals_ivory'),(8,1.99,1.11,.76,'sf_coral'))):
        for j in range(count):
            angle=math.tau*(j+.5*(layer%2))/count
            direction=Vector((math.sin(angle),math.cos(angle),0))
            start=direction*.25+Vector((0,.015,top))
            end=direction*radius+Vector((0,.01,bottom+.055*math.cos(j*1.7)))
            points=[start,start+direction*.20+Vector((0,0,-.17)),end-direction*.11+Vector((0,0,.22)),end]
            _leaf(g,'selya_dress_petal_'+str(layer)+'_'+str(j),points,.235 if layer==0 else .248,
                  material,'body',normal=tuple(direction),trim='sf_gold',veins=2 if layer==2 else 1,
                  bulge=.039,thickness=.012,steps=34)
    # Four milk-glass membranes are solid shells with visible physical veins.
    for sign in (-1,1):
        side='L' if sign>0 else 'R';part='wing.'+side
        _leaf(g,'selya_upper_wing_'+side,[(sign*.26,.28,2.42),(sign*.70,.39,2.80),(sign*1.65,.58,3.39),(sign*1.91,.56,3.37)],
              .355,'sf_wing',part,normal=(0,-1,.12),trim='sf_gold',veins=7,bulge=.045,thickness=.014,steps=48)
        _leaf(g,'selya_lower_wing_'+side,[(sign*.24,.29,2.37),(sign*.65,.40,2.46),(sign*1.45,.52,2.34),(sign*1.58,.52,2.16)],
              .270,'sf_wing_mint',part,normal=(0,-1,.15),trim='sf_gold',veins=5,bulge=.035,thickness=.014,steps=40)
    # Continuous cap and broad wavy locks, not separate spherical curls.
    g.uv('selya_continuous_hair_cap',(0,.085,3.40),(.754,.572,.718),'sf_coral','head',seg=64,rings=40)
    for j in range(13):
        angle=-.1+math.pi*1.20*j/12
        x=.67*math.cos(angle);y=.08+.39*math.sin(angle)
        points=[(x*.72,y*.75,3.83),(x,y+.16,3.26),(x*1.16+.065*math.sin(j),y+.08,2.74),
                (x*1.30-.075*math.sin(j),y+.25,2.24),(x*1.11+.105*math.sin(j),y+.10,1.73+.145*math.sin(j*1.3))]
        _scored_lock(g,'selya_long_wavy_hair_'+str(j),points,[.06,.16,.173,.15,.001],[.035,.082,.105,.080,.001],
                'sf_coral','head',(math.cos(angle),math.sin(angle),.1),'sf_coral_mid',steps=58)
    for j in range(17):
        theta=.03+(math.pi-.06)*j/16
        points=[]
        for k in range(11):
            phi=.20+k*.145
            points.append((.759*math.sin(phi)*math.cos(theta),.085+.579*math.sin(phi)*math.sin(theta),3.40+.724*math.cos(phi)))
        g.line('selya_crown_hair_flow_'+str(j),points,.0055,'sf_coral_mid','head',resolution=5)
    for sign in (-1,1):
        for j in range(3):
            points=[(sign*(.30+j*.075),-.30,3.86-j*.05),(sign*(.62+j*.047),-.55,3.45-j*.06),
                    (sign*(.61+j*.056),-.42,2.96-j*.07),(sign*(.75+j*.045),-.30,2.70-j*.09),
                    (sign*(.61+j*.07),-.33,2.49-j*.10)]
            _scored_lock(g,'selya_face_framing_wave_'+str(sign)+'_'+str(j),points,[.045,.135,.13,.10,.001],[.03,.069,.065,.057,.001],
                    'sf_coral','head',(0,-1,0),'sf_coral_mid',steps=52)
    for j in range(3):
        points=[(.18-j*.055,-.24,3.995),(-.03-j*.065,-.53,3.96-j*.034),
                (-.40-j*.052,-.60,3.75-j*.071),(-.48-j*.06,-.50,3.52-j*.080)]
        _scored_lock(g,'selya_swept_bang_'+str(j),points,[.025,.17,.15,.001],[.02,.065,.055,.001],
                'sf_coral','head',(0,-1,.15),'sf_coral_mid',steps=48)
    bun=g.uv('selya_topknot_core',(.25,.19,4.052),(.27,.25,.34),'sf_coral','head',seg=48,rings=30)
    for j in range(5):
        phi=math.tau*j/5
        points=[]
        for k in range(6):
            t=k/5;a=phi+t*2.4
            points.append((.25+.255*math.cos(a)*math.sin(math.pi*(t*.77+.08)),.19+.244*math.sin(a)*math.sin(math.pi*(t*.77+.08)),3.86+t*.51))
        g.sweep('selya_topknot_lock_'+str(j),points,[.025,.11,.10,.001],[.018,.057,.058,.001],
                'sf_coral_light' if j%2 else 'sf_coral_mid','head',normal=(math.cos(phi),math.sin(phi),.1),steps=36,sides=20,ridge=.008)
    _band(g,'selya_topknot_band',(.25,.19),(.228,.23),3.899,'head',radius=.027)
    flower_center=Vector((.63,-.315,3.82));normal=Vector((.30,-.953,.04));_,u,v=_basis(normal)
    for j in range(7):
        angle=math.tau*j/7
        direction=u*math.cos(angle)+v*math.sin(angle)
        points=[flower_center,flower_center+direction*.13+normal*.015,flower_center+direction*.24,flower_center+direction*.28]
        _leaf(g,'selya_hair_flower_petal_'+str(j),points,.081,'sf_coral' if j%2 else 'sf_coral_light','head',normal=tuple(normal),trim='sf_gold',bulge=.020,thickness=.009,steps=24)
    _gem(g,'selya_hair_flower_center',flower_center+normal*.05,normal,.104,'head',blue=False)
    return {'name':'Selya','kind':'fairy','family':'biped','bones':[
        ('body',(0,.02,1.55),(0,.02,2.37),None),('neck',(0,0,2.39),(0,0,2.77),'body'),
        ('head',(0,0,2.77),(0,0,3.89),'neck'),('arm.L',(.35,0,2.34),(1.01,-.07,1.58),'body'),
        ('arm.R',(-.35,0,2.34),(-1.01,-.07,1.58),'body'),('leg.L',(.22,.025,1.48),(.245,-.01,.22),'body'),
        ('leg.R',(-.22,.025,1.48),(-.245,-.01,.22),'body'),('wing.L',(.27,.29,2.40),(1.43,.5,2.99),'body'),
        ('wing.R',(-.27,.29,2.40),(-1.43,.5,2.99),'body')],
        'notes':['Warm tan chibi fairy with coral wavy hair, teal eyes, pointed ears and four modeled pearl-mint wings with gold veins.',
                 'Radially layered coral, ivory and mint petal dress, open hands, gold leaf jewelry and physical sandals.',
                 'Rear hair, wing thickness and hidden dress petals are coherent interpretations of the approved single-view fairy artwork.']}


def build(g,kind):
    _palette(g)
    if kind=='pony':
        return _pony(g)
    if kind=='fairy':
        return _fairy(g)
    raise ValueError(f"sky_folk does not build {kind!r}")
