"""Face-only Nyra and Fenn sculpt refinement from immutable v004 masters.

Eye geometry follows the fitted orbital skull surface. No body, costume, hair
crown, rest bone, pivot, action, driver or non-facial material is modified.
"""
from pathlib import Path
import importlib.util
import math
import bpy
import numpy as np
from mathutils import Vector

SOURCE=Path(__file__).resolve().parents[2]
HELPER_PATH=SOURCE/'cat/sculpt-v002/nyra_detail.py'
DEPENDENCIES=[HELPER_PATH]
spec=importlib.util.spec_from_file_location('face_only_sculpt_tools',HELPER_PATH)
art=importlib.util.module_from_spec(spec);spec.loader.exec_module(art)


def points(obj):
    p=np.empty(len(obj.data.vertices)*3,dtype=np.float64)
    obj.data.vertices.foreach_get('co',p)
    m=np.array(obj.matrix_world)
    return p.reshape((-1,3))@m[:3,:3].T+m[:3,3]


def write(obj,p):
    if not np.isfinite(p).all():raise ValueError('Nonfinite face geometry: '+obj.name)
    m=np.array(obj.matrix_world.inverted())
    obj.data.vertices.foreach_set('co',(p@m[:3,:3].T+m[:3,3]).ravel());obj.data.update()


def change(obj,p,operation,edits):
    difference=float(np.linalg.norm(p-points(obj),axis=1).max())
    write(obj,p)
    edits.append(dict(name=obj.name,operation=operation,max_displacement=difference))


def allowed(objects,kind):
    prefix='AST_nyra_v2_' if kind=='cat' else 'AST_fenn_v2_'
    selected=[]
    for obj in objects:
        if obj.get('asterion_component')!='body':continue
        name=obj.name
        shared=(name==prefix+'head' or name.startswith(prefix+'eye_'))
        feline=kind=='cat' and any(name.startswith(prefix+s) for s in
            ('triangular_copper_nose','smile_','cheek_fan_','cheek_split_'))
        canine=kind=='dog' and (any(name.startswith(prefix+s) for s in
            ('soft_triangular_nose','nostril_','gentle_smile_','cream_brow_')) or name.startswith('AST_fenn_v4_soft_cheek_fan_'))
        if shared or feline or canine:selected.append(obj)
    return selected


def face_materials(objects,kind):
    copied={}
    for obj in objects:
        for i,source in enumerate(list(obj.data.materials)):
            if source.name not in copied:
                material=source.copy();material.name=f'{kind}_v5_face_'+source.name.removeprefix('AST_')
                copied[source.name]=material
            obj.data.materials[i]=copied[source.name]
    return copied


def design_matrix(x,z):
    return np.column_stack((np.ones(len(x)),x,z,x*x,x*z,z*z))


def fit_orbit(head,eye,annulus,sign,width,height):
    n=np.array(Vector((sign*.53,-.847,.025)).normalized())
    u=np.cross((0,0,1),n);u/=np.linalg.norm(u);v=np.cross(n,u)
    e=points(eye);center=e[:144].mean(axis=0)
    hp=points(head);relative=hp-center
    x,z,d=relative@u,relative@v,relative@n
    r=np.sqrt((x/(width*.5))**2+(z/(height*.5))**2)
    normals=np.empty(len(head.data.vertices)*3)
    head.data.vertices.foreach_get('normal',normals)
    nm=np.array(head.matrix_world.to_3x3().inverted().transposed())
    normals=normals.reshape((-1,3))@nm.T
    mask=(r>1.22)&(r<1.78)&(d>-.17)&(d<.14)&((normals@n)>.40)
    outer=points(annulus)[-144:];outerrel=outer-center
    sample=np.concatenate((relative[mask],outerrel))
    sx,sz,sd=sample@u,sample@v,sample@n
    if len(sample)<180:raise ValueError('Insufficient orbital support samples')
    dm=design_matrix(sx,sz)
    # Weak curvature regularization handles the nearly elliptical sample ring.
    coefficients=np.linalg.solve(dm.T@dm+np.diag((0,0,0,.0002,.0002,.0002)),dm.T@sd)
    residual=sd-dm@coefficients
    eye_relative=e-center
    ex,ez,ed=eye_relative@u,eye_relative@v,eye_relative@n
    old_coefficients=np.linalg.lstsq(design_matrix(ex,ez),ed,rcond=None)[0]
    return dict(center=center,u=u,v=v,n=n,coefficients=coefficients,old_coefficients=old_coefficients,width=width,height=height,
        support_samples=len(sample),rms=float(np.sqrt(np.mean(residual*residual))))


def orbital_map(p,frame,kind,depth=True):
    c,u,v,n=frame['center'],frame['u'],frame['v'],frame['n']
    q=p-c;x,z,d=q@u,q@v,q@n
    width,height=frame['width'],frame['height']
    r=np.sqrt((x/(width*.5))**2+(z/(height*.5))**2)
    strength=np.clip((1.60-r)/.40,0,1)
    # Preserve a soft tall puppy opening, but give Nyra a lifted almond corner.
    nx=x*(1.075 if kind=='cat' else 1.015)
    flatten=np.sqrt(np.maximum(.40,1-(.40 if kind=='cat' else .18)*(x/(width*.52))**2))
    nz=z*flatten+(np.abs(x)/(width*.5))**2*(.013 if kind=='cat' else .005)
    nx=x+(nx-x)*strength;nz=z+(nz-z)*strength
    if depth:
        fitted=design_matrix(nx,nz)@frame['coefficients']
        original=design_matrix(x,z)@frame['old_coefficients']
        new_original=design_matrix(nx,nz)@frame['old_coefficients']
        # Retain each lid/lash/glint's true thickness relative to the old cap.
        # A pure surface projection would collapse the lash tube into a sheet.
        relative=d-original
        target=.25*fitted+.75*new_original-.044+relative
        d=d+(target-d)*strength
    return c+nx[:,None]*u+nz[:,None]*v+d[:,None]*n


def refit_outer_lash(obj,eye,head,annulus,frame,sign,edits):
    p=points(obj);ids=list(obj.data.polygons[0].vertices)
    sides=max(abs(ids[(i+1)%4]-ids[i]) for i in range(4))
    caps=len(p)%sides;count=(len(p)-caps)//sides
    if sides!=18 or caps not in (0,2):raise ValueError('Unexpected original outer lash topology')
    boundary=points(eye)[-144:]
    start=Vector(boundary[0 if sign>0 else 72])+Vector(frame['n'])*.007
    u,v,n=Vector(frame['u']),Vector(frame['v']),Vector(frame['n'])
    controls=[start-u*sign*.010,start+u*sign*.031+v*.008,
        start+u*sign*.065+v*.033-n*.005,start+u*sign*.085+v*.062-n*.021]
    centers=art.path(controls,count-1)
    support=art.Surface(head)
    rim_support=art.Surface(annulus)
    for i in range(count):
        hit,_=support.contact(centers[i],n,.007)
        # Inside the cut opening the head ray may hit the far cavity wall.
        # Never pull the lash backwards to it; outside the hole keep every
        # center in front of the local skin, not just its terminal tip.
        centers[i]+=n*max(0.,(hit-centers[i]).dot(n))
        # The socket transition is a separate skin mesh. A head-only support
        # ray misses this raised bridge, hiding the middle of the lash while
        # leaving its root and tip visible as disconnected black fragments.
        rim_hit,_,_,_=rim_support.tree.ray_cast(centers[i]+n*1.8,-n,3.6)
        if rim_hit is not None:
            centers[i]+=n*max(0.,(rim_hit-centers[i]).dot(n)+.006)
    for i,c in enumerate(centers):
        t=i/(count-1);tan=(centers[min(count-1,i+1)]-centers[max(0,i-1)]).normalized()
        across=tan.cross(n).normalized();normal=across.cross(tan).normalized()
        radius=(.014+.009*math.sin(math.pi*t))*(1-t**3)+.0003
        for j in range(sides):
            angle=math.tau*j/sides
            p[i*sides+j]=c+across*radius*math.cos(angle)+normal*radius*.48*math.sin(angle)
    if caps:
        p[-2]=centers[0];p[-1]=centers[-1]
    change(obj,p,'Continuous tapered outer lash sewn to the reshaped eye corner',edits)


def eyes(objects,kind,edits,g):
    prefix='AST_nyra_v2_' if kind=='cat' else 'AST_fenn_v2_'
    head=next(o for o in objects if o.name==prefix+'head')
    width,height=(.54,.405) if kind=='cat' else (.53,.455)
    frame_reports=[]
    for sign,side in ((1,'L'),(-1,'R')):
        base=prefix+'eye_'+side
        eye=next(o for o in objects if o.name==base)
        annulus=next(o for o in objects if o.name==base+'_skin_annulus')
        frame=fit_orbit(head,eye,annulus,sign,width,height)
        # Move the original cut boundary with the opening while retaining the
        # rest of the head; the same continuous field controls all eye parts.
        hp=points(head);r=hp-frame['center']
        radius=np.sqrt((r@frame['u']/(width*.5))**2+(r@frame['v']/(height*.5))**2)
        facing=r@frame['n']>-.16
        mask=(radius<1.60)&facing
        hp[mask]=orbital_map(hp[mask],frame,kind,depth=False)
        change(head,hp,'Anatomical orbital aperture reshaped with the ocular family',edits)
        for obj in objects:
            if not obj.name.startswith(base):continue
            p=points(obj)
            if obj.name.endswith('_skin_annulus'):
                target=orbital_map(p,frame,kind)
                # Keep the outer ring sewn to the actual skull rather than
                # replacing the complete rim by a uniformly offset disk.
                rows=len(p)//144;t=np.repeat(np.linspace(0,1,rows),144)
                preserve=(t*t*(3-2*t))[:,None]
                target=target*(1-preserve)+orbital_map(p,frame,kind,depth=False)*preserve
            else:
                target=orbital_map(p,frame,kind)
            change(obj,target,'Curved integrated eye surface and matching original blink shell',edits)
            if obj.name.endswith('_upper_lid') or obj.name.endswith('_lower_lid'):
                # Reduce the visible tube depth around the opening.
                p=points(obj);ids=list(obj.data.polygons[0].vertices)
                sides=max(abs(ids[(i+1)%4]-ids[i]) for i in range(4))
                caps=len(p)%sides;count=(len(p)-caps)//sides
                if sides>=12 and count>20:
                    rings=p[:count*sides].reshape((count,sides,3));center=rings.mean(axis=1)
                    rings[:]=center[:,None,:]+(rings-center[:,None,:])*(.68 if obj.name.endswith('_lower_lid') else .88)
                    change(obj,p,'Thinner lid margin without the raised button-eye rim',edits)
        iris_color(eye,frame,kind,g)
        wing=next(o for o in objects if o.name==base+'_lash_wing')
        refit_outer_lash(wing,eye,head,annulus,frame,sign,edits)
        frame_reports.append(dict(side=side,support_samples=frame['support_samples'],fit_rms=frame['rms'],
            coefficients=frame['coefficients'].tolist(),center=frame['center'].tolist(),
            iris_center_recession=float((frame['center']-points(eye)[:144].mean(axis=0))@frame['n'])))
    return frame_reports


def iris_color(obj,frame,kind,g):
    p=points(obj);q=p-frame['center'];x=q@frame['u'];z=q@frame['v']
    width,height=frame['width'],frame['height']
    ir=np.sqrt((x/(width*(.416 if kind=='cat' else .417)))**2+((z+.002)/(height*.565))**2)
    # Large dark pupils and dark upper irises are signature expression cues.
    pr=np.sqrt(((x+.009)/(width*.221))**2+((z-height*.08)/(height*.32))**2)
    angle=np.arctan2(z/height,x/width)
    upper=np.array(g.color('032016' if kind=='cat' else '07152B'))
    lower=np.array(g.color('11A16D' if kind=='cat' else '226BAA'))
    f=np.clip(.49-z/(height*.69),0,1)
    colors=upper+(lower-upper)*f[:,None]
    rays=.9+.12*np.sin(angle*43+ir*11)+.07*np.cos(angle*71-ir*7)
    fibers=np.clip((ir-.45)/.17,0,1)*np.clip((1-ir)/.08,0,1)
    colors[:,:3]*=(1+(rays-1)*fibers)[:,None]
    limb=np.clip((ir-.90)/.095,0,1)
    colors[:,:3]*=(1-.75*limb)[:,None]
    pupil=np.array(g.color('020709'))
    blend=np.clip((pr-.965)/.035,0,1)
    colors=pupil+(colors-pupil)*blend[:,None]
    ivory=np.array(g.color('E6E1D4'))
    edge=np.clip((ir-.995)/.025,0,1)
    colors=colors*(1-edge[:,None])+ivory*edge[:,None]
    colors[:,3]=1
    attr=obj.data.color_attributes.get('AST_eye_color')
    attr.data.foreach_set('color',np.clip(colors,0,1).ravel())
    shader=obj.data.materials[0].node_tree.nodes.get('Principled BSDF')
    shader.inputs['Roughness'].default_value=.28
    shader.inputs['Specular IOR Level'].default_value=.08


def muzzle(objects,kind,edits):
    prefix='AST_nyra_v2_' if kind=='cat' else 'AST_fenn_v2_'
    head=next(o for o in objects if o.name==prefix+'head')
    p=points(head)
    strength=np.clip((2.34-p[:,2])/.16,0,1)*np.clip((p[:,2]-1.91)/.16,0,1)
    strength*=np.clip((-1.24-p[:,1])/.20,0,1)
    # Broader soft whisker pads, not an elongated conical nose bridge.
    p[:,0]*=1+(.12 if kind=='cat' else .085)*strength
    p[:,1]+=.018*strength*(1-np.minimum(1,np.abs(p[:,0])/.40))
    philtrum=np.exp(-(p[:,0]/.032)**2)*np.exp(-((p[:,2]-(2.155 if kind=='cat' else 2.185))/.087)**4)
    philtrum*=np.clip((-1.28-p[:,1])/.22,0,1)
    p[:,1]+=.013*philtrum
    change(head,p,'Broader connected whisker-pad volumes and softened central muzzle',edits)
    surface=art.Surface(head)
    smile=[o for o in objects if 'smile_' in o.name]
    for obj in smile:
        p=points(obj);center=p.mean(axis=0);sign=1 if center[0]>0 else -1
        # A short central dip and raised soft outer corner are species-specific;
        # the complete existing tube remains seated on the actual moved head.
        p[:,0]*=1.08 if kind=='cat' else 1.11
        for i,value in enumerate(p):
            q,n=surface.contact(value,(0,-1,0),.0028)
            p[i]=q
        change(obj,p,'Gentle mouth line refitted to the connected muzzle',edits)
    nose=next(o for o in objects if o.name.endswith('triangular_copper_nose' if kind=='cat' else 'soft_triangular_nose'))
    center=points(nose).mean(axis=0)
    for obj in objects:
        if obj!=nose and 'nostril_' not in obj.name:continue
        p=points(obj)
        p=center+(p-center)*np.array((1.12 if kind=='cat' else .94,.82,.97))
        p[:,1]+=.008
        change(obj,p,'Small rounded triangular nose with coherent nostril placement',edits)
    return head


def cheeks(objects,kind,edits):
    for obj in objects:
        if not any(s in obj.name for s in ('cheek_fan_','cheek_split_','soft_cheek_fan_')):continue
        p=points(obj);ids=list(obj.data.polygons[0].vertices)
        sides=max(abs(ids[(i+1)%4]-ids[i]) for i in range(4))
        caps=len(p)%sides;rows=(len(p)-caps)//sides
        if not 20<=sides<=80 or caps!=2:continue
        rings=p[:rows*sides].reshape((rows,sides,3));centers=rings.mean(axis=1)
        t=np.linspace(0,1,rows)
        # Embedded tips sweep around the cheek rather than reading as tusks.
        reduced=centers-(centers-centers[0])*(.19*t*t)[:,None]
        reduced[:,1]+=.028*t*t
        delta=rings-centers[:,None,:]
        rings[:]=reduced[:,None,:]+delta*(1-.20*t[:,None,None])
        p[-1]+=reduced[-1]-centers[-1]
        change(obj,p,'Softer shorter facial fur tips following cheek curvature',edits)


def facial_color(objects,kind,g):
    for obj in objects:
        attr=obj.data.color_attributes.get('AST_eye_color')
        if attr is None:continue
        if '_eye_' in obj.name and not obj.name.endswith(('_skin_annulus','_closed_lid')):continue
        values=np.empty(len(attr.data)*4);attr.data.foreach_get('color',values);values=values.reshape((-1,4))
        # Preserve authored pigment regions, reduce excessively mottled high
        # frequency contrast around eyes and the cream whisker pads.
        p=points(obj);gain=.98+.022*np.sin(p[:,0]*17+p[:,2]*9)
        values[:,:3]*=gain[:,None]
        if kind=='cat':values[:,:3]*=np.array((1.03,1.,.97))
        attr.data.foreach_set('color',np.clip(values,0,1).ravel())
    nose=next(o for o in objects if o.name.endswith('triangular_copper_nose' if kind=='cat' else 'soft_triangular_nose'))
    shader=nose.data.materials[0].node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value=g.color('874B30' if kind=='cat' else '302112')
    shader.inputs['Roughness'].default_value=.41


def apply(g,rig,kind):
    if kind not in ('cat','dog'):raise ValueError('Expected cat or dog')
    selected=allowed(g.ASSET,kind);edits=[]
    face_materials(selected,kind)
    measurements=eyes(selected,kind,edits,g)
    muzzle(selected,kind,edits)
    cheeks(selected,kind,edits)
    facial_color(selected,kind,g)
    return dict(notes='Face-only integrated orbital curvature, larger dark pupils, connected whisker pads and softened facial fur.',
        edited_objects=edits,face_objects=[o.name for o in selected],removed_face_objects=[],added_base_clothing=[],
        face_frame=dict(center=[0,-1.0,2.47],span=[1.85,1.20,1.44]),orbital_fit=measurements,
        animation_limit='Original uniform-scale lid motion and pivots are retained; partial closure is checked but not reauthored.')
