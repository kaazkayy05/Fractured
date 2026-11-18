"""A9 — shared material library + preview. Source of truth for all shared materials.
Run: blender -b -P art/scripts/build_A9_materials.py
"""
import os
import sys
import math
import bpy
import bmesh

sys.path.insert(0, os.path.dirname(__file__))
import fractured_common as fc

sc = fc.reset_scene()
exp = fc.collection("A9_Export")
pres = fc.collection("A9_Presentation")
prev = fc.collection("PREVIEW_A9")
refc = fc.collection("_Reference")

mats = {n: fc.make_material(n, **spec) for n, spec in fc.SHARED_MATERIALS.items()}
for m in mats.values():
    m.use_fake_user = True
    try:
        m.asset_mark()
        m.asset_data.description = "Fractured shared export material (Block 0). Append, do not duplicate."
        m.asset_data.catalog_simple_name = "Fractured"
    except Exception as e:
        print("asset mark skipped:", e)

label_mat = fc.make_material("M_PREVIEW_Label", "#E8ECEF", roughness=0.8, emission=1.0)
backdrop_mat = fc.make_material("M_PREVIEW_Backdrop", "#5A6068", roughness=0.85)

spacing = 2.0
names = list(mats.keys())
x0 = -spacing * (len(names) - 1) / 2
for i, n in enumerate(names):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=2, radius=0.6)
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, 0.6))
    me = bpy.data.meshes.new("SM_MatBall_" + n[2:])
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mats[n])
    fc.obj("SM_MatBall_" + n[2:], me, exp, (x0 + i * spacing, 0, 0))

    cu = bpy.data.curves.new("TXT_" + n, "FONT")
    cu.body = n
    cu.size = 0.17
    cu.align_x = "CENTER"
    t = bpy.data.objects.new("TXT_" + n, cu)
    t.data.materials.append(label_mat)
    t.location = (x0 + i * spacing, -0.2, -0.35 if i % 2 == 0 else -0.6)
    t.rotation_euler = (math.radians(90), 0, 0)
    pres.objects.link(t)

fc.obj("PREVIEW_Backdrop", fc.build_mesh("PREVIEW_Backdrop",
       fc.box_minmax(-14, 14, -3, 3, -0.05, 0.0), [backdrop_mat]), prev)

cam_data = bpy.data.cameras.new("CAM_A9_Front")
cam_data.type = "ORTHO"
cam_data.ortho_scale = 2.0 * len(names) + 1.5
cam = bpy.data.objects.new("CAM_A9_Front", cam_data)
cam.location = (0, -20, 0.6)
cam.rotation_euler = (math.radians(90), 0, 0)
pres.objects.link(cam)
sc.camera = cam

# Flat lighting, no bloom (EEVEE 5.x has no bloom; nothing added in compositor).
sc.world.use_nodes = True
bg = sc.world.node_tree.nodes.get("Background")
bg.inputs[0].default_value = (0.5, 0.5, 0.5, 1)
bg.inputs[1].default_value = 1.0
sc.render.film_transparent = False

sc["fractured_material_source"] = True
sc["note"] = "A9 material source. Other files append materials from here (fractured_common.append_shared_materials)."

out = os.path.join(fc.RENDER_DIR, "A9_materials_flat_nobloom.png")
try:
    fc.render(out, engine="BLENDER_EEVEE", res=(1920, 540))
    print("RENDERED EEVEE", out)
except Exception as e:
    print("EEVEE failed, falling back to Workbench:", e)
    fc.setup_workbench("FLAT")
    fc.render(out, res=(1920, 540))

out2 = os.path.join(fc.RENDER_DIR, "A9_materials_workbench_flat.png")
fc.setup_workbench("FLAT", world_hex="#7F7F7F")
fc.render(out2, res=(1920, 540))

blend = fc.MATLIB_PATH
fc.save(blend)

# glb so Godot gets the same materials
bpy.ops.object.select_all(action="DESELECT")
for o in exp.objects:
    o.select_set(True)
glb = os.path.join(fc.EXPORT_DIR, "Fractured_A9_MaterialLibrary.glb")
bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB", use_selection=True,
                          export_extras=True, export_yup=True, export_apply=True,
                          export_cameras=False, export_lights=False)

print("A9 DONE")
for n, s in fc.SHARED_MATERIALS.items():
    print(f"  {n:16s} {s}")
print("  blend:", blend)
print("  glb:  ", glb)
