"""Persistent, fail-closed AUTOFABRICADOR workflow (Python 3.12+, stdlib)."""
from __future__ import annotations
import ast
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid

from . import VERSION
from . import isolation
from .providers import Ollama, LlamaCpp, ProviderError
from .storage import (atomic_snapshot, event, json_bytes, load, safe_source, sha_bytes,
                      sha_file, transition, utc, validate_job_id, verify_journal,
                      write, write_json)

DEFAULT = {
    "schema":2,
    "provider":"llama_cpp",
    "model":"af-qwen-coder-1.5b",
    "ollama_endpoint":"http://127.0.0.1:11434",
    "llama_cpp_endpoint":"http://127.0.0.1:11435",
    "llama_cpp_model_path":"VENDOR/models/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf",
    "llama_cpp_model_sha256":"cc324af070c2ecbfd324a30884d2f951a7ff756aba85cb811a6ec436933bb046",
    "docker_image":"python:3.12-slim",
    "isolation_backend":"wasi",
    "max_attempts":3,
    "max_model_calls":3,
    "max_prompt_chars":7000,
    "max_response_bytes":250000,
    "max_source_bytes":150000,
    "max_output_tokens":1900,
    "model_timeout_seconds":180,
    "test_timeout_seconds":60,
    "max_total_tokens":24000,
    "cache_enabled":True,
}
FIXTURE = {
    "program.py": "def add(a, b):\n    return a + b\n",
    "test_program.py": "import unittest\nfrom program import add\n\nclass AdditionTests(unittest.TestCase):\n    def test_add(self):\n        self.assertEqual(add(4, 8), 12)\n",
}
SYSTEM = (
    "You are a local coding worker. Produce a small functioning Python standard-library project. "
    "Reply with a JSON object with exactly one key 'files', mapping relative .py filenames "
    "to COMPLETE source code. Always include at least one test_*.py using unittest. "
    "Use at most 3 files, each under 45 lines; keep functions and tests compact. "
    "No markdown, no commands, no explanations, no claims of test success. "
    "Read previous test errors and fix code when provided. "
    "Never rely on modifying code outside the current project."
)

def root_dir(root):
    return Path(root).resolve()

def init(root):
    root = root_dir(root)
    for folder in ("work","cache","CONTINUIDAD","DIST"):
        (root/folder).mkdir(parents=True,exist_ok=True)
    path = root/"settings.json"
    if not path.exists():
        write_json(path,DEFAULT,new=True)
    return root

def settings(root):
    values=load(root/"settings.json")
    if not isinstance(values,dict) or values.get("schema")!=2:
        raise ValueError("SETTINGS_SCHEMA_INVALID")
    for name in ("max_attempts","max_model_calls","max_prompt_chars","max_response_bytes",
                 "max_source_bytes","max_output_tokens","model_timeout_seconds",
                 "test_timeout_seconds","max_total_tokens"):
        if not isinstance(values.get(name),int) or not 0 < values[name] <= 1000000:
            raise ValueError("BAD_BUDGET:"+name)
    if values.get("provider") not in ("ollama","llama_cpp","fixture"):
        raise ValueError("UNSUPPORTED_PROVIDER")
    if not isinstance(values.get("model"),str) or not values["model"]:
        raise ValueError("MODEL_NOT_SET")
    return values

def jobdir(root,jobid):
    validate_job_id(jobid)
    path = root/"work"/jobid
    if not path.is_dir():raise FileNotFoundError(f"JOB_NOT_FOUND:{jobid}")
    return path

def set_state(folder,status,attempt,next_action,details=None):
    data={"schema":2,"status":status,"attempt":attempt,"nextAction":next_action,"updatedUtc":utc()}
    if details:data.update(details)
    version=transition(folder/"state.json",data,folder/"history")
    event(folder/"journal.jsonl","STATE",{"status":status,"attempt":attempt,"stateSha":version,"nextAction":next_action})
    return data

def create(root,spec_file):
    root=init(root)
    spec=load(Path(spec_file))
    if not isinstance(spec,dict) or not {"goal","language","test_command"}.issubset(spec) or set(spec)-{"goal","language","test_command","acceptance"}:
        raise ValueError("SPEC_KEYS_INVALID")
    acceptance=spec.get("acceptance")
    accepted_bytes=None
    if acceptance is not None:
        if not isinstance(acceptance,dict) or set(acceptance)!={"relativePath","sha256"}:
            raise ValueError("ACCEPTANCE_SPEC_INVALID")
        source=acceptance["relativePath"]
        from pathlib import PurePosixPath
        if not isinstance(source,str) or not source.startswith("examples/"):
            raise ValueError("ACCEPTANCE_ONLY_PROJECT_EXAMPLES")
        parts=PurePosixPath(source).parts
        if len(parts)!=2 or parts[0]!="examples" or not parts[1].startswith("test_") or not parts[1].endswith(".py") or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-.'" for ch in parts[1]):
            raise ValueError("ACCEPTANCE_FILENAME_INVALID")
        source_path=(root/source).resolve()
        if source_path.is_symlink() or not source_path.is_relative_to(root/"examples"):
            raise ValueError("ACCEPTANCE_SOURCE_ESCAPE")
        accepted_bytes=source_path.read_bytes()
        if len(accepted_bytes)>50000 or sha_bytes(accepted_bytes)!=acceptance["sha256"]:
            raise ValueError("ACCEPTANCE_SHA_MISMATCH")
        import ast
        ast.parse(accepted_bytes.decode("utf-8"),filename=source)
    if not isinstance(spec["goal"],str) or not 1<=len(spec["goal"].strip())<=4000:
        raise ValueError("GOAL_MISSING_OR_TOO_LONG")
    if spec["language"]!="python" or spec["test_command"]!=["python","-m","unittest","discover","-v"]:
        raise ValueError("ONLY_PYTHON_UNITTEST_AVAILABLE")
    identifier="AF-"+uuid.uuid4().hex[:16]
    folder=root/"work"/identifier
    folder.mkdir(parents=False,exist_ok=False)
    write_json(folder/"spec.json",spec,new=True)
    if accepted_bytes is not None:
        pinned=folder/"acceptance"/"test_owner_acceptance.py"
        write(pinned,accepted_bytes,new=True)
        if sha_file(pinned)!=acceptance["sha256"]:raise RuntimeError("PINNED_ACCEPTANCE_READBACK_MISMATCH")
    write_json(folder/"control.json",{"command":"RUN","version":1,"updatedUtc":utc()},new=True)
    event(folder/"journal.jsonl","INTAKE",{"objectiveId":identifier,"specSha":sha_file(folder/"spec.json"),"engineVersion":VERSION,"independentAcceptanceSha":acceptance["sha256"] if acceptance else None})
    set_state(folder,"PENDING",0,"preflight and begin new job")
    return identifier

def control(root,jobid,command):
    folder=jobdir(root,jobid)
    path=folder/"control.json"
    old=load(path)
    if old.get("command")==command:return old
    if command not in ("RUN","STOP"):raise ValueError("INVALID_CONTROL")
    new={"command":command,"version":old["version"]+1,"previousSha":sha_file(path),"updatedUtc":utc()}
    transition(path,new,folder/"history")
    event(folder/"journal.jsonl","CONTROL",{"command":command,"version":new["version"]})
    return new

def gate(folder):
    if load(folder/"control.json")["command"]!="RUN":
        raise InterruptedError("STOP_AT_SAFE_BOUNDARY")

def validate_payload(folder,payload,limit):
    if not isinstance(payload,dict) or set(payload)!={"files"} or not isinstance(payload["files"],dict):
        raise ValueError("MODEL_PAYLOAD_INVALID")
    files=payload["files"]
    if not (1<=len(files)<=24) or not any(name.startswith("test_") and name.endswith(".py") for name in files):
        raise ValueError("SOURCE_OR_UNIT_TEST_MISSING")
    size=0
    for name,content in files.items():
        safe_source(folder,name)
        if not isinstance(content,str):raise ValueError("CODE_NOT_A_STRING")
        size+=len(content.encode("utf-8"))
        ast.parse(content,filename=name)
    if size>limit:raise ValueError("SOURCE_TOO_LARGE")
    return files

def fixture_generate():
    """This is *not* AI. Only literal, source-pinned fixtures may run on host."""
    return {"files":dict(FIXTURE)}, {"provider":"fixture","promptTokens":0,"completionTokens":0,"elapsedMs":0}

def pinned_fixture_matches(files):
    return (set(files)==set(FIXTURE) and
            all(sha_bytes(files[k].encode("utf-8"))==sha_bytes(v.encode("utf-8")) for k,v in FIXTURE.items()))

def fixture_test(work,files):
    if not pinned_fixture_matches(files):
        raise RuntimeError("UNTRUSTED_FIXTURE_WILL_NOT_EXECUTE_ON_HOST")
    started=time.monotonic()
    result=subprocess.run([sys.executable,"-m","unittest","discover","-v"],cwd=work,
                          env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1"},
                          stdin=subprocess.DEVNULL,capture_output=True,timeout=12)
    stderr=result.stderr.decode("utf-8","replace")[-9000:]
    counts=re.findall(r"(?m)^Ran (\d+) tests? in ",stderr)
    executed=int(counts[-1]) if counts else 0
    return {"backend":"PINNED_FIXTURE_ONLY_NOT_SANDBOX","exitCode":result.returncode if executed>=1 else -7,
            "testCount":executed,"stdout":result.stdout.decode("utf-8","replace")[-9000:],
            "stderr":stderr,"durationMs":int((time.monotonic()-started)*1000)}

def cache_lookup(root,key):
    path=root/"cache"/(key+".json")
    if not path.exists():return None
    record=load(path)
    if record.get("key")!=key or sha_bytes(json_bytes(record.get("payload")))!=record.get("payloadSha"):
        raise RuntimeError("CACHE_INTEGRITY_MISMATCH")
    return record.get("payload")

def cache_store(root,key,payload,usage):
    path=root/"cache"/(key+".json")
    if path.exists():
        if cache_lookup(root,key)!=payload:raise RuntimeError("CACHE_CONFLICT")
        return
    write_json(path,{"key":key,"payload":payload,"payloadSha":sha_bytes(json_bytes(payload)),
                     "usage":usage,"storedUtc":utc()},new=True)

def runner_preflight(root,cfg):
    backend=cfg.get("isolation_backend","docker")
    if backend=="wasi":
        from .wasi_isolation import wasi_preflight
        return wasi_preflight(root)
    if backend=="docker":
        isolation.docker_preflight(cfg["docker_image"])
        return {"backend":"docker-linux"}
    raise isolation.IsolationUnavailable("NO_VERIFIED_ISOLATION_BACKEND")

def runner_execute(root,cfg,work):
    backend=cfg.get("isolation_backend","docker")
    if backend=="wasi":
        from .wasi_isolation import run_tests as wasi_run
        return wasi_run(work,root,timeout=cfg["test_timeout_seconds"])
    if backend=="docker":
        return isolation.run_tests(work,timeout=cfg["test_timeout_seconds"],image=cfg["docker_image"])
    raise isolation.IsolationUnavailable("NO_VERIFIED_ISOLATION_BACKEND")

def doctor(root):
    root=init(root)
    cfg=settings(root)
    report={"engineVersion":VERSION,"projectRoot":str(root),"provider":cfg["provider"],
            "python":sys.version.split()[0],"isolation":"UNKNOWN","model":"UNKNOWN"}
    try:
        ready=runner_preflight(root,cfg)
        report["isolation"]=ready
    except isolation.IsolationUnavailable as error:
        report["isolation"]=str(error)
    if cfg["provider"]=="fixture":
        report["model"]="SIMULATION_ONLY"
    else:
        try:
            if cfg["provider"]=="llama_cpp":
                m=LlamaCpp(cfg["llama_cpp_endpoint"],cfg["model"],root/cfg["llama_cpp_model_path"],cfg["llama_cpp_model_sha256"],timeout=4).available_model()
            else:
                m=Ollama(cfg["ollama_endpoint"],cfg["model"],timeout=4).available_model()
            report["model"]={"status":"AVAILABLE","digest":m["digest"],"name":m["model"]}
        except (ProviderError, OSError) as error:
            report["model"]={"status":"NOT_AVAILABLE","detail":str(error)[:200]}
    return report

def metrics(root):
    """Count only actually recorded attempts. No invented cash or energy savings."""
    root=init(root)
    rows=[]
    totals={"jobs":0,"completedRealAI":0,"fixturePass":0,"modelCalls":0,
            "cacheHits":0,"promptTokens":0,"completionTokens":0,"elapsedModelMs":0,"advisorCalls":0}
    for folder in sorted((root/"work").glob("AF-*")):
        if not (folder/"state.json").is_file():continue
        totals["jobs"]+=1
        status=load(folder/"state.json")["status"]
        totals["completedRealAI"]+=int(status=="PASS")
        totals["fixturePass"]+=int(status=="PASS_FIXTURE")
        for record in sorted(folder.glob("attempt-*/model.json")):
            saved=load(record)
            usage=saved.get("usage",{})
            cached=bool(saved.get("cached"))
            provider=usage.get("provider")
            reconciled=(record.parent/"RECONCILED-SOURCE.json").is_file()
            totals["cacheHits"]+=int(cached and not reconciled)
            # An original Codex/OpenCode call may be admitted from its saved
            # stdout without another inference. Count that original call once.
            totals["modelCalls"]+=int((provider in ("ollama","llama_cpp","aider","codex","opencode") and not cached) or
                                      (reconciled and provider in ("codex","opencode")))
            for key in ("promptTokens","completionTokens"):
                totals[key]+=int(usage.get(key) or 0)
            totals["elapsedModelMs"]+=int(usage.get("elapsedModelMs") or usage.get("elapsedMs") or 0)
        for advice_file in (folder/"advice").glob("*.json") if (folder/"advice").is_dir() else ():
            if load(advice_file).get("status")=="ADVICE_ONLY_NOT_APPLIED":
                totals["advisorCalls"]+=1
        rows.append({"jobId":folder.name,"status":status})
    totals["knownApiCostEur"]=0
    totals["costNote"]="Both Ollama and local llama.cpp have no cloud per-token API bill here. Electricity, hardware and model-quality costs are not measured."
    totals["possibleCachedCallsAvoided"]=totals["cacheHits"]
    return {"totals":totals,"jobs":rows}

def capabilities():
    return {"schema":1,"product":"AUTOFABRICADOR","version":VERSION,
            "interface":"CLI JSON stdout",
            "commands":["init","doctor","bootstrap","bootstrap-editors","agents","housekeeping","create","draft","run","run-aider","run-source","reconcile-source","mission-create","mission-run","mission-status","mission-stop","mission-resume","mission-reconcile","editors","advise","status","verify","stop",
                        "resume","run-queued","list","metrics","serve-start","serve-status","serve-stop","bundle","verify-bundle","audit-inventory","audit-create","audit-run","audit-status","audit-stop","audit-verify","repair-create","repair-run","repair-verify","python-create","python-run","python-stop","python-status","python-verify","pygen-create","pygen-run","pygen-stop","pygen-status","pygen-verify","pygen-reconcile","pygen-repair-create","pygen-repair-run","pygen-repair-verify","browser-close","browser-close-status","browser-close-verify"],
            "specSchema":{"goal":"nonempty string up to 4000 chars","language":"python",
                          "test_command":["python","-m","unittest","discover","-v"]},
            "provider":"Ollama or llama.cpp localhost; fixture only for non-AI tests",
            "languages":["python"],"realAIRequires":["SHA-pinned local llama.cpp model or Ollama","verified WASI isolated runner or Docker Linux"],
            "externalAIClients":"Any client able to invoke this CLI and parse JSON; no universal agent connector claimed.",
            "authorization":"No protected host/ROOT actions exposed."
            }

def summary(root,jobid):
    folder=jobdir(root,jobid)
    return {"jobId":jobid,"state":load(folder/"state.json"),
            "control":load(folder/"control.json"),
            "manifest":load(folder/"manifest.json") if (folder/"manifest.json").exists() else None,
            "journal":verify_journal(folder/"journal.jsonl")}

def verify_job(root,jobid):
    folder=jobdir(root,jobid)
    report=summary(root,jobid)
    manifest=report.get("manifest")
    if manifest:
        expected_manifest=report["state"].get("manifestSha")
        if expected_manifest!=sha_file(folder/"manifest.json"):
            raise RuntimeError("MANIFEST_STATE_SHA_DRIFT")
        intake=[load for load in (json.loads(line) for line in (folder/"journal.jsonl").read_text("utf-8").splitlines()) if load.get("operation")=="INTAKE"]
        if len(intake)!=1 or intake[0]["detail"].get("specSha")!=sha_file(folder/"spec.json"):
            raise RuntimeError("INTAKE_SPEC_SHA_DRIFT")
        for name, expected in manifest["sourceHashes"].items():
            folder_name=f"attempt-{manifest['attempt']:02d}"
            actual=sha_file(safe_source(folder/folder_name/"code",name))
            if actual != expected:
                raise RuntimeError("SOURCE_RECEIPT_DRIFT:"+name)
        receipt=folder/f"attempt-{manifest['attempt']:02d}"/"test.json"
        if sha_file(receipt)!=manifest["testReceiptSha"]:
            raise RuntimeError("TEST_RECEIPT_DRIFT")
        model_record=load(folder/f"attempt-{manifest['attempt']:02d}"/"model.json")
        if model_record.get("usage",{}).get("provider")=="aider":
            src=folder/f"attempt-{manifest['attempt']:02d}"
            proposal=load(src/"AIDER-RECEIPT.json")
            req=load(src/"AIDER-REQUEST.json")
            invocation=load(src/"EDITOR-EXECUTION.json")
            proposed=proposal.get("proposedSource")
            if not isinstance(proposed,str) or sha_bytes(proposed.encode("utf-8"))!=proposal.get("proposedSha256"):
                raise RuntimeError("AIDER_PROPOSAL_RECEIPT_DRIFT")
            if not proposal.get("sourceUnchanged") or invocation.get("exitCode")!=0:
                raise RuntimeError("AIDER_PROPOSAL_EFFECTS_NOT_VERIFIED")
            if sha_file(src/Path(req["target"]).name)!=proposal.get("sourcePreimageSha256"):
                raise RuntimeError("AIDER_SOURCE_PREIMAGE_DRIFT")
            if model_record["payload"]["files"].get(Path(req["target"]).name)!=proposed:
                raise RuntimeError("AIDER_PROPOSAL_PAYLOAD_DRIFT")
        if model_record.get("usage",{}).get("provider") in ("codex","opencode"):
            from . import source_editors
            at=folder/f"attempt-{manifest['attempt']:02d}"
            request=load(at/"EDITOR-REQUEST.json")
            execution=load(at/"EDITOR-EXECUTION.json")
            tool=request.get("tool")
            if tool not in ("codex","opencode") or execution.get("tool")!=tool:
                raise RuntimeError("NATIVE_EDITOR_IDENTITY_DRIFT")
            out=(at/"EDITOR-STDOUT.bin").read_bytes()
            if sha_bytes(out)!=execution.get("stdoutSha") or execution.get("returnCode")!=0:
                raise RuntimeError("NATIVE_EDITOR_STDOUT_RECEIPT_DRIFT")
            if execution.get("requestSha")!=sha_file(at/"EDITOR-REQUEST.json"):
                raise RuntimeError("NATIVE_EDITOR_REQUEST_SHA_DRIFT")
            if model_record.get("modelDigest")!="sha256:"+request.get("modelSha",""):
                raise RuntimeError("NATIVE_EDITOR_MODEL_SHA_DRIFT")
            if sha_file(at/request["target"])!=request["seedSha"]:
                raise RuntimeError("NATIVE_EDITOR_SEED_SHA_DRIFT")
            candidate,_=source_editors.parse_source(tool,out)
            if model_record.get("payload",{}).get("files",{}).get(request["target"])!=candidate:
                raise RuntimeError("NATIVE_EDITOR_PROPOSAL_DRIFT")
            recovered=at/"RECONCILED-SOURCE.json"
            if execution.get("status")=="FAILED_INVALID_SOURCE":
                if not recovered.is_file():
                    raise RuntimeError("NATIVE_EDITOR_RECONCILIATION_RECEIPT_MISSING")
                record=load(recovered)
                if record.get("originalFailureReceiptSha")!=sha_file(at/"EDITOR-EXECUTION.json") or record.get("proposedSha")!=sha_bytes(candidate.encode()):
                    raise RuntimeError("NATIVE_EDITOR_RECOVERY_SHA_DRIFT")
            elif execution.get("status")!="PROPOSED_UNTESTED":
                raise RuntimeError("NATIVE_EDITOR_NOT_PROPOSED")
        spec=load(folder/"spec.json")
        if spec.get("acceptance"):
            actual=sha_file(folder/"acceptance"/"test_owner_acceptance.py")
            if actual!=spec["acceptance"]["sha256"]:raise RuntimeError("OWNER_ACCEPTANCE_SHA_DRIFT")
            test_data=load(receipt)
            if test_data.get("independentTestCount",0)<1 or manifest.get("independentTestCount",0)<1:
                raise RuntimeError("OWNER_ACCEPTANCE_NOT_EXECUTED")
            if manifest.get("independentTestSha")!=spec["acceptance"]["sha256"]:
                raise RuntimeError("OWNER_ACCEPTANCE_MANIFEST_SHA_DRIFT")
    report["verified"]=True
    return report

def resume_saved_candidate(root,folder,jobid,n,cfg,model_digest):
    """Continue an already evidenced source candidate WITHOUT another model call."""
    attempt=folder/f"attempt-{n:02d}"
    model_path=attempt/"model.json"
    code=attempt/"code"
    if not model_path.is_file() or not code.is_dir() or (attempt/"test.json").exists():
        raise RuntimeError("STOPPED_JOB_NOT_AT_SAFE_TEST_BOUNDARY_RECONCILE")
    saved=load(model_path)
    if saved.get("modelDigest")!=model_digest:
        raise RuntimeError("MODEL_IDENTITY_CHANGED_DURING_RESUME")
    files=validate_payload(code,saved["payload"],cfg["max_source_bytes"])
    current=atomic_snapshot(code)
    expected={name:sha_bytes(content.encode("utf-8")) for name,content in files.items()}
    if current!=expected:
        raise RuntimeError("RESUME_SOURCE_NOT_IDENTICAL_TO_MODEL_RECEIPT")
    events=[json.loads(line) for line in (folder/"journal.jsonl").read_text("utf-8").splitlines()]
    verified_sources=any(x["operation"]=="VERIFIER_SOURCE" and x["detail"].get("attempt")==n
                         and x["detail"].get("sha")==sha_bytes(json_bytes(current)) for x in events)
    verified_model=any(x["operation"]=="CODER_READBACK" and x["detail"].get("attempt")==n
                       and x["detail"].get("responseSha")==sha_file(model_path) for x in events)
    if not verified_sources or not verified_model:
        raise RuntimeError("RESUME_ORIGINAL_RECEIPTS_MISSING")
    verify_journal(folder/"journal.jsonl")
    gate(folder)
    set_state(folder,"TEST_PENDING",n,"resume only pending isolated tests")
    event(folder/"journal.jsonl","VERIFIER_RESUMED",{"attempt":n,"modelReplayed":False})
    try:
        if cfg["provider"]=="fixture": result=fixture_test(code,files)
        else: result=runner_execute(root,cfg,code)
    except (isolation.IsolationUnavailable,subprocess.TimeoutExpired) as error:
        set_state(folder,"UNKNOWN",n,"reconcile test process before any retry",{"error":str(error)[:350]})
        return summary(root,jobid)
    if result["exitCode"]==0 and result.get("testCount",0)<1:
        result.update(exitCode=-7,failureReason="NO_TEST_CASES_EXECUTED")
    if load(folder/"spec.json").get("acceptance") and result.get("independentTestCount",0)<1:
        result.update(exitCode=-8,failureReason="PINNED_OWNER_ACCEPTANCE_NOT_EXECUTED")
    write_json(attempt/"test.json",result,new=True)
    event(folder/"journal.jsonl","VERIFIER_RECEIPT",{"attempt":n,"exitCode":result["exitCode"],
                                                      "testSha":sha_file(attempt/"test.json")})
    if result["exitCode"]!=0:
        set_state(folder,"FAILED_ATTEMPT",n,"repair based on resumed test receipt")
        return summary(root,jobid)
    usage=saved.get("usage",{})
    cumulative={"modelCalls":int(cfg["provider"]!="fixture" and not saved.get("cached")),
                "cacheHits":int(bool(saved.get("cached"))),"promptTokens":usage.get("promptTokens") or 0,
                "completionTokens":usage.get("completionTokens") or 0,
                "elapsedModelMs":usage.get("elapsedMs") or 0}
    receipt=verify_journal(folder/"journal.jsonl")
    manifest={"schema":2,"jobId":jobid,"attempt":n,"atUtc":utc(),
              "provider":cfg["provider"],"realAI":cfg["provider"]!="fixture",
              "model":cfg["model"] if cfg["provider"]!="fixture" else None,
              "modelDigest":model_digest,"sourceHashes":current,
              "testReceiptSha":sha_file(attempt/"test.json"),
              "journalTipSha":receipt["lastEventSha"],"usage":cumulative,
              "isolation":result["backend"],"runnerImageId":result.get("imageId"),"resumedWithoutModelReplay":True,
              "independentTestCount":result.get("independentTestCount",0),"independentTestSha":result.get("independentTestSha"),"testCount":result.get("testCount",0)}
    write_json(folder/"manifest.json",manifest,new=True)
    set_state(folder,"PASS" if cfg["provider"]!="fixture" else "PASS_FIXTURE",
              n,"verified resumed candidate ready",{"manifestSha":sha_file(folder/"manifest.json")})
    return verify_job(root,jobid)

def run(root,jobid):
    root=init(root); cfg=settings(root)
    folder=jobdir(root,jobid); current=load(folder/"state.json")
    if current["status"] in ("PASS","PASS_FIXTURE"):
        return {"status":"ALREADY_PASSED_NO_REPLAY","jobId":jobid}
    if current["status"] in ("RUNNING","MODEL_PENDING","TEST_PENDING","UNKNOWN"):
        raise RuntimeError("UNCERTAIN_OPERATION_RECONCILE_DO_NOT_REPLAY")
    if current["status"] in ("FAILED","STAGNATED"):
        raise RuntimeError("FINAL_FAILED_OR_STAGNATED_REPLAN_NEW_JOB_REQUIRED")
    try:
        gate(folder)
    except InterruptedError:
        set_state(folder,"STOPPED",current["attempt"],"resume control before running")
        return summary(root,jobid)
    spec=load(folder/"spec.json")
    model=None
    model_digest=None
    if cfg["provider"] in ("ollama","llama_cpp"):
        # Before any model call, prove that a constrained test runner exists.
        try:
            runner_preflight(root,cfg)
        except isolation.IsolationUnavailable as error:
            set_state(folder,"BLOCKED_ISOLATION",current["attempt"],"prepare verified isolated runner, then run",{"blocker":str(error)})
            return summary(root,jobid)
        if current["status"] in ("STOPPED","DRAFT_READY_UNTESTED","BLOCKED_ISOLATION") and current["attempt"]>0:
            candidate=folder/f"attempt-{current['attempt']:02d}"
            prior=candidate/"model.json"
            if prior.is_file() and not (candidate/"test.json").exists():
                saved=load(prior)
                digest=saved.get("modelDigest")
                if not isinstance(digest,str) or not digest:
                    raise RuntimeError("CANDIDATE_MODEL_DIGEST_MISSING")
                if cfg["provider"]=="llama_cpp":
                    expected="sha256:"+cfg["llama_cpp_model_sha256"]
                    if digest!=expected or sha_file(root/cfg["llama_cpp_model_path"])!=cfg["llama_cpp_model_sha256"]:
                        raise RuntimeError("RESUME_MODEL_IDENTITY_DRIFT")
                return resume_saved_candidate(root,folder,jobid,current["attempt"],cfg,digest)
        try:
            if cfg["provider"]=="llama_cpp":
                model=LlamaCpp(cfg["llama_cpp_endpoint"],cfg["model"],root/cfg["llama_cpp_model_path"],cfg["llama_cpp_model_sha256"],timeout=cfg["model_timeout_seconds"],max_response_bytes=cfg["max_response_bytes"])
            else:
                model=Ollama(cfg["ollama_endpoint"],cfg["model"],timeout=cfg["model_timeout_seconds"],max_response_bytes=cfg["max_response_bytes"])
            model_digest=model.available_model()["digest"]
        except ProviderError as error:
            set_state(folder,"BLOCKED_PROVIDER",current["attempt"],"start/verify configured local inference backend, then run",{"blocker":str(error)})
            return summary(root,jobid)
    else:
        model_digest="INTERNAL_TRUSTED_FIXTURE_SHA256_"+sha_bytes(json_bytes(FIXTURE))
    if current["status"] in ("STOPPED","DRAFT_READY_UNTESTED","BLOCKED_ISOLATION") and current["attempt"]>0 and (folder/f"attempt-{current['attempt']:02d}"/"model.json").exists() and not (folder/f"attempt-{current['attempt']:02d}"/"test.json").exists():
        return resume_saved_candidate(root,folder,jobid,current["attempt"],cfg,model_digest)
    previous=current["attempt"]
    feedback=""
    if previous>0:
        test=folder/f"attempt-{previous:02d}"/"test.json"
        if test.exists(): feedback=json.dumps(load(test),ensure_ascii=False)[-4500:]
        if current["status"] not in ("FAILED_ATTEMPT","STOPPED","BLOCKED_ISOLATION","BLOCKED_PROVIDER"):
            raise RuntimeError("PREVIOUS_ATTEMPT_REQUIRES_RECONCILIATION")
    cumulative={"modelCalls":0,"cacheHits":0,"promptTokens":0,"completionTokens":0,"elapsedModelMs":0}
    for old_attempt in range(1,previous+1):
        past=folder/f"attempt-{old_attempt:02d}"/"model.json"
        if past.is_file():
            saved=load(past)
            usage=saved.get("usage",{})
            cumulative["cacheHits"]+=int(bool(saved.get("cached")))
            cumulative["modelCalls"]+=int(usage.get("provider") in ("ollama","llama_cpp") and not saved.get("cached"))
            for key in ("promptTokens","completionTokens","elapsedModelMs"):
                cumulative[key]+=int(usage.get(key) or 0)
    for n in range(previous+1,min(cfg["max_attempts"],cfg["max_model_calls"])+1):
        try: gate(folder)
        except InterruptedError:
            set_state(folder,"STOPPED",n-1,"resume control before continuing")
            return summary(root,jobid)
        attempt=folder/f"attempt-{n:02d}"
        if attempt.exists():raise RuntimeError("ATTEMPT_REPLAY_NOT_ALLOWED")
        attempt.mkdir()
        prompt=json.dumps({"goal":spec["goal"],"language":"python","previousTestFailure":feedback,
                           "requirements":"Python stdlib and unittest"},ensure_ascii=False)
        if len(prompt)>cfg["max_prompt_chars"]:
            set_state(folder,"BLOCKED_BUDGET",n-1,"reduce task/context",{"reason":"prompt_chars_exceeded"})
            return summary(root,jobid)
        key=sha_bytes(json_bytes({"prompt":prompt,"system":SYSTEM,"modelDigest":model_digest,
                                  "provider":cfg["provider"],"version":VERSION,
                                  "maxOutputTokens":cfg["max_output_tokens"]}))
        set_state(folder,"MODEL_PENDING",n,"await model response")
        event(folder/"journal.jsonl","CODER_INTENT",{"attempt":n,"promptSha":sha_bytes(prompt.encode()),
                    "modelDigest":model_digest,"cacheKey":key,"operationId":f"{jobid}.MODEL.{n}"})
        usage={}
        payload=None
        from_cache=False
        if cfg["cache_enabled"]:
            payload=cache_lookup(root,key)
            if payload is not None:
                from_cache=True
                cumulative["cacheHits"]+=1
                usage={"provider":cfg["provider"],"cacheHit":True,"promptTokens":0,"completionTokens":0,"elapsedMs":0}
        if payload is None:
            try:
                if cfg["provider"]=="fixture":payload,usage=fixture_generate()
                else:payload,usage=model.generate(SYSTEM,prompt,cfg["max_output_tokens"])
            except ProviderError as error:
                # A FINISHED model reply with finish_reason=length is a
                # deterministic bounded-budget failure, not unknown I/O.
                # The original requested attempt is spent and cannot replay.
                if str(error)=="LOCAL_MODEL_OUTPUT_TRUNCATED":
                    event(folder/"journal.jsonl","MODEL_OUTPUT_LIMIT_PROVEN",
                          {"attempt":n,"reason":"FINISH_REASON_LENGTH",
                           "provider":"llama_cpp","modelIntentAlreadySpent":True})
                    set_state(folder,"FAILED_MODEL_OUTPUT_TRUNCATED",n,
                              "create NEW model job with larger bounded token budget",
                              {"error":str(error),"noBlindReplay":True})
                    return summary(root,jobid)
                set_state(folder,"UNKNOWN",n,"inspect provider/journal and reconcile before any replay",
                          {"errorType":type(error).__name__,"error":str(error)[:350]})
                return summary(root,jobid)
            except Exception as error:
                set_state(folder,"UNKNOWN",n,"inspect provider/journal and reconcile before any replay",
                          {"errorType":type(error).__name__,"error":str(error)[:350]})
                return summary(root,jobid)
            cumulative["modelCalls"]+=1 if cfg["provider"]!="fixture" else 0
            cumulative["promptTokens"]+=usage.get("promptTokens") or 0
            cumulative["completionTokens"]+=usage.get("completionTokens") or 0
            cumulative["elapsedModelMs"]+=usage.get("elapsedMs") or 0
        write_json(attempt/"model.json",{"payload":payload,"usage":usage,"cached":from_cache,
                    "modelDigest":model_digest},new=True)
        event(folder/"journal.jsonl","CODER_READBACK",{"attempt":n,"responseSha":sha_file(attempt/"model.json")})
        try:
            code=attempt/"code";code.mkdir()
            files=validate_payload(code,payload,cfg["max_source_bytes"])
            for name,content in files.items():
                write(safe_source(code,name),content.encode("utf-8"),new=True)
            actual=atomic_snapshot(code)
            event(folder/"journal.jsonl","VERIFIER_SOURCE",{"attempt":n,"sha":sha_bytes(json_bytes(actual))})
        except (ValueError, SyntaxError, TypeError) as error:
            write_json(attempt/"test.json",{"exitCode":-1,"reason":"STATIC_VALIDATION","error":str(error)[:1200]},new=True)
            feedback=str(error)[:1200]
            set_state(folder,"FAILED_ATTEMPT",n,"repair static errors from previous attempt")
            continue
        if not from_cache and cfg["cache_enabled"]:
            cache_store(root,key,payload,usage)
        if cfg["provider"]!="fixture" and cumulative["promptTokens"]+cumulative["completionTokens"]>cfg["max_total_tokens"]:
            set_state(folder,"BLOCKED_BUDGET",n,"increase token budget only after review")
            return summary(root,jobid)
        try: gate(folder)
        except InterruptedError:
            set_state(folder,"STOPPED",n,"inspect pending code before resume")
            return summary(root,jobid)
        set_state(folder,"TEST_PENDING",n,"run isolated tests")
        event(folder/"journal.jsonl","VERIFIER_INTENT",{"attempt":n,"sourceSha":sha_bytes(json_bytes(actual)),
                  "backend":"pinned-fixture" if cfg["provider"]=="fixture" else cfg.get("isolation_backend","docker")})
        try:
            if cfg["provider"]=="fixture":result=fixture_test(code,files)
            else:result=runner_execute(root,cfg,code)
        except (isolation.IsolationUnavailable,subprocess.TimeoutExpired) as error:
            set_state(folder,"UNKNOWN",n,"reconcile test process before any retry",
                      {"error":str(error)[:350]})
            return summary(root,jobid)
        if result["exitCode"]==0 and result.get("testCount",0)<1:
            result.update(exitCode=-7,failureReason="NO_TEST_CASES_EXECUTED")
        if load(folder/"spec.json").get("acceptance") and result.get("independentTestCount",0)<1:
            result.update(exitCode=-8,failureReason="PINNED_OWNER_ACCEPTANCE_NOT_EXECUTED")
        write_json(attempt/"test.json",result,new=True)
        event(folder/"journal.jsonl","VERIFIER_RECEIPT",{"attempt":n,"exitCode":result["exitCode"],"testSha":sha_file(attempt/"test.json")})
        if result["exitCode"]==0:
            validated=verify_journal(folder/"journal.jsonl")
            manifest={"schema":2,"jobId":jobid,"attempt":n,"atUtc":utc(),
                       "provider":cfg["provider"],"realAI":cfg["provider"]!="fixture",
                       "model":cfg["model"] if cfg["provider"]!="fixture" else None,
                       "modelDigest":model_digest,"sourceHashes":actual,
                       "testReceiptSha":sha_file(attempt/"test.json"),
                       "journalTipSha":validated["lastEventSha"],
                       "usage":cumulative,
                       "isolation":result["backend"],"runnerImageId":result.get("imageId"),"testCount":result.get("testCount"),"independentTestCount":result.get("independentTestCount",0),"independentTestSha":result.get("independentTestSha")}
            write_json(folder/"manifest.json",manifest,new=True)
            set_state(folder,"PASS" if cfg["provider"]!="fixture" else "PASS_FIXTURE",
                      n,"verified release candidate ready",{"manifestSha":sha_file(folder/"manifest.json")})
            return verify_job(root,jobid)
        feedback=json.dumps(result,ensure_ascii=False)[-4000:]
        set_state(folder,"FAILED_ATTEMPT",n,"repair based on test receipt")
    set_state(folder,"FAILED",cfg["max_attempts"],"review and submit a new task")
    return summary(root,jobid)
