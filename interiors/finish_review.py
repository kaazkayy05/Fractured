import bpy, os, math, json
from mathutils import Vector
ROOT=os.path.dirname(os.path.abspath(__file__));OUT=os.path.join(ROOT,'D-transit')
sc=bpy.data.scenes['NOVA | Metropolitan Valley'];bpy.context.window.scene=sc
root=bpy.data.collections['INT | Transit Station'];shell=bpy.data.collections['INT | Transit Station | Shell']
cx,cy=-161.280670165,-229.418075561
def world(p):return Vector((p[0]+cx,p[1]+cy,p[2]))
# Widen the gallery landing so all of its guardrails have a supported edge.
for name in ['Ramp upper landing','Ramp upper landing_COL']:
 o=bpy.data.objects[name]
 for v in o.data.vertices:
  v.co.x=cx+(7.75 if v.co.x<cx+11.8 else 13)
cam=bpy.data.objects['CAM | Transit Station'];cam.location=world((6,-19,7.7));cam.rotation_euler=(world((-2,5,14))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=18
sc.camera=cam
# A review needs surface relief rather than a washed-out white mass.
for n in ['INT | Transit daylight','INT | Transit entry fill','INT | Transit rear fill']:bpy.data.lights[n].energy*=.6
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT,'Nova_City_interiors.blend'))
sc.render.image_settings.file_format='PNG';sc.render.filepath=os.path.join(OUT,'renders','D-interior-blockout.png')
bpy.ops.render.render(write_still=True)
hidden=[]
for o in sc.objects:
 if o.type=='MESH' and (o.name not in root.all_objects or o.name in shell.objects or o.name.startswith(('Vault','Upper hall','Tower 047'))):
  if not o.hide_render:hidden.append(o);o.hide_render=True
sc.camera=bpy.data.objects['CAM | Transit Station | Plan']
sc.render.filepath=os.path.join(OUT,'renders','D-topdown-blockout.png')
bpy.ops.render.render(write_still=True)
for o in hidden:o.hide_render=False
# External review through the existing promenade camera; no sun/world edits.
sc.camera=bpy.data.objects['02 | Canal promenade'];sc.render.filepath=os.path.join(OUT,'renders','D-exterior-check.png')
bpy.ops.render.render(write_still=True)
print('REVIEW_RENDERS_COMPLETE',flush=True)
