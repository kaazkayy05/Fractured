class_name Pickup
extends Area3D
## Fracture-energy shard (violet) or health cell (cyan). Optionally exists in one reality only.

var energy := 0.0
var health := 0.0
var reality := -1
var _vis: MeshInstance3D
var _t := 0.0


static func make_energy(amount := 25.0, p_reality := -1) -> Pickup:
	var p := Pickup.new()
	p.energy = amount
	p.reality = p_reality
	return p


static func make_health(amount := 30.0) -> Pickup:
	var p := Pickup.new()
	p.health = amount
	return p


func _ready() -> void:
	collision_layer = 0
	collision_mask = 2
	var cs := CollisionShape3D.new()
	var sp := SphereShape3D.new()
	sp.radius = 0.7
	cs.shape = sp
	cs.position.y = 0.8
	add_child(cs)
	if energy > 0.0:
		_vis = Palette.crystal(0.7, Palette.VIOLET, 3.0)
	else:
		_vis = Palette.box(Vector3(0.35, 0.35, 0.35), Palette.CYAN, 2.5)
	_vis.position.y = 0.8
	add_child(_vis)
	body_entered.connect(_on_body)
	RealityManager.reality_changed.connect(_sync)
	_sync(0)


func _sync(_r: int) -> void:
	var here := RealityManager.present(reality)
	visible = here
	set_deferred("monitoring", here)


func _process(delta: float) -> void:
	_t += delta
	_vis.rotation.y = _t * 2.0
	_vis.position.y = 0.8 + sin(_t * 3.0) * 0.12


func _on_body(body: Node) -> void:
	if body is Player:
		var p := body as Player
		if energy > 0.0:
			p.fracture.add(energy)
			p.toast("+%d Fracture Energy" % int(energy))
		if health > 0.0:
			p.heal(health)
		queue_free()
