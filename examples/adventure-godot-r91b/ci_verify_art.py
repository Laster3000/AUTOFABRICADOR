# coding: utf-8
"""R91 fresh-source owner: 22 exact PNG/ORA bytes from unmodified R90 base art.
Runs independent standard-library navigation/asset validator first, then two rebuilds.
No network, no process except local Python source and no overwritten source files.
"""
from __future__ import annotations
import hashlib,importlib.util,json,os,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
SCRIPT=ROOT/"art/r91_hd_art.py"
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for block in iter(lambda:f.read(1<<20),b""):h.update(block)
 return h.hexdigest()
def read(p):return json.loads(p.read_text(encoding="utf-8"))
def main():
 navpath=ROOT/"qa/adventure_navigation_r91.py"
 spec=importlib.util.spec_from_file_location("r91_standalone_independent_nav_oracle",navpath)
 if spec is None or spec.loader is None:raise RuntimeError("R91_NAV_OWNER_MISSING")
 oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)
 a=oracle.audit(ROOT)
 if a["status"]!="PASS_REUSABLE_WALKMESH_AND_HD_ART_CONTRACT":
  raise RuntimeError("R91_NAV_OWNER_FAILED")
 contract=read(ROOT/"R91-HD-ART-MANIFEST.json")
 if contract["status"]!="PASS_HD_11_ASSETS_11_EDITABLE_ORA":
  raise RuntimeError("R91_ART_MANIFEST_UNACCEPTED")
 assets={}
 for r in contract["assets"]:
  for name,field in ((r["png"],"pngSHA256"),(r["master"],"masterSHA256")):
   expected=r[field]
   if sha(ROOT/name)!=expected:raise RuntimeError("R91_HD_ART_FILE_SHA_CHANGED:"+name)
   assets[name]=expected
 if len(assets)!=22:raise RuntimeError("R91_ART_COUNT_EXPECTED_22")
 outputs=[]
 for attempt in (1,2):
  with tempfile.TemporaryDirectory(prefix=f"AF-R91-SOURCE-ART-{attempt}-") as temp:
   env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1","R91_ART_OUT":str(Path(temp)/"generated")}
   x=subprocess.run([sys.executable,"-B",str(SCRIPT)],
     cwd=ROOT,env=env,capture_output=True,text=True,timeout=120)
   if x.returncode:raise RuntimeError("R91_ART_BUILD_FAILED:"+x.stderr[-1600:])
   generated=Path(temp)/"generated"
   for name,digest in assets.items():
    item=generated/name
    if not item.is_file() or sha(item)!=digest:
     raise RuntimeError("R91_NONDETERMINISTIC_ART:"+name)
   if read(generated/"R91-HD-ART-MANIFEST.json")!=contract:
    raise RuntimeError("R91_ART_OUTPUT_MANIFEST_NOT_EQUAL")
   outputs.append({k:sha(generated/k) for k in assets})
 if outputs[0]!=outputs[1]:raise RuntimeError("R91_TWO_BUILDS_NOT_EQUAL")
 receipt={"schema":1,"status":"PASS_R91_22_HD_ART_TWO_BUILDS_3_NAV_ROOMS",
   "native":[640,360],"output":[1280,720],"walkboxes":a["rooms"],
   "hotspotsReachable":a["hotspotsReachable"],
   "originalLayeredAssetFiles":len(assets),"reproIndependentBuilds":len(outputs),
   "generatorSHA256":sha(SCRIPT),
   "humanVisualArtAccepted":False,"fullAutonomousAiGameGenerated":False}
 print(json.dumps(receipt,sort_keys=True,ensure_ascii=False))
 return receipt
if __name__=="__main__":main()
