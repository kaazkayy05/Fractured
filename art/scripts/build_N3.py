"""N3 Nova Residential Atrium — DETAIL stage + Block Z QA + export.
Layout approved at blockout (build_N3_blockout.py / art/renders/N3_blockout_report.json).
Interior X -15..15, Y -11..11 (entrances on the -Y front wall), ground z=0, balcony levels z=4 / z=8,
non-walkable trim ring at z=12, glass roof at z=16. Balconies (2.5 m) on left / back / right.
Run: blender -b --factory-startup -P art/scripts/build_N3.py
"""
import os
import sys
import math
import json
import random
import bpy
import bmesh
from mathutils import Vector, Euler

sys.path.insert(0, os.path.dirname(__file__))
import fractured_common as fc
import fractured_qa as qa
import nova_kit as nk
import veyra_kit as vk

ID, NAME = "N3", "ResidentialAtrium"
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

# ------------------------------------------------------------------ approved dimensions (unchanged from blockout)
HX, HY, WT = 15.0, 11.0, 0.3
VOID_H, TRIM_Z, SLAB = 16.0, 12.0, 0.4
LEVELS = (0.0, 4.0, 8.0)
BD = 2.5
IX0, IX1, IY1 = -HX + BD, HX - BD, HY - BD
DOOR_W, DOOR_H = 2.0, 3.0
DOOR_XS = [-12.0 + 4 * i for i in range(7)]
APT = {0: -8.0, 1: 0.0, 2: 8.0}
APT_W, APT_D, APT_H = 6.0, 4.0, 3.0
VEST_D = 1.0
PL_X, PL_Y, PL_W, PL_D, PL_H = 0.0, -1.5, 8.0, 6.0, 0.8
ST_X0, ST_X1 = 9.5, 12.5
ST_RISERS, ST_TREAD = 22, 0.30
ST_RISE = 4.0 / ST_RISERS
ST_RUN = (ST_RISERS - 1) * ST_TREAD
F1_TOP_Y, LAND_Y0, LAND_Y1, F2_TOP_Y = 0.0, 0.0, IY1 - ST_RUN, IY1
SX = (ST_X0 + ST_X1) / 2
MAIN_ENT = (-2.0, 2.0, 0.0, 4.0)
SIDE_ENT = (-2.0, 0.0, 0.0, 3.0)
ROOF_GLASS = (-12.0, 12.0, -10.0, 6.0)


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


def col(name, data):
    o = fc.obj(f"{name}-colonly", fc.build_mesh(name, data, weld=False), C_COL)
    o.display_type = "WIRE"
    return o


# ================================================================== floor tiles (4 m grid + 2 m / 1 m fillers)
FX_ = [(-12.0 + 4 * i, 4.0) for i in range(7)] + [(-14.5, 1.0), (14.5, 1.0)]
FY_ = [(-9.0 + 4 * j, 4.0) for j in range(5)] + [(10.0, 2.0)]
tiles = {}
for (x, w) in FX_:
    for (y, d) in FY_:
        key = (w, d)
        if key not in tiles:
            tiles[key] = module(f"MOD_N_Floor_{w:g}x{d:g}", nk.floor_tile(w, d), [SIL, CHR])
        place(f"SM_N3_Floor_{x:+05.1f}_{y:+05.1f}", tiles[key], (x, y, -0.2))
col("COL_N3_Floor", BM(-HX - WT, HX + WT, -HY - WT, HY + WT, -0.2, 0.0))

# ================================================================== walls (modular; seam strip every second side/front panel)
W_MATS = [SIL, CHR, CYN]
w_door = module("MOD_N_Wall_4x4_AptDoor", nk.wall_panel(4, hole=(-1.0, 1.0, 0.0, 3.0), band=False), W_MATS)
w_plain = module("MOD_N_Wall_4x4", nk.wall_panel(4, band=False), W_MATS)
w_seam = module("MOD_N_Wall_4x4_Seam", nk.wall_panel(4, seam=True, band=False), W_MATS)
w_top = module("MOD_N_Wall_4x4_Top", nk.wall_panel(4, band=False, top_strip=True), W_MATS)
w_1 = module("MOD_N_Wall_1x4", nk.wall_panel(1, band=False), W_MATS)
w_1t = module("MOD_N_Wall_1x4_Top", nk.wall_panel(1, band=False, top_strip=True), W_MATS)
w_2 = module("MOD_N_Wall_2x4", nk.wall_panel(2, band=False), W_MATS)
w_2t = module("MOD_N_Wall_2x4_Top", nk.wall_panel(2, band=False, top_strip=True), W_MATS)
w_sdoor = module("MOD_N_Wall_4x4_Door2x3", nk.wall_panel(4, hole=(-1.0, 1.0, 0.0, 3.0), band=False), W_MATS)
ROWS = (0.0, 4.0, 8.0, 12.0)
for r, z in enumerate(ROWS):
    top = r == 3
    for i, x in enumerate(DOOR_XS):
        place(f"SM_N3_Wall_N_{r}{i}", w_top if top else w_door, (x, HY, z), 0)
    for x in (-14.5, 14.5):
        place(f"SM_N3_Wall_N_{r}f{int(x)}", w_1t if top else w_1, (x, HY, z), 0)
SIDE_YS = [(-9.0, 4), (-5.0, 4), (-1.0, 4), (3.0, 4), (7.0, 4), (10.0, 2)]
for side, x, rz in (("W", -HX, 90), ("E", HX, -90)):
    for r, z in enumerate(ROWS):
        top = r == 3
        for i, (y, w) in enumerate(SIDE_YS):
            if w == 2:
                me = w_2t if top else w_2
            elif side == "W" and r == 0 and y == -1.0:
                me = w_sdoor
            else:
                me = w_top if top else (w_seam if i % 2 else w_plain)
            place(f"SM_N3_Wall_{side}_{r}{i}", me, (x, y, z), rz)
FRONT_XS = [(-12.0 + 4 * i, 4) for i in range(7)] + [(-14.5, 1), (14.5, 1)]
for r, z in enumerate(ROWS):
    top = r == 3
    for i, (x, w) in enumerate(FRONT_XS):
        if r == 0 and x == 0.0:
            continue                                                         # 4 x 4 main entrance bay
        me = (w_1t if top else w_1) if w == 1 else (w_top if top else (w_seam if i % 2 else w_plain))
        place(f"SM_N3_Wall_S_{r}{i}", me, (x, -HY, z), 180)
col("COL_N3_Walls", fc.merge(
    BM(-HX - WT, MAIN_ENT[0], -HY - WT, -HY, 0, VOID_H), BM(MAIN_ENT[1], HX + WT, -HY - WT, -HY, 0, VOID_H),
    BM(MAIN_ENT[0], MAIN_ENT[1], -HY - WT, -HY, MAIN_ENT[3], VOID_H),
    BM(-HX - WT, -HX, -HY, SIDE_ENT[0], 0, VOID_H), BM(-HX - WT, -HX, SIDE_ENT[1], HY, 0, VOID_H),
    BM(-HX - WT, -HX, SIDE_ENT[0], SIDE_ENT[1], SIDE_ENT[3], VOID_H),
    BM(HX, HX + WT, -HY, HY, 0, VOID_H), BM(-HX - WT, HX + WT, HY, HY + WT, 12.0, VOID_H)))
bw = []
for z in LEVELS:
    xs = [-HX - WT] + [v for x in DOOR_XS for v in (x - DOOR_W / 2, x + DOOR_W / 2)] + [HX + WT]
    for x0, x1 in zip(xs[0::2], xs[1::2]):
        bw.append(BM(x0, x1, HY, HY + WT, z, z + 4.0))
    for x in DOOR_XS:
        bw.append(BM(x - DOOR_W / 2, x + DOOR_W / 2, HY, HY + WT, z + DOOR_H, z + 4.0))
col("COL_N3_BackWall", fc.merge(*bw))

# ================================================================== balconies + trim ring: slabs with cyan underlight fascia
def ring_slab(z, t=SLAB, strip=True):
    parts = [(*BM(-HX, IX0, -HY, IY1, z - t, z), 0), (*BM(-HX, HX, IY1, HY, z - t, z), 0),
             (*BM(IX1, HX, -HY, IY1, z - t, z), 0)]
    if strip:
        zs = (z - t + 0.06, z - t + 0.14)
        parts += [(*BM(IX0, IX0 + 0.02, -HY, IY1, *zs), 1), (*BM(IX0, IX1, IY1 - 0.02, IY1, *zs), 1),
                  (*BM(IX1 - 0.02, IX1, -HY, IY1, *zs), 1)]
    return fc.mparts(*parts)


for k, z in enumerate((4.0, 8.0)):
    unique(f"SM_N3_Balcony_L{k + 2}", ring_slab(z), [SIL, CYN])
    col(f"COL_N3_Balcony_L{k + 2}", fc.merge(BM(-HX, IX0, -HY, IY1, z - SLAB, z), BM(-HX, HX, IY1, HY, z - SLAB, z),
                                            BM(IX1, HX, -HY, IY1, z - SLAB, z)))
unique("SM_N3_TopTrim_12m", ring_slab(TRIM_Z), [SIL, CYN])

# ================================================================== glass railings (4 m modules + one remainder module per run)
rail_me = {}


def rail_module(L):
    key = round(L, 3)
    if key not in rail_me:
        rail_me[key] = module(f"MOD_N_Railing_Glass_{key:g}m", nk.railing(L), [GLS, SIL])
    return rail_me[key]


def rail_runs(level):
    runs = [("L", (-HY, IY1)), ("R", (-HY, IY1)), ("B", (IX0, IX1))]
    out = []
    for side, (a, b) in runs:
        gaps = []
        if side == "R" and level == 2:
            gaps.append((LAND_Y0, LAND_Y1))
        if side == "B" and level == 3:
            gaps.append((ST_X0, ST_X1))
        s = a
        for g0, g1 in sorted(gaps):
            out.append((side, s, g0))
            s = g1
        out.append((side, s, b))
    return [r for r in out if r[2] - r[1] > 1e-3]


rails_col = []
ri = 0
for level, z in ((2, 4.0), (3, 8.0)):
    for side, s0, s1 in rail_runs(level):
        pos, L = s0, s1 - s0
        pieces = [4.0] * int(L // 4) + ([round(L % 4, 3)] if L % 4 > 1e-3 else [])
        for p in pieces:
            c_ = pos + p / 2
            if side == "B":
                place(f"SM_N3_Rail_{ri:03d}", rail_module(p), (c_, IY1 + 0.06, z), 0)
            else:
                place(f"SM_N3_Rail_{ri:03d}", rail_module(p), (IX0 - 0.06 if side == "L" else IX1 + 0.06, c_, z), 90)
            pos += p
            ri += 1
        if side == "B":
            rails_col.append(BM(s0, s1, IY1, IY1 + 0.12, z, z + 1.1))
        else:
            x = IX0 - 0.06 if side == "L" else IX1 + 0.06
            rails_col.append(BM(x - 0.06, x + 0.06, s0, s1, z, z + 1.1))

# ================================================================== main stair (2 flights + landing), rails, landing columns
me_stair = module("MOD_N_Stair_3m_4rise", nk.stair(3.0, ST_RISERS, ST_RISE, ST_TREAD), [SIL, CHR])
place("SM_N3_Stair_F1", me_stair, (SX, F1_TOP_Y, 0.0))
place("SM_N3_Stair_F2", me_stair, (SX, F2_TOP_Y, 4.0))
unique("SM_N3_Stair_Landing", fc.mparts((*BM(ST_X0, ST_X1, LAND_Y0, LAND_Y1, 4.0 - SLAB, 4.0), 0),
                                        (*BM(ST_X0 - 0.02, ST_X0, LAND_Y0, LAND_Y1, 3.66, 3.74), 1)), [SIL, CYN])
me_colm = module("MOD_N_Column_3.6", fc.prism(nk.ngon(8, 0.2), 0.0, 4.0 - SLAB, side_mats=[0, 1] * 4), [SIL, CHR])
for i, y in enumerate((LAND_Y0 + 0.25, LAND_Y1 - 0.25)):
    place(f"SM_N3_LandingColumn_{i}", me_colm, (ST_X0 + 0.25, y, 0))
ramp = nk.stair_ramp(3.0, ST_RISERS, ST_RISE, ST_TREAD)
col("COL_N3_Stair_F1", fc.xform(ramp, offset=(SX, F1_TOP_Y, 0.0)))
col("COL_N3_Stair_F2", fc.xform(ramp, offset=(SX, F2_TOP_Y, 4.0)))
col("COL_N3_Stair_Landing", BM(ST_X0, ST_X1, LAND_Y0, LAND_Y1, 4.0 - SLAB, 4.0))
col("COL_N3_LandingColumns", fc.merge(*[BM(ST_X0 + 0.05, ST_X0 + 0.45, y - 0.2, y + 0.2, 0, 3.6)
                                        for y in (LAND_Y0 + 0.25, LAND_Y1 - 0.25)]))
for side, x in (("W", ST_X0 + 0.06), ("E", ST_X1 - 0.06)):
    for fl, (y_top, z0) in (("F1", (F1_TOP_Y, 0.0)), ("F2", (F2_TOP_Y, 4.0))):
        unique(f"SM_N3_StairRail_{fl}_{side}", nk.sloped_rail(x, y_top - ST_RUN - ST_TREAD, z0, y_top, z0 + 4.0), [GLS, SIL])
        rails_col.append(fc.sheared_box(x - 0.06, x + 0.06, y_top - ST_RUN - ST_TREAD, z0, y_top, z0 + 4.0, 1.1))
place("SM_N3_LandingRail_W", rail_module(LAND_Y1 - LAND_Y0), (ST_X0 + 0.06, (LAND_Y0 + LAND_Y1) / 2, 4.0), 90)
rails_col.append(BM(ST_X0, ST_X0 + 0.12, LAND_Y0, LAND_Y1, 4.0, 5.1))
col("COL_N3_Rails", fc.merge(*rails_col))

# ================================================================== apartment doors, vestibules, interiors
door = fc.mparts((*BM(-1.2, -1.0, -0.15, 0.0, 0.0, 3.2), 0), (*BM(1.0, 1.2, -0.15, 0.0, 0.0, 3.2), 0),
                 (*BM(-1.0, 1.0, -0.15, 0.0, 3.0, 3.2, skip=("front",)), 0),
                 (*BM(-1.2, 1.2, -0.17, -0.15, 3.05, 3.15), 1))
me_door = module("MOD_N_AptDoor", door, [CHR, CYN])
vv, vf = BM(-1.0, 1.0, WT, WT + VEST_D, 0.0, DOOR_H, skip=("front",))
me_vest = module("MOD_N_AptVestibule", (vv, [tuple(reversed(q)) for q in vf], [0] * len(vf)), [CHR])


def apt_interior():
    """6 x 4 m, 3 m ceiling; opening at local y=0. Living area (sofa, table, wall screen) + 1.5 m utility alcove at +X.
    Mats [silver, charcoal, cloth, cyan]."""
    W, D, Hh = APT_W / 2, APT_D, APT_H
    sv_, sf_ = BM(-W, W, 0.0, D, 0.0, Hh, skip=("front",))
    shell = (sv_, [tuple(reversed(q)) for q in sf_], [1, 0, 0, 0, 0])                 # floor charcoal, walls/ceiling silver
    p = [shell,
         (*BM(-W + 0.6, -W + 4.0, 0.6, D - 0.3, Hh - 0.03, Hh - 0.01), 3),            # ceiling light panel
         (*BM(W - 1.5, W - 1.4, 0.0, D - 1.2, 0.0, 2.2), 1),                          # alcove half partition
         (*BM(W - 1.4, W, D - 0.6, D, 0.0, 0.9), 1), (*BM(W - 1.4, W, D - 0.62, D, 0.9, 0.95), 0),   # counter + top
         (*BM(W - 1.3, W - 0.2, D - 0.04, D - 0.01, 1.0, 1.06), 3),                   # counter light strip
         (*BM(W - 0.4, W, 0.5, D - 0.7, 0.0, 0.05), 1)]
    for h in (0.6, 1.2, 1.8):
        p.append((*BM(W - 0.4, W, 0.5, D - 0.7, h, h + 0.04), 0))                     # shelves
    p += [(*BM(W - 0.4, W - 0.36, 0.5, D - 0.7, 0.05, 1.84), 1),                       # shelf upright
          (*BM(-W + 0.3, -W + 2.5, D - 0.9, D - 0.1, 0.0, 0.42), 2),                   # sofa seat
          (*BM(-W + 0.3, -W + 2.5, D - 0.3, D - 0.1, 0.42, 0.85), 2),                  # sofa back
          (*BM(-W + 0.3, -W + 0.5, D - 0.9, D - 0.3, 0.42, 0.6), 2), (*BM(-W + 2.3, -W + 2.5, D - 0.9, D - 0.3, 0.42, 0.6), 2),
          (*BM(-W + 0.8, -W + 2.0, D - 2.3, D - 1.5, 0.38, 0.45), 0),                  # table top
          (*BM(-W + 1.3, -W + 1.5, D - 2.0, D - 1.8, 0.0, 0.38), 1),                   # table pedestal
          (*BM(-W + 0.0, -W + 0.04, 0.75, 2.85, 0.95, 1.95), 1),                       # screen bezel (against wall)
          (*BM(-W + 0.04, -W + 0.06, 0.8, 2.8, 1.0, 1.9), 3),                          # wall screen face (cyan)
          (*BM(-W + 0.3, -W + 2.8, D - 2.7, D - 1.1, 0.0, 0.01), 2)]                   # rug
    return fc.mparts(*p)


me_apt = module("MOD_N_AptInterior", apt_interior(), [SIL, CHR, CLO, CYN])
landmarks = {}
for lv, z in enumerate(LEVELS):
    for i, x in enumerate(DOOR_XS):
        place(f"SM_N3_AptDoor_L{lv + 1}_{i}", me_door, (x, HY, z), coll=C_APT)
        if APT.get(lv) == x:
            place(f"SM_N3_AptInterior_L{lv + 1}", me_apt, (x, HY + WT, z), coll=C_APT)
            landmarks[f"LM_AptDoor_L{lv + 1}"] = (x, HY, z)
        else:
            place(f"SM_N3_AptVestibule_L{lv + 1}_{i}", me_vest, (x, HY, z), coll=C_APT)
apt_col = []
for lv, z in enumerate(LEVELS):
    for x in DOOR_XS:
        if APT.get(lv) == x:
            x0, x1, y0, y1 = x - APT_W / 2, x + APT_W / 2, HY + WT, HY + WT + APT_D
            apt_col += [BM(x0 - WT, x1 + WT, y0, y1 + WT, z - 0.2, z), BM(x0 - WT, x0, y0, y1, z, z + APT_H),
                        BM(x1, x1 + WT, y0, y1, z, z + APT_H), BM(x0, x1, y1, y1 + WT, z, z + APT_H),
                        BM(x0 - WT, x1 + WT, y0, y1 + WT, z + APT_H, z + APT_H + 0.2),
                        BM(x - 3.0, x - 0.9, y1 - 0.9, y1, z, z + 0.85),                     # sofa
                        BM(x + 1.5, x + 3.0, y1 - 0.6, y1, z, z + 0.95)]                     # counter
        else:
            apt_col.append(BM(x - 1.0, x + 1.0, HY + WT + VEST_D, HY + WT + VEST_D + 0.2, z, z + DOOR_H))
            apt_col.append(BM(x - 1.0, x + 1.0, HY + WT, HY + WT + VEST_D, z - 0.2, z))
col("COL_N3_Apartments", fc.merge(*apt_col))

# ================================================================== entrances
me_df4 = module("MOD_N_DoorFrame_4x4", nk.door_frame(4.0, 4.0, 0.5, 0.6, 0.35), [CHR, CYN])
me_df2 = module("MOD_N_DoorFrame_2x3", nk.door_frame(2.0, 3.0, 0.3, 0.3, 0.25), [CHR, CYN])
place("SM_N3_DoorFrame_Main", me_df4, (0.0, -HY, 0.0), 180)
place("SM_N3_DoorFrame_Side", me_df2, (-HX, -1.0, 0.0), 90)
for n, (v, f) in (("Main", BM(MAIN_ENT[0], MAIN_ENT[1], -HY - WT - 4.0, -HY - WT, 0.0, 4.0, skip=("back",))),
                  ("Side", BM(-HX - WT - 4.0, -HX - WT, SIDE_ENT[0], SIDE_ENT[1], 0.0, 3.0, skip=("right",)))):
    unique(f"SM_N3_EntranceStub_{n}", (v, [tuple(reversed(q)) for q in f], [0] * len(f)), [SIL])
col("COL_N3_DoorFrames", fc.merge(BM(-2.5, -2.0, -HY, -HY + 0.35, 0, 4.6), BM(2.0, 2.5, -HY, -HY + 0.35, 0, 4.6),
                                  BM(-HX, -HX + 0.25, -2.3, -2.0, 0, 3.3), BM(-HX, -HX + 0.25, 0.0, 0.3, 0, 3.3)))

# ================================================================== planter (faceted bed, rim, soil) + tree + shrubs + benches
c = 1.0
def oct_plan(w, d, ch):
    return [(-w / 2 + ch, -d / 2), (w / 2 - ch, -d / 2), (w / 2, -d / 2 + ch), (w / 2, d / 2 - ch), (w / 2 - ch, d / 2),
            (-w / 2 + ch, d / 2), (-w / 2, d / 2 - ch), (-w / 2, -d / 2 + ch)]


outer, inner = oct_plan(PL_W, PL_D, c), oct_plan(PL_W - 0.5, PL_D - 0.5, c - 0.1)
rim_v = [(x, y, PL_H) for x, y in outer] + [(x, y, PL_H) for x, y in inner] + \
        [(x, y, PL_H - 0.08) for x, y in inner]
n8 = 8
rim_f = [(k, (k + 1) % n8, n8 + (k + 1) % n8, n8 + k) for k in range(n8)] + \
        [(n8 + k, n8 + (k + 1) % n8, 2 * n8 + (k + 1) % n8, 2 * n8 + k) for k in range(n8)]
soil = fc.prism(inner, 0.0, PL_H - 0.08, cap_mat=1)
body = fc.prism(outer, 0.0, PL_H, side_mats=[0, 2] * 4, cap_mat=0)
# prism faces: [bottom, top] pairs for the cap fans, then sides. Body keeps bottom+sides (rim/soil replace the top).
planter = fc.mparts((body[0], [f for i, f in enumerate(body[1]) if not (i % 2 == 1 and i < 2 * (n8 - 2))],
                     [m for i, m in enumerate(body[2]) if not (i % 2 == 1 and i < 2 * (n8 - 2))]),
                    (rim_v, rim_f, [2] * len(rim_f)),
                    (soil[0], [f for i, f in enumerate(soil[1]) if i % 2 == 1 and i < 2 * (n8 - 2)],
                     [1] * (n8 - 2)))
unique("SM_N3_Planter", planter, [CHR, MOSS, SIL], loc=(PL_X, PL_Y, 0))
col("COL_N3_Planter", fc.xform(fc.prism(outer, 0.0, PL_H)[:2], offset=(PL_X, PL_Y, 0)))


def tree(seed=12):
    """[bark, foliage]. Leaning 8-sided trunk + 3 branches + 7 faceted canopy clusters (stylised low-poly)."""
    rng = random.Random(seed)
    parts = [(*vk.tube([(0, 0, 0), (0.1, 0.05, 2.0), (0.25, 0.1, 4.0), (0.3, 0.2, 5.6)], [0.55, 0.45, 0.36, 0.25],
                       twist=0.2, jitter=0.06, seed=seed), 0)]
    tips = [(0.3, 0.2, 5.6)]
    for a, h, L in ((40, 3.2, 2.4), (170, 3.8, 2.2), (280, 4.4, 2.0)):
        d = Vector((math.cos(math.radians(a)), math.sin(math.radians(a)), 0.9)).normalized()
        p0 = Vector((0.15, 0.08, h))
        p1 = p0 + d * L
        parts.append((*vk.tube([tuple(p0), tuple(p0 + d * L * 0.5), tuple(p1)], [0.22, 0.17, 0.12], seed=seed + a), 0))
        tips.append(tuple(p1))
    for k, t in enumerate(tips + [(1.2, -1.0, 6.4), (-1.0, 1.2, 6.9), (0.0, 0.3, 7.6)]):
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
        s = (rng.uniform(1.5, 2.0), rng.uniform(1.4, 1.9), rng.uniform(0.95, 1.25))
        R = Euler((0, 0, rng.uniform(0, 3))).to_matrix()
        vs = [tuple(R @ Vector((v.co.x * s[0] * rng.uniform(0.9, 1.1), v.co.y * s[1] * rng.uniform(0.9, 1.1),
                                v.co.z * s[2])) + Vector(t) + Vector((0, 0, 0.5))) for v in bm.verts]
        parts.append((vs, [tuple(v.index for v in f.verts) for f in bm.faces], [1] * len(bm.faces)))
        bm.free()
    return fc.mparts(*parts)


tr = unique("SM_N3_Tree", tree(), [BARK, MOSS], loc=(PL_X, PL_Y, PL_H - 0.08), recalc=True)
col("COL_N3_TreeTrunk", fc.xform(fc.cylinder_data(0.55, 3.0, 8), offset=(PL_X, PL_Y, PL_H)))
blob = fc.lathe([(0, 0), (0.55, 0.15), (0.5, 0.55), (0, 0.75)], 7)
shrub = module("MOD_N_Shrub", fc.mparts(*[(*fc.xform(blob, offset=o), 0)
                                          for o in ((0, 0, 0), (0.45, 0.25, 0.1), (-0.35, 0.3, 0.05))]),
               [MOSS], recalc=True)
for i, (dx, dy) in enumerate(((-2.6, -1.6), (2.4, -1.8), (-2.5, 1.7), (2.6, 1.5))):
    place(f"SM_N3_Shrub_{i}", shrub, (PL_X + dx, PL_Y + dy, PL_H - 0.08), 37 * i)
me_bench = module("MOD_N_Bench", nk.bench(), [SIL, CHR])
BENCHES = [((PL_X - 2.0, PL_Y - PL_D / 2 - 0.35), 0), ((PL_X + 2.0, PL_Y - PL_D / 2 - 0.35), 0),
           ((PL_X - 2.0, PL_Y + PL_D / 2 + 0.35), 180), ((PL_X + 2.0, PL_Y + PL_D / 2 + 0.35), 180),
           ((PL_X - PL_W / 2 - 0.35, PL_Y), -90), ((PL_X + PL_W / 2 + 0.35, PL_Y), 90)]
for i, ((x, y), rz) in enumerate(BENCHES):
    place(f"SM_N3_Bench_{i:02d}", me_bench, (x, y, 0), rz)
col("COL_N3_Benches", fc.merge(*[BM(x - 0.9, x + 0.9, y - 0.3, y + 0.3, 0, 0.9) if rz in (0, 180) else
                                 BM(x - 0.3, x + 0.3, y - 0.9, y + 0.9, 0, 0.9) for (x, y), rz in BENCHES]))

# ================================================================== roof: glass bays + border + ribs; vine cards
sky = module("MOD_N_Skylight_4x4", fc.mparts(
    *[(*BM(*b, 0, 0.5), 0) for b in ((-2, 2, -2, -1.8), (-2, 2, 1.8, 2), (-2, -1.8, -1.8, 1.8), (1.8, 2, -1.8, 1.8))],
    (*BM(-1.8, 1.8, -1.8, 1.8, 0.3, 0.34, skip=("left", "right", "front", "back")), 1)), [CHR, GLS])
k = 0
for x in range(int(ROOF_GLASS[0]) + 2, int(ROOF_GLASS[1]), 4):
    for y in range(int(ROOF_GLASS[2]) + 2, int(ROOF_GLASS[3]), 4):
        place(f"SM_N3_Skylight_{k:02d}", sky, (x, y, VOID_H), coll=C_ROOF)
        k += 1
gx0, gx1, gy0, gy1 = ROOF_GLASS
unique("SM_N3_RoofBorder", fc.mparts(*[(*b, 0) for b in (
    BM(-HX, HX, -HY, gy0, VOID_H, VOID_H + 0.5), BM(-HX, HX, gy1, HY, VOID_H, VOID_H + 0.5),
    BM(-HX, gx0, gy0, gy1, VOID_H, VOID_H + 0.5), BM(gx1, HX, gy0, gy1, VOID_H, VOID_H + 0.5))]), [SIL], coll=C_ROOF)
me_rib = module("MOD_N_RoofBeam_24m", fc.mparts((*BM(-12.0, 12.0, -0.2, 0.2, -0.6, 0.0), 0),
                                                (*BM(-12.0, 12.0, -0.05, 0.05, -0.62, -0.6), 1)), [CHR, CYN])
for i, y in enumerate((-6.0, -2.0, 2.0)):
    place(f"SM_N3_RoofBeam_{i}", me_rib, (0.0, y, VOID_H), coll=C_ROOF)
vine = {L: module(f"MOD_N_VineCard_{L:g}m", vk.vine_card(L), [MOSS]) for L in (2.0, 3.0)}
for i, (x, y, z, L) in enumerate([(-12.6, -6, 7.55, 3.0), (-12.6, 2, 7.55, 2.0), (-6, 8.4, 7.55, 3.0), (5, 8.4, 7.55, 2.0),
                                  (12.6, -4, 7.55, 3.0), (-12.6, -2, 3.55, 2.0), (2, 8.4, 3.55, 2.0),
                                  (-8, 8.4, 11.55, 3.0), (12.6, 4, 11.55, 3.0)]):
    place(f"SM_N3_Vine_{i:02d}", vine[L], (x, y, z), 90 if abs(x) > 12 else 0)

# ================================================================== landmarks (identical to blockout)
landmarks.update({
    "LM_Planter": (PL_X, PL_Y, 0.0),
    "LM_Stair_F1": (SX, F1_TOP_Y - ST_RUN, 0.0), "LM_Stair_Landing": (SX, LAND_Y0, 4.0),
    "LM_Stair_F2_Top": (SX, F2_TOP_Y, 8.0),
    "LM_Entrance_Main": (0.0, -HY, 0.0), "LM_Entrance_Side": (-HX, -1.0, 0.0),
})
for n, p in landmarks.items():
    fc.empty(n, p, C_LM, 0.8, "ARROWS").hide_render = True

# ================================================================== presentation + renders
fc.ref_player(C_REF, (-3.0, -8.0, 0))
C_MOD.hide_render = True
C_COL.hide_render = True
bpy.context.view_layer.layer_collection.children[C_MOD.name].exclude = True
baked = fc.bake_unique_rotations(list(C_EXP.all_objects) + list(C_COL.objects))


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
cam_hero = cam("CAM_Hero34", (-11.5, -9.0, 9.4), target=(4.0, 3.0, 4.0), lens=20)
sun_d = bpy.data.lights.new("LGT_Key_6500K", "SUN")
sun_d.energy = 3.5
try:
    sun_d.use_temperature, sun_d.temperature = True, 6500
except Exception:
    sun_d.color = (0.95, 0.97, 1.0)
sun = bpy.data.objects.new("LGT_Key_6500K", sun_d)
sun.rotation_euler = (math.radians(22), 0, math.radians(25))
C_PRES.objects.link(sun)
sc.world.use_nodes = True
bg = sc.world.node_tree.nodes.get("Background")
bg.inputs[0].default_value = fc.hex_lin("#C9D6E3")
bg.inputs[1].default_value = 0.55
renders = {}
TOP_HIDE = [bpy.data.objects[n] for n in ("SM_N3_TopTrim_12m", "SM_N3_Tree")]
C_ROOF.hide_render = True
for o in TOP_HIDE:
    o.hide_render = True
sc.camera = cam_top
renders["topdown"] = fc.render(os.path.join(fc.RENDER_DIR, "N3_detail_topdown.png"), engine="BLENDER_EEVEE")
C_ROOF.hide_render = False
for o in TOP_HIDE:
    o.hide_render = False
sc.camera = cam_eye
renders["eye"] = fc.render(os.path.join(fc.RENDER_DIR, "N3_detail_eyeheight.png"), engine="BLENDER_EEVEE")
sc.camera = cam_hero
renders["hero"] = fc.render(os.path.join(fc.RENDER_DIR, "N3_detail_hero34.png"), engine="BLENDER_EEVEE")
cam_apt = cam("CAM_AptCheck", (0.0, 11.6, 5.7), target=(-1.5, 14.8, 4.9), lens=18)
sc.camera = cam_apt
renders["apartment"] = fc.render(os.path.join(fc.RENDER_DIR, "N3_detail_apartment.png"), engine="BLENDER_EEVEE")
sun.hide_render = True
bg.inputs[1].default_value = 1.0
sc.camera = cam_eye
renders["eye_flat_ambient"] = fc.render(os.path.join(fc.RENDER_DIR, "N3_detail_eyeheight_flat.png"), engine="BLENDER_EEVEE")
sun.hide_render = False
bg.inputs[1].default_value = 0.55
sc.camera = cam_hero

# ================================================================== Block Z + export
blend = os.path.join(fc.SOURCE_DIR, f"Fractured_{ID}_{NAME}.blend")
glb = os.path.join(fc.EXPORT_DIR, f"Fractured_{ID}_{NAME}.glb")
report = qa.run(ID, C_EXP, C_COL, C_FX, budget=140000, landmark_coll=C_LM, walk_bounds=(-HX, HX, -HY, HY),
                walkable_prefixes=("COL_N3_Floor", "COL_N3_Balcony", "COL_N3_Stair_"),
                pair_with=os.path.join(fc.RENDER_DIR, "N3_blockout_landmarks.json"))
report["apt_interior_tris"] = fc.tri_count(bpy.data.objects["MOD_N_AptInterior"])
report["tree_tris"] = fc.tri_count(tr)
report["rotations_baked"] = baked
report["renders"] = renders
report["blend"] = blend
fc.save(blend)
report["export"] = qa.export_and_verify(C_EXP, C_COL, glb)
report["glb"] = glb
with open(os.path.join(fc.RENDER_DIR, "N3_QA_report.json"), "w") as fh:
    json.dump(report, fh, indent=2)
print("N3 DETAIL DONE pass=", report["pass"], "apt", report["apt_interior_tris"], "tree", report["tree_tris"])
