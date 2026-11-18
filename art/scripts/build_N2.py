"""N2 Nova Transit Station — DETAIL stage + Block Z QA + export.
Layout/dimensions approved at blockout (build_N2_blockout.py / art/renders/N2_blockout_report.json).
Interior X -18..18 (along tracks), Y -10..10. Platform tops z=0, trench floor z=-1.2.
Right platform = -Y side (street entrance at its +X end); left platform = +Y (control room on its back wall).
Run: blender -b --factory-startup -P art/scripts/build_N2.py
"""
import os
import sys
import math
import json
import bpy

sys.path.insert(0, os.path.dirname(__file__))
import fractured_common as fc
import fractured_qa as qa
import nova_kit as nk

ID, NAME = "N2", "TransitStation"
sc = fc.reset_scene()
M = fc.append_shared_materials()
SIL, GLS, CYN, CHR, AMB, CLO, MOSS = (M[k] for k in ("M_NovaSilver", "M_NovaGlass", "M_CyanEmissive", "M_Charcoal",
                                                    "M_AmberWarning", "M_Cloth", "M_Moss"))
C_EXP = fc.collection(f"{ID}_Export")
C_ROOF = fc.collection(f"{ID}_Roof", C_EXP)
C_COL = fc.collection(f"{ID}_Collision")
C_FX = fc.collection(f"{ID}_FX")
C_PRES = fc.collection(f"{ID}_Presentation")
C_REF = fc.collection("_Reference")
C_LM = fc.collection(f"{ID}_Landmarks")
C_MOD = fc.collection(f"{ID}_ModuleSources")
BM = fc.box_minmax

# ------------------------------------------------------------------ approved dimensions (unchanged from blockout)
HX, HY, WT = 18.0, 10.0, 0.3
TR, TZ = 4.0, -1.2
SPRING, APEX = 10.0, 14.0
VR = (HY ** 2 + (APEX - SPRING) ** 2) / (2 * (APEX - SPRING))
VZC = APEX - VR
VA = math.asin(HY / VR)
UP_Z = 5.0
RISERS, TREAD = 28, 0.30
RISE = UP_Z / RISERS
RUN = (RISERS - 1) * TREAD
CR_X0, CR_X1, CR_Y0, CR_TOP = -8.0, 0.0, 5.0, 8.5
BR_X0, BR_X1, BR_Y0, BR_Y1 = -14.0, -11.0, -7.0, 5.0
LAND_R = (-14.0, -11.0, -10.0, -7.0)
LAND_L = (-14.0, -11.0, 5.0, 8.0)
TACT = 0.6
TRACK_Y, GAUGE = 1.6, 1.435
STREET = (-10.0, -4.0, 0.0, 5.0)
WEST_EXIT = (5.0, 9.0, 0.0, 4.0)
PORTAL = (-3.5, 3.5, TZ, 4.5)          # narrowed 0.5 m/side vs blockout so a pier separates it from the street door
DOOR_E, DOOR_W = (8.0, 10.0), (5.6, 7.6)
X_PANELS = [-16.0 + 4 * i for i in range(9)]


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


def inward_box(x0, x1, y0, y1, z0, z1, open_face, mat=0):
    v, f = BM(x0, x1, y0, y1, z0, z1, skip=(open_face,))
    return v, [tuple(reversed(q)) for q in f], [mat] * (len(f))


# ================================================================== platforms, edges, trench, rails
me_ptile = module("MOD_N_Floor_Platform_4x6", nk.floor_tile(4, 6, t=-TZ), [SIL, CHR])
me_ttile = module("MOD_N_Floor_Trench_4x8", nk.floor_tile(4, 8, b=0.08, t=0.2), [CHR, SIL])
edge = fc.mparts((*BM(-2, 2, -TACT, 0.0, 0.0, 0.012, skip=("bottom", "back")), 0),
                 (*BM(-2, 2, 0.0, 0.02, -0.17, -0.08), 1))
me_edge = module("MOD_N_PlatformEdge_4m", edge, [AMB, CYN])
rail_parts = []
for g in (-GAUGE / 2, GAUGE / 2):
    rail_parts.append((*BM(-2, 2, g - 0.04, g + 0.04, 0.12, 0.24), 0))
for k in range(4):
    x = -1.5 + k
    rail_parts.append((*BM(x - 0.14, x + 0.14, -1.25, 1.25, 0.0, 0.12, skip=("bottom",)), 1))
me_track = module("MOD_N_Track_4m", fc.mparts(*rail_parts), [SIL, CHR])
for x in X_PANELS:
    k = int(x + 16) // 4
    place(f"SM_N2_Platform_R_{k:02d}", me_ptile, (x, -7.0, TZ))
    place(f"SM_N2_Platform_L_{k:02d}", me_ptile, (x, 7.0, TZ))
    place(f"SM_N2_PlatformEdge_R_{k:02d}", me_edge, (x, -TR, 0), 0)
    place(f"SM_N2_PlatformEdge_L_{k:02d}", me_edge, (x, TR, 0), 180)
    place(f"SM_N2_Trench_{k:02d}", me_ttile, (x, 0.0, TZ - 0.2))
    place(f"SM_N2_Track_A_{k:02d}", me_track, (x, -TRACK_Y, TZ))
    place(f"SM_N2_Track_B_{k:02d}", me_track, (x, TRACK_Y, TZ))
col("COL_N2_Platform_R", BM(-HX, HX, -HY, -TR, TZ - 0.2, 0.0))
col("COL_N2_Platform_L", BM(-HX, HX, TR, HY, TZ - 0.2, 0.0))
col("COL_N2_TrenchFloor", BM(-HX, HX, -TR, TR, TZ - 0.4, TZ))
ramp_local = fc.wedge_data(-0.75, 0.75, 0.0, 2.1, -TZ)
me_ramp = module("MOD_N_TrenchRamp", (*ramp_local, [0, 1, 0, 0, 0]), [CHR, AMB])     # amber nose on the slope
for name, rz, off in (("E", -90, (10.0, 3.25, TZ)), ("W", 90, (-10.0, -3.25, TZ))):
    place(f"SM_N2_TrenchRamp_{name}", me_ramp, off, rz)
    col(f"COL_N2_TrenchRamp_{name}", fc.xform(ramp_local, rot_z=rz, offset=off))

# ================================================================== side walls (modular), end walls, doors, signs
me_w4 = module("MOD_N_Wall_4x4", nk.wall_panel(4), [SIL, CHR, CYN])
me_w4s = module("MOD_N_Wall_4x4_Seam", nk.wall_panel(4, seam=True), [SIL, CHR, CYN])
me_w2 = module("MOD_N_Wall_4x2_Top", nk.wall_panel(4, height=2.0, band=False, top_strip=True), [SIL, CHR, CYN])
for side, y, rz in (("S", -HY, 180), ("N", HY, 0)):
    for i, x in enumerate(X_PANELS):
        for r, z in enumerate((0.0, 4.0, 8.0)):
            me = me_w2 if r == 2 else (me_w4s if i % 2 else me_w4)
            place(f"SM_N2_Wall_{side}_{i}{r}", me, (x, y, z), rz)
    y0, y1 = (y - WT, y) if side == "S" else (y, y + WT)
    col(f"COL_N2_Wall_{side}", BM(-HX - WT, HX + WT, y0, y1, TZ, SPRING))
me_spr = module("MOD_N_RibSpringer", fc.prism([(-0.3, 0.0), (-0.3, -0.35), (-0.15, -0.5), (0.15, -0.5),
                                               (0.3, -0.35), (0.3, 0.0)], 0.0, 1.0, cap_mat=0), [CHR])
k = 0
for x in range(-18, 19, 4):
    for y, rz in ((-HY, 180), (HY, 0)):
        if abs(x) < HX:
            place(f"SM_N2_RibSpringer_{k:02d}", me_spr, (x, y, SPRING - 1.0), rz)
            k += 1


def end_wall(holes):
    ys = sorted({-HY, -TR, TR, HY} | {h[0] for h in holes} | {h[1] for h in holes})
    zs = sorted({TZ, 0.0, SPRING} | {h[2] for h in holes} | {h[3] for h in holes})

    def filled(i, j):
        cy, cz = (ys[i] + ys[i + 1]) / 2, (zs[j] + zs[j + 1]) / 2
        if cz < 0 and abs(cy) > TR:
            return False
        return not any(h[0] < cy < h[1] and h[2] < cz < h[3] for h in holes)
    pts, faces, mats = fc.grid2d(ys, zs, filled)
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


for side, x, holes in (("E", HX + WT, [STREET, PORTAL]), ("W", -HX, [WEST_EXIT, PORTAL])):
    unique(f"SM_N2_Wall_{side}", fc.xform(end_wall(holes), rot_z=90, offset=(x, 0, 0)), [SIL], recalc=True)
    xs = (HX, HX + WT) if side == "E" else (-HX - WT, -HX)
    ys = sorted({-HY, HY} | {h[0] for h in holes} | {h[1] for h in holes})
    boxes = []
    for y0, y1 in zip(ys, ys[1:]):
        hs = [h for h in holes if h[0] <= y0 and h[1] >= y1]
        if hs:
            boxes.append(BM(*xs, y0, y1, hs[0][3], SPRING))
            if hs[0][2] > TZ:
                boxes.append(BM(*xs, y0, y1, TZ, hs[0][2]))
        else:
            boxes.append(BM(*xs, y0, y1, TZ, SPRING))
    col(f"COL_N2_Wall_{side}", fc.merge(*boxes))

# door frames (frame bottom-centre on the wall face), tunnel portal frames with amber hazard reveal
me_df65 = module("MOD_N_DoorFrame_6x5", nk.door_frame(6.0, 5.0, 0.4, 0.6, 0.35, jambs=(False, True)), [CHR, CYN])
me_df44 = module("MOD_N_DoorFrame_4x4", nk.door_frame(4.0, 4.0, 0.5, 0.6, 0.35), [CHR, CYN])
me_pf = module("MOD_N_PortalFrame_7x5.7", nk.door_frame(7.0, PORTAL[3] - TZ, 0.4, 0.5, 0.3, z0=0.0), [CHR, AMB])
place("SM_N2_DoorFrame_Street", me_df65, (HX, (STREET[0] + STREET[1]) / 2, 0), -90)
place("SM_N2_DoorFrame_West", me_df44, (-HX, (WEST_EXIT[0] + WEST_EXIT[1]) / 2, 0), 90)
place("SM_N2_PortalFrame_E", me_pf, (HX, 0, TZ), -90)
place("SM_N2_PortalFrame_W", me_pf, (-HX, 0, TZ), 90)
col("COL_N2_DoorFrames", fc.merge(BM(HX - 0.35, HX, STREET[0], STREET[0] + 0.4, 0, 5.6),
                                  BM(HX - 0.35, HX, STREET[0], STREET[1], 5.0, 5.6),
                                  BM(-HX, -HX + 0.35, WEST_EXIT[0] - 0.5, WEST_EXIT[0], 0, 4.6),
                                  BM(-HX, -HX + 0.35, WEST_EXIT[1], WEST_EXIT[1] + 0.5, 0, 4.6)))
unique("SM_N2_TunnelStub_E", inward_box(HX + WT, HX + 4.3, PORTAL[0], PORTAL[1], TZ, PORTAL[3], "left"), [CHR])
unique("SM_N2_TunnelStub_W", inward_box(-HX - 4.3, -HX - WT, PORTAL[0], PORTAL[1], TZ, PORTAL[3], "right"), [CHR])
unique("SM_N2_StreetStub", inward_box(HX + WT, HX + 4.3, STREET[0], STREET[1], 0, STREET[3], "left"), [SIL])
unique("SM_N2_WestExitStub", inward_box(-HX - 4.3, -HX - WT, WEST_EXIT[0], WEST_EXIT[1], 0, WEST_EXIT[3], "right"), [SIL])
unique("SM_N2_Sign_Street", nk.sign("STREET >", 0.1), [CHR, CYN], loc=(HX - 0.02, (STREET[0] + STREET[1]) / 2, 5.75), rz=-90)
unique("SM_N2_Sign_West", nk.sign("< EXIT", 0.08), [CHR, CYN], loc=(-HX + 0.02, (WEST_EXIT[0] + WEST_EXIT[1]) / 2, 4.75), rz=90)

# ================================================================== vault: ribs every 4 m + bays with skylight strip, banners
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
inner = {round(VR - 0.6, 4)}


def rib_side(a, b, m):      # cyan strip along the rib's inner (underside) arc on the middle segments
    r = lambda p: math.hypot(p[0], p[1] - VZC)
    return 1 if (abs(r(a) - (VR - 0.6)) < 1e-3 and abs(r(b) - (VR - 0.6)) < 1e-3 and abs(a[0]) < 6.5) else 0


rib = fc.xform(fc.extrude2d(rp, rf, [0] * len(rf), 0.4, -0.2, side_mat=rib_side), rot_z=90)
me_rib = module("MOD_N_RoofRib", rib, [CHR, CYN], recalc=True)
bp, bf = arc_band(VR, VR + 0.1)
bay = fc.xform(fc.extrude2d(bp, bf, [1 if 5 <= k <= 10 else 0 for k in range(16)], 4.0, -2.0), rot_z=90)
me_bay = module("MOD_N_RoofBay_4m", bay, [SIL, GLS], recalc=True)
for i, x in enumerate(range(-18, 19, 4)):
    place(f"SM_N2_RoofRib_{i:02d}", me_rib, (x, 0, 0), coll=C_ROOF)
for i, x in enumerate(X_PANELS):
    place(f"SM_N2_RoofBay_{i:02d}", me_bay, (x, 0, 0), coll=C_ROOF)
me_ban = module("MOD_N_Banner", nk.banner(), [CLO, SIL])
for i, x in enumerate((2.0, 10.0)):
    place(f"SM_N2_Banner_{i + 1:02d}", me_ban, (x, -HY, 4.4), 180)

# ================================================================== upper level: deck, landings, columns, control room
fasc = lambda x0, x1, y: (*BM(x0, x1, y - 0.02, y, UP_Z - 0.32, UP_Z - 0.24), 1)        # cyan underlight strip
deck = fc.mparts((*BM(LAND_L[1], CR_X1, CR_Y0, HY, UP_Z - 0.4, UP_Z), 0),
                 (*BM(BR_X0, LAND_L[1], LAND_L[3], HY, UP_Z - 0.4, UP_Z), 0),
                 fasc(LAND_L[1], CR_X1, CR_Y0))
unique("SM_N2_UpperDeck", deck, [SIL, CYN])
landing = fc.mparts((*BM(-1.5, 1.5, -1.5, 1.5, UP_Z - 0.4, UP_Z), 0), fasc(-1.5, 1.5, -1.5))
me_land = module("MOD_N_BridgeLanding_3x3", landing, [SIL, CYN])
place("SM_N2_BridgeLanding_L", me_land, ((LAND_L[0] + LAND_L[1]) / 2, (LAND_L[2] + LAND_L[3]) / 2, 0), 180)
place("SM_N2_BridgeLanding_R", me_land, ((LAND_R[0] + LAND_R[1]) / 2, (LAND_R[2] + LAND_R[3]) / 2, 0), 0)
col("COL_N2_UpperDeck", BM(BR_X0, CR_X1, CR_Y0, HY, UP_Z - 0.4, UP_Z))
col("COL_N2_Landing_R", BM(*LAND_R, UP_Z - 0.4, UP_Z))
cols_xy = [(-13.6, 8.6), (-8.0, 8.6), (-0.5, 8.0), (-13.6, -8.4), (-11.4, -8.4)]
me_colm = module("MOD_N_Column_4.6", fc.prism(nk.ngon(8, 0.28), 0.0, UP_Z - 0.4, side_mats=[0, 1] * 4), [SIL, CHR])
for i, (x, y) in enumerate(cols_xy):
    place(f"SM_N2_Column_{i:02d}", me_colm, (x, y, 0))
col("COL_N2_Columns", fc.merge(*[BM(x - 0.28, x + 0.28, y - 0.28, y + 0.28, 0, UP_Z - 0.4) for x, y in cols_xy]))

# control room shell: roof with cyan fascia, mullions every 2 m, sill; glass separate
shell = [(*BM(CR_X0 - 0.1, CR_X1 + 0.1, CR_Y0 - 0.1, HY, CR_TOP, CR_TOP + 0.4), 0),
         (*BM(CR_X0 - 0.1, CR_X1 + 0.1, CR_Y0 - 0.12, CR_Y0 - 0.1, CR_TOP + 0.12, CR_TOP + 0.22), 1),
         (*BM(CR_X0, CR_X1, CR_Y0 - 0.08, CR_Y0, UP_Z, UP_Z + 0.3), 0)]
for x in (CR_X0, -6.0, -4.0, -2.0, CR_X1):
    shell.append((*BM(x - 0.06, x + 0.06, CR_Y0 - 0.1, CR_Y0 + 0.02, UP_Z + 0.3, CR_TOP), 0))
for x, ys in ((CR_X0, (DOOR_W[0], DOOR_W[1], 9.0)), (CR_X1, (7.0, DOOR_E[0]))):
    for y in ys:
        shell.append((*BM(x - 0.06, x + 0.06, y - 0.06, y + 0.06, UP_Z, CR_TOP), 0))
unique("SM_N2_ControlRoom_Shell", fc.mparts(*shell), [CHR, CYN])
glass = [BM(CR_X0, CR_X1, CR_Y0 - 0.05, CR_Y0 - 0.01, UP_Z + 0.3, CR_TOP),
         BM(CR_X0 - 0.03, CR_X0 + 0.01, CR_Y0, DOOR_W[0], UP_Z, CR_TOP),
         BM(CR_X0 - 0.03, CR_X0 + 0.01, DOOR_W[1], HY, UP_Z, CR_TOP),
         BM(CR_X0 - 0.03, CR_X0 + 0.01, DOOR_W[0], DOOR_W[1], UP_Z + 3.0, CR_TOP),
         BM(CR_X1 - 0.01, CR_X1 + 0.03, CR_Y0, DOOR_E[0], UP_Z, CR_TOP),
         BM(CR_X1 - 0.01, CR_X1 + 0.03, DOOR_E[0], DOOR_E[1], UP_Z + 3.0, CR_TOP)]
unique("SM_N2_ControlRoom_Glass", (*fc.merge(*glass), [0] * (6 * len(glass))), [GLS], recalc=True)
col("COL_N2_ControlRoom", fc.merge(BM(CR_X0, CR_X1, CR_Y0 - 0.1, CR_Y0, UP_Z, CR_TOP),
                                   BM(CR_X0 - 0.1, CR_X0, CR_Y0, DOOR_W[0], UP_Z, CR_TOP),
                                   BM(CR_X0 - 0.1, CR_X0, DOOR_W[1], HY, UP_Z, CR_TOP),
                                   BM(CR_X1, CR_X1 + 0.1, CR_Y0, DOOR_E[0], UP_Z, CR_TOP),
                                   BM(CR_X0 - 0.1, CR_X1 + 0.1, CR_Y0 - 0.1, HY, CR_TOP, CR_TOP + 0.4)))
desk = fc.mparts((*BM(-1.0, 1.0, -0.3, 0.4, 0, 0.8, skip=("bottom",)), 0),
                 (*fc.slab_grid([-1.0, -0.8, 0.8, 1.0], [-0.4, -0.3, 0.3, 0.4], 0.8,
                                lambda x, y: 0.9 + (y + 0.4) / 0.8 * 0.15, lambda i, j: 2 if (i, j) == (1, 1) else 1,
                                side_mat=1, bottom=False),),
                 (*BM(-0.7, 0.7, 0.3, 0.38, 1.05, 1.55), 1), (*BM(-0.62, 0.62, 0.28, 0.3, 1.1, 1.5), 2))
me_desk = module("MOD_N_ControlDesk", desk, [SIL, CHR, CYN])
for i, x in enumerate((-6.0, -2.0)):
    place(f"SM_N2_ControlDesk_{i + 1:02d}", me_desk, (x, 6.0, UP_Z), 180)
col("COL_N2_ControlDesks", fc.merge(*[BM(x - 1.0, x + 1.0, 5.6, 6.4, UP_Z, UP_Z + 1.1) for x in (-6.0, -2.0)]))

# ================================================================== bridge (3 spans + 2 landings), truss sides
def span():
    p = [(*BM(-1.5, 1.5, -2.0, 2.0, UP_Z - 0.4, UP_Z), 0),
         (*BM(-1.52, -1.5, -2.0, 2.0, UP_Z - 0.32, UP_Z - 0.24), 1),
         (*BM(1.5, 1.52, -2.0, 2.0, UP_Z - 0.32, UP_Z - 0.24), 1)]
    for sx in (-1.0, 1.0):
        x0, x1 = (sx * 1.5, sx * 1.35) if sx < 0 else (sx * 1.35, sx * 1.5)
        p += [(*BM(x0, x1, -2.0, 2.0, UP_Z, UP_Z + 0.15, skip=("bottom",)), 2),            # bottom chord
              (*BM(x0, x1, -2.0, 2.0, UP_Z + 0.98, UP_Z + 1.1), 0),                        # top chord / handrail
              (*BM(x0, x1, -2.0, -1.88, UP_Z + 0.15, UP_Z + 0.98, skip=("top", "bottom")), 2),     # post
              (*fc.sheared_box(x0 + 0.02, x1 - 0.02, -1.86, UP_Z + 0.15, 1.95, UP_Z + 0.86, 0.12), 2),  # diagonal
              (*BM(x0 + 0.03 * sx, x1, -1.88, 2.0, UP_Z + 0.92, UP_Z + 0.96), 1)]           # cyan strip under rail
    return fc.mparts(*p)


me_span = module("MOD_N_Bridge_4m", span(), [SIL, CYN, CHR])
bx = (BR_X0 + BR_X1) / 2
for i, y in enumerate((-5.0, -1.0, 3.0)):
    place(f"SM_N2_Bridge_{i + 1:02d}", me_span, (bx, y, 0))
unique("SM_N2_BridgeEndPosts", fc.mparts(*[(*BM(x0, x0 + 0.15, BR_Y1 - 0.12, BR_Y1, UP_Z, UP_Z + 1.1), 0)
                                           for x0 in (BR_X0, BR_X1 - 0.15)]), [CHR])
col("COL_N2_Bridge", fc.merge(BM(BR_X0, BR_X1, BR_Y0, BR_Y1, UP_Z - 0.4, UP_Z),
                              BM(BR_X0, BR_X0 + 0.15, BR_Y0, BR_Y1, UP_Z, UP_Z + 1.1),
                              BM(BR_X1 - 0.15, BR_X1, BR_Y0, BR_Y1, UP_Z, UP_Z + 1.1)))

# glass railings on open upper edges (modules by length; along X unless rotated)
rail_me = {L: module(f"MOD_N_Railing_Glass_{L}m", nk.railing(L), [GLS, SIL]) for L in (1, 2, 3, 4)}
up_rails = [("Vest", 3, (-9.5, CR_Y0 + 0.06, UP_Z), 0),
            ("DeckW_a", 4, (BR_X0 + 0.06, 7.0, UP_Z), 90), ("DeckW_b", 1, (BR_X0 + 0.06, 9.5, UP_Z), 90),
            ("LandR_W", 3, (BR_X0 + 0.06, -8.5, UP_Z), 90), ("LandR_E", 1, (BR_X1 - 0.06, -7.5, UP_Z), 90)]
for n, L, loc, rz in up_rails:
    place(f"SM_N2_UpperRail_{n}", rail_me[L], loc, rz)
col("COL_N2_UpperRails", fc.merge(BM(LAND_L[1], CR_X0, CR_Y0, CR_Y0 + 0.12, UP_Z, UP_Z + 1.1),
                                  BM(BR_X0, BR_X0 + 0.12, LAND_L[2], HY, UP_Z, UP_Z + 1.1),
                                  BM(BR_X0, BR_X0 + 0.12, LAND_R[2], LAND_R[3], UP_Z, UP_Z + 1.1),
                                  BM(BR_X1 - 0.12, BR_X1, -8.0, LAND_R[3], UP_Z, UP_Z + 1.1)))

# ================================================================== stairs + sloped rails
me_stair = module("MOD_N_Stair_2m_5rise", nk.stair(2.0, RISERS, RISE, TREAD), [SIL, CHR])
ramp = nk.stair_ramp(2.0, RISERS, RISE, TREAD)
for side, top_x, y, rail_y in (("L", CR_X1, 9.0, 8.0), ("R", BR_X1, -9.0, -8.0)):
    place(f"SM_N2_Stair_{side}", me_stair, (top_x, y, 0), 90)
    col(f"COL_N2_Stair_{side}", fc.xform(ramp, rot_z=90, offset=(top_x, y, 0)))
    r = fc.xform(nk.sloped_rail(0.0, -RUN - TREAD, 0.0, 0.0, UP_Z), rot_z=90, offset=(top_x, rail_y, 0))
    unique(f"SM_N2_StairRail_{side}", r, [GLS, SIL])
    col(f"COL_N2_StairRail_{side}", fc.xform(fc.sheared_box(-0.05, 0.05, -RUN - TREAD, 0.0, 0.0, UP_Z, 1.1),
                                             rot_z=90, offset=(top_x, rail_y, 0)))

# ================================================================== power nodes, generator + sockets
NODES = {"01": ((6.0, -8.9, 0.0), 3), "02": ((-12.5, 9.0, UP_Z), 4), "03": ((16.0, 8.6, 0.0), 6)}
landmarks = {}
for n, (loc, sides) in NODES.items():
    o = unique(f"SM_PowerNode_{n}", nk.power_node(sides, seed=int(n)), [SIL, CHR, CYN], loc=loc, recalc=True)
    o["node_index"] = int(n)
    o["base_shape"] = {3: "triangle", 4: "square", 6: "hexagon"}[sides]
    col(f"COL_PowerNode_{n}", fc.xform(fc.prism(nk.ngon(sides, 0.6), 0.0, 2.45)[:2], offset=loc))
    landmarks[f"LM_PowerNode_{n}"] = loc
GEN = (12.0, 9.2, 0.0)
gp = [(-0.7, 0.0), (0.7, 0.0), (0.7, 1.4), (0.5, 1.6), (-0.5, 1.6), (-0.7, 1.4)]
gbody = fc.xform(fc.extrude2d(gp, [(0, 1, 2), (0, 2, 3), (0, 3, 4), (0, 4, 5)], [0] * 4, 2.4, -1.2), rot_z=90)
gen = fc.mparts(gbody,
                *[(*BM(x - 0.05, x + 0.05, -0.72, -0.7, 0.4, 1.2), 1) for x in (-1.0, -0.85, 0.85, 1.0)],
                (*BM(-0.5, -0.4, -0.06, 0.06, 1.6, 1.85, skip=("bottom",)), 2),
                (*BM(0.4, 0.5, -0.06, 0.06, 1.6, 1.85, skip=("bottom",)), 2),
                (*BM(-0.5, 0.5, -0.06, 0.06, 1.85, 1.95), 2))                      # carry handle
unique("SM_Generator", gen, [CHR, CYN, SIL], loc=GEN, recalc=True)
col("COL_Generator", fc.xform(BM(-1.2, 1.2, -0.7, 0.7, 0, 1.6), offset=GEN))
me_port = module("MOD_N_RingPort", nk.ring_port(), [SIL, CHR])
for s, dx in zip("ABC", (-0.45, 0.0, 0.45)):
    o = place(f"SM_Socket_{s}", me_port, (GEN[0] + dx, GEN[1] - 0.7 - 0.03, 0.85))
    o["connector"] = "A2_ring"
landmarks["LM_Generator"] = GEN

# ================================================================== platform props: 3 covers + 2 benches per platform
me_crate = module("MOD_N_CoverCrate", nk.crate(), [SIL, CHR])
me_plant = module("MOD_N_CoverPlanter", nk.planter(), [CHR, MOSS])
me_bench = module("MOD_N_Bench", nk.bench(), [SIL, CHR])
COVERS = [((-16.0, -9.2), me_crate), ((1.0, -9.2), me_plant), ((13.0, -9.2), me_crate),
          ((-12.0, 9.2), me_plant), ((-6.0, 9.2), me_crate), ((-2.5, 9.2), me_plant)]
BENCHES = [((9.0, -9.5), 180), ((4.0, -9.5), 180), ((-9.5, 9.6), 0), ((-16.0, 9.6), 0)]
for i, ((x, y), me) in enumerate(COVERS):
    place(f"SM_N2_Cover_{i:02d}", me, (x, y, 0))
for i, ((x, y), rz) in enumerate(BENCHES):
    place(f"SM_N2_Bench_{i:02d}", me_bench, (x, y, 0), rz)
col("COL_N2_Props", fc.merge(*[BM(x - 0.6, x + 0.6, y - 0.6, y + 0.6, 0, 1.1) for (x, y), _ in COVERS],
                             *[BM(x - 0.9, x + 0.9, y - 0.3, y + 0.3, 0, 0.9) for (x, y), _ in BENCHES]))

# ================================================================== landmarks (identical to blockout)
bx = (BR_X0 + BR_X1) / 2
landmarks.update({
    "LM_Entrance": (HX, (STREET[0] + STREET[1]) / 2, 0.0), "LM_Exit_West": (-HX, (WEST_EXIT[0] + WEST_EXIT[1]) / 2, 0.0),
    "LM_Platform_R": (0.0, -7.0, 0.0), "LM_Platform_L": (0.0, 7.0, 0.0),
    "LM_ControlRoom": ((CR_X0 + CR_X1) / 2, (CR_Y0 + HY) / 2, UP_Z),
    "LM_Bridge_R": (bx, BR_Y0, UP_Z), "LM_Bridge_L": (bx, BR_Y1, UP_Z),
    "LM_Stair_L": (CR_X1 + RUN, 9.0, 0.0), "LM_Stair_L_Top": (CR_X1, 9.0, UP_Z),
    "LM_Stair_R": (BR_X1 + RUN, -9.0, 0.0), "LM_Stair_R_Top": (BR_X1, -9.0, UP_Z),
    "LM_TrenchRamp_E": (12.1, 3.25, 0.0), "LM_TrenchRamp_W": (-12.1, -3.25, 0.0),
})
for n, p in landmarks.items():
    fc.empty(n, p, C_LM, 0.8, "ARROWS").hide_render = True

# ================================================================== presentation + renders
fc.ref_player(C_REF, (11.0, -5.4, 0))
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
cam_eye = cam("CAM_EyeHeight", (HX - 0.5, -7.0, 1.7), target=(-4.0, 7.5, 5.6))
cam_hero = cam("CAM_Hero34", (15.5, -8.8, 5.6), target=(-7.0, 3.0, 4.2), lens=20)
sun_d = bpy.data.lights.new("LGT_Key_6500K", "SUN")
sun_d.energy = 3.5
try:
    sun_d.use_temperature, sun_d.temperature = True, 6500
except Exception:
    sun_d.color = (0.95, 0.97, 1.0)
sun = bpy.data.objects.new("LGT_Key_6500K", sun_d)
sun.rotation_euler = (math.radians(28), 0, math.radians(15))
C_PRES.objects.link(sun)
sc.world.use_nodes = True
bg = sc.world.node_tree.nodes.get("Background")
bg.inputs[0].default_value = fc.hex_lin("#C9D6E3")
bg.inputs[1].default_value = 0.55
renders = {}
C_ROOF.hide_render = True
sc.camera = cam_top
renders["topdown"] = fc.render(os.path.join(fc.RENDER_DIR, "N2_detail_topdown.png"), engine="BLENDER_EEVEE")
C_ROOF.hide_render = False
sc.camera = cam_eye
renders["eye"] = fc.render(os.path.join(fc.RENDER_DIR, "N2_detail_eyeheight.png"), engine="BLENDER_EEVEE")
sc.camera = cam_hero
renders["hero"] = fc.render(os.path.join(fc.RENDER_DIR, "N2_detail_hero34.png"), engine="BLENDER_EEVEE")
sun.hide_render = True
bg.inputs[1].default_value = 1.0
sc.camera = cam_eye
renders["eye_flat_ambient"] = fc.render(os.path.join(fc.RENDER_DIR, "N2_detail_eyeheight_flat.png"), engine="BLENDER_EEVEE")
sun.hide_render = False
bg.inputs[1].default_value = 0.55
sc.camera = cam_hero

# ================================================================== Block Z + export
blend = os.path.join(fc.SOURCE_DIR, f"Fractured_{ID}_{NAME}.blend")
glb = os.path.join(fc.EXPORT_DIR, f"Fractured_{ID}_{NAME}.glb")
report = qa.run(ID, C_EXP, C_COL, C_FX, budget=150000, landmark_coll=C_LM, walk_bounds=(-HX, HX, -HY, HY),
                walkable_prefixes=("COL_N2_Platform", "COL_N2_TrenchFloor", "COL_N2_TrenchRamp", "COL_N2_Stair_",
                                   "COL_N2_UpperDeck", "COL_N2_Landing", "COL_N2_Bridge"),
                pair_with=os.path.join(fc.RENDER_DIR, "N2_blockout_landmarks.json"),
                allowed_drop=lambda lo, hi: abs(lo[1]) < TR)         # any drop into the track trench (designed hazard)
report["rotations_baked"] = baked
report["renders"] = renders
report["blend"] = blend
fc.save(blend)
report["export"] = qa.export_and_verify(C_EXP, C_COL, glb)
report["glb"] = glb
with open(os.path.join(fc.RENDER_DIR, "N2_QA_report.json"), "w") as fh:
    json.dump(report, fh, indent=2)
print("N2 DETAIL DONE pass=", report["pass"])
