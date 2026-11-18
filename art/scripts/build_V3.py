"""V3 Veyra Survivor Sanctuary — built FROM the N3 file (brief: duplicate N3, keep balconies, stair, apartment doors).
Run: blender -b --factory-startup art/source/Fractured_N3_ResidentialAtrium.blend -P art/scripts/build_V3.py
"""
import os
import sys
import math
import json
import random
import bpy
import bmesh
from mathutils import Matrix, Vector, Euler
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(__file__))
import fractured_common as fc
import fractured_qa as qa
import veyra_kit as vk

ID, NAME = "V3", "SurvivorSanctuary"
assert bpy.data.collections.get("N3_Export"), "open Fractured_N3_ResidentialAtrium.blend before running this script"
M = fc.refresh_shared_materials(["M_Water"])
M.update(fc.append_shared_materials())
SIL, GLS, CYN, CHR, CLO, MOSS, BARK, VCON, LANT = (M[k] for k in (
    "M_NovaSilver", "M_NovaGlass", "M_CyanEmissive", "M_Charcoal", "M_Cloth", "M_Moss", "M_Bark", "M_VeyraConcrete",
    "M_LanternWarm"))
BM = fc.box_minmax
OB = bpy.data.objects

# ------------------------------------------------------------------ rename N3 -> V3 (landmarks keep their names)
for c in list(bpy.data.collections):
    if c.name.startswith("N3_"):
        c.name = "V3_" + c.name[3:]
for coll in (bpy.data.objects, bpy.data.meshes):
    for d in list(coll):
        for a, b in (("SM_N3_", "SM_V3_"), ("COL_N3_", "COL_V3_")):
            if d.name.startswith(a):
                d.name = b + d.name[len(a):]
C_EXP, C_ROOF, C_APT, C_COL, C_FX, C_PRES, C_LM, C_MOD = (bpy.data.collections[f"V3_{n}"] for n in (
    "Export", "Roof", "Apartments", "Collision", "FX", "Presentation", "Landmarks", "ModuleSources"))
C_TREE = fc.collection("V3_Banyan", C_EXP)
C_HAB = fc.collection("V3_Habitation", C_EXP)

HX, HY = 15.0, 11.0
IX0, IX1, IY1 = -12.5, 12.5, 8.5
PL_X, PL_Y = 0.0, -1.5
TRUNK = Vector((PL_X, PL_Y, 0.0))
GATHER_C, GATHER_R = (0.0, -8.0), 3.0
INHABITED = {1: (-8.0, 0.0), 2: (0.0, 4.0), 3: (8.0, 8.0)}            # level -> (door x, z)
# 2 m routes to every inhabited door (rect x0, x1, y0, y1, level z) — roots and props must stay out
ROUTES = {
    "gather_to_stair": (3.0, 12.5, -7.6, -5.6, 0.0),
    "gather_to_L1_west": (-12.0, -10.0, -8.0, 11.0, 0.0),
    "L1_door_approach": (-12.0, -7.0, 9.0, 11.0, 0.0),
    "L2_right_balcony": (13.0, 15.0, 0.0, 9.0, 4.0),
    "L2_back_balcony": (-1.0, 15.0, 9.0, 11.0, 4.0),
    "L3_back_balcony": (7.0, 12.5, 9.0, 11.0, 8.0),
}
log = {}


def mesh(name, vfm, mats, recalc=False):
    v, f, m = vfm
    return fc.build_mesh(name, (v, f), mats, face_mats=m, recalc=recalc)


def module(name, vfm, mats, recalc=False):
    me = mesh(name, vfm, mats, recalc)
    fc.obj(name, me, C_MOD)
    return me


def place(name, me, loc=(0, 0, 0), rz=0.0, coll=None):
    return fc.obj(name, me, coll or C_EXP, loc, rz)


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


def reskin(old, slot_map, new=None):
    me = bpy.data.meshes[old]
    me.name = new or old.replace("MOD_N_", "MOD_V_")
    for i, m in slot_map.items():
        me.materials[i] = m
    src = OB.get(old)
    if src:
        src.name = me.name
    return me


# ================================================================== 1. Veyra material pass (cyan off except exits + workstation)
for me in list(bpy.data.meshes):
    if me.name.startswith("MOD_N_Wall_"):
        reskin(me.name, {0: VCON, 2: CHR})
    elif me.name.startswith("MOD_N_Floor_"):
        reskin(me.name, {0: VCON})
for n in ("SM_V3_Balcony_L2", "SM_V3_Balcony_L3", "SM_V3_TopTrim_12m", "SM_V3_Stair_Landing"):
    bpy.data.meshes[n].materials[0], bpy.data.meshes[n].materials[1] = VCON, CHR
reskin("MOD_N_Stair_3m_4rise", {0: VCON})
reskin("MOD_N_Column_3.6", {0: VCON})
reskin("MOD_N_AptDoor", {1: CHR})                                    # lintel strips dead; inhabited doors get warm light
reskin("MOD_N_AptInterior", {3: CHR})
reskin("MOD_N_RoofBeam_24m", {1: CHR})
bpy.data.meshes["SM_V3_Planter"].materials[2] = VCON

# ================================================================== 2. banyan (replaces the planter tree)
for n in ["SM_V3_Tree"] + [f"SM_V3_Shrub_{i}" for i in range(4)] + [f"SM_V3_Bench_{i:02d}" for i in (2, 3, 4, 5)]:
    kill(n)
kill("COL_V3_TreeTrunk-colonly")
OB["COL_V3_Benches-colonly"].data = fc.build_mesh("COL_V3_Benches", fc.merge(
    *[BM(x - 0.9, x + 0.9, -5.15, -4.55, 0, 0.9) for x in (-2.0, 2.0)]), weld=False)
tree_tris = 0
seg_hulls = []                                                   # collision: one convex hull per tube segment
tube_rng = random.Random(3)


def add_tube(name, path, radii, mats, sides=8, coll=C_TREE, collide=True, jitter=0.1, twist=0.25):
    global tree_tris
    v, f, rings = vk.tube(path, radii, sides=sides, twist=twist, jitter=jitter, seed=tube_rng.randint(0, 999),
                          return_rings=True)
    o = unique(name, (v, f, [mats] * len(f)), [BARK, MOSS], coll=coll, recalc=True)
    tree_tris += fc.tri_count(o)
    if collide:
        seg_hulls.extend(vk.hull_points([a + b for a, b in zip(rings, rings[1:])]))
    return o


# trunk: 10-sided, ~3 m diameter at the planter top, rising to ~14 m
tz = [0.0, 0.8, 2.0, 4.0, 7.0, 10.0, 12.5, 14.2]
tr = [1.75, 1.5, 1.35, 1.2, 1.05, 0.9, 0.75, 0.5]
trunk_path = [(PL_X + 0.03 * z, PL_Y + 0.02 * z, z) for z in tz]
add_tube("SM_Banyan_Trunk", trunk_path, tr, 0, sides=10, jitter=0.08, twist=0.15)


def planter_exit(d):
    """Distance from the trunk centre to the planter edge along unit 2D direction d (8 x 6 bed)."""
    return min(4.0 / max(abs(d.x), 1e-6), 3.0 / max(abs(d.y), 1e-6))


def floor_root(angle, length, extra=None):
    d = Vector((math.cos(math.radians(angle)), math.sin(math.radians(angle))))
    e = planter_exit(d)
    p = lambda r, z: (PL_X + d.x * r, PL_Y + d.y * r, z)
    path = [p(1.0, 2.4), p(2.2, 1.55), p(e - 0.2, 1.05), p(e + 0.6, 0.4)]
    if length > e + 1.6:
        path.append(p((e + 0.6 + length) / 2, 0.28))
    path.append(p(length, 0.22))
    radii = [0.75, 0.6, 0.48, 0.38] + ([0.3] if len(path) == 6 else []) + [0.16]
    if extra:
        path += extra
        radii = radii[:-1] + [0.3] * len(extra) + [0.2]
        radii = radii[:len(path)]
    return path, radii


ROOTS = [(10, 7.0, None), (40, 7.5, None), (125, 7.2, None), (160, 9.4, None), (195, 9.4, None),
         (335, 7.2, None),                                 # nothing heads south: that is the 6 m gathering area
         # wraps the back level-2 balcony edge at x = -3 (beyond the L2 door route, which comes from the east)
         (101, 9.4, [(-2.9, 8.2, 1.4), (-2.95, 8.25, 3.0), (-3.0, 8.3, 3.75), (-3.0, 8.6, 4.22), (-3.0, 9.15, 4.2)])]
for i, (a, L, ex) in enumerate(ROOTS):
    path, radii = floor_root(a, L, ex)
    add_tube(f"SM_Banyan_Root_{i + 1:02d}", path, radii, 0)
# limbs from the trunk that wrap the left level-2 and back level-3 balcony edges
add_tube("SM_Banyan_Root_09", [(-0.6, -1.3, 5.6), (-3.5, -0.6, 5.5), (-7.0, 0.5, 5.15), (-10.5, 1.5, 4.75),
                               (-12.3, 1.9, 4.35), (-12.75, 2.0, 4.25), (-13.4, 2.05, 4.2)],
         [0.6, 0.48, 0.4, 0.34, 0.3, 0.27, 0.2], 0)
add_tube("SM_Banyan_Root_10", [(-0.2, -0.6, 9.2), (-2.4, 2.6, 9.0), (-4.6, 6.0, 8.6), (-5.8, 8.25, 8.3),
                               (-6.0, 8.65, 8.24), (-6.0, 9.2, 8.2)], [0.55, 0.45, 0.38, 0.3, 0.27, 0.2], 0)
# aerial-root drops: simple tapered 6-sided prisms
DROPS = [(-6.5, 0.1, 5.0, 0.0), (3.5, 2.6, 10.2, 0.0), (-3.4, -3.8, 10.0, 0.8), (2.8, -4.0, 10.1, 0.8),
         (-4.6, 6.2, 8.4, 0.0)]
drop_col = []
for i, (x, y, zt, zb) in enumerate(DROPS):
    rt, rb = 0.2, 0.09
    v = [(x + rt * math.cos(a), y + rt * math.sin(a), zt) for a in [math.pi * k / 3 for k in range(6)]] + \
        [(x + rb * math.cos(a), y + rb * math.sin(a), zb + 0.02) for a in [math.pi * k / 3 for k in range(6)]]
    f = [(k, (k + 1) % 6, 6 + (k + 1) % 6, 6 + k) for k in range(6)] + \
        [(0, 2, 1), (0, 3, 2), (0, 4, 3), (0, 5, 4), (6, 7, 8), (6, 8, 9), (6, 9, 10), (6, 10, 11)]
    o = unique(f"SM_Banyan_AerialRoot_{i + 1:02d}", (v, f, [0] * len(f)), [BARK], coll=C_TREE, recalc=True)
    tree_tris += fc.tri_count(o)
    drop_col.append((v, f))
# canopy: 10 faceted clusters under the glass roof (z 10.5 - 14.8)
crng = random.Random(8)
CAN = [(0.3, -1.0, 13.6), (4.2, 1.2, 12.6), (-4.0, 0.4, 12.9), (1.5, 4.6, 12.3), (-2.6, 4.8, 13.2), (5.5, -3.6, 12.0),
       (-5.4, -3.8, 12.4), (0.8, -5.6, 11.6), (-7.4, 1.6, 11.2), (6.8, 3.8, 11.0)]
for i, c in enumerate(CAN):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
    s = (crng.uniform(2.6, 3.3), crng.uniform(2.4, 3.1), crng.uniform(1.25, 1.6))
    R = Euler((0, 0, crng.uniform(0, 3))).to_matrix()
    vs = [tuple(R @ Vector((v.co.x * s[0] * crng.uniform(0.9, 1.1), v.co.y * s[1] * crng.uniform(0.9, 1.1),
                            v.co.z * s[2])) + Vector(c)) for v in bm.verts]
    fs = [tuple(v.index for v in f.verts) for f in bm.faces]
    bm.free()
    o = unique(f"SM_Banyan_Canopy_{i + 1:02d}", (vs, fs, [0] * len(fs)), [MOSS], coll=C_TREE, recalc=True)
    tree_tris += fc.tri_count(o)
log["banyan"] = dict(tris=tree_tris, budget=20000, roots=len(ROOTS) + 2, aerial_drops=len(DROPS), canopy=len(CAN),
                     trunk_base_diameter=2 * tr[1], trunk_top_z=tz[-1], balcony_wraps=["back L2 x=-3", "left L2 y=2",
                                                                                         "back L3 x=-6"])
col("COL_Banyan_Trunk", fc.xform(fc.cylinder_data(1.5, 14.0, 10), offset=(PL_X, PL_Y, 0.0)))
col("COL_Banyan_Roots", fc.merge(*seg_hulls))
col("COL_Banyan_AerialRoots", fc.merge(*drop_col))

# ================================================================== 3. habitation (instanced clusters)
def shelter_frame():
    p = []
    for x, y, h in ((-1.15, -1.15, 2.3), (1.15, -1.15, 2.3), (-1.15, 1.15, 2.05), (1.15, 1.15, 2.05)):
        pr = fc.prism([(x + 0.07 * math.cos(a), y + 0.07 * math.sin(a)) for a in [math.pi * k / 3 for k in range(6)]],
                      0.0, h)
        p.append((pr[0], pr[1], [0] * len(pr[1])))
    p += [(*BM(-1.25, 1.25, -1.2, -1.1, 2.22, 2.32), 0), (*BM(-1.25, 1.25, 1.1, 1.2, 1.97, 2.07), 0),
          (*fc.sheared_box(-1.2, -1.1, -1.15, 2.22, 1.15, 1.97, 0.08), 0),
          (*fc.sheared_box(1.1, 1.2, -1.15, 2.22, 1.15, 1.97, 0.08), 0)]
    return fc.mparts(*p)


def cloth_roof():
    zt = lambda x, y: 2.34 - 0.25 * (y + 1.3) / 2.6 - 0.12 * (1 - (x / 1.35) ** 2)
    return fc.slab_grid([-1.35, -0.7, 0.0, 0.7, 1.35], [-1.3, -0.4, 0.4, 1.3], lambda x, y: zt(x, y) - 0.03, zt)


def cloth_back():
    """Back wall cloth + one side drape (olive canvas)."""
    return fc.mparts((*BM(-1.2, 1.2, 1.18, 1.22, 0.05, 2.0), 0), (*BM(-1.2, -1.16, -1.1, 1.18, 0.4, 2.0), 0))


def sleeping_mat():
    return fc.mparts((*BM(-0.4, 0.4, -1.0, 1.0, 0.0, 0.07, skip=("bottom",)), 0),
                     (*BM(-0.3, 0.3, 0.55, 0.9, 0.07, 0.19, skip=("bottom",)), 1))


def water_barrel():
    body = fc.lathe([(0, 0), (0.3, 0), (0.3, 0.9), (0, 0.9)], 8, angle_offset=math.pi / 8)
    rings = [fc.lathe([(0.305, z), (0.315, z), (0.315, z + 0.05), (0.305, z + 0.05)], 8, closed=True,
                      angle_offset=math.pi / 8) for z in (0.15, 0.7)]
    face = 0.3 * math.cos(math.pi / 8)
    drop = [(0, 0.62), (-0.08, 0.5), (-0.1, 0.42), (-0.07, 0.34), (0, 0.31), (0.07, 0.34), (0.1, 0.42), (0.08, 0.5)]
    fan = [(0, i, i + 1) for i in range(1, len(drop) - 1)]
    icon = fc.extrude2d(drop, fan, [2] * len(fan), 0.012, -face - 0.012, back=False)
    return fc.mparts((*body, [0] * len(body[1])), *[(*r, [1] * len(r[1])) for r in rings], icon)


def supply_crate():
    return fc.mparts((*BM(-0.45, 0.45, -0.3, 0.3, 0.0, 0.45, skip=("top",)), 0),
                     (*BM(-0.47, 0.47, -0.32, 0.32, 0.45, 0.55), 1),
                     (*BM(-0.3, -0.2, -0.335, -0.32, 0.35, 0.5), 1), (*BM(0.2, 0.3, -0.335, -0.32, 0.35, 0.5), 1))


def workstation():
    return fc.mparts((*BM(-0.8, 0.8, -0.35, 0.35, 0.72, 0.78), 0),
                     (*BM(-0.75, -0.65, -0.3, 0.3, 0.0, 0.72), 0), (*BM(0.65, 0.75, -0.3, 0.3, 0.0, 0.72), 0),
                     (*BM(-0.35, 0.25, 0.05, 0.15, 0.85, 1.25), 1), (*BM(-0.3, 0.2, 0.04, 0.05, 0.89, 1.21), 2),
                     (*BM(-0.08, 0.02, 0.07, 0.13, 0.78, 0.85), 1),
                     (*BM(0.5, 0.62, 0.1, 0.22, 0.78, 0.81), 1), (*BM(0.545, 0.575, 0.145, 0.175, 0.81, 1.2), 1),
                     (*BM(0.48, 0.64, 0.08, 0.24, 1.2, 1.28), 3))


def rail_drape(L=1.2):
    return fc.mparts((*BM(-L / 2, L / 2, -0.16, 0.16, 1.1, 1.13), 0),
                     (*BM(-L / 2, L / 2, -0.19, -0.16, 0.35, 1.13), 0),
                     (*BM(-L / 2 + 0.1, L / 2 - 0.1, 0.16, 0.19, 0.75, 1.13), 0))


def door_curtain():
    """Two cloth panels hung in a 2 x 3 m doorway (left panel drawn aside) + rod."""
    return fc.mparts((*BM(-0.98, -0.12, 0.06, 0.09, 0.05, 2.95), 0),
                     (*BM(0.3, 0.98, 0.06, 0.09, 0.05, 2.95), 0),
                     (*BM(-1.0, 1.0, 0.04, 0.11, 2.95, 3.0), 1))


def light_spill():
    """Warm emissive floor spill in front of an inhabited doorway (unlit-friendly 'light on' cue)."""
    v = [(-0.95, 0.0, 0.012), (0.95, 0.0, 0.012), (1.5, -1.4, 0.012), (-1.5, -1.4, 0.012)]
    return v, [(0, 3, 2, 1)], [0]


me_frame = module("MOD_V_ShelterFrame", shelter_frame(), [BARK])
me_roofA = module("SM_ClothPanel_A", cloth_roof(), [CLO])
me_roofB = module("SM_ClothPanel_B", cloth_roof(), [VCON])
me_back = module("SM_ClothPanel_C", cloth_back(), [VCON])
me_mat = module("MOD_V_SleepingMat", sleeping_mat(), [CLO, SIL])
me_barrel = module("MOD_V_WaterBarrel", water_barrel(), [CLO, CHR, SIL])
me_crate = module("MOD_V_SupplyCrate", supply_crate(), [VCON, CHR])
me_ws = module("MOD_V_Workstation", workstation(), [BARK, CHR, CYN, LANT])
me_lan = module("MOD_V_Lantern", vk.lantern(), [CHR, LANT])
me_drape = {k: module(f"MOD_V_RailDrape_{k}", rail_drape(), [m]) for k, m in (("A", CLO), ("B", VCON))}
me_curt = module("MOD_V_DoorCurtain", door_curtain(), [CLO, BARK])
me_spill = module("MOD_V_LightSpill", light_spill(), [LANT])
hab_hulls = []


def cluster(name, loc, rz, items, coll=C_HAB):
    e = fc.empty(name, loc, coll, 0.6, "CUBE")
    e.rotation_euler.z = math.radians(rz)
    objs = []
    for n, me, (x, y, z), r in items:
        o = place(f"{name}_{n}", me, (x, y, z), r, coll)
        o.parent = e
        objs.append(o)
    return objs


CAMP = [("Frame", me_frame, (0, 0, 0), 0), ("Roof", me_roofA, (0, 0, 0), 0), ("Back", me_back, (0, 0, 0), 0),
        ("MatA", me_mat, (-0.45, 0.05, 0), 0), ("MatB", me_mat, (0.45, 0.05, 0), 0),
        ("Barrel", me_barrel, (1.5, 0.9, 0), 0), ("CrateA", me_crate, (-1.55, 0.6, 0), 90),
        ("CrateB", me_crate, (-1.55, 0.6, 0.55), 80), ("Lantern", me_lan, (1.45, -0.9, 0), 0)]
camp_objs = cluster("GRP_V3_Camp_W", (-5.8, -8.6, 0.0), 90, CAMP)
# east camp sits between the front wall and the gathering->stair route (y -11 .. -7.6): explicit compact layout
CAMP_E = [("Frame", me_frame, (0, 0, 0), 0), ("Roof", me_roofB, (0, 0, 0), 0), ("Back", me_back, (0, 0, 0), 0),
          ("MatA", me_mat, (-0.45, 0.05, 0), 0), ("MatB", me_mat, (0.45, 0.05, 0), 0),
          ("Barrel", me_barrel, (0.85, 0.95, 0), 0), ("CrateA", me_crate, (-1.55, 0.6, 0), 90),
          ("CrateB", me_crate, (-1.55, 0.6, 0.55), 80), ("Lantern", me_lan, (1.0, -0.9, 0), 0)]
camp_objs += cluster("GRP_V3_Camp_E", (6.0, -9.7, 0.0), -90, CAMP_E)
ws = cluster("GRP_V3_Workstation", (-8.8, -10.35, 0.0), 180,
             [("Desk", me_ws, (0, 0, 0), 0), ("Seat", me_crate, (0.0, -0.75, 0), 0), ("Lantern", me_lan, (-0.6, 0.0, 0.78), 0)])
supplies = []
for i, (loc, rz) in enumerate((((4.5, 10.0, 0.0), 0), ((-14.3, -6.0, 4.0), 90), ((-14.3, 0.0, 8.0), 90))):
    supplies += cluster(f"GRP_V3_Supplies_{i + 1}", loc, rz,
                        [("BarrelA", me_barrel, (-0.5, 0.0, 0), 0), ("BarrelB", me_barrel, (0.15, 0.1, 0), 20),
                         ("Crate", me_crate, (0.95, 0.0, 0), 0)])
lanterns = []
for i, loc in enumerate([(-14.6, -9.0, 4.0), (-14.6, -4.0, 4.0), (-14.6, 6.0, 4.0), (-10.0, 8.85, 4.0), (-6.0, 8.85, 4.0),
                         (4.0, 8.85, 4.0), (-14.6, -6.0, 8.0), (-14.6, 4.0, 8.0), (-10.0, 8.85, 8.0), (-2.0, 8.85, 8.0),
                         (4.0, 8.85, 8.0), (-3.2, -5.2, 0.0), (3.2, -5.2, 0.0), (-3.0, -10.6, 0.0), (3.0, -10.6, 0.0)]):
    lanterns.append(place(f"SM_V3_Lantern_{i:02d}", me_lan, loc, 0, C_HAB))
DRAPES = [((-12.56, -6.0, 4.0), 90, "A"), ((-7.0, 8.56, 4.0), 180, "B"), ((-12.56, 4.0, 8.0), 90, "B"),
          ((2.0, 8.56, 8.0), 180, "A"), ((12.56, -8.0, 4.0), -90, "A"), ((-12.56, -2.0, 8.0), 90, "A")]
for i, (loc, rz, k) in enumerate(DRAPES):
    place(f"SM_V3_RailDrape_{i:02d}", me_drape[k], loc, rz, C_HAB)
for lv, (dx, dz) in INHABITED.items():
    place(f"SM_V3_DoorCurtain_L{lv}", me_curt, (dx, HY, dz), 0, C_HAB)
    place(f"SM_V3_LightSpill_L{lv}", me_spill, (dx, HY, dz), 0, C_HAB)
    place(f"SM_V3_AptLantern_L{lv}", me_lan, (dx - 1.6, HY + 3.4, dz), 0, C_HAB)
    o = OB.get(f"SM_V3_AptVestibule_L{lv}")
log["habitation"] = "2 shelter camps (frame + cloth panels + mats + barrel + crates), workstation, 3 supply groups, " \
                    f"{len(lanterns)} lanterns, {len(DRAPES)} rail drapes, 3 curtained + lit inhabited doors"

bpy.context.view_layer.update()
hull_src = [o for o in camp_objs + ws + supplies if o.data.name in ("MOD_V_ShelterFrame", "MOD_V_WaterBarrel",
                                                                    "MOD_V_SupplyCrate", "MOD_V_Workstation")]
col("COL_V3_Habitation", fc.merge(*vk.hull_parts(hull_src)))

# ================================================================== 4. landmarks (N3's untouched) + gathering
fc.empty("LM_Gathering", (GATHER_C[0], GATHER_C[1], 0.0), C_LM, 0.8, "ARROWS").hide_render = True
for o in C_COL.objects:
    o.display_type = "WIRE"
baked = fc.bake_unique_rotations(list(C_EXP.all_objects) + list(C_COL.objects))

# ================================================================== 5. clearance checks: 6 m gathering circle + 2 m door routes
bpy.context.view_layer.update()
obst = [o for o in C_COL.objects if o.name.startswith(("COL_Banyan", "COL_V3_Habitation", "COL_V3_Benches",
                                                       "COL_V3_Planter"))]
verts, polys = [], []
for o in obst:
    off = len(verts)
    verts += [o.matrix_world @ v.co for v in o.data.vertices]
    polys += [[off + i for i in p.vertices] for p in o.data.polygons]
obvh = BVHTree.FromPolygons(verts, polys)


def blocked(x, y, z):
    hit, _, _, d = obvh.ray_cast(Vector((x, y, z + 0.05)), Vector((0, 0, 1)), 1.8)
    if hit is not None:
        return True
    hit, n, _, d = obvh.ray_cast(Vector((x, y, z + 1.9)), Vector((0, 0, -1)), 1.85)
    return hit is not None


clear = {}
pts = [(GATHER_C[0] + i * 0.25, GATHER_C[1] + j * 0.25) for i in range(-12, 13) for j in range(-12, 13)
       if (i * 0.25) ** 2 + (j * 0.25) ** 2 <= GATHER_R ** 2]
clear["gathering_6m"] = sum(blocked(x, y, 0.0) for x, y in pts)
for k, (x0, x1, y0, y1, z) in ROUTES.items():
    n = 0
    xs = [x0 + 0.125 + 0.25 * i for i in range(int((x1 - x0) / 0.25))]
    ys = [y0 + 0.125 + 0.25 * j for j in range(int((y1 - y0) / 0.25))]
    for x in xs:
        for y in ys:
            n += blocked(x, y, z)
    clear[k] = n
log["clearance_blocked_samples"] = clear

# ================================================================== 6. presentation: warm lanterns, dappled light, dim ambient
sc = bpy.context.scene
sun = OB["LGT_Key_6500K"]
sun.name = sun.data.name = "LGT_Key_4000K"
try:
    sun.data.use_temperature, sun.data.temperature = True, 4000
except Exception:
    sun.data.color = (1.0, 0.82, 0.62)
sun.data.energy = 4.2
sun.rotation_euler = (math.radians(24), 0, math.radians(-30))
for i, (lv, (dx, dz)) in enumerate(INHABITED.items()):
    ld = bpy.data.lights.new(f"LGT_Spill_L{lv}", "POINT")
    ld.energy = 180
    try:
        ld.use_temperature, ld.temperature = True, 3000
    except Exception:
        ld.color = (1.0, 0.72, 0.45)
    lo = bpy.data.objects.new(f"LGT_Spill_L{lv}", ld)
    lo.location = (dx, HY - 0.6, dz + 1.6)
    C_PRES.objects.link(lo)
for i, p in enumerate([(0.0, -8.0, 2.0), (-5.8, -8.6, 1.8), (6.0, -9.3, 1.8)]):
    ld = bpy.data.lights.new(f"LGT_Lantern_{i}", "POINT")
    ld.energy = 120
    ld.color = (1.0, 0.72, 0.45)
    lo = bpy.data.objects.new(f"LGT_Lantern_{i}", ld)
    lo.location = p
    C_PRES.objects.link(lo)
bg = sc.world.node_tree.nodes.get("Background")
bg.inputs[0].default_value = fc.hex_lin("#B9AE97")
bg.inputs[1].default_value = 0.3
OB["REF_Player"].hide_render = True
C_MOD.hide_render = True
renders = {}
C_ROOF.hide_render = True
top_hide = [o for o in C_TREE.objects if o.name.startswith("SM_Banyan_Canopy")] + [OB["SM_V3_TopTrim_12m"]]
for o in top_hide:
    o.hide_render = True
sc.camera = OB["CAM_TopDown"]
renders["topdown"] = fc.render(os.path.join(fc.RENDER_DIR, "V3_detail_topdown.png"), engine="BLENDER_EEVEE")
C_ROOF.hide_render = False
for o in top_hide:
    o.hide_render = False
sc.camera = OB["CAM_EyeHeight"]
renders["eye"] = fc.render(os.path.join(fc.RENDER_DIR, "V3_detail_eyeheight.png"), engine="BLENDER_EEVEE")
sc.camera = OB["CAM_Hero34"]
renders["hero"] = fc.render(os.path.join(fc.RENDER_DIR, "V3_detail_hero34.png"), engine="BLENDER_EEVEE")
cam_g = bpy.data.objects.new("CAM_Gathering", bpy.data.cameras.new("CAM_Gathering"))
cam_g.data.lens = 20
cam_g.location = (2.5, -10.6, 1.7)
C_PRES.objects.link(cam_g)
fc.look_at(cam_g, (-2.0, 2.0, 4.5))
sc.camera = cam_g
renders["gathering"] = fc.render(os.path.join(fc.RENDER_DIR, "V3_detail_gathering.png"), engine="BLENDER_EEVEE")
sun.hide_render = True
for o in C_PRES.objects:
    if o.type == "LIGHT":
        o.hide_render = True
bg.inputs[1].default_value = 1.0
sc.camera = OB["CAM_EyeHeight"]
renders["eye_flat_ambient"] = fc.render(os.path.join(fc.RENDER_DIR, "V3_detail_eyeheight_flat.png"), engine="BLENDER_EEVEE")
for o in C_PRES.objects:
    if o.type == "LIGHT":
        o.hide_render = False
bg.inputs[1].default_value = 0.3
sc.camera = OB["CAM_Hero34"]

# ================================================================== 7. Block Z + export
blend = os.path.join(fc.SOURCE_DIR, f"Fractured_{ID}_{NAME}.blend")
glb = os.path.join(fc.EXPORT_DIR, f"Fractured_{ID}_{NAME}.glb")
report = qa.run(ID, C_EXP, C_COL, C_FX, budget=150000, landmark_coll=C_LM, walk_bounds=(-HX, HX, -HY, HY),
                walkable_prefixes=("COL_V3_Floor", "COL_V3_Balcony", "COL_V3_Stair_"),
                pair_with=os.path.join(fc.RENDER_DIR, "N3_landmarks.json"))
report["v3_changes"] = log
report["rotations_baked"] = baked
report["renders"] = renders
report["blend"] = blend
report["pass"] = report["pass"] and all(v == 0 for v in clear.values()) and tree_tris <= 20000
fc.save(blend)
report["export"] = qa.export_and_verify(C_EXP, C_COL, glb)
report["glb"] = glb
with open(os.path.join(fc.RENDER_DIR, "V3_QA_report.json"), "w") as fh:
    json.dump(report, fh, indent=2)
print("V3 DONE pass=", report["pass"], json.dumps(log))
