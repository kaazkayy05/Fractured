extends Node
## InstabilityManager.gd — INSTABILITY (autoload).
## World instability 0..100. Raised by Reality Shifts (+5), Fracture Bursts (+15), chain reactions (+10 per
## extra reaction) and the unstable reactor; lowered by defeating enemies and activating convergence nodes.
## If instability has not risen for 10 s it decays 1 point every 3 s (Hali's spec).
## Reads RealityManager (each shift adds instability; the reactor destabilises faster in Veyra).

signal changed(value: float)
signal critical

const MAX := 100.0
const SHIFT_COST := 5.0
const CALM_DELAY := 10.0
const DECAY_PER_SEC := 1.0 / 3.0

var value := 0.0
var rise_per_sec := 0.0          # > 0 while the reactor is unstable (Scenes 6-7)
var critical_enabled := false    # only the final encounter can be lost to instability
var _was_critical := false
var _since_rise := 0.0


func _ready() -> void:
	RealityManager.shifted.connect(func(_r): add(SHIFT_COST))


func reset() -> void:
	value = 0.0
	rise_per_sec = 0.0
	critical_enabled = false
	_was_critical = false
	_since_rise = 0.0
	changed.emit(value)


func ratio() -> float:
	return value / MAX


func add(amount: float) -> void:
	if amount > 0.0:
		_since_rise = 0.0
	value = clampf(value + amount, 0.0, MAX)
	changed.emit(value)
	if critical_enabled and value >= MAX and not _was_critical:
		_was_critical = true
		critical.emit()


func _process(delta: float) -> void:
	if rise_per_sec > 0.0:
		var veyra_mult := 1.25 if RealityManager.active == RealityManager.Reality.VEYRA else 1.0
		add(rise_per_sec * veyra_mult * delta)
		return
	_since_rise += delta
	if _since_rise >= CALM_DELAY and value > 0.0:
		value = maxf(0.0, value - DECAY_PER_SEC * delta)
		changed.emit(value)
