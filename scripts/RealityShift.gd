class_name RealityShift
extends Node
## RealityShift.gd — COOLDOWN (Hali). [Q] switches Nova <-> Veyra in place with a 3 s cooldown, keeping
## momentum. If the destination is blocked the player moves to the nearest safe spot (or the shift is undone).
## Shifting at 60+ instability grants +10 Fracture Energy.
## Writes: Player (position), FractureEnergy (bonus), RealityManager (toggle -> +5 instability).

const COOLDOWN := 3.0
const HIGH_INSTABILITY := 60.0
const OFFSETS: Array[Vector3] = [
	Vector3.ZERO,
	Vector3(0.75, 0, 0), Vector3(-0.75, 0, 0), Vector3(0, 0, 0.75), Vector3(0, 0, -0.75),
	Vector3(1.5, 0, 0), Vector3(-1.5, 0, 0), Vector3(0, 0, 1.5), Vector3(0, 0, -1.5),
	Vector3(2.25, 0, 0), Vector3(-2.25, 0, 0), Vector3(0, 0, 2.25), Vector3(0, 0, -2.25),
	Vector3(0, 0.6, 0), Vector3(0, 1.2, 0),
]

var cooldown_left := 0.0
var in_progress := false
var locked := false
var lock_reason := ""
var player: Player


func _ready() -> void:
	player = get_parent() as Player


func _process(delta: float) -> void:
	cooldown_left = maxf(0.0, cooldown_left - delta)


func ready_ratio() -> float:
	return 1.0 - cooldown_left / COOLDOWN


func try_shift() -> void:
	if locked:
		player.toast(lock_reason if lock_reason != "" else "Reality is locked here.")
		return
	if cooldown_left > 0.0 or in_progress:
		player.toast("Reality Shift recharging: %.1fs" % cooldown_left, 1.0)
		return
	in_progress = true
	var high := InstabilityManager.value >= HIGH_INSTABILITY
	var old := RealityManager.active
	RealityManager.set_reality(1 - old)
	# collision shapes toggle deferred; wait for physics to see the new reality
	await get_tree().physics_frame
	await get_tree().physics_frame
	var safe := find_safe_position(player.global_position)
	if safe == Vector3.INF:
		RealityManager.set_reality(old)
		in_progress = false
		player.toast("No safe position in %s." % RealityManager.reality_name(1 - old))
		return
	player.global_position = safe
	in_progress = false
	cooldown_left = COOLDOWN
	RealityManager.shifted.emit(RealityManager.active)   # InstabilityManager: +5
	player.echo.reset_history()
	if high:
		player.fracture.add(10.0)
	player.on_reality_shifted()
	player.toast("Shifted to %s.%s" % [RealityManager.reality_name(), "  +10 Fracture Energy (high instability)" if high else ""], 1.5)


func find_safe_position(origin: Vector3) -> Vector3:
	var cap := CapsuleShape3D.new()
	cap.radius = 0.34
	cap.height = 1.8
	var q := PhysicsShapeQueryParameters3D.new()
	q.shape = cap
	q.collision_mask = 1
	q.exclude = [player.get_rid()]
	var space := player.get_world_3d().direct_space_state
	for off in OFFSETS:
		var c := origin + off
		q.transform = Transform3D(Basis(), c + Vector3(0, 0.92, 0))
		if space.intersect_shape(q, 1).is_empty():
			return c
	return Vector3.INF
