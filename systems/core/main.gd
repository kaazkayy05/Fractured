extends Node3D

const PLAYER_SCRIPT: Script = preload("res://systems/player/player.gd")

var player: Variant
var hud: Label
var notice: Label
var active_reality: int = 0
var instability: float = 0.0
var fracture_energy: float = 0.0
var shift_cooldown: float = 0.0
var burst_cooldown: float = 0.0
var last_instability_change: float = 0.0
var decay_clock: float = 0.0
var targets: Array[StaticBody3D] = []
var target_health: Dictionary = {}
var target_reset_timers: Dictionary = {}
var start_time: float = 0.0

func _ready() -> void:
	start_time = Time.get_ticks_msec() / 1000.0
	_build_environment()
	_build_player()
	_build_targets()
	_build_hud()
	_update_reality_visibility()
	_show_notice("Hali's mechanics: shift realities and build Fracture Energy through successful attacks.")

func _build_environment() -> void:
	var world := WorldEnvironment.new()
	var env := Environment.new()
	env.background_mode = Environment.BG_SKY
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color("#64717a")
	env.ambient_light_energy = 0.7
	world.environment = env
	add_child(world)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-55.0, -25.0, 0.0)
	sun.light_energy = 1.2
	add_child(sun)
	_add_box("Arena floor", Vector3(0, -0.5, 0), Vector3(34, 1, 34), Color("#3a3d40"), -1)
	_add_box("North wall", Vector3(0, 2, -17), Vector3(34, 4, 1), Color("#3a3d40"), -1)
	_add_box("South wall", Vector3(0, 2, 17), Vector3(34, 4, 1), Color("#3a3d40"), -1)
	_add_box("West wall", Vector3(-17, 2, 0), Vector3(1, 4, 34), Color("#3a3d40"), -1)
	_add_box("East wall", Vector3(17, 2, 0), Vector3(1, 4, 34), Color("#3a3d40"), -1)
	for x: float in [-12.0, -6.0, 0.0, 6.0, 12.0]:
		_add_box("Nova light", Vector3(x, 4, -14), Vector3(0.22, 0.22, 3.0), Color("#00e5ff"), 0, true)
		_add_box("Veyra root", Vector3(x, 1.4, 14), Vector3(0.7, 2.8, 1.1), Color("#2e5a3c"), 1, true)
	_add_box("Nova cover", Vector3(-4, 0.8, -2), Vector3(2.2, 1.6, 1.2), Color("#00e5ff"), 0, true)
	_add_box("Veyra cover", Vector3(4, 0.8, 2), Vector3(2.2, 1.6, 1.2), Color("#2e5a3c"), 1, true)
	_add_box("Veyra divider", Vector3(0, 1.5, -5), Vector3(4, 3, 1), Color("#55565d"), 1, true)

func _build_player() -> void:
	player = PLAYER_SCRIPT.new()
	player.name = "Player"
	player.position = Vector3(0, 0, 9)
	add_child(player)

func _build_targets() -> void:
	_add_target("Nova target", Vector3(-8, 0, -5), 0)
	_add_target("Veyra target", Vector3(8, 0, -5), 1)
	_add_target("Nova target 2", Vector3(0, 0, -10), 0)
	_add_target("Veyra target 2", Vector3(0, 0, 10), 1)

func _build_hud() -> void:
	var canvas := CanvasLayer.new()
	add_child(canvas)
	hud = Label.new()
	hud.position = Vector2(18, 14)
	hud.add_theme_font_size_override("font_size", 18)
	hud.add_theme_color_override("font_color", Color("#f4f4f6"))
	canvas.add_child(hud)
	notice = Label.new()
	notice.position = Vector2(18, 620)
	notice.size = Vector2(1100, 70)
	notice.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	notice.add_theme_font_size_override("font_size", 17)
	notice.add_theme_color_override("font_color", Color("#ffffff"))
	canvas.add_child(notice)
	var reticle := Label.new()
	reticle.text = "+"
	reticle.position = Vector2(634, 348)
	reticle.add_theme_font_size_override("font_size", 25)
	canvas.add_child(reticle)

func _process(delta: float) -> void:
	var elapsed: float = Time.get_ticks_msec() / 1000.0 - start_time
	shift_cooldown = maxf(0.0, shift_cooldown - delta)
	burst_cooldown = maxf(0.0, burst_cooldown - delta)
	if elapsed - last_instability_change >= 10.0 and instability > 0.0:
		decay_clock += delta
		if decay_clock >= 3.0:
			decay_clock = 0.0
			instability = maxf(0.0, instability - 1.0)
	else:
		decay_clock = 0.0
	for target: StaticBody3D in targets:
		var key: int = target.get_instance_id()
		if target_reset_timers.has(key):
			target_reset_timers[key] = float(target_reset_timers[key]) - delta
			if float(target_reset_timers[key]) <= 0.0:
				target_health[key] = 50.0
				target_reset_timers.erase(key)
				_set_target_color(target, Color("#00e5ff") if int(target.get_meta("reality_id")) == 0 else Color("#2e5a3c"))
	_update_hud()
	_update_reality_visibility()

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		basic_attack()
		return
	if not (event is InputEventKey and event.pressed and not event.echo):
		return
	var key_event := event as InputEventKey
	match key_event.keycode:
		KEY_Q: reality_shift()
		KEY_F: fracture_burst()
		KEY_H: basic_attack()

func reality_shift() -> void:
	if shift_cooldown > 0.0:
		_show_notice("Reality Shift is recharging.")
		return
	var destination_reality: int = 1 - active_reality
	if not _find_safe_shift_position(destination_reality):
		_show_notice("The new reality is blocked here.")
		return
	var high_instability: bool = instability >= 60.0
	active_reality = destination_reality
	_update_reality_visibility()
	shift_cooldown = 3.0
	add_instability(5.0)
	if high_instability:
		fracture_energy = minf(100.0, fracture_energy + 10.0)
	_show_notice("Shifted to %s.%s" % [_reality_name(active_reality), " +10 Fracture Energy." if high_instability else ""])

func basic_attack() -> void:
	var origin: Vector3 = player.camera.global_position
	var query := PhysicsRayQueryParameters3D.create(origin, origin - player.camera.global_transform.basis.z * 18.0)
	query.exclude = [player.get_rid()]
	var result: Dictionary = get_world_3d().direct_space_state.intersect_ray(query)
	if result.is_empty():
		return
	var collider: Object = result.get("collider")
	if not collider is StaticBody3D or not collider.is_in_group("training_targets"):
		return
	var target := collider as StaticBody3D
	if int(target.get_meta("reality_id")) != active_reality:
		return
	var id: int = target.get_instance_id()
	if float(target_health[id]) <= 0.0:
		return
	target_health[id] = maxf(0.0, float(target_health[id]) - 20.0)
	fracture_energy = minf(100.0, fracture_energy + 5.0)
	_set_target_color(target, Color("#e67e22"))
	if float(target_health[id]) <= 0.0:
		target_reset_timers[id] = 2.0
		_show_notice("Hit confirmed: +5 Fracture Energy. Target resets in 2 seconds.")
	else:
		_show_notice("Hit confirmed: +5 Fracture Energy. Target health: %d / 50" % int(target_health[id]))

func fracture_burst() -> void:
	if burst_cooldown > 0.0 or fracture_energy < 40.0:
		_show_notice("Fracture Burst needs 40 energy and a ready cooldown.")
		return
	fracture_energy -= 40.0
	burst_cooldown = 5.0
	add_instability(15.0)
	var hit_count: int = 0
	for target: StaticBody3D in targets:
		if int(target.get_meta("reality_id")) != active_reality:
			continue
		if target.global_position.distance_to(player.global_position) > 4.0:
			continue
		var id: int = target.get_instance_id()
		target_health[id] = maxf(0.0, float(target_health[id]) - 25.0)
		_set_target_color(target, Color("#a020f0"))
		if float(target_health[id]) <= 0.0:
			target_reset_timers[id] = 2.0
		hit_count += 1
	_show_notice("Fracture Burst dealt 25 damage in 4 m. Targets hit: %d." % hit_count)

func add_instability(amount: float) -> void:
	instability = clampf(instability + amount, 0.0, 100.0)
	last_instability_change = Time.get_ticks_msec() / 1000.0 - start_time
	decay_clock = 0.0

func _find_safe_shift_position(destination_reality: int) -> bool:
	var offsets: Array[Vector3] = [Vector3.ZERO, Vector3(1, 0, 0), Vector3(-1, 0, 0), Vector3(0, 0, 1), Vector3(0, 0, -1)]
	for offset: Vector3 in offsets:
		var candidate: Vector3 = player.global_position + offset
		var blocked: bool = false
		for geometry: Node in get_tree().get_nodes_in_group("reality_geometry"):
			var body := geometry as Node3D
			if int(body.get_meta("reality_id")) == destination_reality and candidate.distance_to(body.global_position) < 1.4:
				blocked = true
				break
		if not blocked:
			player.global_position = candidate
			return true
	return false

func _add_box(label: String, at: Vector3, size: Vector3, color: Color, reality: int, glowing: bool = false) -> StaticBody3D:
	var body := StaticBody3D.new()
	body.name = label
	body.position = at
	if reality >= 0:
		body.add_to_group("reality_geometry")
		body.set_meta("reality_id", reality)
	var mesh_instance := MeshInstance3D.new()
	var mesh := BoxMesh.new()
	mesh.size = size
	mesh_instance.mesh = mesh
	var material := StandardMaterial3D.new()
	material.albedo_color = color
	material.roughness = 0.72
	if glowing:
		material.emission_enabled = true
		material.emission = color * 0.3
	mesh_instance.material_override = material
	body.add_child(mesh_instance)
	var collision := CollisionShape3D.new()
	var shape := BoxShape3D.new()
	shape.size = size
	collision.shape = shape
	body.add_child(collision)
	add_child(body)
	return body

func _add_target(label: String, at: Vector3, reality: int) -> void:
	var target := StaticBody3D.new()
	target.name = label
	target.position = at
	target.add_to_group("training_targets")
	target.set_meta("reality_id", reality)
	var mesh_instance := MeshInstance3D.new()
	var mesh := CylinderMesh.new()
	mesh.top_radius = 0.55
	mesh.bottom_radius = 0.7
	mesh.height = 1.8
	mesh_instance.mesh = mesh
	mesh_instance.position.y = 0.9
	var material := StandardMaterial3D.new()
	material.albedo_color = Color("#00e5ff") if reality == 0 else Color("#2e5a3c")
	mesh_instance.material_override = material
	target.add_child(mesh_instance)
	var collision := CollisionShape3D.new()
	var shape := CylinderShape3D.new()
	shape.radius = 0.65
	shape.height = 1.8
	collision.shape = shape
	collision.position.y = 0.9
	target.add_child(collision)
	add_child(target)
	targets.append(target)
	target_health[target.get_instance_id()] = 50.0

func _set_target_color(target: StaticBody3D, color: Color) -> void:
	var mesh := target.get_node_or_null("MeshInstance3D") as MeshInstance3D
	if mesh == null:
		return
	var material := StandardMaterial3D.new()
	material.albedo_color = color
	material.emission_enabled = true
	material.emission = color * 0.25
	mesh.material_override = material

func _reality_name(id: int) -> String:
	return "Nova" if id == 0 else "Veyra"

func _show_notice(message: String) -> void:
	if notice != null:
		notice.text = message

func _update_hud() -> void:
	if hud == null:
		return
	var shift_status: String = "ready" if shift_cooldown <= 0.0 else "%.1fs" % shift_cooldown
	var burst_status: String = "ready" if burst_cooldown <= 0.0 else "%.1fs" % burst_cooldown
	hud.text = "HALI'S MECHANICS  |  %s  |  Fracture Energy %d / 100  |  Instability %d / 100\nQ Reality Shift (%s, +5 instability)   F Fracture Burst (%s, costs 40, +15 instability)\nWASD move, mouse look, left click or H attack (+5 energy on hit), Space jump, Esc free mouse\nShift at 60+ instability grants +10 energy. Training targets are props for charging and testing the burst." % [_reality_name(active_reality), int(fracture_energy), int(instability), shift_status, burst_status]

func _update_reality_visibility() -> void:
	for geometry: Node in get_tree().get_nodes_in_group("reality_geometry"):
		var body := geometry as CollisionObject3D
		var visible_in_reality: bool = int(body.get_meta("reality_id")) == active_reality
		body.visible = visible_in_reality
		body.collision_layer = 1 if visible_in_reality else 0
		body.collision_mask = 1 if visible_in_reality else 0
	for item: Node in get_tree().get_nodes_in_group("training_targets"):
		var target := item as StaticBody3D
		var visible_in_reality: bool = int(target.get_meta("reality_id")) == active_reality
		target.visible = visible_in_reality
		target.collision_layer = 1 if visible_in_reality else 0
		target.collision_mask = 1 if visible_in_reality else 0
