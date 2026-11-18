class_name DefensiveCounter
extends Node
## DefensiveCounter.gd — GUARD STATE (Kayla). Hold [RMB] to guard (-75% damage). Guarding within 0.3 s of a
## hit is a perfect counter: no damage, the attacker is stunned, and Combat's next strike is empowered.

const PARRY_WINDOW := 0.3
const GUARD_REDUCTION := 0.75
const COUNTER_WINDOW := 2.5

var guarding := false
var guard_time := 0.0
var counter_ready := 0.0
var player: Player


func _ready() -> void:
	player = get_parent() as Player


func _process(delta: float) -> void:
	if guarding:
		guard_time += delta
	counter_ready = maxf(0.0, counter_ready - delta)


func set_guard(on: bool) -> void:
	if on and player.combat.is_attacking():
		on = false
	if on and not guarding:
		guard_time = 0.0
	guarding = on


func filter_damage(amount: float, source: Node) -> float:
	if not guarding:
		return amount
	if guard_time <= PARRY_WINDOW:
		counter_ready = COUNTER_WINDOW
		if source is EnemyAI:
			(source as EnemyAI).stun(1.5)
		player.toast("PERFECT COUNTER! Strike now.")
		FX.ring(player.get_parent(), player.global_position + Vector3(0, 1, 0), 1.6, Palette.CYAN, 0.25)
		return 0.0
	return amount * (1.0 - GUARD_REDUCTION)


func consume_counter() -> bool:
	if counter_ready > 0.0:
		counter_ready = 0.0
		return true
	return false
