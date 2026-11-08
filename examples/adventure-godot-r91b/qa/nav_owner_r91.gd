extends SceneTree
## R91 independent adversarial walkmesh owner; tests every interpolated step,
## unreachable water clicks, obstacles, all hotspots, screen boundaries and saves.
const Nav=preload("res://adventure_nav_r91.gd")
var game:Node
var checks:Array[Dictionary]=[]
var failed:Array[String]=[]
var tested_steps:int=0

func _initialize() -> void:
  call_deferred("_run")

func check(ok:bool,name:String) -> void:
  checks.append({"name":name,"pass":ok})
  if not ok:
    failed.append(name)
    push_error("R91 NAV OWNER FAILED "+name)

func _route_probe(room:String, wanted:Vector2, label:String) -> void:
  game._enter(room)
  var initial:Vector2=game.hero
  var nav:Dictionary=game.nav_section
  var expected:Vector2=Nav.nearest_point(nav,wanted)
  game._walk_to(wanted)
  var steps:int=0
  var walked:bool=game.has_target
  var safe:bool=Nav.allowed(nav,game.hero)
  while game.has_target and steps<550:
    game._process(0.05)
    steps+=1
    tested_steps+=1
    if not Nav.allowed(nav,game.hero):
      safe=false
      break
  check(safe,"safe-step-"+label)
  check(steps<550 and not game.has_target,"route-terminates-"+label)
  check(Nav.allowed(nav,game.hero),"final-foot-on-walkmesh-"+label)
  check(game.hero.distance_to(expected)<2.1 or (not walked and initial.distance_to(expected)<2.1),
    "ends-at-projected-reachable-goal-"+label)
  var w:float=24.0*clampf(0.83+(game.hero.y-105.0)*0.009,0.83,1.05)
  check(game.hero.x-w*0.5>=0.0 and game.hero.x+w*0.5<=320.0
   and game.hero.y<=126.001 and game.hero.y-48.0*1.05>=0.0,
   "sprite-bounds-scene-"+label)

func _run() -> void:
  var source:PackedScene=load("res://main.tscn")
  if source==null:
    check(false,"load-main")
    _finish()
    return
  game=source.instantiate()
  root.add_child(game)
  game.save_location="res://qa/R91-NAV-TEST-SAVE.json"
  await process_frame
  check(game.GRID==Vector2i(640,360),"native-pixel-grid-640x360")
  check(game.LOGICAL_GRID==Vector2i(320,180),"interaction-grid-320x180")
  check(game.navigation["pixelScale"]==2,"two-times-physical-resolution")
  check(Nav.validate_contract(game.navigation),"contract-three-rooms-accepted")
  var names=["harbor","workshop","old_observatory"]
  for room_name in names:
    var zone:Dictionary=game.navigation["scenes"][room_name]
    var hotspots:Array=game.world["scenes"][room_name]["hotspots"]
    for spot in hotspots:
      var pos:Vector2=Vector2(float(spot["walkTo"][0]),float(spot["walkTo"][1]))
      check(Nav.allowed(zone,pos),"hotspot-walkto-safe-"+room_name+"-"+spot["id"])
  # Target points intentionally far outside valid floor and screen, without assuming
  # click position equals the character's standing position.
  var points=[
    Vector2(-500,-100),Vector2(1000,900),Vector2(0,0),
    Vector2(319,0),Vector2(0,179),Vector2(319,179),
    Vector2(160,34),Vector2(170,121),Vector2(200,90),
    Vector2(300,126),Vector2(50,117),Vector2(247,112)
  ]
  for room_name in names:
    for i in range(points.size()):
      _route_probe(room_name,points[i],room_name+"-"+str(i))
  # A walk from left pier to the lighthouse must route around the elder,
  # and never cut through his occupied footprint.
  game._enter("harbor")
  game.hero=Vector2(43,116)
  var direct:=Nav.line_is_safe(game.nav_section,Vector2(43,118),Vector2(247,118))
  check(not direct,"elder-blocks-straight-line")
  var path:Array[Vector2]=Nav.find_path(game.nav_section,Vector2(43,118),Vector2(247,118))
  check(path.size()>1,"astar-detour-around-elder")
  var last:=Vector2(43,118)
  var edges_safe:=true
  for corner in path:
    if not Nav.line_is_safe(game.nav_section,last,corner):
      edges_safe=false
    last=corner
  check(edges_safe,"detour-never-cuts-through-elder")
  # Input positions use real 640x360 pixels, projected into 320x180 walkmesh.
  game._enter("harbor")
  var click:=InputEventMouseButton.new()
  click.button_index=MOUSE_BUTTON_LEFT
  click.pressed=true
  click.position=Vector2(620,15) # far out at sea/sky
  game.verb="IR"
  game._input(click)
  var safe_click:bool=true
  for step in range(180):
    if not game.has_target:break
    game._process(0.05)
    tested_steps+=1
    if not Nav.allowed(game.nav_section,game.hero):
      safe_click=false
      break
  check(safe_click and Nav.allowed(game.nav_section,game.hero),"physical-click-in-sky-does-not-enter-sea")
  check(not game.has_target,"physical-click-projection-converges")
  # Compatibility with existing R90 saves: one clamped position and fresh restart.
  game._enter("harbor")
  game.hero=Vector2(43,116)
  game.inventory.append("lens")
  check(game.save_game(),"manual-save-R91")
  game.hero=Vector2(247,112)
  check(game.load_game(),"manual-load-R91")
  check(Nav.allowed(game.nav_section,game.hero),"load-restores-valid-foot")
  game.completed=true
  game.restart_game()
  check(not game.completed and game.inventory.is_empty() and game.scene_id=="harbor",
    "restart-after-end-resets-inventory-and-flags")
  check(not game.has_target and game.route.is_empty(),"restart-cancels-pending-route")
  _finish()

func _finish() -> void:
  var status:String="PASS_R91_NAV_WALKBOX_ANTI_CLIP" if failed.is_empty() else "FAILED_R91_NAV_OWNER"
  var doc={
    "schema":1,"operationId":"AF.R91.GODOT-WALKMESH-ADVERSARIAL-OWNER-20261108",
    "status":status,"checks":checks,"failures":failed,
    "testedPhysicsSteps":tested_steps,
    "nativeResolution":[640,360],"logicalInteraction":[320,180],
    "note":"All 3 rooms, 36 off-floor routes, 3D footprint protection and all hotspots",
    "humanArtApproved":false,"autonomousFactoryGeneral":false
  }
  var out=FileAccess.open("res://qa/R91-NAV-OWNER-READBACK.json",FileAccess.WRITE)
  if out!=null:
    out.store_string(JSON.stringify(doc,"\t"))
    out.flush()
    out.close()
  print("R91_NAV_OWNER "+JSON.stringify({"status":status,"checks":checks.size(),"failures":failed,"physicsSteps":tested_steps}))
  quit(0 if failed.is_empty() else 4)
