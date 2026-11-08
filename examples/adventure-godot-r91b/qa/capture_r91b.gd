extends SceneTree
## R91B real OpenGL 3.3 render captures, actual running Godot main.tscn.
## No Photoshop-style reconstruction; viewport renders at 1280x720 from native 640x360 16:9.
var game: Node = null
var results: Array = []

func _initialize() -> void:
  call_deferred("_run")

func _capture(slug: String, keep_dialogue: bool = false) -> bool:
  game.bubble_left = 0.0
  if not keep_dialogue:
    game.dialogue_active = false
  game.hovered_hotspot = ""
  game.queue_redraw()
  for i in range(12):
    await process_frame
  var texture: ViewportTexture = root.get_viewport().get_texture()
  var img: Image = texture.get_image()
  if img == null or img.get_width()!=1280 or img.get_height()!=720:
    push_error("R91B_REAL_VIEWPORT_NOT_640_360")
    return false
  var output = "res://qa/R91B-REAL-GODOT-" + slug + ".png"
  if img.save_png(output)!=OK:
    return false
  results.append({"scene":slug,"path":output,"viewport":[img.get_width(),img.get_height()]})
  print("REAL_GODOT_SNAPSHOT "+slug+" "+output)
  return true

func _run() -> void:
  var main: PackedScene = load("res://main.tscn")
  if main==null:
    quit(2)
    return
  game=main.instantiate()
  root.add_child(game)
  await process_frame
  var checks: Array = []
  checks.append(await _capture("HARBOR"))
  game._enter("workshop")
  checks.append(await _capture("WORKSHOP"))
  game._enter("old_observatory")
  checks.append(await _capture("OBSERVATORY"))
  game._enter("harbor")
  game.verb="HABLAR"
  game._perform("elder")
  checks.append(await _capture("DIALOGUE",true))
  var success = checks.size()==4 and checks.all(func(v):return v==true)
  var record={
   "schema":1,"operationId":"AF.R91B.GODOT-OPENGL-CAPTURES-20261108",
   "status":"PASS_FOUR_REAL_GODOT_FRAMES" if success else "FAILED_REAL_FRAMES",
   "renderer":"OpenGL 3.3 compatibility","canvas":[1280,720],
   "sources":results,"notConceptRenders":true,"humanVisualApproval":false}
  var f=FileAccess.open("res://qa/R91B-REAL-FRAMES-RECEIPT.json",FileAccess.WRITE)
  if f != null:
    f.store_string(JSON.stringify(record))
    f.flush()
    f.close()
  print("R91B_REAL_FRAMES_RESULT "+JSON.stringify(record))
  quit(0 if success else 3)
