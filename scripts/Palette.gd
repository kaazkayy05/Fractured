class_name Palette
## Project palette (Block 0) + tiny mesh helpers for placeholder geometry built in code.

const CYAN := Color(0.0, 0.898, 1.0)
const FOREST := Color(0.180, 0.353, 0.235)
const CHARCOAL := Color(0.227, 0.239, 0.251)
const AMBER := Color(0.902, 0.494, 0.133)
const VIOLET := Color(0.627, 0.125, 0.941)      # only fractures / reality shifts / bursts
const SILVER := Color(0.788, 0.808, 0.827)
const BARK := Color(0.420, 0.290, 0.196)
const VCONCRETE := Color(0.541, 0.561, 0.478)
const NAVY := Color(0.122, 0.165, 0.267)
const LANTERN := Color(1.0, 0.690, 0.290)


static func bl(x: float, y: float, z: float) -> Vector3:
	## Blender (Z-up, metres) landmark -> Godot (Y-up). glTF export maps (x, y, z) -> (x, z, -y).
	return Vector3(x, z, -y)


static func mat(c: Color, emission := 0.0, alpha := 1.0) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = Color(c.r, c.g, c.b, alpha)
	m.roughness = 0.6
	if emission > 0.0:
		m.emission_enabled = true
		m.emission = c
		m.emission_energy_multiplier = emission
	if alpha < 1.0:
		m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	return m


static func box(size: Vector3, c: Color, emission := 0.0, alpha := 1.0) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = size
	mi.mesh = bm
	mi.material_override = mat(c, emission, alpha)
	return mi


static func cyl(r: float, h: float, c: Color, emission := 0.0, sides := 8, alpha := 1.0) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	var cm := CylinderMesh.new()
	cm.top_radius = r
	cm.bottom_radius = r
	cm.height = h
	cm.radial_segments = sides
	cm.rings = 1
	mi.mesh = cm
	mi.material_override = mat(c, emission, alpha)
	return mi


static func capsule(r: float, h: float, c: Color, emission := 0.0, alpha := 1.0) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	var cm := CapsuleMesh.new()
	cm.radius = r
	cm.height = h
	cm.radial_segments = 10
	cm.rings = 3
	mi.mesh = cm
	mi.material_override = mat(c, emission, alpha)
	return mi


static func crystal(h: float, c: Color, emission := 2.5) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	var cm := CylinderMesh.new()
	cm.top_radius = 0.0
	cm.bottom_radius = h * 0.3
	cm.height = h
	cm.radial_segments = 6
	cm.rings = 1
	mi.mesh = cm
	mi.material_override = mat(c, emission)
	return mi
