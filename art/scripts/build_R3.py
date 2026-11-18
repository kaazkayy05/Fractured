"""R3 Convergence Chamber (boss arena) — DETAIL stage + Block Z QA + export (layout approved, build_R3_blockout.py).
Circular, 30 m diameter (r=15), ceiling 18 m. Core at the origin (base r=3), circulation ring r 3..7 (4 m, unobstructed),
three convergence nodes at 120 deg with their inner faces at r=7, cover blocks on the outer ring (r~11),
Approach A (from R2) on -X, Approach B (alt route) on +X — 6 x 5 m openings in flat portal walls at |x| = 13.86.
Run: blender -b --factory-startup -P art/scripts/build_R3.py
"""
import os
import sys
import math
import json
import random
import bpy
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(__file__))
import fractured_common as fc
import fractured_qa as qa
import nova_kit as nk
import veyra_kit as vk

ID, NAME = "R3", "ConvergenceChamber"
sc = fc.reset_scene()
M = fc.append_shared_materials()
SIL, GLS, CYN, CHR, AMB, MOSS, VCON = (M[k] for k in ("M_NovaSilver", "M_NovaGlass", "M_CyanEmissive", "M_Charcoal",
                                                    "M_AmberWarning", "M_Moss", "M_VeyraConcrete"))
VIO = fc.make_material("M_FX_Violet", fc.PALETTE["violet"], roughness=0.5, emission=4.0)      # FX-only, never shared
C_EXP = fc.collection(f"{ID}_Export")
C_CORE = fc.collection(f"{ID}_Core", C_EXP)
C_NODE = fc.collection(f"{ID}_Nodes", C_EXP)
C_COL = fc.collection(f"{ID}_Collision")
C_FX = fc.collection(f"{ID}_FX")
C_PRES = fc.collection(f"{ID}_Presentation")
C_REF = fc.collection("_Reference")
C_LM = fc.collection(f"{ID}_Landmarks")
C_MOD = fc.collection(f"{ID}_ModuleSources")
BM = fc.box_minmax

# ------------------------------------------------------------------ dimensions
R, H, WT = 15.0, 18.0, 0.4
SEGS = 32
CORE_R, RING_OUT = 3.0, 7.0
NODE_TRI_R = 1.2                                   # pedestal circumradius (inradius 0.6)
NODE_C = RING_OUT + NODE_TRI_R / 2                 # 7.6: inner face at r=7
NODE_H = 2.5
NODES = {"A": 90.0, "B": 210.0, "C": 330.0}
PORTAL_HALF_DEG = 22.5                              # 4 segments replaced by a flat portal wall
PORTAL_X = R * math.cos(math.radians(PORTAL_HALF_DEG))   # 13.86
DOOR_W, DOOR_H = 6.0, 5.0
COVER_R = 11.0
COVERS = [(30, 1.1), (60, 1.4), (120, 1.25), (150, 1.1), (240, 1.4), (270, 1.25), (300, 1.1)]
BROKEN_PANELS = (8, 19)                             # wall segment indices replaced by damaged panels
BEAM_ANG = 103.0


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


def polar(r, deg):
    a = math.radians(deg)
    return (r * math.cos(a), r * math.sin(a))


# ================================================================== floor: disk + concentric inlays + amber danger band
floor = fc.lathe([(0, -0.3), (R + WT, -0.3), (R + WT, 0.0), (0, 0.0)], SEGS)
mkm("SM_R3_Floor", (*floor, [0] * len(floor[1])), [SIL], recalc=True)
col("COL_R3_Floor", fc.lathe([(0, -0.5), (R + WT, -0.5), (R + WT, 0.0), (0, 0.0)], SEGS))
inlays = []
for r0 in (RING_OUT - 0.06, 11.0 - 0.05, 14.3 - 0.05):
    inl = fc.lathe([(r0 + 0.12 if r0 < 8 else r0 + 0.1, 0.0), (r0 + 0.12 if r0 < 8 else r0 + 0.1, 0.008), (r0, 0.008),
                    (r0, 0.0)], 64)
    inlays.append((*inl, [0] * len(inl[1])))
mkm("SM_R3_FloorInlays", fc.mparts(*inlays), [CYN])
band = []
NB = 24
for k in range(NB):
    a0, a1 = 360.0 * k / NB, 360.0 * (k + 1) / NB
    pts = [polar(CORE_R + 0.05, a0), polar(CORE_R + 0.75, a0), polar(CORE_R + 0.75, a1), polar(CORE_R + 0.05, a1)]
    pr = fc.prism(pts[::-1] if False else [pts[0], pts[3], pts[2], pts[1]][::-1], 0.0, 0.01, cap_mat=k % 2)
    band.append(pr)
mkm("SM_R3_CoreDangerBand", fc.mparts(*band), [AMB, CHR], recalc=True)

# ================================================================== walls: 32 segments, 2 flat portals (6 x 5 openings), 2 broken panels
def seg_pts(i):
    a0, a1 = 360.0 * i / SEGS, 360.0 * (i + 1) / SEGS
    return polar(R, a0), polar(R, a1)


def wall_seg_data(a, b, z0=0.0, z1=H, t=WT):
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy)
    nx, ny = dy / L * t, -dx / L * t                 # CCW circle -> outward is to the right of a->b
    return fc.prism([a, (a[0] + nx, a[1] + ny), (b[0] + nx, b[1] + ny), b], z0, z1)


def in_portal(i):
    mid = 360.0 * (i + 0.5) / SEGS
    return min(abs(mid - 0), abs(mid - 360)) < PORTAL_HALF_DEG or abs(mid - 180) < PORTAL_HALF_DEG


# standard panel module (one chord), placed by rotation: build at angle 0..11.25
a0, a1 = polar(R, 0.0), polar(R, 360.0 / SEGS)
chord = math.hypot(a1[0] - a0[0], a1[1] - a0[1])
mid = ((a0[0] + a1[0]) / 2, (a0[1] + a1[1]) / 2)
seg_rot = math.degrees(math.atan2(a1[1] - a0[1], a1[0] - a0[0]))
# local panel: front face at y=0 (faces -Y), centred on x=0 -> rotate so -Y points to the centre
def panel(chord_w, broken=False):
    w = chord_w / 2
    zs = [0.0, 2.95, 3.05, 11.95, 12.05, H]
    if not broken:
        pts, faces, mats = fc.grid2d([-w, w], zs, lambda i, j: True, lambda i, j: 2 if j in (1, 3) else 0)
        return fc.extrude2d(pts, faces, mats, WT, 0.0)
    # broken: jagged breach (no geometry) between z 4..9 on the right half, exposing a dark recess
    xs = [-w, 0.0, w * 0.55, w]
    pts, faces, mats = fc.grid2d(xs, [0.0, 2.95, 3.05, 4.0, 9.0, 11.95, 12.05, H],
                                 lambda i, j: not (i == 1 and j in (3,)) and not (i == 2 and j in (3, 4)),
                                 lambda i, j: 2 if j in (1, 5) else 0)
    wall = fc.extrude2d(pts, faces, mats, WT, 0.0, side_mat=1)
    recess = (*BM(0.0, w, WT, WT + 0.6, 4.0, 9.0, skip=("front",)), 1)
    return fc.mparts(wall, recess)


me_panel = module("MOD_R_ArenaWall", panel(chord), [SIL, CHR, CYN])
me_panel_b = module("MOD_R_ArenaWall_Broken", panel(chord, broken=True), [SIL, CHR, CYN])
wall_cols = []
for i in range(SEGS):
    if in_portal(i):
        continue
    a, b = seg_pts(i)
    cx, cy = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    ang = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
    me = me_panel_b if i in BROKEN_PANELS else me_panel
    place(f"SM_R3_Wall_{i:02d}{'_Broken' if i in BROKEN_PANELS else ''}", me, (cx, cy, 0.0), ang + 180.0)
    wall_cols.append(wall_seg_data(a, b)[:2])
for side, s in (("A", -1), ("B", 1)):
    y = R * math.sin(math.radians(PORTAL_HALF_DEG))
    xs = PORTAL_X * s
    pts, faces, mats = fc.grid2d([-y, -DOOR_W / 2, DOOR_W / 2, y], [0.0, DOOR_H, H],
                                 lambda i, j: not (i == 1 and j == 0), lambda i, j: 0)
    portal = fc.extrude2d(pts, faces, mats, WT, 0.0)
    rz = -90 if s > 0 else 90
    mkm(f"SM_R3_PortalWall_{side}", fc.xform(portal, rot_z=rz, offset=(xs, 0, 0)), [SIL], recalc=True)
    x0, x1 = sorted((xs, xs + s * WT))
    wall_cols += [BM(x0, x1, -y, -DOOR_W / 2, 0, H), BM(x0, x1, DOOR_W / 2, y, 0, H), BM(x0, x1, -DOOR_W / 2, DOOR_W / 2, DOOR_H, H)]
col("COL_R3_Walls", fc.merge(*wall_cols))

# ---- detail: faceted charcoal buttress ribs at every second wall joint (not at the portals), sparse vines up high
me_butt = module("MOD_R_ArenaButtress", fc.prism([(-0.45, 0.0), (-0.3, -0.55), (0.3, -0.55), (0.45, 0.0)], 0.0, H,
                                                 cap_mat=0), [CHR])
bcol = []
for i in range(0, SEGS, 2):
    ang = 360.0 * i / SEGS
    if min(abs(ang - 0), abs(ang - 360), abs(ang - 180)) <= PORTAL_HALF_DEG + 1e-6:
        continue
    x, y = polar(R, ang)
    place(f"SM_R3_Buttress_{i:02d}", me_butt, (x, y, 0.0), ang - 90)      # local -Y (protrusion) faces the core
    bcol.append(fc.xform(BM(-0.45, 0.45, -0.55, 0.0, 0.0, H), rot_z=ang - 90, offset=(x, y, 0.0)))
col("COL_R3_Buttresses", fc.merge(*bcol))
me_vine = {L: module(f"MOD_V_VineCard_{L:g}m", vk.vine_card(L), [MOSS]) for L in (3.0, 4.5)}
vr = random.Random(21)
for k in range(9):
    ang = vr.choice([40, 75, 110, 135, 230, 255, 285, 310, 325]) + vr.uniform(-3, 3)
    x, y = polar(R - 0.08, ang)
    place(f"SM_R3_Vine_{k:02d}", me_vine[3.0 if k % 2 else 4.5], (x, y, H - 1.0 - vr.uniform(0, 3.0)), ang - 90)

# entrance frames (amber hazard) + stubs
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


me_f6 = module("MOD_R_BlastDoor_Frame_6x5", hazard_frame(DOOR_W, DOOR_H, 0.5, 0.6, 0.4), [AMB, CHR])
place("SM_R3_Approach_A_Frame", me_f6, (-PORTAL_X, 0.0, 0.0), 90)
place("SM_R3_Approach_B_Frame", me_f6, (PORTAL_X, 0.0, 0.0), -90)
mk("SM_R3_ApproachStubs", fc.merge(*[(v, [tuple(reversed(q)) for q in f]) for v, f in (
    BM(-PORTAL_X - WT - 4.0, -PORTAL_X - WT, -DOOR_W / 2, DOOR_W / 2, -0.3, DOOR_H, skip=("right",)),
    BM(PORTAL_X + WT, PORTAL_X + WT + 4.0, -DOOR_W / 2, DOOR_W / 2, -0.3, DOOR_H, skip=("left",)))]), [CHR], recalc=False)

# ceiling with radial ribs + opening for the core column
ceil = fc.lathe([(1.6, H), (R + WT, H), (R + WT, H + 0.5), (1.6, H + 0.5)], SEGS, closed=True)
mkm("SM_R3_Ceiling", (*ceil, [0] * len(ceil[1])), [CHR], recalc=True)
ribs = []
for k in range(16):
    ang = 360.0 * k / 16 + 5.625
    ribs.append(fc.xform(BM(2.0, R - 0.2, -0.25, 0.25, H - 0.8, H), rot_z=ang))
mkm("SM_R3_CeilingRibs", (*fc.merge(*ribs), [0] * (6 * 16)), [CHR], recalc=True)

# ================================================================== core: base, 4 rotating rings, glass + cyan column to the ceiling
base = fc.lathe([(0, 0), (CORE_R, 0), (CORE_R, 1.0), (CORE_R - 0.4, 1.4), (0, 1.4)], 12, angle_offset=math.pi / 12)
mkm("SM_CoreBase", (*base, [0] * 12 + [0] * 12 + [1] * 12 + [0] * 12), [CHR, SIL], coll=C_CORE, recalc=True)
for k in range(4):
    z = 2.4 + k * 2.6
    rr = 2.7 - 0.25 * k
    ring = fc.lathe([(rr - 0.45, -0.25), (rr, -0.25), (rr, 0.25), (rr - 0.45, 0.25)], 12, closed=True)
    m = [1] * 12 + [0] * 12 + [1] * 12 + [0] * 12
    o = mkm(f"SM_CoreRing_{k + 1:02d}", (*ring, m), [CHR, CYN], coll=C_CORE, loc=(0, 0, z), recalc=True)
    o["rotate_axis"] = "local Z"
    o["rotate_dir"] = 1 if k % 2 == 0 else -1
glass = fc.lathe([(1.5, 0), (1.5, H - 1.4), (1.42, H - 1.4), (1.42, 0)], 12, closed=True)
mkm("SM_CoreColumn_Glass", (*glass, [0] * len(glass[1])), [GLS], coll=C_CORE, loc=(0, 0, 1.4), recalc=True)
inner = fc.lathe([(0, 0), (0.75, 0), (0.75, H - 1.4), (0, H - 1.4)], 8)
mkm("SM_CoreColumn_Energy", (*inner, [0] * len(inner[1])), [CYN], coll=C_CORE, loc=(0, 0, 1.4), recalc=True)
col("COL_R3_Core", fc.cylinder_data(CORE_R, H, 12, angle_offset=math.pi / 12))

# ================================================================== convergence nodes (triangular pedestals + separate glyphs)
def tri(r, rot):
    return [(r * math.cos(rot + 2 * math.pi * k / 3), r * math.sin(rot + 2 * math.pi * k / 3)) for k in range(3)]


def pedestal():
    """Triangle pedestal, a flat face toward local -X (the core). Local origin = pedestal centre."""
    rot = 0.0                                                    # vertex at +X -> flat face at -X (inradius 0.6)
    lower = fc.prism(tri(NODE_TRI_R, rot), 0.0, 0.3, cap_mat=1)
    body = fc.prism(tri(NODE_TRI_R * 0.92, rot), 0.3, NODE_H - 0.2, side_mats=[0, 0, 0], cap_mat=0)
    cap = fc.prism(tri(NODE_TRI_R * 0.75, rot), NODE_H - 0.2, NODE_H, cap_mat=2)
    return fc.mparts(lower, body, cap)


def glyph(kind):
    """Emissive glyph on the inward face (plane x = -inradius*0.92), drawn in the (y, z) plane."""
    c = (0.0, 1.75)
    if kind == "A":                                  # triangle
        pts = [(c[0] - 0.32, c[1] - 0.25), (c[0] + 0.32, c[1] - 0.25), (c[0], c[1] + 0.32)]
        faces = [(0, 1, 2)]
    elif kind == "C":                                # diamond
        pts = [(c[0], c[1] - 0.38), (c[0] + 0.26, c[1]), (c[0], c[1] + 0.38), (c[0] - 0.26, c[1])]
        faces = [(0, 1, 2, 3)]
    else:                                            # trefoil: three blades around a centre
        pts, faces = [(c[0], c[1])], []
        for k in range(3):
            a = math.radians(90 + 120 * k)
            tip = (c[0] + 0.38 * math.cos(a), c[1] + 0.38 * math.sin(a))
            l = (c[0] + 0.16 * math.cos(a + 0.9), c[1] + 0.16 * math.sin(a + 0.9))
            r_ = (c[0] + 0.16 * math.cos(a - 0.9), c[1] + 0.16 * math.sin(a - 0.9))
            i0 = len(pts)
            pts += [r_, tip, l]
            faces.append((0, i0, i0 + 1, i0 + 2))
    d = fc.extrude2d(pts, faces, [0] * len(faces), 0.04, 0.0, back=False)
    # extrude2d draws in (x,z) with front at -Y; rotate so the front faces local -X, then push onto the face
    inr = NODE_TRI_R * 0.92 / 2
    return fc.xform(d, rot_z=-90, offset=(-inr - 0.005, 0.0, 0.0))


me_ped = module("MOD_R_ConvergencePedestal", pedestal(), [SIL, CHR, CYN], recalc=True)
landmarks = {}
for n, ang in NODES.items():
    x, y = polar(NODE_C, ang)
    rz = ang                                          # local -X faces the core
    o = place(f"SM_ConvergenceNode_{n}", me_ped, (x, y, 0.0), rz, C_NODE)
    o["glyph"] = {"A": "triangle", "B": "trefoil", "C": "diamond"}[n]
    g = mkm(f"SM_ConvergenceNode_{n}_Glyph", glyph(n), [CYN], coll=C_NODE, recalc=False)
    g.parent = o
    landmarks[f"LM_R3_Node_{n}"] = (x, y, 0.0)
col("COL_R3_Nodes", fc.merge(*[fc.xform(fc.prism(tri(NODE_TRI_R, 0.0), 0.0, NODE_H)[:2], rot_z=ang,
                                        offset=(*polar(NODE_C, ang), 0.0)) for ang in NODES.values()]))

# ================================================================== cover blocks (outer ring), damage, fallen beam
def cover(h):
    return fc.mparts((*BM(-1.0, 1.0, -0.6, 0.6, 0.0, h - 0.06), 0),
                     (*BM(-0.92, 0.92, -0.52, 0.52, h - 0.06, h, skip=("bottom",)), 1),
                     (*BM(-1.04, 1.04, -0.64, 0.64, 0.0, 0.18), 0))


cov_me = {h: module(f"MOD_R_CoverBlock_{int(h * 100)}", cover(h), [VCON, MOSS]) for h in sorted({h for _, h in COVERS})}
cov_col = []
for i, (ang, h) in enumerate(COVERS):
    x, y = polar(COVER_R, ang)
    place(f"SM_R3_Cover_{i}", cov_me[h], (x, y, 0.0), ang + 90)
    cov_col.append(fc.xform(BM(-1.04, 1.04, -0.64, 0.64, 0.0, h), rot_z=ang + 90, offset=(x, y, 0.0)))
col("COL_R3_Cover", fc.merge(*cov_col))
bx, by = polar(12.6, BEAM_ANG)
beam = fc.xform(BM(-3.6, 3.6, -0.3, 0.3, -0.3, 0.3), rot_y=-24, offset=(0, 0, 1.65))
mkm("SM_R3_FallenBeam", (*beam, [0] * 6), [CHR], loc=(bx, by, 0.0), rz=BEAM_ANG + 90, recalc=True)
col("COL_R3_FallenBeam", fc.xform(beam, rot_z=BEAM_ANG + 90, offset=(bx, by, 0.0)))
rub_me = module("SM_Rubble_Cluster", vk.rubble(41, n=6, w=2.0, d=1.4, h=1.1), [VCON, CHR], recalc=True)
rub = []
for i, seg in enumerate(BROKEN_PANELS):
    ang = 360.0 * (seg + 0.5) / SEGS
    x, y = polar(R - 1.1, ang)
    rub.append(place(f"SM_R3_Rubble_{i}", rub_me, (x, y, 0.0), ang + 90))
bpy.context.view_layer.update()
col("COL_R3_Rubble", fc.merge(*vk.hull_parts(rub)))

# ================================================================== violet active fracture (FX only)
frng = random.Random(13)
crack = []
for k in range(3):
    a0 = math.radians(250 + k * 12)
    p = [(CORE_R + 0.1, 0.0)]
    r = CORE_R + 0.1
    pts2 = []
    for s in range(5):
        r += frng.uniform(0.35, 0.55)
        a = a0 + frng.uniform(-0.12, 0.12)
        pts2.append((r * math.cos(a), r * math.sin(a)))
    start = (CORE_R * math.cos(a0), CORE_R * math.sin(a0))
    chain = [start] + pts2
    for (ax, ay), (bx_, by_) in zip(chain, chain[1:]):
        dx, dy = bx_ - ax, by_ - ay
        L = math.hypot(dx, dy)
        nx, ny = -dy / L * 0.06, dx / L * 0.06
        crack.append(fc.prism([(ax - nx, ay - ny), (bx_ - nx, by_ - ny), (bx_ + nx, by_ + ny), (ax + nx, ay + ny)],
                              0.0, 0.015))
mkm("FX_R3_FractureCrack", fc.mparts(*crack), [VIO], coll=C_FX, recalc=True)
for k in range(3):
    sv, sf = fc.lathe([(0, -0.15), (0.08, 0.0), (0, 0.18)], 5)
    x, y = polar(CORE_R + 1.0 + 0.5 * k, 262 + 10 * k)
    mkm(f"FX_R3_FractureShard_{k + 1:02d}", (sv, sf, [0] * len(sf)), [VIO], coll=C_FX, loc=(x, y, 0.6 + 0.35 * k),
        recalc=True)
landmarks["LM_R3_FractureFX"] = (*polar(CORE_R + 1.2, 262), 0.0)

# ================================================================== landmarks + checks
landmarks.update({"LM_R3_Core": (0.0, 0.0, 0.0), "LM_R3_FromR2": (-PORTAL_X, 0.0, 0.0), "LM_R3_ApproachB": (PORTAL_X, 0.0, 0.0)})
for n, p in landmarks.items():
    fc.empty(n, p, C_LM, 0.8, "ARROWS").hide_render = True
bpy.context.view_layer.update()
obst = [o for o in C_COL.objects if not o.name.startswith(("COL_R3_Floor",))]
verts, polys = [], []
for o in obst:
    off = len(verts)
    verts += [o.matrix_world @ v.co for v in o.data.vertices]
    polys += [[off + i for i in p.vertices] for p in o.data.polygons]
obvh = BVHTree.FromPolygons(verts, polys)
blocked = 0
n_s = 0
for rr in [CORE_R + 0.05 + 0.1 * k for k in range(int((RING_OUT - CORE_R - 0.1) / 0.1) + 1)]:
    for k in range(int(2 * math.pi * rr / 0.25)):
        a = 2 * math.pi * k / int(2 * math.pi * rr / 0.25)
        x, y = rr * math.cos(a), rr * math.sin(a)
        n_s += 1
        if obvh.ray_cast(Vector((x, y, 0.05)), Vector((0, 0, 1)), 2.5)[0] is not None:
            blocked += 1
cover_r = [round(math.hypot(*polar(COVER_R, a)), 2) for a, _ in COVERS]
violet_outside = [o.name for o in bpy.data.objects if o.type == "MESH" and C_FX not in o.users_collection
                  and any(s.material == VIO for s in o.material_slots)]

# ================================================================== presentation + renders
fc.ref_player(C_REF, (-8.0, 3.2, 0))
C_MOD.hide_render = True
C_COL.hide_render = True
bpy.context.view_layer.layer_collection.children[C_MOD.name].exclude = True
baked = fc.bake_unique_rotations(list(C_EXP.all_objects) + list(C_COL.objects) + list(C_FX.objects))


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
cam_eye = cam("CAM_EyeHeight", (-PORTAL_X + 0.8, -0.6, 1.7), target=(0.0, 0.5, 4.0))
sun_d = bpy.data.lights.new("LGT_Key_6500K", "SUN")
sun_d.energy = 2.5
sun = bpy.data.objects.new("LGT_Key_6500K", sun_d)
sun.rotation_euler = (math.radians(25), 0, math.radians(30))
C_PRES.objects.link(sun)
sc.world.use_nodes = True
bg = sc.world.node_tree.nodes.get("Background")
bg.inputs[0].default_value = fc.hex_lin("#C9D6E3")
bg.inputs[1].default_value = 0.6
renders = {}
top_hide = [bpy.data.objects[n] for n in ("SM_R3_Ceiling", "SM_R3_CeilingRibs")]
for o in top_hide:
    o.hide_render = True
sc.camera = cam_top
renders["topdown"] = fc.render(os.path.join(fc.RENDER_DIR, "R3_detail_topdown.png"), engine="BLENDER_EEVEE")
for o in top_hide:
    o.hide_render = False
sc.camera = cam_eye
renders["eye"] = fc.render(os.path.join(fc.RENDER_DIR, "R3_detail_eyeheight.png"), engine="BLENDER_EEVEE")
cam_hero = cam("CAM_Hero34", (-9.5, -10.0, 5.5), target=(1.0, 1.0, 3.5), lens=18)
sc.camera = cam_hero
renders["hero"] = fc.render(os.path.join(fc.RENDER_DIR, "R3_detail_hero34.png"), engine="BLENDER_EEVEE")
sun.hide_render = True
bg.inputs[1].default_value = 1.0
sc.camera = cam_eye
renders["eye_flat_ambient"] = fc.render(os.path.join(fc.RENDER_DIR, "R3_detail_eyeheight_flat.png"), engine="BLENDER_EEVEE")
sun.hide_render = False
bg.inputs[1].default_value = 0.6
sc.camera = cam_hero

_, uniq, inst = fc.tri_report([C_EXP])
_, fu, fi = fc.tri_report([C_FX])
report = {
    "arena": dict(diameter=2 * R, ceiling=H, wall_segments=SEGS),
    "core": dict(base_diameter=2 * CORE_R, rings=4, ring_rotation="local Z, alternating", column_to=H,
                 collision="12-sided cylinder r=3 to the ceiling (not climbable)"),
    "circulation_ring": dict(r=[CORE_R, RING_OUT], width=RING_OUT - CORE_R,
                             blocked_samples=f"{blocked}/{n_s} (0 = unobstructed)"),
    "nodes": {n: dict(angle=a, centre=[round(c, 3) for c in polar(NODE_C, a)], inner_face_r=RING_OUT, height=NODE_H,
                      glyph={"A": "triangle", "B": "trefoil", "C": "diamond"}[n]) for n, a in NODES.items()},
    "cover": [dict(angle=a, r=COVER_R, h=h) for a, h in COVERS],
    "entrances": dict(A_from_R2=[-PORTAL_X, 0, 0], B_alt=[PORTAL_X, 0, 0], w=DOOR_W, h=DOOR_H),
    "damage": dict(broken_wall_segments=list(BROKEN_PANELS), fallen_beam_angle=BEAM_ANG),
    "violet": dict(material="M_FX_Violet (R3_FX only)", fx_tris=fi, used_outside_fx=violet_outside),
    "R2_join": "translate R3 so LM_R3_FromR2 meets LM_R2_ToR3 (6 x 5 openings on both sides).",
    "landmarks": {k: [round(c, 3) for c in v] for k, v in landmarks.items()},
    "tris_export_unique": uniq, "tris_export_instanced": inst, "budget": 140000, "renders": renders,
}
blend = os.path.join(fc.SOURCE_DIR, f"Fractured_{ID}_{NAME}.blend")
glb = os.path.join(fc.EXPORT_DIR, f"Fractured_{ID}_{NAME}.glb")
glb_fx = os.path.join(fc.EXPORT_DIR, f"Fractured_{ID}_{NAME}_FX.glb")
report["qa"] = qa.run(ID, C_EXP, C_COL, C_FX, budget=140000, landmark_coll=C_LM, walk_bounds=(-R, R, -R, R),
                      walkable_prefixes=("COL_R3_Floor",),
                      walk_mask=lambda x, y: math.hypot(x, y) <= R - 0.4 and abs(x) < PORTAL_X - 0.1,
                      pair_with=os.path.join(fc.RENDER_DIR, "R3_blockout_landmarks.json"))
report["qa"]["pass"] = report["qa"]["pass"] and blocked == 0 and not violet_outside
report["rotations_baked"] = baked
report["blend"] = blend
fc.save(blend)
# FX ships as its own file (Block 0: <ID>_FX holds violet/transition effects only; the room export stays violet-free)
bpy.ops.object.select_all(action="DESELECT")
for o in C_FX.objects:
    o.select_set(True)
bpy.ops.export_scene.gltf(filepath=glb_fx, export_format="GLB", use_selection=True, export_extras=True, export_yup=True,
                          export_apply=True, export_cameras=False, export_lights=False)
report["glb_fx"] = glb_fx
report["qa"]["export"] = qa.export_and_verify(C_EXP, C_COL, glb)
report["glb"] = glb
with open(os.path.join(fc.RENDER_DIR, "R3_QA_report.json"), "w") as fh:
    json.dump(report, fh, indent=2)
print("R3 DETAIL DONE pass=", report["qa"]["pass"], "ring_blocked", blocked, "violet_outside", violet_outside)
