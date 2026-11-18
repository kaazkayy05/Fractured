"""Make web-weight copies of the team's city meshes for the root Godot project.

    blender -b --factory-startup -P art/scripts/build_city_web.py -- <in.glb> <out.glb>

- WalkGeometry* (collision source) is never touched, so walkable surfaces stay exact.
- Foliage-like meshes (leaf / canopy / foliage / grass / moss / foam) are thinned by randomly
  removing whole faces (keeps leaf cards crisp instead of collapsing them into blobs).
- Other meshes over 60k triangles get a Collapse decimate down to ~60k (never below 30%).
"""
import bpy, bmesh, random, sys

argv = sys.argv[sys.argv.index("--") + 1:]
src, dst = argv[0], argv[1]
THIN = ("leaf", "canopy", "foliage", "grass", "moss", "foam")
random.seed(7)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)


def tris(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)


before = after = 0
for o in list(bpy.context.scene.objects):
    if o.type != 'MESH':
        continue
    n = tris(o)
    before += n
    name = o.name.lower()
    if o.name.startswith("WalkGeometry"):
        after += n
        continue
    if any(k in name for k in THIN) and n > 20000:
        keep = 0.05 if n > 300000 else (0.15 if n > 100000 else 0.3)
        bm = bmesh.new()
        bm.from_mesh(o.data)
        doomed = [f for f in bm.faces if random.random() > keep]
        bmesh.ops.delete(bm, geom=doomed, context='FACES')
        loose = [v for v in bm.verts if not v.link_faces]
        bmesh.ops.delete(bm, geom=loose, context='VERTS')
        bm.to_mesh(o.data)
        bm.free()
    elif n > 40000:
        bpy.context.view_layer.objects.active = o
        for s in bpy.context.selected_objects:
            s.select_set(False)
        o.select_set(True)
        m = o.modifiers.new("web_decimate", 'DECIMATE')
        m.decimate_type = 'COLLAPSE'
        m.ratio = max(40000.0 / n, 0.2)
        bpy.ops.object.modifier_apply(modifier=m.name)
    after += tris(o)
    print("WEB %-45s %8d -> %8d" % (o.name, n, tris(o)))

print("WEB TOTAL", before, "->", after)
# untextured flat materials: UVs and vertex colours are dead weight
bpy.ops.export_scene.gltf(filepath=dst, export_format='GLB', export_apply=True, export_extras=True,
                          export_texcoords=False, export_vertex_color='NONE')
