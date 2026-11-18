"""Nova kit piece generators shared by N2+ rooms (and the A7 kit). Each returns raw (verts, faces, mats).
Material slot conventions are documented per function; callers pass the matching material list.
All pieces: metric, origin bottom-centre (unless noted), front faces -Y, faces wound outward.
"""
import math
import random
import bmesh
from mathutils import Matrix, Vector, Euler

import fractured_common as fc

BM = fc.box_minmax


def floor_tile(sx, sy, b=0.05, t=0.2):
    """[field, border+sides]. Origin bottom-centre, top at z=t."""
    x0, x1, y0, y1 = -sx / 2, sx / 2, -sy / 2, sy / 2
    V = [(x0, y0, t), (x1, y0, t), (x1, y1, t), (x0, y1, t),
         (x0 + b, y0 + b, t), (x1 - b, y0 + b, t), (x1 - b, y1 - b, t), (x0 + b, y1 - b, t),
         (x0, y0, 0), (x1, y0, 0), (x1, y1, 0), (x0, y1, 0)]
    F = [(4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7),
         (8, 11, 10, 9), (0, 8, 9, 1), (1, 9, 10, 2), (2, 10, 11, 3), (3, 11, 8, 0)]
    return V, F, [0] + [1] * 9


def wall_panel(width, height=4.0, seam=False, hole=None, band=True, top_strip=False, t=0.3, hole_mat=1):
    """[surface, charcoal band/reveal, cyan]. Front face at y=0 (faces -Y), thickness toward +Y."""
    w = width / 2
    xs, zs = {-w, w}, {0.0, height}
    mid = height / 2
    if band and height >= 4:
        zs |= {mid - 0.03, mid + 0.03}
    if top_strip:
        zs |= {height - 0.14, height - 0.06}
    if seam:
        xs |= {-0.06, 0.06}
    if hole:
        xs |= {hole[0], hole[1]}
        zs |= {hole[2], hole[3]}
    xs, zs = sorted(xs), sorted(zs)

    def c(i, j):
        return (xs[i] + xs[i + 1]) / 2, (zs[j] + zs[j + 1]) / 2

    def in_hole(i, j):
        cx, cz = c(i, j)
        return bool(hole) and hole[0] < cx < hole[1] and hole[2] < cz < hole[3]

    def mat(i, j):
        cx, cz = c(i, j)
        if top_strip and height - 0.14 < cz < height - 0.06:
            return 2
        if seam and abs(cx) < 0.06:
            return 2
        if band and height >= 4 and mid - 0.03 < cz < mid + 0.03:
            return 1
        return 0

    pts, faces, mats = fc.grid2d(xs, zs, lambda i, j: not in_hole(i, j), mat)

    def side(a, b, m):
        if hole and all(hole[0] - 1e-4 <= p[0] <= hole[1] + 1e-4 and hole[2] - 1e-4 <= p[1] <= hole[3] + 1e-4
                        for p in (a, b)):
            return hole_mat
        return m
    return fc.extrude2d(pts, faces, mats, t, 0.0, side_mat=side)


def door_frame(ow, oh, jamb, head, depth, jambs=(True, True), z0=0.0):
    """[frame, reveal]. Portal frame protruding `depth` toward -Y from the wall face (y=0). Opening ow x oh."""
    w = ow / 2
    jl, jr = (jamb if jambs[0] else 0.0), (jamb if jambs[1] else 0.0)
    xs = [x for x in (-w - jl, -w, w, w + jr)]
    xs = sorted(set(xs))
    zs = [z0, z0 + oh, z0 + oh + head]

    def filled(i, j):
        cx = (xs[i] + xs[i + 1]) / 2
        return not (abs(cx) < w and j == 0)
    pts, faces, mats = fc.grid2d(xs, zs, filled)

    def side(a, b, m):
        return 1 if all(abs(p[0]) <= w + 1e-4 and p[1] <= z0 + oh + 1e-4 for p in (a, b)) else 0
    return fc.extrude2d(pts, faces, mats, depth, -depth, back=False, side_mat=side)


def railing(L, h=1.1):
    """[glass, silver]. Along X centred, post at -X end, origin bottom-centre."""
    return fc.mparts(
        (*BM(-L / 2, -L / 2 + 0.08, -0.05, 0.05, 0, h), 1),
        (*BM(-L / 2 + 0.09, L / 2 - 0.01, -0.02, 0.02, 0.1, h - 0.15), 0),
        (*BM(-L / 2 + 0.08, L / 2, -0.04, 0.04, h - 0.12, h, skip=("left",)), 1),
    )


def sloped_rail(x, y0, z0, y1, z1, h=1.1):
    """[glass, silver]. Glass rail following a stair line from (y0,z0) to (y1,z1) at constant x."""
    return fc.mparts(
        (*BM(x - 0.04, x + 0.04, y0, y0 + 0.1, z0, z0 + h), 1),
        (*fc.sheared_box(x - 0.02, x + 0.02, y0 + 0.11, z0 + 0.12, y1 - 0.02, z1 + 0.12, h - 0.3), 0),
        (*fc.sheared_box(x - 0.04, x + 0.04, y0 + 0.1, z0 + h - 0.12, y1, z1 + h - 0.12, 0.12), 1),
    )


def banner(height=5.0):
    """[cloth, silver]. Navy cloth with V-cut tail, silver double chevron, hanging rod. Faces -Y; hangs from z=height."""
    pts = [(-0.8, 0), (0, 0.5), (0.8, 0), (0.8, height), (0, height), (-0.8, height)]
    cloth = fc.extrude2d(pts, [(0, 1, 4, 5), (1, 2, 3, 4)], [0, 0], 0.03, -0.08)
    emb = []
    for dz in (height * 0.75, height * 0.66):
        left = [(-0.5, 0.4), (0, -0.25), (0, 0.05), (-0.3, 0.4)]
        right = [(0.3, 0.4), (0, 0.05), (0, -0.25), (0.5, 0.4)]
        p = [(x, z + dz) for x, z in left + right]
        emb.append(fc.extrude2d(p, [(0, 1, 2, 3), (4, 5, 6, 7)], [1, 1], 0.015, -0.095, back=False))
    rod = (*BM(-0.95, 0.95, -0.1, -0.04, height, height + 0.08), 1)
    return fc.mparts(cloth, *emb, rod)


def bench(length=1.8):
    """[silver, charcoal]. Seat + backrest at +Y, faces -Y. Seat top 0.45 m."""
    L = length / 2
    return fc.mparts(
        (*BM(-L, L, -0.25, 0.22, 0.37, 0.45), 0),
        (*BM(-L, L, 0.22, 0.3, 0.37, 0.9), 0),
        (*BM(-L + 0.1, -L + 0.22, -0.2, 0.25, 0.0, 0.37, skip=("top",)), 1),
        (*BM(L - 0.22, L - 0.1, -0.2, 0.25, 0.0, 0.37, skip=("top",)), 1),
    )


def sign(text, cell, pad=0.15):
    """[plate, glyph]. Charcoal plate (back at y=0, faces -Y) with raised block glyphs. Origin bottom-centre."""
    gp, gf, _ = fc.glyphs(text, cell, 0.0, pad)
    w = max(p[0] for p in gp) + pad
    h = 5 * cell + 2 * pad
    return fc.mparts((*BM(-w, w, -0.1, 0.0, 0.0, h, skip=("back",)), 0),
                     fc.extrude2d(gp, gf, [1] * len(gf), 0.03, -0.13, back=False))


def stair(width, risers, rise, tread):
    """[tread, riser/sides]. Climbs toward +Y; origin at TOP edge centre (grid-snapped landing edge)."""
    n = risers - 1
    v, f = fc.stair_data(width, n, tread, rise)
    run = n * tread
    return [(x, y - run, z) for x, y, z in v], f, fc.stair_mats(n, len(f))


def stair_ramp(width, risers, rise, tread):
    """Collision ramp riding on the nosings (toe one tread out), origin at top edge like stair()."""
    run = (risers - 1) * tread
    return fc.wedge_data(-width / 2, width / 2, -run - tread, 0.0, risers * rise)


def crate():
    """[silver, charcoal]. 1.2 x 1.2 x 1.1 cover crate with charcoal mid band."""
    return fc.mparts((*BM(-0.6, 0.6, -0.6, 0.6, 0, 0.5, skip=("top",)), 0),
                     (*BM(-0.62, 0.62, -0.62, 0.62, 0.5, 0.6), 1),
                     (*BM(-0.6, 0.6, -0.6, 0.6, 0.6, 1.1, skip=("bottom",)), 0))


def planter(seed=1):
    """[charcoal, moss]. 1.2 x 1.2 x 1.1 cover planter + 3 faceted shrub blobs on top."""
    rng = random.Random(seed)
    parts = [(*BM(-0.6, 0.6, -0.6, 0.6, 0, 1.0, skip=("top",)), 0),
             (*BM(-0.6, 0.6, -0.6, -0.5, 1.0, 1.1, skip=("bottom",)), 0),
             (*BM(-0.6, 0.6, 0.5, 0.6, 1.0, 1.1, skip=("bottom",)), 0),
             (*BM(-0.6, -0.5, -0.5, 0.5, 1.0, 1.1, skip=("bottom",)), 0),
             (*BM(0.5, 0.6, -0.5, 0.5, 1.0, 1.1, skip=("bottom",)), 0),
             (*BM(-0.5, 0.5, -0.5, 0.5, 0.98, 1.0, skip=("bottom", "left", "right", "front", "back")), 1)]
    for k in range(3):
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.0)
        s = rng.uniform(0.22, 0.32)
        c = Vector((rng.uniform(-0.25, 0.25), rng.uniform(-0.25, 0.25), 1.0 + s * 0.6))
        vs = [tuple(Vector((v.co.x * s, v.co.y * s, v.co.z * s * 1.1)) + c) for v in bm.verts]
        parts.append((vs, [tuple(v.index for v in f.verts) for f in bm.faces], [1] * len(bm.faces)))
        bm.free()
    return fc.mparts(*parts)


def ngon(n, r, rot=None):
    rot = (math.pi / 2 if n == 3 else math.pi / n) if rot is None else rot
    return [(r * math.cos(rot + 2 * math.pi * k / n), r * math.sin(rot + 2 * math.pi * k / n)) for k in range(n)]


def power_node(sides, seed=0, crystal_h=1.6):
    """[silver, charcoal, cyan]. Faceted n-gon pedestal (cyan band) + floating faceted crystal."""
    rng = random.Random(seed)
    lower = fc.prism(ngon(sides, 0.6), 0.0, 0.45, side_mats=[0 if k % 2 else 1 for k in range(sides)])
    band = fc.prism(ngon(sides, 0.52), 0.45, 0.55, cap_mat=2)
    top = fc.prism(ngon(sides, 0.44), 0.55, 0.7, cap_mat=1)
    h = crystal_h / 2
    cv, cf = fc.lathe([(0, -h), (0.26, -h * 0.45), (0.34, 0.05), (0.27, h * 0.5), (0, h)], 8)
    cv = [(x * rng.uniform(0.88, 1.12), y * rng.uniform(0.88, 1.12), z + 0.85 + h) for x, y, z in cv]
    return fc.mparts(lower, band, top, (cv, cf, [2] * len(cf)))


def ring_port(r_out=0.16, r_in=0.1, depth=0.08, plate=0.2):
    """[silver, charcoal]. A2 ring connector: 8-sided ring + square backing plate. Axis = -Y (faces -Y), origin at centre."""
    ring = fc.xform(fc.lathe([(r_out, 0), (r_out, depth), (r_in, depth), (r_in, 0)], 8, closed=True,
                             angle_offset=math.pi / 8), rot_x=90)
    ring = (ring[0], ring[1], [0] * len(ring[1]))
    back = (*BM(-plate, plate, 0.0, 0.03, -plate, plate), 1)
    return fc.mparts(ring, back)
