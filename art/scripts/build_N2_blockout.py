"""N2 Nova Transit Station — BLOCKOUT (Block 0 workflow step 2).
Interior: X -18..18 (along tracks), Y -10..10. Platform tops z=0, trench floor z=-1.2.
Right platform = -Y side (street entrance at its +X end); left platform = +Y side (control room on its back wall).
Run: blender -b --factory-startup -P art/scripts/build_N2_blockout.py
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

ID = "N2"
sc = fc.reset_scene()
M = fc.append_shared_materials()
SIL, GLS, CYN, CHR, AMB, CLO = (M[k] for k in ("M_NovaSilver", "M_NovaGlass", "M_CyanEmissive", "M_Charcoal",
                                              "M_AmberWarning", "M_Cloth"))
C_EXP = fc.collection(f"{ID}_Export")
C_ROOF = fc.collection(f"{ID}_Roof", C_EXP)
C_COL = fc.collection(f"{ID}_Collision")
C_FX = fc.collection(f"{ID}_FX")
C_PRES = fc.collection(f"{ID}_Presentation")
C_REF = fc.collection("_Reference")
C_LM = fc.collection(f"{ID}_Landmarks")
C_MOD = fc.collection(f"{ID}_ModuleSources")
BM = fc.box_minmax

# ------------------------------------------------------------------ dimensions
HX, HY = 18.0, 10.0
WT = 0.3
TR, TZ = 4.0, -1.2                     # trench half-width, trench floor
SPRING, APEX = 10.0, 14.0
VR = (HY ** 2 + (APEX - SPRING) ** 2) / (2 * (APEX - SPRING))      # vault radius 14.5
VZC = APEX - VR                                                    # arc centre z -0.5
VA = math.asin(HY / VR)
UP_Z = 5.0
RISERS, TREAD = 28, 0.30
RISE = UP_Z / RISERS                    # 0.1786
RUN = (RISERS - 1) * TREAD              # 8.1
CR_X0, CR_X1, CR_Y0, CR_Y1, CR_TOP = -8.0, 0.0, 5.0, 10.0, 8.5     # control room (floor z=5)
BR_X0, BR_X1, BR_Y0, BR_Y1 = -14.0, -11.0, -7.0, 5.0              # bridge deck span (3 x 4 m)
LAND_R = (-14.0, -11.0, -10.0, -7.0)                              # right upper landing
LAND_L = (-14.0, -11.0, 5.0, 8.0)                                 # left landing (on the deck)
STAIR_L_TOP_X, STAIR_R_TOP_X = CR_X1, BR_X1                        # both stairs climb toward -X
LANE = 3.0
TACT = 0.6
TRACK_Y, GAUGE = 1.6, 1.435
STREET = (-10.0, -4.0, 0.0, 5.0)       # y0, y1, z0, z1 on the +X wall
WEST_EXIT = (5.0, 9.0, 0.0, 4.0)       # on the -X wall (left platform)
PORTAL = (-TR, TR, TZ, 4.5)


def mk(name, data, mats, coll=None, loc=(0, 0, 0), rz=0.0, face_mats=None, recalc=True):
    me = fc.build_mesh(name, data, mats, face_mats=face_mats, recalc=recalc)
    return fc.obj(name, me, coll or C_EXP, loc, rz)


def mkm(name, vfm, mats, coll=None, loc=(0, 0, 0), rz=0.0, recalc=False):
    v, f, m = vfm
    return mk(name, (v, f), mats, coll, loc, rz, face_mats=m, recalc=recalc)


def col(name, data):
    o = fc.obj(f"{name}-colonly", fc.build_mesh(name, data, weld=False), C_COL)
    o.display_type = "WIRE"
    return o


def inward_box(x0, x1, y0, y1, z0, z1, open_face):
    """Corridor/tunnel stub seen from inside: faces point inward, one face left open."""
    v, f = BM(x0, x1, y0, y1, z0, z1, skip=(open_face,))
    return v, [tuple(reversed(q)) for q in f]


# ================================================================== platforms + trench
for side, y0, y1 in (("R", -HY, -TR), ("L", TR, HY)):
    mk(f"SM_N2_Platform_{side}", BM(-HX, HX, y0, y1, TZ, 0.0), [SIL])
    col(f"COL_N2_Platform_{side}", BM(-HX, HX, y0, y1, TZ - 0.2, 0.0))
    edge_y = y1 if side == "R" else y0
    s = 1 if side == "L" else -1
    ty0, ty1 = sorted((edge_y, edge_y + s * TACT))
    strip = fc.mparts((*BM(-HX, HX, ty0, ty1, 0.0, 0.01, skip=("bottom",)), 0),
                      (*BM(-HX, HX, *sorted((edge_y, edge_y - s * 0.02)), -0.16, -0.08), 1))
    mkm(f"SM_N2_PlatformEdge_{side}", strip, [AMB, CYN])
mk("SM_N2_TrenchFloor", BM(-HX, HX, -TR, TR, TZ - 0.2, TZ), [CHR])
col("COL_N2_TrenchFloor", BM(-HX, HX, -TR, TR, TZ - 0.4, TZ))
rails = [BM(-HX, HX, ty + g - 0.04, ty + g + 0.04, TZ, TZ + 0.15) for ty in (-TRACK_Y, TRACK_Y) for g in (-GAUGE / 2, GAUGE / 2)]
mk("SM_N2_Rails", fc.merge(*rails), [SIL])
# trench exit ramps (one per end, against the trench wall, rising to platform level)
ramp_local = fc.wedge_data(-0.75, 0.75, 0.0, 2.1, -TZ)
for name, rz, off in (("E", -90, (10.0, 3.25, TZ)), ("W", 90, (-10.0, -3.25, TZ))):
    d = fc.xform(ramp_local, rot_z=rz, offset=off)
    mk(f"SM_N2_TrenchRamp_{name}", d, [CHR])
    col(f"COL_N2_TrenchRamp_{name}", d)

# ================================================================== walls
for side, y0, y1 in (("S", -HY - WT, -HY), ("N", HY, HY + WT)):
    mk(f"SM_N2_Wall_{side}", BM(-HX, HX, y0, y1, 0.0, SPRING), [SIL])
    col(f"COL_N2_Wall_{side}", BM(-HX - WT, HX + WT, y0, y1, TZ, SPRING))


def end_wall(holes):
    ys = sorted({-HY, -TR, TR, HY} | {h[0] for h in holes} | {h[1] for h in holes})
    zs = sorted({TZ, 0.0, SPRING} | {h[2] for h in holes} | {h[3] for h in holes})

    def filled(i, j):
        cy, cz = (ys[i] + ys[i + 1]) / 2, (zs[j] + zs[j + 1]) / 2
        if cz < 0 and abs(cy) > TR:
            return False                                          # platform blocks fill below z=0
        return not any(h[0] < cy < h[1] and h[2] < cz < h[3] for h in holes)
    pts, faces, mats = fc.grid2d(ys, zs, filled)
    base = [k for k, p in enumerate(pts) if abs(p[1] - SPRING) < 1e-6]
    base.sort(key=lambda k: pts[k][0])
    arc = []
    for k in range(1, 16):
        a = -VA + 2 * VA * k / 16
        pts.append((VR * math.sin(a), VZC + VR * math.cos(a)))
        arc.append(len(pts) - 1)
    outline = base + arc[::-1]                                    # CCW: base left->right, arc right->left
    apex = arc[7]
    i0 = outline.index(apex)
    ring = outline[i0:] + outline[:i0]
    for a, b in zip(ring[1:-1], ring[2:]):
        faces.append((apex, a, b))
        mats.append(0)
    return fc.extrude2d(pts, faces, mats, WT)


for side, x, holes in (("E", HX + WT, [STREET, PORTAL]), ("W", -HX, [WEST_EXIT, PORTAL])):
    d = fc.xform(end_wall(holes), rot_z=90, offset=(x, 0, 0))
    mkm(f"SM_N2_Wall_{side}", d, [SIL], recalc=True)
    xs = (HX, HX + WT) if side == "E" else (-HX - WT, -HX)
    boxes = []
    ys = sorted({-HY, HY} | {h[0] for h in holes} | {h[1] for h in holes})
    for y0, y1 in zip(ys, ys[1:]):
        hs = [h for h in holes if h[0] <= y0 and h[1] >= y1]
        if hs:
            boxes.append(BM(*xs, y0, y1, hs[0][3], SPRING))
            if hs[0][2] > TZ:
                boxes.append(BM(*xs, y0, y1, TZ, hs[0][2]))
        else:
            boxes.append(BM(*xs, y0, y1, TZ, SPRING))
    col(f"COL_N2_Wall_{side}", fc.merge(*boxes))
# tunnel + corridor stubs so openings don't show the void
mk("SM_N2_TunnelStub_E", inward_box(HX + WT, HX + 4.3, -TR, TR, TZ, 4.5, "left"), [CHR], recalc=False)
mk("SM_N2_TunnelStub_W", inward_box(-HX - 4.3, -HX - WT, -TR, TR, TZ, 4.5, "right"), [CHR], recalc=False)
mk("SM_N2_StreetStub", inward_box(HX + WT, HX + 4.3, STREET[0], STREET[1], 0, STREET[3], "left"), [SIL], recalc=False)
mk("SM_N2_WestExitStub", inward_box(-HX - 4.3, -HX - WT, WEST_EXIT[0], WEST_EXIT[1], 0, WEST_EXIT[3], "right"), [SIL],
   recalc=False)
mk("SM_N2_StreetSign", BM(-0.06, 0.0, -9.0, -5.0, 5.3, 6.0), [CYN], loc=(HX, 0, 0))

# ================================================================== vault: ribs every 4 m + bays with skylight strip
def arc_band(r_in, r_out, segs=16):
    pts, faces = [], []
    for k in range(segs + 1):
        a = -VA + 2 * VA * k / segs
        pts.append((r_in * math.sin(a), VZC + r_in * math.cos(a)))
        pts.append((r_out * math.sin(a), VZC + r_out * math.cos(a)))
    for k in range(segs):
        i = 2 * k
        faces.append((i + 2, i, i + 1, i + 3))
    return pts, faces


rp, rf = arc_band(VR - 0.6, VR)
rib = fc.xform(fc.extrude2d(rp, rf, [0] * len(rf), 0.4, -0.2), rot_z=90)
me_rib = fc.build_mesh("MOD_N_RoofRib", rib[:2], [CHR], face_mats=rib[2], recalc=True)
fc.obj("MOD_N_RoofRib", me_rib, C_MOD)
bp, bf = arc_band(VR, VR + 0.1)
bay = fc.xform(fc.extrude2d(bp, bf, [1 if 5 <= k <= 10 else 0 for k in range(16)], 4.0, -2.0), rot_z=90)
me_bay = fc.build_mesh("MOD_N_RoofBay_4m", bay[:2], [SIL, GLS], face_mats=bay[2], recalc=True)
fc.obj("MOD_N_RoofBay_4m", me_bay, C_MOD)
for i, x in enumerate(range(-18, 19, 4)):
    fc.obj(f"SM_N2_RoofRib_{i:02d}", me_rib, C_ROOF, (x, 0, 0))
for i, x in enumerate(range(-16, 17, 4)):
    fc.obj(f"SM_N2_RoofBay_{i:02d}", me_bay, C_ROOF, (x, 0, 0))
for i, x in enumerate((2.0, 10.0)):
    mk(f"SM_N2_Banner_{i + 1:02d}", BM(x - 0.8, x + 0.8, -HY + 0.05, -HY + 0.1, 5.5, 9.5), [CLO])

# ================================================================== upper level: left deck + control room, right landing
mk("SM_N2_UpperDeck", fc.merge(BM(LAND_L[1], CR_X1, CR_Y0, HY, UP_Z - 0.4, UP_Z),
                               BM(BR_X0, LAND_L[1], LAND_L[3], HY, UP_Z - 0.4, UP_Z)), [SIL])
mk("MOD_N_BridgeLanding_L", BM(*LAND_L, UP_Z - 0.4, UP_Z), [SIL])
mk("MOD_N_BridgeLanding_R", BM(*LAND_R, UP_Z - 0.4, UP_Z), [SIL])
col("COL_N2_UpperDeck", fc.merge(BM(BR_X0, CR_X1, CR_Y0, HY, UP_Z - 0.4, UP_Z)))
col("COL_N2_Landing_R", BM(*LAND_R, UP_Z - 0.4, UP_Z))
cols_xy = [(-13.6, 8.6), (-8.0, 8.6), (-0.5, 8.0), (-13.6, -8.4), (-11.4, -8.4)]   # behind the 3 m lanes
me_colm = fc.build_mesh("MOD_N_Column_4.6", BM(-0.25, 0.25, -0.25, 0.25, 0, UP_Z - 0.4), [SIL])
fc.obj("MOD_N_Column_4.6", me_colm, C_MOD)
for i, (x, y) in enumerate(cols_xy):
    fc.obj(f"SM_N2_Column_{i:02d}", me_colm, C_EXP, (x, y, 0))
col("COL_N2_Columns", fc.merge(*[BM(x - 0.25, x + 0.25, y - 0.25, y + 0.25, 0, UP_Z - 0.4) for x, y in cols_xy]))

DOOR_E = (8.0, 10.0)        # east door (stair arrives), y range
DOOR_W = (5.6, 7.6)         # west door (to bridge vestibule)
cr_shell = fc.merge(BM(CR_X0, CR_X1, CR_Y0, HY, CR_TOP, CR_TOP + 0.4),
                    BM(CR_X0 - 0.15, CR_X0, CR_Y0 - 0.15, CR_Y0, UP_Z, CR_TOP),
                    BM(CR_X1, CR_X1 + 0.15, CR_Y0 - 0.15, CR_Y0, UP_Z, CR_TOP))
mk("SM_N2_ControlRoom_Shell", cr_shell, [CHR])
glass = [BM(CR_X0, CR_X1, CR_Y0 - 0.05, CR_Y0, UP_Z, CR_TOP),
         BM(CR_X0 - 0.05, CR_X0, CR_Y0, DOOR_W[0], UP_Z, CR_TOP), BM(CR_X0 - 0.05, CR_X0, DOOR_W[1], HY, UP_Z, CR_TOP),
         BM(CR_X0 - 0.05, CR_X0, DOOR_W[0], DOOR_W[1], UP_Z + 3.0, CR_TOP),
         BM(CR_X1, CR_X1 + 0.05, CR_Y0, DOOR_E[0], UP_Z, CR_TOP),
         BM(CR_X1, CR_X1 + 0.05, DOOR_E[0], DOOR_E[1], UP_Z + 3.0, CR_TOP)]
mk("SM_N2_ControlRoom_Glass", fc.merge(*glass), [GLS])
col("COL_N2_ControlRoom", fc.merge(*glass[:3], glass[4], BM(CR_X0, CR_X1, CR_Y0, HY, CR_TOP, CR_TOP + 0.4)))

# ================================================================== bridge (3 spans + 2 landings), truss sides with cyan strip
span = fc.mparts((*BM(-1.5, 1.5, -2.0, 2.0, UP_Z - 0.4, UP_Z), 0),
                 (*BM(-1.5, -1.35, -2.0, 2.0, UP_Z, UP_Z + 1.1), 0), (*BM(1.35, 1.5, -2.0, 2.0, UP_Z, UP_Z + 1.1), 0),
                 (*BM(-1.52, -1.5, -2.0, 2.0, UP_Z - 0.3, UP_Z - 0.2), 1), (*BM(1.5, 1.52, -2.0, 2.0, UP_Z - 0.3, UP_Z - 0.2), 1))
me_span = fc.build_mesh("MOD_N_Bridge_4m", span[:2], [SIL, CYN], face_mats=span[2])
fc.obj("MOD_N_Bridge_4m", me_span, C_MOD)
bx = (BR_X0 + BR_X1) / 2
for i, y in enumerate((-5.0, -1.0, 3.0)):
    fc.obj(f"SM_N2_Bridge_{i + 1:02d}", me_span, C_EXP, (bx, y, 0))
col("COL_N2_Bridge", fc.merge(BM(BR_X0, BR_X1, BR_Y0, BR_Y1, UP_Z - 0.4, UP_Z),
                              BM(BR_X0, BR_X0 + 0.15, BR_Y0, BR_Y1, UP_Z, UP_Z + 1.1),
                              BM(BR_X1 - 0.15, BR_X1, BR_Y0, BR_Y1, UP_Z, UP_Z + 1.1)))

# railings on open upper edges (blockout boxes)
rails_up = [BM(LAND_L[1], CR_X0, CR_Y0, CR_Y0 + 0.1, UP_Z, UP_Z + 1.1),          # vestibule front edge
            BM(BR_X0, BR_X0 + 0.1, LAND_L[2], HY, UP_Z, UP_Z + 1.1),             # deck west edge
            BM(BR_X0, BR_X0 + 0.1, LAND_R[2], LAND_R[3], UP_Z, UP_Z + 1.1),      # right landing west edge
            BM(LAND_R[1] - 0.1, LAND_R[1], -8.0, LAND_R[3], UP_Z, UP_Z + 1.1)]   # right landing east edge (beside stair)
mk("SM_N2_UpperRails", fc.merge(*rails_up), [GLS])
col("COL_N2_UpperRails", fc.merge(*rails_up))

# ================================================================== stairs (2 m, 28 x 0.1786 rise, climb toward -X; origin at top edge)
sv, sf = fc.stair_data(2.0, RISERS - 1, TREAD, RISE)
sv = [(x, y - RUN, z) for x, y, z in sv]
me_stair = fc.build_mesh("MOD_N_Stair_2m_5rise", (sv, sf), [SIL, CHR], face_mats=fc.stair_mats(RISERS - 1, len(sf)))
fc.obj("MOD_N_Stair_2m_5rise", me_stair, C_MOD)
stair_ramp = fc.wedge_data(-1.0, 1.0, -RUN - TREAD, 0.0, UP_Z)
for side, top_x, y in (("L", STAIR_L_TOP_X, 9.0), ("R", STAIR_R_TOP_X, -9.0)):
    fc.obj(f"SM_N2_Stair_{side}", me_stair, C_EXP, (top_x, y, 0), 90)
    col(f"COL_N2_Stair_{side}", fc.xform(stair_ramp, rot_z=90, offset=(top_x, y, 0)))
    ey = 8.0 if side == "L" else -8.0                                        # open (lane) side rail
    r = fc.xform(fc.sheared_box(-0.05, 0.05, -RUN - TREAD, 0.0, 0.0, UP_Z, 1.1), rot_z=90, offset=(top_x, ey, 0))
    mk(f"SM_N2_StairRail_{side}", r, [GLS])
    col(f"COL_N2_StairRail_{side}", r)

# ================================================================== power nodes, generator + sockets
def ngon(n, r, rot=0.0):
    return [(r * math.cos(rot + 2 * math.pi * k / n), r * math.sin(rot + 2 * math.pi * k / n)) for k in range(n)]


NODES = {"01": ((6.0, -8.9, 0.0), 3), "02": ((-12.5, 9.0, UP_Z), 4), "03": ((16.0, 8.6, 0.0), 6)}
crystal = fc.lathe([(0, -0.8), (0.32, -0.2), (0.34, 0.3), (0, 0.8)], 6)
landmarks = {}
for n, (loc, sides) in NODES.items():
    ped = fc.prism(ngon(sides, 0.6, math.pi / 2 if sides == 3 else math.pi / sides), 0.0, 0.7)
    node = fc.mparts(ped, (*fc.xform(crystal, offset=(0, 0, 0.85 + 0.8)), [1] * len(crystal[1])))
    mkm(f"SM_PowerNode_{n}", node, [SIL, CYN], loc=loc, recalc=True)
    col(f"COL_PowerNode_{n}", fc.xform(BM(-0.6, 0.6, -0.6, 0.6, 0, 1.2), offset=loc))
    landmarks[f"LM_PowerNode_{n}"] = loc
GEN = (12.0, 9.2, 0.0)
mk("SM_Generator", BM(-1.2, 1.2, -0.7, 0.7, 0, 1.6), [CHR], loc=GEN)
col("COL_Generator", fc.xform(BM(-1.2, 1.2, -0.7, 0.7, 0, 1.6), offset=GEN))
for s, dx in zip("ABC", (-0.7, 0.0, 0.7)):
    ring = fc.xform(fc.lathe([(0.16, 0), (0.16, 0.08), (0.1, 0.08), (0.1, 0)], 8, closed=True), rot_x=90)
    mk(f"SM_Socket_{s}", ring, [SIL], loc=(GEN[0] + dx, GEN[1] - 0.7, 0.95))
landmarks["LM_Generator"] = GEN

# ================================================================== platform props: 3 cover crates + 2 benches per platform
crate = fc.build_mesh("MOD_N_CoverCrate", BM(-0.6, 0.6, -0.6, 0.6, 0, 1.1), [SIL])
bench = fc.build_mesh("MOD_N_Bench", BM(-0.9, 0.9, -0.25, 0.25, 0, 0.45), [SIL])
fc.obj("MOD_N_CoverCrate", crate, C_MOD)
fc.obj("MOD_N_Bench", bench, C_MOD)
COVERS = [(-16.0, -9.2), (1.0, -9.2), (13.0, -9.2), (-12.0, 9.2), (-6.0, 9.2), (-2.5, 9.2)]
BENCHES = [(9.0, -9.5), (4.0, -9.5), (-9.5, 9.6), (-16.0, 9.6)]
for i, (x, y) in enumerate(COVERS):
    fc.obj(f"SM_N2_Cover_{i:02d}", crate, C_EXP, (x, y, 0))
for i, (x, y) in enumerate(BENCHES):
    fc.obj(f"SM_N2_Bench_{i:02d}", bench, C_EXP, (x, y, 0))
col("COL_N2_Props", fc.merge(*[BM(x - 0.6, x + 0.6, y - 0.6, y + 0.6, 0, 1.1) for x, y in COVERS],
                             *[BM(x - 0.9, x + 0.9, y - 0.25, y + 0.25, 0, 0.45) for x, y in BENCHES]))

# ================================================================== landmarks
landmarks.update({
    "LM_Entrance": (HX, (STREET[0] + STREET[1]) / 2, 0.0),
    "LM_Exit_West": (-HX, (WEST_EXIT[0] + WEST_EXIT[1]) / 2, 0.0),
    "LM_Platform_R": (0.0, -7.0, 0.0), "LM_Platform_L": (0.0, 7.0, 0.0),
    "LM_ControlRoom": ((CR_X0 + CR_X1) / 2, (CR_Y0 + HY) / 2, UP_Z),
    "LM_Bridge_R": (bx, BR_Y0, UP_Z), "LM_Bridge_L": (bx, BR_Y1, UP_Z),
    "LM_Stair_L": (STAIR_L_TOP_X + RUN, 9.0, 0.0), "LM_Stair_L_Top": (STAIR_L_TOP_X, 9.0, UP_Z),
    "LM_Stair_R": (STAIR_R_TOP_X + RUN, -9.0, 0.0), "LM_Stair_R_Top": (STAIR_R_TOP_X, -9.0, UP_Z),
    "LM_TrenchRamp_E": (12.1, 3.25, 0.0), "LM_TrenchRamp_W": (-12.1, -3.25, 0.0),
})
for n, p in landmarks.items():
    fc.empty(n, p, C_LM, 0.8, "ARROWS").hide_render = True

# ================================================================== checks: sightline + 3 m lanes
bpy.context.view_layer.update()
blockers = [o for o in C_EXP.all_objects if o.type == "MESH" and not any(
    m and m.name == "M_NovaGlass" and all(s.material == m for s in o.material_slots) for m in [GLS])]
verts, polys = [], []
for o in blockers:
    mw = o.matrix_world
    off = len(verts)
    verts += [mw @ v.co for v in o.data.vertices]
    polys += [[off + i for i in p.vertices] for p in o.data.polygons if o.material_slots[p.material_index].material != GLS]
bvh = BVHTree.FromPolygons(verts, polys)
eye = Vector((HX - 0.5, -7.0, 1.7))
targets = [Vector((x, CR_Y0 - 0.06, z)) for x in [CR_X0 + 0.5 + k for k in range(8)] for z in (5.4, 6.2, 7.0, 7.8, 8.3)]
targets += [Vector((CR_X1 + 0.06, y, z)) for y in (5.5, 6.5, 7.5) for z in (5.4, 6.5, 7.6)]
seen, blocked_by = 0, {}
for t in targets:
    d = t - eye
    hit, _, idx, dist = bvh.ray_cast(eye, d.normalized(), d.length - 0.05)
    if hit is None:
        seen += 1
lanes = {"R": (-HY + 0.0, -TR - TACT), "L": (TR + TACT, HY)}
lane_hits = {}
for side, (ya, yb) in lanes.items():
    lane = (yb - LANE, yb) if side == "R" else (ya, ya + LANE)
    hits = []
    for o in C_EXP.all_objects:
        if o.type != "MESH" or o.name.startswith(("SM_N2_Platform", "SM_N2_Wall", "SM_N2_Roof", "SM_N2_TrenchFloor",
                                                   "SM_N2_StreetStub", "SM_N2_WestExitStub", "SM_N2_TunnelStub")):
            continue
        bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
        if min(p.z for p in bb) > 2.5 or max(p.z for p in bb) < 0.02:
            continue
        if max(p.y for p in bb) > lane[0] + 1e-4 and min(p.y for p in bb) < lane[1] - 1e-4:
            hits.append(o.name)
    lane_hits[side] = dict(lane_y=[round(lane[0], 2), round(lane[1], 2)], obstacles=hits)

# ================================================================== presentation + renders
fc.ref_player(C_REF, (11.0, -5.4, 0))
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


cam_top = cam("CAM_TopDown", (0, 0, 60), ortho=40)
cam_eye = cam("CAM_EyeHeight", tuple(eye), target=(-4.0, 7.5, 5.6))
sun_d = bpy.data.lights.new("LGT_Key_6500K", "SUN")
sun_d.energy = 3.0
sun = bpy.data.objects.new("LGT_Key_6500K", sun_d)
sun.rotation_euler = (math.radians(30), 0, math.radians(20))
C_PRES.objects.link(sun)
sc.world.use_nodes = True
bg = sc.world.node_tree.nodes.get("Background")
bg.inputs[0].default_value = fc.hex_lin("#C9D6E3")
bg.inputs[1].default_value = 0.6
ref = bpy.data.objects["REF_Player"]
ref.hide_render = False
renders = {}
C_ROOF.hide_render = True
sc.camera = cam_top
renders["topdown"] = fc.render(os.path.join(fc.RENDER_DIR, "N2_blockout_topdown.png"), engine="BLENDER_EEVEE")
C_ROOF.hide_render = False
sc.camera = cam_eye
renders["eye"] = fc.render(os.path.join(fc.RENDER_DIR, "N2_blockout_eyeheight.png"), engine="BLENDER_EEVEE")
ref.hide_render = True

rows, uniq, inst = fc.tri_report([C_EXP])
report = {
    "footprint_interior_m": [2 * HX, 2 * HY], "vault": dict(spring_z=SPRING, apex_z=APEX, radius=round(VR, 3)),
    "platforms": dict(width=HY - TR, top_z=0.0, right_y=[-HY, -TR], left_y=[TR, HY], tactile_strip=TACT),
    "trench": dict(width=2 * TR, floor_z=TZ, tracks_y=[-TRACK_Y, TRACK_Y], ramps="1.5 m wide, 2.1 m run, 29.7 deg"),
    "control_room": dict(x=[CR_X0, CR_X1], y=[CR_Y0, HY], floor_z=UP_Z, ceiling_z=CR_TOP),
    "bridge": dict(x=[BR_X0, BR_X1], y=[BR_Y0, BR_Y1], deck_z=UP_Z, spans=3, landing_R=LAND_R, landing_L=LAND_L),
    "stairs": dict(width=2.0, risers=RISERS, rise=round(RISE, 4), tread=TREAD, run=RUN,
                   slope_deg=round(math.degrees(math.atan2(RISE, TREAD)), 1)),
    "street_door": dict(w=STREET[1] - STREET[0], h=STREET[3]), "west_exit": dict(w=WEST_EXIT[1] - WEST_EXIT[0], h=WEST_EXIT[3]),
    "sightline_entrance_to_control_room": f"{seen}/{len(targets)} glazing points visible",
    "lanes_3m": lane_hits,
    "landmarks": {k: [round(c, 3) for c in v] for k, v in landmarks.items()},
    "tris_export_unique": uniq, "tris_export_instanced": inst, "budget": 150000,
    "renders": renders,
}
blend = os.path.join(fc.SOURCE_DIR, "Fractured_N2_TransitStation.blend")
fc.save(blend)
report["blend"] = blend
with open(os.path.join(fc.RENDER_DIR, "N2_blockout_report.json"), "w") as fh:
    json.dump(report, fh, indent=2)
print("N2 BLOCKOUT DONE", report["sightline_entrance_to_control_room"], json.dumps(lane_hits))
