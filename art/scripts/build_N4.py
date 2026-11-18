"""N4 Nova Canal Market — DETAIL stage + Block Z QA + export (layout approved at blockout, build_N4_blockout.py).
Interior X -18..18 (along the canal), Y -10..10. Banks z=0, canal floor z=-2, water z=-0.8.
North bank = +Y, south bank = -Y. Loading entrance at the +X end of the south bank; pedestrian entrance at the
-X end of the north bank. Barrel vault: walls to z=8, 14.5 m-radius arc to the 12 m apex (N2 rib/bay modules, -2 m).
Run: blender -b --factory-startup -P art/scripts/build_N4.py
"""
import os
import sys
import math
import json
import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(__file__))
import fractured_common as fc
import fractured_qa as qa
import nova_kit as nk

ID, NAME = "N4", "CanalMarket"
sc = fc.reset_scene()
M = fc.append_shared_materials()
SIL, GLS, CYN, CHR, AMB, BARK, WAT = (M[k] for k in ("M_NovaSilver", "M_NovaGlass", "M_CyanEmissive", "M_Charcoal",
                                                    "M_AmberWarning", "M_Bark", "M_Water"))
C_EXP = fc.collection(f"{ID}_Export")
C_ROOF = fc.collection(f"{ID}_Roof", C_EXP)
C_MKT = fc.collection(f"{ID}_Market", C_EXP)
C_COL = fc.collection(f"{ID}_Collision")
C_FX = fc.collection(f"{ID}_FX")
C_PRES = fc.collection(f"{ID}_Presentation")
C_REF = fc.collection("_Reference")
C_LM = fc.collection(f"{ID}_Landmarks")
C_MOD = fc.collection(f"{ID}_ModuleSources")
BM = fc.box_minmax

# ------------------------------------------------------------------ dimensions
HX, HY, WT = 18.0, 10.0, 0.3
CW, CZ, WZ = 2.5, -2.0, -0.8                  # canal half-width, canal floor, water surface
SPRING, APEX = 8.0, 12.0
VR = (HY ** 2 + (APEX - SPRING) ** 2) / (2 * (APEX - SPRING))   # 14.5 (same arc as N2)
VZC = APEX - VR
VA = math.asin(HY / VR)
CURB_H, CURB_W = 0.3, 0.3
BOLL_Y = CW + CURB_W + 0.3                    # bollard line
LANE = (CW + CURB_W + 0.5, CW + CURB_W + 3.5)  # 3 m clear promenade band (|y|)
SHOP_XS = (-8.0, 4.0)                         # shop fronts on the 4 m wall grid (both banks)
SHOP_OPEN = (3.0, 3.0)                        # opening w x h
SHUTTER_Z = 2.2                               # half-raised shutter bottom
STALL_XS = (-13.5, -2.0, 9.5)
STALL_W, STALL_D = 3.0, 2.0
STALL_Y = HY - 0.6 - STALL_D / 2              # stall centre |y| (back 0.6 m off the wall)
BR_W, BR_HALF, BR_RISE = 3.0, 4.0, 0.6        # bridge width, half-length along Y, arch rise
ST_RISERS, ST_TREAD = 11, 0.30
ST_RISE = -CZ / ST_RISERS
ST_RUN = (ST_RISERS - 1) * ST_TREAD           # 3.0
LOADING = (-9.2, -3.2, 0.0, 5.0)              # y0, y1, z0, z1 on the +X wall (jambs clear the curb + canal edge)
ENTRANCE = (4.5, 8.5, 0.0, 4.0)               # y0, y1, z0, z1 on the -X wall
CULVERT = (-CW, CW, CZ, 1.0)


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


def inward(v, f, mats=0):
    return v, [tuple(reversed(q)) for q in f], [mats] * len(f)


XS = [-16.0 + 4 * i for i in range(9)]

# ================================================================== banks (floor tiles; edge row is 2 m deep = canal wall), canal floor
ev, ef, em = nk.floor_tile(4, 1.5, t=-CZ)
ev = [(x, y + 0.75, z) for x, y, z in ev]                 # origin on the canal edge (grid line) -> local y 0..1.5
t_edge = module("MOD_N_Floor_CanalEdge_4x1.5", (ev, ef, em), [SIL, CHR])
t_mid = module("MOD_N_Floor_4x2", nk.floor_tile(4, 2), [SIL, CHR])
t_back = module("MOD_N_Floor_4x4", nk.floor_tile(4, 4), [SIL, CHR])
t_canal = module("MOD_N_Floor_Canal_4x5", nk.floor_tile(4, 5, b=0.08), [CHR, SIL])
for x in XS:
    for s in (1, -1):
        b = "N" if s > 0 else "S"
        place(f"SM_N4_Bank_{b}_{int(x + 16) // 4}_edge", t_edge, (x, s * CW, CZ), 0 if s > 0 else 180)
        place(f"SM_N4_Bank_{b}_{int(x + 16) // 4}_mid", t_mid, (x, s * (CW + 1.5 + 1.0), -0.2))
        place(f"SM_N4_Bank_{b}_{int(x + 16) // 4}_back", t_back, (x, s * (CW + 3.5 + 2.0), -0.2))
    place(f"SM_N4_CanalFloor_{int(x + 16) // 4}", t_canal, (x, 0.0, CZ - 0.2))
col("COL_N4_Banks", fc.merge(BM(-HX, HX, CW, HY, CZ, 0.0), BM(-HX, HX, -HY, -CW, CZ, 0.0)))
col("COL_N4_CanalFloor", BM(-HX, HX, -CW, CW, CZ - 0.3, CZ))
water = ([(-HX - 4.3, -CW, 0), (HX + 4.3, -CW, 0), (HX + 4.3, CW, 0), (-HX - 4.3, CW, 0)], [(0, 1, 2, 3)], [0])
mkm("SM_Canal_Water", water, [WAT], loc=(0, 0, WZ))

# curbs (0.3 m) with gaps at the bridge and the canal-stair exits; low cyan bollards
curb4 = module("MOD_N_Curb_4m", fc.mparts((*BM(-2, 2, -CURB_W / 2, CURB_W / 2, 0, CURB_H), 0),
                                          (*BM(-2, 2, -CURB_W / 2 - 0.01, -CURB_W / 2, 0.18, 0.24), 1)), [CHR, CYN])
curb1 = module("MOD_N_Curb_1m", fc.mparts((*BM(-0.5, 0.5, -CURB_W / 2, CURB_W / 2, 0, CURB_H), 0),
                                          (*BM(-0.5, 0.5, -CURB_W / 2 - 0.01, -CURB_W / 2, 0.18, 0.24), 1)), [CHR, CYN])
curb05 = module("MOD_N_Curb_0.5m", fc.mparts((*BM(-0.25, 0.25, -CURB_W / 2, CURB_W / 2, 0, CURB_H), 0),
                                             (*BM(-0.25, 0.25, -CURB_W / 2 - 0.01, -CURB_W / 2, 0.18, 0.24), 1)), [CHR, CYN])
CSTAIR = {"N": (11.0, 1), "S": (-11.0, -1)}   # canal stair top x, direction (+1: rises toward +X)
curbs_col = []
for b, s in (("N", 1), ("S", -1)):
    cy = s * (CW + CURB_W / 2)
    rz = 0 if s > 0 else 180
    gx = CSTAIR[b][0] + CSTAIR[b][1] * 1.0          # stair landing centre x (exit gap 2 m wide)
    for i, x in enumerate(XS):
        if x == 0.0:
            for dx in (-1.75, 1.75):
                place(f"SM_N4_Curb_{b}_{i}_{'a' if dx < 0 else 'b'}", curb05, (x + dx, cy, 0), rz)
                curbs_col.append(BM(x + dx - 0.25, x + dx + 0.25, cy - CURB_W / 2, cy + CURB_W / 2, 0, CURB_H))
        elif abs(x - gx) < 2.0:
            for dx in (-1.5, 1.5):
                place(f"SM_N4_Curb_{b}_{i}_{'a' if dx < 0 else 'b'}", curb1, (x + dx, cy, 0), rz)
                curbs_col.append(BM(x + dx - 0.5, x + dx + 0.5, cy - CURB_W / 2, cy + CURB_W / 2, 0, CURB_H))
        else:
            place(f"SM_N4_Curb_{b}_{i}", curb4, (x, cy, 0), rz)
            curbs_col.append(BM(x - 2, x + 2, cy - CURB_W / 2, cy + CURB_W / 2, 0, CURB_H))
col("COL_N4_Curbs", fc.merge(*curbs_col))
boll = module("MOD_N_Bollard", fc.mparts(fc.prism(nk.ngon(6, 0.14), 0.0, 0.75, cap_mat=0),
                                         fc.prism(nk.ngon(6, 0.15), 0.75, 0.9, cap_mat=1)), [CHR, CYN])
bolls = []
for b, s in (("N", 1), ("S", -1)):
    for x in XS:
        if x == 0.0 or abs(x - (CSTAIR[b][0] + CSTAIR[b][1] * 1.0)) < 1.6:
            continue
        place(f"SM_N4_Bollard_{b}_{int(x + 16) // 4}", boll, (x, s * BOLL_Y, 0))
        bolls.append(BM(x - 0.15, x + 0.15, s * BOLL_Y - 0.15, s * BOLL_Y + 0.15, 0, 0.9))
col("COL_N4_Bollards", fc.merge(*bolls))

# canal stairs (one per bank, along the canal wall, 1.5 m wide) + exit landing
me_cst = module("MOD_N_CanalStair_1.5m", nk.stair(1.5, ST_RISERS, ST_RISE, ST_TREAD), [SIL, CHR])
cramp = nk.stair_ramp(1.5, ST_RISERS, ST_RISE, ST_TREAD)
for b, s in (("N", 1), ("S", -1)):
    top_x, d = CSTAIR[b]
    y = s * (CW - 0.75)
    rz = -90 if d > 0 else 90                     # local +Y (climb) -> +X or -X
    place(f"SM_N4_CanalStair_{b}", me_cst, (top_x, y, CZ), rz)
    col(f"COL_N4_CanalStair_{b}", fc.xform(cramp, rot_z=rz, offset=(top_x, y, CZ)))
    lx0, lx1 = sorted((top_x, top_x + d * 2.0))
    mk(f"SM_N4_CanalStairLanding_{b}", BM(lx0, lx1, min(y - 0.75 * s, y + 0.75 * s), max(y - 0.75 * s, y + 0.75 * s),
                                          CZ, 0.0), [SIL])
    col(f"COL_N4_CanalStairLanding_{b}", BM(lx0, lx1, min(y - 0.75 * s, y + 0.75 * s), max(y - 0.75 * s, y + 0.75 * s),
                                            CZ, 0.0))

# ================================================================== arched footbridge (mid-canal, 3 m wide)
arch = lambda y: BR_RISE * max(0.0, 1 - (y / BR_HALF) ** 2)
ys = [-BR_HALF + 2 * BR_HALF * k / 10 for k in range(11)]
deck = fc.slab_grid([-BR_W / 2 + 0.15, BR_W / 2 - 0.15], ys, lambda x, y: arch(y) - 0.3, lambda x, y: arch(y) + 0.02,
                    side_mat=0)
para, caps, strips = [], [], []
for x0 in (-BR_W / 2, BR_W / 2 - 0.15):
    para.append(fc.slab_grid([x0, x0 + 0.15], ys, lambda x, y: arch(y) - 0.3, lambda x, y: arch(y) + 1.0,
                             lambda i, j: 0, side_mat=0))
    caps.append(fc.slab_grid([x0 - 0.03, x0 + 0.18], ys, lambda x, y: arch(y) + 1.0, lambda x, y: arch(y) + 1.1,
                             lambda i, j: 1, side_mat=1))
    xs_ = [x0 - 0.02, x0] if x0 < 0 else [x0 + 0.15, x0 + 0.17]
    strips.append(fc.slab_grid(xs_, ys, lambda x, y: arch(y) - 0.24, lambda x, y: arch(y) - 0.16,
                               lambda i, j: 2, side_mat=2))
mkm("SM_N4_Bridge", fc.mparts(deck, *para, *caps, *strips), [SIL, CHR, CYN], recalc=True)
col("COL_N4_Bridge", fc.slab_grid([-BR_W / 2 + 0.15, BR_W / 2 - 0.15], ys, lambda x, y: arch(y) - 0.3,
                                  lambda x, y: arch(y) + 0.02)[:2])
col("COL_N4_BridgeRail", fc.merge(*[p[:2] for p in para]))

# ================================================================== walls: side walls with shop openings; end walls with openings
W_MATS = [SIL, CHR, CYN]
w4 = module("MOD_N_Wall_4x4", nk.wall_panel(4), W_MATS)
w4s = module("MOD_N_Wall_4x4_Seam", nk.wall_panel(4, seam=True), W_MATS)
w4top = module("MOD_N_Wall_4x4_Top", nk.wall_panel(4, band=False, top_strip=True), W_MATS)
w4shop = module("MOD_N_Wall_4x4_Shop", nk.wall_panel(4, hole=(-1.5, 1.5, 0.0, 3.0)), W_MATS)
for side, y, rz in (("N", HY, 0), ("S", -HY, 180)):
    for i, x in enumerate(XS):
        for r, z in enumerate((0.0, 4.0)):
            if r == 0:
                me = w4shop if x in SHOP_XS else (w4s if i % 2 else w4)
            else:
                me = w4top
            place(f"SM_N4_Wall_{side}_{i}{r}", me, (x, y, z), rz)
for x in (-18.0, 18.0):
    pass                                          # 2 m end strips handled by the end-wall meshes' side returns


def end_wall(holes):
    ys_ = sorted({-HY, -CW, CW, HY} | {h[0] for h in holes} | {h[1] for h in holes})
    zs_ = sorted({CZ, 0.0, SPRING} | {h[2] for h in holes} | {h[3] for h in holes})

    def filled(i, j):
        cy, cz = (ys_[i] + ys_[i + 1]) / 2, (zs_[j] + zs_[j + 1]) / 2
        if cz < 0 and abs(cy) > CW:
            return False
        return not any(h[0] < cy < h[1] and h[2] < cz < h[3] for h in holes)
    pts, faces, mats = fc.grid2d(ys_, zs_, filled)
    base = sorted([k for k, p in enumerate(pts) if abs(p[1] - SPRING) < 1e-6], key=lambda k: pts[k][0])
    arc = []
    for k in range(1, 16):
        a = -VA + 2 * VA * k / 16
        pts.append((VR * math.sin(a), VZC + VR * math.cos(a)))
        arc.append(len(pts) - 1)
    outline = base + arc[::-1]
    apex = arc[7]
    i0 = outline.index(apex)
    ring = outline[i0:] + outline[:i0]
    for a, b in zip(ring[1:-1], ring[2:]):
        faces.append((apex, a, b))
        mats.append(0)
    return fc.extrude2d(pts, faces, mats, WT)


for side, x, holes in (("E", HX + WT, [LOADING, CULVERT]), ("W", -HX, [ENTRANCE, CULVERT])):
    mkm(f"SM_N4_Wall_{side}", fc.xform(end_wall(holes), rot_z=90, offset=(x, 0, 0)), [SIL], recalc=True)
    xs_ = (HX, HX + WT) if side == "E" else (-HX - WT, -HX)
    ys_ = sorted({-HY, HY} | {h[0] for h in holes} | {h[1] for h in holes})
    boxes = []
    for y0, y1 in zip(ys_, ys_[1:]):
        hs = [h for h in holes if h[0] <= y0 and h[1] >= y1]
        if hs:
            boxes.append(BM(*xs_, y0, y1, hs[0][3], SPRING))
            lo = 0.0 if abs((y0 + y1) / 2) > CW else CZ
            if hs[0][2] > lo + 1e-6:                     # only fill below the opening when there is wall there
                boxes.append(BM(*xs_, y0, y1, lo, hs[0][2]))
        else:
            boxes.append(BM(*xs_, y0, y1, CZ if abs((y0 + y1) / 2) < CW else 0.0, SPRING))
    col(f"COL_N4_Wall_{side}", fc.merge(*boxes))
for side, y in (("N", HY), ("S", -HY)):
    y0, y1 = (y, y + WT) if side == "N" else (y - WT, y)
    xs_ = [-HX - WT] + [v for x in SHOP_XS for v in (x - 1.5, x + 1.5)] + [HX + WT]
    boxes = [BM(a, b, y0, y1, 0.0, SPRING) for a, b in zip(xs_[0::2], xs_[1::2])]
    boxes += [BM(x - 1.5, x + 1.5, y0, y1, SHOP_OPEN[1], SPRING) for x in SHOP_XS]
    col(f"COL_N4_Wall_{side}", fc.merge(*boxes))

# loading door (amber/black hazard frame) + corridor stub; pedestrian entrance frame + stub; culvert stubs
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
        k = int((cz if abs(cx) > w else cx + w) / band)
        return k % 2
    pts, faces, mats = fc.grid2d(xs_, zs_, filled, mat)
    return fc.extrude2d(pts, faces, mats, depth, -depth, back=False, side_mat=0)


me_load = module("MOD_N_LoadingDoor", hazard_frame(6.0, 5.0, 0.4, 0.6, 0.35), [AMB, CHR])
place("SM_N4_LoadingDoor", me_load, (HX, (LOADING[0] + LOADING[1]) / 2, 0.0), -90)
mkm("SM_N4_Sign_Loading", nk.sign("LOADING", 0.09), [CHR, CYN],
    loc=(HX - 0.02, (LOADING[0] + LOADING[1]) / 2, LOADING[3] + 0.75), rz=-90)
mkm("SM_N4_Sign_Entrance", nk.sign("< EXIT", 0.08), [CHR, CYN],
    loc=(-HX + 0.02, (ENTRANCE[0] + ENTRANCE[1]) / 2, ENTRANCE[3] + 0.75), rz=90)
me_spr = module("MOD_N_RibSpringer", fc.prism([(-0.3, 0.0), (-0.3, -0.35), (-0.15, -0.5), (0.15, -0.5),
                                               (0.3, -0.35), (0.3, 0.0)], 0.0, 1.0, cap_mat=0), [CHR])
for k_, x in enumerate(range(-14, 15, 4)):
    for y, rz in ((-HY, 180), (HY, 0)):
        place(f"SM_N4_RibSpringer_{k_:02d}{'N' if y > 0 else 'S'}", me_spr, (x, y, SPRING - 1.0), rz)
mkm("SM_N4_LoadingStub", inward(*BM(HX + WT, HX + WT + 4.0, LOADING[0], LOADING[1], 0.0, LOADING[3], skip=("left",)),
                                mats=0), [SIL])
me_df4 = module("MOD_N_DoorFrame_4x4", nk.door_frame(4.0, 4.0, 0.5, 0.6, 0.35), [CHR, CYN])
place("SM_N4_DoorFrame_Entrance", me_df4, (-HX, (ENTRANCE[0] + ENTRANCE[1]) / 2, 0.0), 90)
mkm("SM_N4_EntranceStub", inward(*BM(-HX - WT - 4.0, -HX - WT, ENTRANCE[0], ENTRANCE[1], 0.0, ENTRANCE[3],
                                     skip=("right",))), [SIL])
for side, x0, x1, sk in (("E", HX + WT, HX + WT + 4.0, "left"), ("W", -HX - WT - 4.0, -HX - WT, "right")):
    mkm(f"SM_N4_CulvertStub_{side}", inward(*BM(x0, x1, -CW, CW, CZ, CULVERT[3], skip=(sk,))), [CHR])
col("COL_N4_LoadingStub", fc.merge(BM(HX + WT, HX + WT + 4.0, LOADING[0] - 0.2, LOADING[0], 0.0, LOADING[3]),
                                   BM(HX + WT, HX + WT + 4.0, LOADING[1], LOADING[1] + 0.2, 0.0, LOADING[3]),
                                   BM(HX + WT + 4.0, HX + WT + 4.2, LOADING[0], LOADING[1], 0.0, LOADING[3]),
                                   BM(HX + WT, HX + WT + 4.0, LOADING[0], LOADING[1], -0.2, 0.0)))

# ================================================================== shops: shop front (frame, half-raised shutter, sign) + interior
def shop_front():
    """[charcoal, cyan, silver]. Frame around a 3 x 3 opening, shutter rolled to 2.2 m, roll box, cyan sign strip."""
    fr = nk.door_frame(SHOP_OPEN[0], SHOP_OPEN[1], 0.4, 0.5, 0.25)
    fr = (fr[0], fr[1], [0 if m == 0 else 1 for m in fr[2]])
    sh = [(*BM(-1.5, 1.5, 0.12, 0.18, SHUTTER_Z, SHOP_OPEN[1]), 2)]
    for k in range(4):
        z = SHUTTER_Z + 0.1 + k * 0.18
        sh.append((*BM(-1.5, 1.5, 0.1, 0.12, z, z + 0.03), 0))
    sh += [(*BM(-1.55, 1.55, -0.05, 0.3, SHOP_OPEN[1], SHOP_OPEN[1] + 0.35), 0),
           (*BM(-1.2, 1.2, -0.29, -0.25, SHOP_OPEN[1] + 0.15, SHOP_OPEN[1] + 0.4), 1)]
    return fc.mparts(fr, *sh)


def shop_interior():
    """[silver, charcoal, bark]. 4 x 4 m box (3.2 m), opening at local y=0, shelves on three walls + a few goods crates."""
    v, f = BM(-2.0, 2.0, 0.0, 4.0, 0.0, 3.2, skip=("front",))
    p = [(v, [tuple(reversed(q)) for q in f], [1, 0, 0, 0, 0])]
    for (x0, x1, y0, y1) in ((-2.0, -1.55, 0.4, 3.6), (1.55, 2.0, 0.4, 3.6), (-1.5, 1.5, 3.55, 4.0)):
        p.append((*BM(x0, x1, y0, y1, 0.0, 0.08), 1))
        for h in (0.6, 1.2, 1.8):
            p.append((*BM(x0, x1, y0, y1, h, h + 0.05), 1))                     # charcoal boards read against silver
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            along_x = (x1 - x0) > (y1 - y0)
            for k, off in enumerate((-0.6, 0.35)):
                gx, gy = (cx + off, cy) if along_x else (cx, cy + off)
                p.append((*BM(gx - 0.17, gx + 0.17, gy - 0.15, gy + 0.15, h + 0.05, h + 0.32 - 0.06 * k), 2))
    p += [(*BM(-0.9, -0.3, 2.6, 3.2, 0.0, 0.5), 2), (*BM(0.2, 0.8, 2.8, 3.3, 0.0, 0.45), 2)]
    return fc.mparts(*p)


me_sf = module("MOD_N_ShopFront", shop_front(), [CHR, CYN, SIL])
me_si = module("MOD_N_ShopInterior", shop_interior(), [SIL, CHR, BARK])
shop_col = []
landmarks = {}
for b, s, rz in (("N", 1, 0), ("S", -1, 180)):
    for i, x in enumerate(SHOP_XS):
        place(f"SM_N4_ShopFront_{b}{i + 1}", me_sf, (x, s * HY, 0.0), rz, C_MKT)
        place(f"SM_N4_ShopInterior_{b}{i + 1}", me_si, (x, s * (HY + WT), 0.0), rz, C_MKT)
        landmarks[f"LM_Shop_{b}{i + 1}"] = (x, s * HY, 0.0)
        y0, y1 = sorted((s * (HY + WT), s * (HY + WT + 4.0)))
        shop_col += [BM(x - 2.3, x + 2.3, y0 - 0.3 * (s < 0), y1 + 0.3 * (s > 0), -0.2, 0.0),
                     BM(x - 2.3, x - 2.0, y0, y1, 0.0, 3.2), BM(x + 2.0, x + 2.3, y0, y1, 0.0, 3.2),
                     BM(x - 2.0, x + 2.0, *sorted((s * (HY + WT + 4.0), s * (HY + WT + 4.3))), 0.0, 3.2),
                     BM(x - 2.3, x + 2.3, y0, y1, 3.2, 3.4)]
col("COL_N4_Shops", fc.merge(*shop_col))

# ================================================================== stalls (separate part objects, shared modules)
def stall_counter():
    return fc.mparts((*BM(-1.2, 1.2, -0.4, 0.4, 0.0, 0.95), 0), (*BM(-1.25, 1.25, -0.45, 0.45, 0.95, 1.02), 1),
                     (*BM(-1.1, 1.1, -0.42, -0.4, 0.75, 0.82), 2))


def stall_frame():
    p = []
    for x in (-1.45, 1.45):
        p.append((*BM(x - 0.05, x + 0.05, -0.95, -0.85, 0.0, 2.75), 0))
        p.append((*BM(x - 0.05, x + 0.05, 0.85, 0.95, 0.0, 3.1), 0))
        p.append((*fc.sheared_box(x - 0.05, x + 0.05, -0.95, 2.7, 0.95, 3.05, 0.06), 0))
    p.append((*BM(-1.5, 1.5, -0.95, -0.85, 2.69, 2.75), 0))
    return fc.mparts(*p)


def stall_awning(n=8):
    """[amber, silver] stripes sloping from the back (3.13 m) to the front overhang (2.72 m, clears 2.5 m headroom)."""
    p = []
    for k in range(n):
        x0 = -1.6 + 3.2 * k / n
        x1 = -1.6 + 3.2 * (k + 1) / n
        p.append((*fc.sheared_box(x0, x1, -1.25, 2.72, 1.0, 3.13, 0.04), k % 2))
    return fc.mparts(*p)


def stall_shelf():
    p = [(*BM(-1.2, 1.2, 0.5, 0.85, 0.0, 0.06), 0)]
    for h in (0.5, 1.0, 1.5):
        p.append((*BM(-1.2, 1.2, 0.5, 0.85, h, h + 0.04), 0))
    for x in (-1.2, 1.16):
        p.append((*BM(x, x + 0.04, 0.5, 0.85, 0.06, 1.54), 1))
    return fc.mparts(*p)


me_ct = module("MOD_N_Stall_Counter", stall_counter(), [SIL, CHR, CYN])
me_fr = module("MOD_N_Stall_AwningFrame", stall_frame(), [CHR])
me_aw = module("MOD_N_Stall_AwningCloth", stall_awning(), [AMB, SIL])
me_sh = module("MOD_N_Stall_Shelf", stall_shelf(), [SIL, CHR])
me_cr = module("MOD_N_Stall_Crate", fc.mparts((*BM(-0.3, 0.3, -0.2, 0.2, 0.0, 0.4), 0)), [BARK])
stall_col = []
for b, s, rz in (("N", 1, 0), ("S", -1, 180)):
    for i, x in enumerate(STALL_XS):
        base = f"SM_N4_Stall_{b}{i + 1}"
        y = s * STALL_Y
        place(f"{base}_Counter", me_ct, (x, y - s * 0.55, 0), rz, C_MKT)
        place(f"{base}_AwningFrame", me_fr, (x, y, 0), rz, C_MKT)
        place(f"{base}_AwningCloth", me_aw, (x, y, 0), rz, C_MKT)
        place(f"{base}_Shelf", me_sh, (x, y, 0), rz, C_MKT)
        place(f"{base}_Crate_A", me_cr, (x - 0.7, y + s * 0.05, 0), rz + 8, C_MKT)
        place(f"{base}_Crate_B", me_cr, (x - 0.65, y + s * 0.05, 0.4), rz - 5, C_MKT)
        landmarks[f"LM_Stall_{b}{i + 1}"] = (x, y, 0.0)
        y0, y1 = sorted((y - s * 0.95, y + s * 0.95))
        stall_col.append(BM(x - STALL_W / 2, x + STALL_W / 2, y0, y1, 0.0, 1.1))
col("COL_N4_Stalls", fc.merge(*stall_col))

# ================================================================== vault (N2 rib + bay modules, lowered 2 m), springers
def arc_band(r_in, r_out, segs=16):
    pts, faces = [], []
    for k in range(segs + 1):
        a = -VA + 2 * VA * k / segs
        pts.append((r_in * math.sin(a), VZC + 2.0 + r_in * math.cos(a)))
        pts.append((r_out * math.sin(a), VZC + 2.0 + r_out * math.cos(a)))
    for k in range(segs):
        i = 2 * k
        faces.append((i + 2, i, i + 1, i + 3))
    return pts, faces


rp, rf = arc_band(VR - 0.6, VR)
def rib_side(a, b, m):
    r = lambda p: math.hypot(p[0], p[1] - VZC - 2.0)
    return 1 if (abs(r(a) - (VR - 0.6)) < 1e-3 and abs(r(b) - (VR - 0.6)) < 1e-3 and abs(a[0]) < 6.5) else 0


rib = fc.xform(fc.extrude2d(rp, rf, [0] * len(rf), 0.4, -0.2, side_mat=rib_side), rot_z=90)
me_rib = module("MOD_N_RoofRib", rib, [CHR, CYN], recalc=True)                 # identical to N2's module
bp, bf = arc_band(VR, VR + 0.1)
bay = fc.xform(fc.extrude2d(bp, bf, [1 if 5 <= k <= 10 else 0 for k in range(16)], 4.0, -2.0), rot_z=90)
me_bay = module("MOD_N_RoofBay_4m", bay, [SIL, GLS], recalc=True)
for i, x in enumerate(range(-18, 19, 4)):
    place(f"SM_N4_RoofRib_{i:02d}", me_rib, (x, 0, -2.0), coll=C_ROOF)
for i, x in enumerate(XS):
    place(f"SM_N4_RoofBay_{i:02d}", me_bay, (x, 0, -2.0), coll=C_ROOF)

# ================================================================== landmarks
landmarks.update({
    "LM_Canal": (0.0, 0.0, CZ), "LM_Bridge": (0.0, 0.0, 0.0),
    "LM_Bank_N": (0.0, sum(LANE) / 2, 0.0), "LM_Bank_S": (0.0, -sum(LANE) / 2, 0.0),
    "LM_CanalStair_N": (CSTAIR["N"][0], CW - 0.75, CZ), "LM_CanalStair_S": (CSTAIR["S"][0], -(CW - 0.75), CZ),
    "LM_Loading": (HX, (LOADING[0] + LOADING[1]) / 2, 0.0), "LM_Entrance": (-HX, (ENTRANCE[0] + ENTRANCE[1]) / 2, 0.0),
})
for n, p in landmarks.items():
    fc.empty(n, p, C_LM, 0.8, "ARROWS").hide_render = True

# ================================================================== checks: 3 m promenade bands, 2 m stall <-> shop-front gaps
bpy.context.view_layer.update()
lane_hits = {}
for b, s in (("N", 1), ("S", -1)):
    y0, y1 = sorted((s * LANE[0], s * LANE[1]))
    hits = []
    for o in C_EXP.all_objects:
        if o.type != "MESH" or o.name.startswith(("SM_N4_Bank", "SM_N4_Wall", "SM_N4_Roof", "SM_N4_Bridge",
                                                  "SM_N4_CanalFloor", "SM_Canal_Water", "SM_N4_Curb")):
            continue
        bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
        if min(p.z for p in bb) > 2.5 or max(p.z for p in bb) < 0.02 or max(p.x for p in bb) < -HX or min(p.x for p in bb) > HX:
            continue
        if max(p.y for p in bb) > y0 + 1e-4 and min(p.y for p in bb) < y1 - 1e-4:
            hits.append(o.name)
    lane_hits[b] = dict(lane_abs_y=list(LANE), obstacles=hits)
gaps = []
for sx in STALL_XS:
    for hx in SHOP_XS:
        d = abs(sx - hx) - STALL_W / 2 - (SHOP_OPEN[0] / 2 + 0.4)
        gaps.append(round(d, 2))
min_gap = min(gaps)

# ================================================================== presentation + renders
fc.ref_player(C_REF, (-6.0, -5.0, 0))
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


cam_top = cam("CAM_TopDown", (0, 0, 60), ortho=40)
cam_eye = cam("CAM_EyeHeight", (-16.5, -4.6, 1.7), target=(6.0, 1.0, 2.2))
cam_hero = cam("CAM_Hero34", (-15.5, -8.6, 6.2), target=(4.0, 2.0, 1.0), lens=20)
sun_d = bpy.data.lights.new("LGT_Key_6500K", "SUN")
sun_d.energy = 3.5
try:
    sun_d.use_temperature, sun_d.temperature = True, 6500
except Exception:
    sun_d.color = (0.95, 0.97, 1.0)
sun = bpy.data.objects.new("LGT_Key_6500K", sun_d)
sun.rotation_euler = (math.radians(28), 0, math.radians(18))
C_PRES.objects.link(sun)
sc.world.use_nodes = True
bg = sc.world.node_tree.nodes.get("Background")
bg.inputs[0].default_value = fc.hex_lin("#C9D6E3")
bg.inputs[1].default_value = 0.6
renders = {}
C_ROOF.hide_render = True
sc.camera = cam_top
renders["topdown"] = fc.render(os.path.join(fc.RENDER_DIR, "N4_detail_topdown.png"), engine="BLENDER_EEVEE")
C_ROOF.hide_render = False
sc.camera = cam_eye
renders["eye"] = fc.render(os.path.join(fc.RENDER_DIR, "N4_detail_eyeheight.png"), engine="BLENDER_EEVEE")
sc.camera = cam_hero
renders["hero"] = fc.render(os.path.join(fc.RENDER_DIR, "N4_detail_hero34.png"), engine="BLENDER_EEVEE")
cam_shop = cam("CAM_ShopCheck", (-8.0, 9.0, 1.7), target=(-8.0, 13.5, 1.2), lens=18)
sc.camera = cam_shop
renders["shop"] = fc.render(os.path.join(fc.RENDER_DIR, "N4_detail_shop.png"), engine="BLENDER_EEVEE")
sun.hide_render = True
bg.inputs[1].default_value = 1.0
sc.camera = cam_eye
renders["eye_flat_ambient"] = fc.render(os.path.join(fc.RENDER_DIR, "N4_detail_eyeheight_flat.png"), engine="BLENDER_EEVEE")
sun.hide_render = False
bg.inputs[1].default_value = 0.6
sc.camera = cam_hero

_, uniq, inst = fc.tri_report([C_EXP])
report = {
    "footprint_interior_m": [2 * HX, 2 * HY], "vault": dict(spring_z=SPRING, apex_z=APEX, radius=round(VR, 3)),
    "canal": dict(width=2 * CW, floor_z=CZ, water_z=WZ), "banks": dict(width=HY - CW, curb_h=CURB_H, promenade_abs_y=LANE),
    "bridge": dict(width=BR_W, span_y=[-BR_HALF, BR_HALF], rise=BR_RISE,
                   max_slope_deg=round(math.degrees(math.atan(2 * BR_RISE / BR_HALF)), 1)),
    "canal_stairs": dict(width=1.5, risers=ST_RISERS, rise=round(ST_RISE, 4), tread=ST_TREAD, run=ST_RUN,
                         top_x=dict(N=CSTAIR["N"][0], S=CSTAIR["S"][0])),
    "shops": dict(x=SHOP_XS, opening=SHOP_OPEN, shutter_bottom_z=SHUTTER_Z, interior="4 x 4 x 3.2 m"),
    "stalls": dict(x=STALL_XS, w=STALL_W, d=STALL_D, centre_abs_y=STALL_Y),
    "min_stall_to_shopfront_gap_m": min_gap,
    "loading": dict(wall="+X", y=[LOADING[0], LOADING[1]], w=6, h=5, stub="4 m"),
    "entrance": dict(wall="-X", y=[ENTRANCE[0], ENTRANCE[1]], w=4, h=4),
    "promenades_3m": lane_hits,
    "landmarks": {k: [round(c, 3) for c in v] for k, v in landmarks.items()},
    "tris_export_unique": uniq, "tris_export_instanced": inst, "budget": 150000, "renders": renders,
}
blend = os.path.join(fc.SOURCE_DIR, f"Fractured_{ID}_{NAME}.blend")
glb = os.path.join(fc.EXPORT_DIR, f"Fractured_{ID}_{NAME}.glb")
report["qa"] = qa.run(ID, C_EXP, C_COL, C_FX, budget=150000, landmark_coll=C_LM, walk_bounds=(-HX, HX, -HY, HY),
                      # walkways: banks + bridge deck. The canal (floor + exit stairs) is the designed fall-in hazard.
                      walkable_prefixes=("COL_N4_Banks", "COL_N4_Bridge-"),
                      pair_with=os.path.join(fc.RENDER_DIR, "N4_blockout_landmarks.json"),
                      allowed_drop=lambda lo, hi: abs(lo[1]) < CW)          # any drop into the canal (designed hazard)
report["rotations_baked"] = baked
report["blend"] = blend
fc.save(blend)
report["qa"]["export"] = qa.export_and_verify(C_EXP, C_COL, glb)
report["glb"] = glb
with open(os.path.join(fc.RENDER_DIR, "N4_QA_report.json"), "w") as fh:
    json.dump(report, fh, indent=2)
print("N4 DETAIL DONE pass=", report["qa"]["pass"], "lanes=", json.dumps(lane_hits), "min_gap", min_gap)
