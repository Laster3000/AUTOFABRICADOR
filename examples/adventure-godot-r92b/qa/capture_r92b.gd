extends SceneTree
## Native Godot OpenGL screen frames, not artist mockups.
var game:Node
var saved:Array=[]
func _initialize() -> void:
  call_deferred("_run")
func _snap(name:String)->bool:
  game.queue_redraw()
  for i in range(10):
    await process_frame
  var image:Image=root.get_viewport().get_texture().get_image()
  if image==null or image.get_width()!=1280 or image.get_height()!=720:
    push_error("R92B_SCREENSHOT_NOT_ACTUAL_1280x720")
    return false
  var p:String="res://qa/R92B-REAL-GODOT-"+name+".png"
  if image.save_png(p)!=OK:
    push_error("R92B_NATIVE_GODOT_SCREENSHOT_SAVE_ERROR "+name)
    return false
  saved.append({"name":name,"size":[image.get_width(),image.get_height()],"file":p})
  print("R92B_REAL_GODOT "+name+" "+p)
  return true
func _run()->void:
  var scene:PackedScene=load("res://main.tscn")
  if scene==null:
    quit(2)
    return
  game=scene.instantiate()
  root.add_child(game)
  await process_frame
  var passed:Array=[]
  game.bubble_left=0.0
  passed.append(await _snap("PUERTO"))
  game._enter("workshop")
  game.bubble_left=0.0
  passed.append(await _snap("TALLER"))
  game._enter("old_observatory")
  game.bubble_left=0.0
  passed.append(await _snap("OBSERVATORIO"))
  game._enter("harbor")
  game.verb="HABLAR"
  game._perform("elder")
  game.bubble_left=0.0
  passed.append(await _snap("DIALOGO"))
  game.dialogue_active=false
  game.show_map=true
  game.bubble_left=0.0
  passed.append(await _snap("MAPA"))
  var ok:bool=passed.size()==5 and passed.all(func(x):return x==true)
  var doc={
    "schema":1,"operationId":"AF.R92B.FIVE-REAL-GODOT-FRAMES-20261108",
    "status":"PASS_R92B_FIVE_GODOT_OPENGL_FRAMES" if ok else "FAILED_R92B_GODOT_FRAMES",
    "native":[640,360],"display":[1280,720],
    "frames":saved,"humanArtApproved":false,
    "notConceptArt":true
  }
  var f=FileAccess.open("res://qa/R92B-REAL-FRAMES-RECEIPT.json",FileAccess.WRITE)
  if f:
    f.store_string(JSON.stringify(doc))
    f.flush()
    f.close()
  print("R92B_CAPTURE "+doc["status"])
  quit(0 if ok else 3)
