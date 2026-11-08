extends SceneTree
## R92 independent finite state machine owner. Repeated inputs, stale routes and save isolation.
var game: Node
var checks: Array[Dictionary] = []
var failures: Array[String] = []

func _initialize() -> void:
  call_deferred("_run")

func expect(value: bool, label: String) -> void:
  checks.append({"name":label,"pass":value})
  if not value:
    failures.append(label)
    push_error("R92_STATE_OWNER_FAILED:"+label)

func mouse(x:float,y:float) -> void:
  var e:=InputEventMouseButton.new()
  e.button_index=MOUSE_BUTTON_LEFT
  e.pressed=true
  e.position=Vector2(x*2.0,y*2.0)
  game._input(e)

func key(n:Key) -> void:
  var e:=InputEventKey.new()
  e.keycode=n
  e.pressed=true
  game._input(e)

func _run() -> void:
  var scene: PackedScene=load("res://main.tscn")
  expect(scene!=null,"original-scene-load")
  if scene==null:
    _finish()
    return
  game=scene.instantiate()
  root.add_child(game)
  game.save_location="res://qa/R92-STATE-TEST-SAVE.json"
  await process_frame
  expect(game.GRID==Vector2i(640,360),"native-grid-intact")
  expect(game.SCENE_HEIGHT==145 and game.UI_HEIGHT==35,"more-scene-less-hud")
  expect(game.pictures["harbor_back"].get_size()==Vector2(640,290),"backdrop-expanded-without-stretch")
  expect(game.pictures["interface"].get_size()==Vector2(640,70),"compact-inventory-strip")
  expect(game.pictures["young_sailor"].get_size()==Vector2(672,96),"full-resolution-actor-14-frames")
  expect(game.pictures["elder_whitebeard"].get_size()==Vector2(672,96),"full-resolution-elder-14-frames")
  expect(game.action_state=="IDLE" and game.pending=="" and not game.has_target,"clean-initial-state")
  # Single click action must clear verb/selection/pending, not create false inventory.
  game.verb="MIRAR"
  game.selected="fake"
  game._perform("elder")
  expect(game.verb=="IR","look-verb-one-shot")
  expect(game.selected=="" and game.pending=="","look-clears-stale-selection-pending")
  expect(game.action_state=="IDLE","look-resolves-finite-state")
  expect(game.finalized_action_counter==game.action_counter and game.action_counter==1,
    "look-finalization-counter")
  # Walking to an uninteresting hotspot by IR must not trigger a failed interaction.
  game.verb="IR"
  var failures_before:int=game.fail_count
  mouse(103.0,92.0)
  for i in range(180):
    if not game.has_target:break
    game._process(0.06)
  expect(not game.has_target,"plain-walk-completes")
  expect(game.fail_count==failures_before,"plain-walk-does-not-produce-failed-action")
  expect(game.pending=="" and game.route.is_empty(),"walk-does-not-leak-route")
  # Click while another route exists cancels existing intent without replay.
  game._walk_to(Vector2(270,115),"tavern_door")
  expect(game.has_target,"pending-interaction-created")
  key(KEY_ESCAPE)
  expect(not game.has_target and game.pending=="" and game.route.is_empty(),"escape-cancels-pending-route")
  expect(game.verb=="IR" and game.selected=="" and game.action_state=="IDLE",
    "escape-clears-verbs-and-selection")
  # Hover, map and help close independently; overlay clicks are not game actions.
  key(KEY_M)
  expect(game.show_map,"M-opens-big-map")
  var hero_before:Vector2=game.hero
  mouse(145,87)
  expect(not game.show_map,"click-closes-map")
  expect(game.hero.distance_to(hero_before)<0.01 and not game.has_target,
    "map-click-does-not-start-hidden-route")
  key(KEY_F1)
  expect(game.show_help and not game.show_map,"F1-help-excludes-map")
  key(KEY_ESCAPE)
  expect(not game.show_help and not game.show_map,"escape-closes-overlay")
  # A collected hotspot disappears from interaction graph.
  game.verb="COGER"
  game._perform("lens_pickup")
  expect(game._has("lens"),"collect-lens")
  expect(not game._hotspot_visible("lens_pickup"),"consumed-lens-hotspot-hidden")
  expect(game.verb=="IR" and game.selected=="" and game.action_state=="IDLE",
    "pickup-finishes-with-idle-verb")
  game.verb="COGER"
  game._perform("lens_pickup")
  expect(game.inventory.size()==1,"second-lens-collect-idempotent")
  expect(game.verb=="IR" and not game.has_target,"replayed-consumed-hotspot-clean")
  # Dialogues must not leave the previous movement route alive.
  game.verb="HABLAR"
  game._perform("elder")
  expect(game.dialogue_active and game.action_state=="DIALOGUE","elder-enters-dialogue")
  expect(game.pending=="" and not game.has_target,"dialogue-no-stale-walk")
  mouse(100,60)
  expect(not game.dialogue_active and bool(game.flags["talked"]),"dialogue-resolves-on-click")
  expect(game.verb=="IR" and game.selected=="" and game.action_state=="IDLE",
    "dialogue-finalizes-cleanly")
  # Two inventory items then independent mechanism interactions.
  game._enter("workshop")
  game._add("compass")
  game.verb="USAR"
  game.selected="lens"
  game._perform("mechanism")
  expect(bool(game.flags["lensInstalled"]) and not game._has("lens"),
    "lens-consumed-once")
  expect(game.verb=="IR" and game.selected=="" and game.action_state=="IDLE",
    "mechanism-clears-inventory-target")
  game.verb="USAR"
  game.selected="compass"
  game._perform("mechanism")
  expect(bool(game.flags["compassInstalled"]) and bool(game.flags["calibrated"]),
    "compass-mechanism-completes")
  expect(game.inventory.is_empty() and game.selected=="","both-components-consumed")
  failures_before=game.fail_count
  game.verb="USAR"
  game._perform("mechanism")
  expect(game.fail_count==failures_before,"resolved-mechanism-is-idempotent")
  expect(game.verb=="IR" and game.action_state=="IDLE","repeat-mechanism-no-verb-leak")
  # Save restores a consistent state, not a half-walk or active dialogue.
  game._walk_to(Vector2(232,110),"tavern_door")
  game.save_game()
  expect(FileAccess.file_exists(game.save_location),"QA-save-isolated-from-user")
  game._enter("harbor")
  game.verb="MIRAR"
  game.selected="compass"
  game.show_map=true
  expect(game.load_game(),"load-valid-test-save")
  expect(game.scene_id=="workshop" and bool(game.flags["calibrated"]),"load-puzzle-flags")
  expect(game.verb=="IR" and game.selected=="" and not game.dialogue_active,
    "load-cleans-pending-interaction")
  expect(not game.has_target and game.pending=="" and game.route.is_empty(),
    "load-cancels-pending-walk")
  expect(not game.show_map and not game.show_help,"load-closes-ui-overlays")
  # Finish remains compatible with original gameplay and R restart.
  game._enter("harbor")
  game.verb="USAR"
  game._perform("lighthouse")
  expect(game.completed and bool(game.flags["lit"]),"lighthouse-ending-reached")
  expect(game.action_state=="END" and game.selected=="","end-cleans-action-state")
  key(KEY_R)
  expect(not game.completed and game.action_state=="IDLE" and game.inventory.is_empty(),
    "restart-resets-game-and-inventory")
  expect(not game.has_target and game.verb=="IR" and game.pending=="" and game.route.is_empty(),
    "restart-cleans-navigation-and-verb")
  expect(game.finalized_action_counter==game.action_counter,"no-unfinalized-action-counter")
  _finish()

func _finish() -> void:
  var ok:bool=failures.is_empty()
  var report={
   "schema":1,
   "operationId":"AF.R92.FINITE-STATE-OWNER-20261108",
   "status":"PASS_R92_ACTIONS_IDEMPOTENT_AND_UI" if ok else "FAILED_R92_ACTION_OWNER",
   "checks":checks,"failures":failures,
   "userSaveUntouched":true,
   "wholeGameGeneratedByAi":false,
   "humanArtApproved":false
  }
  var out=FileAccess.open("res://qa/R92-STATE-OWNER-READBACK.json",FileAccess.WRITE)
  if out!=null:
    out.store_string(JSON.stringify(report,"\t"))
    out.flush()
    out.close()
  print("R92_STATE_OWNER "+JSON.stringify({"status":report["status"],"checks":checks.size(),"failures":failures}))
  quit(0 if ok else 4)
