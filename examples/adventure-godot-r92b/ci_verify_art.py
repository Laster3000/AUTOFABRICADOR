# coding: utf-8
"""R92 portable art + walkbox owner, SHA-pinned two fresh rebuilds.
Requires Pillow 12 only when *rebuilding* art; game runs without Python.
"""
from __future__ import annotations
import json,hashlib,os,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
GEN=ROOT/"art/r92_polish.py"
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as stream:
  for part in iter(lambda:stream.read(1<<20),b""):h.update(part)
 return h.hexdigest()
def main():
 sys.path.insert(0,str(ROOT/"qa"))
 import adventure_quality_r92 as gate
 summary=gate.audit(ROOT)
 if summary["status"]!="PASS_REUSABLE_R92_WALKMESH_UI_ART_SHA":
  raise RuntimeError("R92_INDEPENDENT_AUDIT_MISSING")
 document=json.loads((ROOT/"R92-ART-MANIFEST.json").read_text())
 expected={}
 for item in document["assets"]:
  expected[item["png"]]=item["pngSHA256"]
  expected[item["master"]]=item["masterSHA256"]
 if len(expected)!=22:raise RuntimeError("R92_ART_FILE_COUNT_EXPECTED_22")
 manifests=[]
 for number in (1,2):
  with tempfile.TemporaryDirectory(prefix=f"R92-ART-OWNER-{number}-") as root:
   output=Path(root)/"art"
   env={**os.environ,"AF_R92_ART_OUT":str(output),"PYTHONDONTWRITEBYTECODE":"1"}
   proc=subprocess.run([sys.executable,"-B",str(GEN)],env=env,
                       cwd=ROOT,capture_output=True,text=True,timeout=120)
   if proc.returncode:raise RuntimeError("R92_GENERATOR_RUN_FAILED:"+proc.stderr[-1300:])
   seen={}
   for file,digest in expected.items():
    built=output/file
    if not built.exists() or sha(built)!=digest or sha(ROOT/file)!=digest:
     raise RuntimeError("R92_ART_NOT_REPRODUCIBLE:"+file)
    seen[file]=digest
   current=json.loads((output/"R92-ART-MANIFEST.json").read_text())
   if current!=document:raise RuntimeError("R92_GENERATOR_META_NONDETERMINISTIC")
   manifests.append(seen)
 if manifests[0]!=manifests[1]:raise RuntimeError("R92_ART_REPRO_RUNS_MISMATCH")
 record={"schema":1,"status":"PASS_R92_TWO_ART_REBUILDS_AND_WALKMESH",
 "artFilesVerified":22,"independentBuilds":2,"rooms":summary["rooms"],
 "reachableHotspots":summary["reachableHotspots"],
 "totalEditableLayers":summary["editableSemanticLayers"],
 "humanVisualArtApproved":False,"arbitraryAppGeneratedByAi":False}
 print(json.dumps(record,ensure_ascii=False,sort_keys=True))
 return record
if __name__=="__main__":main()
