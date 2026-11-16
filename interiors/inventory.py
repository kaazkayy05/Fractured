import bpy, json, os, sys
from mathutils import Vector
out=os.path.join(os.path.dirname(__file__),'survey')
scene=next(s for s in bpy.data.scenes if 'Metropolitan Valley' in s.name)
def bounds(o):
 p=[o.matrix_world@Vector(c) for c in o.bound_box]
 return [[round(min(v[i] for v in p),4) for i in range(3)],[round(max(v[i] for v in p),4) for i in range(3)]]
rows=[]
for o in scene.objects:
 rows.append(dict(name=o.name,type=o.type,bounds=bounds(o),origin=list(o.location),modifiers=len(o.modifiers),vertices=len(o.data.vertices) if o.type=='MESH' else None))
r=dict(file=bpy.data.filepath,scene=scene.name,objects=rows,collections=[c.name for c in bpy.data.collections],unit=scene.unit_settings.scale_length,engine=scene.render.engine)
path=os.path.join(out,'veyra-inventory.json' if 'VEYRA' in scene.name else 'nova-inventory.json')
with open(path,'w') as f:json.dump(r,f,indent=2)
print('INVENTORY_SAVED',path,len(rows))
