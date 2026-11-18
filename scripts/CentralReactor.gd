extends Location
## CentralReactor.tscn — Location 4 (Zion). Rooms R1 Control Hall -> R2 Turbine Chasm -> R3 Convergence Chamber,
## placed 100 m apart and linked by blast doors (fade + move).
## Scene 6 "The Breaking Point": instability rises on its own; fight through drones, read Voss's log, reach R3.
##   At 100 instability (not yet critical) the reactor bleeds your health.
## Scene 7 "The Heart of the Fracture": confront Dr. Voss, fight the guardian, hold [E] on 3 convergence
##   nodes before instability hits the critical limit (lose condition).
## Reads EnemyAI + InstabilityManager per the architecture.

const R1 := Vector3(0, 0, 0)
const R2 := Vector3(100, 0, 0)
const R3 := Vector3(200, 0, 0)

var r1: Node3D
var r2: Node3D
var r3: Node3D
var guardian: EnemyAI
var nodes_done := 0
var _shield_gen := 0
var _log_read := false
var _r2_cleared := false
var _hurt_t := 0.0


func scene_titles() -> Dictionary:
	return {6: "The Breaking Point", 7: "The Heart of the Fracture"}


func start(n: int) -> void:
	kill_y = -14.0
	environment(Color(0.03, 0.03, 0.06), Color(0.75, 0.78, 0.95), 0.8, 0.6)
	r1 = load_room("R1_ReactorControlHall", R1)
	r2 = load_room("R2_TurbineChasm", R2)
	r3 = load_room("R3_ConvergenceChamber", R3)
	var fx := load_room("R3_ConvergenceChamber_FX", R3, RealityManager.Reality.VEYRA)
	fx.name = "R3_FX"
	for base in [R1, R2, R3]:
		omni(base + Vector3(0, 7, 0), Color(0.85, 0.9, 1.0), 2.2, 26.0)
		omni(base + Vector3(-10, 4, 0), Color(0.85, 0.9, 1.0), 1.0, 14.0)
		omni(base + Vector3(10, 4, 0), Color(0.85, 0.9, 1.0), 1.0, 14.0)
	omni(R3 + Vector3(0, 3, 0), Palette.CYAN, 3.0, 12.0)
	await get_tree().physics_frame
	if n <= 6:
		_scene6()
	else:
		_scene7()


func _physics_process(delta: float) -> void:
	super(delta)
	if player == null or player.dead:
		return
	# Scene 6: maxed instability burns the player (only Scene 7 can be lost to "critical")
	if not InstabilityManager.critical_enabled and InstabilityManager.value >= InstabilityManager.MAX:
		_hurt_t += delta
		player.take_damage(5.0 * delta, null, true)
		if _hurt_t > 2.0:
			_hurt_t = 0.0
			toast("Instability is maxed and the reactor is burning you! Defeat enemies to lower it.", 2.0)


# ---------------------------------------------------------------- Scene 6

func _scene6() -> void:
	set_scene(6, "Fight through the reactor control hall.")
	InstabilityManager.rise_per_sec = 0.55
	place_player(R1 + Palette.bl(-12, -3, 0), -PI / 2)
	say([
		["Mira", "(through the seam) Can you hear me? I made it to the reactor's Veyra side. Things from both worlds are tangled together in here."],
		["You", "I can feel the instability climbing. It's spreading through everything."],
		["Mira", "My grandmother told stories about this place. Our worlds weren't always two. They were split, on purpose, a long time ago."],
		["Mira", "Defeating the guards seems to calm the reactor. Don't let it boil over."],
	], func():
		objective("Defeat the reactor guards. Watch the instability meter.")
		spawn_wave([R1 + Vector3(-3, 2.5, 1), R1 + Vector3(2, 2.5, 3), R1 + Vector3(5, 3, -2), R1 + Vector3(0, 3, -4)], _r1_cleared))


func _r1_cleared() -> void:
	objective("Go through the east blast door to the turbine chasm.")
	_open_doors(r1, "ToR2")
	var exit := R1 + Palette.bl(12, -3, 0)
	exit_marker(exit)
	trigger(exit, 2.2, _to_r2)


func _open_doors(room: Node3D, tag: String) -> void:
	for n in room.find_children("*BlastDoor_%s_Leaf*" % tag, "Node3D", true, false):
		var ex: Dictionary = n.get_meta("extras", {})
		var off := float(ex.get("open_offset_m", 1.9))
		var tw := create_tween()
		tw.tween_property(n, "position", (n as Node3D).position + (n as Node3D).transform.basis.x.normalized() * off, 1.0)


func _to_r2() -> void:
	await hud.fade_out(0.3)
	place_player(R2 + Palette.bl(-19, 0, 0), -PI / 2)
	await hud.fade_in(0.4)
	objective("Cross the turbine chasm on the root bridge. Don't fall.")
	spawn_wave([R2 + Vector3(-6, 2.5, -4), R2 + Vector3(0, 2.5, -3), R2 + Vector3(6, 2.5, -4)], func():
		_r2_cleared = true
		objective("Search the far end of the chasm."))
	var log_pos := floor_near(R2 + Palette.bl(18.4, 1.2, 0), 2.5)
	var it := interactable(log_pos, "Read Dr. Voss's research log", _read_log, -1, 0.0, 2.4)
	var term := Palette.box(Vector3(0.8, 1.2, 0.4), Palette.CHARCOAL)
	term.position.y = 0.6
	it.add_child(term)
	var scr := Palette.box(Vector3(0.6, 0.4, 0.05), Palette.CYAN, 2.5)
	scr.position = Vector3(0, 1.0, -0.22)
	it.add_child(scr)


func _read_log(_i: Interactable) -> void:
	_log_read = true
	say([
		["Log", "VOSS, PERSONAL LOG: The original separation held for a century, but the seam is wearing thin. Veyra keeps leaking back in."],
		["Log", "The stabilizers buy time. The convergence chamber can do better: a permanent cut. Nova safe forever."],
		["Log", "Projected effect on the Veyra side: total collapse. Regrettable. Necessary."],
		["You", "The 'experiment' was never about reading the seam. He wanted to sever it and let Veyra die."],
		["Mira", "(through the seam) Then we stop him. The chamber is just ahead."],
	], func():
		objective("Enter the convergence chamber.")
		var exit := R2 + Palette.bl(20, 0, 0)
		exit_marker(exit, Palette.VIOLET)
		trigger(exit, 2.4, _to_r3))


func _to_r3() -> void:
	await hud.fade_out(0.4)
	clear_enemies()
	await get_tree().process_frame
	_scene7()
	await hud.fade_in(0.5)


# ---------------------------------------------------------------- Scene 7

func _scene7() -> void:
	set_scene(7, "Confront Dr. Voss.")
	InstabilityManager.rise_per_sec = 0.0
	InstabilityManager.value = maxf(InstabilityManager.value, 30.0)
	place_player(R3 + Palette.bl(-12.8, 0, 0), -PI / 2)
	var voss := npc(R3 + Palette.bl(-6.5, 0, 0), "Dr. Voss", Palette.SILVER, func(_i): pass, -1, -PI / 2)
	voss.enabled = false
	trigger(R3 + Palette.bl(-6.5, 0, 0), 4.5, func(): _confront(voss))


func _confront(voss: Interactable) -> void:
	say([
		["Dr. Voss", "So you found the log. Then you know there's no time left for debate."],
		["You", "There are people in Veyra, Doctor. Families. You've been killing them a district at a time."],
		["Dr. Voss", "Two realities can't hold one space. Either we cut the seam cleanly, or both worlds tear apart together."],
		["You", "Or we stop pulling them apart. Let them converge. Let them coexist."],
		["Dr. Voss", "Coexist? You've seen the instability. Convergence is a gamble with every life in both cities."],
		["You", "Severing it is a guarantee that half of them die. I'll take the gamble."],
		["Dr. Voss", "Then you leave me no choice. GUARDIAN: defend the core!"],
	], func():
		voss.queue_free()
		_start_boss())


func _start_boss() -> void:
	objective("Activate the convergence nodes (0 / 3) and defeat the guardian before instability goes critical.")
	InstabilityManager.critical_enabled = true
	InstabilityManager.rise_per_sec = 0.9
	guardian = EnemyAI.make_guardian()
	add_child(guardian)
	guardian.home = R3
	guardian.hover = 1.6
	guardian.global_position = R3 + Vector3(0, 4, 5.5)
	enemies.append(guardian)
	guardian.died.connect(func(_g): _check_win())
	var specs := [["A", Palette.bl(0, 7.6, 0)], ["B", Palette.bl(-6.58, -3.8, 0)], ["C", Palette.bl(6.58, -3.8, 0)]]
	for s in specs:
		var pos := Location.node_pos(r3, "SM_ConvergenceNode_%s" % s[0], R3 + s[1])
		var it := interactable(Vector3(pos.x, 0, pos.z), "Activate convergence node %s" % s[0], _on_convergence, -1, 2.5, 2.6)
		it.marker_height = 2.6
		it.set_meta("light", beacon(Vector3(pos.x, 0, pos.z) + Vector3(0, 2.0, 0), Palette.AMBER, 0.4))
	toast("The guardian is shielded. Each convergence node you activate breaks its shield for 10 s.", 5.0)


func _on_convergence(it: Interactable) -> void:
	nodes_done += 1
	var l: MeshInstance3D = it.get_meta("light")
	(l.material_override as StandardMaterial3D).albedo_color = Palette.VIOLET
	(l.material_override as StandardMaterial3D).emission = Palette.VIOLET
	InstabilityManager.add(-25.0)
	hud.flash(Palette.VIOLET, 0.4)
	objective("Activate the convergence nodes (%d / 3) and defeat the guardian before instability goes critical." % nodes_done)
	if is_instance_valid(guardian) and guardian.alive:
		guardian.shield = false
		_shield_gen += 1
		if nodes_done >= 3:
			toast("All nodes converged. The guardian's shield is gone for good. Finish it!", 4.0)
		else:
			toast("Shield down! Strike the guardian now (10 s).", 3.0)
			var gen := _shield_gen
			get_tree().create_timer(10.0, false).timeout.connect(func():
				if gen == _shield_gen and is_instance_valid(guardian) and guardian.alive and nodes_done < 3:
					guardian.shield = true
					toast("The guardian's shield is back up."))
		# reinforcements
		spawn_drone(R3 + Vector3(8, 3, 8))
		spawn_drone(R3 + Vector3(-8, 3, -8))
	_check_win()


func _check_win() -> void:
	if nodes_done < 3:
		return
	if is_instance_valid(guardian) and guardian.alive:
		return
	InstabilityManager.critical_enabled = false
	InstabilityManager.rise_per_sec = 0.0
	clear_enemies()
	say([
		["Dr. Voss", "(from the core) No... the seam is closing the wrong way. They're... merging."],
		["Mira", "(her voice is clear now, no static) I can see you. Actually see you, standing in the same room."],
		["You", "The realities are converging. Nova and Veyra, together."],
		["Dr. Voss", "...Then I hope you're right. For all our sakes."],
	], func():
		hud.flash(Color.WHITE, 1.5)
		RealityManager.set_merged(true)
		await get_tree().create_timer(1.0).timeout
		completed.emit())
