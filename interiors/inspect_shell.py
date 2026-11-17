import bpy
from mathutils import Vector
s=bpy.data.scenes['NOVA | Metropolitan Valley'];bpy.context.window.scene=s
p=Vector((-161.28067,-229.41808,10))
for name in ['Tower 047 | podium','Tower 047 | glazing','Upper hall sealed ceiling','Vault glass panel']:
 o=bpy.data.objects[name];ok,loc,n,idx=o.ray_cast(o.matrix_world.inverted()@p,Vector((0,0,1)))
 print(name,ok,list(loc),len(o.data.polygons),flush=True)
print('cam',list(s.camera.location),flush=True)
