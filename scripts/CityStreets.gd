extends Location
## CityStreets.tscn — Location 2 (Kayla), reused for the ending.
## Uses the team's Nova / Veyra city meshes from playtest/worlds (same coordinates as playtest/crossing.gd).
## Scene 3 "A City Out of Place": hostile security drones -> Combat + Defensive Counter (+ Echo / Recall).
##   Drones behave differently per reality (Nova: armoured, ranged; Veyra: feral melee). Reach the station.
## Scene 8 "A World Reborn": merged city, talk with Mira, reach the final viewpoint -> credits.

const NOVA := RealityManager.Reality.NOVA
const VEYRA := RealityManager.Reality.VEYRA
const CITY_NOVA := "res://playtest/worlds/nova.glb"
const CITY_VEYRA := "res://playtest/worlds/veyra.glb"

# route points from playtest/crossing.gd
const STATION_CRYSTAL := Vector3(-161.28, 6, 229.42)
const STATION_EAST := Vector3(-135.5, 6, 251.42)
const FRACTURE := Vector3(-104, 4.5, 251.42)
const PROMENADE := Vector3(-78, 6, 352)
const PROMENADE_LINK := Vector3(-91.1, 5.1, 352)

var _waves_cleared := 0
var _saw_both_modes := {}
var _discovered := false
var _mira_talked := false


func scene_titles() -> Dictionary:
	return {3: "A City Out of Place", 8: "A World Reborn"}


func start(n: int) -> void:
	kill_y = -20.0
	if n >= 8:
		environment(Color(0.55, 0.62, 0.78), Color(0.95, 0.9, 1.0), 0.95, 1.1)
	else:
		environment(Color(0.40, 0.58, 0.70), Color("#e5f1ff"), 0.85, 1.0)
	var merged := n >= 8
	var nova := load_city(CITY_NOVA, NOVA, not merged)
	var veyra := load_city(CITY_VEYRA, VEYRA, true)
	if nova == null or veyra == null:
		_fallback_city()
	_promenade_link()
	await get_tree().physics_frame
	await get_tree().physics_frame
	if merged:
		_scene8()
	else:
		_scene3()


func _promenade_link() -> void:
	var link := StaticBody3D.new()
	add_child(link)
	link.position = PROMENADE_LINK
	link.rotation.z = atan2(1.5, 8.0)
	var m := Palette.box(Vector3(8.5, 0.3, 4.0), Color("#94a9ad"))
	link.add_child(m)
	var cs := CollisionShape3D.new()
	var bs := BoxShape3D.new()
	bs.size = Vector3(8.5, 0.3, 4.0)
	cs.shape = bs
	link.add_child(cs)


func _fallback_city() -> void:
	## If the LFS city meshes are missing, build a simple street so the scene stays playable.
	toast("City meshes not found (run `git lfs pull`). Using a placeholder street.", 6.0)
	var floor_body := blocker(Vector3(-120, 3.5, 290), Vector3(120, 1, 160), Palette.CHARCOAL)
	floor_body.position.y = FRACTURE.y - 0.5
	for i in 8:
		blocker(Vector3(-160 + i * 12, 10, 236), Vector3(8, 12, 6), Palette.SILVER, NOVA)
		blocker(Vector3(-160 + i * 12, 7, 266), Vector3(6, 6, 6), Palette.VCONCRETE, VEYRA)


# ---------------------------------------------------------------- Scene 3

func _scene3() -> void:
	set_scene(3, "Find out what is happening in the city.")
	RealityManager.set_reality(NOVA)
	place_player(ground(FRACTURE + Vector3(0, 0.5, 0)), PI / 2)
	RealityManager.reality_changed.connect(_note_reality)
	say([
		["You", "The streets... half the buildings are flickering. I can see the overgrown city bleeding through."],
		["Dr. Voss", "(comm) The surge spread across the whole district. Every system tied to the city grid is failing."],
		["Dr. Voss", "Including security. The patrol drones have lost their identification layer; they're flagging everything as a threat."],
		["You", "Including me. I can hear them coming."],
		["Dr. Voss", "Defend yourself. Strike [LMB] in combos. Raise your guard [RMB] just before a hit lands to counter, then strike back hard."],
	], _wave1)


func _wave1() -> void:
	objective("Defeat the security drones (wave 1).")
	_saw_both_modes[RealityManager.active] = true
	var c := FRACTURE
	spawn_wave([c + Vector3(-8, 3, 3), c + Vector3(-9, 3, -3), c + Vector3(-12, 3, 0)], _wave1_cleared)


func _wave1_cleared() -> void:
	say([
		["You", "That's the first patrol down."],
		["Dr. Voss", "(comm) More are converging near the transit station entrance to the west. That's where you need to go."],
		["Dr. Voss", "One more thing: your neural trace shows a residual echo. Project it [C] and it replays your last few seconds. Drones may chase it."],
		["Dr. Voss", "And if you get cornered, Rift Recall [V] pulls you back to the echo, or a few seconds back along your path. It costs 25 Fracture Energy."],
	], func():
		objective("Fight your way to the transit station entrance (west).")
		trigger(FRACTURE + Vector3(-14, 0, 0), 6.0, _wave2))


func _wave2() -> void:
	objective("Defeat the drones guarding the station (wave 2). Try shifting realities mid-fight.")
	var c := STATION_EAST
	spawn_wave([c + Vector3(6, 3, 4), c + Vector3(8, 3, -4), c + Vector3(3, 3, 6), c + Vector3(10, 3, 0)], _wave2_cleared)


func _note_reality(r: int) -> void:
	if scene_no != 3:
		return
	for e in enemies:
		if is_instance_valid(e) and (e as EnemyAI).alive and (e as EnemyAI).state == EnemyAI.State.CHASE:
			_saw_both_modes[r] = true
	if _saw_both_modes.size() >= 2 and not _discovered:
		_discover()


func _discover() -> void:
	_discovered = true
	say([
		["You", "Wait, did you see that? In Nova they keep their distance and shoot. In Veyra they lose their armour and charge at me."],
		["Dr. Voss", "(comm) Fascinating. The drones are built for Nova's rules. In Veyra their targeting decays into something... feral."],
		["Dr. Voss", "Use it. Shift to Veyra to strip their armour, or stay in Nova to keep them at range."],
	])


func _wave2_cleared() -> void:
	var lines := [["You", "The entrance is clear."]]
	if not _discovered:
		_discovered = true
		lines.append(["Dr. Voss", "(comm) Did you notice? The drones fight differently depending on which reality is active. In Nova they're armoured and ranged; in Veyra they lose their armour and rush you."])
	lines.append(["Dr. Voss", "(comm) The transit station has a reality stabilizer. If we can get it running, we can stop this spreading. Get inside."])
	say(lines, func():
		objective("Enter the transit station.")
		exit_marker(ground(STATION_EAST + Vector3(0, 0.5, 0)))
		trigger(STATION_EAST, 2.5, func(): completed.emit()))


# ---------------------------------------------------------------- Scene 8

func _scene8() -> void:
	set_scene(8, "Explore the merged city and find Mira.")
	RealityManager.set_merged(true)
	player.reality_shift.locked = true
	player.reality_shift.lock_reason = "The realities are one now. There is nothing left to shift between."
	place_player(ground(FRACTURE + Vector3(0, 0.5, 0)), PI)
	var mira_pos := ground(FRACTURE + Vector3(3.0, 0.5, 4.0))
	npc(mira_pos, "Mira", Palette.FOREST, _talk_mira, -1, deg_to_rad(150))
	var view := ground(PROMENADE + Vector3(0, 0.5, 0))
	exit_marker(view, Palette.VIOLET)
	trigger(PROMENADE, 3.0, _viewpoint)
	toast("Nova and Veyra now share one city.", 4.0)


func _talk_mira(_i: Interactable) -> void:
	if _mira_talked:
		say([["Mira", "The waterfront promenade, north of here. You can see the whole city from there."]])
		return
	_mira_talked = true
	say([
		["Mira", "You did it. Look, Nova's towers, and our trees growing between them. Nothing is fading anymore."],
		["You", "It's strange. Both cities, standing in the same place, and neither one is breaking."],
		["Mira", "My people were sure Veyra was dying. It turns out we were just being pushed out of the light."],
		["You", "What happens now?"],
		["Mira", "Now we learn to share it. Two councils, two histories, one street map. It'll be messy. It'll be ours."],
		["Mira", "Come on. There's a viewpoint on the waterfront promenade. I want you to see it all."],
	], func(): objective("Reach the viewpoint on the waterfront promenade (north)."))


func _viewpoint() -> void:
	say([
		["You", "...From up here you can't tell where Nova ends and Veyra begins."],
		["Mira", "Good. That's the point."],
	], func(): completed.emit())
