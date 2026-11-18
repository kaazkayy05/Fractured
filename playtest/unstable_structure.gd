extends StaticBody3D
signal destroyed(event_id: StringName, severity: int)
@export var event_id: StringName = &"canal_column_01"
@export_range(10, 20, 1) var severity := 15
@export var health := 24
var reported := false

func _ready() -> void:
 var mesh := MeshInstance3D.new()
 var pillar := CylinderMesh.new()
 pillar.top_radius = 0.55
 pillar.bottom_radius = 0.7
 pillar.height = 2.6
 mesh.mesh = pillar
 mesh.position.y = 1.3
 add_child(mesh)
 var collider := CollisionShape3D.new()
 var shape := CylinderShape3D.new()
 shape.radius = 0.7
 shape.height = 2.6
 collider.shape = shape
 collider.position.y = 1.3
 add_child(collider)

func damage(amount: int) -> void:
 if reported: return
 health -= amount
 if health <= 0:
  reported = true
  destroyed.emit(event_id, severity)
  queue_free()
