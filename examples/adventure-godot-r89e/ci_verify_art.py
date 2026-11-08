# coding: utf-8
"""R89E one-shot independent reproducer from frozen first-party generator sources.
Works in a clean repo clone and prevents both stale and manipulated art/master files.
Never deletes or overwrites existing assets, secrets, or accepted receipts.
"""
import hashlib,importlib.util,json,os,shutil,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def sha(data):return hashlib.sha256(data).hexdigest()
def put(p,data):
 p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():
  if sha(p.read_bytes())!=sha(data):raise RuntimeError("R89E_ART_SOURCE_CAS_CONFLICT:"+str(p))
  return
 with p.open("xb") as f:f.write(data);f.flush();os.fsync(f.fileno())
 if sha(p.read_bytes())!=sha(data):raise RuntimeError("R89E_ART_READBACK_SHA_FAILED")
def main():
 if (ROOT/"qa/CI-R89E-ART-CHECK.json").exists():
  raise RuntimeError("R89E_CI_ALREADY_SUCCEEDED_NO_REPLAY")
 expected={}
 for name in ("scene-harbor.json","scene-workshop.json","scene-observatory.json"):
  doc=json.loads((ROOT/name).read_text(encoding="utf-8"))
  profile=doc["profile"]
  if profile["aspect"]!="16:9" or profile["canvas"]!=[320,180]:
   raise RuntimeError("R89E_SCENE_NOT_16_9")
  for item in doc["assets"]:
   for filekey,hashkey in (("png","pngSHA256"),("master","masterSHA256")):
    path=item[filekey];digest=item[hashkey]
    if path in expected and expected[path]!=digest:raise RuntimeError("PINNED_HASH_INCONSISTENT")
    expected[path]=digest
 if len(expected)!=22:raise RuntimeError("R89E_ASSET_MISSING_OR_DUPLICATE")
 env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1","DOTNET_ADD_GLOBAL_TOOLS_TO_PATH":"false"}
 with tempfile.TemporaryDirectory(prefix="R89E-ART-BUILD-") as tmp:
  scratch=Path(tmp)
  for name in ("generate_assets.py","generate_new_art.py"):
   target=scratch/"art"/name
   put(target,(ROOT/"art"/name).read_bytes())
   run=subprocess.run([sys.executable,"-B",str(target)],cwd=scratch,
       env=env,capture_output=True,text=True,timeout=95)
   if run.returncode:
    raise RuntimeError("R89E_GENERATOR_FAILED:"+name+":"+run.stderr[-1000:])
  for name,hash_expected in expected.items():
   made=scratch/name
   if not made.is_file() or sha(made.read_bytes())!=hash_expected:
    raise RuntimeError("R89E_NONREPRODUCIBLE_SOURCE:"+name)
   put(ROOT/name,made.read_bytes())
 # Reuse original independent technical oracles, not anything produced by the generator.
 candidates=[
  ROOT.parents[1]/"development/autofab/adventure_visual_gate_r88.py",
  Path(r"C:\AUTOFABRICADOR\autofab\adventure_visual_gate_r88.py")
 ]
 target=next((p for p in candidates if p.is_file()),None)
 if target is None:raise RuntimeError("R89E_ORIGINAL_INDEPENDENT_VISUAL_GATE_MISSING")
 spec=importlib.util.spec_from_file_location("af_r88_owner_gate",target)
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 for scene in ("harbor","workshop","observatory"):
  r=module.audit(ROOT/("scene-"+scene+".json"))
  if not r["technicalPass"] or r["artisticQualityAccepted"]:
   raise RuntimeError("R89E_VISUAL_GATE_FAILED:"+scene+":"+str(r["errors"]))
 receipt={"schema":1,"status":"PASS_SOURCE_REBUILD_22_PINNED_ASSETS_AND_3_SCENES",
          "assetCount":22,"originalVisualGate":str(target),
          "nativeAspect":"16:9","humanVisualApproved":False,
          "modelFullyAutonomousGameBuilt":False,
          "assets":expected}
 out=ROOT/"qa/CI-R89E-ART-CHECK.json"
 put(out,(json.dumps(receipt,ensure_ascii=False,indent=2)+"\n").encode())
 print(json.dumps({"status":receipt["status"],"sha":sha(out.read_bytes())},indent=2))
if __name__=="__main__":main()
