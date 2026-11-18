"""V1 Veyra Reclaimed Research Facility — built FROM the N1 file (brief: duplicate N1, keep landmarks).
Run: blender -b art/source/Fractured_N1_ResearchFacility.blend -P art/scripts/build_V1.py
"""
import os
import sys
import math
import json
import random
import bpy
import bmesh
from mathutils import Matrix, Vector, Euler

sys.path.insert(0, os.path.dirname(__file__))
import fractured_common as fc
import fractured_qa as qa

ID, NAME = "V1", "ReclaimedResearchFacility"
assert bpy.data.collections.get("N1_Export"), "open Fractured_N1_ResearchFacility.blend before running this script"
M = fc.append_shared_materials()
SIL, GLS, CYN, CHR, VCON, MOSS, BARK = (M[k] for k in (
    "M_NovaSilver", "M_NovaGlass", "M_CyanEmissive", "M_Charcoal", "M_VeyraConcrete", "M_Moss", "M_Bark"))

# ------------------------------------------------------------------ rename N1 -> V1 (landmarks keep their names)
for c in list(bpy.data.collections):
    if c.name.startswith("N1_"):
        c.name = "V1_" + c.name[3:]
for coll in (bpy.data.objects, bpy.data.meshes):
    for d in list(coll):
        for a, b in (("SM_N1_", "SM_V1_"), ("COL_N1_", "COL_V1_")):
            if d.name.startswith(a):
                d.name = b + d.name[len(a):]
C_EXP, C_ROOF, C_COL, C_FX, C_PRES, C_LM, C_MOD = (bpy.data.collections[f"V1_{n}"] for n in (
    "Export", "Roof", "Collision", "FX", "Presentation", "Landmarks", "ModuleSources"))
OB = bpy.data.objects

HX, HY, H = 14.0, 9.0, 12.0
BAL_Z, BAL_Y0 = 4.5, 6.0
STAIR_X0 = 12.0
PL_R, PL_H = 1.75, 0.6
OFF8 = math.pi / 8
RAMP_X0, RAMP_X1, RAMP_Y0, RAMP_Y1, RAMP_TOP = -13.6, -10.0, -2.8, 6.0, 4.53
RAMP_SLOPE = math.degrees(math.atan2(RAMP_TOP, RAMP_Y1 - RAMP_Y0))
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


def kill(name):
    o = OB.get(name)
    if o:
        bpy.data.objects.remove(o, do_unlink=True)


# ================================================================== 1. Veyra material pass on the Nova modules
def reskin(old, slot_map):
    me = bpy.data.meshes[old]
    me.name = old.replace("MOD_N_", "MOD_V_")
    for i, m in slot_map.items():
        me.materials[i] = m
    src = OB.get(old)
    if src:
        src.name = me.name
    return me


for n in ("MOD_N_Wall_4x4", "MOD_N_Wall_4x4_Seam", "MOD_N_Wall_2x4", "MOD_N_Wall_4x4_Door2x3", "MOD_N_Wall_4x4_Office"):
    reskin(n, {0: VCON, 2: CHR})                 # broken concrete, seams + office backlights unpowered
for n in ("MOD_N_Floor_4x4", "MOD_N_Floor_4x2", "MOD_N_Pilaster", "MOD_N_Pilaster_Lower", "MOD_N_Pilaster_Upper",
          "MOD_N_Corner_Outer", "MOD_N_Stair_2m_4.5rise"):
    reskin(n, {0: VCON})
bal = bpy.data.meshes["SM_V1_Balcony"]
bal.materials[0], bal.materials[1] = VCON, CHR     # balcony underlight dead
# kept powered (cyan) on purpose: exit door reveals + EXIT sign (wayfinding), one floor-ring arc, console 01

# ================================================================== 2. broken floor tiles (~35%)
def split_poly(poly, p, n):
    a, b = [], []
    for i in range(len(poly)):
        P, Q = poly[i], poly[(i + 1) % len(poly)]
        dp = (P[0] - p[0]) * n[0] + (P[1] - p[1]) * n[1]
        dq = (Q[0] - p[0]) * n[0] + (Q[1] - p[1]) * n[1]
        (a if dp >= 0 else b).append(P)
        if (dp >= 0) != (dq >= 0):
            t = dp / (dp - dq)
            X = (P[0] + t * (Q[0] - P[0]), P[1] + t * (Q[1] - P[1]))
            a.append(X)
            b.append(X)
    return [q for q in (a, b) if len(q) >= 3]


def area2(poly):
    return 0.5 * sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1]
                     for i in range(len(poly)))


def broken_tile(sx, sy, seed, border=0.3, t=0.2):
    """A8 rule: outer 0.3 m border flat & intact; cracked plates inside lifted 0-0.2 m; charcoal subfloor in cracks."""
    rng = random.Random(seed)
    hx, hy, ix, iy = sx / 2, sy / 2, sx / 2 - border, sy / 2 - border
    pts, faces, mats = fc.grid2d([-hx, -ix, ix, hx], [-hy, -iy, iy, hy], lambda i, j: not (i == 1 and j == 1))
    frame = fc.xform(fc.extrude2d(pts, faces, mats, t), rot_x=90)          # XY grid, thickness +Z
    sub = (*fc.box_minmax(-ix, ix, -iy, iy, 0.0, 0.12, skip=("bottom", "front", "back", "left", "right")), 1)
    polys = [[(-ix, -iy), (ix, -iy), (ix, iy), (-ix, iy)]]
    for _ in range(3 if sy > 3 else 2):
        p = (rng.uniform(-ix * 0.5, ix * 0.5), rng.uniform(-iy * 0.5, iy * 0.5))
        a = rng.uniform(0, math.pi)
        n = (math.cos(a), math.sin(a))
        polys = [q for poly in polys for q in split_poly(poly, p, n)]
    plates, plate_data = [], []
    for k, poly in enumerate(polys):
        if area2(poly) < 0 :
            poly = poly[::-1]
        if abs(area2(poly)) < 0.08:
            continue
        cx = sum(p[0] for p in poly) / len(poly)
        cy = sum(p[1] for p in poly) / len(poly)
        ins = []
        for x, y in poly:
            d = math.hypot(cx - x, cy - y) or 1
            ins.append((x + (cx - x) / d * 0.035, y + (cy - y) / d * 0.035))
        lift = rng.choice([0.0, 0.0, 0.05, 0.08, 0.12, 0.14])
        ax, ay = rng.uniform(-0.035, 0.035), rng.uniform(-0.035, 0.035)
        top = lambda x, y, cx=cx, cy=cy, lift=lift, ax=ax, ay=ay: min(t + 0.2, max(t - 0.02, t + lift + ax * (x - cx) + ay * (y - cy)))
        pr = fc.prism(ins, 0.1, top, cap_mat=0, top_mat=2 if rng.random() < 0.15 else 0)
        plates.append(pr)
        plate_data.append(fc.prism(ins, 0.1, top))
    return fc.mparts(frame, sub, *plates), plate_data


bt4, bt4_plates = broken_tile(4, 4, 3)
bt2, bt2_plates = broken_tile(4, 2, 5)
me_bt = {4: module("MOD_V_Floor_Broken_4x4", bt4, [VCON, CHR, MOSS]),
         2: module("MOD_V_Floor_Broken_4x2", bt2, [VCON, CHR, MOSS])}
plates_local = {4: bt4_plates, 2: bt2_plates}

consoles_xy = [tuple(OB[f"SM_Console_0{i}"].location[:2]) for i in (1, 2, 3)]
floor_tiles = sorted([o for o in C_EXP.objects if o.name.startswith("SM_V1_Floor_")], key=lambda o: o.name)


def tile_ok(o):
    w = 4 if o.data.name.endswith("4x4") else 2
    x, y = o.location.x, o.location.y
    x0, x1, y0, y1 = x - 2, x + 2, y - w / 2, y + w / 2
    if any(x0 - 0.8 < cx < x1 + 0.8 and y0 - 0.8 < cy < y1 + 0.8 for cx, cy in consoles_xy):
        return False
    nx_, ny_ = min(max(0.0, x0), x1), min(max(0.0, y0), y1)
    if math.hypot(nx_, ny_) < 4.7:                                       # vessel, steps and the cyan ring inlay
        return False
    if x0 < RAMP_X1 and x1 > RAMP_X0 and y0 < RAMP_Y1 and y1 > RAMP_Y0:  # under the root ramp
        return False
    return True


rng = random.Random(11)
eligible = [o for o in floor_tiles if tile_ok(o)]
broken = rng.sample(eligible, round(0.35 * len(floor_tiles)))
col_plates = []
for o in broken:
    w = 4 if o.data.name.endswith("4x4") else 2
    o.data = me_bt[w]
    o.rotation_euler.z = math.radians(rng.choice([0, 90, 180, 270] if w == 4 else [0, 180]))
    o.name = o.name.replace("SM_V1_Floor_", "SM_V1_FloorBroken_")
    mw = Matrix.Translation(o.location) @ Matrix.Rotation(o.rotation_euler.z, 4, "Z")
    for pv, pf, _ in plates_local[w]:
        col_plates.append(([tuple(mw @ Vector(p)) for p in pv], pf))
log["floor_tiles_broken"] = f"{len(broken)}/{len(floor_tiles)} ({100 * len(broken) / len(floor_tiles):.0f}%)"
broken_rects = [(o.location.x, o.location.y, 4 if "4x4" in o.data.name else 2) for o in broken]

# ================================================================== 3. vessel: shattered glass, no crystal, cracked cap, ring arc dark
kill("SM_Vessel_Glass")
kill("SM_Vessel_Crystal")
NF, GR = 16, 1.5
FW = 2 * GR * math.sin(math.pi / NF)
FD = GR * math.cos(math.pi / NF)
pattern = ["B", "S", "BT", "S", "B", "T", "S", "B", "S", "BT", "S", "S", "B", "T", "S", "B"]
grng = random.Random(21)
raw = []
for kind in pattern:
    pm = grng.uniform(-FW * 0.3, FW * 0.3)
    b = (grng.uniform(0.6, 1.0), grng.uniform(0.6, 1.0), grng.uniform(1.0, 1.4)) if "B" in kind else None
    s = (grng.uniform(0.1, 0.3), grng.uniform(0.1, 0.3), grng.uniform(0.35, 0.55)) if kind == "S" else None
    t = (grng.uniform(0.5, 0.9), grng.uniform(0.5, 0.9), grng.uniform(1.0, 1.3)) if "T" in kind else None
    raw.append((pm, b, s, t))


def shard_layout(kb, kt):
    shapes, area = [], 0.0
    for pm, b, s, t in raw:
        if b:
            hl, hr, hp = (v * kb for v in b)
            shapes.append(("B", [(-FW / 2, 0), (FW / 2, 0), (FW / 2, hr), (pm, hp), (-FW / 2, hl)]))
            area += FW * (hl + hr) / 2 + FW * (hp - (hl + hr) / 2) / 2
        if s:
            hl, hr, hp = s
            shapes.append(("B", [(-FW / 2, 0), (FW / 2, 0), (FW / 2, hr), (pm, hp), (-FW / 2, hl)]))
            area += FW * (hl + hr) / 2 + FW * (hp - (hl + hr) / 2) / 2
        if t:
            hl, hr, hp = (6.0 - v * kt for v in t)
            shapes.append(("T", [(-FW / 2, hl), (pm, hp), (FW / 2, hr), (FW / 2, 6.0), (-FW / 2, 6.0)]))
            area += FW * (6 - (hl + hr) / 2) - FW * ((hl + hr) / 2 - hp) / 2
    return shapes, area / (NF * FW * 6.0)


k_lo, k_hi = 0.5, 4.5
for _ in range(40):                                    # solve for ~40 % remaining glass
    k = (k_lo + k_hi) / 2
    _, ratio = shard_layout(k, k * 0.8)
    k_lo, k_hi = (k, k_hi) if ratio < 0.40 else (k_lo, k)
shapes, ratio = shard_layout(k, k * 0.8)
log["vessel_glass_remaining"] = f"{ratio * 100:.1f}%"
shard_parts = []
si = 0
for f_idx, (pm, b, s, t) in enumerate(raw):
    theta = math.pi / NF + 2 * math.pi * f_idx / NF
    for _ in range(sum(1 for x in (b, s, t) if x)):
        kind, poly = shapes[si]
        si += 1
        poly = [(x, min(5.98, max(0.0, z))) for x, z in poly]
        fan = [(0, i, i + 1) for i in range(1, len(poly) - 1)]
        d = fc.extrude2d(poly, fan, [0] * len(fan), 0.05)
        shard_parts.append(fc.xform(d, rot_z=math.degrees(theta) + 90,
                                    offset=(FD * math.cos(theta), FD * math.sin(theta), 0)))
ribs = [fc.xform((*fc.box_minmax(1.52, 1.6, -0.04, 0.04, 0, 6.0), [1] * 6), rot_z=45 * k + 22.5)
        for k in range(8) if k not in (2, 5)]                    # two frame ribs torn away
place("SM_Vessel_Glass_Broken", mesh("SM_Vessel_Glass_Broken", fc.mparts(*shard_parts, *ribs), [GLS, SIL]),
      (0, 0, PL_H))


def lathe_sector(profile, a0, a1):
    V, F = [], []
    A, Bv = [], []
    for r, z in profile:
        if r <= 1e-9:
            V.append((0, 0, z))
            A.append(len(V) - 1)
            Bv.append(len(V) - 1)
        else:
            V.append((r * math.cos(a0), r * math.sin(a0), z))
            A.append(len(V) - 1)
            V.append((r * math.cos(a1), r * math.sin(a1), z))
            Bv.append(len(V) - 1)
    for i in range(len(profile) - 1):
        q = [A[i], Bv[i], Bv[i + 1], A[i + 1]]
        q = [x for j, x in enumerate(q) if x not in q[:j]]
        F.append(tuple(q))
    n = len(profile)
    for i in range(1, n - 1):
        F.append((A[0], A[i + 1], A[i]))
        F.append((Bv[0], Bv[i], Bv[i + 1]))
    return V, F


cap_prof = [(0, 0), (1.6, 0), (1.8, 0.15), (1.8, 0.3), (1.8, 0.5), (1.8, 0.65), (1.5, 0.8), (0, 0.8)]
cap_parts = []
for s in range(8):
    if s == 3:
        continue                                                      # sector broken out
    a0, a1 = OFF8 + s * math.pi / 4, OFF8 + (s + 1) * math.pi / 4
    v, f = lathe_sector(cap_prof, a0 + 0.01, a1 - 0.01)               # 1 cm crack between sectors
    band = 0 if s in (2, 4) else 2
    m = [0, 1, 0, band, 0, 1, 0] + [0] * (len(f) - 7)
    if s == 2:                                                        # cracked sector sagging
        mid = (a0 + a1) / 2
        axis = Vector((-math.sin(mid), math.cos(mid), 0))
        piv = Vector((0.9 * math.cos(mid), 0.9 * math.sin(mid), 0))
        R = Matrix.Rotation(math.radians(-7), 3, axis)
        v = [tuple(R @ (Vector(p) - piv) + piv + Vector((0, 0, -0.12))) for p in v]
    cap_parts.append((v, f, m))
cap_me = mesh("SM_Vessel_Cap_Cracked", fc.mparts(*cap_parts), [CHR, SIL, CYN], recalc=True)
OB["SM_Vessel_Cap"].data = cap_me

RING_R, RING_W = 4.5, 0.2
ring = fc.lathe([(RING_R + RING_W / 2, 0), (RING_R + RING_W / 2, 0.01), (RING_R - RING_W / 2, 0.01),
                 (RING_R - RING_W / 2, 0)], 64)
ring_m = [1 if 40 <= j < 48 else 0 for _ in range(3) for j in range(64)]
ring_o = OB["SM_V1_FloorRing"]
ring_o.data = mesh("SM_V1_FloorRing", (*ring, ring_m), [CYN, CHR])
ring_o["flicker"] = True
ring_o["dark_segment_deg"] = [225, 270]

# ================================================================== 4. damaged consoles (shared damaged base)
ztop = lambda x, y: 0.95 + (y + 0.4) / 0.8 * 0.15
desk = fc.slab_grid([-0.6, -0.48, 0.48, 0.6], [-0.4, -0.3, 0.28, 0.4], 0.85, ztop,
                    lambda i, j: 2 if (i == 1 and j == 1) else 1, side_mat=1)
o_ = [(-0.25, 0.12), (0.4, 0.12), (0.4, 0.85), (-0.25, 0.85)]
i_ = [(-0.2, 0.17), (0.35, 0.17), (0.35, 0.8), (-0.2, 0.8)]
X0, X1 = 0.6, 0.52
pv = [(X0, y, z) for y, z in o_] + [(X0, y, z) for y, z in i_] + [(X1, y, z) for y, z in i_]
pf, pm_ = [], []
for k in range(4):
    j = (k + 1) % 4
    pf.append((k, j, 4 + j, 4 + k)); pm_.append(0)            # silver frame around missing panel
    pf.append((4 + k, 4 + j, 8 + j, 8 + k)); pm_.append(1)    # charcoal reveal
pf.append((8, 9, 10, 11)); pm_.append(1)                      # dark interior
con_dmg = fc.mparts(
    (*fc.box_minmax(-0.55, 0.55, -0.3, 0.35, 0, 0.12, skip=("bottom",)), 1),
    (*fc.box_minmax(-0.6, 0.6, -0.25, 0.4, 0.12, 0.85, skip=("bottom", "right")), 0),
    (pv, pf, pm_),
    desk,
)
me_cdmg = module("MOD_V_Console_Base_Damaged", con_dmg, [SIL, CHR, GLS])


def cracked_monitor(x0, x1, alive, z0=1.06, z1=1.62, y0=0.24, d=0.1, b=0.04):
    xs, zs = [x0, x0 + b, x1 - b, x1], [z0, z0 + b, z1 - b, z1]
    pts, faces, mats = fc.grid2d(xs, zs, lambda i, j: not (i == 1 and j == 1))
    find = lambda x, z: next(n for n, p in enumerate(pts) if abs(p[0] - x) < 1e-6 and abs(p[1] - z) < 1e-6)
    c00, c10, c11, c01 = find(xs[1], zs[1]), find(xs[2], zs[1]), find(xs[2], zs[2]), find(xs[1], zs[2])
    faces += [(c00, c10, c11), (c00, c11, c01)]
    mats += [1 if alive else 2, 0]                               # one half shattered black
    return fc.extrude2d(pts, faces, mats, d, y0, side_mat=0)


def numeral(ch, mat):
    gp_, gf_, _ = fc.glyphs(ch, 0.1, 0.0, 0.25)
    return fc.extrude2d(gp_, gf_, [mat] * len(gf_), 0.03, -0.28, back=False)


pil = [(0.3, 0.12), (0.55, 0.12), (0.55, 0.38), (0.3, 0.38)]
TOPS = {   # mats [CHR, CYN, GLS, SIL]; numerals cyan only on the console that still has power
    "01": [cracked_monitor(-0.4, 0.4, True), numeral("1", 1)],
    "02": [cracked_monitor(-0.58, -0.04, False), cracked_monitor(0.04, 0.58, False), numeral("2", 0)],
    "03": [cracked_monitor(-0.55, 0.15, False), fc.prism(pil, 1.06, 1.75, cap_mat=3), numeral("3", 0)],
}
for n, parts in TOPS.items():
    c = OB[f"SM_Console_{n}"]
    kill(f"SM_Console_{n}_Top")
    c.data = me_cdmg
    c.name = f"SM_Console_{n}_Damaged"
    t = place(f"SM_Console_{n}_Damaged_Top", mesh(f"SM_Console_{n}_Damaged_Top", fc.mparts(*parts),
                                                  [CHR, CYN, GLS, SIL]))
    t.parent = c
    c["powered"] = n == "01"

# ================================================================== 5. root segments (reusable modules) + systems
def tube(path, radii, sides=8, twist=0.0, jitter=0.0, seed=0):
    rng_ = random.Random(seed)
    P = [Vector(p) for p in path]
    n = len(P)
    T = [((P[min(i + 1, n - 1)] - P[max(i - 1, 0)]).normalized()) for i in range(n)]
    up = Vector((0, 0, 1)) if abs(T[0].z) < 0.9 else Vector((1, 0, 0))
    nrm = (up - T[0] * up.dot(T[0])).normalized()
    V, F, rings = [], [], []
    for i in range(n):
        if i:
            nrm = T[i - 1].rotation_difference(T[i]) @ nrm
            nrm = (nrm - T[i] * nrm.dot(T[i])).normalized()
        b = T[i].cross(nrm)
        inner = 0 < i < n - 1
        ring = []
        for k in range(sides):
            a = 2 * math.pi * k / sides + (twist if inner else 0)
            r = radii[i] * (1 + (rng_.uniform(-jitter, jitter) if inner else 0))
            V.append(tuple(P[i] + r * (math.cos(a) * nrm + math.sin(a) * b)))
            ring.append(len(V) - 1)
        rings.append(ring)
    for A, Bq in zip(rings, rings[1:]):
        for k in range(sides):
            j = (k + 1) % sides
            F.append((A[k], A[j], Bq[j], Bq[k]))
    c = len(V)
    V.append(tuple(P[0]))
    F += [(c, rings[0][(k + 1) % sides], rings[0][k]) for k in range(sides)]
    c = len(V)
    V.append(tuple(P[-1]))
    F += [(rings[-1][k], rings[-1][(k + 1) % sides], c) for k in range(sides)]
    return V, F


R_C = 1.2
seg = {
    "S": tube([(0, 0, 0), (0, 1, 0), (0, 2, 0)], [0.32, 0.36, 0.32], twist=0.3, jitter=0.12, seed=1),
    "C": tube([(0, R_C * math.sin(a), R_C * (1 - math.cos(a))) for a in [math.radians(d) for d in range(0, 91, 18)]],
              [0.32, 0.34, 0.36, 0.35, 0.33, 0.32], twist=0.25, jitter=0.1, seed=2),
    "J": fc.merge(tube([(0, 0, 0), (0, 0.5, 0), (0, 1.0, 0), (0, 1.5, 0)], [0.32, 0.36, 0.34, 0.32], twist=0.2,
                       jitter=0.1, seed=3),
                  tube([(0, 0.5, 0)] + [(math.sin(math.radians(40)) * d, 0.5 + math.cos(math.radians(40)) * d,
                                         -0.08 * d) for d in (0.5, 1.0, 1.6)], [0.22, 0.2, 0.16, 0.08], seed=4)),
    "A": tube([(-1.4 * math.cos(t), 0, 2.6 * math.sin(t) - 0.05) for t in [math.pi * k / 9 for k in range(10)]],
              [0.36, 0.33, 0.31, 0.3, 0.3, 0.3, 0.3, 0.31, 0.33, 0.36], twist=0.2, jitter=0.08, seed=5),
}
seg_names = {"S": "MOD_V_Root_Straight", "C": "MOD_V_Root_Curve", "J": "MOD_V_Root_Junction", "A": "MOD_V_RootArch"}
ROOT_ME = {k: module(seg_names[k], (*seg[k], [0] * len(seg[k][1])), [BARK], recalc=True) for k in seg}
ROOT_END = {"S": Matrix.Translation((0, 2, 0)),
            "C": Matrix.Translation((0, R_C, R_C)) @ Matrix.Rotation(math.radians(90), 4, "X"),
            "J": Matrix.Translation((0, 1.5, 0))}
root_objs = []


def chain(name, start, heading, pitch, seq):
    T = Matrix.Translation(start) @ Matrix.Rotation(math.radians(heading), 4, "Z") @ \
        Matrix.Rotation(math.radians(pitch), 4, "X")
    for k, s in enumerate(seq):
        o = place(f"{name}_{k:02d}", ROOT_ME[s])
        o.matrix_world = T
        root_objs.append(o)
        T = T @ ROOT_END[s]


chain("SM_V1_Root_A", (-8.4, -7.0, 0), 90, 0, "SSCSSS")        # floor -> climbs west wall
chain("SM_V1_Root_B", (8.0, 5.9, 0), 0, 0, "JCS")              # floor -> climbs north wall under balcony
for name, a in (("SM_V1_Root_C", 45), ("SM_V1_Root_D", 135)):    # wrap/climb the vessel base (behind it)
    ar = math.radians(a)
    chain(name, (3.6 * math.cos(ar), 3.6 * math.sin(ar), 0), a + 90, 0, "CS")
# root-supported ramp (alternate route to the balcony): two stringer roots + arch support
chain("SM_V1_Root_RampL", (-13.28, RAMP_Y0 + 0.2, 0.3), 0, RAMP_SLOPE, "SSSSS")
chain("SM_V1_Root_RampR", (-10.25, RAMP_Y0 + 0.2, 0.3), 0, RAMP_SLOPE, "SSSSS")
arch = place("SM_V1_Root_RampArch", ROOT_ME["A"], ((RAMP_X0 + RAMP_X1) / 2, 3.5, 0))
root_objs.append(arch)

cx = (RAMP_X0 + RAMP_X1) / 2
ramp_center = lambda y: RAMP_TOP if y >= RAMP_Y1 else (y - RAMP_Y0) / (RAMP_Y1 - RAMP_Y0) * RAMP_TOP
ramp_top = lambda x, y: ramp_center(y) - (0.15 if abs(x - cx) > (RAMP_X1 - RAMP_X0) / 2 - 0.3 + 1e-6 else 0.0)
deck = fc.slab_grid([RAMP_X0, RAMP_X0 + 0.3, RAMP_X1 - 0.3, RAMP_X1], [RAMP_Y0, -0.6, 1.6, 3.8, RAMP_Y1, RAMP_Y1 + 0.4],
                    lambda x, y: ramp_center(y) - 0.35, ramp_top, lambda i, j: 0 if i == 1 else 1, side_mat=0)
place("SM_V1_RootRamp", mesh("SM_V1_RootRamp", deck, [BARK, MOSS]))
kill("SM_V1_BalconyRail_00")                                     # railing bay torn out where the ramp lands

# ================================================================== 6. rubble blocking the N1 stair
def rubble(seed, n=8, w=2.3, d=2.0, h=1.8):
    rng_ = random.Random(seed)
    parts = []
    for k in range(n):
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.0)
        s = (rng_.uniform(0.4, 0.75), rng_.uniform(0.35, 0.7), rng_.uniform(0.3, 0.55))
        R = Euler((rng_.uniform(0, 3), rng_.uniform(0, 3), rng_.uniform(0, 3))).to_matrix()
        c = Vector((rng_.uniform(-w / 2 + 0.45, w / 2 - 0.45), rng_.uniform(-d / 2 + 0.4, d / 2 - 0.4),
                    s[2] * 0.6 + (rng_.uniform(0.3, h - 0.9) if k >= 4 else 0)))
        vs = [R @ Vector((v.co.x * s[0] * rng_.uniform(0.85, 1.15), v.co.y * s[1] * rng_.uniform(0.85, 1.15),
                          v.co.z * s[2])) + c for v in bm.verts]
        parts.append(([tuple(v) for v in vs], [tuple(v.index for v in f.verts) for f in bm.faces],
                      [1 if k % 4 == 3 else 0] * len(bm.faces)))
        bm.free()
    return fc.mparts(*parts)


me_rub = mesh("SM_Rubble_Cluster", rubble(31), [VCON, CHR], recalc=True)
rub = [place("SM_Rubble_Cluster_01", me_rub, (13.0, -0.5, 0.0), 0),
       place("SM_Rubble_Cluster_02", me_rub, (13.0, 2.6, 2.1), 90)]

# ================================================================== 7. moss patches (flat, horizontal only) + vine cards
def moss_patch(seed, r):
    rng_ = random.Random(seed)
    n = 9
    ring = [(r * rng_.uniform(0.75, 1.1) * math.cos(2 * math.pi * k / n),
             r * rng_.uniform(0.75, 1.1) * math.sin(2 * math.pi * k / n)) for k in range(n)]
    V = [(0, 0, 0.02)] + [(x, y, 0.02) for x, y in ring] + [(x, y, 0.0) for x, y in ring]
    F = [(0, 1 + k, 1 + (k + 1) % n) for k in range(n)]
    F += [(1 + n + k, 1 + n + (k + 1) % n, 1 + (k + 1) % n, 1 + k) for k in range(n)]
    area = sum(0.5 * (ring[k][0] * ring[(k + 1) % n][1] - ring[(k + 1) % n][0] * ring[k][1]) for k in range(n))
    return (V, F, [0] * len(F)), area


moss_me, moss_area = [], []
for i, r in enumerate((0.9, 1.3, 1.7)):
    d, a = moss_patch(40 + i, r)
    moss_me.append(module(f"SM_Moss_Patch_0{i + 1}", d, [MOSS]))
    moss_area.append(a)
mrng = random.Random(9)
unbroken = [o for o in C_EXP.objects if o.name.startswith("SM_V1_Floor_") and tile_ok(o)]
moss_spots = [(o.location.x + mrng.uniform(-1, 1), o.location.y + mrng.uniform(-0.5, 0.5), 0.0)
              for o in mrng.sample(unbroken, min(9, len(unbroken)))]
moss_spots += [(-6.0, 7.6, BAL_Z), (2.5, 7.9, BAL_Z), (9.0, 7.4, BAL_Z), (-11.8, 1.0, ramp_center(1.0))]
total_moss = 0.0
for i, (x, y, z) in enumerate(moss_spots):
    if z > 0 and abs(x - cx) < 2:                    # patch on the ramp deck: skip (deck is sloped; moss edges exist)
        continue
    k = i % 3
    place(f"SM_V1_Moss_{i:02d}", moss_me[k], (x, y, z), mrng.uniform(0, 360))
    total_moss += moss_area[k]
log["moss_coverage"] = f"{100 * total_moss / (2 * HX * 2 * HY + 2 * HX * 3):.1f}% of floor+balcony (limit 15%)"


def vine_card(L, w=0.45):
    V = [(-w / 2, 0, -L + 0.5), (0, 0, -L), (w / 2, 0, -L + 0.5), (w / 2, 0, 0), (-w / 2, 0, 0)]
    Vb = [(x, 0.005, z) for x, _, z in V]
    F = [(0, 1, 2), (0, 2, 3, 4), (5, 7, 6), (5, 9, 8, 7)]
    return V + Vb, F, [0] * 4


vine_me = {L: module(f"MOD_V_VineCard_{L:g}m", vine_card(L), [MOSS]) for L in (2.5, 3.5)}

# ================================================================== 8. roof: 40 % panes missing, some frames bent
def frame_only(src_name, new_name, sag=0.0):
    bm = bmesh.new()
    bm.from_mesh(bpy.data.meshes[src_name])
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index == 1], context="FACES_ONLY")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    if sag:
        for v in bm.verts:
            if v.co.y > 0.5:
                v.co.z -= sag * math.cos(math.pi * v.co.x / 4.0) * min(1.0, (v.co.y - 0.5) / 1.3)
    me = bpy.data.meshes.new(new_name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(CHR)
    me.materials.append(GLS)
    fc.obj(new_name, me, C_MOD)
    return me


sky_broken = {4: frame_only("MOD_N_Skylight_4x4", "MOD_V_Skylight_4x4_Broken"),
              2: frame_only("MOD_N_Skylight_4x2", "MOD_V_Skylight_4x2_Broken")}
sky_bent = frame_only("MOD_N_Skylight_4x4", "MOD_V_Skylight_4x4_Bent", sag=0.35)
skys = sorted([o for o in C_ROOF.objects], key=lambda o: o.name)
srng = random.Random(17)
missing = srng.sample(skys, round(0.4 * len(skys)))
vi = 0
for k, o in enumerate(missing):
    w = 4 if o.data.name.endswith("4x4") else 2
    o.data = sky_bent if (w == 4 and k % 3 == 0) else sky_broken[w]
    if vi < 8:                                                     # vines hang through the open bays
        for dx in (-1.2, 1.1):
            if vi >= 8:
                break
            L = 2.5 if vi % 2 else 3.5
            place(f"SM_V1_Vine_{vi:02d}", vine_me[L], (o.location.x + dx, o.location.y + srng.uniform(-1.2, 1.2),
                                                       H - 0.02), srng.uniform(0, 180))
            vi += 1
log["skylight_panes_missing"] = f"{len(missing)}/{len(skys)} ({100 * len(missing) / len(skys):.0f}%)"

# ================================================================== 9. collision updates
def hull_parts(objs):
    out = []
    for o in objs:
        mw = o.matrix_world
        bm = bmesh.new()
        for v in o.data.vertices:
            bm.verts.new(mw @ v.co)
        res = bmesh.ops.convex_hull(bm, input=bm.verts[:])
        dead = list({g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)})
        bmesh.ops.delete(bm, geom=dead, context="VERTS")
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.verts.index_update()
        out.append(([tuple(v.co) for v in bm.verts], [tuple(v.index for v in f.verts) for f in bm.faces]))
        bm.free()
    return out


def col(name, data):
    o = fc.obj(f"{name}-colonly", fc.build_mesh(name, data, weld=False), C_COL)   # shells stay separate
    o.display_type = "WIRE"
    return o


bpy.context.view_layer.update()
col("COL_V1_Roots", fc.merge(*hull_parts(root_objs)))
col("COL_V1_Rubble", fc.merge(*hull_parts(rub)))
col("COL_V1_FloorBroken", fc.merge(*col_plates))
col("COL_V1_RootRamp", fc.merge(fc.wedge_data(RAMP_X0, RAMP_X1, RAMP_Y0, RAMP_Y1, RAMP_TOP),
                                 fc.box_minmax(RAMP_X0, RAMP_X1, RAMP_Y1, RAMP_Y1 + 0.4, BAL_Z, RAMP_TOP)))
OB["COL_V1_BalconyRail-colonly"].data = fc.build_mesh(
    "COL_V1_BalconyRail", fc.box_minmax(RAMP_X1, STAIR_X0, BAL_Y0 + 0.04, BAL_Y0 + 0.16, BAL_Z, BAL_Z + 1.1))
for o in C_COL.objects:
    o.display_type = "WIRE"

# landmarks: inherited from N1 untouched; V1-only route landmarks added
fc.empty("LM_RootRamp", (cx, RAMP_Y0, 0.0), C_LM, 0.8, "ARROWS").hide_render = True
fc.empty("LM_RootRamp_Top", (cx, RAMP_Y1, RAMP_TOP), C_LM, 0.8, "ARROWS").hide_render = True

baked = fc.bake_unique_rotations(list(C_EXP.all_objects) + list(C_COL.objects))

# ================================================================== 10. presentation: warm 4000K shafts, dimmer ambient
sun = OB["LGT_Key_6500K"]
sun.name = sun.data.name = "LGT_Key_4000K"
try:
    sun.data.use_temperature, sun.data.temperature = True, 4000
except Exception:
    sun.data.color = (1.0, 0.82, 0.62)
sun.data.energy = 4.5
sun.rotation_euler = (math.radians(38), 0, math.radians(-32))
sc = bpy.context.scene
bgn = sc.world.node_tree.nodes.get("Background")
bgn.inputs[0].default_value = fc.hex_lin("#B9AE97")
bgn.inputs[1].default_value = 0.32
OB["REF_Player"].hide_render = True

renders = {}
C_ROOF.hide_render = True
sc.camera = OB["CAM_TopDown"]
renders["topdown"] = fc.render(os.path.join(fc.RENDER_DIR, "V1_detail_topdown.png"), engine="BLENDER_EEVEE")
C_ROOF.hide_render = False
sc.camera = OB["CAM_EyeHeight"]
renders["eye"] = fc.render(os.path.join(fc.RENDER_DIR, "V1_detail_eyeheight.png"), engine="BLENDER_EEVEE")
sc.camera = OB["CAM_Hero34"]
renders["hero"] = fc.render(os.path.join(fc.RENDER_DIR, "V1_detail_hero34.png"), engine="BLENDER_EEVEE")
cam_ramp = bpy.data.objects.new("CAM_RampCheck", bpy.data.cameras.new("CAM_RampCheck"))
cam_ramp.data.lens = 24
cam_ramp.location = (-4.0, -8.3, 2.2)
C_PRES.objects.link(cam_ramp)
fc.look_at(cam_ramp, (-11.0, 3.0, 2.6))
sc.camera = cam_ramp
renders["ramp_route"] = fc.render(os.path.join(fc.RENDER_DIR, "V1_detail_ramp_route.png"), engine="BLENDER_EEVEE")
sun.hide_render = True
bgn.inputs[1].default_value = 1.0
sc.camera = OB["CAM_EyeHeight"]
renders["eye_flat_ambient"] = fc.render(os.path.join(fc.RENDER_DIR, "V1_detail_eyeheight_flat.png"), engine="BLENDER_EEVEE")
sun.hide_render = False
bgn.inputs[1].default_value = 0.32
sc.camera = OB["CAM_Hero34"]

# ================================================================== 11. Block Z + export
blend = os.path.join(fc.SOURCE_DIR, f"Fractured_{ID}_{NAME}.blend")
glb = os.path.join(fc.EXPORT_DIR, f"Fractured_{ID}_{NAME}.glb")
report = qa.run(ID, C_EXP, C_COL, C_FX, budget=140000, landmark_coll=C_LM,
                walk_bounds=(-HX, HX, -HY, HY),
                walkable_prefixes=("COL_V1_Floor", "COL_V1_FloorBroken", "COL_V1_Balcony", "COL_V1_Stair",
                                   "COL_Vessel_Steps", "COL_V1_RootRamp"),
                pair_with=os.path.join(fc.RENDER_DIR, "N1_landmarks.json"))
report["v1_changes"] = log
report["ramp"] = dict(x=[RAMP_X0, RAMP_X1], y=[RAMP_Y0, RAMP_Y1], top=RAMP_TOP, slope_deg=round(RAMP_SLOPE, 1),
                      deck_width=RAMP_X1 - RAMP_X0, clear_between_roots=round((RAMP_X1 - 0.57) - (RAMP_X0 + 0.62), 2))
report["rotations_baked"] = baked
report["renders"] = renders
report["blend"] = blend
fc.save(blend)
report["export"] = qa.export_and_verify(C_EXP, C_COL, glb)
report["glb"] = glb
with open(os.path.join(fc.RENDER_DIR, "V1_QA_report.json"), "w") as fh:
    json.dump(report, fh, indent=2)
print("V1 DONE", json.dumps(log))
