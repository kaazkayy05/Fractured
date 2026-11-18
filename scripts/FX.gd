class_name FX
## Throwaway visual effects (expanding sphere / ring) built from primitives.


static func sphere(parent: Node, pos: Vector3, radius: float, c: Color, time := 0.35) -> void:
	if parent == null:
		return
	var mi := MeshInstance3D.new()
	var sm := SphereMesh.new()
	sm.radius = 1.0
	sm.height = 2.0
	sm.radial_segments = 16
	sm.rings = 8
	mi.mesh = sm
	var m := Palette.mat(c, 2.0, 0.45)
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.cull_mode = BaseMaterial3D.CULL_DISABLED
	mi.material_override = m
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	parent.add_child(mi)
	mi.global_position = pos
	mi.scale = Vector3.ONE * 0.2
	var tw := mi.create_tween()
	tw.set_parallel(true)
	tw.tween_property(mi, "scale", Vector3.ONE * radius, time)
	tw.tween_property(m, "albedo_color:a", 0.0, time)
	tw.chain().tween_callback(mi.queue_free)


static func ring(parent: Node, pos: Vector3, radius: float, c: Color, time := 0.4) -> void:
	if parent == null:
		return
	var mi := MeshInstance3D.new()
	var tm := TorusMesh.new()
	tm.inner_radius = 0.9
	tm.outer_radius = 1.0
	tm.rings = 24
	tm.ring_segments = 6
	mi.mesh = tm
	var m := Palette.mat(c, 3.0, 0.9)
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mi.material_override = m
	parent.add_child(mi)
	mi.global_position = pos
	mi.scale = Vector3(0.2, 1.0, 0.2)
	var tw := mi.create_tween()
	tw.set_parallel(true)
	tw.tween_property(mi, "scale", Vector3(radius, 1.0, radius), time)
	tw.tween_property(m, "albedo_color:a", 0.0, time)
	tw.chain().tween_callback(mi.queue_free)
