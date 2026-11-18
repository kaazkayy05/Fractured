class_name Interactable
extends Node3D
## Anything the player uses with [E]: consoles, power nodes, clues, convergence nodes, NPCs.
## hold_time > 0 means hold [E].

signal used(i: Interactable)

var prompt := "Interact"
var radius := 2.4
var hold_time := 0.0
var reality := -1
var enabled := true
var one_shot := true
var show_marker := true
var marker_height := 2.0
var callback := Callable()
var _marker: MeshInstance3D
var _t := 0.0


func _ready() -> void:
	add_to_group("interactable")
	_marker = Palette.crystal(0.35, Palette.CYAN, 3.0)
	_marker.rotation.x = PI
	_marker.position.y = marker_height
	add_child(_marker)
	RealityManager.reality_changed.connect(_sync)
	_sync(0)


func _sync(_r: int) -> void:
	visible = RealityManager.present(reality)


func can_use() -> bool:
	return enabled and RealityManager.present(reality)


func _process(delta: float) -> void:
	_t += delta
	_marker.visible = show_marker and enabled
	_marker.position.y = marker_height + sin(_t * 3.0) * 0.1
	_marker.rotation.y = _t


func use() -> void:
	if not can_use():
		return
	if one_shot:
		enabled = false
	used.emit(self)
	if callback.is_valid():
		callback.call(self)
