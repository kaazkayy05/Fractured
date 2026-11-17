import bpy, bmesh, ast, os, math, json
from mathutils import Vector
ROOT=os.path.dirname(os.path.abspath(__file__));OUT=os.path.join(ROOT,'D-transit')
sc=bpy.data.scenes['NOVA | Metropolitan Valley'];bpy.context.window.scene=sc
root=bpy.data.collections['INT | Transit Station'];cols={k:bpy.data.collections['INT | Transit Station | '+k] for k in ['Shell','Architecture','Props','Foliage','Lighting','Collision']}
cx,cy=-161.280670165,-229.418075561
clay=bpy.data.materials['INT | Blockout | Clay architecture'];glass=bpy.data.materials['INT | Blockout | Clear glass']
tree=ast.parse(open(os.path.join(ROOT,'build_transit.py')).read())
defs=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['world','mesh','collision','beam','rail']]
defs += [n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='FACES' for t in n.targets)]
exec(compile(ast.Module(body=defs,type_ignores=[]),'<blockout_helpers>','exec'))
rail('Rear gallery outer guard',(-19,21,12),(19,21,12))
rail('Rear gallery west guard',(-19,15,12),(-19,21,12))
rail('East gallery outer guard',(19,-12,12),(19,21,12))
# Transparent blockout glazing keeps the vault ribs and city view legible in EEVEE.
for material in [glass,bpy.data.materials['INT | Transit lower shell glass']]:
 node=next(n for n in material.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
 node.inputs['Alpha'].default_value=.16
 node.inputs['Transmission Weight'].default_value=0
 methods=[i.identifier for i in material.bl_rna.properties['surface_render_method'].enum_items]
 if 'DITHERED' in methods:material.surface_render_method='DITHERED'
glz=bpy.data.objects['Tower 047 | glazing']
bm=bmesh.new();bm.from_mesh(glz.data)
bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.00001,plane_co=(0,0,33),plane_no=(0,0,1),clear_inner=False,clear_outer=False)
bm.to_mesh(glz.data);bm.free();glz.data.update()
for face in glz.data.polygons:
 if face.center.z<33:face.material_index=len(glz.data.materials)-1
# Verify originals and paired host bounds without changing either source file.
n=json.load(open(os.path.join(ROOT,'survey','nova-inventory.json')));v=json.load(open(os.path.join(ROOT,'survey','veyra-inventory.json')))
nm={o['name']:o for o in n['objects']};vm={o['name']:o for o in v['objects']}
qa=json.load(open(os.path.join(OUT,'qa-blockout.json')))
qa['paired_host_bounds_match']=all(nm[k]['bounds']==vm[k]['bounds'] for k in nm if k.startswith('Tower 047 |'))
qa['mesh_checks']=[]
for o in list(cols['Collision'].objects)+[bpy.data.objects['Tower 047 | podium'],bpy.data.objects['Tower 047 | glazing'],bpy.data.objects['Upper hall sealed ceiling']]:
 bm=bmesh.new();bm.from_mesh(o.data)
 qa['mesh_checks'].append({'name':o.name,'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'zero_area_faces':sum(f.calc_area()<1e-9 for f in bm.faces),'signed_volume':bm.calc_volume(signed=True)});bm.free()
qa['triangles_visible']=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in root.all_objects if o.type=='MESH' and not o.name.endswith('_COL'))
qa['triangles_collision']=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in cols['Collision'].objects)
qa['ramps']=[{'name':'East avenue access','rise_m':1.5,'run_m':12,'slope_degrees':math.degrees(math.atan(1.5/12))},{'name':'South ground access','rise_m':4,'run_m':12,'slope_degrees':math.degrees(math.atan(4/12))},{'name':'Gallery accessible ramp','rise_m':6,'run_m':12,'slope_degrees':math.degrees(math.atan(6/12))}]
qa['camera']={'location':list(bpy.data.objects['CAM | Transit Station'].location),'lens_mm':18,'eye_above_floor_m':1.7}
qa['ceiling_difference']='The glazed vault is an interior canopy below retained upper tower floors; it does not open to the sky. Side glazing supplies the exterior views. This preserves the existing tower silhouette.'
json.dump(qa,open(os.path.join(OUT,'qa-blockout.json'),'w'),indent=2)
brief=json.load(open(os.path.join(OUT,'room-brief.json')));brief['productionCamera'].update(location=qa['camera']['location'],target=[cx-2,cy+5,14],verticalFovDegrees=67.38);json.dump(brief,open(os.path.join(OUT,'room-brief.json'),'w'),indent=2)
# Persist a selection useful on opening, without modifying global sun/world.
bpy.ops.object.select_all(action='DESELECT');cam=bpy.data.objects['CAM | Transit Station'];cam.select_set(True);bpy.context.view_layer.objects.active=cam;sc.camera=cam
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':area.spaces.active.region_3d.view_perspective='CAMERA'
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT,'Nova_City_interiors.blend'))
sc.render.image_settings.file_format='PNG';sc.render.filepath=os.path.join(OUT,'renders','D-interior-blockout.png');bpy.ops.render.render(write_still=True)
hidden=[]
for o in sc.objects:
 if o.type=='MESH' and (o.name not in root.all_objects or o.name in cols['Shell'].objects or o.name.startswith(('Vault','Upper hall','Tower 047'))):
  if not o.hide_render:hidden.append(o);o.hide_render=True
sc.camera=bpy.data.objects['CAM | Transit Station | Plan'];sc.camera.location=world((8,-8,100));sc.camera.rotation_euler=(Vector(world((8,-8,0)))-sc.camera.location).to_track_quat('-Z','Y').to_euler();sc.camera.data.ortho_scale=92
sc.render.resolution_x=1100;sc.render.resolution_y=1100
sc.render.filepath=os.path.join(OUT,'renders','D-topdown-blockout.png');bpy.ops.render.render(write_still=True)
print('FINAL_BLOCKOUT',qa['triangles_visible'],qa['triangles_collision'],flush=True)
