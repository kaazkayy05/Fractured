import bpy,sys,os,bmesh
from mathutils import Vector
from collections import defaultdict
city=sys.argv[-1]
sc=next(s for s in bpy.data.scenes if 'Metropolitan Valley' in s.name)
bpy.context.window.scene=sc
groups=defaultdict(list)
for o in list(sc.objects):
 if o.type not in ('MESH','CURVE') or any(c.name.startswith('_BACKUP') for c in o.users_collection):continue
 physical=o.name.endswith('_COL')
 interior=any(c.name.startswith('INT |') for c in o.users_collection)
 if o.hide_render and not physical:continue
 if physical: groups['collision'].append(o);continue
 groups['visual'].append(o)
 if not interior and o.type=='MESH' and (o.name.endswith((' | podium',' | glazing')) or any(k in o.name.lower() for k in ['terrain','foundation','paving','terraces','avenue','boulevards','retaining walls','footbridges','viaduct','expressway','gateway towers','civic circular terrace','lookout terrace','cliff columns','surviving floor slabs'])):groups['collision'].append(o)
# Batch geometry by material to keep runtime draw calls modest.
from array import array
deps=bpy.context.evaluated_depsgraph_get()
batches={}
for category,objects in groups.items():
 for o in objects:
  if o.type=='MESH':me=o.data
  else:
   ev=o.evaluated_get(deps);me=ev.to_mesh()
  if not me:continue
  me.calc_loop_triangles()
  pts=[tuple(o.matrix_world@v.co) for v in me.vertices]
  indexed=defaultdict(list)
  for t in me.loop_triangles:
   ma=me.materials[t.material_index] if category=='visual' and t.material_index<len(me.materials) else None
   indexed[ma].append(tuple(t.vertices))
  for ma,tris in indexed.items():
   key=(category,ma);vs,fs=batches.setdefault(key,([],[]));offset=len(vs);vs.extend(pts);fs.extend((a+offset,b+offset,c+offset) for a,b,c in tris)
  if o.type=='CURVE':ev.to_mesh_clear()
ns=bpy.data.scenes.new('Game export');bpy.context.window.scene=ns
for (cat,ma),(vs,fs) in batches.items():
 name='WalkGeometry' if cat=='collision' else 'Surface_'+(ma.name if ma else 'default')
 me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.update()
 ob=bpy.data.objects.new(name,me);ns.collection.objects.link(ob)
 if ma:me.materials.append(ma)
bpy.ops.export_scene.gltf(filepath=os.path.abspath('playtest/worlds/'+city+'.glb'),use_active_scene=True,export_format='GLB',export_texcoords=False,export_normals=True,export_animations=False)
print('DONE',city)
