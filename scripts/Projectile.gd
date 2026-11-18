class_name Projectile
extends Area3D
## Drone / guardian energy bolt.

var velocity := Vector3.ZERO
var damage := 8.0
var shooter: Node = null
var life := 3.5


func _ready() -> void:
	collision_layer = 0
	collision_mask = 1 | 2
	var cs := CollisionShape3D.new()
	var sp := SphereShape3D.new()
	sp.radius = 0.18
	cs.shape = sp
	add_child(cs)
	var m := Palette.box(Vector3(0.18, 0.18, 0.5), Palette.AMBER, 4.0)
	add_child(m)
	body_entered.connect(_on_body)


func _physics_process(delta: float) -> void:
	global_position += velocity * delta
	if velocity.length() > 0.1:
		look_at(global_position + velocity, Vector3.UP)
	life -= delta
	if life <= 0.0:
		queue_free()


func _on_body(body: Node) -> void:
	if body is EnemyAI:
		return
	if body is Player:
		(body as Player).take_damage(damage, shooter if is_instance_valid(shooter) else null)
	queue_free()
