class_name Controls
## Registers the input map in code so every scene works even when run on its own (F6).

const KEYS := {
	"move_forward": [KEY_W, KEY_UP],
	"move_back": [KEY_S, KEY_DOWN],
	"move_left": [KEY_A, KEY_LEFT],
	"move_right": [KEY_D, KEY_RIGHT],
	"jump": [KEY_SPACE],
	"sprint": [KEY_SHIFT],
	"interact": [KEY_E],              # interact / Structural Manipulation (Megan)
	"reality_shift": [KEY_Q],         # Reality Shift (Hali)
	"fracture_burst": [KEY_F],        # Fracture Energy burst (Hali)
	"chain_reaction": [KEY_G],        # Environmental Chain Reaction (Megan)
	"echo": [KEY_C],                  # Echo Projection (Kayla)
	"recall": [KEY_V],                # Rift Recall (Kayla)
	"pause": [KEY_ESCAPE],
	"retry": [KEY_R],
	"advance": [KEY_ENTER, KEY_KP_ENTER],
	"debug_skip": [KEY_F9],
}
const MOUSE := {
	"attack": MOUSE_BUTTON_LEFT,      # Combat (Kayla)
	"guard": MOUSE_BUTTON_RIGHT,      # Defensive Counter (Kayla)
}


static func setup() -> void:
	for action in KEYS:
		if InputMap.has_action(action):
			continue
		InputMap.add_action(action)
		for k in KEYS[action]:
			var ev := InputEventKey.new()
			ev.physical_keycode = k
			InputMap.action_add_event(action, ev)
	for action in MOUSE:
		if InputMap.has_action(action):
			continue
		InputMap.add_action(action)
		var mb := InputEventMouseButton.new()
		mb.button_index = MOUSE[action]
		InputMap.action_add_event(action, mb)
