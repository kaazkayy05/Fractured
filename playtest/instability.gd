extends Node
signal changed(district_id: StringName, value: int)
@export var shift_increase := 5
@export_range(10, 20, 1) var destruction_increase := 15
@export var stabilizer_reduction := 30
@export var stabilizer_uses := 2
var values: Dictionary = {}
var remaining_uses: Dictionary = {}
var processed_events: Dictionary = {}

func register_district(id: StringName) -> void:
 if values.has(id): return
 values[id] = 0
 remaining_uses[id] = stabilizer_uses
 processed_events[id] = {}

func value(id: StringName) -> int:
 register_district(id)
 return values[id]

func add(id: StringName, amount: int) -> void:
 register_district(id)
 var next_value: int = clampi(values[id] + amount, 0, 100)
 if next_value != values[id]:
  values[id] = next_value
  changed.emit(id, next_value)

func reality_shift(id: StringName) -> void:
 add(id, shift_increase)

func structural_destruction(id: StringName, event_id: StringName, severity: int = 15) -> bool:
 register_district(id)
 if event_id == &"" or processed_events[id].has(event_id): return false
 processed_events[id][event_id] = true
 add(id, clampi(severity, 10, 20))
 return true

func activate_stabilizer(id: StringName) -> bool:
 register_district(id)
 if remaining_uses[id] <= 0: return false
 remaining_uses[id] -= 1
 add(id, -stabilizer_reduction)
 return true

func tier(id: StringName) -> int:
 var current := value(id)
 if current >= 90: return 3
 if current >= 60: return 2
 if current >= 30: return 1
 return 0
