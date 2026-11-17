import bpy, os, math
from mathutils import Vector
ROOT=os.path.dirname(os.path.abspath(__file__));OUT=os.path.join(ROOT,'D-transit','renders')
sc=bpy.data.scenes['NOVA | Metropolitan Valley'];bpy.context.window.scene=sc
root=bpy.data.collections['INT | Transit Station'];shell=bpy.data.collections['INT | Transit Station | Shell']
cx,cy=-161.280670165,-229.418075561
# Persist the plan camera correction while preserving the scene's EEVEE engine.
top=bpy.data.objects['CAM | Transit Station | Plan'];top.location=(cx+8,cy-8,100);top.rotation_euler=(0,0,0);top.data.ortho_scale=92
sc.camera=bpy.data.objects['CAM | Transit Station']
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT,'Nova_City_interiors.blend'))
try:sc.render.engine='BLENDER_WORKBENCH'
except TypeError as e:raise RuntimeError(str(e))
sh=sc.display.shading
sh.light='STUDIO';sh.color_type='MATERIAL';sh.show_shadows=True;sh.show_cavity=True;sh.cavity_type='BOTH'
sh.show_specular_highlight=True
# Transparent panes are suppressed in clay views so they cannot conceal the geometry.
for o in list(root.all_objects):
 if o and o.type=='MESH' and (o.name.startswith('Vault glass panel') or 'barrier' in o.name or o.name in ['Tower 047 | glazing','W01 north glazing']):o.hide_render=True
sc.render.resolution_x=1200;sc.render.resolution_y=800;sc.render.resolution_percentage=100
sc.render.image_settings.file_format='PNG';sc.render.filepath=os.path.join(OUT,'D-interior-clay.png');bpy.ops.render.render(write_still=True)
for o in list(sc.objects):
 if o and o.type=='MESH' and (o.name not in root.all_objects or o.name in shell.objects or o.name.startswith(('Vault','Upper hall','Tower 047'))):o.hide_render=True
sc.camera=top;sc.render.resolution_x=1100;sc.render.resolution_y=1100
sc.render.filepath=os.path.join(OUT,'D-topdown-blockout.png');bpy.ops.render.render(write_still=True)
print('CLAY_REVIEW_COMPLETE',flush=True)

