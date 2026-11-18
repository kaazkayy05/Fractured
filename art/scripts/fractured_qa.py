"""Block Z â€” scripted QA checks + export/re-import verification for Fractured assets."""
import os
import json
import math
import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

import fractured_common as fc

STRUCTURAL = tuple(f"MOD_{k}_{p}" for k in ("N", "V")
                   for p in ("Floor", "Wall", "Skylight", "Pilaster", "DoorFrame", "Stair"))
ALLOWED_NODES = {"BSDF_PRINCIPLED", "OUTPUT_MATERIAL"}


def _meshes(coll):
    return [o for o in coll.all_objects if o.type == "MESH"]


def _on_grid(v, step=0.5, tol=1e-4):
    return abs(v / step - round(v / step)) * step < tol


def _bvh(objs):
    verts, polys, owners = [], [], []
    for o in objs:
        mw = o.matrix_world
        off = len(verts)
        verts += [mw @ v.co for v in o.data.vertices]
        for p in o.data.polygons:
            polys.append([off + i for i in p.vertices])
            owners.append(o.name)
    return BVHTree.FromPolygons(verts, polys, epsilon=1e-6), owners


def _entries_down(bvh, name, x, y, z_start=60.0):
    """Upward-facing entry surfaces of ONE closed collider along a downward ray."""
    out, inside, z = [], False, z_start
    for _ in range(64):
        loc, n, idx, d = bvh.ray_cast(Vector((x, y, z)), Vector((0, 0, -1)))
        if loc is None:
            break
        if n.z > 1e-3:
            if not inside:
                out.append((loc.z, n.copy(), name))
            inside = True
        elif n.z < -1e-3:
            inside = False
        z = loc.z - 1e-3
    return out


def _inside_any(per_obj, p):
    """Point is inside a closed collider if the first hit straight up is that collider's up-facing (inner) side."""
    for _, b in per_obj:
        loc, n, _, _ = b.ray_cast(p, Vector((0, 0, 1)))
        if loc is not None and n.z > 1e-3:
            return True
    return False


def _surfaces_down(per_obj, x, y):
    """Standable surfaces (any collider) not buried inside another collider, highest first."""
    out = []
    for name, b in per_obj:
        for z, n, nm in _entries_down(b, name, x, y):
            if not _inside_any(per_obj, Vector((x, y, z + 0.02))):
                out.append((z, n, nm))
    return sorted(out, key=lambda s: -s[0])


def check_geometry(objs, closed_required=False):
    rows, seen = [], set()
    for o in objs:
        me = o.data
        if me.name in seen:
            continue
        seen.add(me.name)
        bm = bmesh.new()
        bm.from_mesh(me)
        ngons = sum(1 for f in bm.faces if len(f.verts) > 4)
        zero = sum(1 for f in bm.faces if f.calc_area() < 1e-7)
        nonman = sum(1 for e in bm.edges if not e.is_manifold)
        boundary = sum(1 for e in bm.edges if e.is_boundary)
        inverted = None
        if nonman == 0 and len(bm.faces):
            inverted = bm.calc_volume(signed=True) < 0
        bm.free()
        rows.append(dict(mesh=me.name, obj=o.name, ngons=ngons, zero_area=zero, non_manifold_edges=nonman,
                         boundary_edges=boundary, inverted=inverted))
    fails = [r for r in rows if r["ngons"] or r["zero_area"] or r["inverted"]
             or (closed_required and r["non_manifold_edges"])]
    return rows, fails


def wall_and_floor_seams(objs):
    floor, walls = [], {}
    for o in objs:
        dn = o.data.name
        bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
        xs, ys, zs = [p.x for p in bb], [p.y for p in bb], [p.z for p in bb]
        if dn.startswith(("MOD_N_Floor", "MOD_V_Floor")):
            floor.append((min(xs), max(xs), min(ys), max(ys)))
        elif dn.startswith(("MOD_N_Wall", "MOD_V_Wall")):
            rz = round(math.degrees(o.rotation_euler.z)) % 360
            along_x = rz in (0, 180)
            plane = round(o.location.y if along_x else o.location.x, 3)
            key = (rz, plane, round(o.location.z, 2))
            walls.setdefault(key, []).append((min(xs), max(xs)) if along_x else (min(ys), max(ys)))
    res = {"floor_tiles": len(floor)}
    if floor:
        area = sum((a[1] - a[0]) * (a[3] - a[2]) for a in floor)
        ext = (min(f[0] for f in floor), max(f[1] for f in floor), min(f[2] for f in floor), max(f[3] for f in floor))
        overlap = 0.0
        for i in range(len(floor)):
            for j in range(i + 1, len(floor)):
                a, b = floor[i], floor[j]
                ox = min(a[1], b[1]) - max(a[0], b[0])
                oy = min(a[3], b[3]) - max(a[2], b[2])
                if ox > 1e-4 and oy > 1e-4:
                    overlap += ox * oy
        res.update(floor_extent=[round(v, 4) for v in ext], floor_area=round(area, 4),
                   floor_extent_area=round((ext[1] - ext[0]) * (ext[3] - ext[2]), 4),
                   floor_overlap_m2=round(overlap, 6))
        res["floor_gap_m2"] = round(res["floor_extent_area"] - area + overlap, 6)
    seam_fail, openings = [], []
    for key, iv in walls.items():
        iv.sort()
        for (a0, a1), (b0, b1) in zip(iv, iv[1:]):
            gap = b0 - a1
            if abs(gap) <= 1e-3:
                continue
            (openings if gap >= 1.99 else seam_fail).append(dict(row=str(key), gap_m=round(gap, 4), at=round(a1, 3)))
    res.update(wall_rows=len(walls), wall_seam_failures=seam_fail, wall_openings=openings)
    return res


def walk_test(col_objs, vis_objs, bounds, walkable_prefixes, step=1.0, allowed_drop=None, jitter=0.037, mask=None):
    """Samples sit `jitter` m off the 0.5 m module grid so rays never graze module/stair/balcony edges exactly."""
    bpy.context.view_layer.update()
    cbvh, cown = _bvh(col_objs)
    per_obj = [(o.name, _bvh([o])[0]) for o in col_objs]
    vbvh, _ = _bvh(vis_objs)
    x0, x1, y0, y1 = bounds
    nx, ny = int(round((x1 - x0) / step)), int(round((y1 - y0) / step))
    cos_max = math.cos(math.radians(35))
    cache = {}

    def walkables(x, y):
        key = (round(x, 4), round(y, 4))
        if key in cache:
            return cache[key]
        res = []
        for z, n, own in _surfaces_down(per_obj, x, y):
            if not own.startswith(walkable_prefixes):
                continue
            hit, hn, _, d = cbvh.ray_cast(Vector((x, y, z + 0.02)), Vector((0, 0, 1)))
            if hit is not None and d < 1.8:
                continue                                   # obstacle above head height
            res.append((z, n, own))
        cache[key] = res
        return res

    def under_level(x, y, z_low, z_up):
        """True if a collider surface near z_up covers the lower point (multi-level, not an edge)."""
        hit, _, _, d = cbvh.ray_cast(Vector((x, y, z_low + 0.05)), Vector((0, 0, 1)))
        return hit is not None and (z_low + 0.05 + d) <= z_up + 0.05

    samples, holes, steep, low = {}, [], [], []
    min_ceiling = 1e9
    for i in range(nx):
        for j in range(ny):
            x, y = x0 + step / 2 + i * step + jitter, y0 + step / 2 + j * step + jitter
            if mask and not mask(x, y):
                continue                                       # outside a non-rectangular room footprint
            surf = walkables(x, y)
            samples[(i, j)] = surf
            if not surf:
                occupied = bool(_surfaces_down(per_obj, x, y))
                if not occupied:
                    holes.append((x, y))
                continue
            for z, n, own in surf:
                if n.z < cos_max:
                    steep.append(dict(x=x, y=y, z=round(z, 3), slope=round(math.degrees(math.acos(min(1, n.z))), 1)))
                # start 0.5 m up: rails, decals, kerbs at floor level are not "ceilings"
                hit, _, _, d = vbvh.ray_cast(Vector((x, y, z + 0.5)), Vector((0, 0, 1)))
                c = (d + 0.5) if hit is not None else 1e9
                min_ceiling = min(min_ceiling, c)
                if c < 2.5:
                    low.append(dict(x=x, y=y, z=round(z, 3), ceiling=round(c, 3)))

    # edges to void: walkable sample next to a sample with no walkable surface -> something must stop the player
    edge_guarded, edge_open = 0, []
    for (i, j), surf in samples.items():
        if not surf:
            continue
        xa, ya = x0 + step / 2 + i * step + jitter, y0 + step / 2 + j * step + jitter
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if (i + di, j + dj) not in samples or samples[(i + di, j + dj)]:
                continue                                   # neighbour outside the room, or walkable
            for z, _, _ in surf:
                hit, _, _, d = cbvh.ray_cast(Vector((xa, ya, z + 0.6)), Vector((di, dj, 0)), step)
                if hit is not None:
                    edge_guarded += 1
                else:
                    edge_open.append(dict(at=[round(xa, 2), round(ya, 2), round(z, 3)], toward=[di, dj]))

    def nearest(x, y, zref):
        s = walkables(x, y)
        return min((abs(z - zref), z) for z, _, _ in s)[1] if s else None

    steps_guarded, steps_unguarded, designed_drops = 0, [], 0
    for (i, j), surf in samples.items():
        for di, dj in ((1, 0), (0, 1)):
            nb = samples.get((i + di, j + dj))
            if not nb:
                continue
            xa, ya = x0 + step / 2 + i * step + jitter, y0 + step / 2 + j * step + jitter
            xb, yb = xa + di * step, ya + dj * step
            for za, _, _ in surf:
                zb_ = min(nb, key=lambda s: abs(s[0] - za))[0]
                if abs(zb_ - za) <= 0.4:
                    continue
                # march between samples to see if a ramp/stair connects them
                zc, jump = za, 0.0
                for k in range(1, 11):
                    t = k / 10
                    zn = nearest(xa + (xb - xa) * t, ya + (yb - ya) * t, zc)
                    if zn is None:
                        jump = max(jump, 99)
                        break
                    jump = max(jump, abs(zn - zc))
                    zc = zn
                if jump <= 0.4 and abs(zc - zb_) < 0.05:
                    continue
                low_pt, z_low, z_up = ((xa, ya), za, zb_) if za < zb_ else ((xb, yb), zb_, za)
                high_pt = (xb, yb) if low_pt == (xa, ya) else (xa, ya)
                if under_level(low_pt[0], low_pt[1], z_low, z_up):
                    continue                                   # lower point sits beneath the upper level
                if allowed_drop and allowed_drop((*low_pt, z_low), (*high_pt, z_up)):
                    designed_drops += 1
                    continue                                   # intentional hazard edge (e.g. track trench)
                zt = max(za, zb_) + 0.6
                hit, _, _, d = cbvh.ray_cast(Vector((xa, ya, zt)), Vector((xb - xa, yb - ya, 0)).normalized())
                if hit is not None and d <= step:
                    steps_guarded += 1
                else:
                    steps_unguarded.append(dict(a=[xa, ya, round(za, 3)], b=[xb, yb, round(zb_, 3)]))
    return dict(samples=nx * ny, holes=holes, slopes_over_35=steep, ceilings_under_2_5=low,
                min_ceiling_m=round(min_ceiling, 3), drops_guarded=steps_guarded, drops_unguarded=steps_unguarded,
                drops_designed_hazard=designed_drops, edges_to_void_guarded=edge_guarded, edges_to_void_open=edge_open)


def check_materials(objs, fx_coll):
    over, proc, violet = [], [], []
    mats = set()
    fx_names = {o.name for o in fx_coll.all_objects} if fx_coll else set()
    vio = fc.hex_lin("#A020F0")
    for o in objs:
        if len(o.material_slots) > 4:
            over.append((o.name, len(o.material_slots)))
        for s in o.material_slots:
            m = s.material
            if m is None:
                continue
            mats.add(m.name)
            bad = [n.type for n in m.node_tree.nodes if n.type not in ALLOWED_NODES] if m.node_tree else []
            if bad:
                proc.append((m.name, bad))
            b = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None) if m.node_tree else None
            col = tuple(b.inputs["Base Color"].default_value)[:3] if b else (0, 0, 0)
            is_violet = "violet" in m.name.lower() or sum(abs(a - c) for a, c in zip(col, vio[:3])) < 0.05
            if is_violet and o.name not in fx_names:
                violet.append((o.name, m.name))
    return dict(materials=sorted(mats), over_4_slots=over, procedural_nodes=proc, violet_outside_fx=violet)


def run(ID, C_EXP, C_COL, C_FX, budget, landmark_coll, walk_bounds, walkable_prefixes, pair_with=None,
        allowed_drop=None, walk_mask=None, strict_edges=False):
    """strict_edges=True fails the run if any walkable edge faces a void/hazard with nothing at 0.6 m to stop the player
    (for catwalk spaces; rooms with designed open hazard edges such as canals/trenches keep it False)."""
    bpy.context.view_layer.update()
    exp, col = _meshes(C_EXP), _meshes(C_COL)
    r = {"asset": ID}
    # 1 transforms
    r["scale_not_applied"] = [o.name for o in exp + col if any(abs(s - 1) > 1e-6 for s in o.scale)]
    r["negative_scale"] = [o.name for o in exp + col if any(s < 0 for s in o.scale)]
    # rotation must be applied on single-user meshes; instances (shared mesh) and parents keep object rotation
    rotated = lambda o: any(abs(a) > 1e-6 for a in o.rotation_euler)
    r["rotation_not_applied"] = [o.name for o in exp + col if rotated(o) and o.data.users == 1 and not o.children]
    r["instanced_rotations"] = sum(1 for o in exp + col if rotated(o))
    # 2 geometry
    g_rows, g_fail = check_geometry(exp)
    c_rows, c_fail = check_geometry(col, closed_required=True)
    r["geometry_fail_visual"] = g_fail
    r["geometry_fail_collision"] = c_fail
    r["open_visual_meshes"] = [x["mesh"] for x in g_rows if x["boundary_edges"]]
    r["colonly_suffix_missing"] = [o.name for o in col if not o.name.endswith("-colonly")]
    r["collision_on_decorative"] = [o.name for o in exp if o.name.endswith("colonly")]
    # 3 grid / seams
    r["off_grid_modules"] = [(o.name, tuple(round(v, 4) for v in o.location[:2])) for o in exp
                             if o.data.name.startswith(STRUCTURAL)
                             and not (_on_grid(o.location.x) and _on_grid(o.location.y))]
    r["seams"] = wall_and_floor_seams(exp)
    # 4 walk test
    # water surfaces are not ceilings (you can wade under them); everything else visible counts
    ceiling_objs = [o for o in exp if not all(s.material and s.material.name == "M_Water" for s in o.material_slots)]
    r["walk"] = walk_test(col, ceiling_objs, walk_bounds, walkable_prefixes, allowed_drop=allowed_drop, mask=walk_mask)
    # 5 tris
    per = {}
    for c in [C_EXP] + list(C_EXP.children) + [C_COL] + ([C_FX] if C_FX else []):
        _, u, i = fc.tri_report([c])
        per[c.name] = dict(unique=u, instanced=i)
    _, u_all, i_all = fc.tri_report([C_EXP])
    rows, _, _ = fc.tri_report([C_EXP])
    top = {}
    for _, on, mn, t in rows:
        top.setdefault(mn, [0, 0])
        top[mn][0] = t
        top[mn][1] += 1
    r["tris"] = dict(per_collection=per, export_unique=u_all, export_instanced=i_all, budget=budget,
                     within_budget=i_all <= budget,
                     heaviest_meshes=sorted(([k, v[0], v[1]] for k, v in top.items()), key=lambda z: -z[1] * z[2])[:12])
    # 6 materials
    r["materials"] = check_materials(exp, C_FX)
    # 7 landmarks
    lm = {o.name: [round(v, 4) for v in o.matrix_world.translation] for o in landmark_coll.objects}
    r["landmarks"] = lm
    with open(os.path.join(fc.RENDER_DIR, f"{ID}_landmarks.json"), "w") as fh:
        json.dump(lm, fh, indent=2)
    if pair_with and os.path.exists(pair_with):
        with open(pair_with, encoding="utf-8-sig") as fh:
            other = json.load(fh)
        cmp_ = {}
        for k in sorted(set(lm) & set(other)):
            a, b = lm[k], other[k]
            d = round(max(abs(p - q) for p, q in zip(a, b)), 4)
            cmp_[k] = dict(this=a, pair=b, delta_m=d, ok=d <= 0.01)
        r["landmark_pair"] = cmp_
        r["landmark_pair_missing_here"] = sorted(set(other) - set(lm))
        r["landmark_only_here"] = sorted(set(lm) - set(other))
        r["landmark_pair_ok"] = all(v["ok"] for v in cmp_.values()) and not r["landmark_pair_missing_here"]
    # summary
    w = r["walk"]
    r["pass"] = not any([r["scale_not_applied"], r["negative_scale"], r["rotation_not_applied"], g_fail, c_fail,
                         r["colonly_suffix_missing"], r["off_grid_modules"], r["seams"]["wall_seam_failures"],
                         r["seams"].get("floor_gap_m2", 0) > 1e-4, w["holes"], w["slopes_over_35"], w["drops_unguarded"],
                         w["ceilings_under_2_5"], not r["tris"]["within_budget"],
                         r["materials"]["over_4_slots"], r["materials"]["procedural_nodes"],
                         r["materials"]["violet_outside_fx"], not r.get("landmark_pair_ok", True),
                         strict_edges and w["edges_to_void_open"]])
    return r


def export_and_verify(C_EXP, C_COL, glb):
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action="DESELECT")
    objs = [o for o in list(C_EXP.all_objects) + list(C_COL.all_objects)]
    for o in objs:
        o.hide_set(False)
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    expected = {o.name: tuple(o.matrix_world.translation) for o in objs}
    bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB", use_selection=True, export_extras=True,
                              export_yup=True, export_apply=True, export_cameras=False, export_lights=False)
    size = os.path.getsize(glb)
    # re-import into a clean scene
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=glb)
    bpy.context.view_layer.update()
    got = {o.name: tuple(o.matrix_world.translation) for o in bpy.data.objects}
    missing = sorted(set(expected) - set(got))
    moved = [(n, [round(v, 4) for v in expected[n]], [round(v, 4) for v in got[n]]) for n in expected
             if n in got and max(abs(a - b) for a, b in zip(expected[n], got[n])) > 1e-3]
    col_exp = sum(1 for n in expected if n.endswith("-colonly"))
    col_got = sum(1 for n in got if n.endswith("-colonly"))
    return dict(glb_bytes=size, exported_objects=len(expected), reimported_objects=len(got),
                missing_after_reimport=missing, origin_mismatch=moved,
                colonly_exported=col_exp, colonly_reimported=col_got,
                ok=not missing and not moved and col_exp == col_got)
