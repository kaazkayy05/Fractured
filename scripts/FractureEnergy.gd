class_name FractureEnergy
extends Node
## FractureEnergy.gd — ENERGY (Hali). Successful hits grant +5 energy (max 100); shards add more.
## [F] Fracture Burst: 40 energy, 25 damage within 4 m to enemies and unstable structures, interrupts enemy
## attacks, 5 s cooldown, +15 instability (writes InstabilityManager).

signal changed(value: float)

const MAX := 100.0
const HIT_GAIN := 5.0
const BURST_COST := 40.0
const BURST_RADIUS := 4.0
const BURST_DAMAGE := 25.0
const BURST_COOLDOWN := 5.0
const BURST_INSTABILITY := 15.0

var energy := 0.0
var cooldown_left := 0.0
var player: Player


func _ready() -> void:
	player = get_parent() as Player


func _process(delta: float) -> void:
	cooldown_left = maxf(0.0, cooldown_left - delta)


func add(amount: float) -> void:
	energy = clampf(energy + amount, 0.0, MAX)
	changed.emit(energy)


func on_hit() -> void:
	add(HIT_GAIN)


func try_burst() -> bool:
	if cooldown_left > 0.0 or energy < BURST_COST:
		player.toast("Fracture Burst needs %d energy and a ready cooldown (%d / %d)." % [int(BURST_COST), int(energy), int(BURST_COST)])
		return false
	add(-BURST_COST)
	cooldown_left = BURST_COOLDOWN
	var centre := player.global_position + Vector3(0, 1.0, 0)
	var affected := 0
	for e in get_tree().get_nodes_in_group("enemy"):
		var enemy := e as EnemyAI
		if enemy and enemy.alive and enemy.global_position.distance_to(centre) <= BURST_RADIUS + enemy.radius:
			enemy.take_damage(BURST_DAMAGE, true, player, 0.0)
			enemy.interrupt_attack()
			affected += 1
	for s in get_tree().get_nodes_in_group("structure"):
		var st := s as Structure
		if st and st.is_present() and st.distance_to_point(centre) <= BURST_RADIUS:
			if st.apply_damage(BURST_DAMAGE, true):
				affected += 1
	InstabilityManager.add(BURST_INSTABILITY)
	FX.ring(player.get_parent(), player.global_position + Vector3(0, 0.2, 0), BURST_RADIUS, Palette.VIOLET, 0.45)
	FX.sphere(player.get_parent(), centre, BURST_RADIUS, Palette.VIOLET, 0.35)
	player.toast("Fracture Burst hit %d target(s). Instability +15." % affected, 1.5)
	return true
