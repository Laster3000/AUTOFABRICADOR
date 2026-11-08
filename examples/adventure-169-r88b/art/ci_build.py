# coding: utf-8
"""Offline, reproducible source build from a fresh clone. No third-party runtime."""
from __future__ import annotations
import hashlib
import importlib.util
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parent.parent
REPO=ROOT.parent.parent
GATE=REPO/"development"/"autofab"/"adventure_visual_gate_r88.py"
def digest(b:bytes)->str:
    return hashlib.sha256(b).hexdigest()

def check_art():
    if not GATE.is_file():
        raise RuntimeError("R88_GATE_SOURCE_MISSING")
    spec=importlib.util.spec_from_file_location("gate_r88",GATE)
    if spec is None or spec.loader is None:
        raise RuntimeError("R88_GATE_IMPORT_FAILED")
    gate=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate)
    for scene in ("harbor","workshop"):
        result=gate.audit(ROOT/("scene-"+scene+".json"))
        if not result["technicalPass"]:
            raise RuntimeError("R88_VISUAL_CONTRACT_FAILED:"+scene+":"+str(result["errors"]))
        if result["artisticQualityAccepted"]:
            raise RuntimeError("R88_MUST_NOT_AUTOAPPROVE_ART")

def main():
    check_art()
    wanted=[
        "index.html","styles.css","game.js","data.js","scene-harbor.json",
        "scene-workshop.json","LEEME-PRIMERO.md","LICENCIAS-Y-PROCEDENCIA.md",
        "INICIAR_JUEGO.cmd","art/generate_assets.py"
    ]
    wanted.extend("assets/"+p.name for p in sorted((ROOT/"assets").glob("*.png")))
    wanted.extend("source/"+p.name for p in sorted((ROOT/"source").glob("*.ora")))
    if len(wanted)!=24:
        raise RuntimeError("R88_EXPECTED_7_RESOURCES_AND_24_FILES")
    sources={k:(ROOT/k).read_bytes() for k in wanted}
    manifest={
        "schema":1,"product":"LA LUZ DE BRUMA","release":"R88B-CI-SOURCE-BUILD",
        "ratio":"16:9","artResolution":[320,180],"presentation":[640,360],
        "status":"SOURCE_REBUILT_TECHNICAL_ONLY_ART_REVIEW_REQUIRED",
        "artisticAccepted":False,"browserE2EExecutedByThisBuild":False,
        "localAIEndToEndVerified":False,"externalExecutablesIncluded":False,
        "files":{k:{"bytes":len(v),"sha256":digest(v)} for k,v in sorted(sources.items())}
    }
    sources["MANIFEST-SHA256.json"]=(json.dumps(manifest,ensure_ascii=False,indent=2,sort_keys=True)+"\n").encode()
    dist=ROOT/"DIST"
    dist.mkdir(exist_ok=True)
    output=dist/"LA-LUZ-DE-BRUMA-16x9-R88B-SOURCE-REBUILD.zip"
    with zipfile.ZipFile(output,"x",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,raw in sorted(sources.items()):
            info=zipfile.ZipInfo(name,date_time=(2026,11,8,12,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,raw)
    with zipfile.ZipFile(output) as z:
        if set(z.namelist())!=set(sources):
            raise RuntimeError("R88_SOURCE_ZIP_MISMATCH")
        for name,raw in sources.items():
            if digest(z.read(name))!=digest(raw):
                raise RuntimeError("R88_SOURCE_ZIP_SHA_BAD:"+name)
    print(json.dumps({"status":"PASS_SOURCE_BUILD_NOT_ART_ACCEPTED",
                      "archive":str(output),"sha256":digest(output.read_bytes()),
                      "files":len(sources)},indent=2))
if __name__=="__main__":
    main()
