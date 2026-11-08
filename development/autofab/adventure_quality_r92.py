# coding: utf-8
"""AF R92 reusable scene/art/state *acceptance gate*, stdlib only.
Source of truth: independent R91 polygon math plus new compact-HUD and ORA contracts.
Read-only validation. Runtime state transitions are separately tested in Godot.
"""
from __future__ import annotations
import argparse,hashlib,json,sys
from pathlib import Path
from typing import Any
sys.path.insert(0,str(Path(__file__).resolve().parent))
try:
 from . import adventure_navigation_r91 as oldnav
except ImportError:
 import adventure_navigation_r91 as oldnav
VERSION="AF.R92.QUALITY-ACCEPTANCE.1"
class QualityError(ValueError):pass
def ensure(test:bool,message:str):
 if not test:raise QualityError(message)
def digest(path:Path)->str:
 h=hashlib.sha256()
 with path.open("rb") as f:
  for block in iter(lambda:f.read(1048576),b""):h.update(block)
 return h.hexdigest()
def audit(root:Path)->dict[str,Any]:
 root=root.resolve()
 ensure(root.is_dir(),"PROJECT_MISSING")
 nav=oldnav.load(root/"navigation_r91.json")
 world=oldnav.load(root/"game_data.json")
 ensure(nav["schema"]==1 and nav["pixelScale"]==2,"INVALID_NAV_PROFILE")
 ensure(set(nav["scenes"])==set(world["scenes"]),"ROOMS_NOT_SYNCHRONIZED")
 ensure(len(nav["scenes"])==3,"THREE_ROOMS_REQUIRED_FOR_THIS_PROVEN_ORACLE")
 sections={}
 total_hotspots=0
 for sid,room in nav["scenes"].items():
  section=oldnav.nav_section(room)
  sections[sid]=section
  reachable=oldnav.bfs_reachable(section)
  ensure(len(reachable)>80,"SCENE_NAVIGATION_DISCONNECTED:"+sid)
  for item in world["scenes"][sid]["hotspots"]:
   p=oldnav.point(item["walkTo"])
   ensure(oldnav.permitted(section,p),"HOTSPOT_INSIDE_WALL:"+item["id"])
   cell=(round(p[0]/2)*2,round(p[1]/2)*2)
   ensure(cell in reachable,"HOTSPOT_UNREACHABLE:"+item["id"])
   total_hotspots+=1
 manifest=oldnav.load(root/"R92-ART-MANIFEST.json")
 ensure(manifest["status"]=="PASS_ELEVEN_ORIGINAL_REEDITABLE_ART_MASTERS","ART_OWNER_STATUS")
 assets=manifest["assets"]
 ensure(len(assets)==11 and len({a["id"] for a in assets})==11,"ELEVEN_UNIQUE_ART_ASSETS")
 seen={}
 n_layers=0
 for item in assets:
  name=item["id"]
  for field,key in (("png","pngSHA256"),("master","masterSHA256")):
   rel=item[field]
   source=oldnav.safe_path(root,rel)
   ensure(digest(source)==item[key],"ASSET_SHA_MISMATCH:"+rel)
   seen[rel]=item[key]
  if name in ("young_sailor","elder_whitebeard"):
   expected=(672,96)
  elif name=="interface":
   expected=(640,70)
  elif name in ("compass","lens"):
   expected=(32,32)
  else:
   expected=(640,290)
  ensure(oldnav.image_dimensions(root/item["png"])==expected,"PIXEL_SIZE_WRONG:"+name)
  ow,oh,layers=oldnav.source_layers(root/item["master"])
  ensure((ow,oh)==expected and layers>=6,"ORA_EDITABLE_LAYERS_INVALID:"+name)
  n_layers+=layers
 # Verify each scene still references exactly the SHA checked assets.
 refs=0
 assets_by_id={r["id"]:r for r in assets}
 for sceneid in nav["scenes"]:
  base="observatory" if sceneid=="old_observatory" else sceneid
  sc=oldnav.load(root/("scene-"+base+".json"))
  ensure(sc["profile"]["canvas"]==[640,360] and sc["profile"]["presentation"]==[1280,720],
    "NOT_PANORAMIC_HD")
  ensure(sc["profile"]["sceneHeight"]==290 and sc.get("interfaceHeight")==70,
    "SCENE_NOT_EXPANDED_OR_HUD_NOT_COMPACT")
  for item in sc["assets"]:
   original=assets_by_id[item["id"]]
   ensure(item["pngSHA256"]==original["pngSHA256"] and
          item["masterSHA256"]==original["masterSHA256"],
          "STALE_SCENE_HASH:"+item["id"])
   refs+=1
 # Frozen GDScript source contract, not a substitute for an executed E2E check.
 script=(root/"game.gd").read_text(encoding="utf-8")
 for snippet in ("func _finish_action() -> void:","func _clear_pending_action(",
                 "func _hotspot_visible(","var show_map: bool = false",
                 'const SCENE_HEIGHT = 145','const UI_HEIGHT = 35',
                 'const SAVE_PATH = "user://bruma_r92.json"'):
  ensure(snippet in script,"STATE_MACHINE_CONTRACT_MISSING:"+snippet)
 ensure(len(seen)==22 and n_layers>=66,"ART_LAYERS_OR_FILES_MISSING")
 # Immutable base needed for reproducible editing, no deployment of paid fonts.
 for name in assets_by_id:
  base=root/"art/base_r91/source"/(name+".ora")
  ensure(base.is_file() and not base.is_symlink(),"R91_LAYERED_BASE_MISSING:"+name)
 return {"schema":1,"operationId":VERSION,
  "status":"PASS_REUSABLE_R92_WALKMESH_UI_ART_SHA",
  "rooms":len(sections),"reachableHotspots":total_hotspots,
  "uniqueVerifiedAssets":len(seen),"editableSemanticLayers":n_layers,
  "native":[640,360],"window":[1280,720],"sceneHeight":145,
  "uiHeight":35,"humanArtApproved":False,"completeGeneralFactoryAccepted":False}
def main():
 parser=argparse.ArgumentParser()
 parser.add_argument("project",type=Path)
 args=parser.parse_args()
 print(json.dumps(audit(args.project),ensure_ascii=False,sort_keys=True,indent=2))
if __name__=="__main__":main()
