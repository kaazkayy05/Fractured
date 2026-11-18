"""Veyra (reclaimed) piece generators shared by V2+ rooms and the A8 kit. Each returns raw (verts, faces[, mats]).
Faceted, no fine detail: roots are 8-sided tubes, rubble is jittered icospheres, vines are planar cards.
"""
import math
import random
import bpy
import bmesh
from mathutils import Matrix, Vector, Euler

import fractured_common as fc

BM = fc.box_minmax


# ------------------------------------------------------------------ roots
def tube(path, radii, sides=8, twist=0.0, jitter=0.0, seed=0, return_rings=False):
    """Faceted tube along a polyline (parallel-transport frames), capped. Closed; build with recalc=True.
    return_rings=True also returns the per-ring vertex positions (for per-segment collision hulls)."""
    rng = random.Random(seed)
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
            r = radii[i] * (1 + (rng.uniform(-jitter, jitter) if inner else 0))
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
    if return_rings:
        return V, F, [[V[i] for i in ring] for ring in rings]
    return V, F


def hull_points(points_list):
    """Convex hull per point set -> list of (verts, faces). Used for segment-wise root/branch collision."""
    out = []
    for pts in points_list:
        bm = bmesh.new()
        for p in pts:
            bm.verts.new(p)
        res = bmesh.ops.convex_hull(bm, input=bm.verts[:])
        dead = list({g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)})
        bmesh.ops.delete(bm, geom=dead, context="VERTS")
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.verts.index_update()
        out.append(([tuple(v.co) for v in bm.verts], [tuple(v.index for v in f.verts) for f in bm.faces]))
        bm.free()
    return out


R_CURVE = 1.2
ROOT_NAMES = {"S": "MOD_V_Root_Straight", "C": "MOD_V_Root_Curve", "J": "MOD_V_Root_Junction", "A": "MOD_V_RootArch"}


def root_segments():
    """Reusable root segments; each starts at the origin heading +Y with up +Z."""
    return {
        "S": tube([(0, 0, 0), (0, 1, 0), (0, 2, 0)], [0.32, 0.36, 0.32], twist=0.3, jitter=0.12, seed=1),
        "C": tube([(0, R_CURVE * math.sin(a), R_CURVE * (1 - math.cos(a)))
                   for a in [math.radians(d) for d in range(0, 91, 18)]],
                  [0.32, 0.34, 0.36, 0.35, 0.33, 0.32], twist=0.25, jitter=0.1, seed=2),
        "J": fc.merge(tube([(0, 0, 0), (0, 0.5, 0), (0, 1.0, 0), (0, 1.5, 0)], [0.32, 0.36, 0.34, 0.32], twist=0.2,
                           jitter=0.1, seed=3),
                      tube([(0, 0.5, 0)] + [(math.sin(math.radians(40)) * d, 0.5 + math.cos(math.radians(40)) * d,
                                             -0.08 * d) for d in (0.5, 1.0, 1.6)], [0.22, 0.2, 0.16, 0.08], seed=4)),
        "A": tube([(-1.4 * math.cos(t), 0, 2.6 * math.sin(t) - 0.05) for t in [math.pi * k / 9 for k in range(10)]],
                  [0.36, 0.33, 0.31, 0.3, 0.3, 0.3, 0.3, 0.31, 0.33, 0.36], twist=0.2, jitter=0.08, seed=5),
    }


ROOT_END = {"S": Matrix.Translation((0, 2, 0)),
            "C": Matrix.Translation((0, R_CURVE, R_CURVE)) @ Matrix.Rotation(math.radians(90), 4, "X"),
            "J": Matrix.Translation((0, 1.5, 0))}


def chain(place_fn, root_me, name, start, heading, pitch, seq):
    """Place segments end-to-end. heading: deg about Z (0 = +Y); pitch: deg about X (+ = upward)."""
    T = Matrix.Translation(start) @ Matrix.Rotation(math.radians(heading), 4, "Z") @ \
        Matrix.Rotation(math.radians(pitch), 4, "X")
    objs = []
    for k, s in enumerate(seq):
        o = place_fn(f"{name}_{k:02d}", root_me[s])
        o.matrix_world = T
        objs.append(o)
        T = T @ ROOT_END[s]
    return objs


# ------------------------------------------------------------------ debris, cards, patches
def rubble(seed, n=8, w=2.3, d=2.0, h=1.8, mats=(0, 1)):
    rng = random.Random(seed)
    parts = []
    for k in range(n):
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.0)
        s = (rng.uniform(0.4, 0.75), rng.uniform(0.35, 0.7), rng.uniform(0.3, 0.55))
        R = Euler((rng.uniform(0, 3), rng.uniform(0, 3), rng.uniform(0, 3))).to_matrix()
        c = Vector((rng.uniform(-w / 2 + 0.45, w / 2 - 0.45), rng.uniform(-d / 2 + 0.4, d / 2 - 0.4),
                    s[2] * 0.6 + (rng.uniform(0.3, h - 0.9) if k >= 4 else 0)))
        vs = [R @ Vector((v.co.x * s[0] * rng.uniform(0.85, 1.15), v.co.y * s[1] * rng.uniform(0.85, 1.15),
                          v.co.z * s[2])) + c for v in bm.verts]
        parts.append(([tuple(v) for v in vs], [tuple(v.index for v in f.verts) for f in bm.faces],
                      [mats[1] if k % 4 == 3 else mats[0]] * len(bm.faces)))
        bm.free()
    return fc.mparts(*parts)


def vine_card(L, w=0.45):
    """Two-sided hanging card (top at z=0, hangs down to -L), pointed tip."""
    V = [(-w / 2, 0, -L + 0.5), (0, 0, -L), (w / 2, 0, -L + 0.5), (w / 2, 0, 0), (-w / 2, 0, 0)]
    Vb = [(x, 0.005, z) for x, _, z in V]
    F = [(0, 1, 2), (0, 2, 3, 4), (5, 7, 6), (5, 9, 8, 7)]
    return V + Vb, F, [0] * 4


def moss_patch(seed, r, n=9):
    rng = random.Random(seed)
    ring = [(r * rng.uniform(0.75, 1.1) * math.cos(2 * math.pi * k / n),
             r * rng.uniform(0.75, 1.1) * math.sin(2 * math.pi * k / n)) for k in range(n)]
    V = [(0, 0, 0.02)] + [(x, y, 0.02) for x, y in ring] + [(x, y, 0.0) for x, y in ring]
    F = [(0, 1 + k, 1 + (k + 1) % n) for k in range(n)]
    F += [(1 + n + k, 1 + n + (k + 1) % n, 1 + (k + 1) % n, 1 + k) for k in range(n)]
    return V, F, [0] * len(F)


def hull_parts(objs):
    """World-space convex hull per object (for collision proxies). Returns list of (verts, faces)."""
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


def root_ramp(x0, x1, y0, y1, z0, z1, thick=0.4, bevel=0.15, lip=0.0):
    """[bark, moss]. Root-deck ramp rising +Y from (y0,z0) to (y1,z1); flat walkable centre, mossy bevelled edges."""
    cx = (x0 + x1) / 2
    zc = lambda y: z1 if y >= y1 else z0 + (y - y0) / (y1 - y0) * (z1 - z0)
    ztop = lambda x, y: zc(y) - (0.12 if abs(x - cx) > (x1 - x0) / 2 - bevel + 1e-6 else 0.0)
    ys = [y0 + (y1 - y0) * k / 4 for k in range(5)] + ([y1 + lip] if lip else [])
    return fc.slab_grid([x0, x0 + bevel, x1 - bevel, x1], ys, lambda x, y: zc(y) - thick, ztop,
                        lambda i, j: 0 if i == 1 else 1, side_mat=0)


# ------------------------------------------------------------------ habitation (V2/V3)
def shelter_small():
    """[bark, cloth]. Lean-to: two front poles + ridge, cloth sloping to the ground at the back (+Y), sleeping mat."""
    pole = lambda x: fc.prism([(x + 0.06 * math.cos(a), -0.9 + 0.06 * math.sin(a))
                               for a in [2 * math.pi * k / 6 for k in range(6)]], 0.0, 1.85)
    return fc.mparts((*pole(-1.1)[:2], 0), (*pole(1.1)[:2], 0),
                     (*BM(-1.25, 1.25, -0.96, -0.84, 1.75, 1.87), 0),
                     (*fc.sheared_box(-1.2, 1.2, -0.95, 1.72, 1.0, 0.0, 0.04), 1),
                     (*BM(-0.9, 0.9, -0.6, 0.6, 0.0, 0.05, skip=("bottom",)), 1))


def luggage_stack():
    """[charcoal, cloth, bark, silver]. Two suitcases + a duffel, stacked."""
    duffel = fc.xform(fc.lathe([(0, 0), (0.17, 0), (0.17, 0.7), (0, 0.7)], 8), rot_y=90, offset=(-0.35, 0.0, 0.89))
    return fc.mparts((*BM(-0.3, 0.3, -0.14, 0.14, 0.0, 0.72), 0),
                     (*BM(-0.12, 0.12, -0.03, 0.03, 0.72, 0.8, skip=("bottom",)), 3),
                     (*BM(0.3, 1.0, -0.3, 0.25, 0.0, 0.26), 1),
                     (*BM(0.32, 0.98, -0.28, 0.23, 0.26, 0.45), 0),
                     (duffel[0], duffel[1], [2] * len(duffel[1])))


def lantern():
    """[charcoal, warm light]. Standing lantern 0.34 m."""
    return fc.mparts((*BM(-0.1, 0.1, -0.1, 0.1, 0.0, 0.04), 0),
                     (*BM(-0.07, 0.07, -0.07, 0.07, 0.04, 0.26), 1),
                     fc.prism([(-0.1, -0.1), (0.1, -0.1), (0.1, 0.1), (-0.1, 0.1)], 0.26, 0.3),
                     (*BM(-0.02, 0.02, -0.06, 0.06, 0.3, 0.34, skip=("bottom",)), 0))


def blanket_drape():
    """[cloth]. Blanket over a MOD_N_Bench (seat top 0.45, backrest to 0.9 at y 0.22..0.3)."""
    return fc.mparts((*BM(-0.55, 0.45, -0.27, 0.2, 0.45, 0.475), 0),
                     (*BM(-0.55, 0.45, -0.3, -0.27, 0.15, 0.475), 0),
                     (*BM(-0.55, 0.45, 0.2, 0.32, 0.9, 0.925), 0),
                     (*BM(-0.55, 0.45, 0.32, 0.35, 0.5, 0.925), 0))


def bench_damaged():
    """[silver, charcoal]. MOD_N_Bench with the right leg gone, seat + back sagging to the floor on that side."""
    seat = fc.mparts((*BM(-0.9, 0.9, -0.25, 0.22, -0.04, 0.04), 0), (*BM(-0.9, 0.9, 0.22, 0.3, -0.04, 0.45), 0))
    seat = fc.xform(seat, rot_y=14, offset=(0.0, 0.0, 0.25))
    return fc.mparts(seat, (*BM(-0.8, -0.68, -0.2, 0.25, 0.0, 0.43, skip=("top",)), 1))
