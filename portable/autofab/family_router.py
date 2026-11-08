# coding: utf-8
"""R75 one entrypoint for independently owned portable software-family requests.

Dispatches only to ORIGINAL accepted factory routes. Does not promote a model
response, reinterpret a simple WASI function as a full application, or start a
new runner. Blocked classes require first-party E2E oracles/toolchains.
"""
from __future__ import annotations
from pathlib import Path
import json,re,hashlib
from . import open_orders,desktop_workflow,portfolio_workflow
from .storage import sha_file

VERSION="AF.R75.FAMILY-ROUTER.1"
# Actual source/acceptance type, not the user's aspirational product name.
ROUTES={
 "library-js":("order","PURE_JS_TWO_MODULE_WASI",False),
 "offline-web-calculator":("order","OFFLINE_GENERIC_BROWSER_UI_AND_WASI",False),
 "api-route-logic":("order","PURE_API_ROUTING_LOGIC_NO_HTTP_SERVER",False),
 "game-2d-rules":("order","PURE_COLLISION_GRID_RULES_NO_2D_RENDERER",False),
 "game-3d-math":("order","PURE_3D_MATH_NO_WEBGL_GAME",False),
 "agent-decision-logic":("order","DETERMINISTIC_AGENT_POLICY_NOT_LLM_APP",False),
 "desktop-orders":("desktop","BOUNDED_WINDOWS_SQLITE_ORDERS",False),
 "desktop-portfolio":("portfolio","BOUNDED_WINDOWS_SQLITE_PORTFOLIO",False),
}
# Not supported even if language package/toolchain is available. Avoid pretending
# that an arbitrary game/Android/AI app passed an unrelated owner oracle.
BLOCKED={
 "web-fullstack":("FIRST_PARTY_DB_HTTP_AUTH_OWNER_AND_ISOLATED_SERVER_E2E_MISSING",
       "HTTP server, DB migrations, auth, concurrency and browser E2E"),
 "game-2d":("GAME_ENGINE_RENDERER_COLLISION_VISUAL_E2E_MISSING",
       "scene graph, renderer, input, collisions, persistence and visual tests"),
 "game-3d":("TRUE_3D_GAME_RENDERER_AND_GPU_E2E_MISSING",
       "WebGL mesh/camera/shader, physics, input, render QA and performance"),
 "android":("ANDROID_SDK_JAVA_GRADLE_DEVICE_OWNER_MISSING",
       "pinned Android SDK/JDK/Gradle, emulator or physical-device instrumentation"),
 "ai-integrated":("MODEL_APP_PROTOCOL_PRIVACY_BUDGET_OWNER_MISSING",
       "scoped model service, streaming, timeout, privacy and safety owner E2E"),
}
_ALLOWED={"schema","family","owner","goal","provider"}
_PROVIDER=("small","cuda7b","cuda9b","coder14b")
_NAME=re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{1,110}\Z")
def _family(name):
 if not isinstance(name,str) or name not in set(ROUTES)|set(BLOCKED):
  raise ValueError("FAMILY_UNKNOWN_FAIL_CLOSED")
 return name
def capabilities():
 return {"schema":1,"version":VERSION,
   "status":"BOUNDED_ROUTES_ONLY_NOT_UNIVERSAL",
   "routes":{k:{"originalRoute":r,"trueScope":scope,
     "universalProgramSupported":universal} for k,(r,scope,universal) in ROUTES.items()},
   "blocked":{k:{"status":"BLOCKED_NOT_ROUTABLE",
     "reason":why,"required":missing} for k,(why,missing) in BLOCKED.items()},
   "supportedDoesNotMeanNativePhoneOrGame":True,
   "modelMustNotWriteIndependentAcceptance":True,
   "hostGeneratedSourceExecution":False}
def _source(root,filename,family):
 root=Path(root).resolve()
 if type(filename) is not str or not _NAME.fullmatch(filename) or filename in (".",".."):
  raise ValueError("FAMILY_OWNER_BASENAME_ONLY")
 directory=root/"ENTRADAS"
 full=directory/filename
 suffix=".txt" if ROUTES[family][0]!="order" else ".json"
 if full.suffix.lower()!=suffix or not full.is_file() or full.is_symlink() or full.resolve().parent!=directory:
  raise ValueError("FAMILY_OWNER_MUST_BE_REGULAR_ENTRADAS_FILE")
 if full.stat().st_size>110000:raise ValueError("FAMILY_OWNER_SIZE_LIMIT")
 return full
def _load(root,path):
 root=Path(root).resolve();request=Path(path)
 base=root/"ENTRADAS"
 if (not request.is_file() or request.is_symlink() or request.resolve().parent!=base
       or request.suffix.lower()!=".json" or request.stat().st_size>13000):
  raise ValueError("FAMILY_REQUEST_MUST_BE_ENTRADAS_JSON")
 def strict(pairs):
  obj={}
  for k,v in pairs:
   if k in obj:raise ValueError("FAMILY_DUPLICATE_JSON_KEY:"+k)
   obj[k]=v
  return obj
 value=json.loads(request.read_text(encoding="utf-8"),object_pairs_hook=strict,
       parse_constant=lambda k: (_ for _ in ()).throw(ValueError("FAMILY_JSON_NAN_DENIED")))
 if type(value) is not dict or set(value)!=_ALLOWED or value["schema"]!=1:
  raise ValueError("FAMILY_REQUEST_SCHEMA_INVALID")
 family=_family(value["family"])
 if type(value["goal"]) is not str or not 24<=len(value["goal"])<=1800:
  raise ValueError("FAMILY_GOAL_BOUNDED_REQUIRED")
 if type(value["owner"]) is not str or not _NAME.fullmatch(value["owner"]):
  raise ValueError("FAMILY_OWNER_FILENAME_INVALID")
 if value["provider"] not in _PROVIDER:
  raise ValueError("FAMILY_PROVIDER_UNSUPPORTED")
 # Only the frozen owner file determines independently tested behavior.
 return value,request,sha_file(request)
def preview(root,path):
 v,request,hash_req=_load(root,path)
 family=v["family"]
 base={"schema":1,"version":VERSION,"family":family,
       "operationId":"AF.R75.FAMILY."+hash_req[:20],
       "requestSHA":hash_req,"goal":v["goal"],"modelGeneratedAcceptance":False,
       "universalAppApproved":False,"protectedInstallationAuthorized":False}
 if family in BLOCKED:
  why,needed=BLOCKED[family]
  return {**base,"status":"BLOCKED_NOT_ROUTABLE","reason":why,
          "nextRequirement":needed,"modelCalled":False,"ownerFrozen":False}
 route,scope,_=ROUTES[family]
 source=_source(root,v["owner"],family)
 original=(open_orders.preview(root,source) if route=="order" else
           desktop_workflow.preview(root,source) if route=="desktop" else
           portfolio_workflow.preview(root,source))
 expected={"order":"FROZEN_OWNER_INPUT_READY",
           "desktop":"FROZEN_FIRST_PARTY_DESKTOP_ORDERS_SCOPE",
           "portfolio":"PASS_FROZEN_INDEPENDENT_FIRST_PARTY_SCOPE"}
 observed=(original.get("status") or "")
 admissible=observed==expected[route]
 return {**base,"status":"ADMISSIBLE_SCOPED_OWNER_ROUTE" if admissible else "BLOCKED_OWNER_POLICY",
   "route":route,"trueScope":scope,"originalPreview":original,
   "ownerPath":str(source),"ownerSHA":sha_file(source),
   "modelCalled":False,"ownerFrozen":admissible}
def submit(root,path):
 # This entrypoint does not run a new worker. It delegates to the established
 # owner and original supervisor, retaining original journal/lease/readbacks.
 before=preview(root,path)
 if before["status"]!="ADMISSIBLE_SCOPED_OWNER_ROUTE":
  return before
 after=preview(root,path)
 if before["requestSHA"]!=after["requestSHA"] or before["ownerSHA"]!=after["ownerSHA"]:
  raise RuntimeError("FAMILY_REQUEST_OR_OWNER_CAS_CHANGED_NO_SUBMIT")
 v,_,_=_load(root,path)
 src=Path(before["ownerPath"])
 if before["route"]=="order":
  result=open_orders.submit(root,src,provider=v["provider"],acceptance_mode="wasi-browser")
 elif before["route"]=="desktop":
  result=desktop_workflow.submit(root,src)
 else:
  result=portfolio_workflow.submit(root,src)
 return {"schema":1,"version":VERSION,"status":"SUBMITTED_TO_ORIGINAL_OWNER",
   "family":before["family"],"trueScope":before["trueScope"],
   "operationId":before["operationId"],"original":result,
   "originalRequestSHA":before["requestSHA"],"originalOwnerSHA":before["ownerSHA"],
   "notAUniversalApp":True,"notHostInstalled":True,
   "noParallelModelWorkersStarted":True}
def status(root,family,original_id):
 family=_family(family)
 if family in BLOCKED:return {"family":family,"status":"BLOCKED_NOT_ROUTABLE"}
 route=ROUTES[family][0]
 if route=="order":
  if not re.fullmatch(r"OJ-[a-f0-9]{16}",original_id):raise ValueError("FAMILY_ORDER_ID_INVALID")
  result=open_orders.status(root,original_id)
 elif route=="desktop":
  if not re.fullmatch(r"DW-[a-f0-9]{16}",original_id):raise ValueError("FAMILY_DESKTOP_ID_INVALID")
  result=desktop_workflow.status(root,original_id)
 else:
  if not re.fullmatch(r"DP-[a-f0-9]{16}",original_id):raise ValueError("FAMILY_PORTFOLIO_ID_INVALID")
  result=portfolio_workflow.status(root,original_id)
 return {"family":family,"trueScope":ROUTES[family][1],
   "status":"ORIGINAL_OWNER_READBACK","original":result,
   "universalAppApproved":False}
