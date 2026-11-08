# coding: utf-8
"""R90 clean offline art oracle: frozen owner SHA, full rebuild and independent VGA gates."""
import hashlib,importlib.util,json,os,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
 contract=json.loads((ROOT/"ART-R90-CONTRACT.json").read_text(encoding="utf-8"))
 files=contract["assets"]
 if len(files)!=22:raise RuntimeError("EXPECTED_11_PNG_AND_11_LAYERED_MASTERS")
 script=ROOT/"art"/"r90_illustrate.py"
 if sha(script)!=contract["sourceSha256"]:raise RuntimeError("GENERATOR_SOURCE_HASH_CHANGED")
 with tempfile.TemporaryDirectory(prefix="R90-CI-OWNER-ART-") as tmp:
  generated=Path(tmp)/"generated"
  env={**os.environ,"R90_ART_OUT":str(generated),"PYTHONDONTWRITEBYTECODE":"1"}
  process=subprocess.run([sys.executable,"-B",str(script)],env=env,
    capture_output=True,text=True,timeout=120)
  if process.returncode!=0:raise RuntimeError("R90_GENERATOR_FAILED:"+process.stderr[-800:])
  for rel,digest in files.items():
   if sha(ROOT/rel)!=digest or sha(generated/rel)!=digest:
    raise RuntimeError("ART_BYTE_REPRO_DRIFT:"+rel)
 # Retain the independent R88 gate, never let the generator validate itself.
 spec=importlib.util.spec_from_file_location("r90_original_independent_oracle",ROOT/"qa/adventure_visual_gate_r88.py")
 module=importlib.util.module_from_spec(spec)
 spec.loader.exec_module(module)
 results=[]
 for name in ("harbor","workshop","observatory"):
  audit=module.audit(ROOT/("scene-"+name+".json"))
  if not audit["technicalPass"] or audit["artisticQualityAccepted"]:
   raise RuntimeError("R90_VGA_SCENE_GATE:"+name+str(audit["errors"]))
  results.append(name)
 record={"status":"PASS_22_BYTE_IDENTICAL_ASSETS_THREE_SCENE_GATES",
  "files":len(files),"scenes":results,"humanArtApproved":False}
 print(json.dumps(record,sort_keys=True))
 return record
if __name__=="__main__":main()
