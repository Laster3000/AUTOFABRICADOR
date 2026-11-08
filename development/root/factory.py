# coding: utf-8
"""AUTOFABRICADOR: isolated Python project builder (candidate). Standard library only."""
import argparse
import datetime
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import urllib.request
import uuid

ROOT = pathlib.Path(__file__).resolve().parent
JOBS = ROOT / "jobs"
CONFIG = ROOT / "config.json"
def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()
def digest(raw):
    return hashlib.sha256(raw).hexdigest()
def serialize(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)+"\n").encode("utf-8")
def atomic(path, data, *, new=False):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if new and path.exists():
        raise RuntimeError("EXISTS_NO_OVERWRITE: "+str(path))
    temp = path.with_name(path.name+".tmp-"+uuid.uuid4().hex)
    try:
        with temp.open("xb") as f:
            f.write(data); f.flush(); os.fsync(f.fileno())
        if new and path.exists():
            raise RuntimeError("RACE_EXISTS")
        os.replace(temp, path)
        if path.read_bytes()!=data:
            raise RuntimeError("READBACK_MISMATCH")
    finally:
        if temp.exists(): temp.unlink()
def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))
def receipt(folder, action, detail):
    event={"time":now(),"action":action,"detail":detail}
    with (folder/"journal.jsonl").open("ab") as f:
        f.write(serialize(event)); f.flush(); os.fsync(f.fileno())
    return event
def job_path(jobid):
    if not jobid or not all(ch.isalnum() or ch in "-_" for ch in jobid):
        raise ValueError("INVALID_JOB_ID")
    return JOBS/jobid
def config():
    return load(CONFIG)
def init():
    JOBS.mkdir(parents=True,exist_ok=True)
    if not CONFIG.exists():
        atomic(CONFIG,serialize({"schema":1,"provider":"ollama","ollama_url":"http://127.0.0.1:11434","model":"qwen2.5-coder:14b","max_attempts":3,"timeout_seconds":180,"max_generated_bytes":250000,"test_timeout_seconds":45}),new=True)
    print("INITIALIZED",ROOT)
def create(specfile):
    init()
    spec=load(pathlib.Path(specfile))
    if not isinstance(spec,dict) or not isinstance(spec.get("goal"),str) or not spec["goal"].strip():
        raise ValueError("GOAL_REQUIRED")
    if spec.get("language")!="python" or spec.get("test_command")!=["python","-m","unittest","discover","-v"]:
        raise ValueError("ONLY_PYTHON_UNITTEST_SUPPORTED")
    jobid="job-"+uuid.uuid4().hex[:12]
    folder=job_path(jobid);folder.mkdir(parents=False,exist_ok=False)
    atomic(folder/"spec.json",serialize(spec),new=True)
    atomic(folder/"control.json",serialize({"command":"run","revision":1}),new=True)
    atomic(folder/"state.json",serialize({"status":"PENDING","attempt":0,"nextAction":"run"}),new=True)
    receipt(folder,"CREATED",{"specSha":digest((folder/"spec.json").read_bytes())})
    print(jobid)
def state(folder, status, attempt, next_action, extra=None):
    data={"status":status,"attempt":attempt,"nextAction":next_action,"updatedUtc":now()}
    if extra: data.update(extra)
    atomic(folder/"state.json",serialize(data))
    receipt(folder,status,data)
def gate(folder):
    if load(folder/"control.json").get("command")!="run":
        raise InterruptedError("STOP_REQUESTED")
def control(jobid,command):
    folder=job_path(jobid)
    old=load(folder/"control.json")
    old.update(command=command,revision=int(old.get("revision",0))+1)
    atomic(folder/"control.json",serialize(old))
    receipt(folder,"CONTROL_"+command.upper(),{"revision":old["revision"]})
    print("CONTROL",command,jobid)
def safe_file(work,name):
    if not isinstance(name,str) or not name or "\\" in name or ":" in name:
        raise ValueError("INVALID_PATH")
    rel=pathlib.PurePosixPath(name)
    if rel.is_absolute() or any(c in ("..",".","") for c in rel.parts) or len(rel.parts)>5:
        raise ValueError("PATH_ESCAPE")
    if rel.suffix!=".py" or any(part.startswith(".") or part=="__pycache__" for part in rel.parts):
        raise ValueError("ONLY_PYTHON_SOURCES")
    path=work.joinpath(*rel.parts)
    if any(p.is_symlink() for p in [work,*path.parents]):
        raise ValueError("SYMLINK_NOT_ALLOWED")
    if not path.resolve().is_relative_to(work.resolve()):
        raise ValueError("ESCAPE")
    return path
def validate_payload(work, payload, maxbytes):
    if not isinstance(payload,dict) or set(payload)!={"files"}:
        raise ValueError("INVALID_MODEL_JSON")
    files=payload["files"]
    if not isinstance(files,dict) or not files or len(files)>24:
        raise ValueError("INVALID_FILES")
    size=0
    for name,source in files.items():
        safe_file(work,name)
        if not isinstance(source,str):
            raise ValueError("SOURCE_NOT_TEXT")
        size+=len(source.encode("utf-8"))
    if size>maxbytes:
        raise ValueError("OUTPUT_TOO_LARGE")
    return files
def call_model(conf, prompt, attempt):
    if conf["provider"]=="fixture":
        # Fixture provider is ONLY for local infrastructure tests; never real AI evidence.
        return {"files":{"calculator.py":"def add(a, b):\n    return a + b\n","test_calculator.py":"import unittest\nfrom calculator import add\nclass T(unittest.TestCase):\n    def test_add(self):\n        self.assertEqual(add(2,3),5)\n"}}
    if conf["provider"]!="ollama":
        raise RuntimeError("UNSUPPORTED_PROVIDER")
    endpoint=conf["ollama_url"].rstrip("/")
    if endpoint!="http://127.0.0.1:11434":
        raise RuntimeError("LOCAL_ENDPOINT_ONLY")
    system="You are a software engineer. Respond with ONLY a JSON object with one key 'files', a mapping of relative Python filenames to complete source contents. Include unittest tests. No Markdown, shell commands or external dependencies."
    body={"model":conf["model"],"stream":False,"format":"json","messages":[{"role":"system","content":system},{"role":"user","content":prompt}],"options":{"temperature":0.2,"num_ctx":8192}}
    req=urllib.request.Request(endpoint+"/api/chat",data=serialize(body),headers={"Content-Type":"application/json"},method="POST")
    with urllib.request.urlopen(req,timeout=int(conf["timeout_seconds"])) as response:
        envelope=json.load(response)
    if not envelope.get("done"):
        raise RuntimeError("INCOMPLETE_MODEL_RESPONSE")
    return json.loads(envelope["message"]["content"])
def tests(work, timeout):
    env=os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"]="1"
    # No shell, no network tool access granted to the model. This is NOT a secure OS sandbox.
    result=subprocess.run([sys.executable,"-m","unittest","discover","-v"],cwd=work,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
    return {"exitCode":result.returncode,"stdout":result.stdout.decode("utf-8","replace")[-8000:],"stderr":result.stderr.decode("utf-8","replace")[-8000:]}
def run(jobid):
    folder=job_path(jobid)
    spec=load(folder/"spec.json")
    conf=config()
    previous=load(folder/"state.json")
    if previous["status"]=="PASS":
        print("ALREADY_PASS_NO_REPLAY");return
    if previous["status"] in ("RUNNING","UNKNOWN"):
        raise RuntimeError("RECONCILE_UNKNOWN_OPERATION_BEFORE_REPLAY")
    max_attempts=min(5,max(1,int(conf["max_attempts"])))
    feedback=""
    for i in range(int(previous.get("attempt",0))+1,max_attempts+1):
        gate(folder)
        attempt=folder/("attempt-%02d"%i)
        if attempt.exists(): raise RuntimeError("ATTEMPT_EXISTS_NO_REPLAY")
        attempt.mkdir()
        state(folder,"RUNNING",i,"model and tests",{"provider":conf["provider"]})
        prompt=json.dumps({"goal":spec["goal"],"language":"python","test_command":spec["test_command"],"previous_failure":feedback},ensure_ascii=False)
        receipt(folder,"MODEL_INTENT",{"attempt":i,"provider":conf["provider"],"model":conf.get("model"),"promptSha":digest(prompt.encode())})
        try:
            payload=call_model(conf,prompt,i)
        except Exception as e:
            state(folder,"UNKNOWN",i,"inspect provider and journal before retry",{"error":str(e)[:350]})
            raise
        raw=serialize(payload)
        atomic(attempt/"model-response.json",raw,new=True)
        work=attempt/"work";work.mkdir()
        try:
            files=validate_payload(work,payload,int(conf["max_generated_bytes"]))
            for name,source in files.items():
                target=safe_file(work,name)
                atomic(target,source.encode("utf-8"),new=True)
            receipt(folder,"SOURCE_READBACK",{"attempt":i,"files":{name:digest(s.encode("utf-8")) for name,s in files.items()}})
            gate(folder)
            if conf["provider"]!="fixture" and not conf.get("allow_untrusted_test_execution",False):
                state(folder,"BLOCKED",i,"configure an OS-isolated test runner before executing model-generated Python")
                print("BLOCKED_UNTRUSTED_CODE_NOT_SANDBOXED");return
            result=tests(work,int(conf["test_timeout_seconds"]))
        except InterruptedError:
            state(folder,"STOPPED",i,"inspect and resume");return
        except subprocess.TimeoutExpired:
            state(folder,"UNKNOWN",i,"inspect timed out test process before replay");return
        except Exception as e:
            result={"exitCode":-1,"error":str(e)}
        atomic(attempt/"test-result.json",serialize(result),new=True)
        receipt(folder,"TEST",{"attempt":i,"sha":digest((attempt/"test-result.json").read_bytes()),"exitCode":result["exitCode"]})
        if result["exitCode"]==0:
            gate(folder)
            manifest={"atUtc":now(),"provider":conf["provider"],"model":conf.get("model"),"attempt":i,"sources":{name:digest(s.encode("utf-8")) for name,s in files.items()},"testReceiptSha":digest((attempt/"test-result.json").read_bytes()),"realModel":conf["provider"]!="fixture"}
            atomic(folder/"manifest.json",serialize(manifest),new=True)
            state(folder,"PASS",i,"deliver work and verify package",{"manifestSha":digest((folder/"manifest.json").read_bytes())})
            print("PASS",jobid,"attempt",i,"realModel",manifest["realModel"]);return
        feedback=json.dumps(result,ensure_ascii=False)[-5000:]
        state(folder,"FAILED_ATTEMPT",i,"correct using test output",{"testResultSha":digest((attempt/"test-result.json").read_bytes())})
    state(folder,"FAILED",max_attempts,"human review or new job")
    print("FAILED",jobid)
def status(jobid):
    folder=job_path(jobid)
    print(json.dumps({"job":jobid,"state":load(folder/"state.json"),"control":load(folder/"control.json"),"manifest":load(folder/"manifest.json") if (folder/"manifest.json").exists() else None},ensure_ascii=False,indent=2))
def main():
    p=argparse.ArgumentParser()
    sub=p.add_subparsers(dest="action",required=True)
    sub.add_parser("init")
    s=sub.add_parser("create");s.add_argument("spec")
    for cmd in ("run","status","stop","resume"):
        x=sub.add_parser(cmd);x.add_argument("jobid")
    a=p.parse_args()
    if a.action=="init":init()
    elif a.action=="create":create(a.spec)
    elif a.action=="run":run(a.jobid)
    elif a.action=="status":status(a.jobid)
    else:control(a.jobid,"stop" if a.action=="stop" else "run")
if __name__=="__main__":
    main()
