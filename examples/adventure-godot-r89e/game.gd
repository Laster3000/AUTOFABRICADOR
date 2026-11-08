extends Node2D
## AUTOFABRICADOR R89: Godot 4.6.3 16:9 original adventure runtime.
## Popochiu 2.1.1 is staged as an EDITOR ADDON; no false claim that this
## custom deterministic runtime already delegates actions to Popochiu.

const GRID = Vector2i(320, 180)
const SCENE_HEIGHT = 130
const UI_HEIGHT = 50
const VERBS = ["IR", "MIRAR", "COGER", "USAR", "HABLAR"]
const SPRITE_FRAMES = {"idle":[0,1], "walk":[2,3,4,5], "talk":[6,7], "look":[8], "pick":[9], "use":[10,11], "react":[12,13]}
const SAVE_PATH = "user://bruma_r89.json"
const REQUIRED_TEXTURES = ["harbor_back", "workshop_back", "observatory_back", "harbor_front", "workshop_front", "observatory_front", "interface", "young_sailor", "elder_whitebeard", "lens", "compass"]
var world: Dictionary = {}
var pictures: Dictionary = {}
var scene_id: String = "harbor"
var hero: Vector2 = Vector2(43,116)
var target: Vector2 = Vector2.ZERO
var has_target: bool = false
var pending: String = ""
var verb: String = "IR"
var selected: String = ""
var inventory: Array[String] = []
var flags: Dictionary = {
  "talked":false,"lensInstalled":false,"compassInstalled":false,
  "calibrated":false,"lit":false,"starAligned":false
}
var bubble: String = "La luz del faro se ha apagado."
var bubble_left: float = 8.0
var animation: String = "idle"
var animation_left: float = 0.0
var dialogue_active: bool = false
var completed: bool = false
var tick: float = 0.0
var last_action: String = "INIT"
var fail_count: int = 0

func _ready() -> void:
  texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
  world = JSON.parse_string(FileAccess.get_file_as_string("res://game_data.json"))
  if typeof(world) != TYPE_DICTIONARY:
    push_error("R89 WORLD_JSON_INVALID")
    get_tree().quit(2)
    return
  for name in REQUIRED_TEXTURES:
    var path := "res://assets/%s.png" % name
    var loaded = load(path)
    if loaded == null:
      push_error("R89 ASSET_MISSING " + name)
      get_tree().quit(2)
      return
    pictures[name] = loaded
  set_process(true)
  queue_redraw()

func _process(delta: float) -> void:
  tick += delta
  bubble_left = maxf(0.0,bubble_left-delta)
  animation_left = maxf(0.0,animation_left-delta)
  if has_target and not completed and not dialogue_active:
    var distance := hero.distance_to(target)
    var travel := 58.0*delta
    if distance <= travel:
      hero = target
      has_target = false
      animation = "idle"
      if not pending.is_empty():
        var action_id := pending
        pending = ""
        _perform(action_id)
    else:
      hero = hero.move_toward(target,travel)
      animation = "walk"
  elif animation_left <= 0.0:
    animation = "idle"
  queue_redraw()

func _say(message: String, seconds: float = 5.0) -> void:
  bubble = message
  bubble_left = seconds
  queue_redraw()

func _animate(action: String, seconds: float = 0.6) -> void:
  animation = action
  animation_left = seconds

func _in_polygon(points: Array, pos: Vector2) -> bool:
  var found := false
  var length := points.size()
  for i in range(length):
    var a: Array = points[i]
    var b: Array = points[(i+1)%length]
    var ax := float(a[0])
    var ay := float(a[1])
    var bx := float(b[0])
    var by := float(b[1])
    if ((ay>pos.y) != (by>pos.y)) and pos.x < ((bx-ax)*(pos.y-ay)/(by-ay)+ax):
      found = not found
  return found

func _hotspot(pos: Vector2) -> Dictionary:
  var spots: Array = world["scenes"][scene_id]["hotspots"]
  for i in range(spots.size()-1,-1,-1):
    var spot: Dictionary = spots[i]
    if _in_polygon(spot["polygon"],pos):
      return spot
  return {}

func _walk_to(pos: Vector2, after: String = "") -> void:
  target = Vector2(clampf(pos.x,4.0,315.0),clampf(pos.y,92.0,128.0))
  has_target = true
  pending = after
  animation = "walk"

func _input(event: InputEvent) -> void:
  if event is InputEventKey and event.pressed:
    var key: InputEventKey = event
    if key.keycode >= KEY_1 and key.keycode <= KEY_5:
      verb = VERBS[int(key.keycode)-int(KEY_1)]
      selected = ""
    elif key.keycode == KEY_F5:
      save_game()
    elif key.keycode == KEY_F9:
      load_game()
    elif key.keycode == KEY_ESCAPE:
      dialogue_active = false
      _say("Volvemos a la aventura.")
    queue_redraw()
    return
  if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
    var mouse: Vector2 = event.position
    if completed:
      return
    if dialogue_active:
      if mouse.y >= 26.0 and mouse.y <= 88.0:
        flags["talked"] = true
        dialogue_active = false
        _say("El faro necesita una lente y una brujula para orientarse.",8.0)
        _animate("talk",1.0)
      return
    if mouse.x < 0 or mouse.x >= 320 or mouse.y < 0 or mouse.y >= 180:
      return
    if mouse.y >= 130:
      if mouse.y < 153:
        var slot: int = clampi(int(mouse.x/64),0,4)
        verb = VERBS[slot]
        if verb != "USAR":
          selected = ""
      else:
        var inventory_slot: int = int(mouse.x/50)
        if inventory_slot < inventory.size():
          selected = inventory[inventory_slot]
          verb = "USAR"
          _say("Usar objeto con...",3.0)
    else:
      var hot := _hotspot(mouse)
      if hot.is_empty():
        _walk_to(mouse)
      else:
        var target_pos: Array = hot["walkTo"]
        _walk_to(Vector2(float(target_pos[0]),float(target_pos[1])),str(hot["id"]))
    queue_redraw()

func _has(item: String) -> bool:
  return item in inventory

func _add(item: String) -> void:
  if not _has(item):
    inventory.append(item)

func _remove(item: String) -> void:
  inventory.erase(item)

func _enter(which: String) -> void:
  if not which in ["harbor","workshop","old_observatory"]:
    push_error("R89 UNKNOWN ROOM "+which)
    return
  scene_id = which
  hero = Vector2(74,116) if which == "harbor" else (Vector2(286,116) if which == "workshop" else Vector2(45,113))
  has_target = false
  selected = ""
  _say("Regresas al puerto." if which=="harbor" else ("Has llegado al taller." if which=="workshop" else str(world["AIOriginalNarrative"]["summary"])),5.0)

func _perform(hot_id: String) -> void:
  last_action = verb+":"+hot_id
  if verb=="MIRAR":
    if hot_id=="constellations":
      _say(str(world["AIOriginalNarrative"]["elderHint"]),8.0)
    elif hot_id=="elder":
      _say("El anciano observa el mar bajo una barba blanca.",6.0)
    elif hot_id=="mechanism":
      _say("La maquinaria solo funciona con una lente y una brujula.",6.0)
    else:
      _say("Un detalle curioso del puerto de Bruma.",4.0)
    _animate("look")
    return
  if verb=="HABLAR" and hot_id=="elder":
    dialogue_active=true
    _animate("talk",1.0)
    return
  if verb=="COGER" and hot_id=="lens_pickup":
    if bool(flags["lensInstalled"]):
      _say("La lente ya esta colocada en la maquinaria.")
    elif _has("lens"):
      _say("Llevas la lente contigo.")
    else:
      _add("lens")
      _say("Guardas la lente de laton.",4.0)
      _animate("pick")
    return
  if verb=="COGER" and hot_id=="compass_pickup":
    if bool(flags["compassInstalled"]):
      _say("La brujula ya esta montada.")
    elif _has("compass"):
      _say("Llevas la brujula contigo.")
    else:
      _add("compass")
      _say("Has encontrado una brujula de mar.",4.0)
      _animate("pick")
    return
  if verb in ["IR","ABRIR"] and hot_id=="tavern_door":
    _enter("workshop")
    return
  if verb in ["IR","ABRIR"] and hot_id=="exit_door":
    _enter("harbor")
    return
  if verb=="IR" and hot_id=="observatory_stairs":
    _enter("old_observatory")
    return
  if verb in ["IR","ABRIR"] and hot_id=="back_stairs":
    _enter("workshop")
    return
  if verb=="MIRAR" and hot_id=="constellations":
    _say(str(world["AIOriginalNarrative"]["elderHint"]),8.0)
    return
  if verb=="USAR" and hot_id=="telescope":
    if not bool(flags["calibrated"]):
      _say("Primero orienta el mecanismo del taller.",6.0)
      fail_count+=1
      return
    flags["starAligned"]=true
    _say(str(world["AIOriginalNarrative"]["successLine"]),9.0)
    _animate("use",0.9)
    return
  if verb=="USAR" and hot_id=="mechanism":
    if selected=="lens" and _has("lens") and not bool(flags["lensInstalled"]):
      flags["lensInstalled"]=true
      _remove("lens")
      selected=""
      _animate("use")
      _say("La lente encaja en el mecanismo.")
      return
    if selected=="compass" and _has("compass") and not bool(flags["compassInstalled"]):
      flags["compassInstalled"]=true
      _remove("compass")
      selected=""
      flags["calibrated"]=bool(flags["lensInstalled"]) and bool(flags["compassInstalled"])
      _animate("use")
      _say("Ahora el mecanismo esta calibrado." if bool(flags["calibrated"]) else "Aun falta una lente.")
      return
    _say("La maquina necesita una lente y una brujula.",7.0)
    fail_count += 1
    return
  if verb=="USAR" and hot_id=="lighthouse":
    if not bool(flags["calibrated"]):
      _say("Primero debes reparar el mecanismo del taller.",6.0)
      fail_count += 1
      return
    flags["lit"]=true
    completed=true
    _say("El faro ilumina la costa. Has salvado Bruma.",15.0)
    return
  _say("Eso no produce ningun cambio.",4.0)
  fail_count += 1

func save_game() -> bool:
  var payload = {
    "schema":1,"scene":scene_id,"inventory":inventory,
    "flags":flags,"hero":[hero.x,hero.y],"completed":completed
  }
  var path: String = SAVE_PATH
  var file := FileAccess.open(path,FileAccess.WRITE)
  if file==null:
    _say("No se puede guardar la partida.",6.0)
    return false
  file.store_string(JSON.stringify(payload))
  file.flush()
  file.close()
  _say("Partida guardada.",4.0)
  return true

func load_game() -> bool:
  if not FileAccess.file_exists(SAVE_PATH):
    _say("No existe una partida guardada.",4.0)
    return false
  var data = JSON.parse_string(FileAccess.get_file_as_string(SAVE_PATH))
  if typeof(data)!=TYPE_DICTIONARY or data.get("schema")!=1:
    _say("Guardado incompatible.",4.0)
    return false
  if not str(data.get("scene","")) in ["harbor","workshop","old_observatory"]:
    return false
  if typeof(data.get("inventory",null))!=TYPE_ARRAY or typeof(data.get("flags",null))!=TYPE_DICTIONARY:
    return false
  var opts: Array = data["inventory"]
  for entry in opts:
    if not entry in ["lens","compass"]:
      return false
  var fs: Dictionary = data["flags"]
  for flag in flags.keys():
    if typeof(fs.get(flag,null))!=TYPE_BOOL:
      return false
  if bool(fs["calibrated"]) and not (bool(fs["lensInstalled"]) and bool(fs["compassInstalled"])):
    return false
  if bool(fs["lit"]) and not bool(fs["calibrated"]):
    return false
  var pos: Array = data.get("hero",[])
  if pos.size()!=2 or typeof(pos[0]) not in [TYPE_FLOAT,TYPE_INT] or typeof(pos[1]) not in [TYPE_FLOAT,TYPE_INT]:
    return false
  scene_id=str(data["scene"])
  inventory.clear()
  for item in opts:
    if not str(item) in inventory:
      inventory.append(str(item))
  flags=fs.duplicate(true)
  hero=Vector2(clampf(float(pos[0]),4.0,315.0),clampf(float(pos[1]),92.0,128.0))
  completed=bool(data.get("completed",false))
  selected=""
  has_target=false
  pending=""
  _say("Partida recuperada.",4.0)
  return true

func owner_snapshot() -> Dictionary:
  return {
    "scene":scene_id,"inventory":inventory.duplicate(),
    "flags":flags.duplicate(true),"hero":[hero.x,hero.y],
    "dialogue":dialogue_active,"completed":completed,
    "lastAction":last_action,"failCount":fail_count,"aspect":"16:9"
  }

func _draw_sprite(name: String, x: float,y: float, frame: int=0) -> void:
  if not pictures.has(name):
    return
  var tex: Texture2D = pictures[name]
  if name in ["young_sailor","elder_whitebeard"]:
    draw_texture_rect_region(tex,Rect2(x-12,y-47,24,48),Rect2(frame*24,0,24,48))
  else:
    draw_texture(tex,Vector2(x,y))

func _label(text: String, pos: Vector2, color: Color = Color("#f0d7ac"), font_size: int = 8) -> void:
  var font: Font = ThemeDB.fallback_font
  draw_string(font,pos,text,HORIZONTAL_ALIGNMENT_LEFT,-1,font_size,color)

func _draw() -> void:
  if pictures.is_empty() or world.is_empty():
    return
  draw_texture(pictures[world["sceneBackgrounds"][scene_id]],Vector2.ZERO)
  if scene_id=="harbor":
    if not _has("lens") and not bool(flags["lensInstalled"]):
      _draw_sprite("lens",98,95)
    var elder_frame: int=0 if (int(tick*2.2)%2)==0 else 1
    _draw_sprite("elder_whitebeard",168,117,elder_frame)
    if bool(flags["lit"]):
      draw_rect(Rect2(283,36,11,4),Color("#fff3b7"))
      draw_rect(Rect2(294,37,26,2),Color("#f3d18b"))
  elif scene_id=="workshop":
    if not _has("compass") and not bool(flags["compassInstalled"]):
      _draw_sprite("compass",83,99)
    if bool(flags["lensInstalled"]):
      draw_rect(Rect2(250,84,6,5),Color("#92edce"))
    if bool(flags["compassInstalled"]):
      draw_rect(Rect2(241,83,5,3),Color("#f6cf87"))
  else:
    if bool(flags["starAligned"]):
      draw_rect(Rect2(250,39,4,4),Color("#fdf0ba"))
  var active_frames: Array = SPRITE_FRAMES.get(animation,SPRITE_FRAMES["idle"])
  var index: int=int(tick*6.0)%active_frames.size()
  _draw_sprite("young_sailor",hero.x,hero.y)
  var foreground_name: String = "harbor_front" if scene_id=="harbor" else ("workshop_front" if scene_id=="workshop" else "observatory_front")
  if pictures.has(foreground_name):
    draw_texture(pictures[foreground_name],Vector2.ZERO)
  if bubble_left>0.0:
    draw_rect(Rect2(6,5,308,29),Color("#0a1024"))
    draw_line(Vector2(7,6),Vector2(313,6),Color("#d0a671"),1.0)
    var words:=bubble.split(" ")
    var lines: Array[String]=[]
    var current: String=""
    for word in words:
      if current.length()+word.length()+1>58:
        lines.append(current)
        current=word
      else:
        current+=((" " if not current.is_empty() else "")+word)
    lines.append(current)
    for i in range(mini(3,lines.size())):
      _label(lines[i],Vector2(11,14+8*i),Color("#f5ddaf"),7)
  draw_texture(pictures["interface"],Vector2(0,130))
  for i in range(VERBS.size()):
    if VERBS[i]==verb:
      draw_rect(Rect2(i*64+3,136,57,15),Color("#ac7e62"))
    _label(VERBS[i],Vector2(i*64+6,147),Color("#ffdf9b") if VERBS[i]==verb else Color("#d6b88d"),8)
  for i in range(mini(6,inventory.size())):
    if inventory[i]==selected:
      draw_rect(Rect2(i*50+3,154,46,20),Color("#865358"))
    _draw_sprite(inventory[i],float(i*50+8),155)
    _label("LENTE" if inventory[i]=="lens" else "BRUJULA",Vector2(i*50+28,166),Color("#f3ddba"),6)
  _label("PUERTO DE BRUMA" if scene_id=="harbor" else ("TALLER DEL FARO" if scene_id=="workshop" else "OBSERVATORIO"),Vector2(169,178),Color("#dabb8b"),7)
  if dialogue_active:
    draw_rect(Rect2(36,22,250,76),Color("#10162b"))
    draw_rect(Rect2(36,22,250,2),Color("#c6a271"))
    _label("El guardafaro:",Vector2(44,39),Color("#ffe7af"),10)
    _label("¿Por que el faro se ha apagado?",Vector2(44,60),Color("#f6ddb4"),8)
    _label("Haz clic aqui para preguntar.",Vector2(44,79),Color("#edbe93"),7)
  if completed:
    draw_rect(Rect2(37,47,246,54),Color("#12182c"))
    _label("LA LUZ DE BRUMA",Vector2(67,67),Color("#ffe6b3"),14)
    _label("FIN DEL PROLOGO",Vector2(93,88),Color("#f1c583"),8)
