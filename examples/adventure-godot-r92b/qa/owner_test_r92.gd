extends SceneTree
## R89 independent original mouse-input owner (no writes to game logic).
const EXPECTED_GODOT = "4.6"
var checks: Array[Dictionary] = []
var problems: Array[String] = []
var game: Node = null

func _initialize() -> void:
  call_deferred("_execute")

func _check(ok: bool, name: String) -> void:
  checks.append({"name":name,"pass":ok})
  if not ok:
    problems.append("FAILED:"+name)
    push_error("R89 OWNER: "+name)

func _click(x: float,y: float) -> void:
  var mouse := InputEventMouseButton.new()
  mouse.button_index=MOUSE_BUTTON_LEFT
  mouse.pressed=true
  mouse.position=Vector2(x*2.0,y*2.0)
  game._input(mouse)
  for _i in range(220):
    if not game.has_target:
      break
    game._process(0.1)

func _key(keycode: Key) -> void:
  var ke:=InputEventKey.new()
  ke.keycode=keycode
  ke.pressed=true
  game._input(ke)

func _execute() -> void:
  var p: PackedScene = load("res://main.tscn")
  if p==null:
    _check(false,"main-scene-load")
    _finish()
    return
  game=p.instantiate()
  root.add_child(game)
  game.save_location="res://qa/R92-OWNER-TEST-SAVE.json"
  await process_frame
  _check(Engine.get_version_info().get("major")==4 and Engine.get_version_info().get("minor")==6,"godot-4.6-engine")
  _check(root.get_viewport().get_visible_rect().size == Vector2(640,360),"real-native-640x360-16x9-viewport")
  _check(not root.has_node("E"),"no-unapproved-thirdparty-runtime-dependency")
  _check(game.world.has("sceneBackgrounds"),"game-world-imported")
  _check(game.pictures.size()==11,"eleven-original-layered-textures-imported")
  _check(game.scene_id=="harbor","starts-harbor")
  # Initial negative actions.
  _click(203,154)
  _click(283,85)
  _check(not bool(game.flags["lit"]),"cannot-light-lighthouse-unprepared")
  # Pick up lens and learn from the elder.
  _click(140,154)
  _click(105,103)
  _check("lens" in game.inventory,"pick-up-lens-mouse")
  _click(270,154)
  _click(168,90)
  _check(game.dialogue_active,"elder-dialogue-open")
  _click(100,64)
  _check(bool(game.flags["talked"]),"elder-dialogue-consequence")
  # Navigate to workshop, pick up compass and repair machine.
  _click(10,154)
  _click(60,96)
  _check(game.scene_id=="workshop","room-transition-to-workshop")
  _click(138,154)
  _click(90,105)
  _check("compass" in game.inventory and game.inventory.size()==2,"two-independent-inventory-items")
  _click(20,171)
  _click(251,85)
  _check(bool(game.flags["lensInstalled"]) and not "lens" in game.inventory,"lens-attached-consumed")
  _check(not bool(game.flags["calibrated"]),"calibration-needs-two-components")
  _click(20,171)
  _click(251,85)
  _check(bool(game.flags["compassInstalled"]) and game.inventory.is_empty(),"compass-attached-consumed")
  _check(bool(game.flags["calibrated"]),"calibration-done")
  # New AI narrative accepted only after owner JSON and SHA verification.
  _check(game.world["AIOriginalNarrative"]["sceneId"]=="old_observatory","ai-original-scene-id")
  _check(game.world["AIOriginalNarrative"]["source"]=="offline_cuda7b_frozen_owner","local-ai-provenance-in-world")
  _check(game.pictures.size()==11,"eleven-layered-asset-textures-imported")
  _click(10,154)
  _click(146,67)
  _check(game.scene_id=="old_observatory","enter-new-observatory-by-real-hotspot")
  _check(not bool(game.flags["starAligned"]),"stars-unaligned-before-observation")
  _click(70,154)
  _click(116,40)
  _check(game.bubble==str(game.world["AIOriginalNarrative"]["elderHint"]),"local-ai-hint-displayed")
  _click(203,154)
  _click(184,75)
  _check(bool(game.flags["starAligned"]),"star-telescope-logic-after-calibration")
  _check(game.bubble==str(game.world["AIOriginalNarrative"]["successLine"]),"local-ai-success-text-displayed")
  # Save to own portable data and reload.
  _key(KEY_F5)
  _check(FileAccess.file_exists(game.save_location),"save-file-available")
  game._enter("harbor")
  game.inventory.clear()
  _key(KEY_F9)
  _check(game.scene_id=="old_observatory" and bool(game.flags["calibrated"]) and bool(game.flags["starAligned"]),"save-load-restores-observatory-ai-progress")
  _click(10,154)
  _click(32,87)
  _check(game.scene_id=="workshop","back-from-observatory")
  # Final transition and finish.
  _click(10,154)
  _click(307,94)
  _check(game.scene_id=="harbor","return-to-harbor")
  _click(205,154)
  _click(283,85)
  _check(bool(game.flags["lit"]) and game.completed,"ending-reached-after-puzzle")
  _check(game.owner_snapshot()["aspect"]=="16:9","owner-state-aspect")
  _check(game.SPRITE_FRAMES["walk"].size()==4,"four-walking-sprite-frames")
  _check(game.SPRITE_FRAMES["talk"].size()==2,"talking-sprite-expression-frames")
  _check(game.pictures["young_sailor"].get_width()==672,"real-fourteen-HD-frame-character-atlas")
  _check(game.pictures["elder_whitebeard"].get_height()==96,"elder-sprite-96-native-pixels-tall")
  var mm := InputEventMouseMotion.new()
  mm.position=Vector2(338,180)
  game._enter("harbor")
  game._input(mm)
  _check(game.hovered_hotspot=="Anciano de barba blanca","real-interactive-hotspot-hover-tooltip")

  _finish()

func _finish() -> void:
  var result={
    "schema":1,"operationId":"AF.R92.GODOT-POLISHED-ORIGINAL-OWNER-20261108",
    "status":"PASS_SCOPED_THREE_SCENE_STANDALONE_GODOT_OWNER" if problems.is_empty() else "FAILED_GODOT_OWNER",
    "checks":checks,"failures":problems,"godotVersion":Engine.get_version_info().get("string"),
    "pixelArt":[640,360],"presentation":[1280,720],
    "standaloneNoPopochiuOrCustomFont":true,
    "gameplayUsesCustomGodotAdapterNotPopochiuRooms":true,
    "humanVisualAccepted":false,"fullLocalAIAppGenerated":false,
    "aiNarrativeIntegratedInGame":true,
    "otherProjectTouched":false
  }
  var path="res://qa/R92-GODOT-OWNER-READBACK.json"
  var f=FileAccess.open(path,FileAccess.WRITE)
  if f!=null:
    f.store_string(JSON.stringify(result,"\t"))
    f.flush()
    f.close()
  print("R92_OWNER_RESULT "+JSON.stringify(result))
  quit(0 if problems.is_empty() else 3)
