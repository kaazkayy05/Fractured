extends Node3D

const FILES = ["res://worlds/nova.glb", "res://worlds/veyra.glb"]
const NAMES = ["NOVA", "VEYRA"]
const TITLES = ["Inspect the station crystal", "Reach the east entrance", "Follow the avenue to the fracture", "Recover the echo on the promenade", "Return to the fracture"]
const POINTS = [Vector3(-161.28,6,229.42),Vector3(-135.5,6,251.42),Vector3(-104,4.5,251.42),Vector3(-78,6,352),Vector3(-104,4.5,251.42)]
var worlds: Array[Node3D] = []
var bodies: Array[StaticBody3D] = []
var player := CharacterBody3D.new()
var camera := Camera3D.new()
var beacon := MeshInstance3D.new()
var hud := Label.new()
var marker := Label3D.new()
var timeline := 0
var stage := 0
var elapsed := 0.0
var safe_position := Vector3(-157.28,6.1,257.42)

func _ready():
 for path in FILES:
  var city := (load(path) as PackedScene).instantiate() as Node3D
  add_child(city)
  worlds.append(city)
  var body := StaticBody3D.new()
  city.add_child(body)
  var meshes := city.find_children("WalkGeometry*", "MeshInstance3D", true, false)
  assert(meshes.size()==1, "Missing city collision mesh")
  var geo := meshes[0] as MeshInstance3D
  var collider := CollisionShape3D.new()
  collider.shape = geo.mesh.create_trimesh_shape()
  body.add_child(collider)
  collider.global_transform = geo.global_transform
  geo.visible = false
  bodies.append(body)
 var env := Environment.new()
 env.background_mode = Environment.BG_SKY
 env.sky = Sky.new()
 env.sky.sky_material = ProceduralSkyMaterial.new()
 env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
 env.ambient_light_color = Color("#e5f1ff")
 env.ambient_light_energy = 0.85
 var ambience := WorldEnvironment.new()
 ambience.environment = env
 add_child(ambience)
 var sun := DirectionalLight3D.new()
 sun.rotation_degrees = Vector3(-54,-32,0)
 sun.light_energy = 1.0
 add_child(sun)
 add_child(player)
 var capsule := CapsuleShape3D.new()
 capsule.height=1.8
 capsule.radius=0.4
 var shape := CollisionShape3D.new()
 shape.shape=capsule
 player.add_child(shape)
 shape.position.y=0.9
 player.floor_snap_length=0.35
 player.add_child(camera)
 camera.position.y=1.68
 camera.far=3800
 player.position=safe_position
 var orb := SphereMesh.new()
 orb.radius=0.34
 orb.height=0.68
 beacon.mesh=orb
 var glow := StandardMaterial3D.new()
 glow.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED
 glow.albedo_color=Color("#75fff0")
 beacon.material_override=glow
 add_child(beacon)
 marker.billboard=BaseMaterial3D.BILLBOARD_ENABLED
 marker.no_depth_test=true
 marker.fixed_size=true
 marker.pixel_size=0.00055
 marker.font_size=23
 marker.outline_size=6
 add_child(marker)
 var canvas := CanvasLayer.new()
 add_child(canvas)
 canvas.add_child(hud)
 hud.position=Vector2(18,15)
 hud.add_theme_font_size_override("font_size",19)
 hud.add_theme_constant_override("outline_size",6)
 add_promenade_link()
 switch_world(0)
 update_target()
 Input.mouse_mode=Input.MOUSE_MODE_CAPTURED

func switch_world(index:int):
 timeline=index
 for i in worlds.size():
  worlds[i].visible=(i==index)
  bodies[i].collision_layer=1 if i==index else 0

func update_target():
 if stage<POINTS.size():
  beacon.position=POINTS[stage]+Vector3.UP*1.6
  marker.position=beacon.position+Vector3.UP*1.4
 else:
  marker.hide()
  beacon.hide()

func _unhandled_input(event):
 if event is InputEventMouseMotion and Input.mouse_mode==Input.MOUSE_MODE_CAPTURED:
  player.rotate_y(-event.relative.x*0.002)
  camera.rotation.x=clamp(camera.rotation.x-event.relative.y*0.002,-1.48,1.48)
 if event is InputEventMouseButton and event.pressed:
  Input.mouse_mode=Input.MOUSE_MODE_CAPTURED
 if event is InputEventKey and event.pressed and not event.echo:
  match event.physical_keycode:
   KEY_ESCAPE: Input.mouse_mode=Input.MOUSE_MODE_VISIBLE
   KEY_R:
    player.position=safe_position
    player.velocity=Vector3.ZERO
   KEY_SPACE:
    if player.is_on_floor(): player.velocity.y=6
   KEY_E:
    if stage<POINTS.size() and player.position.distance_to(POINTS[stage])<6:
     if stage==2: switch_world(1)
     if stage==4: switch_world(0)
     safe_position=player.position+Vector3.UP*0.2
     stage+=1
     update_target()
   KEY_ENTER:
    if stage==POINTS.size(): get_tree().reload_current_scene()

func _physics_process(dt):
 if worlds.size()!=2: return
 if stage<POINTS.size(): elapsed+=dt
 var local_move:=Vector3.ZERO
 if Input.is_physical_key_pressed(KEY_W): local_move.z-=1
 if Input.is_physical_key_pressed(KEY_S): local_move.z+=1
 if Input.is_physical_key_pressed(KEY_A): local_move.x-=1
 if Input.is_physical_key_pressed(KEY_D): local_move.x+=1
 var direction:=player.transform.basis*local_move.normalized()
 var speed:=7.5 if Input.is_physical_key_pressed(KEY_SHIFT) else 4.7
 player.velocity.x=direction.x*speed
 player.velocity.z=direction.z*speed
 player.velocity.y-=18*dt
 player.move_and_slide()
 if player.position.y < -10:
  player.position=safe_position
  player.velocity=Vector3.ZERO
 if stage<POINTS.size():
  var dist:=player.position.distance_to(POINTS[stage])
  marker.text="◇   %d m" % roundi(dist)
  hud.text="%s   /   CANAL CROSSING     %d / 5\n%s%s\nWASD move    Mouse look    Shift sprint    Space jump    R recover    Esc cursor" % [NAMES[timeline],stage+1,TITLES[stage],"   [E]" if dist<6 else "   ·   Follow the diamond"]
 else:
  hud.text="ECHO RECOVERED    /    %d:%02d\nExplore Nova, or press Enter to replay." % [int(elapsed)/60,int(elapsed)%60]

func add_promenade_link():
 # Join the avenue at y=4.5 to the raised waterfront paving at y=6.
 var link := StaticBody3D.new()
 add_child(link)
 link.position=Vector3(-91.1,5.1,352)
 link.rotation.z=atan2(1.5,8.0)
 var plank := BoxMesh.new()
 plank.size=Vector3(8.5,0.3,4.0)
 var surface := MeshInstance3D.new()
 surface.mesh=plank
 var mat := StandardMaterial3D.new()
 mat.albedo_color=Color("#94a9ad")
 surface.material_override=mat
 link.add_child(surface)
 var shape := BoxShape3D.new()
 shape.size=plank.size
 var collider := CollisionShape3D.new()
 collider.shape=shape
 link.add_child(collider)
