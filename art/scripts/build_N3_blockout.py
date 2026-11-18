"""N3 Nova Residential Atrium — BLOCKOUT (Block 0 workflow step 2).
Interior X -15..15, Y -11..11 (entrances on the -Y front wall), ground z=0, balcony levels z=4 and z=8,
non-walkable trim ring at z=12, glass roof at z=16. Balconies (2.5 m) on left / back / right.
Run: blender -b --factory-startup -P art/scripts/build_N3_blockout.py
"""
import os
import sys
import math
import json
import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(__file__))
import fractured_common as fc
import nova_kit as nk

ID = "N3"
sc = fc.reset_scene()
M = fc.append_shared_materials()
SIL, GLS, CYN, CHR, CLO, MOSS, BARK = (M[k] for k in ("M_NovaSilver", "M_NovaGlass", "M_CyanEmissive", "M_Charcoal",
                                                    "M_Cloth", "M_Moss", "M_Bark"))
C_EXP = fc.collection(f"{ID}_Export")
C_ROOF = fc.collection(f"{ID}_Roof", C_EXP)
C_APT = fc.collection(f"{ID}_Apartments", C_EXP)
C_COL = fc.collection(f"{ID}_Collision")
C_FX = fc.collection(f"{ID}_FX")
C_PRES = fc.collection(f"{ID}_Presentation")
C_REF = fc.collection("_Reference")
C_LM = fc.collection(f"{ID}_Landmarks")
C_MOD = fc.collection(f"{ID}_ModuleSources")
BM = fc.box_minmax

# ------------------------------------------------------------------ dimensions
HX, HY, WT = 15.0, 11.0, 0.3
VOID_H = 16.0
LEVELS = (0.0, 4.0, 8.0)
TRIM_Z = 12.0
SLAB = 0.4
BD = 2.5                                   # balcony depth
IX0, IX1, IY1 = -HX + BD, HX - BD, HY - BD  # inner balcony edges: x=-12.5 / 12.5, y=8.5
DOOR_W, DOOR_H = 2.0, 3.0
DOOR_XS = [-12.0 + 4 * i for i in range(7)]
APT = {0: -8.0, 1: 0.0, 2: 8.0}              # level index -> door x with an interior behind it
APT_W, APT_D, APT_H = 6.0, 4.0, 3.0
VEST_D = 1.0
PL_X, PL_Y, PL_W, PL_D, PL_H = 0.0, -1.5, 8.0, 6.0, 0.8
ST_X0, ST_X1 = 9.5, 12.5                   # main stair, 3 m wide, along the right side
ST_RISERS, ST_TREAD = 22, 0.30
ST_RISE = 4.0 / ST_RISERS
ST_RUN = (ST_RISERS - 1) * ST_TREAD        # 6.3
F1_TOP_Y = 0.0                             # flight 1: y -6.3 -> 0 (z 0 -> 4)
LAND_Y0, LAND_Y1 = 0.0, IY1 - ST_RUN       # landing y 0 -> 2.2 at z=4
F2_TOP_Y = IY1                             # flight 2: y 2.2 -> 8.5 (z 4 -> 8), arrives on the level-3 back balcony
MAIN_ENT = (-2.0, 2.0, 0.0, 4.0)           # x0, x1, z0, z1 on the front wall
SIDE_ENT = (-2.0, 0.0, 0.0, 3.0)           # y0, y1, z0, z1 on the left wall (hole of the panel centred y=-1)
ROOF_GLASS = (-12.0, 12.0, -10.0, 6.0)


def mk(name, data, mats, coll=None, loc=(0, 0, 0), rz=0.0, face_mats=None, recalc=True):
    return fc.obj(name, fc.build_mesh(name, data, mats, face_mats=face_mats, recalc=recalc), coll or C_EXP, loc, rz)


def mkm(name, vfm, mats, coll=None, loc=(0, 0, 0), rz=0.0, recalc=False):
    v, f, m = vfm
    return mk(name, (v, f), mats, coll, loc, rz, face_mats=m, recalc=recalc)


def module(name, vfm, mats, recalc=False):
    v, f, m = vfm
    me = fc.build_mesh(name, (v, f), mats, face_mats=m, recalc=recalc)
    fc.obj(name, me, C_MOD)
    return me


def col(name, data):
    o = fc.obj(f"{name}-colonly", fc.build_mesh(name, data, weld=False), C_COL)
    o.display_type = "WIRE"
    return o


# ================================================================== floor + walls
mk("SM_N3_Floor", BM(-HX, HX, -HY, HY, -0.2, 0.0), [SIL])
col("COL_N3_Floor", BM(-HX - WT, HX + WT, -HY - WT, HY + WT, -0.2, 0.0))
# back wall: per level, panels centred on the door grid with apartment door holes; 1 m fillers at the ends
wall_door = module("MOD_N_Wall_4x4_AptDoor", nk.wall_panel(4, hole=(-1.0, 1.0, 0.0, 3.0), band=False), [SIL, CHR, CYN])
wall_plain = module("MOD_N_Wall_4x4", nk.wall_panel(4, band=False), [SIL, CHR, CYN])
wall_1 = module("MOD_N_Wall_1x4", nk.wall_panel(1, band=False), [SIL, CHR, CYN])
wall_2 = module("MOD_N_Wall_2x4", nk.wall_panel(2, band=False), [SIL, CHR, CYN])
for r, z in enumerate((0.0, 4.0, 8.0, 12.0)):
    for i, x in enumerate(DOOR_XS):
        fc.obj(f"SM_N3_Wall_N_{r}{i}", wall_door if r < 3 else wall_plain, C_EXP, (x, HY, z), 0)
    for x in (-14.5, 14.5):
        fc.obj(f"SM_N3_Wall_N_{r}f{int(x)}", wall_1, C_EXP, (x, HY, z), 0)
# side walls (left = -X, right = +X): panels centred y -9,-5,-1,3,7 + 2 m filler (9..11); side entrance on the left
SIDE_YS = [(-9.0, 4), (-5.0, 4), (-1.0, 4), (3.0, 4), (7.0, 4), (10.0, 2)]
wall_sidedoor = module("MOD_N_Wall_4x4_Door2x3", nk.wall_panel(4, hole=(-1.0, 1.0, 0.0, 3.0), band=False), [SIL, CHR, CYN])
for side, x, rz in (("W", -HX, 90), ("E", HX, -90)):
    for r, z in enumerate((0.0, 4.0, 8.0, 12.0)):
        for i, (y, w) in enumerate(SIDE_YS):
            me = wall_2 if w == 2 else (wall_sidedoor if (side == "W" and r == 0 and y == -1.0) else wall_plain)
            fc.obj(f"SM_N3_Wall_{side}_{r}{i}", me, C_EXP, (x, y, z), rz)
# front wall: panels centred x -13..13 (2 m end fillers? 30 = 7x4 + 2) with the main entrance on the centre panel
FRONT_XS = [(-12.0, 4), (-8.0, 4), (-4.0, 4), (0.0, 4), (4.0, 4), (8.0, 4), (12.0, 4), (-14.5, 1), (14.5, 1)]
wall_main = module("MOD_N_Wall_4x4_Door4x4", nk.wall_panel(4, hole=(-2.0, 2.0, 0.0, 4.0), band=False), [SIL, CHR, CYN])
for r, z in enumerate((0.0, 4.0, 8.0, 12.0)):
    for i, (x, w) in enumerate(FRONT_XS):
        me = wall_1 if w == 1 else (None if (r == 0 and x == 0.0) else wall_plain)
        if me is None:
            continue                                  # 4 x 4 main entrance (no wall panel in that bay)
        fc.obj(f"SM_N3_Wall_S_{r}{i}", me, C_EXP, (x, -HY, z), 180)
col("COL_N3_Walls", fc.merge(
    BM(-HX - WT, HX + WT, HY, HY + WT, 0, VOID_H),
    BM(-HX - WT, MAIN_ENT[0], -HY - WT, -HY, 0, VOID_H), BM(MAIN_ENT[1], HX + WT, -HY - WT, -HY, 0, VOID_H),
    BM(MAIN_ENT[0], MAIN_ENT[1], -HY - WT, -HY, MAIN_ENT[3], VOID_H),
    BM(-HX - WT, -HX, -HY, SIDE_ENT[0], 0, VOID_H), BM(-HX - WT, -HX, SIDE_ENT[1], HY, 0, VOID_H),
    BM(-HX - WT, -HX, SIDE_ENT[0], SIDE_ENT[1], SIDE_ENT[3], VOID_H),
    BM(HX, HX + WT, -HY, HY, 0, VOID_H)))
# back-wall collision with door gaps per walkable level (apartment / vestibule openings are enterable)
bw = []
for z in LEVELS:
    xs = [-HX] + [v for x in DOOR_XS for v in (x - DOOR_W / 2, x + DOOR_W / 2)] + [HX]
    for x0, x1 in zip(xs[0::2], xs[1::2]):
        bw.append(BM(x0, x1, HY, HY + WT, z, z + 4.0))
    for x in DOOR_XS:
        bw.append(BM(x - DOOR_W / 2, x + DOOR_W / 2, HY, HY + WT, z + DOOR_H, z + 4.0))
col("COL_N3_BackWall", fc.merge(*bw))

# ================================================================== balconies (levels 2, 3) + non-walkable trim ring at 12 m
def ring_slab(z, t=SLAB):
    return fc.merge(BM(-HX, IX0, -HY, IY1, z - t, z), BM(-HX, HX, IY1, HY, z - t, z), BM(IX1, HX, -HY, IY1, z - t, z))


for k, z in enumerate((4.0, 8.0)):
    mk(f"SM_N3_Balcony_L{k + 2}", ring_slab(z), [SIL])
    col(f"COL_N3_Balcony_L{k + 2}", ring_slab(z))
mk("SM_N3_TopTrim_12m", ring_slab(TRIM_Z), [SIL])

# glass railings along the inner balcony edges (gaps: level-2 landing joint, level-3 stair arrival)
def rail_runs(level):
    runs = [("L", (-HY, IY1)), ("R", (-HY, IY1)), ("B", (IX0, IX1))]
    out = []
    for side, (a, b) in runs:
        gaps = []
        if side == "R" and level == 2:
            gaps.append((LAND_Y0, LAND_Y1))
        if side == "B" and level == 3:
            gaps.append((ST_X0, ST_X1))
        segs, s = [], a
        for g0, g1 in sorted(gaps):
            segs.append((s, g0))
            s = g1
        segs.append((s, b))
        out += [(side, s0, s1) for s0, s1 in segs if s1 - s0 > 1e-3]
    return out


rails_col = []
for level, z in ((2, 4.0), (3, 8.0)):
    for k, (side, s0, s1) in enumerate(rail_runs(level)):
        L = s1 - s0
        if side == "B":
            data = fc.xform(nk.railing(L), offset=((s0 + s1) / 2, IY1 + 0.06, z))
            box = BM(s0, s1, IY1, IY1 + 0.12, z, z + 1.1)
        else:
            x = IX0 - 0.06 if side == "L" else IX1 + 0.06
            data = fc.xform(nk.railing(L), rot_z=90, offset=(x, (s0 + s1) / 2, z))
            box = BM(x - 0.06, x + 0.06, s0, s1, z, z + 1.1)
        mkm(f"SM_N3_Rail_L{level}_{side}{k}", data, [GLS, SIL])
        rails_col.append(box)

# ================================================================== main stair (flight 1 -> landing -> flight 2) + rails
me_stair = module("MOD_N_Stair_3m_4rise", nk.stair(3.0, ST_RISERS, ST_RISE, ST_TREAD), [SIL, CHR])
SX = (ST_X0 + ST_X1) / 2
fc.obj("SM_N3_Stair_F1", me_stair, C_EXP, (SX, F1_TOP_Y, 0.0))
fc.obj("SM_N3_Stair_F2", me_stair, C_EXP, (SX, F2_TOP_Y, 4.0))
mk("SM_N3_Stair_Landing", BM(ST_X0, ST_X1, LAND_Y0, LAND_Y1, 4.0 - SLAB, 4.0), [SIL])
ramp = nk.stair_ramp(3.0, ST_RISERS, ST_RISE, ST_TREAD)
col("COL_N3_Stair_F1", fc.xform(ramp, offset=(SX, F1_TOP_Y, 0.0)))
f2 = fc.xform(ramp, offset=(SX, F2_TOP_Y, 4.0))
col("COL_N3_Stair_F2", f2)
col("COL_N3_Stair_Landing", BM(ST_X0, ST_X1, LAND_Y0, LAND_Y1, 4.0 - SLAB, 4.0))
for side, x in (("W", ST_X0 + 0.06), ("E", ST_X1 - 0.06)):
    for fl, (y_top, z0) in (("F1", (F1_TOP_Y, 0.0)), ("F2", (F2_TOP_Y, 4.0))):
        r = nk.sloped_rail(x, y_top - ST_RUN - ST_TREAD, z0, y_top, z0 + 4.0)
        mkm(f"SM_N3_StairRail_{fl}_{side}", r, [GLS, SIL])
        rails_col.append(fc.sheared_box(x - 0.06, x + 0.06, y_top - ST_RUN - ST_TREAD, z0, y_top, z0 + 4.0, 1.1))
mkm("SM_N3_LandingRail_W", fc.xform(nk.railing(LAND_Y1 - LAND_Y0), rot_z=90,
                                    offset=(ST_X0 + 0.06, (LAND_Y0 + LAND_Y1) / 2, 4.0)), [GLS, SIL])
rails_col.append(BM(ST_X0, ST_X0 + 0.12, LAND_Y0, LAND_Y1, 4.0, 5.1))
col("COL_N3_Rails", fc.merge(*rails_col))

# ================================================================== apartment doors, vestibules, 3 interiors
door_frame = fc.mparts((*BM(-1.2, -1.0, -0.15, 0.0, 0.0, 3.2), 0), (*BM(1.0, 1.2, -0.15, 0.0, 0.0, 3.2), 0),
                       (*BM(-1.0, 1.0, -0.15, 0.0, 3.0, 3.2, skip=("front",)), 0),
                       (*BM(-1.2, 1.2, -0.17, -0.15, 3.05, 3.15), 1))          # cyan lintel strip
me_door = module("MOD_N_AptDoor", door_frame, [CHR, CYN])
vest = fc.mparts(*[(v, [tuple(reversed(q)) for q in f], 0) for v, f in
                   [BM(-1.0, 1.0, HY + WT, HY + WT + VEST_D, 0.0, DOOR_H, skip=("front",))]])
me_vest = module("MOD_N_AptVestibule", fc.xform(vest, offset=(0, -HY, 0)), [CHR])


def apt_interior():
    """6 x 4 m interior, 3 m ceiling, door opening at local y=0 centre; living area + 1.5 m utility alcove (+X end)."""
    W, D, Hh = APT_W / 2, APT_D, APT_H
    shell = BM(-W, W, 0.0, D, 0.0, Hh, skip=("front",))
    shell = (shell[0], [tuple(reversed(q)) for q in shell[1]])
    return fc.mparts((*shell, 0),
                     (*BM(W - 1.5, W - 1.4, 0.0, D - 1.2, 0.0, 2.2), 1),              # alcove partition (half wall)
                     (*BM(W - 1.4, W, D - 0.6, D, 0.0, 0.9), 1),                      # counter
                     (*BM(W - 0.4, W, 0.5, D - 0.7, 0.0, 2.0), 1),                    # shelving block
                     (*BM(-W + 0.3, -W + 2.3, D - 0.9, D - 0.1, 0.0, 0.8), 2),         # sofa block
                     (*BM(-W + 0.8, -W + 1.8, D - 2.2, D - 1.4, 0.0, 0.45), 1),        # table
                     (*BM(-W + 0.6, -W + 2.2, D - 0.05, D - 0.01, 1.2, 2.1), 3))       # wall screen


me_apt = module("MOD_N_AptInterior", apt_interior(), [SIL, CHR, CLO, CYN])
landmarks = {}
for lv, z in enumerate(LEVELS):
    for i, x in enumerate(DOOR_XS):
        fc.obj(f"SM_N3_AptDoor_L{lv + 1}_{i}", me_door, C_APT, (x, HY, z))
        if APT.get(lv) == x:
            fc.obj(f"SM_N3_AptInterior_L{lv + 1}", me_apt, C_APT, (x, HY + WT, z))
            landmarks[f"LM_AptDoor_L{lv + 1}"] = (x, HY, z)
        else:
            fc.obj(f"SM_N3_AptVestibule_L{lv + 1}_{i}", me_vest, C_APT, (x, HY, z))
apt_col = []
for lv, z in enumerate(LEVELS):
    for x in DOOR_XS:
        if APT.get(lv) == x:
            x0, x1, y0, y1 = x - APT_W / 2, x + APT_W / 2, HY + WT, HY + WT + APT_D
            apt_col += [BM(x0 - WT, x1 + WT, y0, y1 + WT, z - 0.2, z), BM(x0 - WT, x0, y0, y1, z, z + APT_H),
                        BM(x1, x1 + WT, y0, y1, z, z + APT_H), BM(x0, x1, y1, y1 + WT, z, z + APT_H),
                        BM(x0 - WT, x1 + WT, y0, y1 + WT, z + APT_H, z + APT_H + 0.2)]
        else:
            apt_col.append(BM(x - 1.0, x + 1.0, HY + WT + VEST_D, HY + WT + VEST_D + 0.2, z, z + DOOR_H))
            apt_col.append(BM(x - 1.0, x + 1.0, HY + WT, HY + WT + VEST_D, z - 0.2, z))
col("COL_N3_Apartments", fc.merge(*apt_col))

# ================================================================== entrances
me_df4 = module("MOD_N_DoorFrame_4x4", nk.door_frame(4.0, 4.0, 0.5, 0.6, 0.35), [CHR, CYN])
me_df2 = module("MOD_N_DoorFrame_2x3", nk.door_frame(2.0, 3.0, 0.3, 0.3, 0.25), [CHR, CYN])
fc.obj("SM_N3_DoorFrame_Main", me_df4, C_EXP, (0.0, -HY, 0.0), 180)
fc.obj("SM_N3_DoorFrame_Side", me_df2, C_EXP, (-HX, -1.0, 0.0), 90)
for n, (v, f) in (("Main", BM(MAIN_ENT[0], MAIN_ENT[1], -HY - WT - 4.0, -HY - WT, 0.0, 4.0, skip=("back",))),
                  ("Side", BM(-HX - WT - 4.0, -HX - WT, SIDE_ENT[0], SIDE_ENT[1], 0.0, 3.0, skip=("right",)))):
    mk(f"SM_N3_EntranceStub_{n}", (v, [tuple(reversed(q)) for q in f]), [SIL], recalc=False)

# ================================================================== planter, tree, shrubs, benches
c = 1.0                                                     # chamfer -> faceted plan
pp = [(PL_X - PL_W / 2 + c, PL_Y - PL_D / 2), (PL_X + PL_W / 2 - c, PL_Y - PL_D / 2), (PL_X + PL_W / 2, PL_Y - PL_D / 2 + c),
      (PL_X + PL_W / 2, PL_Y + PL_D / 2 - c), (PL_X + PL_W / 2 - c, PL_Y + PL_D / 2), (PL_X - PL_W / 2 + c, PL_Y + PL_D / 2),
      (PL_X - PL_W / 2, PL_Y + PL_D / 2 - c), (PL_X - PL_W / 2, PL_Y - PL_D / 2 + c)]
mkm("SM_N3_Planter", fc.prism(pp, 0.0, PL_H, cap_mat=0, top_mat=1), [CHR, MOSS])
col("COL_N3_Planter", fc.prism(pp, 0.0, PL_H)[:2])
trunk = fc.lathe([(0.55, 0), (0.42, 2.5), (0.32, 5.0), (0.0, 6.2)], 8)
mkm("SM_N3_Tree", fc.mparts((*trunk, 0),
                            *[(*fc.xform(fc.lathe([(0, -1.0), (1.6, -0.3), (1.4, 0.6), (0, 1.1)], 7), offset=o), 1)
                              for o in ((0, 0, 7.0), (1.8, 0.6, 6.0), (-1.7, -0.4, 6.3), (0.4, -1.8, 5.7),
                                        (-0.6, 1.7, 6.8), (1.0, -0.9, 8.4))]), [BARK, MOSS],
    loc=(PL_X, PL_Y, PL_H), recalc=True)
col("COL_N3_TreeTrunk", fc.xform(fc.cylinder_data(0.55, 3.0, 8), offset=(PL_X, PL_Y, PL_H)))
for i, (dx, dy) in enumerate(((-2.6, -1.6), (2.4, -1.8), (-2.5, 1.7), (2.6, 1.5))):
    mk(f"SM_N3_Shrub_{i}", fc.lathe([(0, 0), (0.7, 0.2), (0.6, 0.7), (0, 0.9)], 6), [MOSS],
       loc=(PL_X + dx, PL_Y + dy, PL_H))
me_bench = module("MOD_N_Bench", nk.bench(), [SIL, CHR])
BENCHES = [((PL_X - 2.0, PL_Y - PL_D / 2 - 0.35), 0), ((PL_X + 2.0, PL_Y - PL_D / 2 - 0.35), 0),
           ((PL_X - 2.0, PL_Y + PL_D / 2 + 0.35), 180), ((PL_X + 2.0, PL_Y + PL_D / 2 + 0.35), 180),
           ((PL_X - PL_W / 2 - 0.35, PL_Y), -90), ((PL_X + PL_W / 2 + 0.35, PL_Y), 90)]
for i, ((x, y), rz) in enumerate(BENCHES):
    fc.obj(f"SM_N3_Bench_{i:02d}", me_bench, C_EXP, (x, y, 0), rz)
col("COL_N3_Benches", fc.merge(*[BM(x - 0.9, x + 0.9, y - 0.3, y + 0.3, 0, 0.9) if rz in (0, 180) else
                                 BM(x - 0.3, x + 0.3, y - 0.9, y + 0.9, 0, 0.9) for (x, y), rz in BENCHES]))

# ================================================================== roof: 4 m glass bays over the void, solid border; vines
sky = module("MOD_N_Skylight_4x4", fc.mparts(
    *[(*BM(*b, 0, 0.5), 0) for b in ((-2, 2, -2, -1.8), (-2, 2, 1.8, 2), (-2, -1.8, -1.8, 1.8), (1.8, 2, -1.8, 1.8))],
    (*BM(-1.8, 1.8, -1.8, 1.8, 0.3, 0.34, skip=("left", "right", "front", "back")), 1)), [CHR, GLS])
k = 0
for x in range(int(ROOF_GLASS[0]) + 2, int(ROOF_GLASS[1]), 4):
    for y in range(int(ROOF_GLASS[2]) + 2, int(ROOF_GLASS[3]), 4):
        fc.obj(f"SM_N3_Skylight_{k:02d}", sky, C_ROOF, (x, y, VOID_H))
        k += 1
gx0, gx1, gy0, gy1 = ROOF_GLASS
mk("SM_N3_RoofBorder", fc.merge(BM(-HX, HX, -HY, gy0, VOID_H, VOID_H + 0.5), BM(-HX, HX, gy1, HY, VOID_H, VOID_H + 0.5),
                                BM(-HX, gx0, gy0, gy1, VOID_H, VOID_H + 0.5), BM(gx1, HX, gy0, gy1, VOID_H, VOID_H + 0.5)),
   [SIL], coll=C_ROOF)
vine = module("MOD_N_VineCard_3m", fc.xform((*fc.box_minmax(-0.2, 0.2, 0, 0.01, -3.0, 0.0)[:2],
                                             [0] * 6), offset=(0, 0, 0)), [MOSS])
for i, (x, y, z) in enumerate([(-12.6, -6, 8.95), (-12.6, 2, 8.95), (-6, 8.4, 8.95), (5, 8.4, 8.95), (12.6, -4, 8.95),
                               (-12.6, -2, 4.95), (2, 8.4, 4.95)]):
    fc.obj(f"SM_N3_Vine_{i:02d}", vine, C_EXP, (x, y, z), 90 if abs(x) > 12 else 0)

# ================================================================== landmarks
landmarks.update({
    "LM_Planter": (PL_X, PL_Y, 0.0),
    "LM_Stair_F1": (SX, F1_TOP_Y - ST_RUN, 0.0), "LM_Stair_Landing": (SX, LAND_Y0, 4.0),
    "LM_Stair_F2_Top": (SX, F2_TOP_Y, 8.0),
    "LM_Entrance_Main": (0.0, -HY, 0.0), "LM_Entrance_Side": (-HX, -1.0, 0.0),
})
for n, p in landmarks.items():
    fc.empty(n, p, C_LM, 0.8, "ARROWS").hide_render = True

# ================================================================== checks: 3 m loop around planter+benches, stair slope
bpy.context.view_layer.update()
loop_box = (PL_X - PL_W / 2 - 0.65 - 3.0, PL_X + PL_W / 2 + 0.65 + 3.0, PL_Y - PL_D / 2 - 0.65 - 3.0, PL_Y + PL_D / 2 + 0.65 + 3.0)
inner_box = (PL_X - PL_W / 2 - 0.65, PL_X + PL_W / 2 + 0.65, PL_Y - PL_D / 2 - 0.65, PL_Y + PL_D / 2 + 0.65)
loop_hits = []
for o in C_EXP.all_objects:
    if o.type != "MESH" or o.name.startswith(("SM_N3_Floor", "SM_N3_Planter", "SM_N3_Tree", "SM_N3_Shrub", "SM_N3_Bench",
                                              "SM_N3_Balcony", "SM_N3_TopTrim", "SM_N3_Roof", "SM_N3_Skylight",
                                              "SM_N3_Vine", "SM_N3_Rail_L")):
        continue
    bb = [o.matrix_world @ Vector(c_) for c_ in o.bound_box]
    if min(p.z for p in bb) > 2.5:
        continue
    x0, x1, y0, y1 = min(p.x for p in bb), max(p.x for p in bb), min(p.y for p in bb), max(p.y for p in bb)
    if x1 > loop_box[0] and x0 < loop_box[1] and y1 > loop_box[2] and y0 < loop_box[3]:
        loop_hits.append(o.name)

# ================================================================== presentation + renders
fc.ref_player(C_REF, (-3.0, -8.0, 0))
C_MOD.hide_render = True
C_COL.hide_render = True
bpy.context.view_layer.layer_collection.children[C_MOD.name].exclude = True


def cam(name, loc, target=None, lens=24, ortho=None):
    cd = bpy.data.cameras.new(name)
    if ortho:
        cd.type, cd.ortho_scale = "ORTHO", ortho
    else:
        cd.lens = lens
    cd.clip_end = 300
    o = bpy.data.objects.new(name, cd)
    o.location = loc
    C_PRES.objects.link(o)
    if target:
        fc.look_at(o, target)
    return o


cam_top = cam("CAM_TopDown", (0, 0, 60), ortho=34)
cam_eye = cam("CAM_EyeHeight", (-10.0, -10.0, 1.7), target=(3.0, 5.0, 4.0))
sun_d = bpy.data.lights.new("LGT_Key_6500K", "SUN")
sun_d.energy = 3.0
sun = bpy.data.objects.new("LGT_Key_6500K", sun_d)
sun.rotation_euler = (math.radians(25), 0, math.radians(20))
C_PRES.objects.link(sun)
sc.world.use_nodes = True
bg = sc.world.node_tree.nodes.get("Background")
bg.inputs[0].default_value = fc.hex_lin("#C9D6E3")
bg.inputs[1].default_value = 0.6
ref = bpy.data.objects["REF_Player"]
ref.hide_render = False
renders = {}
C_ROOF.hide_render = True
TOP_HIDE = ("SM_N3_TopTrim_12m", "SM_N3_Tree")          # plan view: show the planter and benches under the canopy
for c_name in TOP_HIDE:
    bpy.data.objects[c_name].hide_render = True
sc.camera = cam_top
renders["topdown"] = fc.render(os.path.join(fc.RENDER_DIR, "N3_blockout_topdown.png"), engine="BLENDER_EEVEE")
C_ROOF.hide_render = False
for c_name in TOP_HIDE:
    bpy.data.objects[c_name].hide_render = False
sc.camera = cam_eye
renders["eye"] = fc.render(os.path.join(fc.RENDER_DIR, "N3_blockout_eyeheight.png"), engine="BLENDER_EEVEE")
ref.hide_render = True

_, uniq, inst = fc.tri_report([C_EXP])
_, au, ai = fc.tri_report([C_APT])
apt_tris = fc.tri_count(bpy.data.objects["MOD_N_AptInterior"])
tree_tris = fc.tri_count(bpy.data.objects["SM_N3_Tree"])
report = {
    "footprint_interior_m": [2 * HX, 2 * HY], "void_height": VOID_H, "levels_z": list(LEVELS), "trim_z": TRIM_Z,
    "balconies": dict(depth=BD, inner_edges=dict(x=[IX0, IX1], y_back=IY1), slab=SLAB, headroom_under=4.0 - SLAB),
    "apartment_doors": dict(per_level=len(DOOR_XS), x=DOOR_XS, w=DOOR_W, h=DOOR_H,
                            interiors={f"L{k + 1}": [v, HY, LEVELS[k]] for k, v in APT.items()}),
    "apt_interior": dict(w=APT_W, d=APT_D, ceiling=APT_H, tris=apt_tris, budget=6000),
    "planter": dict(centre=[PL_X, PL_Y], w=PL_W, d=PL_D, h=PL_H, tree_tris=tree_tris, tree_budget=4000),
    "loop_3m_obstacles": loop_hits,
    "stair": dict(width=ST_X1 - ST_X0, x=[ST_X0, ST_X1], risers_per_flight=ST_RISERS, rise=round(ST_RISE, 4),
                  tread=ST_TREAD, run=ST_RUN, f1_y=[F1_TOP_Y - ST_RUN, F1_TOP_Y], landing_y=[LAND_Y0, LAND_Y1],
                  f2_y=[F2_TOP_Y - ST_RUN, F2_TOP_Y], slope_deg=round(math.degrees(math.atan2(ST_RISE, ST_TREAD)), 1)),
    "entrances": dict(main=dict(wall="front -Y", w=4, h=4), side=dict(wall="left -X", w=2, h=3)),
    "roof": dict(z=VOID_H, glass_bays=k, glass_area=ROOF_GLASS),
    "landmarks": {n: [round(c_, 3) for c_ in v] for n, v in landmarks.items()},
    "tris_export_unique": uniq, "tris_export_instanced": inst, "budget": 140000,
    "renders": renders,
}
blend = os.path.join(fc.SOURCE_DIR, "Fractured_N3_ResidentialAtrium.blend")
fc.save(blend)
report["blend"] = blend
with open(os.path.join(fc.RENDER_DIR, "N3_blockout_report.json"), "w") as fh:
    json.dump(report, fh, indent=2)
print("N3 BLOCKOUT DONE loop_hits=", loop_hits, "tris", uniq, inst, "apt", apt_tris, "tree", tree_tris)
