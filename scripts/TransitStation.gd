extends Location
## TransitStation.tscn — Location 3 (Megan). Rooms: N2 Transit Station (Nova) / V2 Flooded Station (Veyra).
## Scene 4 "The Forgotten Station": manipulate structures, power 3 nodes, reach the control room, run the
##   stabilizer (protects Nova, damages Veyra).
##   Node 01: an electrified field powered by three linked unstable conduits -> Chain Reaction [G] (or E each).
##   Node 02: sealed behind a Nova security shutter -> reach it from Veyra.
##   Node 03: caged behind an unstable wall -> Structural Manipulation [E] x4.
## Scene 5 "Someone on the Other Side": locked in Veyra, investigate the damage, meet Mira -> reactor.

const NOVA := RealityManager.Reality.NOVA
const VEYRA := RealityManager.Reality.VEYRA

var nova_room: Node3D
var veyra_room: Node3D
var nodes_on := 0
var node_lights: Array = []
var stabilizer: Interactable
var clues := 0
var mira: Interactable
var _mira_stage := 0


func scene_titles() -> Dictionary:
	return {4: "The Forgotten Station", 5: "Someone on the Other Side"}


func start(n: int) -> void:
	kill_y = -12.0
	environment(Color(0.05, 0.07, 0.09), Color(0.78, 0.84, 0.92), 0.85, 0.7)
	nova_room = load_room("N2_TransitStation", Vector3.ZERO, NOVA)
	veyra_room = load_room("V2_FloodedTransitStation", Vector3.ZERO, VEYRA)
	for p in [Vector3(12, 6, 0), Vector3(-4, 8, 0), Vector3(-14, 8, -4), Vector3(4, 6, 6), Vector3(14, 6, -7)]:
		omni(p, Color(0.9, 0.95, 1.0), 1.3, 16.0)
	await get_tree().physics_frame
	if n <= 4:
		_scene4()
	else:
		_scene5()


# ---------------------------------------------------------------- Scene 4

func _scene4() -> void:
	set_scene(4, "Listen to Dr. Voss.")
	RealityManager.set_reality(NOVA)
	place_player(Palette.bl(18, -6.0, 0), PI / 2)
	_build_node1()
	_build_node2()
	_build_node3()
	stabilizer = interactable(Palette.bl(-4, 7.5, 5), "Activate the reality stabilizer", _activate_stabilizer, -1, 1.5, 2.6)
	stabilizer.enabled = false
	beacon(Palette.bl(-4, 7.5, 5) + Vector3(1.2, 0, 0), Palette.AMBER, 1.6)
	say([
		["Dr. Voss", "(comm) The transit station. Before the accident this was the anchor point for the city's reality stabilizer."],
		["Dr. Voss", "The stabilizer clamps the seam shut around Nova. Power its three nodes, then start it from the control room upstairs."],
		["You", "The station looks wrecked on both sides. Unstable supports everywhere."],
		["Dr. Voss", "Then use them. Press [E] near an unstable structure to stress it, and four strains will bring it down. [G] sends a pulse through every linked structure within six metres."],
		["Dr. Voss", "Careful, though. Every extra reaction in a chain adds instability to the area."],
	], func(): objective("Power the three nodes (0 / 3), then reach the control room."))


func _node_pos(i: int, fb: Vector3) -> Vector3:
	return Location.node_pos(nova_room, "SM_PowerNode_0%d" % i, fb)


func _make_node(i: int, pos: Vector3, reality := -1) -> Interactable:
	var it := interactable(pos, "Power node %02d" % i, _on_node, reality, 1.0, 2.4)
	it.marker_height = 2.2
	var l := beacon(pos + Vector3(0, 1.8, 0), Palette.AMBER, 0.4)
	node_lights.append(l)
	it.set_meta("light", l)
	return it


func _build_node1() -> void:
	var p := _node_pos(1, Palette.bl(6, -8.9, 0))
	var floor_p := Vector3(p.x, 0, p.z)
	var it := _make_node(1, floor_p)
	it.enabled = false
	var conduits: Array = []
	for off in [Vector3(-2.8, 0.75, -1.6), Vector3(2.8, 0.75, -1.6), Vector3(0, 0.75, -3.2)]:
		var s := structure(floor_p + off, Vector3(0.6, 1.5, 0.6), Palette.SILVER, Structure.Mode.MACHINERY, 25.0, -1, "overloaded conduit")
		conduits.append(s)
	for s in conduits:
		for o in conduits:
			if o != s:
				s.linked.append(o)
	var hz := Hazard.new()
	hz.radius = 2.2
	hz.height = 3.0
	hz.dps = 25.0
	hz.sources = conduits
	add_child(hz)
	hz.global_position = floor_p
	var cb := func(_s):
		if not hz.active and not it.get_meta("unlocked", false):
			it.set_meta("unlocked", true)
			it.enabled = true
			toast("The electrified field around node 01 collapsed.")
	for s in conduits:
		(s as Structure).collapsed.connect(func(x): cb.call(x), CONNECT_DEFERRED)


func _build_node2() -> void:
	var p := _node_pos(2, Palette.bl(-12.5, 9, 5))
	_make_node(2, p)
	# Nova security shutter boxes the node in; it does not exist in Veyra.
	var c := Palette.SILVER.darkened(0.2)
	blocker(p + Vector3(0, 1.3, 1.5), Vector3(3.2, 2.6, 0.2), c, NOVA)
	blocker(p + Vector3(-1.6, 1.3, 0.2), Vector3(0.2, 2.6, 2.6), c, NOVA)
	blocker(p + Vector3(1.6, 1.3, 0.2), Vector3(0.2, 2.6, 2.6), c, NOVA)
	var sign := Label3D.new()
	sign.text = "SECURITY LOCKDOWN"
	sign.modulate = Palette.AMBER
	sign.font_size = 48
	add_child(sign)
	sign.global_position = p + Vector3(0, 2.0, 1.65)
	RealityManager.register_layer(sign, NOVA)


func _build_node3() -> void:
	var p := _node_pos(3, Palette.bl(16, 8.6, 0))
	var floor_p := Vector3(p.x, 0, p.z)
	_make_node(3, floor_p)
	var c := Palette.CHARCOAL
	structure(floor_p + Vector3(0, 1.25, 1.5), Vector3(3.2, 2.5, 0.3), Palette.VCONCRETE, Structure.Mode.COLLAPSE, 100.0, -1, "collapsed support wall")
	blocker(floor_p + Vector3(-1.6, 1.25, 0.3), Vector3(0.3, 2.5, 2.4), c)
	blocker(floor_p + Vector3(1.6, 1.25, 0.3), Vector3(0.3, 2.5, 2.4), c)


func _on_node(it: Interactable) -> void:
	var l: MeshInstance3D = it.get_meta("light")
	var m := l.material_override as StandardMaterial3D
	m.albedo_color = Palette.CYAN
	m.emission = Palette.CYAN
	nodes_on += 1
	objective("Power the three nodes (%d / 3), then reach the control room." % nodes_on)
	if nodes_on == 1:
		say([
			["You", "Node online. Doctor, when I broke that wall in Nova, the same wall in Veyra cracked too."],
			["Dr. Voss", "(comm) The two sides share structure at this anchor point. Push on one and the other feels it."],
			["You", "So everything we do here hurts somebody over there?"],
			["Dr. Voss", "(comm) ...Let's focus on the nodes."],
		])
	elif nodes_on == 3:
		stabilizer.enabled = true
		objective("All nodes powered. Activate the stabilizer in the upstairs control room.")
		say([["Dr. Voss", "(comm) All three nodes are live! Get to the control room. Upstairs, west side."]])


func _activate_stabilizer(_i: Interactable) -> void:
	say([
		["Dr. Voss", "(comm) Stabilizer spinning up. Nova's grid is locking back into phase. It's working!"],
		["You", "Wait. Something's wrong. The Veyra side, the walls are crumbling, the water's rising."],
		["Dr. Voss", "(comm) An acceptable side effect. The stabilizer pulls its strength from the other reality."],
		["You", "You knew? Doctor? Doctor!"],
	], _stabilizer_fx)


func _stabilizer_fx() -> void:
	hud.flash(Palette.CYAN, 1.0)
	FX.sphere(self, Palette.bl(-4, 7.5, 5.5), 30.0, Palette.CYAN, 1.2)
	await get_tree().create_timer(0.8).timeout
	await hud.fade_out(0.6)
	_scene5()
	await hud.fade_in(0.8)


# ---------------------------------------------------------------- Scene 5

func _scene5() -> void:
	set_scene(5, "Investigate the damaged Veyra station.")
	RealityManager.set_reality(VEYRA)
	player.reality_shift.locked = true
	player.reality_shift.lock_reason = "The stabilizer has pinned the seam shut. You are stuck in Veyra."
	if stabilizer:
		stabilizer.enabled = false
	place_player(ground(Palette.bl(-6.5, 6.0, 5.2)), PI)
	# stabilizer damage in Veyra: collapsed debris + flicker lights
	for p in [Palette.bl(2, 2, 0.6), Palette.bl(-6, -2, 0.6), Palette.bl(10, 4, 0.6)]:
		blocker(p, Vector3(1.6, 1.2, 1.4), Palette.VCONCRETE.darkened(0.3), VEYRA)
	omni(Palette.bl(6, -8.0, 1.5), Palette.AMBER, 1.5, 6.0)
	var clue_defs := [
		[Location.node_pos(veyra_room, "SM_PowerNode_01", Palette.bl(6, -8.9, 0)), "Inspect the drained power node", [
			["You", "This node is completely dark, burned out from the inside. It's the twin of the one I powered in Nova."],
			["You", "The stabilizer didn't make that energy. It took it from here."]]],
		[Location.node_pos(veyra_room, "SM_PowerNode_03", Palette.bl(16, 8.6, 0)), "Inspect the cracked generator bay", [
			["You", "The cracks are fresh. Same pattern as the wall I brought down, only far worse."]]],
		[Palette.bl(-9.5, 0, 0), "Inspect the survivors' belongings", [
			["You", "Blankets, lanterns, a child's drawing of the station. People were living here, today."],
			["You", "They left in a hurry."]]],
	]
	for c in clue_defs:
		var pos: Vector3 = c[0]
		var lines: Array = c[2]
		var it := interactable(ground(Vector3(pos.x, pos.y + 0.5, pos.z)), c[1], func(_i): _on_clue(lines), VEYRA, 0.0, 2.4)
		it.marker_height = 1.6
	mira = npc(ground(Palette.bl(-9.5, 7.5, 5.2)), "Mira", Palette.FOREST, _talk_mira, VEYRA, deg_to_rad(-90))
	say([
		["You", "The water's higher than before. Everything is cracking."],
		["Mira", "Don't move! You... you're one of them. A Nova ghost. Your stabilizer just tore the east platform in half."],
	], func():
		_mira_stage = 1
		objective("Talk to the stranger."))


func _talk_mira(_i: Interactable) -> void:
	match _mira_stage:
		0, 1:
			_mira_stage = 2
			say([
				["Mira", "I'm Mira. This is Veyra. It's not a theory or an echo, it's my home, and people live here."],
				["You", "I didn't know. I was told this place was empty. A reflection."],
				["Mira", "Every time your city 'stabilizes', ours loses a district. We call them the quiet storms."],
				["Mira", "If you don't believe me, look around. Look at what your machine just did."],
			], func(): objective("Investigate the damage (%d / 3), then speak with Mira." % clues))
		2:
			if clues < 3:
				say([["Mira", "Look around first. Then tell me Veyra isn't real."]])
			else:
				_mira_stage = 3
				say([
					["You", "I saw it. The nodes, the cracks, the shelter. I'm sorry."],
					["Mira", "Sorry won't stop the next storm. The stabilizers are only the outer ring of it."],
					["Mira", "Everything feeds into the central reactor, where the seam was first cut. Whatever your doctor is planning, it's happening there."],
					["Mira", "Take the west tunnel. I'll find my own way and meet you near the reactor."],
				], func():
					objective("Head through the west tunnel to the Central Reactor.")
					exit_marker(ground(Palette.bl(-17.0, 7, 0.5)), Palette.FOREST.lightened(0.4))
					trigger(Palette.bl(-17.0, 7, 0), 2.6, func(): completed.emit()))
		_:
			say([["Mira", "The west tunnel. Go."]])


func _on_clue(lines: Array) -> void:
	clues += 1
	say(lines, func():
		if _mira_stage >= 2:
			objective("Investigate the damage (%d / 3), then speak with Mira." % clues)
		if clues >= 3:
			objective("Speak with Mira."))
