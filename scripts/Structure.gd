class_name Structure
extends StaticBody3D
## Structure.gd — OBJECT STATE (Megan). Stability 0..100; [E] Structural Manipulation within 3 m costs 25.
## At 0 it collapses (opens a path), transforms (moves into a new pose, e.g. a bridge) or, for machinery,
## shuts down linked hazards. Reads RealityManager: it only exists in its reality, and is weaker in Veyra.

signal collapsed(s: Structure)

enum Mode { COLLAPSE, TRANSFORM, MACHINERY }

const MANIPULATE_RANGE := 3.0
const MANIPULATE_DAMAGE := 25.0

var stability := 100.0
var max_stability := 100.0
var reality := -1
var mode := Mode.COLLAPSE
var burst_only := false
var label := "Unstable structure"
var linked: Array = []
var transform_to := Transform3D()
var broken := false
var size := Vector3.ONE
var base_color := Palette.SILVER
var mesh: MeshInstance3D
var shape: CollisionShape3D
var _mat: StandardMaterial3D


static func create(p_size: Vector3, color: Color, p_mode := Mode.COLLAPSE, p_stability := 100.0) -> Structure:
	var s := Structure.new()
	s.size = p_size
	s.base_color = color
	s.mode = p_mode
	s.stability = p_stability
	s.max_stability = 100.0
	return s


func _ready() -> void:
	add_to_group("structure")
	mesh = Palette.box(size, base_color, 0.0)
	_mat = mesh.material_override
	add_child(mesh)
	shape = CollisionShape3D.new()
	var bs := BoxShape3D.new()
	bs.size = size
	shape.shape = bs
	add_child(shape)
	if burst_only:
		_mat.albedo_color = Palette.VIOLET.darkened(0.3)
		_mat.emission_enabled = true
		_mat.emission = Palette.VIOLET
		_mat.emission_energy_multiplier = 1.2
	RealityManager.reality_changed.connect(_sync)
	_sync(0)
	_refresh()


func is_present() -> bool:
	return not broken and RealityManager.present(reality)


func _sync(_r: int) -> void:
	var here := RealityManager.present(reality)
	visible = here and not (broken and mode == Mode.COLLAPSE)
	shape.set_deferred("disabled", not here or (broken and mode == Mode.COLLAPSE))


func prompt() -> String:
	if burst_only:
		return "%s: too dense to move. Needs a Fracture burst [F]" % label
	return "[E] Manipulate %s (stability %d)" % [label, int(stability)]


func manipulate() -> void:
	if burst_only:
		return
	apply_damage(MANIPULATE_DAMAGE)


func apply_damage(amount: float, from_burst := false, delay := 0.0) -> bool:
	if not is_present():
		return false
	if burst_only and not from_burst:
		return false
	if RealityManager.active == RealityManager.Reality.VEYRA and not RealityManager.merged:
		amount *= 1.25
	if burst_only:
		amount = stability          # fracture crystals shatter from a single burst
	stability = maxf(0.0, stability - amount)
	_react(delay)
	return true


func _react(delay: float) -> void:
	## Visual + state reaction, optionally delayed so chain reactions ripple outward.
	if delay > 0.0:
		await get_tree().create_timer(delay).timeout
		if not is_instance_valid(self):
			return
	_refresh()
	_shake()
	if stability <= 0.0 and not broken:
		_break()


func _refresh() -> void:
	if burst_only or broken:
		return
	var t := 1.0 - stability / max_stability
	_mat.albedo_color = base_color.lerp(Palette.AMBER, t * 0.8)
	_mat.emission_enabled = t > 0.0
	_mat.emission = Palette.AMBER
	_mat.emission_energy_multiplier = t * 1.5


func _shake() -> void:
	var tw := create_tween()
	var p := mesh.position
	tw.tween_property(mesh, "position", p + Vector3(0.06, 0, 0.04), 0.04)
	tw.tween_property(mesh, "position", p - Vector3(0.05, 0, 0.03), 0.04)
	tw.tween_property(mesh, "position", p, 0.04)


func _break() -> void:
	broken = true
	match mode:
		Mode.COLLAPSE:
			shape.set_deferred("disabled", true)
			var tw := create_tween()
			tw.set_parallel(true)
			tw.tween_property(mesh, "scale", Vector3(1.1, 0.05, 1.1), 0.5)
			tw.tween_property(mesh, "position", Vector3(0, -size.y * 0.48, 0), 0.5)
			tw.chain().tween_callback(func(): visible = false)
		Mode.TRANSFORM:
			var tw := create_tween()
			tw.tween_property(self, "transform", transform_to, 0.9).set_trans(Tween.TRANS_BOUNCE).set_ease(Tween.EASE_OUT)
			_mat.albedo_color = base_color
			_mat.emission_enabled = false
		Mode.MACHINERY:
			_mat.albedo_color = Palette.CHARCOAL
			_mat.emission_enabled = false
	FX.sphere(get_parent(), global_position, maxf(size.x, size.y) * 0.8, Palette.AMBER, 0.3)
	collapsed.emit(self)


func distance_to_point(p: Vector3) -> float:
	var local := to_local(p)
	var h := size * 0.5
	var c := Vector3(clampf(local.x, -h.x, h.x), clampf(local.y, -h.y, h.y), clampf(local.z, -h.z, h.z))
	return (local - c).length()
