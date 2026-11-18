class_name Hazard
extends Node3D
## Damage zone powered by machinery Structures. Shuts off once every source Structure is broken.

var radius := 2.0
var height := 3.0
var dps := 20.0
var sources: Array = []
var active := true
var _vis: MeshInstance3D
var _t := 0.0


func _ready() -> void:
	_vis = Palette.cyl(radius, height, Palette.CYAN, 2.0, 16, 0.25)
	_vis.position.y = height * 0.5
	add_child(_vis)
	for s in sources:
		(s as Structure).collapsed.connect(func(_x): _check())


func _check() -> void:
	for s in sources:
		if not (s as Structure).broken:
			return
	active = false
	_vis.visible = false


func _physics_process(delta: float) -> void:
	if not active:
		return
	_t += delta
	_vis.scale = Vector3.ONE * (1.0 + 0.04 * sin(_t * 30.0))
	var p := get_tree().get_first_node_in_group("player") as Player
	if p == null:
		return
	var d := p.global_position - global_position
	if Vector2(d.x, d.z).length() < radius and d.y > -0.5 and d.y < height:
		p.take_damage(dps * delta, null, true)
