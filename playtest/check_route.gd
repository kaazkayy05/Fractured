extends SceneTree
func _initialize():
 call_deferred("check")
func check():
 var main=load("res://Crossing.tscn").instantiate()
 root.add_child(main)
 for n in 24: await physics_frame
 if main.worlds.size()!=2 or not main.player.is_on_floor():
  printerr("Spawn floor failed");quit(1);return
 for i in 5:
  main.player.position=main.POINTS[i]+Vector3(0,0.15,0) if i!=0 else main.POINTS[i]+Vector3(4,0.15,0)
  main.player.velocity=Vector3.ZERO
  for n in 22: await physics_frame
  if not main.player.is_on_floor() or abs(main.player.position.y-main.POINTS[i].y)>1:
   printerr("Waypoint floor failed ",i," ",main.player.position);quit(1);return
  var e=InputEventKey.new()
  e.physical_keycode=KEY_E
  e.pressed=true
  main._unhandled_input(e)
  if main.stage!=i+1:
   printerr("Interaction failed ",i);quit(1);return
 print("PASS spawn, five waypoint floors, timeline crossings, finish. Timeline=",main.timeline)
 quit()
