class_name EnemyAI
extends CharacterBody3D
## EnemyAI.gd — ENEMY STATE. Security drones and the reactor guardian.
## Reads RealityManager: in NOVA drones are "ordered" (armoured, keep range, fire bolts);
## in VEYRA they are "feral" (fast melee rushers, no armour). Reads InstabilityManager: higher
## instability makes every enemy faster and more aggressive. Kills lower instability.

signal died(e: EnemyAI)

enum Kind { DRONE, GUARDIAN }
enum State { IDLE, CHASE, STUNNED, DEAD }

var kind := Kind.DRONE
var max_hp := 40.0
var hp := 40.0
var radius := 0.45
var state := State.IDLE
var aggro_range := 18.0
var alive := true
var shield := false               # guardian: convergence shield
var home := Vector3.ZERO          # guardian stays near the core
var stun_left := 0.0
var attack_cd := 1.5
var hover := 1.5
var drop_energy := 12.0

var _body: MeshInstance3D
var _eye: MeshInstance3D
var _shield_mesh: MeshInstance3D
var _knock := Vector3.ZERO
var _strafe := 1.0
var _strafe_t := 0.0
var _flash := 0.0
var _last_mode := -1
var _slam_cancel := false


static func make_drone() -> EnemyAI:
	var e := EnemyAI.new()
	e.kind = Kind.DRONE
	e.max_hp = 40.0
	e.radius = 0.45
	return e


static func make_guardian() -> EnemyAI:
	var e := EnemyAI.new()
	e.kind = Kind.GUARDIAN
	e.max_hp = 320.0
	e.radius = 1.4
	e.hover = 2.4
	e.shield = true
	e.aggro_range = 60.0
	e.attack_cd = 3.0
	e.drop_energy = 0.0
	return e


func _ready() -> void:
	hp = max_hp
	add_to_group("enemy")
	collision_layer = 4
	collision_mask = 1
	motion_mode = CharacterBody3D.MOTION_MODE_FLOATING
	var cs := CollisionShape3D.new()
	var sp := SphereShape3D.new()
	sp.radius = radius
	cs.shape = sp
	add_child(cs)
	if kind == Kind.DRONE:
		_body = Palette.box(Vector3(0.8, 0.45, 0.8), Palette.CHARCOAL)
		add_child(_body)
		var ring := Palette.cyl(0.55, 0.08, Palette.SILVER, 0.0, 12)
		add_child(ring)
		_eye = Palette.box(Vector3(0.36, 0.16, 0.1), Palette.AMBER, 3.0)
		_eye.position = Vector3(0, 0, -0.42)
		add_child(_eye)
	else:
		_body = Palette.cyl(1.2, 1.6, Palette.CHARCOAL, 0.0, 6)
		add_child(_body)
		var crown := Palette.crystal(1.4, Palette.SILVER, 0.5)
		crown.position.y = 1.4
		add_child(crown)
		_eye = Palette.box(Vector3(1.2, 0.3, 0.2), Palette.AMBER, 3.0)
		_eye.position = Vector3(0, 0.3, -1.15)
		add_child(_eye)
		_shield_mesh = MeshInstance3D.new()
		var sm := SphereMesh.new()
		sm.radius = 2.0
		sm.height = 4.0
		_shield_mesh.mesh = sm
		var m := Palette.mat(Palette.CYAN, 1.5, 0.25)
		m.cull_mode = BaseMaterial3D.CULL_DISABLED
		_shield_mesh.material_override = m
		add_child(_shield_mesh)
	_strafe = 1.0 if randf() > 0.5 else -1.0


func _target() -> Node3D:
	var echo := get_tree().get_first_node_in_group("echo") as Node3D
	if echo and echo.visible and echo.global_position.distance_to(global_position) < 12.0:
		return echo
	return get_tree().get_first_node_in_group("player") as Node3D


func _feral() -> bool:
	return RealityManager.active == RealityManager.Reality.VEYRA and not RealityManager.merged


func _physics_process(delta: float) -> void:
	if not alive:
		return
	_flash = maxf(0.0, _flash - delta)
	_update_look()
	var target := _target()
	if target == null:
		return
	var aim := target.global_position + Vector3(0, 1.0, 0)
	var to := aim - global_position
	var dist := to.length()
	var flat := Vector3(to.x, 0, to.z)
	var aggression := 1.0 + 0.6 * InstabilityManager.ratio()
	attack_cd -= delta * aggression
	_knock = _knock.move_toward(Vector3.ZERO, 20.0 * delta)

	if stun_left > 0.0:
		stun_left -= delta
		velocity = _knock
		rotate_y(delta * 8.0)
		move_and_slide()
		return
	if state == State.IDLE:
		if dist < aggro_range:
			state = State.CHASE
		else:
			return

	var desired := Vector3.ZERO
	if kind == Kind.DRONE:
		if _feral():
			desired = flat.normalized() * 6.0 * aggression
			if dist < 1.7 and attack_cd <= 0.0:
				_melee(target, 12.0)
				attack_cd = 1.3
				_knock = -flat.normalized() * 5.0
		else:
			_strafe_t -= delta
			if _strafe_t <= 0.0:
				_strafe_t = randf_range(1.5, 3.0)
				_strafe = -_strafe
			var side := flat.normalized().cross(Vector3.UP) * _strafe
			if dist > 8.5:
				desired = flat.normalized() * 4.0 * aggression
			elif dist < 5.0:
				desired = -flat.normalized() * 3.0
			desired += side * 2.2
			if attack_cd <= 0.0 and dist < 16.0:
				_fire(aim, 8.0, 13.0)
				attack_cd = 1.9
	else:
		var off := global_position - home
		off.y = 0
		desired = flat.normalized() * 2.2 * aggression
		if off.length() > 11.0:
			desired = -off.normalized() * 3.0
		if attack_cd <= 0.0:
			if _feral():
				_slam(target.global_position)
				attack_cd = 3.2
			else:
				for i in 5:
					var spread := (float(i) - 2.0) * 1.2
					_fire(aim + flat.normalized().cross(Vector3.UP) * spread, 10.0, 11.0)
				attack_cd = 3.6

	var hover_y := target.global_position.y + hover
	velocity = desired + _knock
	velocity.y = (hover_y - global_position.y) * 2.5
	move_and_slide()
	if flat.length() > 0.1:
		look_at(global_position + flat, Vector3.UP)


func _update_look() -> void:
	var mode := 1 if _feral() else 0
	var c: Color = Palette.FOREST.lightened(0.25) if mode == 1 else Palette.AMBER
	if _flash > 0.0:
		c = Color.WHITE
	(_eye.material_override as StandardMaterial3D).albedo_color = c
	(_eye.material_override as StandardMaterial3D).emission = c
	if _shield_mesh:
		_shield_mesh.visible = shield
	_last_mode = mode


func _melee(target: Node3D, dmg: float) -> void:
	if target is Player:
		(target as Player).take_damage(dmg, self)
	elif target.is_in_group("echo"):
		pass
	FX.sphere(get_parent(), global_position.lerp(target.global_position + Vector3(0, 1, 0), 0.6), 0.6, Palette.FOREST, 0.15)


func _fire(at: Vector3, dmg: float, speed: float) -> void:
	var p := Projectile.new()
	p.damage = dmg
	p.shooter = self
	get_parent().add_child(p)
	p.global_position = global_position + (at - global_position).normalized() * (radius + 0.3)
	p.velocity = (at - p.global_position).normalized() * speed


func _slam(at: Vector3) -> void:
	var ring := Palette.cyl(3.0, 0.05, Palette.AMBER, 2.5, 24, 0.5)
	get_parent().add_child(ring)
	ring.global_position = at + Vector3(0, 0.05, 0)
	_slam_cancel = false
	await get_tree().create_timer(1.0, false).timeout
	if not is_instance_valid(ring):
		return
	ring.queue_free()
	if not alive or _slam_cancel:
		return
	FX.sphere(get_parent(), at, 3.0, Palette.AMBER, 0.3)
	var p := get_tree().get_first_node_in_group("player") as Player
	if p and p.global_position.distance_to(at) < 3.0:
		p.take_damage(25.0, self)


func knockback(v: Vector3) -> void:
	if kind == Kind.DRONE:
		_knock = v


func interrupt_attack() -> void:
	## Fracture Burst interrupts: resets the attack wind-up and cancels a pending slam.
	attack_cd = maxf(attack_cd, 1.5)
	_slam_cancel = true


func stun(t: float) -> void:
	stun_left = maxf(stun_left, t)


func take_damage(amount: float, piercing := false, _source: Node = null, p_stun := 0.0) -> void:
	if not alive:
		return
	if shield:
		var p := get_tree().get_first_node_in_group("player") as Player
		if p:
			p.toast("The guardian is shielded. Activate a convergence node to break it.")
		FX.sphere(get_parent(), global_position, 2.2, Palette.CYAN, 0.15)
		return
	if kind == Kind.DRONE and not _feral() and not piercing and stun_left <= 0.0:
		amount *= 0.6                # Nova drones are armoured
	hp -= amount
	_flash = 0.12
	state = State.CHASE
	if p_stun > 0.0:
		stun(p_stun)
	if hp <= 0.0:
		_die()


func _die() -> void:
	alive = false
	remove_from_group("enemy")
	InstabilityManager.add(-4.0)
	if drop_energy > 0.0:
		var pk := Pickup.make_energy(drop_energy)
		get_parent().add_child(pk)
		pk.global_position = global_position - Vector3(0, hover * 0.6, 0)
	died.emit(self)
	FX.sphere(get_parent(), global_position, radius * 3.0, Palette.AMBER, 0.35)
	var tw := create_tween()
	tw.tween_property(self, "scale", Vector3.ONE * 0.05, 0.3)
	tw.tween_callback(queue_free)
