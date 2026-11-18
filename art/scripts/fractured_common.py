"""Shared helpers for Fractured asset scripts (Blender 5.x, run with blender -b -P).

Conventions (Block 0): metric, 1 BU = 1 m, Z-up authoring, fronts face -Y,
origins bottom-center unless stated, meshes built directly (no ops) so
scale/rotation stay clean.
"""
import bpy
import bmesh
import math
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SOURCE_DIR = os.path.join(ROOT, "art", "source")
RENDER_DIR = os.path.join(ROOT, "art", "renders")
EXPORT_DIR = os.path.join(ROOT, "export")
MATLIB_PATH = os.path.join(SOURCE_DIR, "Fractured_A9_MaterialLibrary.blend")
for _d in (SOURCE_DIR, RENDER_DIR, EXPORT_DIR):
    os.makedirs(_d, exist_ok=True)

PALETTE = {
    "cyan": "#00E5FF", "forest": "#2E5A3C", "charcoal": "#3A3D40",
    "amber": "#E67E22", "violet": "#A020F0", "silver": "#C9CED3",
    "bark": "#6B4A32", "veyra_concrete": "#8A8F7A",
}

# Shared export material set (Block 0). Violet deliberately absent.
SHARED_MATERIALS = {
    "M_NovaSilver":    dict(color="#C9CED3", metallic=0.35, roughness=0.40),
    "M_NovaGlass":     dict(color="#BFE6EE", metallic=0.0, roughness=0.05, alpha=0.25),
    "M_CyanEmissive":  dict(color="#00E5FF", metallic=0.0, roughness=0.40, emission=4.0),
    "M_Charcoal":      dict(color="#3A3D40", metallic=0.10, roughness=0.75),
    "M_AmberWarning":  dict(color="#E67E22", metallic=0.0, roughness=0.60),
    "M_Bark":          dict(color="#6B4A32", metallic=0.0, roughness=0.85),
    "M_Moss":          dict(color="#2E5A3C", metallic=0.0, roughness=0.85),
    "M_VeyraConcrete": dict(color="#8A8F7A", metallic=0.0, roughness=0.85),
    # Water is the one non-glass alpha material: V2 requires rails to read through the flood (Block 0 exception).
    "M_Water":         dict(color="#2F6A73", metallic=0.0, roughness=0.35, alpha=0.7),
    "M_Cloth":         dict(color="#1F2A44", metallic=0.0, roughness=0.85),
    # Warm lantern light for Veyra habitation (V2/V3); amber stays reserved for warnings.
    "M_LanternWarm":   dict(color="#FFB04A", metallic=0.0, roughness=0.5, emission=3.0),
}


# ---------------------------------------------------------------- colour
def _s2l(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hex_lin(h, a=1.0):
    h = h.lstrip("#")
    return tuple(_s2l(int(h[i:i + 2], 16) / 255.0) for i in (0, 2, 4)) + (a,)


# ---------------------------------------------------------------- scene
def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    sc.view_settings.view_transform = "Standard"
    if sc.world is None:
        sc.world = bpy.data.worlds.new("World")
    return sc


def collection(name, parent=None):
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    parent = parent or bpy.context.scene.collection
    if c.name not in parent.children:
        parent.children.link(c)
    return c


# ---------------------------------------------------------------- materials
def _bsdf(mat):
    try:
        mat.use_nodes = True
    except Exception:
        pass
    nt = mat.node_tree
    bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        nt.nodes.clear()
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        out.location = (300, 0)
        nt.links.new(bsdf.outputs[0], out.inputs[0])
    return bsdf


def make_material(name, color, metallic=0.0, roughness=0.6, emission=0.0, alpha=1.0):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    bsdf = _bsdf(mat)
    rgba = hex_lin(color)
    bsdf.inputs["Base Color"].default_value = rgba
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if emission:
        bsdf.inputs["Emission Color"].default_value = rgba
        bsdf.inputs["Emission Strength"].default_value = emission
    if alpha < 1.0:
        bsdf.inputs["Alpha"].default_value = alpha
        for attr, val in (("surface_render_method", "BLENDED"), ("blend_method", "BLEND")):
            try:
                setattr(mat, attr, val)
            except Exception:
                pass
    # Viewport/Workbench display colour mirrors the export colour.
    mat.diffuse_color = rgba[:3] + (alpha,)
    mat.metallic = metallic
    mat.roughness = roughness
    mat["fractured_hex"] = color
    return mat


def refresh_shared_materials(names):
    """Replace existing copies of shared materials with the current A9 versions (remaps all users)."""
    old = {}
    for n in names:
        m = bpy.data.materials.get(n)
        if m:
            m.name = n + "__stale"
            old[n] = m
    new = append_shared_materials(names)
    for n, m in old.items():
        m.user_remap(new[n])
        bpy.data.materials.remove(m)
    return new


def append_shared_materials(names=None):
    """Append shared materials from the A9 library (the material source of truth)."""
    names = list(names or SHARED_MATERIALS.keys())
    missing = [n for n in names if n not in bpy.data.materials]
    if missing:
        with bpy.data.libraries.load(MATLIB_PATH, link=False) as (src, dst):
            dst.materials = [n for n in src.materials if n in missing]
    out = {}
    for n in names:
        m = bpy.data.materials[n]
        try:
            m.asset_clear()
        except Exception:
            pass
        out[n] = m
    return out


# ---------------------------------------------------------------- geometry data
BOX_FACES = ("bottom", "top", "front", "right", "back", "left")


def box_data(sx, sy, sz, cx=0.0, cy=0.0, z0=0.0, skip=()):
    x0, x1, y0, y1, z1 = cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2, z0 + sz
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
         (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    f = [face for face, n in zip(f, BOX_FACES) if n not in skip]
    return v, f


def box_minmax(x0, x1, y0, y1, z0, z1, skip=()):
    return box_data(x1 - x0, y1 - y0, z1 - z0, (x0 + x1) / 2, (y0 + y1) / 2, z0, skip)


def sheared_box(x0, x1, ya, za, yb, zb, h):
    """Box whose bottom edge runs from (ya,za) to (yb,zb); height h. For sloped rails/ramps."""
    v = [(x0, ya, za), (x1, ya, za), (x1, yb, zb), (x0, yb, zb),
         (x0, ya, za + h), (x1, ya, za + h), (x1, yb, zb + h), (x0, yb, zb + h)]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    return v, f


def wedge_data(x0, x1, y0, y1, height):
    """Ramp rising from z=0 at y0 to `height` at y1 (walk-up toward +Y)."""
    v = [(x0, y0, 0), (x1, y0, 0), (x1, y1, 0), (x0, y1, 0), (x0, y1, height), (x1, y1, height)]
    f = [(0, 3, 2, 1), (0, 1, 5, 4), (2, 3, 4, 5), (1, 2, 5), (0, 4, 3)]
    return v, f


def lathe(profile, segs, closed=False, angle_offset=0.0, cx=0.0, cy=0.0, z0=0.0):
    """Revolve a (radius, z) profile around Z. radius 0 -> single pole vertex (tri fan)."""
    verts, rings = [], []
    for r, z in profile:
        if r <= 1e-9:
            rings.append([len(verts)])
            verts.append((cx, cy, z0 + z))
        else:
            idx = []
            for j in range(segs):
                a = angle_offset + 2 * math.pi * j / segs
                idx.append(len(verts))
                verts.append((cx + r * math.cos(a), cy + r * math.sin(a), z0 + z))
            rings.append(idx)
    pairs = list(zip(rings[:-1], rings[1:]))
    if closed:
        pairs.append((rings[-1], rings[0]))
    faces = []
    for a, b in pairs:
        for j in range(segs):
            k = (j + 1) % segs
            if len(a) == 1 and len(b) == 1:
                continue
            if len(a) == 1:
                faces.append((a[0], b[k], b[j]))
            elif len(b) == 1:
                faces.append((a[j], a[k], b[0]))
            else:
                faces.append((a[j], a[k], b[k], b[j]))
    return verts, faces


def cylinder_data(r, h, segs, **kw):
    return lathe([(0, 0), (r, 0), (r, h), (0, h)], segs, **kw)


def capsule_data(r=0.4, h=1.8, segs=16, rings=4):
    prof = []
    for i in range(rings + 1):
        a = -math.pi / 2 + (math.pi / 2) * i / rings
        prof.append((r * math.cos(a), r + r * math.sin(a)))
    for i in range(rings + 1):
        a = (math.pi / 2) * i / rings
        prof.append((r * math.cos(a), h - r + r * math.sin(a)))
    prof[0] = (0, 0)
    prof[-1] = (0, h)
    return lathe(prof, segs)


def stair_data(width, treads, tread, rise, back=True, bottom=True):
    """Solid straight stair, origin bottom-centre of first riser, climbing toward +Y.
    Risers/treads are quads; each side is a triangle fan from the back-bottom
    corner (manifold, no T-junctions). Top tread ends at z = treads*rise; the
    final riser is supplied by the landing/slab it meets."""
    n = treads
    run = n * tread
    v, f = [], []
    x0, x1 = -width / 2, width / 2

    def add(p):
        v.append(p)
        return len(v) - 1

    for i in range(n):
        ya, yb, zt, zprev = i * tread, (i + 1) * tread, (i + 1) * rise, i * rise
        f.append((add((x0, ya, zprev)), add((x1, ya, zprev)), add((x1, ya, zt)), add((x0, ya, zt))))
        f.append((add((x0, ya, zt)), add((x1, ya, zt)), add((x1, yb, zt)), add((x0, yb, zt))))
    outline = [(0.0, 0.0)]
    for i in range(n):
        outline += [(i * tread, (i + 1) * rise), ((i + 1) * tread, (i + 1) * rise)]
    for x in (x0, x1):
        pivot = add((x, run, 0.0))
        pts = [add((x, y, z)) for y, z in outline]
        for a, b in zip(pts[:-1], pts[1:]):
            f.append((pivot, a, b) if x == x0 else (pivot, b, a))
    if back:
        a, b, c, d = add((x0, run, 0)), add((x1, run, 0)), add((x1, run, n * rise)), add((x0, run, n * rise))
        f.append((b, a, d, c))
    if bottom:
        a, b, c, d = add((x0, 0, 0)), add((x1, 0, 0)), add((x1, run, 0)), add((x0, run, 0))
        f.append((a, d, c, b))
    return v, f


def stair_mats(treads, total_faces, tread_mat=0, other_mat=1):
    m = [other_mat, tread_mat] * treads
    return m + [other_mat] * (total_faces - len(m))


# ---------------------------------------------------------------- 2D grids / extrusion
FONT = {
    "1": [".X.", "XX.", ".X.", ".X.", "XXX"],
    "2": ["XXX", "..X", "XXX", "X..", "XXX"],
    "3": ["XXX", "..X", "XXX", "..X", "XXX"],
    "E": ["XXX", "X..", "XX.", "X..", "XXX"],
    "X": ["X.X", "X.X", ".X.", "X.X", "X.X"],
    "I": ["XXX", ".X.", ".X.", ".X.", "XXX"],
    "T": ["XXX", ".X.", ".X.", ".X.", ".X."],
    "S": ["XXX", "X..", "XXX", "..X", "XXX"],
    "L": ["X..", "X..", "X..", "X..", "XXX"],
    "O": ["XXX", "X.X", "X.X", "X.X", "XXX"],
    "A": ["XXX", "X.X", "XXX", "X.X", "X.X"],
    "D": ["XX.", "X.X", "X.X", "X.X", "XX."],
    "N": ["X..X", "XX.X", "X.XX", "X..X", "X..X"],
    "G": ["XXX", "X..", "X.X", "X.X", "XXX"],
    "R": ["XX.", "X.X", "XX.", "X.X", "X.X"],
    ">": ["..X..", "..XX.", "XXXXX", "..XX.", "..X.."],
    "<": ["..X..", ".XX..", "XXXXX", ".XX..", "..X.."],
    " ": ["..", "..", "..", "..", ".."],
}


def grid2d(xs, zs, filled, matfn=lambda i, j: 0):
    """Quads on a rectilinear grid in the (x, z) plane, CCW seen from -Y. Shared corner verts."""
    idx, pts, faces, mats = {}, [], [], []

    def vid(i, j):
        if (i, j) not in idx:
            idx[(i, j)] = len(pts)
            pts.append((xs[i], zs[j]))
        return idx[(i, j)]

    for i in range(len(xs) - 1):
        for j in range(len(zs) - 1):
            if filled(i, j):
                faces.append((vid(i, j), vid(i + 1, j), vid(i + 1, j + 1), vid(i, j + 1)))
                mats.append(matfn(i, j))
    return pts, faces, mats


def glyphs(text, cell, x_center=0.0, z0=0.0, gap=1):
    """Block-letter bitmap text -> grid2d data (centred on x_center, bottom at z0)."""
    rows = 5
    cols = []
    for k, ch in enumerate(text):
        g = FONT[ch]
        if k:
            cols += ["." * rows] * gap
        for c in range(len(g[0])):
            cols.append("".join(g[r][c] for r in range(rows)))
    w = len(cols) * cell
    xs = [x_center - w / 2 + i * cell for i in range(len(cols) + 1)]
    zs = [z0 + j * cell for j in range(rows + 1)]
    return grid2d(xs, zs, lambda i, j: cols[i][rows - 1 - j] == "X")


def extrude2d(pts, faces, mats, t, y0=0.0, front=True, back=True, side_mat=None):
    """Extrude (x,z) faces along +Y from y0 to y0+t. Front faces -Y. Returns (verts, faces, mats)."""
    n = len(pts)
    V = [(x, y0, z) for x, z in pts] + [(x, y0 + t, z) for x, z in pts]
    F, M, edges = [], [], {}
    for f, m in zip(faces, mats):
        f = tuple(f)
        if front:
            F.append(f)
            M.append(m)
        if back:
            F.append(tuple(i + n for i in reversed(f)))
            M.append(m)
        for a, b in zip(f, f[1:] + f[:1]):
            edges[(a, b)] = m
    for (a, b), m in edges.items():
        if (b, a) in edges:
            continue
        if callable(side_mat):
            sm = side_mat(pts[a], pts[b], m)
        else:
            sm = m if side_mat is None else side_mat
        F.append((a, a + n, b + n, b))
        M.append(sm)
    return V, F, M


def prism(pts, z0, z1, side_mats=None, cap_mat=0, top_mat=None):
    """Extrude a convex CCW (x,y) polygon along Z; caps are triangle fans (no n-gons).
    z1 may be a callable(x, y) for a tilted/uneven top."""
    n = len(pts)
    ztop = z1 if callable(z1) else (lambda x, y: z1)
    V = [(x, y, z0) for x, y in pts] + [(x, y, ztop(x, y)) for x, y in pts]
    F, M = [], []
    for i in range(1, n - 1):
        F.append((0, i + 1, i))
        M.append(cap_mat)
        F.append((n, n + i, n + i + 1))
        M.append(cap_mat if top_mat is None else top_mat)
    for i in range(n):
        j = (i + 1) % n
        F.append((i, j, j + n, i + n))
        M.append(side_mats[i] if side_mats else cap_mat)
    return V, F, M


def slab_grid(xs, ys, zb, ztop, matfn=lambda i, j: 0, side_mat=0, bottom=True):
    """Closed slab on an XY grid: bottom at zb (number or callable(x, y)), top height ztop(x, y). All quads."""
    V, F, M, idx = [], [], [], {}
    zbf = zb if callable(zb) else (lambda x, y: zb)

    def vid(i, j, top):
        k = (i, j, top)
        if k not in idx:
            x, y = xs[i], ys[j]
            idx[k] = len(V)
            V.append((x, y, ztop(x, y) if top else zbf(x, y)))
        return idx[k]

    nx, ny = len(xs) - 1, len(ys) - 1
    for i in range(nx):
        for j in range(ny):
            F.append((vid(i, j, 1), vid(i + 1, j, 1), vid(i + 1, j + 1, 1), vid(i, j + 1, 1)))
            M.append(matfn(i, j))
            if bottom:
                F.append((vid(i, j, 0), vid(i, j + 1, 0), vid(i + 1, j + 1, 0), vid(i + 1, j, 0)))
                M.append(side_mat)
    ring = [(i, 0) for i in range(nx)] + [(nx, j) for j in range(ny)] + \
           [(i, ny) for i in range(nx, 0, -1)] + [(0, j) for j in range(ny, 0, -1)]
    for k, (i, j) in enumerate(ring):
        i2, j2 = ring[(k + 1) % len(ring)]
        F.append((vid(i, j, 0), vid(i2, j2, 0), vid(i2, j2, 1), vid(i, j, 1)))
        M.append(side_mat)
    return V, F, M


def xform(data, rot_z=0.0, rot_x=0.0, offset=(0, 0, 0), rot_y=0.0):
    """Rotate (deg; applied X, then Y, then Z) then translate raw (verts, faces[, mats]) data."""
    from mathutils import Matrix, Vector
    R = Matrix.Rotation(math.radians(rot_z), 3, "Z") @ Matrix.Rotation(math.radians(rot_y), 3, "Y") @ \
        Matrix.Rotation(math.radians(rot_x), 3, "X")
    v = [tuple(R @ Vector(p) + Vector(offset)) for p in data[0]]
    return (v,) + tuple(data[1:])


def mparts(*parts):
    """[(verts, faces, mats) or (verts, faces, mat_int)] -> (verts, faces, mats)"""
    out = []
    for p in parts:
        if len(p) == 3 and isinstance(p[2], int):
            out.append((p[0], p[1], [p[2]] * len(p[1])))
        else:
            out.append(p)
    V, F, M = [], [], []
    for pv, pf, pm in out:
        off = len(V)
        V.extend(pv)
        F.extend(tuple(i + off for i in f) for f in pf)
        M.extend(pm)
    return V, F, M


def look_at(o, target):
    from mathutils import Vector
    d = Vector(target) - o.location
    o.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def bake_unique_rotations(objs):
    """Apply rotation into mesh data for single-user meshes without children (Block Z #1)."""
    baked = []
    for o in objs:
        if o.type != "MESH" or o.data.users > 1 or o.children:
            continue
        if any(abs(a) > 1e-6 for a in o.rotation_euler):
            o.data.transform(o.rotation_euler.to_matrix().to_4x4())
            o.rotation_euler = (0, 0, 0)
            baked.append(o.name)
    return baked


def merge(*parts):
    verts, faces = [], []
    for pv, pf in parts:
        off = len(verts)
        verts.extend(pv)
        faces.extend(tuple(i + off for i in face) for face in pf)
    return verts, faces


def with_material_index(parts_with_idx):
    """[(verts, faces, mat_index)] -> verts, faces, face_mat_indices"""
    verts, faces, mats = [], [], []
    for pv, pf, mi in parts_with_idx:
        off = len(verts)
        verts.extend(pv)
        faces.extend(tuple(i + off for i in face) for face in pf)
        mats.extend([mi] * len(pf))
    return verts, faces, mats


# ---------------------------------------------------------------- objects
def build_mesh(name, data, mats=None, face_mats=None, recalc=True, weld=True):
    """weld=False keeps separate shells separate (e.g. touching collision hulls must stay manifold)."""
    v, f = data
    me = bpy.data.meshes.new(name)
    me.from_pydata(v, [], f)
    me.validate()
    bm = bmesh.new()
    bm.from_mesh(me)
    if weld:
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.001)
    if recalc:
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    for m in mats or []:
        me.materials.append(m)
    if face_mats:
        # remove_doubles keeps face order
        for poly, mi in zip(me.polygons, face_mats):
            poly.material_index = mi
    me.update()
    return me


def obj(name, mesh, coll, loc=(0, 0, 0), rot_z_deg=0.0):
    o = bpy.data.objects.new(name, mesh)
    coll.objects.link(o)
    o.location = loc
    o.rotation_euler = (0, 0, math.radians(rot_z_deg))
    return o


def empty(name, loc, coll, size=0.5, kind="PLAIN_AXES"):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = kind
    e.empty_display_size = size
    e.location = loc
    coll.objects.link(e)
    return e


def ref_player(coll, loc=(0, 0, 0)):
    mat = bpy.data.materials.get("M_REF_Player") or make_material("M_REF_Player", "#FF3B7F", roughness=0.8)
    o = obj("REF_Player", build_mesh("REF_Player", capsule_data(), [mat]), coll, loc)
    o["note"] = "1.8 m player reference, capsule r=0.4. Presentation only."
    o.hide_render = True
    o.hide_set(True)
    return o


def tri_count(o):
    if o.type != "MESH":
        return 0
    me = o.data
    me.calc_loop_triangles()
    return len(me.loop_triangles)


def tri_report(colls):
    """Return (rows, unique_total, instanced_total) for mesh objects in collections."""
    rows, seen = [], set()
    uniq = inst = 0
    for c in colls:
        for o in c.all_objects:
            if o.type != "MESH":
                continue
            t = tri_count(o)
            inst += t
            if o.data.name not in seen:
                seen.add(o.data.name)
                uniq += t
            rows.append((c.name, o.name, o.data.name, t))
    return rows, uniq, inst


def render(path, engine="BLENDER_WORKBENCH", res=(1920, 1080)):
    sc = bpy.context.scene
    sc.render.engine = engine
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.filepath = path
    sc.render.image_settings.file_format = "PNG"
    bpy.ops.render.render(write_still=True)
    return path


def setup_workbench(light="STUDIO", world_hex="#20242A"):
    sc = bpy.context.scene
    sh = sc.display.shading
    sh.light = light
    sh.color_type = "MATERIAL"
    sh.show_shadows = light != "FLAT"
    sh.show_cavity = light != "FLAT"
    try:
        sh.cavity_type = "WORLD"
    except Exception:
        pass
    sc.world.color = hex_lin(world_hex)[:3]
    sc.display.render_aa = "8"


def save(path):
    bpy.ops.wm.save_as_mainfile(filepath=path, compress=True)
