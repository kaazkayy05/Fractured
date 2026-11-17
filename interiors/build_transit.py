"""First-room review blockout. Run only on Nova_City_interiors.blend."""
import bpy, bmesh, math, json, os
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=os.path.dirname(os.path.abspath(__file__))
OUT=os.path.join(ROOT,'D-transit')
assert os.path.basename(bpy.data.filepath)=='Nova_City_interiors.blend'
sc=bpy.data.scenes['NOVA | Metropolitan Valley']
bpy.context.window.scene=sc
assert bpy.data.collections.get('INT | Transit Station') is None, 'Already built'
cx,cy=-161.280670165,-229.418075561
def world(p):return (p[0]+cx,p[1]+cy,p[2])
def coll(name,parent):
 c=bpy.data.collections.new(name);parent.children.link(c);return c
root=coll('INT | Transit Station',sc.collection)
cols={k:coll('INT | Transit Station | '+k,root) for k in ['Shell','Architecture','Props','Foliage','Lighting','Collision']}
backup=coll('_BACKUP | Tower 047',sc.collection)
backup.hide_render=True;backup.hide_viewport=True
host=[o for o in sc.objects if o.name.startswith('Tower 047 |')]
for o in host:
 b=o.copy();b.data=o.data.copy();backup.objects.link(b)
 b.name='_BACKUP | '+o.name
 for c in list(o.users_collection):c.objects.unlink(o)
 cols['Shell'].objects.link(o)
def mat(name,color,metal=0,rough=.45,emit=0):
 m=bpy.data.materials.new('INT | Blockout | '+name);m.diffuse_color=(*color,1);m.use_nodes=True
 n=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
 n.inputs['Base Color'].default_value=(*color,1);n.inputs['Metallic'].default_value=metal;n.inputs['Roughness'].default_value=rough
 if emit:n.inputs['Emission Color'].default_value=(*color,1);n.inputs['Emission Strength'].default_value=emit
 return m
white=bpy.data.materials.get('Nova | ceramic alloy') or mat('Ceramic',(.65,.7,.73))
floor=mat('Clay floor',(.22,.29,.32),.15)
clay=mat('Clay architecture',(.65,.72,.75),.15)
dark=mat('Reserved prop',(.06,.1,.12),.25)
cyan=mat('Cyan orientation',(.02,.65,.78),.1,emit=2)
amber=mat('Platform edge',(.8,.5,.07),.1)
glass=mat('Clear glass',(.38,.65,.73),.0,.13)
gn=next(n for n in glass.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
gn.inputs['Transmission Weight'].default_value=.95;gn.inputs['IOR'].default_value=1.45
glass.use_backface_culling=False
def mesh(name,verts,faces,group='Architecture',material=clay,local=True):
 me=bpy.data.meshes.new(name);me.from_pydata([world(v) if local else v for v in verts],[],faces);me.update()
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
 ob=bpy.data.objects.new(name,me);cols[group].objects.link(ob)
 if material:me.materials.append(material)
 return ob
FACES=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
def box(name,p,size,group='Architecture',material=clay):
 x,y,z=p;a,b,c=[s/2 for s in size]
 return mesh(name,[(x-a,y-b,z-c),(x+a,y-b,z-c),(x+a,y+b,z-c),(x-a,y+b,z-c),(x-a,y-b,z+c),(x+a,y-b,z+c),(x+a,y+b,z+c),(x-a,y+b,z+c)],FACES,group,material)
def active(o):
 bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
def boolean(ob,cut):
 active(ob);m=ob.modifiers.new('Measured structural aperture','BOOLEAN');m.operation='DIFFERENCE';m.solver='EXACT';m.object=cut
 bpy.ops.object.modifier_apply(modifier=m.name);bpy.data.objects.remove(cut,do_unlink=True)
def cut(ob,name,p,size):boolean(ob,box(name,p,size,material=None))
def collision(ob,name=None):
 c=ob.copy();c.data=ob.data.copy();c.name=(name or ob.name)+'_COL';cols['Collision'].objects.link(c);c.hide_render=True;c.display_type='WIRE';return c
pod=bpy.data.objects['Tower 047 | podium'];glz=bpy.data.objects['Tower 047 | glazing']
cut(pod,'Lower hall cavity',(0,0,10.8),(54.6568,60.1846,9.6))
cut(pod,'Open central volume',(0,0,12),(39.6568,45.1846,13))
cut(glz,'Upper hall cavity',(0,0,23.75),(39.6568,45.1846,18.5))
# Entry thresholds are exactly level with the concourse.
cut(pod,'E01 east entry',(27.7284,-22,8.25),(2,6,4.5))
cut(pod,'E02 south entry',(4,-30.4923,8.25),(6,2,4.5))
cut(pod,'W01 north city window',(0,30.4923,12),(32,2,6))
box('W01 north glazing',(0,30.4923,12),(32,.12,6),'Shell',glass)
collision(pod);collision(glz)
collision(bpy.data.objects['W01 north glazing'])
# Duplicate the existing glass material so the rest of the city is unaffected.
gmat=glz.data.materials[0].copy();gmat.name='INT | Transit lower shell glass';gmat.use_backface_culling=False
gn=next(n for n in gmat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
gn.inputs['Transmission Weight'].default_value=.9;gn.inputs['Roughness'].default_value=.16
# Only lower glazing faces receive transparent interior material.
glz.data.materials.append(gmat)
for p in glz.data.polygons:
 if max(glz.data.vertices[i].co.z for i in p.vertices)<=33.001:p.material_index=len(glz.data.materials)-1
slab=box('Concourse slab',(0,0,5.8),(54.6568,60.1846,.4),material=floor);collision(slab)
roof=box('Upper hall sealed ceiling',(0,0,32.8),(39.6568,45.1846,.4),'Shell',clay);collision(roof)
def beam(name,a,b,r=.07,material=clay,group='Architecture'):
 a=Vector(a);b=Vector(b);d=b-a;axis=d.normalized();u=axis.cross(Vector((0,0,1)))
 if u.length<.01:u=axis.cross(Vector((0,1,0)))
 u.normalize();v=axis.cross(u);verts=[]
 for p in [a,b]:
  for i in range(8):verts.append(tuple(p+r*(u*math.cos(i*math.tau/8)+v*math.sin(i*math.tau/8))))
 faces=[tuple(reversed(range(8))),tuple(range(8,16))]+[(i,(i+1)%8,(i+1)%8+8,i+8) for i in range(8)]
 return mesh(name,verts,faces,group,material)
def rail(name,a,b,solid=True):
 a=Vector(a);b=Vector(b);d=(b-a).length
 for i in range(max(1,math.ceil(d/2))+1):
  p=a+(b-a)*i/max(1,math.ceil(d/2));beam(name+' post',p,p+Vector((0,0,1.1)),.045)
 beam(name+' top',a+Vector((0,0,1.1)),b+Vector((0,0,1.1)),.055)
 beam(name+' middle',a+Vector((0,0,.55)),b+Vector((0,0,.55)),.035)
 if solid:
  # Closed thin glass barrier keeps collision coincident with its visible panel.
  axis=(b-a).normalized();normal=Vector((-axis.y,axis.x,0))*.025
  verts=[tuple(p+side*normal+Vector((0,0,z))) for z in [.08,1.03] for p,side in [(a,-1),(b,-1),(b,1),(a,1)]]
  collision(mesh(name+' barrier',verts,FACES,material=glass))
def ramp(name,a,b,width,thickness=.25):
 a=Vector(a);b=Vector(b);axis=Vector((b.x-a.x,b.y-a.y,0)).normalized();n=Vector((-axis.y,axis.x,0))*width/2
 verts=[tuple(p+s*n-Vector((0,0,t))) for t in [thickness,0] for p,s in [(a,-1),(b,-1),(b,1),(a,1)]]
 o=mesh(name,verts,FACES,material=floor);collision(o)
 for s in [-1,1]:rail(name+' rail',a+s*n,b+s*n)
 return o
east=box('East entrance landing',(29.15,-22,5.8),(3.65,6,.4),material=floor);collision(east)
ramp('East avenue access',(30.975,-22,6),(42.975,-22,4.5),6)
approach=box('Avenue threshold landing',(45.2,-22,4.3),(4.45,6,.4),material=floor);collision(approach)
south=box('South entrance landing',(4,-31.75,5.8),(6,3.3,.4),material=floor);collision(south)
ramp('South ground access',(4,-33.4,6),(4,-45.4,2),6)
landing=box('South ground landing',(4,-46.4,1.8),(6,2,.4),material=floor);collision(landing)
for x in [1,7]:rail('South landing edge',(x,-30.5,6),(x,-33.4,6))
for y in [-25,-19]:rail('East landing edge',(27.7,y,6),(30.975,y,6))
for x,y,z in [(29.5,-24,3.8),(29.5,-20,3.8),(2,-32,3.8),(6,-32,3.8)]:
 box('Entrance support pier',(x,y,z),(.4,.4,3.6),material=clay)
# Upper circulation: rear balcony, right balcony, stair reservation implemented as a walkable ramp.
rear=box('Rear gallery',(0,18,11.8),(38,6,.4),material=floor);collision(rear)
side=box('East gallery',(15.5,1.5,11.8),(7,27,.4),material=floor);collision(side)
ramp('Gallery accessible ramp',(9.5,-12,6),(9.5,0,12),3.5)
join=box('Ramp upper landing',(10.375,1,11.8),(5.25,2,.4),material=floor);collision(join)
rail('Rear gallery inner edge',(-19,15,12),(12,15,12))
rail('East gallery inner edge',(12,2,12),(12,15,12))
rail('East gallery front edge',(12,-12,12),(19,-12,12))
rail('East gallery lower inner edge',(12,-12,12),(12,0,12))
rail('Upper landing outer edge',(7.75,2,12),(12,2,12))
for x,y in [(-17,18),(0,18),(17,18),(16,6),(16,-10)]:box('Gallery support',(x,y,8.8),(.5,.5,5.6))
# Barrel-vault ribs and glazing: intentionally restrained blockout, no final props.
def arch(y):
 pts=[(18*math.cos(math.pi*i/32),y,12+18*math.sin(math.pi*i/32)) for i in range(33)]
 for a,b in zip(pts,pts[1:]):beam('Vault structural rib',a,b,.16)
 for x in [-18,18]:box('Vault pilaster',(x,y,9),(.35,.4,6))
for y in [-20,-10,0,10,20]:arch(y)
for i in range(32):
 a=math.pi*i/32;b=math.pi*(i+1)/32
 verts=[]
 for y in [-20,20]:
  for r,t in [(18,a),(18,b),(18.08,b),(18.08,a)]:verts.append((r*math.cos(t),y,12+r*math.sin(t)))
 mesh('Vault glass panel',verts,FACES,material=glass)
for x in [-18,18]:beam('Vault spring beam',(x,-20,12),(x,20,12),.17)
tram=box('BLOCKOUT | Tram envelope',(-12,-1,7.75),(3.4,24,3.5),'Props',clay)
active(tram);be=tram.modifiers.new('Rounded tram envelope','BEVEL');be.width=.65;be.segments=3;bpy.ops.object.modifier_apply(modifier=be.name)
collision(tram)
for x in [-12.8,-11.2]:box('Track rail',(x,-1,6.035),(.09,38,.07),material=dark)
box('Platform tactile reservation',(-8.5,-1,6.025),(.55,36,.05),material=amber)
for y in [-8,0,8]:box('Tram glazing placeholder',(-10.27,y,8.2),(.05,5,1.4),'Props',dark)
def cylinder(name,p,r,depth,material,group='Props',n=32):
 x,y,z=p;verts=[(x+r*math.cos(i*math.tau/n),y+r*math.sin(i*math.tau/n),z+s*depth/2) for s in [-1,1] for i in range(n)]
 faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
 return mesh(name,verts,faces,group,material)
island=cylinder('BLOCKOUT | Central planted island',(0,0,6.3),3.2,.6,clay);collision(island)
obelisk=mesh('BLOCKOUT | Crystal obelisk',[(-.5,-.5,6.6),(.5,-.5,6.6),(.5,.5,6.6),(-.5,.5,6.6),(-.5,-.5,10),(.5,-.5,10),(.5,.5,10),(-.5,.5,10),(0,0,11.5)],[(0,3,2,1),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,8),(5,6,8),(6,7,8),(7,4,8)],'Props',cyan)
for y in [-12,-8,-4,0,4]:
 k=box('BLOCKOUT | Ticket kiosk',(22,y,6.8),(1.2,1.2,1.6),'Props',dark);collision(k)
for y in [-14,-11,-8]:
 gate=box('BLOCKOUT | Fare gate',(17,y,6.5),(1.4,.3,1),'Props',clay);collision(gate)
podfloor=cylinder('BLOCKOUT | Control pod floor',(15,8,12),3.1,.4,clay);collision(podfloor)
cylinder('BLOCKOUT | Control pod cap',(15,8,15.5),3.1,.3,clay)
for i in range(8):
 a=i*math.tau/8;beam('Control pod frame',(15+3*math.cos(a),8+3*math.sin(a),12.2),(15+3*math.cos(a),8+3*math.sin(a),15.35),.06)
# Entry frames and spawn. Empty local -Y points inward from the south entry.
for x in [1,7]:box('South door frame',(x,-30.5,8.3),(.15,.2,4.6),material=cyan)
box('South door lintel',(4,-30.5,10.6),(6.15,.2,.15),material=cyan)
for y in [-25,-19]:box('East door frame',(27.73,y,8.3),(.2,.15,4.6),material=cyan)
box('East door lintel',(27.73,-22,10.6),(.2,6.15,.15),material=cyan)
spawn=bpy.data.objects.new('SPAWN | Transit Station',None);root.objects.link(spawn);spawn.location=world((4,-28,6.05));spawn.rotation_euler.z=math.pi;spawn.empty_display_size=.8
def camera(name,p,target,lens=21,ortho=None):
 d=bpy.data.cameras.new(name);o=bpy.data.objects.new(name,d);root.objects.link(o);o.location=world(p);o.rotation_euler=(Vector(world(target))-o.location).to_track_quat('-Z','Y').to_euler();d.lens=lens;d.clip_end=4000
 if ortho:d.type='ORTHO';d.ortho_scale=ortho
 return o
cam=camera('CAM | Transit Station',(6,-19,7.7),(-2,5,14),18)
top=camera('CAM | Transit Station | Plan',(0,-3,100),(0,-3,0),ortho=104)
def area(name,p,target,power,size):
 d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size;o=bpy.data.objects.new(name,d);cols['Lighting'].objects.link(o);o.location=world(p);o.rotation_euler=(Vector(world(target))-o.location).to_track_quat('-Z','Y').to_euler()
area('INT | Transit daylight',(0,0,29),(0,0,6),16000,22)
area('INT | Transit entry fill',(0,-22,14),(0,4,8),6000,12)
area('INT | Transit rear fill',(0,20,25),(0,0,8),12000,15)
cols['Collision'].hide_render=True;cols['Collision'].hide_viewport=True
# Topology QA of modified shells, closed collision volumes, and degenerate faces.
qa={'phase':'blockout','host':'Tower 047','floor_z':6,'gallery_z':12,'doors':{'east':world((27.7284,-22,6)),'south':world((4,-30.4923,6))},'spawn':list(spawn.location),'mesh_checks':[]}
for o in list(cols['Collision'].objects)+[pod,glz,roof]:
 bm=bmesh.new();bm.from_mesh(o.data)
 qa['mesh_checks'].append({'name':o.name,'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'zero_area_faces':sum(f.calc_area()<1e-9 for f in bm.faces),'signed_volume':bm.calc_volume(signed=True)})
 bm.free()
qa['triangles_visible']=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in root.all_objects if o.type=='MESH' and not o.name.endswith('_COL'))
qa['triangles_collision']=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in cols['Collision'].objects)
# Per-object BVHs prevent props or upper decks from masking floor holes.
surfaces=[o for o in cols['Collision'].objects if any(k in o.name for k in ['Concourse slab','access','threshold landing','entrance landing','ground landing','gallery','Gallery accessible ramp','Ramp upper landing'])]
trees=[]
for o in surfaces:
 verts=[o.matrix_world@v.co for v in o.data.vertices];faces=[list(p.vertices) for p in o.data.polygons];trees.append((o.name,BVHTree.FromPolygons(verts,faces)))
def hit(x,y,z=6.3):
 hits=[]
 for name,bvh in trees:
  co,no,idx,dist=bvh.ray_cast(Vector(world((x,y,z))),Vector((0,0,-1)),5)
  if co is not None:hits.append((co.z,name))
 return max(hits) if hits else None
holes=[];samples=0
for x in range(-26,27):
 for y in range(-29,30):
  samples+=1
  if hit(x,y) is None:holes.append([x,y])
qa['ground_grid']={'spacing_m':1,'samples':samples,'missing_floor':holes}
qa['known_issues']=['Blockout only: props are labeled massing envelopes; no final detailing.','Upper circulation uses a visible 26.6-degree ramp; reference-style stairs remain a review decision.','Reference images were not individually attached; composition follows the supplied written brief.','Full player-capsule and ceiling-clearance navigation validation, and Veyra obstruction audit remain pending.','No Veyra interior has been built yet.']
qa['collision_surface_match']='Collision surfaces copy visible solid geometry exactly, including ramps and glass railing barriers.'
with open(os.path.join(OUT,'qa-blockout.json'),'w') as f:json.dump(qa,f,indent=2)
sc.camera=cam
sc['interior_stage']='D transit blockout awaiting user review; other rooms not built'
sc.render.resolution_x=1200;sc.render.resolution_y=800;sc.render.resolution_percentage=100
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT,'Nova_City_interiors.blend'))
print('BLOCKOUT_SAVED',json.dumps({'triangles':qa['triangles_visible'],'floor_samples':samples,'holes':len(holes),'topology_failures':[r for r in qa['mesh_checks'] if r['nonmanifold_edges'] or r['zero_area_faces']]}),flush=True)
# Render setup is temporary: the saved scene retains its global sun and world.
sc.render.image_settings.file_format='PNG'
sc.render.filepath=os.path.join(OUT,'renders','D-interior-blockout.png')
bpy.ops.render.render(write_still=True)
# Plan is a true orthographic projection of the blockout with upper shell and vault hidden.
hidden=[]
for o in sc.objects:
 if o.type=='MESH' and (o.name not in root.all_objects or o.name in cols['Shell'].objects or o.name.startswith(('Vault','Upper hall','Tower 047'))):
  if not o.hide_render:hidden.append(o);o.hide_render=True
sc.camera=top
sc.render.filepath=os.path.join(OUT,'renders','D-topdown-blockout.png')
bpy.ops.render.render(write_still=True)
for o in hidden:o.hide_render=False
sc.camera=cam
print('RENDERS_COMPLETE',flush=True)
