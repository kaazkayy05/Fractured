"""N1 Nova Research Facility — DETAIL stage (Block 0 workflow step 3) + Block Z QA + export.
Layout/dimensions approved at blockout (see build_N1_blockout.py / art/renders/N1_blockout_report.json).
Room interior: X -14..14, Y -9..9 (entrance on -Y), floor top z=0, ceiling (skylight underside) z=12.
Run: blender -b --factory-startup -P art/scripts/build_N1.py
"""
import os
import sys
import math
import json
import random
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(__file__))
import fractured_common as fc
import fractured_qa as qa

ID, NAME = "N1", "ResearchFacility"
sc = fc.reset_scene()
M = fc.append_shared_materials()
SIL, GLS, CYN, CHR, CLO = (M[k] for k in ("M_NovaSilver", "M_NovaGlass", "M_CyanEmissive", "M_Charcoal", "M_Cloth"))

C_EXP = fc.collection(f"{ID}_Export")
C_ROOF = fc.collection(f"{ID}_Roof", C_EXP)
C_COL = fc.collection(f"{ID}_Collision")
C_FX = fc.collection(f"{ID}_FX")
C_PRES = fc.collection(f"{ID}_Presentation")
C_REF = fc.collection("_Reference")
C_LM = fc.collection(f"{ID}_Landmarks")
C_MOD = fc.collection(f"{ID}_ModuleSources")

# ------------------------------------------------------------------ approved dimensions
HX, HY, H = 14.0, 9.0, 12.0
WT = 0.3
BAL_Z, BAL_T = 4.5, 0.4
BAL_Y0 = 6.0
STAIR_X0, STAIR_X1 = 12.0, 14.0
RISE, TREAD, N_TREADS = 0.18, 0.30, 24
STAIR_Y0 = BAL_Y0 - N_TREADS * TREAD          # -1.2
SX = (STAIR_X0 + STAIR_X1) / 2
SIDE_DOOR_Y = -7.0
RING_R, RING_W = 4.5, 0.2
CONSOLE_R = 5.2
CONSOLE_CLOCK = {"01": 7, "02": 6, "03": 5}
ROWS_Z = (0.0, 4.0, 8.0)
Y_PANELS = [(-7.0, 4), (-3.0, 4), (1.0, 4), (5.0, 4), (8.0, 2)]     # centre, width along Y walls
X_PANELS = [(-12.0 + 4 * i, 4) for i in range(7)]                    # along X walls


def mesh(name, vfm, mats, recalc=False):   # generators wind faces outward; QA verifies closed volumes
    v, f, m = vfm
    return fc.build_mesh(name, (v, f), mats, face_mats=m, recalc=recalc)


def module(name, vfm, mats, recalc=False):
    """Create a reusable module mesh + one source object in the excluded module collection."""
    me = mesh(name, vfm, mats, recalc)
    fc.obj(name, me, C_MOD)
    return me


def place(name, me, loc, rz=0.0, coll=None):
    return fc.obj(name, me, coll or C_EXP, loc, rz)


# ================================================================== MODULES
# --- floor tiles: silver field, charcoal 5 cm border (reads as tile seams), origin bottom-centre
def floor_tile(sx, sy, b=0.05, t=0.2):
    x0, x1, y0, y1 = -sx / 2, sx / 2, -sy / 2, sy / 2
    V = [(x0, y0, t), (x1, y0, t), (x1, y1, t), (x0, y1, t),
         (x0 + b, y0 + b, t), (x1 - b, y0 + b, t), (x1 - b, y1 - b, t), (x0 + b, y1 - b, t),
         (x0, y0, 0), (x1, y0, 0), (x1, y1, 0), (x0, y1, 0)]
    F = [(4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7),
         (8, 11, 10, 9), (0, 8, 9, 1), (1, 9, 10, 2), (2, 10, 11, 3), (3, 11, 8, 0)]
    return V, F, [0] + [1] * 9


me_floor = {4: module("MOD_N_Floor_4x4", floor_tile(4, 4), [SIL, CHR]),
            2: module("MOD_N_Floor_4x2", floor_tile(4, 2), [SIL, CHR])}

# --- wall panels (front face at local y=0 facing -Y, 0.3 m thick toward +Y), mats [SIL, CHR, CYN]
BAND = (1.97, 2.03)


def wall_panel(width, seam=False, hole=None, hole_mat=1):
    w = width / 2
    xs = {-w, w}
    zs = {0.0, BAND[0], BAND[1], 4.0}
    if seam:
        xs |= {-0.06, 0.06}
    if hole:
        hx0, hx1, hz0, hz1 = hole
        xs |= {hx0, hx1}
        zs |= {hz0, hz1}
    xs, zs = sorted(xs), sorted(zs)

    def inside_hole(i, j):
        if not hole:
            return False
        cx, cz = (xs[i] + xs[i + 1]) / 2, (zs[j] + zs[j + 1]) / 2
        return hole[0] < cx < hole[1] and hole[2] < cz < hole[3]

    def mat(i, j):
        cx, cz = (xs[i] + xs[i + 1]) / 2, (zs[j] + zs[j + 1]) / 2
        if seam and abs(cx) < 0.06:
            return 2
        if BAND[0] < cz < BAND[1]:
            return 1
        return 0

    pts, faces, mats = fc.grid2d(xs, zs, lambda i, j: not inside_hole(i, j), mat)

    def side(a, b, m):
        if hole and all(hole[0] - 1e-4 <= p[0] <= hole[1] + 1e-4 and hole[2] - 1e-4 <= p[1] <= hole[3] + 1e-4
                        for p in (a, b)) and not (abs(abs(a[0]) - w) < 1e-4 and abs(a[0] - b[0]) < 1e-4):
            return hole_mat
        return m
    return fc.extrude2d(pts, faces, mats, WT, 0.0, side_mat=side)


WALL_MATS = [SIL, CHR, CYN]
me_wall = {
    "plain4": module("MOD_N_Wall_4x4", wall_panel(4), WALL_MATS),
    "seam4": module("MOD_N_Wall_4x4_Seam", wall_panel(4, seam=True), WALL_MATS),
    "plain2": module("MOD_N_Wall_2x4", wall_panel(2), WALL_MATS),
    "door2x3": module("MOD_N_Wall_4x4_Door2x3", wall_panel(4, hole=(-1.0, 1.0, 0.0, 3.0)), WALL_MATS),
}
# office window wall: opening + recessed backlit emissive panel + charcoal mullions
ow = wall_panel(4, hole=(-1.6, 1.6, 0.8, 3.6))
mx = [-1.6, -0.83, -0.77, -0.03, 0.03, 0.77, 0.83, 1.6]
mz = [0.8, 2.17, 2.23, 3.6]
mpts, mfaces, mmats = fc.grid2d(mx, mz, lambda i, j: i % 2 == 1 or j == 1, lambda i, j: 1)
mull = fc.extrude2d(mpts, mfaces, mmats, 0.1, 0.12, back=False)
blpts, blf, blm = fc.grid2d([-1.6, 1.6], [0.8, 3.6], lambda i, j: True, lambda i, j: 2)
backlight = fc.extrude2d(blpts, blf, blm, 0.04, 0.22, side_mat=2)
me_wall["office4"] = module("MOD_N_Wall_4x4_Office", fc.mparts(ow, mull, backlight), WALL_MATS, recalc=False)

# --- outer corner post (fills the 0.3 x 0.3 wall corner)
me_corner = module("MOD_N_Corner_Outer", fc.mparts((*fc.box_minmax(-0.15, 0.15, -0.15, 0.15, 0, H), 0)), [SIL])

# --- faceted pilaster: front protrudes 0.4 m toward local -Y, chamfered facets charcoal
PIL_PTS = [(-0.3, 0.0), (-0.3, -0.25), (-0.18, -0.4), (0.18, -0.4), (0.3, -0.25), (0.3, 0.0)]
PIL_SIDES = [0, 1, 0, 1, 0, 0]
me_pil = {
    "full": module("MOD_N_Pilaster", fc.prism(PIL_PTS, 0, H, PIL_SIDES), [SIL, CHR]),
    "lower": module("MOD_N_Pilaster_Lower", fc.prism(PIL_PTS, 0, BAL_Z - BAL_T, PIL_SIDES), [SIL, CHR]),
    "upper": module("MOD_N_Pilaster_Upper", fc.prism(PIL_PTS, 0, H - BAL_Z, PIL_SIDES), [SIL, CHR]),
}


# --- door frames: charcoal portal protruding into the room, cyan reveal around the opening
def door_frame(ow_, oh, jamb, head, depth):
    w = ow_ / 2
    xs, zs = [-w - jamb, -w, w, w + jamb], [0.0, oh, oh + head]
    pts, faces, mats = fc.grid2d(xs, zs, lambda i, j: not (i == 1 and j == 0))

    def side(a, b, m):
        return 1 if all(abs(p[0]) <= w + 1e-4 and p[1] <= oh + 1e-4 for p in (a, b)) else 0
    return fc.extrude2d(pts, faces, mats, depth, -depth, back=False, side_mat=side)


me_df4 = module("MOD_N_DoorFrame_4x4", door_frame(4.0, 4.0, 0.5, 0.6, 0.35), [CHR, CYN], recalc=False)
me_df2 = module("MOD_N_DoorFrame_2x3", door_frame(2.0, 3.0, 0.3, 0.3, 0.25), [CHR, CYN], recalc=False)

# --- glass railing modules (glass + silver post + top rail), origin bottom-centre
def railing(L):
    return fc.mparts(
        (*fc.box_minmax(-L / 2, -L / 2 + 0.08, -0.05, 0.05, 0, 1.1), 1),
        (*fc.box_minmax(-L / 2 + 0.09, L / 2 - 0.01, -0.02, 0.02, 0.1, 0.95), 0),
        (*fc.box_minmax(-L / 2 + 0.08, L / 2, -0.04, 0.04, 0.98, 1.1, skip=("left",)), 1),
    )


me_rail = {4: module("MOD_N_Railing_Glass_4m", railing(4), [GLS, SIL]),
           2: module("MOD_N_Railing_Glass_2m", railing(2), [GLS, SIL])}
me_post = module("MOD_N_RailPost", fc.mparts((*fc.box_minmax(-0.04, 0.04, -0.05, 0.05, 0, 1.1), 0)), [SIL])

# --- stair module (24 treads / 25 risers to 4.5 m; final riser = balcony slab edge)
sv, sf = fc.stair_data(2.0, N_TREADS, TREAD, RISE)
sv = [(x, y - N_TREADS * TREAD, z) for x, y, z in sv]     # origin at top edge (grid-snapped landing edge)
me_stair = module("MOD_N_Stair_2m_4.5rise", (sv, sf, fc.stair_mats(N_TREADS, len(sf))), [SIL, CHR])

# --- skylight bays: charcoal frame (0.2 m border) + glass pane; frame bottom at module origin
def skylight(sy, b=0.2, depth=0.5):
    xs, ys = [-2, -2 + b, 2 - b, 2], [-sy / 2, -sy / 2 + b, sy / 2 - b, sy / 2]
    pts, faces, mats = fc.grid2d(xs, ys, lambda i, j: not (i == 1 and j == 1))
    frame = fc.xform(fc.extrude2d(pts, faces, mats, depth), rot_x=90)       # 2D z -> -Y ; extrusion -> +Z
    frame = (list(frame[0]), frame[1], frame[2])
    frame = ([(x, -y_, z) for x, y_, z in frame[0]], [tuple(reversed(f)) for f in frame[1]], frame[2])
    pane = fc.box_minmax(-2 + b, 2 - b, -sy / 2 + b, sy / 2 - b, 0.3, 0.34, skip=("left", "right", "front", "back"))
    return fc.mparts(frame, (*pane, 1))


me_sky = {4: module("MOD_N_Skylight_4x4", skylight(4.0), [CHR, GLS]),
          2: module("MOD_N_Skylight_4x2", skylight(2.0), [CHR, GLS])}

# --- banner: navy cloth with V-cut tail, silver double-chevron emblem, silver hanging rod
cloth_pts = [(-0.8, 0), (0, 0.5), (0.8, 0), (0.8, 5), (0, 5), (-0.8, 5)]
cloth = fc.extrude2d(cloth_pts, [(0, 1, 4, 5), (1, 2, 3, 4)], [0, 0], 0.03, -0.08)
emb = []
for dz in (3.75, 3.3):
    left = [(-0.5, 0.4), (0, -0.25), (0, 0.05), (-0.3, 0.4)]
    right = [(0.3, 0.4), (0, 0.05), (0, -0.25), (0.5, 0.4)]
    pts = [(x, z + dz) for x, z in left + right]
    emb.append(fc.extrude2d(pts, [(0, 1, 2, 3), (4, 5, 6, 7)], [1, 1], 0.015, -0.095, back=False))
rod = (*fc.box_minmax(-0.95, 0.95, -0.1, -0.04, 5.0, 5.08), 1)
me_banner = module("MOD_N_Banner", fc.mparts(cloth, *emb, rod), [CLO, SIL], recalc=False)

# ================================================================== PLACEMENT
# --- floor
for x, _ in X_PANELS:
    for y, w in Y_PANELS:
        place(f"SM_N1_Floor_{int(x + 14):02d}_{int(y + 9):02d}", me_floor[w], (x, y, -0.2))

# --- walls: (side, origin fn, rotation)
k = 0
for i, (x, w) in enumerate(X_PANELS):            # south (-Y) wall, faces +Y
    for r, z in enumerate(ROWS_Z):
        if r == 0 and abs(x) < 1e-6:
            continue                              # 4 x 4 main entrance
        kind = "seam4" if i % 2 else "plain4"
        place(f"SM_N1_Wall_S_{i}{r}", me_wall[kind], (x, -HY, z), 180)
for i, (x, w) in enumerate(X_PANELS):            # north (+Y) wall, faces -Y; office row above balcony
    for r, z in enumerate(ROWS_Z):
        kind = "office4" if r == 1 else ("seam4" if i % 2 else "plain4")
        place(f"SM_N1_Wall_N_{i}{r}", me_wall[kind], (x, HY, z), 0)
for side, xw, rz in (("W", -HX, 90), ("E", HX, -90)):
    for i, (y, w) in enumerate(Y_PANELS):
        for r, z in enumerate(ROWS_Z):
            if w == 2:
                kind = "plain2"
            elif side == "E" and r == 0 and abs(y - SIDE_DOOR_Y) < 1e-6:
                kind = "door2x3"
            else:
                kind = "seam4" if i % 2 else "plain4"
            place(f"SM_N1_Wall_{side}_{i}{r}", me_wall[kind], (xw, y, z), rz)
for i, (x, y) in enumerate([(-HX - 0.15, -HY - 0.15), (HX + 0.15, -HY - 0.15),
                            (HX + 0.15, HY + 0.15), (-HX - 0.15, HY + 0.15)]):
    place(f"SM_N1_Corner_{i}", me_corner, (x, y, 0))

# --- pilasters every 4 m (split above/below balcony; none at door edges or along the stair)
pil = []
for x in (-10, -6, 6, 10):
    pil.append(("full", (x, -HY, 0), 180))
for x in (-10, -6, -2, 2, 6, 10):
    pil += [("lower", (x, HY, 0), 0), ("upper", (x, HY, BAL_Z), 0)]
for y in (-5, -1, 3):
    pil.append(("full", (-HX, y, 0), 90))
pil.append(("full", (HX, -5, 0), -90))
for xw, rz in ((-HX, 90), (HX, -90)):
    pil += [("lower", (xw, 7, 0), rz), ("upper", (xw, 7, BAL_Z), rz)]
for i, (kind, loc, rz) in enumerate(pil):
    place(f"SM_N1_Pilaster_{i:02d}", me_pil[kind], loc, rz)

# --- doors
place("SM_N1_DoorFrame_Main", me_df4, (0, -HY, 0), 180)
place("SM_N1_DoorFrame_Side", me_df2, (HX, SIDE_DOOR_Y, 0), -90)

# --- EXIT sign + arrow as geometry (charcoal plate, cyan letters), above the side exit
gp, gf, gm = fc.glyphs("EXIT >", 0.06, 0.0, 0.075)
sign = fc.mparts((*fc.box_minmax(-0.85, 0.85, -0.1, 0.0, 0.0, 0.45, skip=("back",)), 0),
                 fc.extrude2d(gp, gf, [1] * len(gf), 0.03, -0.13, back=False))
place("SM_N1_ExitSign", mesh("SM_N1_ExitSign", sign, [CHR, CYN], recalc=False), (HX, SIDE_DOOR_Y, 3.45), -90)

# --- banners on the entrance wall, flanking the main door
for i, x in enumerate((-8, 8)):
    place(f"SM_N1_Banner_{i + 1:02d}", me_banner, (x, -HY, 5.5), 180)

# --- balcony slab: silver deck, silver fascia with cyan underlight strip (open mesh: no back/ends)
bv = [(-HX, BAL_Y0, BAL_Z), (HX, BAL_Y0, BAL_Z), (HX, HY, BAL_Z), (-HX, HY, BAL_Z),
      (-HX, BAL_Y0, BAL_Z - BAL_T), (HX, BAL_Y0, BAL_Z - BAL_T), (HX, HY, BAL_Z - BAL_T), (-HX, HY, BAL_Z - BAL_T),
      (-HX, BAL_Y0, BAL_Z - BAL_T + 0.08), (HX, BAL_Y0, BAL_Z - BAL_T + 0.08)]
bf = [(0, 1, 2, 3), (4, 7, 6, 5), (4, 5, 9, 8), (8, 9, 1, 0)]
place("SM_N1_Balcony", mesh("SM_N1_Balcony", (bv, bf, [0, 0, 1, 0]), [SIL, CYN], recalc=False), (0, 0, 0))

for i, (x, L) in enumerate([(x, 4) for x in (-12, -8, -4, 0, 4, 8)] + [(11, 2)]):
    place(f"SM_N1_BalconyRail_{i:02d}", me_rail[L], (x, BAL_Y0 + 0.1, BAL_Z))
place("SM_N1_RailPost_00", me_post, (STAIR_X0 - 0.04, BAL_Y0 + 0.1, BAL_Z))

# --- office/backlit row is part of the north wall modules (row z=4)

# --- stair + sloped glass rail on its open (-X) side
place("SM_N1_BalconyStair", me_stair, (SX, BAL_Y0, 0))
slope = BAL_Z / (BAL_Y0 - STAIR_Y0)
zr = lambda y: (y - STAIR_Y0) * slope
rx0, rx1 = STAIR_X0 + 0.02, STAIR_X0 + 0.1
srail = fc.mparts(
    (*fc.box_minmax(rx0, rx1, STAIR_Y0, STAIR_Y0 + 0.1, 0, 1.1), 1),
    (*fc.sheared_box(rx0 + 0.02, rx1 - 0.02, STAIR_Y0 + 0.11, zr(STAIR_Y0 + 0.11) + 0.12,
                     BAL_Y0 - 0.02, zr(BAL_Y0 - 0.02) + 0.12, 0.8), 0),
    (*fc.sheared_box(rx0, rx1, STAIR_Y0 + 0.1, zr(STAIR_Y0 + 0.1) + 0.98, BAL_Y0, BAL_Z + 0.98, 0.12), 1),
)
place("SM_N1_StairRail", mesh("SM_N1_StairRail", srail, [GLS, SIL]), (0, 0, 0))

# ================================================================== VESSEL
PL_R, PL_H = 1.75, 0.6
OFF8 = math.pi / 8
facet = PL_R * math.cos(OFF8)                     # flat facet faces -Y
plinth = fc.lathe([(PL_R, 0), (PL_R, 0.52), (PL_R - 0.08, PL_H), (0, PL_H)], 8, angle_offset=OFF8)
plinth = (plinth[0], plinth[1], [0] * 8 + [1] * 8 + [0] * 8)
stv, stf = fc.stair_data(1.3, 2, 0.3, 0.2, back=False, bottom=False)
steps = fc.xform((stv, stf, fc.stair_mats(2, len(stf), 1, 0)), offset=(0, -facet - 0.6, 0))
place("SM_Vessel_Base", mesh("SM_Vessel_Base", fc.mparts(plinth, steps), [CHR, SIL], recalc=False), (0, 0, 0))

glass = fc.lathe([(1.5, 0), (1.5, 6.0), (1.45, 6.0), (1.45, 0)], 16, closed=True, angle_offset=math.pi / 16)
ribs = [fc.xform((*fc.box_minmax(1.52, 1.6, -0.04, 0.04, 0, 6.0), [1] * 6), rot_z=45 * k + 22.5) for k in range(8)]
place("SM_Vessel_Glass", mesh("SM_Vessel_Glass", fc.mparts((*glass, 0), *ribs), [GLS, SIL]), (0, 0, PL_H))

cap_prof = [(0, 0), (1.6, 0), (1.8, 0.15), (1.8, 0.3), (1.8, 0.5), (1.8, 0.65), (1.5, 0.8), (0, 0.8)]
cap = fc.lathe(cap_prof, 8, angle_offset=OFF8)
cap_seg = [0, 1, 0, 2, 0, 1, 0]
place("SM_Vessel_Cap", mesh("SM_Vessel_Cap", (cap[0], cap[1], [m for m in cap_seg for _ in range(8)]),
                            [CHR, SIL, CYN]), (0, 0, PL_H + 6.0))

rng = random.Random(7)
cr_prof = [(0, -1.25), (0.32, -0.85), (0.55, -0.35), (0.62, 0.15), (0.5, 0.6), (0.28, 0.95), (0, 1.25)]
cv, cf = fc.lathe(cr_prof, 10)
cv = [(x * rng.uniform(0.85, 1.15), y * rng.uniform(0.85, 1.15), z + rng.uniform(-0.05, 0.05)) for x, y, z in cv]
parts = [(cv, cf, 0)]
for k in range(4):
    sv_, sf_ = fc.lathe([(0, -0.28), (0.11, -0.02), (0.08, 0.1), (0, 0.3)], 5)
    R = Matrix.Rotation(rng.uniform(-0.6, 0.6), 3, "X") @ Matrix.Rotation(rng.uniform(-0.6, 0.6), 3, "Y")
    a = math.radians(90 * k + 30)
    off = Vector((0.95 * math.cos(a), 0.95 * math.sin(a), rng.uniform(-0.6, 0.6)))
    parts.append(([tuple(R @ Vector(p) + off) for p in sv_], sf_, 0))
place("SM_Vessel_Crystal", mesh("SM_Vessel_Crystal", fc.mparts(*parts), [CYN]), (0, 0, 2.5))

ring = fc.lathe([(RING_R + RING_W / 2, 0), (RING_R + RING_W / 2, 0.01), (RING_R - RING_W / 2, 0.01),
                 (RING_R - RING_W / 2, 0)], 64)
place("SM_N1_FloorRing", mesh("SM_N1_FloorRing", (*ring, [0] * len(ring[1])), [CYN], recalc=False), (0, 0, 0))

# ================================================================== CONSOLES
# shared base (local: operator side -Y, 1.2 W x 0.8 D x 1.1 H); mats [SIL, CHR, CYN]
ztop = lambda x, y: 0.95 + (y + 0.4) / 0.8 * 0.15
desk = fc.slab_grid([-0.6, -0.48, 0.48, 0.6], [-0.4, -0.3, 0.28, 0.4], 0.85, ztop,
                    lambda i, j: 2 if (i == 1 and j == 1) else 1, side_mat=1)
con_base = fc.mparts(
    (*fc.box_minmax(-0.55, 0.55, -0.3, 0.35, 0, 0.12, skip=("bottom",)), 1),
    (*fc.box_minmax(-0.6, 0.6, -0.25, 0.4, 0.12, 0.85, skip=("bottom",)), 0),
    desk,
)
me_con = module("MOD_N_Console_Base", con_base, [SIL, CHR, CYN])


def monitor(x0, x1, z0=1.06, z1=1.62, y0=0.24, d=0.1, b=0.04):
    pts, faces, mats = fc.grid2d([x0, x0 + b, x1 - b, x1], [z0, z0 + b, z1 - b, z1],
                                 lambda i, j: True, lambda i, j: 1 if (i == 1 and j == 1) else 0)
    return fc.extrude2d(pts, faces, mats, d, y0, side_mat=0)


def numeral(ch):
    gp_, gf_, _ = fc.glyphs(ch, 0.1, 0.0, 0.25)
    return fc.extrude2d(gp_, gf_, [1] * len(gf_), 0.03, -0.28, back=False)


TOPS = {
    "01": [monitor(-0.4, 0.4)],
    "02": [monitor(-0.58, -0.04), monitor(0.04, 0.58)],
    "03": [monitor(-0.55, 0.15), (*fc.prism([(0.3, 0.12), (0.55, 0.12), (0.55, 0.38), (0.3, 0.38)], 1.06, 1.9), ),
           (*fc.prism([(0.3, 0.12), (0.55, 0.12), (0.55, 0.38), (0.3, 0.38)], 1.9, 2.0, cap_mat=1),)],
}
TOPS["03"][1] = (TOPS["03"][1][0], TOPS["03"][1][1], [2] * len(TOPS["03"][1][1]))

landmarks = {"LM_Vessel": (0.0, 0.0, 0.0)}
for n, clock in CONSOLE_CLOCK.items():
    theta = math.radians(90 - clock * 30)
    x, y = round(CONSOLE_R * math.cos(theta), 3), round(CONSOLE_R * math.sin(theta), 3)
    rz = math.degrees(theta) + 90
    c = place(f"SM_Console_{n}", me_con, (x, y, 0), rz)
    c["console_number"] = int(n)
    t = place(f"SM_Console_{n}_Top", mesh(f"SM_Console_{n}_Top", fc.mparts(*TOPS[n], numeral(n[-1])),
                                          [CHR, CYN, SIL], recalc=False), (0, 0, 0))
    t.parent = c
    landmarks[f"LM_Console_{n}"] = (x, y, 0.0)

landmarks["LM_Exit_Main"] = (0.0, -HY, 0.0)
landmarks["LM_Exit_Side"] = (HX, SIDE_DOOR_Y, 0.0)
landmarks["LM_BalconyStair"] = (SX, STAIR_Y0, 0.0)
landmarks["LM_BalconyStair_Top"] = (SX, BAL_Y0, BAL_Z)
for n, p in landmarks.items():
    e = fc.empty(n, p, C_LM, 0.8, "ARROWS")
    e.hide_render = True

# ================================================================== ROOF
rows = [(-7, 4), (-3, 4), (1, 4), (5, 4), (8, 2)]
k = 0
for x, _ in X_PANELS:
    for y, sy in rows:
        place(f"SM_N1_Skylight_{k:02d}", me_sky[sy], (x, y, H), 0, C_ROOF)
        k += 1

# ================================================================== COLLISION (-colonly)
B, BM = fc.build_mesh, fc.box_minmax
def col(name, data):
    o = fc.obj(f"{name}-colonly", B(name, data), C_COL)
    o.display_type = "WIRE"
    return o

col("COL_N1_Floor", BM(-HX - WT, HX + WT, -HY - WT, HY + WT, -0.2, 0.0))
col("COL_N1_Wall_S", fc.merge(BM(-HX - WT, -2.5, -HY - WT, -HY, 0, H), BM(2.5, HX + WT, -HY - WT, -HY, 0, H),
                              BM(-2.5, 2.5, -HY - WT, -HY + 0.35, 4.0, H),
                              BM(-2.5, -2.0, -HY, -HY + 0.35, 0, 4.0), BM(2.0, 2.5, -HY, -HY + 0.35, 0, 4.0)))
col("COL_N1_Wall_N", BM(-HX - WT, HX + WT, HY, HY + WT, 0, H))
col("COL_N1_Wall_W", BM(-HX - WT, -HX, -HY, HY, 0, H))
col("COL_N1_Wall_E", fc.merge(BM(HX, HX + WT, -HY, SIDE_DOOR_Y - 1.0, 0, H), BM(HX, HX + WT, SIDE_DOOR_Y + 1.0, HY, 0, H),
                              BM(HX - 0.25, HX + WT, SIDE_DOOR_Y - 1.3, SIDE_DOOR_Y + 1.3, 3.0, H),
                              BM(HX - 0.25, HX, SIDE_DOOR_Y - 1.3, SIDE_DOOR_Y - 1.0, 0, 3.0),
                              BM(HX - 0.25, HX, SIDE_DOOR_Y + 1.0, SIDE_DOOR_Y + 1.3, 0, 3.0)))
pil_boxes = []
for kind, (x, y, z), rz in pil:
    hgt = {"full": H, "lower": BAL_Z - BAL_T, "upper": H - BAL_Z}[kind]
    if rz in (0, 180):
        dy = -0.4 if rz == 0 else 0.0
        pil_boxes.append(BM(x - 0.3, x + 0.3, y + dy, y + dy + 0.4, z, z + hgt))
    else:
        dx = 0.0 if rz == 90 else -0.4
        pil_boxes.append(BM(x + dx, x + dx + 0.4, y - 0.3, y + 0.3, z, z + hgt))
col("COL_N1_Pilasters", fc.merge(*pil_boxes))
col("COL_N1_Balcony", BM(-HX, HX, BAL_Y0, HY, BAL_Z - BAL_T, BAL_Z))
col("COL_N1_BalconyRail", BM(-HX, STAIR_X0, BAL_Y0 + 0.04, BAL_Y0 + 0.16, BAL_Z, BAL_Z + 1.1))
# ramps ride on the step nosings (toe extended one tread) so the collider never sits inside the steps
col("COL_N1_Stair", fc.wedge_data(STAIR_X0, STAIR_X1, STAIR_Y0 - TREAD, BAL_Y0, BAL_Z))
col("COL_N1_StairRail", fc.sheared_box(STAIR_X0 - 0.04, STAIR_X0 + 0.1, STAIR_Y0, 0.0, BAL_Y0, BAL_Z, 1.1))
col("COL_Vessel_Plinth", fc.cylinder_data(PL_R, PL_H, 8, angle_offset=OFF8))
col("COL_Vessel_Steps", fc.wedge_data(-0.65, 0.65, -facet - 0.9, -facet, PL_H))
glass_col = col("COL_Vessel_Glass", fc.cylinder_data(1.5, 6.8, 8, angle_offset=OFF8))
glass_col.location = (0, 0, PL_H)
for n in CONSOLE_CLOCK:
    src = bpy.data.objects[f"SM_Console_{n}"]
    o = col(f"COL_Console_{n}", BM(-0.6, 0.6, -0.4, 0.4, 0, 1.1))
    o.location, o.rotation_euler = src.location.copy(), src.rotation_euler.copy()

# ================================================================== REFERENCE / PRESENTATION
fc.ref_player(C_REF, (0, -7.0, 0))
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
    cd.clip_end = 200
    o = bpy.data.objects.new(name, cd)
    o.location = loc
    C_PRES.objects.link(o)
    if target:
        fc.look_at(o, target)
    return o


cam_top = cam("CAM_TopDown", (0, 0, 40), ortho=34)
cam_eye = cam("CAM_EyeHeight", (-9.5, -8.3, 1.7), target=(1.5, 1.5, 2.8))
cam_hero = cam("CAM_Hero34", (7.5, -8.7, 4.6), target=(-1.2, 1.0, 2.6), lens=20)
sun_d = bpy.data.lights.new("LGT_Key_6500K", "SUN")
sun_d.energy = 3.5
try:
    sun_d.use_temperature, sun_d.temperature = True, 6500
except Exception:
    sun_d.color = (0.95, 0.97, 1.0)
sun_d.angle = math.radians(2)
sun = bpy.data.objects.new("LGT_Key_6500K", sun_d)
sun.rotation_euler = (math.radians(32), 0, math.radians(28))
C_PRES.objects.link(sun)

sc.world.use_nodes = True
bgn = sc.world.node_tree.nodes.get("Background")
bgn.inputs[0].default_value = fc.hex_lin("#C9D6E3")
bgn.inputs[1].default_value = 0.55

renders = {}
C_ROOF.hide_render = True
sc.camera = cam_top
renders["topdown"] = fc.render(os.path.join(fc.RENDER_DIR, "N1_detail_topdown.png"), engine="BLENDER_EEVEE")
C_ROOF.hide_render = False
sc.camera = cam_eye
renders["eye"] = fc.render(os.path.join(fc.RENDER_DIR, "N1_detail_eyeheight.png"), engine="BLENDER_EEVEE")
sc.camera = cam_hero
renders["hero"] = fc.render(os.path.join(fc.RENDER_DIR, "N1_detail_hero34.png"), engine="BLENDER_EEVEE")
# flat-ambient readability check (no key light)
sun.hide_render = True
bgn.inputs[1].default_value = 1.0
sc.camera = cam_eye
renders["eye_flat_ambient"] = fc.render(os.path.join(fc.RENDER_DIR, "N1_detail_eyeheight_flat.png"), engine="BLENDER_EEVEE")
sun.hide_render = False
bgn.inputs[1].default_value = 0.55
sc.camera = cam_hero

# ================================================================== BLOCK Z + EXPORT
blend = os.path.join(fc.SOURCE_DIR, f"Fractured_{ID}_{NAME}.blend")
glb = os.path.join(fc.EXPORT_DIR, f"Fractured_{ID}_{NAME}.glb")
report = qa.run(ID, C_EXP, C_COL, C_FX, budget=120000, landmark_coll=C_LM,
                walk_bounds=(-HX, HX, -HY, HY),
                # plinth top is a 0.25 m ledge around the glass (obstacle), not a walk path; its steps are walkable
                walkable_prefixes=("COL_N1_Floor", "COL_N1_Balcony", "COL_N1_Stair", "COL_Vessel_Steps"))
report["rotations_baked"] = baked
report["renders"] = renders
report["blend"] = blend
fc.save(blend)
report["export"] = qa.export_and_verify(C_EXP, C_COL, glb)
report["glb"] = glb
with open(os.path.join(fc.RENDER_DIR, "N1_QA_report.json"), "w") as fh:
    json.dump(report, fh, indent=2)
print("N1 DETAIL DONE")
