extends RefCounted
## AF.R91 navigation engine: reusable walkbox projection and obstacle-safe A*.
## Logic coordinates are 320x180, irrespective of pixels in the 640x360 render.
## Object interactions are performed only after an actual reachable walking path.
const CELL := 2
const WIDTH := 320
const HEIGHT := 130
const GRID_W := 160
const GRID_H := 65

static func in_polygon(poly: Array, point: Vector2) -> bool:
  var inside := false
  var n := poly.size()
  if n < 3:
    return false
  for i in range(n):
    var p: Array = poly[i]
    var q: Array = poly[(i+1)%n]
    var a := Vector2(float(p[0]),float(p[1]))
    var b := Vector2(float(q[0]),float(q[1]))
    if (a.y > point.y) != (b.y > point.y):
      var intersect := a.x + (point.y-a.y) * (b.x-a.x) / (b.y-a.y)
      if point.x < intersect:
        inside = not inside
  return inside

static func allowed(section: Dictionary, p: Vector2) -> bool:
  if not p.is_finite() or p.x < 14.0 or p.x > 306.0 or p.y < 99.0 or p.y > 126.0:
    return false
  var good := false
  for poly in section["walkable"]:
    if in_polygon(poly,p):
      good = true
      break
  if not good:
    return false
  for obstacle in section["obstacles"]:
    if in_polygon(obstacle,p):
      return false
  return true

static func nearest_point(section: Dictionary, where: Vector2) -> Vector2:
  if allowed(section,where):
    return where
  var best := Vector2(-1,-1)
  var distance := INF
  for cy in range(50,64):
    for cx in range(7,154):
      var p := Vector2(float(cx*CELL),float(cy*CELL))
      if allowed(section,p):
        var d := p.distance_squared_to(where)
        if d < distance:
          distance = d
          best = p
  return best

static func line_is_safe(section: Dictionary, a: Vector2, b: Vector2) -> bool:
  var steps: int = maxi(1,ceili(a.distance_to(b)))
  for k in range(steps+1):
    if not allowed(section,a.lerp(b,float(k)/float(steps))):
      return false
  return true

static func make_grid(section: Dictionary) -> AStarGrid2D:
  var grid := AStarGrid2D.new()
  grid.region = Rect2i(0,0,GRID_W,GRID_H)
  grid.cell_size = Vector2(CELL,CELL)
  grid.diagonal_mode = AStarGrid2D.DIAGONAL_MODE_NEVER
  grid.update()
  for y in range(GRID_H):
    for x in range(GRID_W):
      var point := Vector2(float(x*CELL),float(y*CELL))
      if not allowed(section,point):
        grid.set_point_solid(Vector2i(x,y),true)
  return grid

static func find_path(section: Dictionary, from: Vector2, wanted: Vector2) -> Array[Vector2]:
  var points: Array[Vector2] = []
  var start := nearest_point(section,from)
  var goal := nearest_point(section,wanted)
  if start.x < 0.0 or goal.x < 0.0:
    return points
  if line_is_safe(section,start,goal):
    if start.distance_to(goal)>0.5:
      points.append(goal)
    return points
  var grid := make_grid(section)
  var s := Vector2i(clampi(roundi(start.x/CELL),0,GRID_W-1),clampi(roundi(start.y/CELL),0,GRID_H-1))
  var g := Vector2i(clampi(roundi(goal.x/CELL),0,GRID_W-1),clampi(roundi(goal.y/CELL),0,GRID_H-1))
  if grid.is_point_solid(s) or grid.is_point_solid(g):
    var adjusted_a := nearest_point(section,Vector2(s*CELL))
    var adjusted_b := nearest_point(section,Vector2(g*CELL))
    if adjusted_a.x < 0 or adjusted_b.x < 0:
      return points
    s = Vector2i(roundi(adjusted_a.x/CELL),roundi(adjusted_a.y/CELL))
    g = Vector2i(roundi(adjusted_b.x/CELL),roundi(adjusted_b.y/CELL))
  var path := grid.get_point_path(s,g)
  if path.is_empty():
    return points
  var chain: Array[Vector2] = [start]
  for p in path:
    chain.append(p)
  chain.append(goal)
  var cursor := 0
  # Funnel-like line-of-sight simplification, but never cut through forbidden cells.
  while cursor < chain.size()-1:
    var far := chain.size()-1
    while far > cursor+1 and not line_is_safe(section,chain[cursor],chain[far]):
      far -= 1
    if far <= cursor:
      break
    var next: Vector2=chain[far]
    if points.is_empty() or points.back().distance_to(next)>0.1:
      points.append(next)
    cursor=far
  return points

static func validate_contract(contract: Dictionary) -> bool:
  if contract.get("schema")!=1 or contract.get("pixelScale")!=2:
    return false
  var rooms: Dictionary=contract.get("scenes",{})
  if rooms.size()!=3:
    return false
  for room in rooms.values():
    if typeof(room)!=TYPE_DICTIONARY or not room.has("walkable") or not room.has("obstacles"):
      return false
    if not allowed(room,Vector2(room["start"][0],room["start"][1])):
      return false
  return true
