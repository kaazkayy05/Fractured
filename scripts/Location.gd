class_name Location
extends Node3D
## Base for the four location scenes. Main.gd instances a location, hands it the Player and HUD, and calls
## start(scene_no). The location emits `completed` when the player leaves for the next location.
## Helpers here build reality layers, interactables, structures, enemies and triggers.

signal completed
signal checkpoint_reached(scene_no: int)

const ROOMS := "res://export/Fractured_%s.glb"

var player: Player
var hud: HUD
var scene_no := 0
var kill_y := -30.0
var respawn_point := Vector3.ZERO
var respawn_yaw := 0.0
var enemies: Array = []
var _triggers: Array = []      # [{pos, radius, cb, once, reality}]
var _env: WorldEnvironment


# ----------------------------------------------------------- lifecycle (override)

func start(_scene: int) -> void:
	pass


func scene_titles() -> Dictionary:
	return {}


# ----------------------------------------------------------- shared helpers

## Abilities are introduced by the scene that teaches them (architecture: location -> mechanic arrows).
const UNLOCKS := {
	2: ["shift", "burst"],                    # Research Facility: RealityShift, FractureEnergy
	3: ["combat", "guard", "echo"],           # City Streets: Combat, DefensiveCounter (+ Echo / Recall)
	4: ["structure", "chain"],                # Transit Station: Structure, ChainReaction
}


func set_scene(n: int, objective: String) -> void:
	scene_no = n
	for k in UNLOCKS:
		if k <= n:
			player.unlock(UNLOCKS[k])
	var t: String = scene_titles().get(n, "")
	hud.set_scene_title("Scene %d — %s" % [n, t])
	hud.set_objective(objective)
	checkpoint_reached.emit(n)


func objective(text: String) -> void:
	hud.set_objective(text)


func say(lines: Array, cb := Callable()) -> void:
	hud.say(lines, cb)


func toast(text: String, time := 3.5) -> void:
	hud.toast(text, time)


func set_respawn(pos: Vector3, yaw := 0.0) -> void:
	respawn_point = pos
	respawn_yaw = yaw


func place_player(pos: Vector3, yaw := 0.0) -> void:
	set_respawn(pos, yaw)
	player.teleport(pos, yaw)
	player.echo.reset_history()


func environment(sky: Color, ambient: Color, ambient_energy := 0.9, sun_energy := 0.9, fog := 0.0) -> void:
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = ambient
	env.ambient_light_energy = ambient_energy
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	if fog > 0.0:
		env.fog_enabled = true
		env.fog_light_color = sky
		env.fog_density = fog
	_env = WorldEnvironment.new()
	_env.environment = env
	add_child(_env)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-55, -35, 0)
	sun.light_energy = sun_energy
	sun.shadow_enabled = false
	add_child(sun)


func omni(pos: Vector3, c: Color, energy := 1.5, rng := 12.0) -> OmniLight3D:
	var l := OmniLight3D.new()
	l.light_color = c
	l.light_energy = energy
	l.omni_range = rng
	l.position = pos
	add_child(l)
	return l


func load_room(id: String, offset := Vector3.ZERO, reality := -1) -> Node3D:
	## Instances an exported room glb. reality -1 = always present, else a RealityManager layer.
	var ps := load(ROOMS % id) as PackedScene
	var room := ps.instantiate() as Node3D
	room.position = offset
	add_child(room)
	for b in room.find_children("*VOL_*", "StaticBody3D", true, false):
		# trigger volumes (water / chasm) are handled in code, not as solid floors
		for cs in b.find_children("*", "CollisionShape3D", true, false):
			cs.add_to_group("force_disabled")
			cs.disabled = true
	_apply_extras(room)
	if reality >= 0:
		RealityManager.register_layer(room, reality)
	return room


var _spinners: Array = []      # [{node, axis, speed}]


func _apply_extras(room: Node) -> void:
	## Uses the glTF extras written by the Blender build scripts.
	for n in room.find_children("*", "Node3D", true, false):
		if not n.has_meta("extras"):
			continue
		var ex: Dictionary = n.get_meta("extras")
		if ex.get("state", "") == "broken":
			# breakaway bridge starts intact; broken pieces + broken collision stay hidden
			(n as Node3D).visible = false
			for cs in n.find_children("*", "CollisionShape3D", true, false):
				cs.add_to_group("force_disabled")
				cs.disabled = true
		if ex.has("rotate_axis"):
			# Blender local Y -> Godot local Z, Blender local Z -> Godot local Y
			var axis := Vector3(0, 0, 1) if str(ex.rotate_axis).ends_with("Y") else Vector3(0, 1, 0)
			_spinners.append({"node": n, "axis": axis, "speed": 0.6 * float(ex.get("rotate_dir", 1.0))})


func _process(delta: float) -> void:
	for s in _spinners:
		if is_instance_valid(s.node):
			(s.node as Node3D).rotate_object_local(s.axis, s.speed * delta)


static func node_pos(room: Node, node_name: String, fallback: Vector3) -> Vector3:
	var n := room.find_child(node_name, true, false) as Node3D
	return n.global_position if n else fallback


func load_city(path: String, reality: int, with_collision := true) -> Node3D:
	## The team's Nova/Veyra city meshes (web-weight copies in res://cities/). Collision comes from the
	## hidden WalkGeometry mesh, exactly like playtest/crossing.gd.
	if not ResourceLoader.exists(path):
		return null
	var city := (load(path) as PackedScene).instantiate() as Node3D
	add_child(city)
	var walk := city.find_children("WalkGeometry*", "MeshInstance3D", true, false)
	if walk.size() > 0:
		var geo := walk[0] as MeshInstance3D
		geo.visible = false
		if with_collision:
			var body := StaticBody3D.new()
			city.add_child(body)
			var cs := CollisionShape3D.new()
			cs.shape = geo.mesh.create_trimesh_shape()
			body.add_child(cs)
			cs.global_transform = geo.global_transform
	RealityManager.register_layer(city, reality)
	return city


func interactable(pos: Vector3, prompt: String, cb: Callable, reality := -1, hold := 0.0, rad := 2.4) -> Interactable:
	var it := Interactable.new()
	it.prompt = prompt
	it.callback = cb
	it.reality = reality
	it.hold_time = hold
	it.radius = rad
	add_child(it)
	it.global_position = pos
	return it


func beacon(pos: Vector3, c: Color, h := 1.2) -> MeshInstance3D:
	var m := Palette.cyl(0.18, h, c, 3.0, 8)
	add_child(m)
	m.global_position = pos + Vector3(0, h * 0.5, 0)
	return m


func npc(pos: Vector3, who: String, color: Color, cb: Callable, reality := -1, yaw := 0.0) -> Interactable:
	var it := interactable(pos, "Talk to " + who, cb, reality, 0.0, 2.8)
	it.one_shot = false
	it.marker_height = 2.4
	it.rotation.y = yaw
	var body := Palette.capsule(0.33, 1.75, color)
	body.position.y = 0.88
	it.add_child(body)
	var head := Palette.box(Vector3(0.36, 0.12, 0.2), Palette.CYAN if who == "Dr. Voss" else Palette.LANTERN, 2.0)
	head.position = Vector3(0, 1.5, -0.25)
	it.add_child(head)
	var lbl := Label3D.new()
	lbl.text = who
	lbl.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	lbl.position.y = 2.05
	lbl.font_size = 40
	lbl.outline_size = 8
	it.add_child(lbl)
	var col := StaticBody3D.new()
	var cs := CollisionShape3D.new()
	var cap := CapsuleShape3D.new()
	cap.radius = 0.33
	cap.height = 1.75
	cs.shape = cap
	cs.position.y = 0.88
	col.add_child(cs)
	it.add_child(col)
	return it


func structure(pos: Vector3, size: Vector3, color: Color, mode := Structure.Mode.COLLAPSE, stability := 100.0, reality := -1, lbl := "unstable structure") -> Structure:
	var s := Structure.create(size, color, mode, stability)
	s.reality = reality
	s.label = lbl
	add_child(s)
	s.global_position = pos
	return s


func blocker(pos: Vector3, size: Vector3, color: Color, reality := -1) -> StaticBody3D:
	## Plain solid that only exists in one reality (debris, roots, shutters).
	var b := StaticBody3D.new()
	var m := Palette.box(size, color)
	b.add_child(m)
	var cs := CollisionShape3D.new()
	var bs := BoxShape3D.new()
	bs.size = size
	cs.shape = bs
	b.add_child(cs)
	add_child(b)
	b.global_position = pos
	if reality >= 0:
		RealityManager.register_layer(b, reality)
	return b


func spawn_drone(pos: Vector3) -> EnemyAI:
	var e := EnemyAI.make_drone()
	add_child(e)
	e.global_position = pos
	enemies.append(e)
	return e


func spawn_wave(points: Array, on_cleared: Callable) -> void:
	var wave: Array = []
	for p in points:
		wave.append(spawn_drone(p))
	var remaining := [wave.size()]
	for e in wave:
		(e as EnemyAI).died.connect(func(_x):
			remaining[0] -= 1
			if remaining[0] <= 0:
				on_cleared.call())


func trigger(pos: Vector3, radius: float, cb: Callable, once := true, reality := -1) -> Dictionary:
	var t := {"pos": pos, "radius": radius, "cb": cb, "once": once, "reality": reality, "active": true}
	_triggers.append(t)
	return t


func exit_marker(pos: Vector3, c := Palette.CYAN) -> Node3D:
	var n := Node3D.new()
	add_child(n)
	n.global_position = pos
	var ring := Palette.cyl(1.2, 0.06, c, 2.5, 24, 0.7)
	n.add_child(ring)
	var col := Palette.cyl(0.08, 3.0, c, 3.0, 6, 0.6)
	col.position.y = 1.5
	n.add_child(col)
	return n


func ground(p: Vector3, up := 3.0, down := 12.0) -> Vector3:
	## Snap a point onto the floor below it (needs at least one physics frame after collision is added).
	var q := PhysicsRayQueryParameters3D.create(p + Vector3(0, up, 0), p - Vector3(0, down, 0), 1)
	var hit := get_world_3d().direct_space_state.intersect_ray(q)
	return hit.position if hit else p


func floor_near(center: Vector3, radius := 3.0, step := 0.75) -> Vector3:
	## Nearest point (spiral grid search) with a floor at roughly center.y — keeps props off ledges/chasms.
	var best := center
	var best_d := INF
	var r := 0.0
	while r <= radius:
		var n := maxi(1, int(r * 8.0 / step))
		for i in n:
			var a := TAU * i / n
			var c := center + Vector3(cos(a) * r, 0, sin(a) * r)
			var g := ground(c, 1.5, 1.5)
			if g != c and absf(g.y - center.y) < 0.35 and r < best_d:
				best = g
				best_d = r
		if best_d < INF:
			return best
		r += step
	return center


func clear_enemies() -> void:
	for e in enemies:
		if is_instance_valid(e):
			e.queue_free()
	enemies.clear()


func _physics_process(_delta: float) -> void:
	if player == null:
		return
	if player.global_position.y < kill_y and not player.dead:
		on_fell()
	for t in _triggers:
		if not t.active or not RealityManager.present(t.reality):
			continue
		if player.global_position.distance_to(t.pos) < t.radius:
			if t.once:
				t.active = false
			(t.cb as Callable).call()


func on_fell() -> void:
	toast("You fell. Back to the last safe point.")
	player.take_damage(15.0, null, true)
	if not player.dead:
		player.teleport(respawn_point, respawn_yaw)
