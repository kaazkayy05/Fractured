class_name Player
extends CharacterBody3D
## Player.gd — HEALTH / POSITION. Third-person controller. Abilities are child components:
## RealityShift, FractureEnergy, Combat, DefensiveCounter, ChainReaction, EchoProjection.
## Abilities unlock as the story introduces them (see Main.gd).

signal health_changed(hp: float, max_hp: float)
signal died

const SPEED := 5.0
const SPRINT := 8.0
const JUMP := 5.4
const GRAVITY := 15.0
const MOUSE_SENS := 0.0025

var max_health := 100.0
var health := 100.0
var abilities := {}
var control_enabled := true
var dead := false
var interact_block_until := 0

var pivot: Node3D
var spring: SpringArm3D
var camera: Camera3D
var model: Node3D
var shield_vis: MeshInstance3D
var reality_shift: RealityShift
var fracture: FractureEnergy
var combat: Combat
var defense: DefensiveCounter
var chain: ChainReaction
var echo: EchoProjection

var _pitch := -0.3
var _hold_t := 0.0
var _hold_target: Object = null
var _hurt := 0.0
var _body_mat: StandardMaterial3D


func _ready() -> void:
	Controls.setup()
	add_to_group("player")
	collision_layer = 2
	collision_mask = 1
	floor_snap_length = 0.4
	floor_max_angle = deg_to_rad(50)
	var cs := CollisionShape3D.new()
	var cap := CapsuleShape3D.new()
	cap.radius = 0.35
	cap.height = 1.8
	cs.shape = cap
	cs.position.y = 0.9
	add_child(cs)

	model = Node3D.new()
	add_child(model)
	var body := Palette.capsule(0.35, 1.7, Palette.SILVER)
	body.position.y = 0.88
	_body_mat = body.material_override
	model.add_child(body)
	var visor := Palette.box(Vector3(0.42, 0.14, 0.2), Palette.CYAN, 2.5)
	visor.position = Vector3(0, 1.5, -0.27)
	model.add_child(visor)
	var pack := Palette.box(Vector3(0.4, 0.5, 0.2), Palette.NAVY)
	pack.position = Vector3(0, 1.1, 0.33)
	model.add_child(pack)
	var core := Palette.box(Vector3(0.12, 0.12, 0.05), Palette.VIOLET, 3.0)
	core.position = Vector3(0, 1.15, -0.33)
	model.add_child(core)
	shield_vis = Palette.cyl(0.6, 0.05, Palette.CYAN, 2.0, 16, 0.4)
	shield_vis.rotation.x = PI / 2
	shield_vis.position = Vector3(0, 1.1, -0.6)
	shield_vis.visible = false
	model.add_child(shield_vis)

	pivot = Node3D.new()
	pivot.position.y = 1.55
	add_child(pivot)
	pivot.top_level = true
	spring = SpringArm3D.new()
	spring.spring_length = 4.2
	spring.margin = 0.2
	spring.collision_mask = 1
	spring.rotation.x = _pitch
	var sph := SphereShape3D.new()
	sph.radius = 0.2
	spring.shape = sph
	pivot.add_child(spring)
	camera = Camera3D.new()
	camera.fov = 72
	camera.h_offset = 0.6           # over-the-shoulder
	camera.current = true
	spring.add_child(camera)
	spring.add_excluded_object(get_rid())

	reality_shift = RealityShift.new()
	fracture = FractureEnergy.new()
	combat = Combat.new()
	defense = DefensiveCounter.new()
	chain = ChainReaction.new()
	echo = EchoProjection.new()
	for c in [reality_shift, fracture, combat, defense, chain, echo]:
		add_child(c)
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED


func hud() -> HUD:
	return get_tree().get_first_node_in_group("hud") as HUD


func toast(text: String, time := 3.0) -> void:
	var h := hud()
	if h:
		h.toast(text, time)


func has_ability(a: String) -> bool:
	return abilities.get(a, false)


func unlock(list: Array) -> void:
	for a in list:
		abilities[a] = true


func set_yaw(yaw: float) -> void:
	pivot.rotation.y = yaw
	model.rotation.y = yaw


func teleport(pos: Vector3, yaw := NAN) -> void:
	global_position = pos
	velocity = Vector3.ZERO
	pivot.global_position = pos + Vector3(0, 1.55, 0)
	if not is_nan(yaw):
		set_yaw(yaw)
	reset_physics_interpolation()


func aim_forward() -> Vector3:
	var f := -pivot.global_transform.basis.z
	f.y = 0
	return f.normalized()


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		pivot.rotation.y -= event.relative.x * MOUSE_SENS
		_pitch = clampf(_pitch - event.relative.y * MOUSE_SENS, -1.2, 0.6)
		spring.rotation.x = _pitch
	elif event.is_action_pressed("pause"):
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	elif event is InputEventMouseButton and event.pressed and Input.mouse_mode != Input.MOUSE_MODE_CAPTURED:
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
		get_viewport().set_input_as_handled()


func _physics_process(delta: float) -> void:
	pivot.global_position = global_position + Vector3(0, 1.55, 0)
	model.visible = spring.get_hit_length() > 1.1      # don't fill the screen with the back of your head
	_hurt = maxf(0.0, _hurt - delta)
	_body_mat.albedo_color = Palette.SILVER.lerp(Color(1, 0.3, 0.2), _hurt * 4.0)
	if dead:
		return
	# abilities work even if the browser refused pointer lock (mouse look then just needs a click)
	var can_act := control_enabled
	var input := Input.get_vector("move_left", "move_right", "move_forward", "move_back") if control_enabled else Vector2.ZERO
	var fwd := aim_forward()
	var right := fwd.cross(Vector3.UP)
	var dir := (right * input.x - fwd * input.y)
	if dir.length() > 1.0:
		dir = dir.normalized()

	var speed := SPRINT if Input.is_action_pressed("sprint") else SPEED
	if defense.guarding:
		speed *= 0.4
	if combat.is_attacking():
		speed *= 0.5
	var target_v := dir * speed
	var accel := 40.0 if is_on_floor() else 12.0
	velocity.x = move_toward(velocity.x, target_v.x, accel * delta)
	velocity.z = move_toward(velocity.z, target_v.z, accel * delta)
	if not is_on_floor():
		velocity.y -= GRAVITY * delta
	elif control_enabled and Input.is_action_just_pressed("jump"):
		velocity.y = JUMP
	move_and_slide()

	if combat.is_attacking() or defense.guarding:
		model.rotation.y = lerp_angle(model.rotation.y, atan2(-fwd.x, -fwd.z), 0.4)
	elif dir.length() > 0.1:
		model.rotation.y = lerp_angle(model.rotation.y, atan2(-dir.x, -dir.z), 0.2)

	if not can_act:
		defense.set_guard(false)
		shield_vis.visible = false
		return
	if has_ability("shift") and Input.is_action_just_pressed("reality_shift"):
		reality_shift.try_shift()
	if has_ability("burst") and Input.is_action_just_pressed("fracture_burst"):
		fracture.try_burst()
	if has_ability("combat") and Input.is_action_just_pressed("attack"):
		combat.attack()
	defense.set_guard(has_ability("guard") and Input.is_action_pressed("guard"))
	shield_vis.visible = defense.guarding
	if has_ability("chain") and Input.is_action_just_pressed("chain_reaction"):
		chain.try_pulse()
	if has_ability("echo") and Input.is_action_just_pressed("echo"):
		echo.project()
	if has_ability("echo") and Input.is_action_just_pressed("recall"):
		echo.recall()
	_interaction(delta)


func _interaction(delta: float) -> void:
	var h := hud()
	var best: Object = null
	var best_d := INF
	var p := global_position + Vector3(0, 0.9, 0)
	for n in get_tree().get_nodes_in_group("interactable"):
		var it := n as Interactable
		if it and it.can_use():
			var d := it.global_position.distance_to(global_position)
			if d < it.radius and d < best_d:
				best = it
				best_d = d
	if best == null and has_ability("structure"):
		for n in get_tree().get_nodes_in_group("structure"):
			var st := n as Structure
			if st and st.is_present():
				var d := st.distance_to_point(p)
				if d < Structure.MANIPULATE_RANGE and d < best_d:
					best = st
					best_d = d
	if best != _hold_target:
		_hold_t = 0.0
		_hold_target = best
	if h:
		if best is Interactable:
			var it := best as Interactable
			h.set_prompt(("[Hold E] " if it.hold_time > 0.0 else "[E] ") + it.prompt, _hold_t / it.hold_time if it.hold_time > 0.0 else -1.0)
		elif best is Structure:
			h.set_prompt((best as Structure).prompt())
		else:
			h.set_prompt("")
	if best == null or Time.get_ticks_msec() < interact_block_until:
		return
	if best is Interactable and (best as Interactable).hold_time > 0.0:
		var it := best as Interactable
		if Input.is_action_pressed("interact"):
			_hold_t += delta
			if _hold_t >= it.hold_time:
				_hold_t = 0.0
				it.use()
		else:
			_hold_t = 0.0
	elif Input.is_action_just_pressed("interact"):
		if best is Interactable:
			(best as Interactable).use()
		elif best is Structure:
			(best as Structure).manipulate()


func on_reality_shifted() -> void:
	FX.sphere(get_parent(), global_position + Vector3(0, 1, 0), 2.5, Palette.VIOLET, 0.3)
	var h := hud()
	if h:
		h.flash(Palette.VIOLET, 0.25)


func take_damage(amount: float, source: Node = null, unblockable := false) -> void:
	if dead or amount <= 0.0:
		return
	if not unblockable:
		amount = defense.filter_damage(amount, source)
	if amount <= 0.0:
		return
	health = maxf(0.0, health - amount)
	_hurt = 0.25
	health_changed.emit(health, max_health)
	if health <= 0.0:
		dead = true
		died.emit()


func heal(amount: float) -> void:
	health = minf(max_health, health + amount)
	health_changed.emit(health, max_health)


func revive() -> void:
	dead = false
	health = max_health
	health_changed.emit(health, max_health)


func swing_fx(step: int, counter: bool) -> void:
	var c := Palette.VIOLET if counter else Palette.CYAN
	var pos := global_position + Vector3(0, 1.0, 0) + aim_forward() * 1.2
	FX.sphere(get_parent(), pos, 0.9 if step < 2 else 1.4, c, 0.15)
