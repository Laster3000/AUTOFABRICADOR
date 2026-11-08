extends Node2D
## AUTOFABRICADOR R92: authored pixel art + finite-state interactions + accessible 16:9.
## Popochiu 2.1.1 is staged as an EDITOR ADDON; no false claim that this
## custom deterministic runtime already delegates actions to Popochiu.

const GRID = Vector2i(640, 360)
const LOGICAL_GRID = Vector2i(320,180)
const Navigation = preload("res://adventure_nav_r91.gd")
const SCENE_HEIGHT = 145
const UI_HEIGHT = 35
const VERBS = ["IR", "MIRAR", "COGER", "USAR", "HABLAR"]
const SPRITE_FRAMES = {"idle":[0,1], "walk":[2,3,4,5], "talk":[6,7], "look":[8], "pick":[9], "use":[10,11], "react":[12,13]}
const SAVE_PATH = "user://bruma_r92.json"
const PREV_SAVE_PATH = "user://bruma_r91.json"
const LEGACY_SAVE_PATH = "user://bruma_r89.json"
var save_location: String = SAVE_PATH
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
var hovered_hotspot: String = ""
var fail_count: int = 0
var navigation: Dictionary = {}
var nav_section: Dictionary = {}
var route: Array[Vector2] = []
var show_help: bool = false
var show_map: bool = false
var action_state: String = "IDLE"
var action_counter: int = 0
var finalized_action_counter: int = 0
var player_facing: int = 1
var last_reachable_click: Vector2 = Vector2.ZERO

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
  navigation = JSON.parse_string(FileAccess.get_file_as_string("res://navigation_r91.json"))
  if typeof(navigation)!=TYPE_DICTIONARY or not Navigation.validate_contract(navigation):
    push_error("R91_NAVIGATION_CONTRACT_INVALID")
    get_tree().quit(2)
    return
  nav_section=navigation["scenes"][scene_id]
  hero=Navigation.nearest_point(nav_section,hero)
  if hero.x<0:
    push_error("R91_START_NOT_ON_WALKMESH")
    get_tree().quit(2)
    return
  set_process(true)
  queue_redraw()

func _process(delta: float) -> void:
  tick += delta
  bubble_left = maxf(0.0,bubble_left-delta)
  animation_left = maxf(0.0,animation_left-delta)
  if has_target and not completed and not dialogue_active and not show_map and not show_help:
    var remaining:=62.0*minf(delta,0.25)
    var steps:=0
    while has_target and remaining>0.0001 and steps<256:
      steps+=1
      if route.is_empty():
        _end_walk()
        break
      var next: Vector2=route[0]
      var distance: float=hero.distance_to(next)
      if distance<=remaining+0.001:
        hero=next
        remaining=maxf(0.0,remaining-distance)
        route.pop_front()
        if route.is_empty():
          _end_walk()
      else:
        var new_pos:Vector2=hero.move_toward(next,remaining)
        if not Navigation.allowed(nav_section,new_pos):
          _stop_walk("No se puede pisar ese lugar.")
          break
        player_facing=1 if new_pos.x>=hero.x else -1
        hero=new_pos
        remaining=0.0
        animation="walk"
  elif animation_left<=0.0:
    animation="idle"

func _end_walk() -> void:
  has_target=false
  route.clear()
  animation="idle"
  target=Vector2.ZERO
  action_state="IDLE"
  if not pending.is_empty():
    var action_id:=pending
    pending=""
    _perform(action_id)

func _stop_walk(reason: String) -> void:
  _clear_pending_action(true)
  _say(reason,4.0)
  queue_redraw()

func _clear_pending_action(clear_verb: bool=true) -> void:
  has_target=false
  pending=""
  route.clear()
  target=Vector2.ZERO
  animation="idle"
  animation_left=0.0
  action_state="IDLE"
  hovered_hotspot=""
  if clear_verb:
    verb="IR"
    selected=""

func _finish_action() -> void:
  # Verbs and selected inventory are one-shot, never leak into the next click.
  action_counter+=1
  finalized_action_counter=action_counter
  has_target=false
  pending=""
  route.clear()
  target=Vector2.ZERO
  hovered_hotspot=""
  selected=""
  verb="IR"
  action_state="DIALOGUE" if dialogue_active else ("END" if completed else "IDLE")
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

func _hotspot_visible(id: String) -> bool:
  if id=="lens_pickup":
    return not _has("lens") and not bool(flags["lensInstalled"])
  if id=="compass_pickup":
    return not _has("compass") and not bool(flags["compassInstalled"])
  return true

func _hotspot(pos: Vector2) -> Dictionary:
  var spots: Array = world["scenes"][scene_id]["hotspots"]
  for i in range(spots.size()-1,-1,-1):
    var spot: Dictionary = spots[i]
    if not _hotspot_visible(str(spot["id"])):
      continue
    if _in_polygon(spot["polygon"],pos):
      return spot
  return {}

func _walk_to(pos: Vector2, after: String = "") -> void:
  if completed:
    return
  var reached:=Navigation.nearest_point(nav_section,pos)
  if reached.x<0:
    _stop_walk("El lugar no tiene un camino seguro.")
    return
  var path:Array[Vector2]=Navigation.find_path(nav_section,hero,reached)
  if path.is_empty():
    if hero.distance_to(reached)<2.0:
      if not after.is_empty():
        _perform(after)
    else:
      _stop_walk("No encuentro un camino.")
    return
  route=path
  target=path.back()
  last_reachable_click=reached
  has_target=true
  pending=after
  action_state="WALKING"
  animation="walk"

func _input(event: InputEvent) -> void:
  if event is InputEventMouseMotion:
    var pointer: Vector2 = event.position / 2.0
    hovered_hotspot = ""
    if pointer.x >= 0 and pointer.x < 320 and pointer.y >= 0 and pointer.y < SCENE_HEIGHT:
      var obj: Dictionary = _hotspot(pointer)
      if not obj.is_empty():
        hovered_hotspot = str(obj["name"])
    queue_redraw()
    return
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
      if dialogue_active:
        dialogue_active=false
        _finish_action()
        _say("Volvemos a la aventura.",2.5)
      elif show_map or show_help:
        show_map=false
        show_help=false
      else:
        _clear_pending_action(true)
        _say("Accion cancelada.",2.0)
    elif key.keycode == KEY_F1:
      show_help=not show_help
      show_map=false
    elif key.keycode == KEY_M:
      show_map=not show_map
      show_help=false
    elif key.keycode == KEY_F11:
      var window=get_window()
      window.mode=Window.MODE_WINDOWED if window.mode==Window.MODE_FULLSCREEN else Window.MODE_FULLSCREEN
    elif key.keycode == KEY_R and completed:
      restart_game()
    queue_redraw()
    return
  if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
    var mouse: Vector2 = event.position / 2.0
    if show_map:
      show_map=false
      queue_redraw()
      return
    if show_help:
      show_help=false
      queue_redraw()
      return
    if completed:
      return
    if dialogue_active:
      if mouse.y >= 26.0 and mouse.y <= 88.0:
        flags["talked"] = true
        dialogue_active=false
        _say("El faro necesita una lente y una brujula para orientarse.",6.0)
        _animate("talk",0.55)
        _finish_action()
      return
    if mouse.x < 0 or mouse.x >= 320 or mouse.y < 0 or mouse.y >= 180:
      return
    if mouse.y >= SCENE_HEIGHT:
      _clear_pending_action(false)
      if mouse.y < 162:
        var slot: int = clampi(int(mouse.x/64),0,4)
        verb = VERBS[slot]
        if verb != "USAR":
          selected = ""
      else:
        var inventory_slot:int=int(mouse.x/50)
        if inventory_slot<inventory.size():
          selected=inventory[inventory_slot]
          verb="USAR"
          action_state="SELECTED"
          _say("Objeto elegido: "+("lente" if selected=="lens" else "brujula")+".",2.2)
        else:
          selected=""
          verb="IR"
    else:
      var hot := _hotspot(mouse)
      if hot.is_empty():
        _walk_to(mouse)
      else:
        var target_pos:Array=hot["walkTo"]
        var is_transition:bool=str(hot["id"]) in ["tavern_door","exit_door","observatory_stairs","back_stairs"]
        var perform_id:String=str(hot["id"]) if verb!="IR" or is_transition else ""
        _walk_to(Vector2(float(target_pos[0]),float(target_pos[1])),perform_id)
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
  scene_id=which
  nav_section=navigation["scenes"][scene_id]
  var spawn:Array=nav_section["start"]
  hero=Navigation.nearest_point(nav_section,Vector2(float(spawn[0]),float(spawn[1])))
  route.clear()
  has_target=false
  pending=""
  selected=""
  hovered_hotspot=""
  verb="IR"
  animation="idle"
  animation_left=0.0
  dialogue_active=false
  action_state="IDLE"
  _say("Regresas al puerto." if which=="harbor" else ("Has llegado al taller." if which=="workshop" else str(world["AIOriginalNarrative"]["summary"])),5.0)

func _perform(hot_id: String) -> void:
  if not _hotspot_visible(hot_id):
    _clear_pending_action(true)
    return
  last_action=verb+":"+hot_id
  _resolve_action(hot_id)
  _finish_action()

func _resolve_action(hot_id: String) -> void:
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
    if bool(flags["calibrated"]):
      _say("La maquinaria ya esta reparada.",3.0)
      return
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
  var path: String = save_location
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
  if not FileAccess.file_exists(save_location) and not FileAccess.file_exists(PREV_SAVE_PATH) and not FileAccess.file_exists(LEGACY_SAVE_PATH):
    _say("No existe una partida guardada.",4.0)
    return false
  var source_path:=save_location if FileAccess.file_exists(save_location) else (PREV_SAVE_PATH if FileAccess.file_exists(PREV_SAVE_PATH) else LEGACY_SAVE_PATH)
  var data=JSON.parse_string(FileAccess.get_file_as_string(source_path))
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
  nav_section=navigation["scenes"][scene_id]
  hero=Navigation.nearest_point(nav_section,Vector2(float(pos[0]),float(pos[1])))
  if hero.x<0:
    return false
  completed=bool(data.get("completed",false))
  selected=""
  has_target=false
  route.clear()
  pending=""
  target=Vector2.ZERO
  animation="idle"
  animation_left=0.0
  verb="IR"
  hovered_hotspot=""
  dialogue_active=false
  show_map=false
  show_help=false
  action_state="END" if completed else "IDLE"
  _say("Partida recuperada.",3.0)
  return true

func restart_game() -> void:
  scene_id="harbor"
  nav_section=navigation["scenes"][scene_id]
  var spawn:Array=nav_section["start"]
  hero=Navigation.nearest_point(nav_section,Vector2(float(spawn[0]),float(spawn[1])))
  route.clear()
  has_target=false
  pending=""
  selected=""
  inventory.clear()
  completed=false
  dialogue_active=false
  for k in flags.keys():
    flags[k]=false
  verb="IR"
  hovered_hotspot=""
  animation="idle"
  animation_left=0.0
  target=Vector2.ZERO
  show_map=false
  show_help=false
  action_state="IDLE"
  _say("Una nueva aventura comienza.",3.0)

func owner_snapshot() -> Dictionary:
  return {
    "scene":scene_id,"inventory":inventory.duplicate(),
    "flags":flags.duplicate(true),"hero":[hero.x,hero.y],
    "dialogue":dialogue_active,"completed":completed,
    "lastAction":last_action,"failCount":fail_count,"aspect":"16:9",
    "insideWalkmesh":Navigation.allowed(nav_section,hero),
    "routeWaypoints":route.size(),"native":[640,360],"logical":[320,180],
    "selected":selected,"verb":verb,"actionState":action_state,
    "actionCounter":action_counter,"finalizedActionCounter":finalized_action_counter
  }

func _draw_sprite(name: String, x: float,y: float, frame: int=0) -> void:
  if not pictures.has(name):
    return
  var tex: Texture2D = pictures[name]
  if name in ["young_sailor","elder_whitebeard"]:
    var scale:float=1.0 if name=="elder_whitebeard" else clampf(0.91+(y-105.0)*0.006,0.91,1.09)
    draw_texture_rect_region(tex,Rect2(x-17.0*scale,y-64.0*scale,34.0*scale,64.0*scale),
      Rect2(float(frame*48),0.0,48.0,96.0))
  else:
    draw_texture_rect(tex,Rect2(x,y,16.0,16.0),false)

func _draw_hero(frame: int) -> void:
  var scale:float=clampf(0.91+(hero.y-105.0)*0.006,0.91,1.09)
  draw_circle(Vector2(hero.x,hero.y-1.0),8.0*scale,Color("#0d162a36"))
  _draw_sprite("young_sailor",hero.x,hero.y,frame)

func _label(text: String, pos: Vector2, color: Color = Color("#f0d7ac"), font_size: int = 8) -> void:
  var font: Font = ThemeDB.fallback_font
  draw_string(font,pos,text,HORIZONTAL_ALIGNMENT_LEFT,-1,font_size,color)

func _draw() -> void:
  if pictures.is_empty() or world.is_empty():
    return
  draw_set_transform(Vector2.ZERO,0.0,Vector2(2,2))
  draw_texture_rect(pictures[world["sceneBackgrounds"][scene_id]],Rect2(0,0,320,145),false)
  if scene_id=="harbor":
    if not _has("lens") and not bool(flags["lensInstalled"]):
      _draw_sprite("lens",98,95)
    pass # Elder is depth-sorted with player lower down.
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
  var player_first:bool=(scene_id=="harbor" and hero.y<=116.5)
  if player_first:
    _draw_hero(int(active_frames[index]))
  if scene_id=="harbor":
    draw_circle(Vector2(168,116),7.0,Color("#0d162a55"))
    var elder_frame:int=0 if int(tick*2.2)%2==0 else 1
    _draw_sprite("elder_whitebeard",168,117,elder_frame)
  if not player_first:
    _draw_hero(int(active_frames[index]))
  var foreground_name: String = "harbor_front" if scene_id=="harbor" else ("workshop_front" if scene_id=="workshop" else "observatory_front")
  if pictures.has(foreground_name):
    draw_texture_rect(pictures[foreground_name],Rect2(0,0,320,145),false)
  # R92 intentionally removes ad hoc shimmer lines that appeared as visual artifacts.
  if not hovered_hotspot.is_empty() and not dialogue_active and not completed:
    draw_rect(Rect2(8,111,168,15),Color("#1a233c"))
    draw_line(Vector2(8,111),Vector2(176,111),Color("#d6a779"),1.0)
    _label(hovered_hotspot,Vector2(13,121),Color("#f7d9a8"),8)
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
  draw_texture_rect(pictures["interface"],Rect2(0,145,320,35),false)
  for i in range(VERBS.size()):
    if VERBS[i]==verb:
      draw_rect(Rect2(i*64+3,149,57,12),Color("#ac7e62"))
    _label(VERBS[i],Vector2(i*64+6,159),Color("#ffdf9b") if VERBS[i]==verb else Color("#d6b88d"),8)
  for i in range(mini(6,inventory.size())):
    if inventory[i]==selected:
      draw_rect(Rect2(i*50+3,164,46,15),Color("#865358"))
    _draw_sprite(inventory[i],float(i*50+5),161)
    _label("LENTE" if inventory[i]=="lens" else "BRUJULA",Vector2(i*50+22,173),Color("#f3ddba"),7)
  _label("PUERTO DE BRUMA" if scene_id=="harbor" else ("TALLER DEL FARO" if scene_id=="workshop" else "OBSERVATORIO"),Vector2(213,174),Color("#dabb8b"),7)
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
    _label("R PARA REINICIAR",Vector2(80,96),Color("#f1c583"),7)
  if show_help:
    draw_rect(Rect2(18,35,286,93),Color("#13192fe9"))
    draw_rect(Rect2(18,35,286,2),Color("#debb80"))
    _label("AYUDA / F1 PARA CERRAR",Vector2(43,50),Color("#ffe6b3"),10)
    _label("1-5 elegir verbo - clic caminar e interactuar",Vector2(27,67),Color("#f6deb0"),8)
    _label("F5 guardar, F9 cargar, ESC salir dialogo",Vector2(27,82),Color("#f6deb0"),8)
    _label("M: mapa   F11: pantalla completa",Vector2(27,97),Color("#d3bd99"),8)
  if show_map:
    draw_rect(Rect2(13,13,294,122),Color("#101a2eec"))
    draw_rect(Rect2(13,13,294,2),Color("#d9aa76"))
    _label("MAPA DE BRUMA - M PARA CERRAR",Vector2(28,28),Color("#fbe3b3"),10)
    for j in range(3):
      var sx:int=25+j*94
      draw_rect(Rect2(sx,43,82,54),Color("#2b4252"))
      draw_rect(Rect2(sx,43,82,2),Color("#d49c67"))
      var sid:String=["harbor","workshop","old_observatory"][j]
      _label(["PUERTO","TALLER","OBSERVATORIO"][j],Vector2(sx+7,64),Color("#f3d5a3"),8)
      _label("ESTAS AQUI" if scene_id==sid else "EXPLORAR",Vector2(sx+7,83),
        Color("#8ce1c9") if scene_id==sid else Color("#c1b4a5"),7)
    _label("Busca pistas en los tres lugares.",Vector2(41,116),Color("#f3d5a3"),8)
