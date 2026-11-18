extends Location
## ResearchFacility.tscn — Location 1 (Hali). Rooms: N1 Research Facility (Nova) / V1 Reclaimed Facility (Veyra).
## Scene 1 "The Experiment": talk to Dr. Voss, activate the three consoles -> explosion.
## Scene 2 "The First Shift": learn Reality Shift + Fracture Energy, get past the blocked exit, escape.

const NOVA := RealityManager.Reality.NOVA
const VEYRA := RealityManager.Reality.VEYRA

var nova_room: Node3D
var consoles_done := 0
var console_lights: Array = []
var voss: Interactable
var barrier: Structure
var debris: Array = []
var _met_voss := false
var _first_veyra := false
var _energy_hint := false


func scene_titles() -> Dictionary:
	return {1: "The Experiment", 2: "The First Shift"}


func start(n: int) -> void:
	environment(Color(0.04, 0.06, 0.08), Color(0.78, 0.86, 0.95), 0.85, 0.7)
	nova_room = load_room("N1_ResearchFacility", Vector3.ZERO, NOVA)
	load_room("V1_ReclaimedResearchFacility", Vector3.ZERO, VEYRA)
	omni(Vector3(0, 7, 0), Color(0.85, 0.95, 1.0), 2.0, 20.0)
	omni(Vector3(-9, 4, 3), Color(0.9, 0.95, 1.0), 1.2, 14.0)
	omni(Vector3(9, 4, 3), Color(0.9, 0.95, 1.0), 1.2, 14.0)
	omni(Vector3(0, 3, 6), Palette.CYAN, 1.0, 8.0)
	RealityManager.set_reality(NOVA)
	if n <= 1:
		_scene1()
	else:
		_scene2(true)


# ---------------------------------------------------------------- Scene 1

func _scene1() -> void:
	set_scene(1, "Talk to Dr. Voss.")
	place_player(Palette.bl(0, -7.4, 0), 0.0)
	player.reality_shift.locked = true
	voss = npc(Palette.bl(-5.0, -3.2, 0), "Dr. Voss", Palette.SILVER, _talk_voss, -1, deg_to_rad(-120))
	var fallbacks := [Palette.bl(-2.6, -4.503, 0), Palette.bl(0, -5.2, 0), Palette.bl(2.6, -4.503, 0)]
	for i in 3:
		var pos := Location.node_pos(nova_room, "SM_Console_0%d" % (i + 1), fallbacks[i])
		pos.y = 0.0
		var it := interactable(pos, "Activate console %d" % (i + 1), _on_console, NOVA, 0.0, 2.1)
		it.enabled = false
		it.marker_height = 1.9
		var light := beacon(pos + Vector3(0, 1.3, 0), Palette.AMBER, 0.3)
		console_lights.append(light)
		it.set_meta("index", i)


func _talk_voss(_i: Interactable) -> void:
	if not _met_voss:
		_met_voss = true
		say([
			["Dr. Voss", "There you are. The resonance vessel is charged, and today we find out whether my life's work holds together."],
			["You", "Remind me what we're actually trying to prove?"],
			["Dr. Voss", "That reality has a seam. Nova sits on one side of it. If we can read that seam, we can reinforce it and keep the city stable forever."],
			["You", "The overnight logs showed energy readings that weren't ours. Something answering from the other side of the vessel."],
			["Dr. Voss", "Echoes. Instrument noise. ...Probably. Bring the three consoles online and we'll see for ourselves."],
		], func():
			objective("Activate the consoles (0 / 3).")
			for it in get_tree().get_nodes_in_group("interactable"):
				if it.has_meta("index"):
					it.enabled = true)
	elif consoles_done < 3:
		say([["Dr. Voss", "Three consoles, three phases. Don't keep the vessel waiting."]])


func _on_console(it: Interactable) -> void:
	var i: int = it.get_meta("index")
	var light: MeshInstance3D = console_lights[i]
	var m := light.material_override as StandardMaterial3D
	m.albedo_color = Palette.CYAN
	m.emission = Palette.CYAN
	consoles_done += 1
	objective("Activate the consoles (%d / 3)." % consoles_done)
	match consoles_done:
		1:
			say([["Dr. Voss", "Phase one is stable. Readings are nominal..."]])
		2:
			say([["Dr. Voss", "Phase two. Wait. That spike again, those are the readings from the logs. Keep going, carefully."]])
		3:
			say([
				["Dr. Voss", "Phase three online. Containment at... no. No, that's impossible, the field is folding inward!"],
				["You", "Doctor, the vessel is splitting! I can see something through it, a forest?"],
				["Dr. Voss", "Get away from the core! GET DOWN!"],
			], _explosion)


func _explosion() -> void:
	hud.flash(Palette.VIOLET, 1.2)
	FX.sphere(self, Vector3(0, 2, 0), 18.0, Palette.VIOLET, 1.0)
	player.control_enabled = false
	await get_tree().create_timer(0.6).timeout
	await hud.fade_out(0.8)
	voss.queue_free()
	await get_tree().create_timer(0.8).timeout
	_scene2(false)
	await hud.fade_in(1.2)


# ---------------------------------------------------------------- Scene 2

func _scene2(direct: bool) -> void:
	set_scene(2, "Get your bearings.")
	player.control_enabled = true
	player.reality_shift.locked = false
	if direct:
		for i in 3:
			beacon(Palette.bl([-2.6, 0.0, 2.6][i], [-4.503, -5.2, -4.503][i], 1.3), Palette.CYAN, 0.3)
	place_player(Palette.bl(-4.0, -6.6, 0), deg_to_rad(20))
	# damaged lab (Nova): debris has sealed the main exit
	debris.append(blocker(Palette.bl(0, -8.1, 1.5), Vector3(5.5, 3.0, 1.4), Palette.CHARCOAL, NOVA))
	debris.append(blocker(Palette.bl(-1.8, -7.0, 0.5), Vector3(1.6, 1.0, 1.2), Palette.SILVER.darkened(0.4), NOVA))
	debris.append(blocker(Palette.bl(1.6, -7.2, 0.4), Vector3(1.2, 0.8, 1.6), Palette.CHARCOAL, NOVA))
	omni(Palette.bl(0, -7.5, 1.0), Palette.AMBER, 2.0, 7.0)
	# Veyra: the way is open, but a fracture crystal grew across the doorway
	barrier = structure(Palette.bl(0, -8.3, 1.5), Vector3(4.8, 3.0, 0.5), Palette.VIOLET, Structure.Mode.COLLAPSE, 100.0, VEYRA, "fracture crystal")
	barrier.burst_only = true
	barrier.collapsed.connect(func(_s):
		objective("Escape through the main exit.")
		say([["Dr. Voss", "(over the comm) The crystal shattered! The exit is clear, go, go!"]]))
	# Fracture shards only exist in Veyra
	for p in [Palette.bl(-7, -5, 0), Palette.bl(7, 3, 0), Palette.bl(-11.8, 6.0, 4.53), Palette.bl(6, -6.5, 0)]:
		var pk := Pickup.make_energy(15.0, VEYRA)
		add_child(pk)
		pk.global_position = p
	exit_marker(Palette.bl(0, -8.7, 0), Palette.CYAN)
	trigger(Palette.bl(0, -8.6, 0), 1.9, _escape, false, VEYRA)
	RealityManager.reality_changed.connect(_on_reality)
	player.fracture.changed.connect(_on_energy)
	say([
		["You", "...ugh. My ears are ringing. Doctor? Dr. Voss!"],
		["Dr. Voss", "(over the comm, static) ...can you hear me? I'm... somewhere else. The blast threw me through the seam."],
		["You", "The lab is wrecked. Debris has buried the main exit."],
		["Dr. Voss", "Listen. The vessel's energy passed through you. Your readings show you are anchored to BOTH sides of the seam."],
		["Dr. Voss", "Focus on the other place you saw, the overgrown one. We called it Veyra in the theory papers. Try to step into it. [Q]"],
	], func(): objective("Use Reality Shift [Q] to step into Veyra."))


func _on_reality(r: int) -> void:
	if r == VEYRA and not _first_veyra and scene_no == 2:
		_first_veyra = true
		say([
			["You", "It's the same lab, but it's been abandoned for decades. Roots everywhere. And the debris is gone."],
			["Dr. Voss", "Two realities layered in the same space. The doorway is blocked by a fracture crystal, though. Do you see the violet shards on the floor?"],
			["Dr. Voss", "That's Fracture Energy. Collect it, then release it all at once [F]. It should shatter the crystal. Shards only appear on the Veyra side."],
		], func(): objective("Collect Fracture Energy in Veyra (%d / 40)." % int(player.fracture.energy)))


func _on_energy(v: float) -> void:
	if scene_no != 2 or barrier == null or barrier.broken:
		return
	if v >= FractureEnergy.BURST_COST:
		if not _energy_hint:
			_energy_hint = true
			toast("Enough energy! Stand near the crystal in Veyra and press [F].")
		objective("Shatter the fracture crystal at the main exit with a Fracture Burst [F] (within 4 m).")
	elif _first_veyra:
		objective("Collect Fracture Energy in Veyra (%d / 40)." % int(v))


func _escape() -> void:
	if barrier and not barrier.broken:
		return
	for t in _triggers:
		t.active = false
	say([
		["You", "I'm out. There's daylight ahead, the city."],
		["Dr. Voss", "Good. The surge didn't stop at the lab. Head into the streets; I'll guide you as best I can."],
	], func(): completed.emit())
