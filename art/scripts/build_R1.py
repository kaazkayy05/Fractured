"""R1 Reactor Control Hall — DETAIL stage + Block Z QA + export (layout approved at blockout, build_R1_blockout.py).
Octagonal plan 24 x 18 m (X -12..12, Y -9..9, 3 m chamfered corners), ceiling 8 m.
Front zone (y -9..0) at floor level with the blast doors (transit entry -X, turbine sector +X, both at y=-3).
Three operator tiers (0.5 m steps) rise toward the 16 x 6 m viewing window on the +Y wall; 3 m central aisle with
3-riser steps at each tier edge.
Run: blender -b --factory-startup -P art/scripts/build_R1.py
"""
import os
import sys
import math
import json
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(__file__))
import fractured_common as fc
import fractured_qa as qa
import nova_kit as nk

ID, NAME = "R1", "ReactorControlHall"
sc = fc.reset_scene()
M = fc.append_shared_materials()
SIL, GLS, CYN, CHR, AMB = (M[k] for k in ("M_NovaSilver", "M_NovaGlass", "M_CyanEmissive", "M_Charcoal", "M_AmberWarning"))
C_EXP = fc.collection(f"{ID}_Export")
C_BG = fc.collection(f"{ID}_Backdrop", C_EXP)
C_COL = fc.collection(f"{ID}_Collision")
C_FX = fc.collection(f"{ID}_FX")
C_PRES = fc.collection(f"{ID}_Presentation")
C_REF = fc.collection("_Reference")
C_LM = fc.collection(f"{ID}_Landmarks")
C_MOD = fc.collection(f"{ID}_ModuleSources")
BM = fc.box_minmax

# ------------------------------------------------------------------ dimensions
HX, HY, CH, H, WT = 12.0, 9.0, 3.0, 8.0, 0.3
OCT = [(-HX + CH, -HY), (HX - CH, -HY), (HX, -HY + CH), (HX, HY - CH), (HX - CH, HY), (-HX + CH, HY), (-HX, HY - CH),
       (-HX, -HY + CH)]                                            # CCW, interior
TIER_Y = (0.0, 3.0, 6.0)                                           # tier front edges
TIER_Z = (0.5, 1.0, 1.5)
AISLE = 1.5                                                        # half width (3 m aisle)
STEP_R, STEP_T = 0.5 / 3, 0.30                                     # 3 risers per tier edge
DOOR_Y, DOOR_W, DOOR_H = -3.0, 4.0, 4.0
WIN_X, WIN_Z0, WIN_Z1 = 8.0, 1.5, 7.5                              # window half width, sill, head
DESK_W, DESK_D, DESK_H = 2.4, 0.8, 1.1
DESKS = {0: (3.5, 6.5, 9.5), 1: (3.5, 6.5, 9.5), 2: (3.5, 6.5)}   # |x| per tier
DESK_Y = (2.3, 5.3, 6.95)
STRUTS = (-9.2, -5.0, 5.0, 9.2)


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


def clip_y(poly, ymin, ymax):
    """Clip a convex CCW polygon to ymin <= y <= ymax."""
    def half(p, keep):
        out = []
        for i in range(len(p)):
            a, b = p[i], p[(i + 1) % len(p)]
            ka, kb = keep(a), keep(b)
            if ka:
                out.append(a)
            if ka != kb:
                yc = ymin if (a[1] < ymin) != (b[1] < ymin) else ymax
                t = (yc - a[1]) / (b[1] - a[1])
                out.append((a[0] + t * (b[0] - a[0]), yc))
        return out
    p = half(poly, lambda q: q[1] >= ymin - 1e-9)
    p = half(p, lambda q: q[1] <= ymax + 1e-9)
    out = []                                                       # drop duplicate points (clip at a vertex)
    for q in p:
        if not out or math.hypot(q[0] - out[-1][0], q[1] - out[-1][1]) > 1e-6:
            out.append(q)
    if len(out) > 1 and math.hypot(out[0][0] - out[-1][0], out[0][1] - out[-1][1]) < 1e-6:
        out.pop()
    return out


# ================================================================== floor, tiers, ceiling
mkm("SM_R1_Floor", fc.prism(clip_y(OCT, -HY, TIER_Y[0]), -0.2, 0.0), [SIL])
tier_bounds = list(zip(TIER_Y, list(TIER_Y[1:]) + [HY]))
for k, ((y0, y1), z) in enumerate(zip(tier_bounds, TIER_Z)):
    poly = clip_y(OCT, y0, y1)
    mkm(f"SM_R1_Tier_{k + 1}", fc.prism(poly, -0.2, z, cap_mat=0), [SIL])
    col(f"COL_R1_Tier_{k + 1}", fc.prism(poly, -0.2, z)[:2])
col("COL_R1_Floor", fc.prism(clip_y(OCT, -HY, TIER_Y[0]), -0.4, 0.0)[:2])
mkm("SM_R1_Ceiling", fc.prism(OCT, H, H + 0.3), [CHR])
strips = fc.mparts(*[(*BM(x - 0.08, x + 0.08, -HY + 0.5, HY - 0.5, H - 0.05, H), 0) for x in (-1.2, 1.2)])
mkm("SM_R1_CeilingLightStrips", strips, [CYN])

# aisle steps: 3 risers in front of each tier edge (3 m wide)
me_step = module("MOD_R_AisleStep_3m", nk.stair(2 * AISLE, 4, STEP_R, STEP_T), [SIL, CHR])
ramp = nk.stair_ramp(2 * AISLE, 4, STEP_R, STEP_T)
step_rails = []
for k, (y, z) in enumerate(zip(TIER_Y, TIER_Z)):
    place(f"SM_R1_AisleStep_{k + 1}", me_step, (0.0, y, z - 0.5))
    col(f"COL_R1_AisleStep_{k + 1}", fc.xform(ramp, offset=(0.0, y, z - 0.5)))
    # the step block stands proud of the tier edge: rail both open sides (they drop to the level below)
    for s in (-1, 1):
        x = s * (AISLE + 0.06)
        mkm(f"SM_R1_AisleStepRail_{k + 1}{'L' if s < 0 else 'R'}",
            nk.sloped_rail(x, y - 3 * STEP_T - STEP_T, z - 0.5, y, z), [GLS, SIL])
        step_rails.append(fc.sheared_box(x - 0.06, x + 0.06, y - 4 * STEP_T, z - 0.5, y, z, 1.1))

# railings along tier front edges (outside the aisle)
rails_col = []
for k, (y, z) in enumerate(zip(TIER_Y, TIER_Z)):
    poly = clip_y(OCT, y, y + 0.01)
    xmax = max(p[0] for p in poly)
    for s in (-1, 1):
        x0, x1 = sorted((s * AISLE, s * xmax))
        L = x1 - x0
        mkm(f"SM_R1_TierRail_{k + 1}{'L' if s < 0 else 'R'}", fc.xform(nk.railing(L), offset=((x0 + x1) / 2, y + 0.08, z)),
            [GLS, SIL])
        rails_col.append(BM(x0, x1, y + 0.02, y + 0.14, z, z + 1.1))
col("COL_R1_TierRails", fc.merge(*rails_col, *step_rails))

# ================================================================== walls (octagon) with door + window openings
def seg_wall(a, b, z0, z1, t=WT):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    L = math.hypot(dx, dy)
    nx, ny = dy / L * t, -dx / L * t
    pts = [(ax, ay), (ax + nx, ay + ny), (bx + nx, by + ny), (bx, by)]
    return fc.prism(pts, z0, z1)[:2]


def lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


wall_parts = []
for i in range(8):
    a, b = OCT[i], OCT[(i + 1) % 8]
    if a[0] == HX and b[0] == HX or a[0] == -HX and b[0] == -HX:          # side walls: blast door at y -5..-1
        ys = (DOOR_Y - DOOR_W / 2, DOOR_Y + DOOR_W / 2)
        L = b[1] - a[1]
        t0, t1 = sorted(((ys[0] - a[1]) / L, (ys[1] - a[1]) / L))
        wall_parts += [seg_wall(a, lerp(a, b, t0), 0, H), seg_wall(lerp(a, b, t1), b, 0, H),
                       seg_wall(lerp(a, b, t0), lerp(a, b, t1), DOOR_H, H)]
    elif a[1] == HY and b[1] == HY:                                       # window wall (b -> a runs -x)
        L = b[0] - a[0]
        t0, t1 = sorted(((-WIN_X - a[0]) / L, (WIN_X - a[0]) / L))
        wall_parts += [seg_wall(a, lerp(a, b, t0), 0, H), seg_wall(lerp(a, b, t1), b, 0, H),
                       seg_wall(lerp(a, b, t0), lerp(a, b, t1), 0, WIN_Z0), seg_wall(lerp(a, b, t0), lerp(a, b, t1), WIN_Z1, H)]
    else:
        wall_parts.append(seg_wall(a, b, 0, H))
mk("SM_R1_Walls", fc.merge(*wall_parts), [SIL])
col("COL_R1_Walls", fc.merge(*wall_parts))

# ---- detail: faceted charcoal ribs at the octagon corners, cyan wall band (skips the openings), tier fascia strips,
#      aisle floor lines, ceiling beams, window sill
me_rib = module("MOD_R_WallRib", fc.prism([(-0.35, 0.0), (-0.25, -0.3), (0.25, -0.3), (0.35, 0.0)], 0.0, H, cap_mat=0),
                [CHR])
for i, (a, b) in enumerate(zip(OCT, OCT[1:] + OCT[:1])):
    ang = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
    place(f"SM_R1_WallRib_{i}", me_rib, (a[0], a[1], 0.0), ang)
band_parts = []
for a, b in zip(OCT, OCT[1:] + OCT[:1]):
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy)
    nx, ny = -dy / L * 0.02, dx / L * 0.02                     # inward offset (CCW -> interior on the left)
    cuts = []
    if abs(a[0]) == HX and abs(b[0]) == HX:
        cuts = [sorted(((DOOR_Y - 2.5 - a[1]) / dy, (DOOR_Y + 2.5 - a[1]) / dy))]
    if a[1] == HY and b[1] == HY:
        cuts = [sorted(((-WIN_X - 0.4 - a[0]) / dx, (WIN_X + 0.4 - a[0]) / dx))]
    spans, t = [], 0.0
    for c0, c1 in cuts:
        spans.append((t, max(t, c0)))
        t = c1
    spans.append((t, 1.0))
    for t0, t1 in spans:
        if t1 - t0 < 1e-3:
            continue
        p0 = (a[0] + dx * t0, a[1] + dy * t0)
        p1 = (a[0] + dx * t1, a[1] + dy * t1)
        band_parts.append(fc.prism([p0, (p0[0] + nx, p0[1] + ny), (p1[0] + nx, p1[1] + ny), p1][::-1], 2.9, 3.0)[:2])
mk("SM_R1_WallBand", fc.merge(*band_parts), [CYN])
fascia = []
for (y, z) in zip(TIER_Y, TIER_Z):
    xmax = max(p[0] for p in clip_y(OCT, y, y + 0.01))
    for s in (-1, 1):
        x0, x1 = sorted((s * AISLE, s * xmax))
        fascia.append((*BM(x0, x1, y - 0.02, y, z - 0.22, z - 0.14), 0))
mkm("SM_R1_TierFascia", fc.mparts(*fascia), [CYN])
lines = [(*BM(x - 0.06, x + 0.06, -HY + 0.3, TIER_Y[0] - 1.0, 0.0, 0.006, skip=("bottom",)), 0) for x in (-AISLE, AISLE)]
lines += [(*BM(-HX + 1.0, -AISLE - 0.5, DOOR_Y - 0.06, DOOR_Y + 0.06, 0.0, 0.006, skip=("bottom",)), 0),
          (*BM(AISLE + 0.5, HX - 1.0, DOOR_Y - 0.06, DOOR_Y + 0.06, 0.0, 0.006, skip=("bottom",)), 0)]
mkm("SM_R1_FloorLines", fc.mparts(*lines), [CHR])
beams = fc.mparts(*[(*BM(-HX + 0.3, HX - 0.3, y - 0.2, y + 0.2, H - 0.5, H), 0) for y in (-6.0, -2.0, 2.0, 6.0)])
mkm("SM_R1_CeilingBeams", beams, [CHR])

# ================================================================== viewing window: faceted frame + glass (separate)
def window_frame():
    p = []
    for x in (-WIN_X, -4.0, 0.0, 4.0, WIN_X):
        w = 0.35 if abs(x) == WIN_X else 0.18
        p.append((*fc.prism([(x - w, HY), (x + w, HY), (x + w * 0.6, HY - 0.4), (x - w * 0.6, HY - 0.4)], WIN_Z0, WIN_Z1), ))
    for z, w in ((WIN_Z0, 0.3), (4.5, 0.15), (WIN_Z1, 0.3)):
        p.append((*BM(-WIN_X, WIN_X, HY - 0.35, HY, max(z - w, WIN_Z0), z + w), [0] * 6))
    p.append((*BM(-WIN_X - 0.4, WIN_X + 0.4, HY - 0.6, HY - 0.35, WIN_Z0, WIN_Z0 + 0.12), [0] * 6))   # sill ledge
    return fc.mparts(*[(q[0], q[1], [0] * len(q[1])) for q in p])


mkm("SM_R1_WindowFrame", window_frame(), [CHR], recalc=True)
mkm("SM_R1_WindowGlass", (*BM(-WIN_X, WIN_X, HY + 0.1, HY + 0.14, WIN_Z0, WIN_Z1), [0] * 6), [GLS], recalc=True)
col("COL_R1_WindowGlass", BM(-WIN_X, WIN_X, HY, HY + 0.2, WIN_Z0, WIN_Z1))

# ================================================================== blast doors: hazard frame + 2 sliding leaves + arrow sign
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


me_frame = module("MOD_R_BlastDoor_Frame", hazard_frame(DOOR_W, DOOR_H, 0.5, 0.6, 0.4), [AMB, CHR])
leaf = fc.mparts((*BM(-1.0, 1.0, -0.12, 0.12, 0.0, DOOR_H), 0), (*BM(-0.95, -0.85, -0.14, -0.12, 0.3, 3.7), 1))
me_leaf = module("MOD_R_BlastDoor_Leaf", leaf, [SIL, CYN])            # origin bottom-centre (slides along local X)
# floor arrow (points +X in local space): shaft + head, 1.5 cm proud of the floor
arrow = fc.mparts(fc.prism([(-0.9, -0.18), (0.3, -0.18), (0.3, 0.18), (-0.9, 0.18)], 0.0, 0.015, cap_mat=0),
                  fc.prism([(0.3, -0.5), (1.0, 0.0), (0.3, 0.5)], 0.0, 0.015, cap_mat=0))
me_arrow = module("MOD_R_DirectionArrow", arrow, [CYN])
doors = {}
for name, x, rz in (("Entry", -HX, 90), ("ToR2", HX, -90)):
    place(f"SM_R1_BlastDoor_{name}_Frame", me_frame, (x, DOOR_Y, 0), rz)
    for side, off in (("A", -1.0), ("B", 1.0)):
        ldx = (0.0 if rz == 90 else 0.0)
        o = place(f"SM_R1_BlastDoor_{name}_Leaf{side}", me_leaf,
                  (x + (0.15 if x < 0 else -0.15), DOOR_Y + (off if rz == 90 else -off), 0), rz)
        o["slide_axis"] = "local X"
        o["open_offset_m"] = 1.9 * (1 if side == "B" else -1)
    # entry arrow points out to the transit hub (-X); exit arrow points toward R2 (+X)
    place(f"SM_R1_Arrow_{name}", me_arrow, (x + (2.2 if x < 0 else -2.2), DOOR_Y, 0.0), 180 if x < 0 else 0)
    doors[name] = (x, DOOR_Y, 0.0)
mk("SM_R1_DoorStubs", fc.merge(
    *[(v, [tuple(reversed(q)) for q in f]) for v, f in (
        BM(-HX - WT - 4.0, -HX - WT, DOOR_Y - DOOR_W / 2, DOOR_Y + DOOR_W / 2, 0.0, DOOR_H, skip=("right",)),
        BM(HX + WT, HX + WT + 4.0, DOOR_Y - DOOR_W / 2, DOOR_Y + DOOR_W / 2, 0.0, DOOR_H, skip=("left",)))]),
   [CHR], recalc=False)
col("COL_R1_DoorFrames", fc.merge(*[BM(x - 0.4 if x > 0 else x, x if x > 0 else x + 0.4, y0, y1, 0, DOOR_H + 0.6)
                                    for x in (-HX, HX) for (y0, y1) in ((DOOR_Y - 2.5, DOOR_Y - 2.0),
                                                                         (DOOR_Y + 2.0, DOOR_Y + 2.5))]))

# ================================================================== operator desks (twin cyan screens, cover height)
def desk():
    w, d = DESK_W / 2, DESK_D / 2
    body = (*BM(-w, w, -d + 0.1, d, 0.0, 0.85), 0)
    top = fc.slab_grid([-w, w], [-d, d], 0.85, lambda x, y: 0.88 + (y + d) / (2 * d) * 0.12, side_mat=1, matfn=lambda i, j: 1)
    p = [body, top]
    for cx in (-0.6, 0.6):
        p += [(*BM(cx - 0.55, cx + 0.55, 0.15, 0.25, 0.9, DESK_H + 0.45), 1),
              (*BM(cx - 0.5, cx + 0.5, 0.13, 0.15, 0.95, DESK_H + 0.4), 2)]
    return fc.mparts(*p)


me_desk = module("MOD_R_OperatorDesk", desk(), [SIL, CHR, CYN])
desk_col = []
for k, xs in DESKS.items():
    for s in (-1, 1):
        for x in xs:
            place(f"SM_R1_Desk_T{k + 1}_{'L' if s < 0 else 'R'}{int(x)}", me_desk, (s * x, DESK_Y[k], TIER_Z[k]), 0)
            desk_col.append(BM(s * x - DESK_W / 2, s * x + DESK_W / 2, DESK_Y[k] - DESK_D / 2, DESK_Y[k] + DESK_D / 2,
                               TIER_Z[k], TIER_Z[k] + DESK_H))
col("COL_R1_Desks", fc.merge(*desk_col))

# ================================================================== warning struts (charcoal, amber triangle panel)
def strut():
    h = H - TIER_Z[2]
    body = fc.prism([(-0.3, -0.2), (-0.2, -0.3), (0.2, -0.3), (0.3, -0.2), (0.3, 0.2), (0.2, 0.3), (-0.2, 0.3),
                     (-0.3, 0.2)], 0.0, h, cap_mat=0)
    # "stressed": a bolted collar band + a slight kink (upper half offset 4 cm toward the glass)
    body = (body[0], body[1], body[2])
    body = ([(x, y + (0.04 if z > h / 2 else 0.0), z) for x, y, z in body[0]], body[1], body[2])
    collar = (*BM(-0.36, 0.36, -0.36, 0.36, h / 2 - 0.15, h / 2 + 0.15), [0] * 6)
    tri = [(-0.45, 1.6), (0.45, 1.6), (0.0, 2.38)]
    panel = fc.extrude2d(tri, [(0, 1, 2)], [1], 0.03, -0.33, back=False)
    bang = fc.extrude2d([(-0.04, 1.85), (0.04, 1.85), (0.04, 2.15), (-0.04, 2.15)], [(0, 1, 2, 3)], [0], 0.01, -0.34,
                        back=False)
    dot = fc.extrude2d([(-0.04, 1.72), (0.04, 1.72), (0.04, 1.79), (-0.04, 1.79)], [(0, 1, 2, 3)], [0], 0.01, -0.34,
                       back=False)
    return fc.mparts(body, collar, panel, bang, dot)


me_strut = module("MOD_R_WarningStrut", strut(), [CHR, AMB])
for i, x in enumerate(STRUTS):
    place(f"SM_R1_WarningStrut_{i + 1}", me_strut, (x, HY - 0.9, TIER_Z[2]), 0)
col("COL_R1_Struts", fc.merge(*[BM(x - 0.3, x + 0.3, HY - 1.2, HY - 0.6, TIER_Z[2], H) for x in STRUTS]))

# ================================================================== reactor core background card (not walkable, beyond the glass)
core = fc.mparts((*fc.lathe([(0, -12), (3.2, -12), (3.2, 22), (0, 22)], 12), [0] * 48),
                 *[(*fc.lathe([(3.2, z), (4.4, z), (4.4, z + 0.8), (3.2, z + 0.8)], 12, closed=True), [0] * 48)
                   for z in (-2.0, 3.0, 8.0, 13.0)],
                 *[(*fc.lathe([(3.21, z), (3.3, z), (3.3, z + 2.2), (3.21, z + 2.2)], 12), [1] * 36)
                   for z in (-0.6, 4.4, 9.4)])
mkm("SM_R1_ReactorCard", core, [CHR, CYN], coll=C_BG, loc=(0.0, 32.0, 0.0), recalc=True)
mkm("SM_R1_ReactorBackdrop", ([(-40, 45, -15), (40, 45, -15), (40, 45, 35), (-40, 45, 35)], [(0, 3, 2, 1)], [0]), [CHR],
    coll=C_BG)

# ================================================================== landmarks + checks
landmarks = {"LM_R1_Entry": doors["Entry"], "LM_R1_ToR2": doors["ToR2"], "LM_R1_Aisle": (0.0, -HY + 1.0, 0.0),
             "LM_R1_Window": (0.0, HY, TIER_Z[2])}
for k, (y, z) in enumerate(zip(TIER_Y, TIER_Z)):
    landmarks[f"LM_R1_Tier{k + 1}"] = (0.0, y, z)
for n, p in landmarks.items():
    fc.empty(n, p, C_LM, 0.8, "ARROWS").hide_render = True
bpy.context.view_layer.update()
# sightline: from the entry door (eye height) and from the aisle foot to points on the window glass
blk = [o for o in C_EXP.all_objects if o.type == "MESH" and o.name not in ("SM_R1_WindowGlass",) and C_BG not in o.users_collection]
verts, polys = [], []
for o in blk:
    off = len(verts)
    verts += [o.matrix_world @ v.co for v in o.data.vertices]
    polys += [[off + i for i in p.vertices] for p in o.data.polygons if o.material_slots[p.material_index].material != GLS]
bvh = BVHTree.FromPolygons(verts, polys)
sight = {}
for name, eye in (("aisle_foot", Vector((0.0, -8.0, 1.7))), ("entry_door", Vector((-11.0, -3.0, 1.7)))):
    tg = [Vector((x, HY + 0.05, z)) for x in (-6, -2, 2, 6) for z in (3.0, 5.0, 7.0)]
    sight[name] = sum(1 for t in tg if bvh.ray_cast(eye, (t - eye).normalized(), (t - eye).length - 0.1)[0] is None)
sight = {k: f"{v}/12 window points visible" for k, v in sight.items()}

# ================================================================== presentation + renders
fc.ref_player(C_REF, (-3.5, -6.0, 0))
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


cam_top = cam("CAM_TopDown", (0, 0, 60), ortho=27)
cam_eye = cam("CAM_EyeHeight", (0.0, -8.5, 1.7), target=(0.0, 9.0, 3.4))
sun_d = bpy.data.lights.new("LGT_Key_6500K", "SUN")
sun_d.energy = 2.5
sun = bpy.data.objects.new("LGT_Key_6500K", sun_d)
sun.rotation_euler = (math.radians(20), 0, math.radians(160))
C_PRES.objects.link(sun)
sc.world.use_nodes = True
bg = sc.world.node_tree.nodes.get("Background")
bg.inputs[0].default_value = fc.hex_lin("#C9D6E3")
bg.inputs[1].default_value = 0.7
renders = {}
TOP_HIDE = [bpy.data.objects[n] for n in ("SM_R1_Ceiling", "SM_R1_CeilingLightStrips", "SM_R1_CeilingBeams")]
for o in TOP_HIDE:
    o.hide_render = True
C_BG.hide_render = True
sc.camera = cam_top
renders["topdown"] = fc.render(os.path.join(fc.RENDER_DIR, "R1_detail_topdown.png"), engine="BLENDER_EEVEE")
for o in TOP_HIDE:
    o.hide_render = False
C_BG.hide_render = False
sc.camera = cam_eye
renders["eye"] = fc.render(os.path.join(fc.RENDER_DIR, "R1_detail_eyeheight.png"), engine="BLENDER_EEVEE")
cam_hero = cam("CAM_Hero34", (-10.2, -7.6, 4.4), target=(3.0, 6.0, 2.5), lens=20)
sc.camera = cam_hero
renders["hero"] = fc.render(os.path.join(fc.RENDER_DIR, "R1_detail_hero34.png"), engine="BLENDER_EEVEE")
sun.hide_render = True
bg.inputs[1].default_value = 1.0
sc.camera = cam_eye
renders["eye_flat_ambient"] = fc.render(os.path.join(fc.RENDER_DIR, "R1_detail_eyeheight_flat.png"), engine="BLENDER_EEVEE")
sun.hide_render = False
bg.inputs[1].default_value = 0.7
sc.camera = cam_hero

_, uniq, inst = fc.tri_report([C_EXP])
report = {
    "plan": dict(footprint=[2 * HX, 2 * HY], chamfer=CH, ceiling=H, octagon=OCT),
    "front_zone": dict(y=[-HY, TIER_Y[0]], z=0.0),
    "tiers": [dict(y=[y0, y1], z=z) for (y0, y1), z in zip(tier_bounds, TIER_Z)],
    "aisle": dict(width=2 * AISLE, steps_per_tier=3, rise=round(STEP_R, 4), tread=STEP_T),
    "doors": dict(entry=doors["Entry"], to_R2=doors["ToR2"], w=DOOR_W, h=DOOR_H, leaves="2 x 2 m sliding, separate"),
    "window": dict(x=[-WIN_X, WIN_X], z=[WIN_Z0, WIN_Z1], size=[2 * WIN_X, WIN_Z1 - WIN_Z0]),
    "desks": {f"tier{k + 1}": len(v) * 2 for k, v in DESKS.items()}, "desk_size": [DESK_W, DESK_D, DESK_H],
    "struts_x": STRUTS, "sightlines": sight,
    "landmarks": {k: [round(c, 3) for c in v] for k, v in landmarks.items()},
    "tris_export_unique": uniq, "tris_export_instanced": inst, "budget": 100000, "renders": renders,
}
blend = os.path.join(fc.SOURCE_DIR, f"Fractured_{ID}_{NAME}.blend")
glb = os.path.join(fc.EXPORT_DIR, f"Fractured_{ID}_{NAME}.glb")
report["qa"] = qa.run(ID, C_EXP, C_COL, C_FX, budget=100000, landmark_coll=C_LM, walk_bounds=(-HX, HX, -HY, HY),
                      walkable_prefixes=("COL_R1_Floor", "COL_R1_Tier_", "COL_R1_AisleStep"),
                      walk_mask=lambda x, y: abs(x) + abs(y) <= HX + HY - CH - 0.05,   # inside the chamfered octagon
                      pair_with=os.path.join(fc.RENDER_DIR, "R1_blockout_landmarks.json"))
report["rotations_baked"] = baked
report["blend"] = blend
fc.save(blend)
report["qa"]["export"] = qa.export_and_verify(C_EXP, C_COL, glb)
report["glb"] = glb
with open(os.path.join(fc.RENDER_DIR, "R1_QA_report.json"), "w") as fh:
    json.dump(report, fh, indent=2)
print("R1 DETAIL DONE pass=", report["qa"]["pass"], json.dumps(sight))
