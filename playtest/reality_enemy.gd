extends CharacterBody3D
@export_range(50, 100, 1) var max_health := 75
@export var detection_range := 10.0
@export var nova_patrol_radius := 6.0
@export var nova_patrol_speed := 1.4
@export var nova_attack_range := 7.0
@export var nova_attack_interval := 2.0
@export var veyra_speed := 3.2
@export var veyra_attack_range := 2.1
@export var veyra_attack_interval := 1.0
@export var high_instability_range_bonus := 3.0
@export var high_instability_speed_multiplier := 1.35
@export var high_instability_attack_interval_multiplier := 0.7
@export var attack_damage := 8
var health := 75
var player: CharacterBody3D
var unstable_structure: Node3D
var reality := 0
var instability := 0
var origin := Vector3.ZERO
var patrol_phase := 0.0
var cooldown := 0.0

func _ready() -> void:
 health = max_health
 origin = global_position
 var mesh := MeshInstance3D.new()
 var body := CapsuleMesh.new()
 body.radius = 0.45
 body.height = 1.8
 mesh.mesh = body
 mesh.position.y = 0.9
 var material := StandardMaterial3D.new()
 material.albedo_color = Color("#ffad56") if reality == 0 else Color("#a675ed")
 mesh.material_override = material
 add_child(mesh)
 var collider := CollisionShape3D.new()
 var shape := CapsuleShape3D.new()
 shape.radius = 0.45
 shape.height = 1.8
 collider.shape = shape
 collider.position.y = 0.9
 add_child(collider)

func configure(active_reality: int, current_instability: int) -> void:
 reality = active_reality
 instability = current_instability

func take_damage(amount: int) -> void:
 health = maxi(0, health - amount)
 if health == 0: queue_free()

func _physics_process(delta: float) -> void:
 if not is_instance_valid(player): return
 cooldown = maxf(0.0, cooldown - delta)
 var distance := global_position.distance_to(player.global_position)
 var hot := instability >= 60
 var range_bonus := high_instability_range_bonus if hot else 0.0
 var direction := Vector3.ZERO
 if reality == 0:
  patrol_phase += delta * nova_patrol_speed
  var patrol_target := origin + Vector3(cos(patrol_phase), 0, sin(patrol_phase)) * nova_patrol_radius
  direction = patrol_target - global_position
  direction = direction.normalized() * nova_patrol_speed if direction.length() > 0.5 else Vector3.ZERO
  if distance <= detection_range and distance <= nova_attack_range + range_bonus and has_line_of_sight():
   attack(nova_attack_interval, hot)
 else:
  if distance <= detection_range + range_bonus and distance > 1.2:
   direction = player.global_position - global_position
   direction.y = 0
   direction = direction.normalized() * veyra_speed * (high_instability_speed_multiplier if hot else 1.0)
  if distance <= veyra_attack_range + range_bonus and has_line_of_sight():
   attack(veyra_attack_interval, hot)
 velocity.x = direction.x
 velocity.z = direction.z
 velocity.y -= 18.0 * delta
 move_and_slide()

func has_line_of_sight() -> bool:
 var start := global_position + Vector3.UP * 1.4
 var finish := player.global_position + Vector3.UP * 1.4
 var query := PhysicsRayQueryParameters3D.create(start, finish)
 query.exclude = [get_rid()]
 var hit := get_world_3d().direct_space_state.intersect_ray(query)
 return hit.is_empty() or hit.get("collider") == player

func attack(interval: float, hot: bool) -> void:
 if cooldown > 0.0: return
 cooldown = interval * (high_instability_attack_interval_multiplier if hot else 1.0)
 if player.has_meta("health"):
  player.set_meta("health", maxi(0, int(player.get_meta("health")) - attack_damage))
 if is_instance_valid(unstable_structure) and global_position.distance_to(unstable_structure.global_position) < 4.0:
  unstable_structure.call("damage", attack_damage)
