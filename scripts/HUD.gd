class_name HUD
extends CanvasLayer
## HUD: bars (health / fracture energy / instability), reality + cooldowns, objective, prompts, toasts,
## dialogue box, fades, title / lose / credits screens. Runs while the tree is paused (dialogue).

signal dialogue_finished
signal title_dismissed
signal retry_requested

var player: Player
var _root: Control
var _hp: ProgressBar
var _en: ProgressBar
var _inst: ProgressBar
var _inst_label: Label
var _reality: Label
var _cooldowns: Label
var _objective: Label
var _scene_title: Label
var _prompt: Label
var _hold: ProgressBar
var _toast: Label
var _toast_t := 0.0
var _controls: Label
var _fade: ColorRect
var _flash: ColorRect
var _dlg_panel: PanelContainer
var _dlg_name: Label
var _dlg_text: Label
var _dlg_hint: Label
var _dlg_lines: Array = []
var _dlg_index := 0
var _dlg_done := Callable()
var _overlay: PanelContainer
var _overlay_text: Label
var _overlay_mode := ""
var _credits: Label
var _credits_t := 0.0


func _ready() -> void:
	add_to_group("hud")
	layer = 10
	process_mode = Node.PROCESS_MODE_ALWAYS
	_root = Control.new()
	_root.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_root)

	var bars := VBoxContainer.new()
	_place(bars, 0, 0, 20, 14, 300, 120)
	_root.add_child(bars)
	_hp = _bar(bars, "HEALTH", Color(0.85, 0.25, 0.25))
	_en = _bar(bars, "FRACTURE ENERGY", Palette.VIOLET)
	_inst_label = Label.new()
	_inst = _bar(bars, "INSTABILITY", Palette.AMBER, _inst_label)

	_reality = _label(_root, 30, Palette.CYAN)
	_place(_reality, 1, 0, -340, 14, 320, 40)
	_reality.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	_cooldowns = _label(_root, 16, Color(0.9, 0.9, 0.9))
	_place(_cooldowns, 1, 0, -340, 58, 320, 120)
	_cooldowns.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT

	_scene_title = _label(_root, 15, Color(0.75, 0.8, 0.85))
	_place(_scene_title, 0.5, 0, -300, 12, 600, 22)
	_scene_title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_objective = _label(_root, 20, Color(1, 1, 1))
	_place(_objective, 0.5, 0, -300, 34, 600, 60)
	_objective.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_objective.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART

	var cross := _label(_root, 18, Color(1, 1, 1, 0.6))
	cross.text = "+"
	_place(cross, 0.5, 0.5, -6, -14, 12, 24)

	_prompt = _label(_root, 20, Palette.CYAN)
	_place(_prompt, 0.5, 1, -450, -235, 900, 30)
	_prompt.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_hold = ProgressBar.new()
	_hold.show_percentage = false
	_place(_hold, 0.5, 1, -120, -200, 240, 10)
	_hold.max_value = 1.0
	_hold.visible = false
	_root.add_child(_hold)

	_toast = _label(_root, 22, Color(1, 0.95, 0.85))
	_place(_toast, 0.5, 0.5, -450, 60, 900, 60)
	_toast.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_toast.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART

	_controls = _label(_root, 14, Color(0.8, 0.85, 0.9, 0.85))
	_place(_controls, 0, 1, 20, -170, 460, 155)
	_controls.vertical_alignment = VERTICAL_ALIGNMENT_BOTTOM

	_dlg_panel = PanelContainer.new()
	_place(_dlg_panel, 0.5, 1, -460, -180, 920, 160)
	_dlg_panel.add_theme_stylebox_override("panel", _panel_style(Color(0.05, 0.07, 0.1, 0.9), Palette.CYAN))
	var v := VBoxContainer.new()
	_dlg_panel.add_child(v)
	_dlg_name = _label(v, 22, Palette.CYAN)
	_dlg_text = _label(v, 20, Color(1, 1, 1))
	_dlg_text.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_dlg_text.custom_minimum_size = Vector2(880, 70)
	_dlg_hint = _label(v, 14, Color(0.7, 0.7, 0.7))
	_dlg_hint.text = "[E / Space / Enter / Click] continue"
	_dlg_hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	_dlg_panel.visible = false
	_root.add_child(_dlg_panel)

	_flash = ColorRect.new()
	_flash.set_anchors_preset(Control.PRESET_FULL_RECT)
	_flash.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_flash.color = Color(1, 1, 1, 0)
	_root.add_child(_flash)
	_fade = ColorRect.new()
	_fade.set_anchors_preset(Control.PRESET_FULL_RECT)
	_fade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_fade.color = Color(0, 0, 0, 0)
	_root.add_child(_fade)

	_overlay = PanelContainer.new()
	_overlay.set_anchors_preset(Control.PRESET_FULL_RECT)
	_overlay.add_theme_stylebox_override("panel", _panel_style(Color(0.02, 0.03, 0.05, 0.94), Color(0, 0, 0, 0)))
	_overlay_text = _label(_overlay, 22, Color(1, 1, 1))
	_overlay_text.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_overlay_text.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	_overlay_text.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_overlay.visible = false
	_root.add_child(_overlay)
	_credits = _label(_root, 24, Color(1, 1, 1))
	_credits.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_place(_credits, 0.5, 0, -450, 800, 900, 900)
	_credits.visible = false


func _bar(parent: Control, title: String, c: Color, lab: Label = null) -> ProgressBar:
	var l := lab if lab else Label.new()
	l.text = title
	l.add_theme_font_size_override("font_size", 13)
	l.add_theme_color_override("font_color", c.lightened(0.3))
	parent.add_child(l)
	var b := ProgressBar.new()
	b.show_percentage = false
	b.custom_minimum_size = Vector2(300, 14)
	b.max_value = 100
	var fill := StyleBoxFlat.new()
	fill.bg_color = c
	b.add_theme_stylebox_override("fill", fill)
	var bg := StyleBoxFlat.new()
	bg.bg_color = Color(0, 0, 0, 0.5)
	b.add_theme_stylebox_override("background", bg)
	parent.add_child(b)
	return b


static func _place(c: Control, ax: float, ay: float, x: float, y: float, w: float, h: float) -> void:
	## anchor (ax, ay) in 0..1 of the screen, box offset (x, y) from that anchor, size w x h
	c.anchor_left = ax
	c.anchor_right = ax
	c.anchor_top = ay
	c.anchor_bottom = ay
	c.offset_left = x
	c.offset_top = y
	c.offset_right = x + w
	c.offset_bottom = y + h


func _label(parent: Node, size: int, c: Color) -> Label:
	var l := Label.new()
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", c)
	l.add_theme_color_override("font_outline_color", Color(0, 0, 0))
	l.add_theme_constant_override("outline_size", 6)
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	parent.add_child(l)
	return l


func _panel_style(bg: Color, border: Color) -> StyleBoxFlat:
	var s := StyleBoxFlat.new()
	s.bg_color = bg
	s.border_color = border
	s.set_border_width_all(2 if border.a > 0 else 0)
	s.set_corner_radius_all(6)
	s.set_content_margin_all(16)
	return s


# ---------------------------------------------------------------- per-frame

func _process(delta: float) -> void:
	_toast_t -= delta
	_toast.modulate.a = clampf(_toast_t, 0.0, 1.0)
	if _credits.visible:
		_credits_t += delta
		var y := get_viewport().get_visible_rect().size.y - _credits_t * 60.0
		_credits.offset_top = y
		_credits.offset_bottom = y + 900
	if player == null or not is_instance_valid(player):
		return
	_hp.value = player.health
	_en.value = player.fracture.energy
	_inst.value = InstabilityManager.value
	_inst_label.text = "INSTABILITY" + ("  —  CRITICAL LIMIT ACTIVE" if InstabilityManager.critical_enabled else "")
	_reality.text = RealityManager.reality_name()
	_reality.add_theme_color_override("font_color", Palette.VIOLET.lightened(0.3) if RealityManager.merged else (Palette.CYAN if RealityManager.is_nova() else Palette.FOREST.lightened(0.45)))
	var cd: Array[String] = []
	if player.has_ability("shift"):
		cd.append("Shift [Q] " + ("ready" if player.reality_shift.cooldown_left <= 0 else "%.1fs" % player.reality_shift.cooldown_left) + (" (locked)" if player.reality_shift.locked else ""))
	if player.has_ability("burst"):
		cd.append("Burst [F] " + ("ready" if player.fracture.cooldown_left <= 0 else "%.1fs" % player.fracture.cooldown_left))
	if player.has_ability("echo"):
		cd.append("Recall [V] " + ("ready" if player.echo.recall_cooldown <= 0 else "%.1fs" % player.echo.recall_cooldown))
	if player.has_ability("chain"):
		cd.append("Chain [G] " + ("ready" if player.chain.cooldown_left <= 0 else "%.1fs" % player.chain.cooldown_left))
	if player.has_ability("echo"):
		cd.append("Echo [C] " + ("active %.0fs" % player.echo.time_left if player.echo.echo else ("ready" if player.echo.cooldown_left <= 0 else "%.1fs" % player.echo.cooldown_left)))
	if player.defense.counter_ready > 0:
		cd.append("COUNTER READY")
	_cooldowns.text = "\n".join(cd)
	var c: Array[String] = ["WASD move · Space jump · Shift sprint · Mouse look · Esc free mouse"]
	if player.has_ability("shift"):
		c.append("Q  Reality Shift")
	if player.has_ability("burst"):
		c.append("F  Fracture Burst (40 energy, 4 m)")
	if player.has_ability("combat"):
		c.append("LMB  Attack combo · RMB  Guard (tap just before a hit = Counter)")
	if player.has_ability("echo"):
		c.append("C  Echo Projection · V  Rift Recall")
	if player.has_ability("structure"):
		c.append("E  Interact / Structural Manipulation")
	else:
		c.append("E  Interact")
	if player.has_ability("chain"):
		c.append("G  Chain Reaction (6 m)")
	_controls.text = "\n".join(c)


# ---------------------------------------------------------------- api

func set_objective(text: String) -> void:
	_objective.text = text


func set_scene_title(text: String) -> void:
	_scene_title.text = text


func set_prompt(text: String, hold := -1.0) -> void:
	_prompt.text = text
	_hold.visible = hold >= 0.0 and text != ""
	if hold >= 0.0:
		_hold.value = hold


func toast(text: String, time := 3.0) -> void:
	_toast.text = text
	_toast_t = time


func flash(c: Color, time := 0.3) -> void:
	_flash.color = Color(c.r, c.g, c.b, 0.6)
	var tw := create_tween()
	tw.tween_property(_flash, "color:a", 0.0, time)


func fade_out(time := 0.5) -> void:
	var tw := create_tween()
	tw.tween_property(_fade, "color:a", 1.0, time)
	await tw.finished


func fade_in(time := 0.5) -> void:
	var tw := create_tween()
	tw.tween_property(_fade, "color:a", 0.0, time)
	await tw.finished


func in_dialogue() -> bool:
	return _dlg_panel.visible


func say(lines: Array, on_done := Callable()) -> void:
	## lines: [[speaker, text], ...]
	if lines.is_empty():
		if on_done.is_valid():
			on_done.call()
		return
	_dlg_lines = lines
	_dlg_index = 0
	_dlg_done = on_done
	_dlg_panel.visible = true
	_show_line()
	get_tree().paused = true


func _show_line() -> void:
	var l: Array = _dlg_lines[_dlg_index]
	_dlg_name.text = l[0]
	var col := Palette.CYAN
	match l[0]:
		"Dr. Voss":
			col = Palette.SILVER
		"Mira":
			col = Palette.FOREST.lightened(0.45)
		"You":
			col = Palette.CYAN
		_:
			col = Palette.AMBER
	_dlg_name.add_theme_color_override("font_color", col)
	_dlg_text.text = l[1]


func _advance() -> void:
	_dlg_index += 1
	if _dlg_index >= _dlg_lines.size():
		_dlg_panel.visible = false
		get_tree().paused = false
		if player:
			player.interact_block_until = Time.get_ticks_msec() + 250
		var cb := _dlg_done
		_dlg_done = Callable()
		dialogue_finished.emit()
		if cb.is_valid():
			cb.call()
	else:
		_show_line()


func show_title() -> void:
	_overlay_mode = "title"
	_overlay.visible = true
	_overlay_text.text = "F R A C T U R E D\n\nTwo realities. One city. One experiment that broke them apart.\n\n" \
		+ "[Enter] or [Click] to begin\n\n\nCredits (gameplay owners): Research Facility (Hali) · City Streets (Kayla) · Transit Station (Megan) · Central Reactor (Zion)\n" \
		+ "F9 skips to the next scene (testing)"
	get_tree().paused = true


func show_lose(reason: String) -> void:
	_overlay_mode = "lose"
	_overlay.visible = true
	_overlay_text.text = "REALITY COLLAPSED\n\n%s\n\n[R] or [Enter] retry from the last checkpoint" % reason
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	get_tree().paused = true


func show_credits() -> void:
	_overlay_mode = "credits"
	_overlay.visible = true
	_overlay_text.text = ""
	_credits.visible = true
	_credits_t = 0.0
	_credits.text = "F R A C T U R E D\n\nNova and Veyra, together again.\n\n\nResearch Facility — Hali\nReality Shift · Fracture Energy\n\n" \
		+ "City Streets — Kayla\nCombat · Defensive Counter · Echo Projection · Rift Recall\n\nTransit Station — Megan\nStructural Manipulation · Chain Reactions\n\n" \
		+ "Central Reactor — Zion\nEnemy AI · Instability · Convergence\n\n\nThanks for playing.\n\n[Enter] return to title"
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	get_tree().paused = true


func hide_overlay() -> void:
	_overlay.visible = false
	_credits.visible = false
	_overlay_mode = ""
	get_tree().paused = false
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED


func _input(event: InputEvent) -> void:
	if _overlay_mode == "title":
		if event.is_action_pressed("advance") or (event is InputEventMouseButton and event.pressed):
			get_viewport().set_input_as_handled()
			hide_overlay()
			title_dismissed.emit()
		return
	if _overlay_mode == "lose":
		if event.is_action_pressed("retry") or event.is_action_pressed("advance"):
			get_viewport().set_input_as_handled()
			hide_overlay()
			retry_requested.emit()
		return
	if _overlay_mode == "credits":
		if event.is_action_pressed("advance"):
			get_viewport().set_input_as_handled()
			hide_overlay()
			get_tree().reload_current_scene()
		return
	if _dlg_panel.visible:
		var adv := event.is_action_pressed("interact") or event.is_action_pressed("jump") or event.is_action_pressed("advance")
		if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
			adv = true
		if adv:
			get_viewport().set_input_as_handled()
			_advance()
