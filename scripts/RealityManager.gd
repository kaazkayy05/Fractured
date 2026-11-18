extends Node
## RealityManager.gd — ACTIVE REALITY (autoload).
## Holds which reality is active (Nova / Veyra) and shows/hides every registered reality layer.
## Read by: RealityShift, Structure, InstabilityManager, EnemyAI (per the architecture diagram).

signal reality_changed(reality: int)
signal shifted(reality: int)     # a player-caused Reality Shift (not scripted scene changes)

enum Reality { NOVA, VEYRA }

var active: int = Reality.NOVA
var merged := false              # Scene 8: both realities exist at once
var _layers: Array = []          # [{ "node": Node3D, "reality": int }]


func reset() -> void:
	_layers.clear()
	merged = false
	active = Reality.NOVA


func is_nova() -> bool:
	return active == Reality.NOVA


func reality_name(r: int = -1) -> String:
	if merged:
		return "CONVERGED"
	return "NOVA" if (active if r < 0 else r) == Reality.NOVA else "VEYRA"


func set_reality(r: int) -> void:
	active = r
	_apply()
	reality_changed.emit(active)


func toggle(from_shift := false) -> void:
	set_reality(Reality.VEYRA if active == Reality.NOVA else Reality.NOVA)
	if from_shift:
		shifted.emit(active)


func set_merged(on: bool) -> void:
	merged = on
	_apply()
	reality_changed.emit(active)


func register_layer(node: Node3D, reality: int) -> void:
	_layers.append({"node": node, "reality": reality})
	set_node_active(node, merged or reality == active)


func present(reality: int) -> bool:
	## true if something that belongs to `reality` (-1 = both) exists right now
	return reality < 0 or merged or reality == active


func _apply() -> void:
	for layer in _layers:
		if is_instance_valid(layer.node):
			set_node_active(layer.node, merged or layer.reality == active)


static func set_node_active(node: Node3D, on: bool) -> void:
	node.visible = on
	for cs in node.find_children("*", "CollisionShape3D", true, false):
		if cs.is_in_group("force_disabled"):
			continue
		cs.set_deferred("disabled", not on)
