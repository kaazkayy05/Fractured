"""R2 Turbine Chasm — BLOCKOUT (Block 0 workflow step 2).
Chasm X -20..20 (5 x 8 m bays), Y -8..8, main catwalk level z=0, level B z=-4, chasm floor z=-24, roof z=14.
Primary route (y -1.5..1.5): R1 door (-X) -> entry catwalks -> stair down to level B -> landing -> 8 m breakaway span
(x -4..4) -> landing -> stair up -> exit catwalks -> R3 door (+X).
Alternate route: root bridge at z=0 (x -12..12, y 2.4..5.6) between the entry and exit junction decks.
Run: blender -b --factory-startup -P art/scripts/build_R2_blockout.py
"""
import os
import sys
import math
import json
import random
import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(__file__))
import fractured_common as fc
import nova_kit as nk
import veyra_kit as vk

ID = "R2"
sc = fc.reset_scene()
M = fc.append_shared_materials()
SIL, GLS, CYN, CHR, AMB, BARK, MOSS = (M[k] for k in ("M_NovaSilver", "M_NovaGlass", "M_CyanEmissive", "M_Charcoal",
                                                    "M_AmberWarning", "M_Bark", "M_Moss"))
C_EXP = fc.collection(f"{ID}_Export")
C_BRK = fc.collection(f"{ID}_Breakaway", C_EXP)
C_ROOT = fc.collection(f"{ID}_RootBridge", C_EXP)
C_COL = fc.collection(f"{ID}_Collision")
C_FX = fc.collection(f"{ID}_FX")
C_PRES = fc.collection(f"{ID}_Presentation")
C_REF = fc.collection("_Reference")
C_LM = fc.collection(f"{ID}_Landmarks")
C_MOD = fc.collection(f"{ID}_ModuleSources")
BM = fc.box_minmax

# ------------------------------------------------------------------ dimensions
HX, HY, WT = 20.0, 8.0, 0.4
ZA, ZB, ZF, ZR = 0.0, -4.0, -24.0, 14.0           # main catwalk, level B, chasm floor, roof
CW = 1.5                                          # catwalk half-width (3 m)
DECK_T = 0.25
RAIL_H = 1.1
RISERS, TREAD = 22, 0.30
RISE = (ZA - ZB) / RISERS
RUN = (RISERS - 1) * TREAD                        # 6.3
STAIR_TOP_X = 12.0                                # stairs: x -12 -> -5.7 (down) and 5.7 -> 12 (up)
BRK_X = 4.0                                       # breakaway span x -4..4
RB_Y0, RB_Y1 = 2.4, 5.6                           # root bridge deck (strands on both edges)
JUNC_X = 16.0                                     # junction decks x -16..-12 / 12..16, y 1.5..5.6
ENTRY = (-2.0, 2.0, 0.0, 4.0)                     # R1 door on -X wall (y0, y1, z0, z1)
EXIT = (-3.0, 3.0, 0.0, 5.0)                      # R3 approach on +X wall (6 x 5)
TURB = [(-8.0, -10.0), (8.0, -10.0)]              # (x, z) on the south wall, 8 m diameter
KILL_Z = -20.0


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


def place(name, me, loc=(0, 0, 0), rz=0.0, coll=None):
    return fc.obj(name, me, coll or C_EXP, loc, rz)


def col(name, data):
    o = fc.obj(f"{name}-colonly", fc.build_mesh(name, data, weld=False), C_COL)
    o.display_type = "WIRE"
    return o


def rail_run(x0, x1, y, z, mat=1):
    """Amber railing along X at y: posts every 2 m, mid + top rail. Returns parts with material index `mat`."""
    p = [(*BM(x0, x1, y - 0.04, y + 0.04, z + RAIL_H - 0.08, z + RAIL_H), mat),
         (*BM(x0, x1, y - 0.03, y + 0.03, z + 0.5, z + 0.56), mat)]
    n = max(1, int(round((x1 - x0) / 2.0)))
    for k in range(n + 1):
        x = x0 + (x1 - x0) * k / n
        p.append((*BM(x - 0.04, x + 0.04, y - 0.04, y + 0.04, z, z + RAIL_H - 0.08), mat))
    return p


def rail_run_y(y0, y1, x, z, mat=1):
    """Amber railing along Y at x."""
    n = max(1, int(round((y1 - y0) / 2.0)))
    p = [(*BM(x - 0.04, x + 0.04, y0, y1, z + RAIL_H - 0.08, z + RAIL_H), mat),
         (*BM(x - 0.03, x + 0.03, y0, y1, z + 0.5, z + 0.56), mat)]
    p += [(*BM(x - 0.04, x + 0.04, y - 0.04, y + 0.04, z, z + RAIL_H - 0.08), mat)
          for y in [y0 + (y1 - y0) * k / n for k in range(n + 1)]]
    return p


cols = {"decks": [], "rails": [], "stairs": []}

# ================================================================== catwalk modules (3 m wide, 4 m long), junctions, landings
def catwalk(rail_n=True, rail_s=True, L=4.0):
    p = [(*BM(-L / 2, L / 2, -CW, CW, -DECK_T, 0.0), 0),
         (*BM(-L / 2, L / 2, -CW - 0.02, -CW, -0.2, -0.12), 2), (*BM(-L / 2, L / 2, CW, CW + 0.02, -0.2, -0.12), 2)]
    if rail_s:
        p += rail_run(-L / 2, L / 2, -CW + 0.05, 0.0)
    if rail_n:
        p += rail_run(-L / 2, L / 2, CW - 0.05, 0.0)
    return fc.mparts(*p)


me_cw = module("MOD_R_Catwalk_4m", catwalk(), [SIL, AMB, CYN])
me_cw_open = module("MOD_R_Catwalk_4m_OpenN", catwalk(rail_n=False), [SIL, AMB, CYN])
me_land = module("MOD_R_StairLanding", catwalk(L=STAIR_TOP_X - RUN - BRK_X), [SIL, AMB, CYN])
for side, s in (("W", -1), ("E", 1)):
    place(f"SM_R2_Catwalk_{side}1", me_cw, (s * 18.0, 0.0, ZA))
    place(f"SM_R2_Catwalk_{side}2", me_cw_open, (s * 14.0, 0.0, ZA))
    cols["decks"].append(BM(s * 20.0 if s < 0 else 12.0, -12.0 if s < 0 else 20.0, -CW, CW, ZA - DECK_T, ZA))
    for y in (-CW + 0.05,):
        cols["rails"].append(BM(min(s * 20, s * 12), max(s * 20, s * 12), y - 0.05, y + 0.05, ZA, ZA + RAIL_H))
    cols["rails"].append(BM(min(s * 20, s * 16), max(s * 20, s * 16), CW - 0.1, CW, ZA, ZA + RAIL_H))
    # junction deck to the root bridge (x 12..16, y 1.5..5.6)
    jx0, jx1 = sorted((s * 12.0, s * JUNC_X))
    jun = [(*BM(jx0, jx1, CW, RB_Y1, -DECK_T, 0.0), 0)]
    jun += rail_run(jx0, jx1, RB_Y1 - 0.05, 0.0)
    jun += rail_run_y(CW, RB_Y1, s * (JUNC_X - 0.05), 0.0)            # outer edge
    jun += rail_run_y(CW, RB_Y0, s * 12.05, 0.0)                       # short return beside the root-bridge opening
    mkm(f"SM_R2_Junction_{side}", fc.mparts(*jun), [SIL, AMB])
    cols["decks"].append(BM(jx0, jx1, CW, RB_Y1, -DECK_T, 0.0))
    cols["rails"] += [BM(jx0, jx1, RB_Y1 - 0.1, RB_Y1, 0, RAIL_H),
                      BM(s * JUNC_X - 0.1 * (s > 0), s * JUNC_X + 0.1 * (s < 0), CW, RB_Y1, 0, RAIL_H),
                      BM(s * 12.0 - 0.05, s * 12.0 + 0.05, CW, RB_Y0, 0, RAIL_H)]
    # level-B landing (x 4..5.7) between stair foot and the breakaway span
    lx = s * (BRK_X + (STAIR_TOP_X - RUN - BRK_X) / 2)
    place(f"SM_R2_Landing_{side}", me_land, (lx, 0.0, ZB))
    lx0, lx1 = sorted((s * BRK_X, s * (STAIR_TOP_X - RUN)))
    cols["decks"].append(BM(lx0, lx1, -CW, CW, ZB - DECK_T, ZB))
    cols["rails"] += [BM(lx0, lx1, -CW, -CW + 0.1, ZB, ZB + RAIL_H), BM(lx0, lx1, CW - 0.1, CW, ZB, ZB + RAIL_H)]

# stairs down / up (3 m, 22 x 0.1818), amber side rails; pylons under landings
me_st = module("MOD_R_Stair_3m_4drop", nk.stair(2 * CW, RISERS, RISE, TREAD), [SIL, CHR])
ramp = nk.stair_ramp(2 * CW, RISERS, RISE, TREAD)
for side, s, rz in (("W", -1, 90), ("E", 1, -90)):
    loc = (s * STAIR_TOP_X, 0.0, ZB)
    place(f"SM_R2_Stair_{side}", me_st, loc, rz)
    col(f"COL_R2_Stair_{side}", fc.xform(ramp, rot_z=rz, offset=loc))
    for y in (-CW + 0.05, CW - 0.05):
        r = fc.xform(fc.sheared_box(y - 0.04, y + 0.04, -RUN - TREAD, 0.0, 0.0, ZA - ZB, RAIL_H), rot_z=rz, offset=loc)
        mk(f"SM_R2_StairRail_{side}{'S' if y < 0 else 'N'}", r, [AMB])
        cols["rails"].append(r)
me_py = module("MOD_R_Pylon", fc.prism(nk.ngon(6, 0.3), 0.0, ZB - ZF - DECK_T, cap_mat=0), [CHR])
pylons = [(sx * (BRK_X + 0.4), sy * (CW - 0.3)) for sx in (-1, 1) for sy in (-1, 1)]
for i, (x, y) in enumerate(pylons):
    place(f"SM_R2_Pylon_{i}", me_py, (x, y, ZF))
cols["decks"] += [BM(x - 0.3, x + 0.3, y - 0.3, y + 0.3, ZF, ZB - DECK_T) for x, y in pylons]

# ================================================================== breakaway bridge: intact + 5 pre-fractured pieces (same origin)
def hazard_deck(x0, x1, y0, y1, band=0.5):
    xs = [x0 + k * band for k in range(int(round((x1 - x0) / band)) + 1)]
    pts, faces, mats = fc.grid2d(xs, [y0, y1], lambda i, j: True, lambda i, j: i % 2)
    top = fc.xform(fc.extrude2d(pts, faces, mats, DECK_T, 0.0), rot_x=90)
    return ([(x, -y, z) for x, y, z in top[0]], [tuple(reversed(f)) for f in top[1]], top[2])


intact = fc.mparts(hazard_deck(-BRK_X, BRK_X, -CW, CW),
                   *rail_run(-BRK_X, BRK_X, -CW + 0.05, 0.0, 0), *rail_run(-BRK_X, BRK_X, CW - 0.05, 0.0, 0))
intact = (intact[0], intact[1], [m if m < 2 else 0 for m in intact[2]])
br = mkm("SM_BreakawayBridge_Intact", fc.xform(intact, offset=(0, 0, -DECK_T)), [AMB, CHR], coll=C_BRK, loc=(0, 0, ZB),
         recalc=True)
br["state"] = "intact"
cuts = [(-BRK_X, -BRK_X), (-2.4, -2.0), (-0.6, -0.9), (1.1, 0.8), (2.6, 2.3), (BRK_X, BRK_X)]   # x at y=-CW / y=+CW
for k in range(5):
    (a0, a1), (b0, b1) = cuts[k], cuts[k + 1]
    poly = [(a0, -CW), (b0, -CW), (b1, CW), (a1, CW)]
    piece = fc.prism(poly, -DECK_T, 0.0, cap_mat=1, top_mat=0)
    rails = []
    for y in (-CW + 0.05, CW - 0.05):
        xa, xb = (a0, b0) if y < 0 else (a1, b1)
        rails += rail_run(min(xa, xb) + 0.02, max(xa, xb) - 0.02, y, 0.0, 0)
    o = mkm(f"SM_BreakawayBridge_Piece_{k + 1:02d}", fc.mparts(piece, *rails), [AMB, CHR], coll=C_BRK,
            loc=(0, 0, ZB), recalc=True)
    o["state"] = "broken"
    o.hide_render = True                           # authored at the bridge origin; Godot shows them when it breaks
# unstable supports (amber/black) from the span ends to the south wall
sup = []
for x in (-BRK_X + 0.4, BRK_X - 0.4):
    for k in range(6):
        ya = -CW - k * (HY - CW - 0.2) / 6
        yb = -CW - (k + 1) * (HY - CW - 0.2) / 6
        za = ZB - DECK_T - k * 1.0
        sup.append((*fc.sheared_box(x - 0.15, x + 0.15, ya, za - 0.3, yb, za - 1.3, 0.3)[:2], k % 2))
mkm("SM_BreakawayBridge_Supports", fc.mparts(*sup), [AMB, CHR], coll=C_BRK, recalc=True)
col("COL_R2_BreakawayIntact", fc.merge(BM(-BRK_X, BRK_X, -CW, CW, ZB - DECK_T, ZB),
                                       BM(-BRK_X, BRK_X, -CW, -CW + 0.1, ZB, ZB + RAIL_H),
                                       BM(-BRK_X, BRK_X, CW - 0.1, CW, ZB, ZB + RAIL_H)))
col("COL_R2_BreakawayBroken", fc.merge(BM(-BRK_X, -BRK_X + 0.4, -CW, CW, ZB - DECK_T, ZB),
                                       BM(BRK_X - 0.4, BRK_X, -CW, CW, ZB - DECK_T, ZB)))
bpy.data.objects["COL_R2_BreakawayBroken-colonly"]["state"] = "broken"
bpy.data.objects["COL_R2_BreakawayIntact-colonly"]["state"] = "intact"

# ================================================================== root bridge (alternate route), 3.2 m deck + edge root strands
deck = fc.slab_grid([-12.0, -6.0, 0.0, 6.0, 12.0], [RB_Y0, RB_Y0 + 0.32, RB_Y1 - 0.32, RB_Y1], lambda x, y: -0.5,
                    lambda x, y: 0.0 if RB_Y0 + 0.32 - 1e-6 <= y <= RB_Y1 - 0.32 + 1e-6 else -0.1,
                    lambda i, j: 0 if j == 1 else 1, side_mat=0)
mkm("MOD_V_RootBridge", deck, [BARK, MOSS], coll=C_ROOT, recalc=True)
strands, hulls = [], []
for y in (RB_Y0, RB_Y1):
    path = [(-12.6, y, 0.25)] + [(x, y + 0.08 * math.sin(x), 0.35) for x in (-9.0, -4.0, 0.0, 4.0, 9.0)] + [(12.6, y, 0.25)]
    v, f, rings = vk.tube(path, [0.3, 0.33, 0.32, 0.34, 0.32, 0.33, 0.3], seed=int(y * 10), jitter=0.08,
                          return_rings=True)
    strands.append((v, f, [0] * len(f)))
    hulls += vk.hull_points([a + b for a, b in zip(rings, rings[1:])])
for x in (-7.0, 0.0, 7.0):                                     # support roots diving to the north wall
    v, f, rings = vk.tube([(x, RB_Y1 - 0.4, -0.4), (x + 0.4, 6.6, -2.2), (x + 0.6, 7.6, -5.0)], [0.4, 0.33, 0.25],
                          seed=int(x + 50), return_rings=True)
    strands.append((v, f, [0] * len(f)))
for (x0, x1) in ((-12.0, 0.0), (0.0, 12.0)):                    # sagging under-roots
    xm = (x0 + x1) / 2
    v, f = vk.tube([(x0, 4.0, -0.4), (xm, 4.2, -1.3), (x1, 4.0, -0.4)], [0.45, 0.5, 0.45], seed=int(xm + 9))
    strands.append((v, f, [0] * len(f)))
mkm("SM_R2_RootBridge_Roots", fc.mparts(*strands), [BARK], coll=C_ROOT, recalc=True)
col("COL_R2_RootBridge", fc.slab_grid([-12.0, 12.0], [RB_Y0, RB_Y1], -0.5, lambda x, y: 0.0)[:2])
col("COL_R2_RootBridgeStrands", fc.merge(*hulls))

# ================================================================== chasm bays (5 x 8 m, both sides), end walls, floor, roof
def bay_wall():
    w = 4.0
    zs = [ZF, -12.1, -11.9, -1.1, -0.9, ZR]
    pts, faces, mats = fc.grid2d([-w, w], zs, lambda i, j: True, lambda i, j: 2 if j in (1, 3) else 1)
    wall = fc.extrude2d(pts, faces, mats, WT, 0.0)
    pipes = [fc.xform(fc.lathe([(0, 0), (0.28, 0), (0.28, ZR - ZF), (0, ZR - ZF)], 8), offset=(x, -0.35, ZF))
             for x in (-2.6, 2.6)]
    collars = [fc.xform(fc.lathe([(0.28, 0), (0.36, 0), (0.36, 0.3), (0.28, 0.3)], 8, closed=True), offset=(x, -0.35, z))
               for x in (-2.6, 2.6) for z in (-18.0, -6.0, 6.0)]
    return fc.mparts(wall, *[(p[0], p[1], [0] * len(p[1])) for p in pipes],
                     *[(c[0], c[1], [0] * len(c[1])) for c in collars])


me_bay = module("MOD_R_ChasmBay", bay_wall(), [SIL, CHR, CYN], recalc=True)
for i, x in enumerate((-16.0, -8.0, 0.0, 8.0, 16.0)):
    place(f"SM_R2_Bay_N{i}", me_bay, (x, HY, 0.0), 0)
    place(f"SM_R2_Bay_S{i}", me_bay, (x, -HY, 0.0), 180)
cols["walls"] = [BM(-HX - WT, HX + WT, HY, HY + WT, ZF, ZR), BM(-HX - WT, HX + WT, -HY - WT, -HY, ZF, ZR)]


def end_wall(hole):
    y0, y1, z0, z1 = hole
    pts, faces, mats = fc.grid2d([-HY, y0, y1, HY], [ZF, z0, z1, ZR], lambda i, j: not (i == 1 and j == 1),
                                 lambda i, j: 1)
    return fc.extrude2d(pts, faces, mats, WT, 0.0)


for side, x, hole, rz in (("W", -HX, ENTRY, 90), ("E", HX + WT, EXIT, 90)):
    mkm(f"SM_R2_EndWall_{side}", fc.xform(end_wall(hole), rot_z=rz, offset=(x if side == "W" else x, 0, 0)),
        [SIL, CHR], recalc=True)
    xs = (-HX - WT, -HX) if side == "W" else (HX, HX + WT)
    cols["walls"] += [BM(*xs, -HY, hole[0], ZF, ZR), BM(*xs, hole[1], HY, ZF, ZR), BM(*xs, hole[0], hole[1], hole[3], ZR),
                      BM(*xs, hole[0], hole[1], ZF, hole[2])]
# blast-door frames (amber/black) on both openings + corridor stubs
def hazard_frame(ow, oh, jamb, head, depth, band=0.4):
    w = ow / 2
    xs_ = sorted({-w - jamb, -w, w, w + jamb} | {-w + k * band for k in range(int(ow / band) + 1)})
    zs_ = sorted({0.0, oh, oh + head} | {k * band for k in range(int(oh / band) + 1)})
    xs_ = [x for x in xs_ if -w - jamb <= x <= w + jamb]
    zs_ = [z for z in zs_ if z <= oh + head]

    def filled(i, j):
        cx, cz = (xs_[i] + xs_[i + 1]) / 2, (zs_[j] + zs_[j + 1]) / 2
        return not (abs(cx) < w and cz < oh)

    def mat(i, j):
        cx, cz = (xs_[i] + xs_[i + 1]) / 2, (zs_[j] + zs_[j + 1]) / 2
        return int((cz if abs(cx) > w else cx + w) / band) % 2
    pts, faces, mats = fc.grid2d(xs_, zs_, filled, mat)
    return fc.extrude2d(pts, faces, mats, depth, -depth, back=False, side_mat=0)


me_f4 = module("MOD_R_BlastDoor_Frame", hazard_frame(4.0, 4.0, 0.5, 0.6, 0.4), [AMB, CHR])
me_f6 = module("MOD_R_BlastDoor_Frame_6x5", hazard_frame(6.0, 5.0, 0.5, 0.6, 0.4), [AMB, CHR])
place("SM_R2_DoorFrame_FromR1", me_f4, (-HX, 0.0, 0.0), 90)
place("SM_R2_DoorFrame_ToR3", me_f6, (HX, 0.0, 0.0), -90)
mk("SM_R2_DoorStubs", fc.merge(*[(v, [tuple(reversed(q)) for q in f]) for v, f in (
    BM(-HX - WT - 4.0, -HX - WT, ENTRY[0], ENTRY[1], ZA - DECK_T, ENTRY[3], skip=("right",)),
    BM(HX + WT, HX + WT + 4.0, EXIT[0], EXIT[1], ZA - DECK_T, EXIT[3], skip=("left",)))]), [CHR], recalc=False)
mk("SM_R2_ChasmFloor", BM(-HX, HX, -HY, HY, ZF - 0.5, ZF), [CHR])
roof = fc.merge(BM(-HX - WT, HX + WT, -HY - WT, -5.0, ZR, ZR + 0.6), BM(-HX - WT, HX + WT, 5.0, HY + WT, ZR, ZR + 0.6),
                BM(-HX - WT, -16.0, -5.0, 5.0, ZR, ZR + 0.6), BM(16.0, HX + WT, -5.0, 5.0, ZR, ZR + 0.6))
mk("SM_R2_Roof", roof, [CHR])

# ================================================================== turbines (housings in the south wall, rotors spin on local Y)
def housing():
    """Axis along Y. Local y=0 is the open front (faces the chasm, +Y); y=-3 is the back plate at the wall."""
    shell = fc.xform(fc.lathe([(3.6, 0), (4.0, 0), (4.0, 3.0), (3.6, 3.0)], 16, closed=True), rot_x=90)
    lip = fc.xform(fc.lathe([(3.6, -0.05), (3.75, -0.05), (3.75, 0.15), (3.6, 0.15)], 16, closed=True), rot_x=90)
    back = fc.xform(fc.cylinder_data(3.6, 0.2, 16), rot_x=90, offset=(0, -2.8, 0))
    hub_mount = fc.xform(fc.cylinder_data(0.9, 1.4, 8), rot_x=90, offset=(0, -1.6, 0))
    return fc.mparts((*shell, [0] * len(shell[1])), (*lip, [2] * len(lip[1])), (*back, [1] * len(back[1])),
                     (*hub_mount, [1] * len(hub_mount[1])))


def rotor():
    hub = fc.xform(fc.cylinder_data(0.7, 0.8, 8), rot_x=90, offset=(0, 0.4, 0))
    p = [(*hub, [0] * len(hub[1]))]
    for k in range(6):
        b = fc.xform(BM(0.6, 3.4, -0.08, 0.08, -0.35, 0.35), rot_x=18)
        b = fc.xform(b, rot_y=60 * k)
        p.append((*b, [1] * 6))
    p.append((*fc.xform(fc.cylinder_data(0.25, 0.1, 8), rot_x=90, offset=(0, 0.5, 0)), [2] * 24))   # cyan nose cap (front)
    return fc.mparts(*p)


me_house = module("MOD_R_TurbineHousing", housing(), [CHR, SIL, CYN], recalc=True)
me_rotor = module("MOD_R_TurbineRotor", rotor(), [CHR, SIL, CYN], recalc=True)
for i, (x, z) in enumerate(TURB):
    place(f"SM_R2_TurbineHousing_{i + 1}", me_house, (x, -HY + 3.0, z), 0)       # shell spans y -8..-5
    r = place(f"SM_TurbineRotor_{i + 1}", me_rotor, (x, -HY + 1.6, z), 0)       # origin on the axis
    r["rotate_axis"] = "local Y"
cols["walls"] += [fc.xform(fc.cylinder_data(4.0, 3.0, 12), rot_x=90, offset=(x, -HY + 3.0, z)) for x, z in TURB]

# ================================================================== sparse moss + vines on the upper walls
me_vine = {L: module(f"MOD_V_VineCard_{L:g}m", vk.vine_card(L), [MOSS]) for L in (3.0, 4.5)}
vr = random.Random(5)
for i in range(10):
    x = vr.uniform(-15, 15)
    y = vr.choice((-HY + 0.05, HY - 0.05, -5.0, 5.0))
    z = ZR - 0.05 if abs(y) == 5.0 else vr.uniform(9.0, 13.0)
    place(f"SM_R2_Vine_{i:02d}", me_vine[3.0 if i % 2 else 4.5], (x, y, z), 0)
me_moss = module("SM_Moss_Patch_01", vk.moss_patch(3, 1.4), [MOSS])
for i, (x, y) in enumerate(((-12, -3), (-3, 4), (6, -2), (13, 3))):
    place(f"SM_R2_FloorMoss_{i}", me_moss, (x, y, ZF), 40 * i)

# ================================================================== collision + kill volume
col("COL_R2_Decks", fc.merge(*cols["decks"]))
col("COL_R2_Rails", fc.merge(*cols["rails"]))
col("COL_R2_Walls", fc.merge(*cols["walls"]))
col("COL_R2_ChasmFloor", BM(-HX, HX, -HY, HY, ZF - 0.5, ZF))
v = col("VOL_ChasmFall", BM(-HX, HX, -HY, HY, ZF, KILL_Z))
v["gameplay"] = "kill volume (fall). Godot imports -colonly as StaticBody: convert to Area3D in the import script."

# ================================================================== landmarks
SX = STAIR_TOP_X
landmarks = {"LM_R2_FromR1": (-HX, 0.0, ZA), "LM_R2_ToR3": (HX, 0.0, ZA),
             "LM_R2_StairDown_Top": (-SX, 0.0, ZA), "LM_R2_StairDown_Foot": (-SX + RUN, 0.0, ZB),
             "LM_R2_Breakaway": (0.0, 0.0, ZB), "LM_R2_StairUp_Foot": (SX - RUN, 0.0, ZB), "LM_R2_StairUp_Top": (SX, 0.0, ZA),
             "LM_R2_RootBridge_W": (-12.0, (RB_Y0 + RB_Y1) / 2, ZA), "LM_R2_RootBridge_E": (12.0, (RB_Y0 + RB_Y1) / 2, ZA),
             "LM_R2_Turbine_1": (TURB[0][0], -HY + 1.6, TURB[0][1]), "LM_R2_Turbine_2": (TURB[1][0], -HY + 1.6, TURB[1][1])}
for n, p in landmarks.items():
    fc.empty(n, p, C_LM, 0.8, "ARROWS").hide_render = True

# ================================================================== presentation + renders
fc.ref_player(C_REF, (-13.5, 3.8, 0))
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


cam_top = cam("CAM_TopDown", (0, 0, 60), ortho=44)
cam_eye = cam("CAM_EyeHeight", (-19.0, -0.6, 1.7), target=(0.0, 1.5, -3.0))
sun_d = bpy.data.lights.new("LGT_Key_6500K", "SUN")
sun_d.energy = 3.0
sun = bpy.data.objects.new("LGT_Key_6500K", sun_d)
sun.rotation_euler = (math.radians(18), 0, math.radians(15))
C_PRES.objects.link(sun)
sc.world.use_nodes = True
bg = sc.world.node_tree.nodes.get("Background")
bg.inputs[0].default_value = fc.hex_lin("#C9D6E3")
bg.inputs[1].default_value = 0.6
ref = bpy.data.objects["REF_Player"]
ref.hide_render = False
renders = {}
bpy.data.objects["SM_R2_Roof"].hide_render = True
sc.camera = cam_top
renders["topdown"] = fc.render(os.path.join(fc.RENDER_DIR, "R2_blockout_topdown.png"), engine="BLENDER_EEVEE")
bpy.data.objects["SM_R2_Roof"].hide_render = False
sc.camera = cam_eye
renders["eye"] = fc.render(os.path.join(fc.RENDER_DIR, "R2_blockout_eyeheight.png"), engine="BLENDER_EEVEE")
ref.hide_render = True

_, uniq, inst = fc.tri_report([C_EXP])
report = {
    "space": dict(x=[-HX, HX], y=[-HY, HY], catwalk_z=ZA, level_b_z=ZB, chasm_floor_z=ZF, roof_z=ZR, bays="5 x 8 m"),
    "primary_route": dict(width=2 * CW, entry_catwalks="x -20..-12", stair_down=f"x -12..{-SX + RUN} (z 0 -> -4)",
                          landing_w=f"x {-SX + RUN}..-4", breakaway="x -4..4 at z -4", landing_e=f"x 4..{SX - RUN}",
                          stair_up=f"x {SX - RUN}..12", exit_catwalks="x 12..20",
                          stairs=dict(risers=RISERS, rise=round(RISE, 4), tread=TREAD, run=RUN,
                                      slope_deg=round(math.degrees(math.atan2(RISE, TREAD)), 1))),
    "root_bridge": dict(x=[-12, 12], y=[RB_Y0, RB_Y1], z=ZA, deck_width=RB_Y1 - RB_Y0,
                        flat_clear_between_strands=round(RB_Y1 - RB_Y0 - 2 * 0.33, 2)),
    "turbines": [dict(centre=[x, -HY + 1.6, z], diameter=8, axis="Y") for x, z in TURB],
    "doors": dict(from_R1=dict(at=[-HX, 0, 0], w=4, h=4), to_R3=dict(at=[HX, 0, 0], w=6, h=5)),
    "kill_volume_top_z": KILL_Z,
    "R1_join": "translate R2 so LM_R2_FromR1 meets LM_R1_ToR2: R2 offset = R1 + (32, -3, 0) for a wall-to-wall join "
               "(each room also carries its own 4 m door stub).",
    "landmarks": {k: [round(c, 3) for c in v] for k, v in landmarks.items()},
    "tris_export_unique": uniq, "tris_export_instanced": inst, "budget": 150000, "renders": renders,
}
blend = os.path.join(fc.SOURCE_DIR, "Fractured_R2_TurbineChasm.blend")
fc.save(blend)
report["blend"] = blend
with open(os.path.join(fc.RENDER_DIR, "R2_blockout_report.json"), "w") as fh:
    json.dump(report, fh, indent=2)
print("R2 BLOCKOUT DONE tris", uniq, inst)
