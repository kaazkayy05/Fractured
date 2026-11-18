extends Node
## Prints FPS for a scene in both realities. Run (windowed):  Godot --path . res://tests/Perf.tscn -- --scene=3

var main: Node


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	main = (load("res://scenes/Main.tscn") as PackedScene).instantiate()
	get_tree().root.add_child.call_deferred(main)
	_run()


func _run() -> void:
	var t0 := Time.get_ticks_msec()
	while main.location == null or main._loading:
		await get_tree().process_frame
	print("PERF load_ms=", Time.get_ticks_msec() - t0)
	for i in 300:
		if main.hud.in_dialogue():
			main.hud._advance()
		await get_tree().process_frame
		if not main.hud.in_dialogue() and i > 10:
			break
	for r in [0, 1, 0]:
		RealityManager.set_reality(r)
		await get_tree().create_timer(3.0).timeout
		print("PERF reality=", r, " fps=", Engine.get_frames_per_second(), " draw_calls=", RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME), " prims=", RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_PRIMITIVES_IN_FRAME), " phys_ms=", Performance.get_monitor(Performance.TIME_PHYSICS_PROCESS) * 1000.0)
	get_tree().quit()
