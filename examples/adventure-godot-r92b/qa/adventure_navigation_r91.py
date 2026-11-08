# coding: utf-8
"""AF R91 reusable, stdlib-only point-click navigation/art contract.

This is NOT a second factory. It provides an inspectable authoring and acceptance
gate that any AI agent may call before handing a scene to Godot.
No network, file writes, sandbox escapes or process launches on audit.
The native Godot runtime is adventure_nav_r91.gd.
"""
from __future__ import annotations
import argparse, collections, hashlib, json, math, struct, zipfile
from pathlib import Path
from xml.etree import ElementTree
from typing import Any

VERSION="AF.R91.NAV-WALKBOX-ART-640.1"
GRID=(320,180)
NATIVE=(640,360)
PRESENTATION=(1280,720)
AVATAR_HALF_WIDTH=12
STEP=2
PNG_HEADER=b"\x89PNG\r\n\x1a\n"
class NavContractError(ValueError):pass
def check(ok:bool,why:str):
    if not ok:raise NavContractError(why)
def load(path:Path)->Any:
    def unique(pairs):
        out={}
        for k,v in pairs:
            if k in out:raise NavContractError("DUPLICATE_JSON_KEY:"+k)
            out[k]=v
        return out
    def no_infinity(v):raise NavContractError("NONFINITE_JSON:"+v)
    return json.loads(path.read_text(encoding="utf-8-sig"),object_pairs_hook=unique,parse_constant=no_infinity)
def sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda:stream.read(1<<20),b""):h.update(block)
    return h.hexdigest()
def safe_path(root:Path,rel:str)->Path:
    check(type(rel)==str and 1<len(rel)<180 and "\\" not in rel and ":" not in rel,
        "UNSAFE_ASSET_PATH")
    p=Path(rel)
    check(not p.is_absolute() and ".." not in p.parts and len(p.parts)>=2,
        "PATH_ESCAPE")
    file=root.joinpath(*p.parts)
    check(file.is_file() and not file.is_symlink(),"FILE_MISSING_OR_SYMLINK:"+rel)
    check(file.resolve().is_relative_to(root.resolve()),"FILE_OUTSIDE_ROOT")
    check(file.stat().st_size<30_000_000,"FILE_OVER_MAX_SIZE")
    return file
def point(value)->tuple[float,float]:
    check(type(value) is list and len(value)==2 and all(type(z) in (int,float) and math.isfinite(z) for z in value),
        "POINT_INVALID")
    return float(value[0]),float(value[1])
def polygon(data)->list[tuple[float,float]]:
    check(type(data) is list and 3<=len(data)<=32,"POLYGON_VERTICES_INVALID")
    p=[point(a) for a in data]
    check(all(0<=x<=320 and 0<=y<=130 for x,y in p),"POLYGON_OUTSIDE_ROOM")
    signed=sum(p[i][0]*p[(i+1)%len(p)][1]-p[(i+1)%len(p)][0]*p[i][1] for i in range(len(p)))
    check(abs(signed)>5,"POLYGON_DEGENERATE")
    return p
def inside(poly:list[tuple[float,float]],where:tuple[float,float])->bool:
    x,y=where;yes=False
    for i in range(len(poly)):
        a,b=poly[i],poly[(i+1)%len(poly)]
        if (a[1]>y)!=(b[1]>y) and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:
            yes=not yes
    return yes
def permitted(section:dict,where:tuple[float,float])->bool:
    x,y=where
    return (14<=x<=306 and 99<=y<=126 and
        any(inside(poly,where) for poly in section["walkable"]) and
        not any(inside(poly,where) for poly in section["obstacles"]))
def nav_section(raw:dict)->dict:
    check(type(raw) is dict and set(["walkable","obstacles","start"]).issubset(raw),"NAV_ROOM_SCHEMA")
    walkable=[polygon(v) for v in raw["walkable"]]
    obstacles=[polygon(v) for v in raw["obstacles"]]
    section={"walkable":walkable,"obstacles":obstacles,"start":point(raw["start"])}
    check(1<=len(walkable)<=12 and len(obstacles)<=35,"NAV_POLYGON_COUNT")
    check(permitted(section,section["start"]),"SPAWN_NOT_WALKABLE")
    return section
def nearest(section:dict,wanted:tuple[float,float])->tuple[float,float]:
    if permitted(section,wanted):return wanted
    allpoints=((float(x),float(y)) for y in range(100,128,STEP) for x in range(14,308,STEP))
    valid=(p for p in allpoints if permitted(section,p))
    return min(valid,key=lambda p:(p[0]-wanted[0])**2+(p[1]-wanted[1])**2)
def bfs_reachable(section:dict)->set[tuple[int,int]]:
    allowed={(x,y) for y in range(100,128,STEP) for x in range(14,308,STEP)
            if permitted(section,(float(x),float(y)))}
    origin=nearest(section,section["start"])
    start=(round(origin[0]/STEP)*STEP,round(origin[1]/STEP)*STEP)
    check(start in allowed,"NO_VALID_GRID_SPAWN")
    seen={start}
    pending=collections.deque([start])
    while pending:
        x,y=pending.popleft()
        for nxt in ((x+2,y),(x-2,y),(x,y+2),(x,y-2)):
            if nxt in allowed and nxt not in seen:
                seen.add(nxt);pending.append(nxt)
    return seen
def image_dimensions(file:Path)->tuple[int,int]:
    with file.open("rb") as f:
        header=f.read(24)
    check(header[:8]==PNG_HEADER and header[12:16]==b"IHDR","INVALID_PNG")
    return struct.unpack(">II",header[16:24])
def source_layers(file:Path)->tuple[int,int,int]:
    with zipfile.ZipFile(file) as z:
        filenames=z.namelist()
        check("stack.xml" in filenames and "mimetype" in filenames,"ORA_STACK_MISSING")
        check(z.read("mimetype")==b"image/openraster","ORA_MIMETYPE_INVALID")
        root=ElementTree.fromstring(z.read("stack.xml"))
        layers=list(root.iter("layer"))
        check(len(layers)>=6,"ORA_INSUFFICIENT_SEMANTIC_LAYERS")
        for lay in layers:
            check(lay.attrib["src"] in filenames,"ORA_LAYER_SOURCE_MISSING")
        return int(root.attrib["w"]),int(root.attrib["h"]),len(layers)
def build_contract(scenes:list[Path],overrides:dict|None=None)->dict:
    """Produce a new navigation contract for any authored adventure scene set.
    No writes. Use the built-in fallback walkable polygons if there is no override.
    """
    check(bool(scenes),"NO_SCENES_PROVIDED")
    cfg={}
    overrides=overrides or {}
    for file in scenes:
        content=load(file); scene=content["scene"]; name=scene["id"]
        check(name not in cfg,"DUPLICATED_SCENE_ID")
        room_override=overrides.get(name,{})
        cfg[name]={
           "walkable":room_override.get("walkable",[scene["walkable"]]),
           "obstacles":room_override.get("obstacles",[]),
           "start":room_override.get("start",scene["playerStart"])}
        nav_section(cfg[name])
    return {"schema":1,"pixelScale":2,"logicalGrid":list(GRID),"nativeGrid":list(NATIVE),
        "presentationGrid":list(PRESENTATION),"scenes":cfg}
def audit(root:Path)->dict:
    check(root.is_dir(),"ROOT_MISSING")
    nav=load(root/"navigation_r91.json")
    check(nav["schema"]==1 and nav["pixelScale"]==2,"NAV_FORMAT")
    check(nav.get("logicalGrid") == list(GRID),"LOGICAL_RESOLUTION_WRONG")
    check(nav.get("nativeGrid",nav.get("presentationGrid")) == list(NATIVE),
       "NATIVE_RESOLUTION_WRONG")
    rooms=nav["scenes"]
    check(type(rooms) is dict and len(rooms)>0,"NO_NAVIGATION_ROOMS")
    world=load(root/"game_data.json")
    check(set(rooms)==set(world["scenes"]),"ROOM_NAV_SET_DIFFERENT_FROM_GAME")
    sections={name:nav_section(record) for name,record in rooms.items()}
    art_seen={}; hotspot_count=0;check_count=0
    for name,record in world["scenes"].items():
        contract_path=root/("scene-"+("observatory" if name=="old_observatory" else name)+".json")
        manifest=load(contract_path)
        profile=manifest["profile"]
        check(profile["aspect"]=="16:9" and profile["canvas"]==list(NATIVE)
              and profile["presentation"]==list(PRESENTATION),"SCENE_NOT_NATIVE_HD:"+name)
        section=sections[name]
        cells=bfs_reachable(section)
        check(len(cells)>80,"WALKABLE_REGION_TOO_SMALL:"+name)
        for hot in record["hotspots"]:
            hp=point(hot["walkTo"])
            check(permitted(section,hp),"HOTSPOT_STAND_IN_OBSTACLE:"+hot["id"])
            gx=round(hp[0]/STEP)*STEP;gy=round(hp[1]/STEP)*STEP
            check((gx,gy) in cells,"HOTSPOT_UNREACHABLE:"+hot["id"])
            hotspot_count+=1
        for a in manifest["assets"]:
            asset_id=a["id"]
            for field,hashfield in (("png","pngSHA256"),("master","masterSHA256")):
                file=safe_path(root,a[field])
                check(sha(file)==a[hashfield],"FILE_SHA_MISMATCH:"+a[field])
                if a[field] in art_seen:
                    check(art_seen[a[field]]==a[hashfield],"MISMATCHED_SHARED_ASSET")
                else:art_seen[a[field]]=a[hashfield]
            dimensions=image_dimensions(root/a["png"])
            if a["kind"] in ("background","foreground"):wanted=(640,260)
            elif a["kind"]=="character":wanted=(672,96)
            elif a["kind"]=="ui":wanted=(640,100)
            else:wanted=(32,32)
            check(dimensions==wanted,"ASSET_DIMENSIONS_MISMATCH:"+asset_id)
            w,h,layercount=source_layers(root/a["master"])
            check((w,h)==wanted,"ORA_LAYER_DIMENSIONS_MISMATCH:"+asset_id)
            check_count+=1
        for spot in ((-800,-800),(900,900),(160,23),(319,179)):
            nearest_point=nearest(section,spot)
            check(permitted(section,nearest_point),"OUTSIDE_CLICK_NOT_PROJECTABLE")
    check(len(art_seen)==22,"EXPECTED_11_PNG_PLUS_11_ORA")
    return {"schema":1,"operationId":VERSION,
     "status":"PASS_REUSABLE_WALKMESH_AND_HD_ART_CONTRACT",
     "native":list(NATIVE),"presentation":list(PRESENTATION),
     "rooms":len(rooms),"hotspotsReachable":hotspot_count,
     "layeredAssetReferencesValidated":check_count,
     "uniqueFilesSHA256":len(art_seen),"humanArtApproved":False,
     "wholeGameGeneratedByAi":False}
def main():
    p=argparse.ArgumentParser(description="AF R91 reusable navigation/HD art gate")
    p.add_argument("command",choices=("audit","compile"))
    p.add_argument("project_root",type=Path)
    p.add_argument("--overrides",type=Path)
    args=p.parse_args()
    if args.command=="audit":
        result=audit(args.project_root)
    else:
        names=sorted(args.project_root.glob("scene-*.json"))
        extra=load(args.overrides) if args.overrides else {}
        result=build_contract(names,extra)
    print(json.dumps(result,sort_keys=True,indent=2,ensure_ascii=False))
if __name__=="__main__":main()
