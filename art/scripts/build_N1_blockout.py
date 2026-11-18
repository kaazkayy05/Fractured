"""N1 Nova Research Facility — BLOCKOUT stage (Block 0 workflow step 2).
Room interior: X -14..14, Y -9..9 (entrance on -Y), floor top z=0, ceiling/roof underside z=12.
Run: blender -b -P art/scripts/build_N1_blockout.py
"""
import os
import sys
import math
import json
import bpy

sys.path.insert(0, os.path.dirname(__file__))
import fractured_common as fc

ID = "N1"
sc = fc.reset_scene()
M = fc.append_shared_materials()
silver, glass, cyan, charcoal, amber, cloth = (M[k] for k in (
    "M_NovaSilver", "M_NovaGlass", "M_CyanEmissive", "M_Charcoal", "M_AmberWarning", "M_Cloth"))

C_EXP = fc.collection(f"{ID}_Export")
C_COL = fc.collection(f"{ID}_Collision")
C_FX = fc.collection(f"{ID}_FX")
C_PRES = fc.collection(f"{ID}_Presentation")
C_REF = fc.collection("_Reference")
C_LM = fc.collection(f"{ID}_Landmarks")
C_ROOF = fc.collection(f"{ID}_Roof", C_EXP)
C_MOD = fc.collection(f"{ID}_ModuleSources")   # one source copy of each module, excluded from view
B, BM = fc.build_mesh, fc.box_minmax

# ------------------------------------------------------------------ dimensions
HX, HY, H = 14.0, 9.0, 12.0          # half extents, ceiling
WT = 0.3                              # wall thickness (outside interior footprint)
BAL_Z, BAL_D, BAL_T = 4.5, 3.0, 0.4   # balcony top, depth, slab thickness
BAL_Y0 = HY - BAL_D                   # 6.0
STAIR_X0, STAIR_X1 = 12.0, 14.0       # 2 m wide against +X wall
RISE, TREAD = 0.18, 0.30
N_TREADS = 24                         # 25 risers -> 4.5 m (last riser = balcony slab edge)
STAIR_RUN = N_TREADS * TREAD          # 7.2
STAIR_Y0 = BAL_Y0 - STAIR_RUN         # -1.2
MAIN_DOOR_W, MAIN_DOOR_H = 4.0, 4.0
SIDE_DOOR_W, SIDE_DOOR_H = 2.0, 3.0
SIDE_DOOR_Y = -7.0                    # centre of side exit on +X wall
RING_R, RING_W = 4.5, 0.2
CONSOLE_R = 5.2
CONSOLE_CLOCK = {"01": 7, "02": 6, "03": 5}

# ------------------------------------------------------------------ floor
fc.obj("SM_N1_Floor", B("SM_N1_Floor", BM(-HX, HX, -HY, HY, -0.2, 0.0), [silver]), C_EXP)
fc.obj(f"COL_N1_Floor-colonly", B("COL_N1_Floor", BM(-HX - WT, HX + WT, -HY - WT, HY + WT, -0.2, 0.0)), C_COL)

# ------------------------------------------------------------------ walls (+ collision copies)
walls = {
    "S": [BM(-HX - WT, -MAIN_DOOR_W / 2, -HY - WT, -HY, 0, H),
          BM(MAIN_DOOR_W / 2, HX + WT, -HY - WT, -HY, 0, H),
          BM(-MAIN_DOOR_W / 2, MAIN_DOOR_W / 2, -HY - WT, -HY, MAIN_DOOR_H, H)],
    "N": [BM(-HX - WT, HX + WT, HY, HY + WT, 0, H)],
    "W": [BM(-HX - WT, -HX, -HY, HY, 0, H)],
    "E": [BM(HX, HX + WT, -HY, SIDE_DOOR_Y - SIDE_DOOR_W / 2, 0, H),
          BM(HX, HX + WT, SIDE_DOOR_Y + SIDE_DOOR_W / 2, HY, 0, H),
          BM(HX, HX + WT, SIDE_DOOR_Y - SIDE_DOOR_W / 2, SIDE_DOOR_Y + SIDE_DOOR_W / 2, SIDE_DOOR_H, H)],
}
for side, parts in walls.items():
    fc.obj(f"SM_N1_Wall_{side}", B(f"SM_N1_Wall_{side}", fc.merge(*parts), [silver]), C_EXP)
    fc.obj(f"COL_N1_Wall_{side}-colonly", B(f"COL_N1_Wall_{side}", fc.merge(*parts)), C_COL)

# ------------------------------------------------------------------ pilasters (linked duplicates)
pil_me = B("MOD_N_Pilaster", BM(-0.3, 0.3, -0.4, 0.0, 0, H), [silver])   # origin bottom-centre of wall face, protrudes -Y
pil_src = fc.obj("MOD_N_Pilaster", pil_me, C_MOD)
pilasters = []
for x in (-10, -6, -2, 2, 6, 10):
    pilasters.append((x, -HY, 180.0))   # protrude +Y into room
    pilasters.append((x, HY, 0.0))      # protrude -Y
for y in (-5, -1, 3, 7):
    pilasters.append((-HX, y, 90.0))    # protrude +X
for y in (-5, 7):                       # +X wall: skipped at y=-1,3 where the stair runs
    pilasters.append((HX, y, -90.0))
for i, (x, y, r) in enumerate(pilasters):
    fc.obj(f"SM_N1_Pilaster_{i:02d}", pil_me, C_EXP, (x, y, 0), r)

# ------------------------------------------------------------------ doors frames (blockout volumes)
df4 = B("MOD_N_DoorFrame_4x4", fc.merge(BM(-2.4, -2.0, -0.25, 0.15, 0, 4.4), BM(2.0, 2.4, -0.25, 0.15, 0, 4.4),
                                        BM(-2.0, 2.0, -0.25, 0.15, 4.0, 4.4)), [charcoal])
fc.obj("MOD_N_DoorFrame_4x4", df4, C_MOD)
fc.obj("SM_N1_DoorFrame_Main", df4, C_EXP, (0, -HY, 0), 0)
df2 = B("MOD_N_DoorFrame_2x3", fc.merge(BM(-1.3, -1.0, -0.25, 0.15, 0, 3.3), BM(1.0, 1.3, -0.25, 0.15, 0, 3.3),
                                        BM(-1.0, 1.0, -0.25, 0.15, 3.0, 3.3)), [charcoal])
fc.obj("MOD_N_DoorFrame_2x3", df2, C_MOD)
fc.obj("SM_N1_DoorFrame_Side", df2, C_EXP, (HX, SIDE_DOOR_Y, 0), 90)
# EXIT sign + arrow (geometry), above side exit, faces into room (-X)
sign = fc.merge(BM(-0.8, 0.8, -0.12, 0.0, 0, 0.45))
fc.obj("SM_N1_ExitSign", B("SM_N1_ExitSign", sign, [cyan]), C_EXP, (HX - 0.05, SIDE_DOOR_Y, 3.5), -90)
arrow = ([(-0.35, -0.02, 0.1), (0.15, -0.02, 0.1), (0.15, -0.02, 0.0), (0.45, -0.02, 0.225),
          (0.15, -0.02, 0.45), (0.15, -0.02, 0.35), (-0.35, -0.02, 0.35)],
         [(0, 1, 5, 6), (2, 3, 4)])
fc.obj("SM_N1_ExitArrow", B("SM_N1_ExitArrow", arrow, [silver], recalc=False), C_EXP,
       (HX - 0.18, SIDE_DOOR_Y, 3.5), -90)

# ------------------------------------------------------------------ banners (navy, M_Cloth)
ban = B("MOD_N_Banner", BM(-0.8, 0.8, -0.05, 0.0, 0, 5.0), [cloth])
for i, x in enumerate((-8, 8)):
    fc.obj(f"SM_N1_Banner_{i + 1:02d}", ban, C_EXP, (x, -HY + 0.06, 5.5), 180)

# ------------------------------------------------------------------ balcony
fc.obj("SM_N1_Balcony", B("SM_N1_Balcony", BM(-HX, HX, BAL_Y0, HY, BAL_Z - BAL_T, BAL_Z), [silver]), C_EXP)
fc.obj("COL_N1_Balcony-colonly", B("COL_N1_Balcony", BM(-HX, HX, BAL_Y0, HY, BAL_Z - BAL_T, BAL_Z)), C_COL)

def railing(length):
    return fc.with_material_index([
        (*BM(-length / 2, length / 2, -0.04, 0.04, 0.1, 1.0), 0),          # glass
        (*BM(-length / 2, length / 2, -0.06, 0.06, 1.0, 1.1), 1),          # top rail
        (*BM(-length / 2, -length / 2 + 0.08, -0.06, 0.06, 0, 1.0), 1),    # post
    ])

rail_meshes = {}
for L in (4, 2):
    v, f, fm = railing(L)
    me = B(f"MOD_N_Railing_Glass_{L}m", (v, f), [glass, silver], face_mats=fm)
    rail_meshes[L] = me
    fc.obj(f"MOD_N_Railing_Glass_{L}m", me, C_MOD)
rails = [(x, 4) for x in (-12, -8, -4, 0, 4, 8)] + [(11, 2)]
for i, (x, L) in enumerate(rails):
    fc.obj(f"SM_N1_BalconyRail_{i:02d}", rail_meshes[L], C_EXP, (x, BAL_Y0 + 0.1, BAL_Z), 0)
fc.obj("COL_N1_BalconyRail-colonly", B("COL_N1_BalconyRail", BM(-HX, STAIR_X0, BAL_Y0 + 0.04, BAL_Y0 + 0.16, BAL_Z, BAL_Z + 1.1)), C_COL)

# Office windows behind balcony (backlit emissive panels, non-enterable)
win = B("MOD_N_OfficeWindow", BM(-1.6, 1.6, -0.06, 0.0, 0, 3.0), [cyan])
for i, x in enumerate((-12, -8, -4, 0, 4, 8, 12)):
    fc.obj(f"SM_N1_OfficeWindow_{i:02d}", win, C_EXP, (x, HY, BAL_Z + 0.8), 0)

# ------------------------------------------------------------------ stair (+X side) and its collision
stair_me = B("MOD_N_Stair_2m_4.5rise", fc.stair_data(2.0, N_TREADS, TREAD, RISE), [silver])
fc.obj("MOD_N_Stair_2m_4.5rise", stair_me, C_MOD)
SX = (STAIR_X0 + STAIR_X1) / 2
fc.obj("SM_N1_BalconyStair", stair_me, C_EXP, (SX, STAIR_Y0, 0), 0)
fc.obj("COL_N1_Stair-colonly", B("COL_N1_Stair", fc.wedge_data(STAIR_X0, STAIR_X1, STAIR_Y0, BAL_Y0, BAL_Z)), C_COL)
stair_rail = fc.sheared_box(STAIR_X0 - 0.06, STAIR_X0 + 0.06, STAIR_Y0, 0.0, BAL_Y0, BAL_Z, 1.1)
fc.obj("SM_N1_StairRail", B("SM_N1_StairRail", stair_rail, [silver]), C_EXP)
fc.obj("COL_N1_StairRail-colonly", B("COL_N1_StairRail", stair_rail), C_COL)

# ------------------------------------------------------------------ vessel
PL_R, PL_H = 1.75, 0.6
fc.obj("SM_Vessel_Base", B("SM_Vessel_Base", fc.merge(
    fc.cylinder_data(PL_R, PL_H, 24),
    BM(-1.0, 1.0, -PL_R - 0.9, -1.3, 0, 0.2),     # 3 steps on the front (-Y), 0.2 rise / 0.3 tread
    BM(-1.0, 1.0, -PL_R - 0.6, -1.3, 0.2, 0.4),
    BM(-1.0, 1.0, -PL_R - 0.3, -1.3, 0.4, 0.6)), [charcoal]), C_EXP)
fc.obj("SM_Vessel_Glass", B("SM_Vessel_Glass", fc.lathe([(1.5, 0), (1.5, 6.0), (1.44, 6.0), (1.44, 0)], 24, closed=True),
                           [glass]), C_EXP, (0, 0, PL_H))
fc.obj("SM_Vessel_Cap", B("SM_Vessel_Cap", fc.merge(
    fc.cylinder_data(1.7, 0.8, 24)), [charcoal]), C_EXP, (0, 0, PL_H + 6.0))
fc.obj("SM_Vessel_CapRing", B("SM_Vessel_CapRing", fc.lathe([(1.7, 0), (1.78, 0), (1.78, 0.15), (1.7, 0.15)], 24),
                             [cyan]), C_EXP, (0, 0, PL_H + 6.3))
crystal = fc.lathe([(0, -1.25), (0.55, -0.35), (0.7, 0.2), (0, 1.25)], 6)
cr = fc.obj("SM_Vessel_Crystal", B("SM_Vessel_Crystal", crystal, [cyan]), C_EXP, (0, 0, 2.5))
cr.rotation_euler = (0, 0, math.radians(15))
fc.obj("SM_N1_FloorRing", B("SM_N1_FloorRing", fc.lathe(
    [(RING_R + RING_W / 2, 0), (RING_R + RING_W / 2, 0.01), (RING_R - RING_W / 2, 0.01), (RING_R - RING_W / 2, 0)], 64),
    [cyan]), C_EXP)
# collision: plinth 8 sides + steps ramp + glass (keeps player out of the cylinder)
fc.obj("COL_Vessel_Plinth-colonly", B("COL_Vessel_Plinth", fc.cylinder_data(PL_R, PL_H, 8, angle_offset=math.pi / 8)), C_COL)
fc.obj("COL_Vessel_Steps-colonly", B("COL_Vessel_Steps", fc.wedge_data(-1.0, 1.0, -PL_R - 0.9, -1.3, PL_H)), C_COL)
fc.obj("COL_Vessel_Glass-colonly", B("COL_Vessel_Glass", fc.cylinder_data(1.5, 6.8, 8, angle_offset=math.pi / 8)), C_COL,
       (0, 0, PL_H))

# ------------------------------------------------------------------ consoles (shared base mesh)
con_base = B("MOD_N_Console_Base", fc.merge(
    BM(-0.6, 0.6, -0.4, 0.4, 0, 0.8),
    fc.sheared_box(-0.55, 0.55, -0.3, 0.8, 0.35, 1.0, 0.1)), [silver])   # tilted screen slab to ~1.1 m
fc.obj("MOD_N_Console_Base", con_base, C_MOD)
tops = {
    "01": [BM(-0.35, 0.35, 0.15, 0.3, 1.0, 1.6)],                                   # single screen
    "02": [BM(-0.55, -0.05, 0.15, 0.3, 1.0, 1.55), BM(0.05, 0.55, 0.15, 0.3, 1.0, 1.55)],  # twin screens
    "03": [BM(-0.5, 0.2, 0.15, 0.3, 1.0, 1.55), BM(0.35, 0.55, -0.1, 0.3, 0.8, 2.0)],      # screen + side pillar
}
landmarks = {"LM_Vessel": (0.0, 0.0, 0.0)}
for n, clock in CONSOLE_CLOCK.items():
    theta = math.radians(90 - clock * 30)            # 12 o'clock = +Y, clockwise
    x, y = CONSOLE_R * math.cos(theta), CONSOLE_R * math.sin(theta)
    rz = math.degrees(theta) + 90                    # local -Y (operator side) faces away from vessel
    x, y = round(x, 3), round(y, 3)
    c = fc.obj(f"SM_Console_{n}", con_base, C_EXP, (x, y, 0), rz)
    t = fc.obj(f"SM_Console_{n}_Top", B(f"SM_Console_{n}_Top", fc.merge(*tops[n]), [cyan]), C_EXP)
    t.parent = c
    colb = fc.obj(f"COL_Console_{n}-colonly", B(f"COL_Console_{n}", BM(-0.6, 0.6, -0.4, 0.4, 0, 1.1)), C_COL, (x, y, 0), rz)
    landmarks[f"LM_Console_{n}"] = (x, y, 0.0)

landmarks["LM_Exit_Main"] = (0.0, -HY, 0.0)
landmarks["LM_Exit_Side"] = (HX, SIDE_DOOR_Y, 0.0)
landmarks["LM_BalconyStair"] = (SX, STAIR_Y0, 0.0)
landmarks["LM_BalconyStair_Top"] = (SX, BAL_Y0, BAL_Z)
for n, p in landmarks.items():
    fc.empty(n, p, C_LM, 0.8, "ARROWS")

# ------------------------------------------------------------------ roof (skylight bays, own collection)
def skylight(sy):
    b = 0.2
    return fc.with_material_index([
        (*BM(-2, 2, -sy / 2, -sy / 2 + b, 0, 0.5), 0), (*BM(-2, 2, sy / 2 - b, sy / 2, 0, 0.5), 0),
        (*BM(-2, -2 + b, -sy / 2 + b, sy / 2 - b, 0, 0.5), 0), (*BM(2 - b, 2, -sy / 2 + b, sy / 2 - b, 0, 0.5), 0),
        (*BM(-2 + b, 2 - b, -sy / 2 + b, sy / 2 - b, 0.3, 0.34), 1),
    ])
sky = {}
for sy, name in ((4.0, "MOD_N_Skylight_4x4"), (2.0, "MOD_N_Skylight_4x2")):
    v, f, fm = skylight(sy)
    sky[sy] = B(name, (v, f), [charcoal, glass], face_mats=fm)
    fc.obj(name, sky[sy], C_MOD)
rows = [(-7, 4.0), (-3, 4.0), (1, 4.0), (5, 4.0), (8, 2.0)]
k = 0
for x in (-12, -8, -4, 0, 4, 8, 12):
    for y, sy in rows:
        fc.obj(f"SM_N1_Skylight_{k:02d}", sky[sy], C_ROOF, (x, y, H), 0)
        k += 1

# ------------------------------------------------------------------ reference / presentation
fc.ref_player(C_REF, (0, -7.0, 0))
C_MOD.hide_render = True
C_COL.hide_render = True
for o in C_COL.objects:
    o.display_type = "WIRE"
for o in C_LM.objects:
    o.hide_render = True
bpy.context.view_layer.layer_collection.children[C_MOD.name].exclude = True

def cam(name, loc, rot, lens=24, ortho=None):
    cd = bpy.data.cameras.new(name)
    if ortho:
        cd.type, cd.ortho_scale = "ORTHO", ortho
    else:
        cd.lens = lens
    cd.clip_end = 200
    o = bpy.data.objects.new(name, cd)
    o.location, o.rotation_euler = loc, [math.radians(a) for a in rot]
    C_PRES.objects.link(o)
    return o

cam_top = cam("CAM_TopDown", (0, 0, 40), (0, 0, 0), ortho=34)
cam_eye = cam("CAM_EyeHeight", (-9.5, -8.3, 1.7), (95, 0, -46), lens=24)
sun_d = bpy.data.lights.new("LGT_Key_6500K", "SUN")
sun_d.color = (0.92, 0.96, 1.0)
sun = bpy.data.objects.new("LGT_Key_6500K", sun_d)
sun.rotation_euler = (math.radians(35), 0, math.radians(25))
C_PRES.objects.link(sun)

# ------------------------------------------------------------------ renders (Workbench, flat-ambient-friendly)
fc.setup_workbench("STUDIO", world_hex="#1C2026")
sc.display.shading.show_shadows = False
ref = bpy.data.objects["REF_Player"]
ref.hide_render = False            # visible in blockout previews for scale; hidden again before save
renders = {}
C_ROOF.hide_render = True
sc.camera = cam_top
renders["topdown"] = fc.render(os.path.join(fc.RENDER_DIR, "N1_blockout_topdown.png"))
C_ROOF.hide_render = False
sc.camera = cam_eye
# EEVEE for eye height so glass reads as glass; flat-ish ambient + cool key.
sc.world.use_nodes = True
bgn = sc.world.node_tree.nodes.get("Background")
bgn.inputs[0].default_value = fc.hex_lin("#C9D6E3")
bgn.inputs[1].default_value = 0.6
sun_d.energy = 3.0
renders["eye"] = fc.render(os.path.join(fc.RENDER_DIR, "N1_blockout_eyeheight.png"), engine="BLENDER_EEVEE")
ref.hide_render = True

# ------------------------------------------------------------------ report
rows, uniq, inst = fc.tri_report([C_EXP])
_, cu, ci = fc.tri_report([C_COL])
report = {
    "footprint_interior_m": [2 * HX, 2 * HY], "ceiling_m": H, "wall_thickness_m": WT,
    "balcony": {"top_z": BAL_Z, "y_range": [BAL_Y0, HY], "depth": BAL_D},
    "stair": {"x_range": [STAIR_X0, STAIR_X1], "y_range": [STAIR_Y0, BAL_Y0], "risers": N_TREADS + 1,
              "rise": RISE, "tread": TREAD, "slope_deg": round(math.degrees(math.atan2(BAL_Z, STAIR_RUN)), 1)},
    "main_door": {"centre": [0, -HY], "w": MAIN_DOOR_W, "h": MAIN_DOOR_H},
    "side_door": {"centre": [HX, SIDE_DOOR_Y], "w": SIDE_DOOR_W, "h": SIDE_DOOR_H},
    "vessel": {"plinth_d": 2 * PL_R, "plinth_h": PL_H, "glass_d": 3.0, "glass_h": 6.0, "cap_top_z": PL_H + 6.8,
               "crystal_centre_z": 2.5, "crystal_h": 2.5},
    "floor_ring": {"radius": RING_R, "width": RING_W, "clear_to_walls_m": round(HY - (RING_R + RING_W / 2), 2)},
    "landmarks": {k: [round(c, 3) for c in v] for k, v in landmarks.items()},
    "tris_export_unique": uniq, "tris_export_instanced": inst,
    "tris_collision": ci, "budget": 120000,
}
blend = os.path.join(fc.SOURCE_DIR, "Fractured_N1_ResearchFacility.blend")
fc.save(blend)
report["blend"] = blend
report["renders"] = renders
with open(os.path.join(fc.RENDER_DIR, "N1_blockout_report.json"), "w") as fh:
    json.dump(report, fh, indent=2)
print("N1 REPORT", json.dumps(report, indent=2))
