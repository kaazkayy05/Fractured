extends Node3D

const FILES: Array[String] = ["res://worlds/nova.glb", "res://worlds/veyra.glb"]
const NAMES: Array[String] = ["NOVA", "VEYRA"]
const TITLES: Array[String] = ["Inspect the station crystal", "Reach the east entrance", "Follow the avenue to the fracture", "Recover the echo on the promenade", "Return to the fracture"]
const POINTS: Array[Vector3] = [Vector3(-161.28, 6, 229.42), Vector3(-135.5, 6, 251.42), Vector3(-104, 4.5, 251.42), Vector3(-78, 6, 352), Vector3(-104, 4.5, 251.42)]
const REQUIRED_REALITIES: Array[int] = [0, 0, 0, 1, 0]
const TRAINING_TARGETS: Array[Vector3] = [Vector3(-135.5, 6, 255.5), Vector3(-78, 6, 356)]
const ECHO_REPLAY_SECONDS := 8.0
const ECHO_LIFETIME_SECONDS := 8.0
const ECHO_COOLDOWN_SECONDS := 10.0

var worlds: Array[Node3D] = []
var bodies: Array[StaticBody3D] = []
var player := CharacterBody3D.new()
var camera := Camera3D.new()
var beacon := MeshInstance3D.new()
var hud := Label.new()
var marker := Label3D.new()
var timeline: int = 0
var stage: int = 0
var elapsed: float = 0.0
var checkpoints: Array[Vector3] = [Vector3(-157.28, 6.1, 257.42), Vector3(-157.28, 6.1, 257.42)]
var fracture_energy: float = 0.0
var instability: float = 0.0
var shift_cooldown: float = 0.0
var burst_cooldown: float = 0.0
var quiet_time: float = 0.0
var decay_timer: float = 0.0
var shift_in_progress: bool = false
var target_health: Dictionary = {}
var target_reset_timers: Dictionary = {}
var feedback: String = ""
var feedback_timer: float = 0.0
var movement_time := 0.0
var movement_times: Array[float] = []
var movement_positions: Array[Vector3] = []
var echo: Node3D
var echo_reality := 0
var echo_cooldown := 0.0
var echo_remaining := 0.0
var echo_replay_elapsed := 0.0
var echo_path_start := 0.0
var echo_times: Array[float] = []
var echo_positions: Array[Vector3] = []
var echo_segment := 0

func _ready() -> void:
	for path: String in FILES:
		var city := (load(path) as PackedScene).instantiate() as Node3D
		add_child(city)
		worlds.append(city)
		var body := StaticBody3D.new()
		city.add_child(body)
		var meshes: Array[Node] = city.find_children("WalkGeometry*", "MeshInstance3D", true, false)
		assert(meshes.size() == 1, "Missing city collision mesh")
		var geometry := meshes[0] as MeshInstance3D
		var collider := CollisionShape3D.new()
		collider.shape = geometry.mesh.create_trimesh_shape()
		body.add_child(collider)
		collider.global_transform = geometry.global_transform
		geometry.visible = false
		bodies.append(body)
	_build_environment()
	_build_player()
	_build_training_targets()
	_build_hud()
	add_promenade_link()
	switch_world(0)
	_reset_movement_history()
	update_target()
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED

func _build_environment() -> void:
	var environment := Environment.new()
	environment.background_mode = Environment.BG_SKY
	environment.sky = Sky.new()
	environment.sky.sky_material = ProceduralSkyMaterial.new()
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.ambient_light_color = Color("#e5f1ff")
	environment.ambient_light_energy = 0.85
	var ambience := WorldEnvironment.new()
	ambience.environment = environment
	add_child(ambience)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-54, -32, 0)
	sun.light_energy = 1.0
	add_child(sun)

func _build_player() -> void:
	add_child(player)
	var capsule := CapsuleShape3D.new()
	capsule.height = 1.8
	capsule.radius = 0.4
	var shape := CollisionShape3D.new()
	shape.shape = capsule
	shape.position.y = 0.9
	player.add_child(shape)
	player.floor_snap_length = 0.35
	player.position = checkpoints[0]
	player.add_child(camera)
	camera.position.y = 1.68
	camera.far = 3800.0

func _build_training_targets() -> void:
	for index: int in range(TRAINING_TARGETS.size()):
		var reality_id: int = 0 if index == 0 else 1
		var target := StaticBody3D.new()
		target.name = "FracturePracticeTarget_%s" % NAMES[reality_id]
		target.position = TRAINING_TARGETS[index]
		target.add_to_group("fracture_targets")
		target.set_meta("reality_id", reality_id)
		target.set_meta("health", 50.0)
		var mesh := MeshInstance3D.new()
		var cylinder := CylinderMesh.new()
		cylinder.top_radius = 0.55
		cylinder.bottom_radius = 0.7
		cylinder.height = 1.8
		mesh.mesh = cylinder
		mesh.position.y = 0.9
		var material := StandardMaterial3D.new()
		material.albedo_color = Color("#00e5ff") if reality_id == 0 else Color("#2e5a3c")
		material.emission_enabled = true
		material.emission = material.albedo_color * 0.2
		mesh.material_override = material
		target.add_child(mesh)
		var collision := CollisionShape3D.new()
		var target_shape := CylinderShape3D.new()
		target_shape.radius = 0.65
		target_shape.height = 1.8
		collision.shape = target_shape
		collision.position.y = 0.9
		target.add_child(collision)
		add_child(target)
		target_health[target.get_instance_id()] = 50.0

func _build_hud() -> void:
	var canvas := CanvasLayer.new()
	add_child(canvas)
	canvas.add_child(hud)
	hud.position = Vector2(18, 15)
	hud.add_theme_font_size_override("font_size", 19)
	hud.add_theme_constant_override("outline_size", 6)
	var orb := SphereMesh.new()
	orb.radius = 0.34
	orb.height = 0.68
	beacon.mesh = orb
	var glow := StandardMaterial3D.new()
	glow.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	glow.albedo_color = Color("#75fff0")
	beacon.material_override = glow
	add_child(beacon)
	marker.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	marker.no_depth_test = true
	marker.fixed_size = true
	marker.pixel_size = 0.00055
	marker.font_size = 23
	marker.outline_size = 6
	add_child(marker)

func switch_world(index: int) -> void:
	timeline = index
	for i: int in range(worlds.size()):
		worlds[i].visible = i == index
		bodies[i].collision_layer = 1 if i == index else 0
		bodies[i].collision_mask = 1 if i == index else 0
	for item: Node in get_tree().get_nodes_in_group("fracture_targets"):
		var target := item as CollisionObject3D
		var active: bool = int(target.get_meta("reality_id")) == index
		target.visible = active
		target.collision_layer = 1 if active else 0
		target.collision_mask = 1 if active else 0

func reality_shift() -> void:
	if shift_cooldown > 0.0 or shift_in_progress:
		_show_message("Reality Shift recharging: %.1fs" % shift_cooldown)
		return
	shift_in_progress = true
	var old_reality: int = timeline
	var target_reality: int = 1 - timeline
	var high_instability: bool = instability >= 60.0
	switch_world(target_reality)
	await get_tree().physics_frame
	var safe_spot: Vector3 = _find_safe_position(player.position)
	if safe_spot == Vector3.INF:
		switch_world(old_reality)
		shift_in_progress = false
		_show_message("No safe position found in %s." % NAMES[target_reality])
		return
	player.position = safe_spot
	_reset_movement_history()
	shift_in_progress = false
	shift_cooldown = 3.0
	_add_instability(5.0)
	if high_instability:
		fracture_energy = minf(100.0, fracture_energy + 10.0)
	_show_message("Shifted to %s.%s" % [NAMES[timeline], " +10 Fracture Energy at high instability." if high_instability else ""])

func _find_safe_position(origin: Vector3) -> Vector3:
	var offsets: Array[Vector3] = [
		Vector3.ZERO,
		Vector3(0.75, 0, 0), Vector3(-0.75, 0, 0), Vector3(0, 0, 0.75), Vector3(0, 0, -0.75),
		Vector3(1.5, 0, 0), Vector3(-1.5, 0, 0), Vector3(0, 0, 1.5), Vector3(0, 0, -1.5),
		Vector3(2.25, 0, 0), Vector3(-2.25, 0, 0), Vector3(0, 0, 2.25), Vector3(0, 0, -2.25)
	]
	var capsule := CapsuleShape3D.new()
	capsule.height = 1.8
	capsule.radius = 0.38
	var query := PhysicsShapeQueryParameters3D.new()
	query.shape = capsule
	query.collision_mask = 1
	query.exclude = [player.get_rid()]
	for offset: Vector3 in offsets:
		var candidate: Vector3 = origin + offset
		query.transform = Transform3D(Basis(), candidate + Vector3(0, 0.91, 0))
		if get_world_3d().direct_space_state.intersect_shape(query, 1).is_empty():
			return candidate
	return Vector3.INF

func fracture_attack() -> void:
	var from: Vector3 = camera.global_position
	var query := PhysicsRayQueryParameters3D.create(from, from - camera.global_transform.basis.z * 18.0)
	query.exclude = [player.get_rid()]
	var result: Dictionary = get_world_3d().direct_space_state.intersect_ray(query)
	if result.is_empty():
		return
	var target: Object = result.get("collider")
	if _damage_target(target, 20.0):
		fracture_energy = minf(100.0, fracture_energy + 5.0)
		_show_message("Successful hit: +5 Fracture Energy (%d / 100)." % int(fracture_energy))

func fracture_burst() -> void:
	if burst_cooldown > 0.0 or fracture_energy < 40.0:
		_show_message("Fracture Burst requires 40 energy and a ready cooldown.")
		return
	fracture_energy -= 40.0
	burst_cooldown = 5.0
	_add_instability(15.0)
	var affected: int = 0
	for group_name: StringName in [&"fracture_targets", &"enemies", &"unstable_structures"]:
		for candidate: Node in get_tree().get_nodes_in_group(group_name):
			if not candidate is Node3D:
				continue
			var target := candidate as Node3D
			if target.has_meta("reality_id") and int(target.get_meta("reality_id")) != timeline:
				continue
			if target.global_position.distance_to(player.global_position) > 4.0:
				continue
			if _damage_target(candidate, 25.0):
				affected += 1
				if candidate.has_method("interrupt_attack"):
					candidate.call("interrupt_attack")
	_show_message("Fracture Burst hit %d target(s) in 4 m. Instability +15." % affected)

func _damage_target(target: Object, amount: float) -> bool:
	if target == null:
		return false
	if target is Node and target.is_in_group("fracture_targets"):
		var practice_target := target as Node3D
		var id: int = practice_target.get_instance_id()
		var current_health: float = float(target_health.get(id, 0.0))
		if current_health <= 0.0:
			return false
		var remaining: float = maxf(0.0, current_health - amount)
		target_health[id] = remaining
		if remaining <= 0.0:
			target_reset_timers[id] = 2.0
		_set_target_color(practice_target, Color("#a020f0") if amount >= 25.0 else Color("#e67e22"))
		return true
	if target.has_method("take_damage"):
		target.call("take_damage", amount)
		return true
	if target.has_method("apply_damage"):
		target.call("apply_damage", amount)
		return true
	return false

func _set_target_color(target: Node3D, color: Color) -> void:
	var visual := target.get_node_or_null("MeshInstance3D") as MeshInstance3D
	if visual == null:
		return
	var material := StandardMaterial3D.new()
	material.albedo_color = color
	material.emission_enabled = true
	material.emission = color * 0.25
	visual.material_override = material

func _add_instability(amount: float) -> void:
	instability = clampf(instability + amount, 0.0, 100.0)
	quiet_time = 0.0
	decay_timer = 0.0

func update_target() -> void:
	if stage < POINTS.size():
		beacon.show()
		marker.show()
		beacon.position = POINTS[stage] + Vector3.UP * 1.6
		marker.position = beacon.position + Vector3.UP * 1.4
	else:
		marker.hide()
		beacon.hide()

func _try_interact() -> void:
	if stage >= POINTS.size():
		return
	if timeline != REQUIRED_REALITIES[stage]:
		_show_message("Shift to %s to continue this objective." % NAMES[REQUIRED_REALITIES[stage]])
		return
	if player.position.distance_to(POINTS[stage]) >= 6.0:
		return
	checkpoints[timeline] = player.position + Vector3.UP * 0.2
	stage += 1
	update_target()

func _show_message(text: String) -> void:
	feedback = text
	feedback_timer = 2.5

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		player.rotate_y(-event.relative.x * 0.002)
		camera.rotation.x = clampf(camera.rotation.x - event.relative.y * 0.002, -1.48, 1.48)
	if event is InputEventMouseButton and event.pressed:
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
		if event.button_index == MOUSE_BUTTON_LEFT:
			fracture_attack()
	if event is InputEventKey and event.pressed and not event.echo:
		match event.physical_keycode:
			KEY_ESCAPE: Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
			KEY_Q: reality_shift()
			KEY_F: fracture_burst()
			KEY_C: _try_spawn_echo()
			KEY_R:
				player.position = checkpoints[timeline]
				player.velocity = Vector3.ZERO
				_reset_movement_history()
			KEY_SPACE:
				if player.is_on_floor(): player.velocity.y = 6.0
			KEY_E:
				_try_interact()
			KEY_ENTER:
				if stage == POINTS.size(): get_tree().reload_current_scene()

func _physics_process(dt: float) -> void:
	if worlds.size() != 2:
		return
	movement_time += dt
	echo_cooldown = maxf(0.0, echo_cooldown - dt)
	shift_cooldown = maxf(0.0, shift_cooldown - dt)
	burst_cooldown = maxf(0.0, burst_cooldown - dt)
	feedback_timer = maxf(0.0, feedback_timer - dt)
	quiet_time += dt
	if quiet_time >= 10.0 and instability > 0.0:
		decay_timer += dt
		if decay_timer >= 3.0:
			instability = maxf(0.0, instability - 1.0)
			decay_timer = 0.0
	if stage < POINTS.size(): elapsed += dt
	for candidate: Node in get_tree().get_nodes_in_group("fracture_targets"):
		var target := candidate as Node3D
		var id: int = target.get_instance_id()
		if target_reset_timers.has(id):
			target_reset_timers[id] = float(target_reset_timers[id]) - dt
			if float(target_reset_timers[id]) <= 0.0:
				target_health[id] = 50.0
				target_reset_timers.erase(id)
				var color: Color = Color("#00e5ff") if int(target.get_meta("reality_id")) == 0 else Color("#2e5a3c")
				_set_target_color(target, color)
	var local_move := Vector3.ZERO
	if Input.is_physical_key_pressed(KEY_W): local_move.z -= 1.0
	if Input.is_physical_key_pressed(KEY_S): local_move.z += 1.0
	if Input.is_physical_key_pressed(KEY_A): local_move.x -= 1.0
	if Input.is_physical_key_pressed(KEY_D): local_move.x += 1.0
	var direction: Vector3 = player.transform.basis * local_move.normalized()
	var speed: float = 7.5 if Input.is_physical_key_pressed(KEY_SHIFT) else 4.7
	player.velocity.x = direction.x * speed
	player.velocity.z = direction.z * speed
	player.velocity.y -= 18.0 * dt
	player.move_and_slide()
	if player.position.y < -10.0:
		player.position = checkpoints[timeline]
		player.velocity = Vector3.ZERO
		_reset_movement_history()
	else:
		_record_movement()
	_update_echo(dt)
	_update_hud()

func _reset_movement_history() -> void:
	movement_times.clear()
	movement_positions.clear()
	_record_movement()

func _record_movement() -> void:
	movement_times.append(movement_time)
	movement_positions.append(player.position)
	var cutoff := movement_time - ECHO_REPLAY_SECONDS
	# Keep the sample at or just before the cutoff for interpolation.
	while movement_times.size() > 1 and movement_times[1] <= cutoff:
		movement_times.pop_front()
		movement_positions.pop_front()

func _try_spawn_echo() -> void:
	if echo_cooldown > 0.0:
		_show_message("Your echo isn’t ready yet.")
		return
	if is_instance_valid(echo):
		_show_message("An echo is already active")
		return
	var start_time := movement_time - ECHO_REPLAY_SECONDS
	if movement_times.size() < 2 or movement_times[0] > start_time:
		_show_message("Echo Projection needs 8 seconds of movement history.")
		return

	echo_times = movement_times.duplicate()
	echo_positions = movement_positions.duplicate()
	echo_path_start = start_time
	echo_segment = 0
	echo_replay_elapsed = 0.0
	echo_remaining = ECHO_LIFETIME_SECONDS
	echo_reality = timeline

	var capsule := CapsuleMesh.new()
	capsule.radius = 0.4
	capsule.height = 1.8
	var material := StandardMaterial3D.new()
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.albedo_color = Color("#DCE6EE")
	var visual := MeshInstance3D.new()
	visual.mesh = capsule
	visual.material_override = material
	visual.position.y = 0.9

	echo = Node3D.new()
	echo.position = _echo_position_at(start_time)
	echo.add_child(visual)
	add_child(echo)
	echo_cooldown = ECHO_COOLDOWN_SECONDS

func _echo_position_at(sample_time: float) -> Vector3:
	while echo_segment + 1 < echo_times.size() - 1 and echo_times[echo_segment + 1] <= sample_time:
		echo_segment += 1
	var next := echo_segment + 1
	var weight := inverse_lerp(echo_times[echo_segment], echo_times[next], sample_time)
	return echo_positions[echo_segment].lerp(echo_positions[next], weight)

func _update_echo(dt: float) -> void:
	if not is_instance_valid(echo):
		return
	echo_remaining = maxf(0.0, echo_remaining - dt)
	if echo_remaining <= 0.0:
		echo.queue_free()
		echo = null
		return
	echo.visible = echo_reality == timeline
	echo_replay_elapsed = minf(echo_replay_elapsed + dt, ECHO_REPLAY_SECONDS)
	echo.position = _echo_position_at(echo_path_start + echo_replay_elapsed)

func _update_hud() -> void:
	var shift_text: String = "ready" if shift_cooldown <= 0.0 else "%.1fs" % shift_cooldown
	var burst_text: String = "ready" if burst_cooldown <= 0.0 else "%.1fs" % burst_cooldown
	var mechanics_text: String = "Q Shift (%s)   F Burst (%s)   LMB attack (+5 on hit)" % [shift_text, burst_text]
	var energy_text: String = "Fracture Energy %d / 100     Instability %d / 100" % [int(fracture_energy), int(instability)]
	if stage < POINTS.size():
		var distance: float = player.position.distance_to(POINTS[stage])
		var required_reality: int = REQUIRED_REALITIES[stage]
		var objective_hint: String = "[E]" if distance < 6.0 and timeline == required_reality else "Shift to %s" % NAMES[required_reality] if timeline != required_reality else "Follow the diamond"
		marker.text = "◇   %d m   %s" % [roundi(distance), "" if timeline == required_reality else "· %s" % NAMES[required_reality]]
		hud.text = "%s   /   CANAL CROSSING     %d / 5\n%s   [%s]\n%s\n%s%s" % [NAMES[timeline], stage + 1, TITLES[stage], objective_hint, energy_text, mechanics_text + "   WASD move   Mouse look   Shift sprint   Space jump   R recover   Esc cursor", "\n" + feedback if feedback_timer > 0.0 else ""]
	else:
		hud.text = "ECHO RECOVERED   /   %d:%02d\n%s\nExplore the city or press Enter to replay.%s" % [int(elapsed) / 60, int(elapsed) % 60, energy_text + "   " + mechanics_text, "\n" + feedback if feedback_timer > 0.0 else ""]

func add_promenade_link() -> void:
	# Join the avenue at y=4.5 to the raised waterfront paving at y=6.
	var link := StaticBody3D.new()
	add_child(link)
	link.position = Vector3(-91.1, 5.1, 352)
	link.rotation.z = atan2(1.5, 8.0)
	var plank := BoxMesh.new()
	plank.size = Vector3(8.5, 0.3, 4.0)
	var surface := MeshInstance3D.new()
	surface.mesh = plank
	var material := StandardMaterial3D.new()
	material.albedo_color = Color("#94a9ad")
	surface.material_override = material
	link.add_child(surface)
	var shape := BoxShape3D.new()
	shape.size = plank.size
	var collider := CollisionShape3D.new()
	collider.shape = shape
	link.add_child(collider)
