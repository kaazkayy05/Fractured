class_name ChainReaction
extends Node
## ChainReaction.gd — LINKED REACTIONS (Megan). [G] sends a pulse into every unstable structure within 6 m;
## the pulse travels through each structure's linked structures. 10 s cooldown. Every reaction after the
## first adds +10 instability. Writes Structure (damage) and InstabilityManager.

const RADIUS := 6.0
const COOLDOWN := 10.0
const PULSE_DAMAGE := 25.0
const INSTABILITY_PER_EXTRA := 10.0

var cooldown_left := 0.0
var player: Player


func _ready() -> void:
	player = get_parent() as Player


func _process(delta: float) -> void:
	cooldown_left = maxf(0.0, cooldown_left - delta)


func ready_ratio() -> float:
	return 1.0 - cooldown_left / COOLDOWN


func try_pulse() -> bool:
	if cooldown_left > 0.0:
		return false
	var origin := player.global_position + Vector3(0, 1, 0)
	var queue: Array = []
	for s in get_tree().get_nodes_in_group("structure"):
		var st := s as Structure
		if st and st.is_present() and not st.burst_only and st.distance_to_point(origin) <= RADIUS:
			queue.append(st)
	if queue.is_empty():
		player.toast("No unstable structures within 6 m.")
		return false
	cooldown_left = COOLDOWN
	var visited := {}
	var reactions := 0
	while not queue.is_empty():
		var st: Structure = queue.pop_front()
		if visited.has(st) or not is_instance_valid(st) or not st.is_present():
			continue
		visited[st] = true
		if st.apply_damage(PULSE_DAMAGE, false, 0.12 * reactions):
			reactions += 1
		for l in st.linked:
			if not visited.has(l):
				queue.append(l)
	if reactions > 1:
		InstabilityManager.add(INSTABILITY_PER_EXTRA * (reactions - 1))
	FX.ring(player.get_parent(), player.global_position + Vector3(0, 0.15, 0), RADIUS, Palette.CYAN, 0.5)
	player.toast("Chain reaction x%d" % reactions)
	return true
