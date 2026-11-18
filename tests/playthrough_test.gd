extends Node
## Automated smoke test: drives the whole story (Scenes 1-8) through its objectives and checks that the player
## stands on real floor at every spawn / objective point. Run:
##   Godot --headless --path . res://tests/Playthrough.tscn
## Prints "TEST PASS" / "TEST FAIL" lines; exits with code 1 on any failure.

var main: Node
var hud: HUD
var player: Player
var fails := 0


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	get_tree().create_timer(900.0, true, false, true).timeout.connect(func():
		print("TEST FAIL  watchdog timeout")
		get_tree().quit(2))
	main = (load("res://scenes/Main.tscn") as PackedScene).instantiate()
	get_tree().root.add_child.call_deferred(main)
	_run()


func ok(cond: bool, what: String) -> void:
	if cond:
		print("TEST PASS  ", what, "   [t=%ds]" % (Time.get_ticks_msec() / 1000))
	else:
		fails += 1
		print("TEST FAIL  ", what)


func frames(n: int) -> void:
	for i in n:
		await get_tree().physics_frame


func loc() -> Location:
	return main.location


func wait_loaded(scene: int, timeout := 900) -> bool:
	for i in timeout:
		if main.location and not main._loading and main.location.scene_no == scene:
			await frames(5)
			return true
		await get_tree().process_frame
	return false


func flush() -> void:
	for i in 200:
		if hud.in_dialogue():
			hud._advance()
		await get_tree().process_frame


func settle(label: String) -> void:
	## let the player fall onto whatever is under them and verify it is a floor
	await frames(45)
	var y0 := player.global_position.y
	await frames(30)
	var on_floor := player.is_on_floor() and absf(player.global_position.y - y0) < 0.05
	ok(on_floor, "%s: standing on floor at %s" % [label, player.global_position.snapped(Vector3.ONE * 0.01)])


func shot(label: String) -> void:
	## with `-- --shots=<dir>` (non-headless) saves a screenshot of the current view
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--shots="):
			for i in 3:
				await get_tree().process_frame
			var img := get_viewport().get_texture().get_image()
			img.save_png(a.trim_prefix("--shots=").path_join(label.replace(" ", "_") + ".png"))


func goto(pos: Vector3, label: String) -> void:
	player.teleport(pos + Vector3(0, 0.3, 0))
	await settle(label)


func interactables(filter := "") -> Array:
	var out := []
	for n in get_tree().get_nodes_in_group("interactable"):
		var it := n as Interactable
		if filter == "" or it.prompt.contains(filter):
			out.append(it)
	return out


func use_at(it: Interactable, label: String) -> void:
	## walk-test: stand next to the interactable, then use it
	var best := it.global_position
	var st := player.reality_shift
	for off in [Vector3(0, 0, -1.4), Vector3(0, 0, 1.4), Vector3(1.4, 0, 0), Vector3(-1.4, 0, 0), Vector3(0, 0, -2.0), Vector3(0, 0, 2.0)]:
		var c: Vector3 = it.global_position + off
		if st.find_safe_position(c) == c:
			best = c
			break
	player.teleport(best + Vector3(0, 0.3, 0))
	await settle(label)
	ok(it.can_use(), "%s: usable" % label)
	it.use()
	await frames(2)
	await flush()


func kill_all() -> void:
	for e in get_tree().get_nodes_in_group("enemy"):
		var en := e as EnemyAI
		if en.kind == EnemyAI.Kind.DRONE:
			en.take_damage(9999, true)
	await frames(10)
	await flush()


func _run() -> void:
	await frames(5)
	hud = main.hud
	player = main.player
	# ---- title -> Scene 1
	hud.hide_overlay()
	hud.title_dismissed.emit()
	ok(await wait_loaded(1), "Scene 1 loaded")
	await flush()
	await settle("S1 spawn")
	await shot("S1 spawn")
	var voss := interactables("Dr. Voss")
	ok(voss.size() == 1, "S1 Dr. Voss present")
	await use_at(voss[0], "S1 Voss")
	var consoles := interactables("console")
	ok(consoles.size() == 3, "S1 three consoles")
	for c in consoles:
		await use_at(c, "S1 " + c.prompt)
	await frames(10)
	await flush()
	# ---- Scene 2 (explosion transitions inside the location)
	for i in 400:
		if loc().scene_no == 2:
			break
		await get_tree().process_frame
	await frames(120)
	await flush()
	ok(loc().scene_no == 2, "Scene 2 reached after explosion")
	ok(player.has_ability("shift") and player.has_ability("burst"), "S2 shift + burst unlocked")
	await settle("S2 spawn")
	await shot("S2 spawn")
	player.reality_shift.try_shift()
	await frames(10)
	await flush()
	ok(RealityManager.active == RealityManager.Reality.VEYRA, "S2 shifted to Veyra")
	ok(InstabilityManager.value >= 4.9, "S2 shift added instability (%.1f)" % InstabilityManager.value)
	var shards := 0
	for n in get_tree().root.find_children("*", "Pickup", true, false):
		var pk := n as Pickup
		if pk.reality == RealityManager.Reality.VEYRA and shards < 3:
			var e0 := player.fracture.energy
			await goto(pk.global_position, "S2 shard %d" % shards)
			await frames(5)
			ok(player.fracture.energy > e0, "S2 shard %d collected (energy %d)" % [shards, int(player.fracture.energy)])
			shards += 1
	await flush()
	var rf := loc()
	await goto(Palette.bl(0, -6.2, 0), "S2 in front of crystal")
	ok(player.fracture.try_burst(), "S2 burst fired")
	await frames(10)
	await flush()
	ok(rf.barrier.broken, "S2 crystal barrier shattered")
	player.teleport(Palette.bl(0, -7.6, 0) + Vector3(0, 0.3, 0))
	await frames(20)
	await flush()
	# ---- Scene 3
	ok(await wait_loaded(3), "Scene 3 (City Streets) loaded")
	await flush()
	await settle("S3 spawn")
	await shot("S3 spawn")
	ok(get_tree().get_nodes_in_group("enemy").size() == 3, "S3 wave 1 spawned (3 drones)")
	# real combat check: one drone, melee from close range
	var d := get_tree().get_nodes_in_group("enemy")[0] as EnemyAI
	var hp0 := d.hp
	d.global_position = player.global_position + player.aim_forward() * 1.5 + Vector3(0, 1.2, 0)
	player.combat.attack()
	ok(d.hp < hp0, "S3 melee hit damaged a drone (%.0f -> %.0f)" % [hp0, d.hp])
	await kill_all()
	await frames(5)
	await flush()
	player.teleport(CityStreetsPos.wave2())
	await frames(10)
	await flush()
	ok(get_tree().get_nodes_in_group("enemy").size() == 4, "S3 wave 2 spawned (4 drones)")
	await kill_all()
	await flush()
	player.teleport(Vector3(-135.5, 6.3, 251.42))
	await frames(10)
	await flush()
	# ---- Scene 4
	ok(await wait_loaded(4), "Scene 4 (Transit Station) loaded")
	await flush()
	await settle("S4 spawn")
	await shot("S4 spawn")
	RealityManager.set_reality(RealityManager.Reality.NOVA)
	var conduits := []
	for n in get_tree().get_nodes_in_group("structure"):
		if (n as Structure).mode == Structure.Mode.MACHINERY:
			conduits.append(n)
	ok(conduits.size() == 3, "S4 three conduits")
	var n1 := interactables("Power node 01")[0] as Interactable
	await goto(n1.global_position + Vector3(0, 0, -4.6), "S4 node 01 approach")
	ok(player.chain.try_pulse(), "S4 chain reaction fired")
	await frames(30)
	var all_broken := true
	for c in conduits:
		all_broken = all_broken and (c as Structure).broken
	ok(all_broken, "S4 chain reaction broke all linked conduits")
	await use_at(n1, "S4 node 01")
	var n3 := interactables("Power node 03")[0] as Interactable
	var wall: Structure = null
	for n in get_tree().get_nodes_in_group("structure"):
		if (n as Structure).mode == Structure.Mode.COLLAPSE:
			wall = n
	await goto(wall.global_position + Vector3(0, -1.25, 1.6), "S4 node 03 wall")
	for i in 4:
		wall.manipulate()
	await frames(40)
	ok(wall.broken, "S4 support wall collapsed after 4 manipulations")
	await use_at(n3, "S4 node 03")
	player.reality_shift.cooldown_left = 0
	RealityManager.set_reality(RealityManager.Reality.VEYRA)
	await frames(3)
	var n2 := interactables("Power node 02")[0] as Interactable
	await use_at(n2, "S4 node 02 (Veyra)")
	var stab := interactables("stabilizer")[0] as Interactable
	ok(stab.enabled, "S4 stabilizer enabled after 3 nodes")
	await use_at(stab, "S4 control room")
	await frames(200)
	await flush()
	# ---- Scene 5
	ok(loc().scene_no == 5, "Scene 5 reached")
	await settle("S5 spawn")
	await shot("S5 spawn")
	var mira := interactables("Mira")[0] as Interactable
	await use_at(mira, "S5 Mira (1)")
	for c in interactables("Inspect"):
		await use_at(c, "S5 " + c.prompt)
	await use_at(mira, "S5 Mira (2)")
	player.teleport(Palette.bl(-17.0, 7, 0) + Vector3(0, 0.3, 0))
	await frames(10)
	await flush()
	# ---- Scene 6
	ok(await wait_loaded(6), "Scene 6 (Central Reactor) loaded")
	await flush()
	await settle("S6 R1 spawn")
	await shot("S6 R1 spawn")
	ok(InstabilityManager.rise_per_sec > 0.0, "S6 instability rising")
	await kill_all()
	await goto(Palette.bl(12, -3, 0), "S6 R1 east door")
	await frames(60)
	await flush()
	await settle("S6 R2 spawn")
	await shot("S6 R2 spawn")
	await kill_all()
	var logi := interactables("log")[0] as Interactable
	await use_at(logi, "S6 Voss log")
	await goto(Vector3(100, 0, 0) + Palette.bl(19.4, 0, 0), "S6 R2 exit")
	await frames(90)
	await flush()
	# ---- Scene 7
	ok(loc().scene_no == 7, "Scene 7 reached")
	await settle("S7 spawn")
	await shot("S7 spawn")
	await goto(Vector3(200, 0, 0) + Palette.bl(-8.5, 0, 0), "S7 approach Voss")
	await frames(10)
	await flush()
	var g: EnemyAI = loc().guardian
	await shot("S7 guardian")
	ok(g != null and g.shield, "S7 guardian spawned with shield")
	ok(InstabilityManager.critical_enabled, "S7 critical instability limit active")
	var nodes := interactables("convergence")
	ok(nodes.size() == 3, "S7 three convergence nodes")
	for i in 3:
		await use_at(nodes[i], "S7 " + nodes[i].prompt)
		if i == 0:
			ok(not g.shield, "S7 node breaks guardian shield")
			g.take_damage(400, true)
			await frames(5)
			ok(not g.alive, "S7 guardian defeated")
		await kill_all()
	await frames(60)
	await flush()
	# ---- Scene 8
	ok(await wait_loaded(8), "Scene 8 (merged city) loaded")
	await flush()
	ok(RealityManager.merged, "S8 realities merged")
	await settle("S8 spawn")
	await shot("S8 spawn")
	var m8 := interactables("Mira")[0] as Interactable
	await use_at(m8, "S8 Mira")
	await goto(Vector3(-78, 6, 352), "S8 promenade viewpoint")
	await frames(20)
	await flush()
	await frames(60)
	ok(hud._overlay_mode == "credits", "Credits rolled")
	print("TEST SUMMARY: %d failure(s)" % fails)
	get_tree().quit(1 if fails > 0 else 0)


class CityStreetsPos:
	static func wave2() -> Vector3:
		return Vector3(-104 - 14, 4.8, 251.42)
