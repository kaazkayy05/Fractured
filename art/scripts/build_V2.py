"""V2 Veyra Flooded Transit Station — built FROM the N2 file (brief: duplicate N2, keep landmark positions).
Run: blender -b --factory-startup art/source/Fractured_N2_TransitStation.blend -P art/scripts/build_V2.py
"""
import os
import sys
import math
import json
import random
import bpy
import bmesh
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(__file__))
import fractured_common as fc
import fractured_qa as qa
import nova_kit as nk
import veyra_kit as vk

ID, NAME = "V2", "FloodedTransitStation"
assert bpy.data.collections.get("N2_Export"), "open Fractured_N2_TransitStation.blend before running this script"
M = fc.refresh_shared_materials(["M_Water"])
M.update(fc.append_shared_materials())
SIL, GLS, CYN, CHR, AMB, CLO, MOSS, VCON, BARK, WAT, LANT = (M[k] for k in (
    "M_NovaSilver", "M_NovaGlass", "M_CyanEmissive", "M_Charcoal", "M_AmberWarning", "M_Cloth", "M_Moss",
    "M_VeyraConcrete", "M_Bark", "M_Water", "M_LanternWarm"))
BM = fc.box_minmax
OB = bpy.data.objects

# ------------------------------------------------------------------ rename N2 -> V2 (landmarks keep their names)
for c in list(bpy.data.collections):
    if c.name.startswith("N2_"):
        c.name = "V2_" + c.name[3:]
for coll in (bpy.data.objects, bpy.data.meshes):
    for d in list(coll):
        for a, b in (("SM_N2_", "SM_V2_"), ("COL_N2_", "COL_V2_")):
            if d.name.startswith(a):
                d.name = b + d.name[len(a):]
C_EXP, C_ROOF, C_COL, C_FX, C_PRES, C_LM, C_MOD = (bpy.data.collections[f"V2_{n}"] for n in (
    "Export", "Roof", "Collision", "FX", "Presentation", "Landmarks", "ModuleSources"))
# brief: separate collections Water / Rubble / Roots / Structure / Habitation (all under V2_Export so they ship)
C_STR = fc.collection("V2_Structure", C_EXP)
for o in list(C_EXP.objects):
    C_STR.objects.link(o)
    C_EXP.objects.unlink(o)
C_EXP.children.unlink(C_ROOF)
C_STR.children.link(C_ROOF)
C_WAT, C_RUB, C_ROOTS, C_HAB = (fc.collection(f"V2_{n}", C_EXP) for n in ("Water", "Rubble", "Roots", "Habitation"))

HX, HY, TR, TZ, UP_Z = 18.0, 10.0, 4.0, -1.2, 5.0
WATER_Z = -0.3
BR_X0, BR_X1 = -14.0, -11.0
CR_X0, CR_Y0 = -8.0, 5.0
RAMP_X0, RAMP_X1, RAMP_Y0, RAMP_Y1 = -11.0, -8.0, -4.6, 5.0       # root ramp: right platform -> control-room level
RAMP_SLOPE = math.degrees(math.atan2(UP_Z, RAMP_Y1 - RAMP_Y0))
log = {}


def mesh(name, vfm, mats, recalc=False):
    v, f, m = vfm
    return fc.build_mesh(name, (v, f), mats, face_mats=m, recalc=recalc)


def module(name, vfm, mats, recalc=False):
    me = mesh(name, vfm, mats, recalc)
    fc.obj(name, me, C_MOD)
    return me


def place(name, me, loc=(0, 0, 0), rz=0.0, coll=None):
    return fc.obj(name, me, coll or C_STR, loc, rz)


def unique(name, vfm, mats, loc=(0, 0, 0), rz=0.0, coll=None, recalc=False):
    return place(name, mesh(name, vfm, mats, recalc), loc, rz, coll)


def kill(name):
    o = OB.get(name)
    if o:
        bpy.data.objects.remove(o, do_unlink=True)


def col(name, data):
    o = fc.obj(f"{name}-colonly", fc.build_mesh(name, data, weld=False), C_COL)
    o.display_type = "WIRE"
    return o


def recol(name, data):
    o = OB[f"{name}-colonly"]
    o.data = fc.build_mesh(name, data, weld=False)
    return o


def reskin(old, slot_map, new=None):
    me = bpy.data.meshes[old]
    me.name = new or old.replace("MOD_N_", "MOD_V_")
    for i, m in slot_map.items():
        me.materials[i] = m
    src = OB.get(old)
    if src:
        src.name = me.name
    return me


# ================================================================== 1. Veyra material pass
for n in ("MOD_N_Wall_4x4", "MOD_N_Wall_4x4_Seam", "MOD_N_Wall_4x2_Top"):
    reskin(n, {0: VCON, 2: CHR})
reskin("MOD_N_RoofRib", {1: MOSS})                                   # dead light strips -> moss on ribs
for n in ("MOD_N_Stair_2m_5rise", "MOD_N_Column_4.6", "MOD_N_BridgeLanding_3x3"):
    reskin(n, {0: VCON})
bpy.data.meshes["MOD_V_BridgeLanding_3x3"].materials[1] = CHR
for n in ("SM_V2_UpperDeck",):
    bpy.data.meshes[n].materials[0], bpy.data.meshes[n].materials[1] = VCON, CHR
for n in ("SM_V2_Wall_E", "SM_V2_Wall_W"):
    bpy.data.meshes[n].materials[0] = VCON
bpy.data.meshes["MOD_N_Floor_Trench_4x8"].materials[1] = VCON
# kept powered: street + west exit reveals and signs (wayfinding), one power node (flickering)

# ================================================================== 2. platform: chipped Veyra tiles + worn edges
def platform_tile_chipped(chip, sx=4.0, sy=6.0, t=1.2, d=0.35, depth=0.18):
    a, c = chip
    xs = [-sx / 2, a - 0.2, a, c, c + 0.2, sx / 2]
    ys = [-sy / 2, sy / 2 - d, sy / 2]
    zt = lambda x, y: t - depth if (abs(y - sy / 2) < 1e-6 and a - 1e-6 <= x <= c + 1e-6) else t
    return fc.slab_grid(xs, ys, 0.0, zt, lambda i, j: 1 if (i == 2 and j == 1) else 0, side_mat=0)


def worn_edge(chip, gap2):
    a, c = chip
    segs, x = [], -2.0
    for g0, g1 in sorted([(a - 0.25, c + 0.25), gap2]):
        if g0 > x:
            segs.append((x, g0))
        x = g1
    segs.append((x, 2.0))
    parts = [(*BM(s0, s1, -0.6, 0.0, 0.0, 0.012, skip=("bottom", "back")), 0) for s0, s1 in segs]
    parts.append((*BM(-2, 2, 0.0, 0.02, -0.17, -0.08), 1))
    return fc.mparts(*parts)


CHIPS = {"A": ((-0.6, 0.4), (1.2, 1.5)), "B": ((0.5, 1.3), (-1.5, -1.1))}
me_ptile = {k: module(f"MOD_V_Floor_Platform_4x6_{k}", platform_tile_chipped(c), [VCON, CHR]) for k, (c, g) in CHIPS.items()}
me_pedge = {k: module(f"MOD_V_PlatformEdge_4m_{k}", worn_edge(c, g), [AMB, CHR]) for k, (c, g) in CHIPS.items()}
for k in range(9):
    v = "AB"[k % 2]
    for side, rz in (("R", 0), ("L", 180)):
        t = OB[f"SM_V2_Platform_{side}_{k:02d}"]
        t.data = me_ptile[v]
        t.rotation_euler.z = math.radians(rz)        # chipped edge always faces the trench
        OB[f"SM_V2_PlatformEdge_{side}_{k:02d}"].data = me_pedge[v]

# ================================================================== 3. flooded trench (water plane + gameplay volume)
water = ([(-HX - 4.3, -TR, 0), (HX + 4.3, -TR, 0), (HX + 4.3, TR, 0), (-HX - 4.3, TR, 0)], [(0, 1, 2, 3)], [0])
place("SM_Trench_Water", mesh("SM_Trench_Water", water, [WAT]), (0, 0, WATER_Z), coll=C_WAT)
v = col("VOL_Water", BM(-HX, HX, -TR, TR, TZ, WATER_Z))
v.name = "VOL_Water-colonly"
v["gameplay"] = "water volume (hazard). Godot imports -colonly as StaticBody: convert to Area3D in the import script."

# ================================================================== 4. bridge: middle span collapsed, ends bent
kill("SM_V2_Bridge_02")
bm = bmesh.new()
bm.from_mesh(bpy.data.meshes["MOD_N_Bridge_4m"])
for vtx in bm.verts:
    if vtx.co.y > 0.6 and vtx.co.z > UP_Z + 0.4:                   # top chord / strip / diagonal ends sag and splay
        t = (vtx.co.y - 0.6) / 1.4
        vtx.co.z -= 0.55 * t * t
        vtx.co.x += math.copysign(0.25 * t * t, vtx.co.x)
me_bent = bpy.data.meshes.new("MOD_V_Bridge_4m_Bent")
bm.to_mesh(me_bent)
bm.free()
for m in (VCON, CHR, CHR):
    me_bent.materials.append(m)
fc.obj("MOD_V_Bridge_4m_Bent", me_bent, C_MOD)
OB["SM_V2_Bridge_01"].data = me_bent                                # broken end at local +Y (y = -3)
OB["SM_V2_Bridge_03"].data = me_bent
OB["SM_V2_Bridge_03"].rotation_euler.z = math.radians(180)           # broken end faces -Y (y = +1)
bx = (BR_X0 + BR_X1) / 2
pieces = [
    ("01", fc.mparts((*BM(-1.5, 1.5, -1.3, 1.3, -0.2, 0.2), 0), (*BM(-1.5, -1.35, -1.3, 1.3, 0.2, 0.35), 1)),
     dict(rot_x=24, rot_y=-6), (bx, -1.9, -0.55)),
    ("02", fc.mparts((*BM(-1.4, 1.4, -1.0, 1.0, -0.2, 0.2), 0), (*BM(1.25, 1.4, -1.0, 1.0, 0.2, 0.35), 1)),
     dict(rot_x=-30, rot_y=8), (bx + 0.2, 0.0, -0.45)),
    ("03", fc.mparts((*BM(-0.075, 0.075, -1.8, 1.8, -0.06, 0.06), 1), (*BM(-0.075, 0.075, -1.8, 1.8, 0.8, 0.92), 1)),
     dict(rot_x=6, rot_y=82), (bx - 1.0, -0.9, -0.85)),
]
for n, d, rot, loc in pieces:
    unique(f"SM_Bridge_Broken_{n}", fc.xform(d, **rot), [VCON, CHR], loc=loc, coll=C_RUB, recalc=True)
recol("COL_V2_Bridge", fc.merge(BM(BR_X0, BR_X1, -7.0, -3.0, UP_Z - 0.4, UP_Z), BM(BR_X0, BR_X1, 1.0, 5.0, UP_Z - 0.4, UP_Z),
                                BM(BR_X0, BR_X0 + 0.15, -7.0, -3.0, UP_Z, UP_Z + 1.1),
                                BM(BR_X1 - 0.15, BR_X1, -7.0, -3.0, UP_Z, UP_Z + 1.1),
                                BM(BR_X0, BR_X0 + 0.15, 1.0, 5.0, UP_Z, UP_Z + 1.1),
                                BM(BR_X1 - 0.15, BR_X1, 1.0, 5.0, UP_Z, UP_Z + 1.1)))

# ================================================================== 5. power nodes: two dimmed, one flickering
for n, state in (("01", "flicker"), ("02", "dim"), ("03", "dim")):
    o = OB[f"SM_PowerNode_{n}"]
    o["power_state"] = state
    if state == "dim":
        o.data.materials[2] = GLS                                    # crystal + band read unpowered (pale glass)
    else:
        o["flicker"] = True

# ================================================================== 6. roof: broken skylight panes + vines
def broken_bay(drop):
    bm_ = bmesh.new()
    bm_.from_mesh(bpy.data.meshes["MOD_N_RoofBay_4m"])
    VR = (HY ** 2 + 16) / 8
    VZC = 14 - VR
    VA = math.asin(HY / VR)
    dead = []
    for f in bm_.faces:
        if f.material_index != 1:
            continue
        c = f.calc_center_median()
        k = int((math.atan2(c.y, c.z - VZC) + VA) / (2 * VA / 16))
        if k in drop:
            dead.append(f)
    bmesh.ops.delete(bm_, geom=dead, context="FACES")
    me_ = bpy.data.meshes.new(f"MOD_V_RoofBay_4m_Broken_{''.join(map(str, drop))}")
    bm_.to_mesh(me_)
    bm_.free()
    for m in bpy.data.meshes["MOD_N_RoofBay_4m"].materials:
        me_.materials.append(m)
    fc.obj(me_.name, me_, C_MOD)
    return me_


bays = [broken_bay((6, 7, 9)), broken_bay((5, 8, 10))]
bay_objs = sorted([o for o in C_ROOF.objects if o.name.startswith("SM_V2_RoofBay_")], key=lambda o: o.name)
for k, i in enumerate((1, 3, 4, 7)):
    bay_objs[i].data = bays[k % 2]
me_vine = {L: module(f"MOD_V_VineCard_{L:g}m", vk.vine_card(L), [MOSS]) for L in (2.5, 3.5)}
vrng = random.Random(4)
for k in range(10):
    x = bay_objs[(1, 3, 4, 7)[k % 4]].location.x + vrng.uniform(-1.6, 1.6)
    y = vrng.uniform(-3.5, 3.5)
    z = 14.5 * math.cos(math.asin(y / 14.5)) - 0.5 - 0.6
    place(f"SM_V2_Vine_{k:02d}", me_vine[2.5 if k % 2 else 3.5], (x, y, z), vrng.uniform(0, 180), C_ROOTS)
log["skylight_bays_broken"] = "4/9 bays, 3 of 6 glass facets missing in each"

# ================================================================== 7. roots: root ramp (alternate route) + supports + wall climber
ROOT_ME = {k: module(vk.ROOT_NAMES[k], (*d, [0] * len(d[1])), [BARK], recalc=True) for k, d in vk.root_segments().items()}
place_root = lambda name, me: place(name, me, coll=C_ROOTS)
root_objs = []
ramp = vk.root_ramp(RAMP_X0, RAMP_X1, RAMP_Y0, RAMP_Y1, 0.0, UP_Z, thick=0.45, bevel=0.1)
place("SM_V2_RootRamp", module("MOD_V_RootRamp", ramp, [BARK, MOSS]), coll=C_ROOTS)
root_objs += vk.chain(place_root, ROOT_ME, "SM_V2_Root_RampGuard", (RAMP_X1 + 0.15, RAMP_Y0 + 0.2, 0.3), 0, RAMP_SLOPE, "SSSSS")
arch = place("SM_V2_Root_RampArch", ROOT_ME["A"], ((RAMP_X0 + RAMP_X1) / 2, -1.5, TZ), coll=C_ROOTS)
root_objs.append(arch)
for i, x in enumerate((RAMP_X0 + 0.5, RAMP_X1 - 0.5)):
    root_objs += vk.chain(place_root, ROOT_ME, f"SM_V2_Root_RampLeg{i}", (x, 2.0, TZ), 0, 90, "SS")
root_objs += vk.chain(place_root, ROOT_ME, "SM_V2_Root_WallE", (14.5, 6.45, 0.0), 0, 0, "SCSS")
kill("SM_V2_UpperRail_Vest")                                         # railing bay removed where the ramp lands
recol("COL_V2_UpperRails", fc.merge(BM(BR_X0, BR_X0 + 0.12, 5.0, HY, UP_Z, UP_Z + 1.1),
                                     BM(BR_X0, BR_X0 + 0.12, -10.0, -7.0, UP_Z, UP_Z + 1.1),
                                     BM(BR_X1 - 0.12, BR_X1, -8.0, -7.0, UP_Z, UP_Z + 1.1)))
col("COL_V2_RootRamp", fc.sheared_box(RAMP_X0, RAMP_X1, RAMP_Y0, -0.5, RAMP_Y1, UP_Z - 0.5, 0.5))
# the guard root ends ~0.5 m short of the landing (control-room corner): close the last metre with a rail module
place("SM_V2_RampRail", bpy.data.meshes["MOD_N_Railing_Glass_1m"], (RAMP_X1 + 0.05, RAMP_Y1 - 0.5, UP_Z - 0.26), 90,
      C_ROOTS)
col("COL_V2_RampRail", BM(RAMP_X1 - 0.05, RAMP_X1 + 0.15, RAMP_Y1 - 1.0, RAMP_Y1, UP_Z - 0.6, UP_Z + 1.1))

# ================================================================== 8. rubble (in the flooded trench under the break)
me_rub = module("SM_Rubble_Cluster", vk.rubble(31), [VCON, CHR], recalc=True)
rub = [place("SM_Rubble_Cluster_01", me_rub, (bx, -2.6, TZ), 0, C_RUB),
       place("SM_Rubble_Cluster_02", me_rub, (-5.5, 1.2, TZ), 90, C_RUB)]

# ================================================================== 9. habitation clusters (instanced)
me_sh = module("MOD_V_Shelter_Small", vk.shelter_small(), [BARK, CLO])
me_lug = module("MOD_V_LuggageStack", vk.luggage_stack(), [CHR, CLO, BARK, SIL])
me_lan = module("MOD_V_Lantern", vk.lantern(), [CHR, LANT])
me_bl = module("MOD_V_BlanketDrape", vk.blanket_drape(), [CLO])
me_bd = module("MOD_V_Bench_Damaged", vk.bench_damaged(), [SIL, CHR])
CAMP = [("Shelter", me_sh, (0.0, 0.0), 0), ("Luggage", me_lug, (1.65, 0.35), 15), ("LanternA", me_lan, (-1.5, -0.7), 0),
        ("LanternB", me_lan, (1.45, -0.75), 0)]
hab_objs = []


def cluster(name, loc, rz, items):
    e = fc.empty(name, loc, C_HAB, 0.6, "CUBE")
    e.rotation_euler.z = math.radians(rz)
    for n, me, (x, y), r in items:
        o = place(f"{name}_{n}", me, (x, y, 0), r, C_HAB)
        o.parent = e
        hab_objs.append(o)
    return e


kill("SM_V2_Cover_02")                                               # crate moved out for the right-platform camp
cluster("GRP_V2_Camp_R", (12.0, -9.0, 0.0), 180, CAMP)
cluster("GRP_V2_Camp_L", (15.3, 5.4, 0.0), 0, CAMP)
for i, b in enumerate(("SM_V2_Bench_00", "SM_V2_Bench_01")):            # right platform: blankets on intact benches
    o = OB[b]
    d = place(f"SM_V2_Blanket_{i:02d}", me_bl, (0, 0, 0), 0, C_HAB)
    d.parent = o
for b in ("SM_V2_Bench_02", "SM_V2_Bench_03"):                       # left platform benches damaged
    OB[b].data = me_bd
    OB[b].name = b.replace("Bench", "BenchDamaged")
cluster("GRP_V2_Luggage_01", (2.7, -9.6, 0.0), 180, [("Luggage", me_lug, (0, 0), 0), ("Lantern", me_lan, (0.9, 0.2), 0)])
for i, loc in enumerate([(-1.0, -9.7, 0.0), (6.8, -9.7, 0.0), (-10.0, 9.6, UP_Z), (-4.0, 9.6, UP_Z), (-7.5, 9.8, 0.0),
                         (17.4, -4.9, 0.0)]):
    hab_objs.append(place(f"SM_V2_Lantern_{i:02d}", me_lan, loc, 0, C_HAB))
log["habitation"] = "2 lean-to camps (instanced cluster), 2 blanketed benches, 2 damaged benches, luggage, 10 lanterns"

# ================================================================== 10. collision updates
bpy.context.view_layer.update()
col("COL_V2_Roots", fc.merge(*vk.hull_parts([o for o in root_objs])))
col("COL_V2_Rubble", fc.merge(*vk.hull_parts(rub)))
col("COL_V2_Habitation", fc.merge(*vk.hull_parts([o for o in hab_objs if o.data.name in ("MOD_V_Shelter_Small",
                                                                                         "MOD_V_LuggageStack")])))
covers = [o for o in C_STR.objects if o.name.startswith(("SM_V2_Cover_", "SM_V2_Bench"))]
recol("COL_V2_Props", fc.merge(*[BM(o.location.x - 0.6, o.location.x + 0.6, o.location.y - 0.6, o.location.y + 0.6, 0, 1.1)
                                 if "Cover" in o.name else
                                 BM(o.location.x - 0.9, o.location.x + 0.9, o.location.y - 0.3, o.location.y + 0.3, 0, 0.9)
                                 for o in covers]))
for o in C_COL.objects:
    o.display_type = "WIRE"
fc.empty("LM_RootRamp", ((RAMP_X0 + RAMP_X1) / 2, RAMP_Y0, 0.0), C_LM, 0.8, "ARROWS").hide_render = True
fc.empty("LM_RootRamp_Top", ((RAMP_X0 + RAMP_X1) / 2, RAMP_Y1, UP_Z), C_LM, 0.8, "ARROWS").hide_render = True
baked = fc.bake_unique_rotations(list(C_EXP.all_objects) + list(C_COL.objects))

# ================================================================== 11. presentation: warm 4000K, dimmer ambient
sun = OB["LGT_Key_6500K"]
sun.name = sun.data.name = "LGT_Key_4000K"
try:
    sun.data.use_temperature, sun.data.temperature = True, 4000
except Exception:
    sun.data.color = (1.0, 0.82, 0.62)
sun.data.energy = 4.0
sun.rotation_euler = (math.radians(34), 0, math.radians(-28))
sc = bpy.context.scene
bg = sc.world.node_tree.nodes.get("Background")
bg.inputs[0].default_value = fc.hex_lin("#B9AE97")
bg.inputs[1].default_value = 0.32
OB["REF_Player"].hide_render = True
C_MOD.hide_render = True
renders = {}
C_ROOF.hide_render = True
sc.camera = OB["CAM_TopDown"]
renders["topdown"] = fc.render(os.path.join(fc.RENDER_DIR, "V2_detail_topdown.png"), engine="BLENDER_EEVEE")
C_ROOF.hide_render = False
sc.camera = OB["CAM_EyeHeight"]
renders["eye"] = fc.render(os.path.join(fc.RENDER_DIR, "V2_detail_eyeheight.png"), engine="BLENDER_EEVEE")
sc.camera = OB["CAM_Hero34"]
renders["hero"] = fc.render(os.path.join(fc.RENDER_DIR, "V2_detail_hero34.png"), engine="BLENDER_EEVEE")
cam_r = bpy.data.objects.new("CAM_RampCheck", bpy.data.cameras.new("CAM_RampCheck"))
cam_r.data.lens = 22
cam_r.location = (-1.0, -8.6, 2.0)
C_PRES.objects.link(cam_r)
fc.look_at(cam_r, (-9.5, 1.5, 2.5))
sc.camera = cam_r
renders["ramp_route"] = fc.render(os.path.join(fc.RENDER_DIR, "V2_detail_ramp_route.png"), engine="BLENDER_EEVEE")
sun.hide_render = True
bg.inputs[1].default_value = 1.0
sc.camera = OB["CAM_EyeHeight"]
renders["eye_flat_ambient"] = fc.render(os.path.join(fc.RENDER_DIR, "V2_detail_eyeheight_flat.png"), engine="BLENDER_EEVEE")
sun.hide_render = False
bg.inputs[1].default_value = 0.32
sc.camera = OB["CAM_Hero34"]

# ================================================================== 12. Block Z + export
blend = os.path.join(fc.SOURCE_DIR, f"Fractured_{ID}_{NAME}.blend")
glb = os.path.join(fc.EXPORT_DIR, f"Fractured_{ID}_{NAME}.glb")
report = qa.run(ID, C_EXP, C_COL, C_FX, budget=150000, landmark_coll=C_LM, walk_bounds=(-HX, HX, -HY, HY),
                walkable_prefixes=("COL_V2_Platform", "COL_V2_TrenchRamp", "COL_V2_Stair_", "COL_V2_UpperDeck",
                                   "COL_V2_Landing", "COL_V2_Bridge", "COL_V2_RootRamp"),
                pair_with=os.path.join(fc.RENDER_DIR, "N2_landmarks.json"),
                allowed_drop=lambda lo, hi: abs(lo[1]) < TR)
report["v2_changes"] = log
report["ramp"] = dict(x=[RAMP_X0, RAMP_X1], y=[RAMP_Y0, RAMP_Y1], top=UP_Z, slope_deg=round(RAMP_SLOPE, 1),
                      width=RAMP_X1 - RAMP_X0, flat_top_width=round(RAMP_X1 - RAMP_X0 - 0.2, 2))
report["rotations_baked"] = baked
report["renders"] = renders
report["blend"] = blend
fc.save(blend)
report["export"] = qa.export_and_verify(C_EXP, C_COL, glb)
report["glb"] = glb
with open(os.path.join(fc.RENDER_DIR, "V2_QA_report.json"), "w") as fh:
    json.dump(report, fh, indent=2)
print("V2 DONE pass=", report["pass"], json.dumps(log))
