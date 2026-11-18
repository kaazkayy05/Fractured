extends Node3D
## Main.gd — SCENE PROGRESSION. Owns the persistent Player and HUD, loads the four location scenes in story
## order (Scenes 1-8), handles win (credits) and lose (health 0 / critical instability in the final encounter).
##   Scene 1-2  ResearchFacility.tscn   (Hali)   RealityShift, FractureEnergy
##   Scene 3    CityStreets.tscn        (Kayla)  Combat, DefensiveCounter, Echo / Recall
##   Scene 4-5  TransitStation.tscn     (Megan)  Structure, ChainReaction
##   Scene 6-7  CentralReactor.tscn     (Zion)   EnemyAI, InstabilityManager
##   Scene 8    CityStreets.tscn        (merged city, credits)
## Start at a given scene for testing:  Godot --path . -- --scene=4     (F9 in game skips ahead)

const LOCATION_FOR_SCENE := {
	1: "res://scenes/ResearchFacility.tscn", 2: "res://scenes/ResearchFacility.tscn",
	3: "res://scenes/CityStreets.tscn",
	4: "res://scenes/TransitStation.tscn", 5: "res://scenes/TransitStation.tscn",
	6: "res://scenes/CentralReactor.tscn", 7: "res://scenes/CentralReactor.tscn",
	8: "res://scenes/CityStreets.tscn",
}

var hud: HUD
var player: Player
var location: Location
var checkpoint_scene := 1
var _loading := false


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	Controls.setup()
	hud = HUD.new()
	add_child(hud)
	player = Player.new()
	player.process_mode = Node.PROCESS_MODE_PAUSABLE
	add_child(player)
	hud.player = player
	player.died.connect(func(): hud.show_lose("Your health reached zero."))
	InstabilityManager.critical.connect(func(): hud.show_lose("The reactor reached critical instability."))
	hud.retry_requested.connect(func(): go_to(checkpoint_scene))
	var start := 1
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--scene="):
			start = clampi(int(a.trim_prefix("--scene=")), 1, 8)
	if start == 1:
		hud.show_title()
		await hud.title_dismissed
	go_to(start)


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("debug_skip") and location and not _loading and not get_tree().paused:
		go_to(location.scene_no + 1)


func go_to(n: int) -> void:
	if _loading:
		return
	_loading = true
	await hud.fade_out(0.4)
	if n > 8:
		_loading = false
		hud.fade_in(0.1)
		hud.show_credits()
		return
	hud.toast("Loading…", 30.0)
	await get_tree().process_frame
	if location:
		location.queue_free()
		location = null
		await get_tree().process_frame
	player.echo._clear()
	player.revive()
	player.reality_shift.locked = false
	player.control_enabled = true
	RealityManager.reset()
	InstabilityManager.reset()
	checkpoint_scene = n
	var ps := load(LOCATION_FOR_SCENE[n]) as PackedScene
	location = ps.instantiate() as Location
	location.process_mode = Node.PROCESS_MODE_PAUSABLE
	location.player = player
	location.hud = hud
	add_child(location)
	location.completed.connect(_on_location_completed.bind(location))
	location.checkpoint_reached.connect(func(s): checkpoint_scene = s)
	await location.start(n)
	hud.toast("", 0.0)
	_loading = false
	await hud.fade_in(0.6)


func _on_location_completed(loc: Location) -> void:
	if loc == location:
		go_to(loc.scene_no + 1)
