class_name EchoProjection
extends Node
## Kayla's mechanics, matching playtest/crossing.gd:
## [C] Echo Projection — an echo replays your last 8 s of movement in the current reality (lives 8 s,
##     10 s cooldown, needs 8 s of history). Enemies are drawn to it.
## [V] Rift Recall — teleport to the active echo, or 4 s back along your path if there is none.
##     Costs 25 Fracture Energy, 12 s cooldown; after a recall the echo fades in 4 s.

const REPLAY := 8.0
const LIFETIME := 8.0
const COOLDOWN := 10.0
const RECALL_HISTORY := 4.0
const RECALL_ECHO_LIFETIME := 4.0
const RECALL_COST := 25.0
const RECALL_COOLDOWN := 12.0

var echo: Node3D
var echo_reality := 0
var time_left := 0.0
var cooldown_left := 0.0
var recall_cooldown := 0.0
var player: Player
var _time := 0.0
var _times: Array[float] = []
var _positions: Array[Vector3] = []
var _echo_times: Array[float] = []
var _echo_positions: Array[Vector3] = []
var _echo_start := 0.0
var _echo_elapsed := 0.0
var _seg := 0
var _sample_t := 0.0


func _ready() -> void:
	player = get_parent() as Player
	reset_history()


func reset_history() -> void:
	_times.clear()
	_positions.clear()
	_record()


func _record() -> void:
	_times.append(_time)
	_positions.append(player.global_position if player.is_inside_tree() else Vector3.ZERO)
	var cutoff := _time - REPLAY
	while _times.size() > 1 and _times[1] <= cutoff:
		_times.pop_front()
		_positions.pop_front()


func _has_history(seconds: float) -> bool:
	return _times.size() >= 2 and _times[0] <= _time - seconds


func _physics_process(delta: float) -> void:
	_time += delta
	cooldown_left = maxf(0.0, cooldown_left - delta)
	recall_cooldown = maxf(0.0, recall_cooldown - delta)
	_sample_t += delta
	if _sample_t >= 0.1:
		_sample_t = 0.0
		_record()
	if echo:
		time_left -= delta
		if time_left <= 0.0:
			_clear()
			return
		echo.visible = RealityManager.present(echo_reality)
		_echo_elapsed = minf(_echo_elapsed + delta, REPLAY)
		echo.global_position = _echo_at(_echo_start + _echo_elapsed)


func _echo_at(t: float) -> Vector3:
	while _seg + 1 < _echo_times.size() - 1 and _echo_times[_seg + 1] <= t:
		_seg += 1
	var nxt := mini(_seg + 1, _echo_times.size() - 1)
	var w := inverse_lerp(_echo_times[_seg], _echo_times[nxt], t) if nxt != _seg else 1.0
	return _echo_positions[_seg].lerp(_echo_positions[nxt], clampf(w, 0.0, 1.0))


func active_echo() -> Node3D:
	if echo and RealityManager.present(echo_reality):
		return echo
	return null


func project() -> void:
	if cooldown_left > 0.0:
		player.toast("Your echo isn't ready yet.", 1.0)
		return
	if echo:
		player.toast("An echo is already active.", 1.0)
		return
	if not _has_history(REPLAY):
		player.toast("Echo Projection needs 8 seconds of movement history.", 1.5)
		return
	_echo_times = _times.duplicate()
	_echo_positions = _positions.duplicate()
	_echo_start = _time - REPLAY
	_echo_elapsed = 0.0
	_seg = 0
	echo = Node3D.new()
	echo.name = "Echo"
	var body := Palette.capsule(0.4, 1.8, Color("#DCE6EE"), 0.0, 0.7)
	(body.material_override as StandardMaterial3D).shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	body.position.y = 0.9
	echo.add_child(body)
	var anchor := Palette.box(Vector3(0.3, 0.3, 0.3), Palette.CYAN, 3.0)
	anchor.position.y = 2.1
	echo.add_child(anchor)
	player.get_parent().add_child(echo)
	echo.global_position = _echo_at(_echo_start)
	echo.add_to_group("echo")
	echo_reality = RealityManager.active
	time_left = LIFETIME
	cooldown_left = COOLDOWN
	player.toast("Echo projected: it replays your last 8 seconds. [V] Rift Recall.", 2.0)


func recall() -> void:
	if recall_cooldown > 0.0:
		player.toast("Rift Recall recharging: %.1fs" % recall_cooldown, 1.0)
		return
	if player.reality_shift.in_progress:
		player.toast("Rift Recall is unavailable during Reality Shift.", 1.0)
		return
	if player.fracture.energy < RECALL_COST:
		player.toast("Rift Recall needs 25 Fracture Energy.", 1.5)
		return
	var dest := Vector3.INF
	if echo:
		if not RealityManager.present(echo_reality):
			player.toast("Your echo is in the other reality.", 1.5)
			return
		dest = echo.global_position
	elif _has_history(RECALL_HISTORY):
		var t := _time - RECALL_HISTORY
		for i in range(1, _times.size()):
			if _times[i] >= t:
				var w := inverse_lerp(_times[i - 1], _times[i], t)
				dest = _positions[i - 1].lerp(_positions[i], w)
				break
	if dest == Vector3.INF:
		player.toast("Rift Recall needs 4 seconds of movement history.", 1.5)
		return
	if player.reality_shift.find_safe_position(dest) != dest:
		player.toast("Rift Recall destination is blocked.", 1.5)
		return
	FX.sphere(player.get_parent(), player.global_position + Vector3(0, 1, 0), 1.2, Palette.CYAN, 0.25)
	player.teleport(dest)
	player.fracture.add(-RECALL_COST)
	recall_cooldown = RECALL_COOLDOWN
	reset_history()
	if echo:
		time_left = minf(time_left, RECALL_ECHO_LIFETIME)


func _clear() -> void:
	if echo:
		echo.queue_free()
	echo = null
