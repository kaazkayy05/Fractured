class_name Combat
extends Node
## Combat.gd — COMBOS (Kayla). [LMB] 3-hit melee combo. Reads DefensiveCounter: a perfect guard primes a
## counter, and the next strike deals 2.5x damage and stuns. (Combat <-> DefensiveCounter.)

const DAMAGE := [10.0, 12.0, 22.0]
const RANGE := 2.6
const COMBO_WINDOW := 0.8

var combo := 0
var combo_timer := 0.0
var attack_cd := 0.0
var attacking := 0.0
var player: Player


func _ready() -> void:
	player = get_parent() as Player


func _process(delta: float) -> void:
	combo_timer = maxf(0.0, combo_timer - delta)
	attack_cd = maxf(0.0, attack_cd - delta)
	attacking = maxf(0.0, attacking - delta)


func is_attacking() -> bool:
	return attacking > 0.0


func attack() -> void:
	if attack_cd > 0.0 or player.defense.guarding:
		return
	if combo_timer <= 0.0:
		combo = 0
	var dmg: float = DAMAGE[combo]
	var stun := 0.0
	var counter := player.defense.consume_counter()
	if counter:
		dmg *= 2.5
		stun = 1.2
	var fwd := player.aim_forward()
	var origin := player.global_position + Vector3(0, 1.0, 0)
	var hits := 0
	for e in get_tree().get_nodes_in_group("enemy"):
		var enemy := e as EnemyAI
		if enemy == null or not enemy.alive:
			continue
		var to := enemy.global_position - origin
		var flat := Vector3(to.x, 0, to.z)
		if to.length() > RANGE + enemy.radius:
			continue
		if flat.length() > 0.3 and flat.normalized().dot(fwd) < 0.25:
			continue
		enemy.take_damage(dmg, counter, player, stun)
		enemy.knockback(flat.normalized() * (6.0 if combo == 2 or counter else 2.5))
		hits += 1
	if hits > 0:
		player.fracture.on_hit()          # Hali: successful hit = +5 Fracture Energy
	player.swing_fx(combo, counter)
	attacking = 0.22
	combo = (combo + 1) % 3
	combo_timer = COMBO_WINDOW
	attack_cd = 0.55 if combo == 0 else 0.3
