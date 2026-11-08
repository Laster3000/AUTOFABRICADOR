# coding: utf-8
"""Original-receipt-based JS/TS AI jobs with independent WASI acceptance.

A separate AL job namespace prevents contaminating legacy Python acceptance.
Only a bounded source proposal is collected from a no-tool local CLI; compiled
JS/TS runs exclusively inside wasm with explicit fuel, no FS/network grants.
"""
from __future__ import annotations
import json,os
from pathlib import Path
import re
import subprocess
import time
import uuid

from . import engine,local_runtime,source_editors,js_wasi,npm_umd
from .storage import (atomic_snapshot,event,json_bytes,load,sha_bytes,sha_file,
                      transition,utc,write,write_json,verify_journal)

def jobdir(root,jobid):
    if not isinstance(jobid,str) or not re.fullmatch(r"AL-[a-f0-9]{16}",jobid):
        raise ValueError("LANG_JOB_ID_INVALID")
    folder=Path(root).resolve()/"langjobs"/jobid
    if not folder.is_dir():raise FileNotFoundError("LANG_JOB_NOT_FOUND")
    return folder

def _valid_spec(spec):
    required={"language","goal","sources","function","acceptance"}
    if not isinstance(spec,dict) or not required.issubset(spec) or set(spec)-required-{"dependencies"}:
        raise ValueError("LANG_SPEC_KEYS_NOT_EXACT")
    dependencies=spec.get("dependencies",[])
    if not isinstance(dependencies,list) or len(dependencies)>2 or len(set(dependencies))!=len(dependencies) or any(x not in npm_umd.ALLOW for x in dependencies):
        raise ValueError("LANG_DEPENDENCIES_NOT_PINNED_ALLOWLIST")
    lang=spec["language"]
    if lang not in ("javascript","typescript"):raise ValueError("ONLY_JS_TS_FULL_WASI_ACCEPTANCE_SUPPORTED")
    if not isinstance(spec["goal"],str) or not 20<=len(spec["goal"])<=2400:
        raise ValueError("LANG_GOAL_LENGTH")
    if not re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]{0,45}",spec["function"]):
        raise ValueError("LANG_TARGET_FUNCTION_UNSAFE")
    suffix=".js" if lang=="javascript" else ".ts"
    src=spec["sources"]
    if not isinstance(src,dict) or not 1<=len(src)<=5:raise ValueError("LANG_SOURCE_COUNT")
    if len(set(src))!=len(src):raise ValueError("LANG_DUPLICATE_SOURCE")
    if not all(re.fullmatch(r"[a-z][a-z0-9_-]{0,45}"+re.escape(suffix),name) and
               isinstance(text,str) and 10<=len(text)<=5000 for name,text in src.items()):
        raise ValueError("LANG_SOURCE_SEEDS_UNSAFE")
    cases=spec["acceptance"]
    if not isinstance(cases,list) or not 5<=len(cases)<=50:
        raise ValueError("LANG_OWNER_CASE_COUNT")
    if any(not isinstance(row,dict) or set(row)!={"args","expected"} or
           not isinstance(row["args"],list) for row in cases):
        raise ValueError("LANG_OWNER_CASE_BAD")
    if len(json_bytes(cases))>20000:raise ValueError("LANG_OWNER_CASES_TOO_LARGE")
    return True

def create(root,spec_path):
    root=engine.init(root)
    location=Path(spec_path).resolve()
    if not location.is_file() or location.is_symlink() or not location.is_relative_to(root/"examples"):
        raise ValueError("LANG_SPEC_MUST_BE_PROJECT_EXAMPLE")
    spec=load(location)
    _valid_spec(spec)
    # No job or model effect before verifying the runner's immutable identity.
    js_wasi.preflight(root,spec["language"])
    npm_umd.preflight(root,spec.get("dependencies",[]))
    # Identical already accepted owner+goal+model source is reusable: no new
    # inference, duplicate work or inflated completion counters.
    for existing in sorted((root/"langjobs").glob("AL-*/spec.json")):
        if load(existing)!=spec:continue
        prior=existing.parent
        state=load(prior/"state.json")["status"]
        if state=="PASS":
            verify(root,prior.name)
            return {"jobId":prior.name,"status":"EXISTING_ACCEPTED_REUSE_NO_MODEL_CALL",
                    "ownerAcceptanceSha":sha_file(prior/"owner-acceptance.json")}
        raise RuntimeError("IDENTICAL_LANGUAGE_JOB_EXISTS_NOT_ACCEPTED_RECONCILE_NO_DUPLICATE")
    jid="AL-"+uuid.uuid4().hex[:16]
    folder=root/"langjobs"/jid
    folder.mkdir(parents=True,exist_ok=False)
    write_json(folder/"spec.json",spec,new=True)
    acceptance={"schema":1,"cases":spec["acceptance"],"function":spec["function"],
                "language":spec["language"]}
    write_json(folder/"owner-acceptance.json",acceptance,new=True)
    write_json(folder/"control.json",{"schema":1,"command":"RUN","version":1,"atUtc":utc()},new=True)
    write_json(folder/"state.json",{"schema":1,"status":"PENDING","attempt":0,
                                   "nextAction":"run-language editor source proposal"},new=True)
    event(folder/"journal.jsonl","INTAKE",{"jobId":jid,
         "specSha":sha_file(folder/"spec.json"),
         "ownerAcceptanceSha":sha_file(folder/"owner-acceptance.json"),
         "sourceNames":list(spec["sources"])})
    return {"jobId":jid,"language":spec["language"],
            "ownerAcceptanceSha":sha_file(folder/"owner-acceptance.json")}

def _state(folder,status,attempt,next_action):
    old=sha_file(folder/"state.json")
    transition(folder/"state.json",{"schema":1,"status":status,"attempt":attempt,
               "atUtc":utc(),"nextAction":next_action},folder/"history")
    event(folder/"journal.jsonl","STATE",{"status":status,"attempt":attempt,
          "previousStateSha":old,"stateSha":sha_file(folder/"state.json")})

def control(root,jobid,command):
    folder=jobdir(root,jobid)
    if command not in ("RUN","STOP"):raise ValueError("LANG_CONTROL_INVALID")
    old=load(folder/"control.json")
    if old["command"]==command:return old
    transition(folder/"control.json",{"schema":1,"command":command,
               "version":old["version"]+1,"previousSha":sha_file(folder/"control.json"),
               "atUtc":utc()},folder/"history")
    event(folder/"journal.jsonl","CONTROL",{"command":command})
    return load(folder/"control.json")

def _parse(tool,raw,expected):
    texts=[]
    tokens={}
    for line in raw.decode("utf-8","replace").splitlines():
        try:row=json.loads(line)
        except ValueError:continue
        if tool=="codex":
            if row.get("type")=="item.completed":
                item=row.get("item") or {}
                if item.get("type") in ("command_execution","file_change","mcp_tool_call"):
                    raise ValueError("FORBIDDEN_SHELL_OR_FILE_TOOL_EVENT")
                if item.get("type")=="agent_message":texts.append(item.get("text",""))
            if row.get("type")=="turn.completed":tokens=row.get("usage") or {}
        elif tool=="opencode":
            if str(row.get("type","")).startswith("tool"):
                raise ValueError("FORBIDDEN_OPENCODE_TOOL_EVENT")
            if row.get("type")=="text":texts.append((row.get("part") or {}).get("text",""))
            if row.get("type")=="step_finish":tokens=(row.get("part") or {}).get("tokens") or {}
    if not texts:raise ValueError("NO_GENERATED_SOURCE")
    text=texts[-1].strip()
    if text.startswith(chr(96)*3):
        lines=text.splitlines()
        if len(lines)>=3 and lines[-1].strip()==chr(96)*3:
            text="\n".join(lines[1:-1]).strip()
    try:result=json.loads(text)
    except ValueError:raise ValueError("EXPECTED_JSON_FILES_MAP")
    if not isinstance(result,dict):raise ValueError("LANG_RESPONSE_NOT_FILES_MAP")
    # Some CLIs wrap the source map in files, others return the exact map.
    # Accept the exact expected-key map only, never extra operation fields.
    if set(result)=={"files"} and isinstance(result["files"],dict):
        selected=result["files"]
    elif set(result)==set(expected):
        selected=result
    else:
        raise ValueError("LANG_RESPONSE_NOT_FILES_MAP")
    if set(selected)!=set(expected):
        raise ValueError("LANG_FILES_NAME_MISMATCH")
    if not all(isinstance(content,str) and 10<=len(content)<=16000
               for content in selected.values()):
        raise ValueError("LANG_SOURCE_STRING_BAD")
    return selected,tokens

def _prompt(spec):
    return ("Implement the following "+spec["language"]+" software using the provided starter files. "
        "Return ONLY valid JSON {\"files\":{\"name.ext\":\"COMPLETE SOURCE TEXT\"}}. "
        "The JSON must contain ALL source files, with exact original filenames. "
        "Use simple standalone top-level function declarations shared across files, "
        "NO import/export, no Node APIs, no third-party dependencies, no Markdown, "
        "no file operations, no shell commands. Implement the requested function "
        "correctly. Do NOT write any tests: acceptance is handled independently.\n"
        +"Goal: "+spec["goal"]+"\n"
        +"Allowed pinned UMD global dependencies: "+",".join(spec.get("dependencies",[]))+". "
        +"dayjs is global dayjs(); lodash is global _; no imports, require or npm scripts.\n"
        +"Target function: "+spec["function"]+"\n"
        +"Initial source files (replace every one completely):\n"
        +json.dumps(spec["sources"],ensure_ascii=False,sort_keys=True)+"\n"
        +"Output a single JSON object with a files map containing updated source.")

def summary(root,jobid):
    folder=jobdir(root,jobid)
    verify_journal(folder/"journal.jsonl")
    return {"jobId":jobid,"state":load(folder/"state.json"),
            "tool":load(folder/"request.json").get("editor") if (folder/"request.json").exists() else None,
            "manifest":load(folder/"manifest.json") if (folder/"manifest.json").exists() else None}

def verify(root,jobid):
    folder=jobdir(root,jobid)
    state=load(folder/"state.json")
    if state["status"]!="PASS":raise RuntimeError("LANG_JOB_NOT_ACCEPTED")
    spec=load(folder/"spec.json")
    _valid_spec(spec)
    snap=load(folder/"owner-acceptance.json")
    if snap["cases"]!=spec["acceptance"] or snap["function"]!=spec["function"]:
        raise RuntimeError("OWNER_ACCEPTANCE_CONTENT_DRIFT")
    receipt=load(folder/"manifest.json")
    if receipt["ownerAcceptanceSha"]!=sha_file(folder/"owner-acceptance.json"):
        raise RuntimeError("OWNER_ACCEPTANCE_CAS_DRIFT")
    if receipt.get("dependencyHashes",{})!=npm_umd.preflight(root,spec.get("dependencies",[])):
        raise RuntimeError("PINNED_NPM_DEPENDENCY_SHA_DRIFT")
    result=load(folder/"test.json")
    if result["status"]!="PASS" or result["independentTestCount"]!=len(spec["acceptance"]):
        raise RuntimeError("OWNER_WASI_TEST_NOT_PROVED")
    if sha_file(folder/"test.json")!=receipt["testReceiptSha"]:
        raise RuntimeError("GUEST_RECEIPT_DRIFT")
    if sha_file(folder/"original-output.json")!=receipt["originalOutputReceiptSha"]:
        raise RuntimeError("MODEL_OUTPUT_RECEIPT_DRIFT")
    reply=load(folder/"original-output.json")
    model=load(folder/"model.json")
    if sha_bytes(json_bytes(model["files"]))!=receipt["sourceProposalSha"]:
        raise RuntimeError("MODEL_SOURCE_PROPOSAL_DRIFT")
    if reply["proposalSha"]!=receipt["sourceProposalSha"]:
        raise RuntimeError("PROPOSAL_ORIGIN_DRIFT")
    verify_journal(folder/"journal.jsonl")
    return {"status":"PASS","verified":True,"jobId":jobid,
            "ownerTests":len(spec["acceptance"]),
            "language":spec["language"],
            "modelOutputReceiptSha":receipt["originalOutputReceiptSha"]}

def _accept(root,folder,spec,tool,proposed,tokens,original,output):
    # No generated source in this execution path has run on host JS/.NET.
    write_json(folder/"model.json",{"schema":1,"files":proposed,
               "editor":tool,"tokens":tokens,"createdUtc":utc()},new=True)
    owner=load(folder/"owner-acceptance.json")
    if owner["cases"]!=spec["acceptance"]:
        raise RuntimeError("OWNER_CASES_MODIFIED_DURING_MODEL_CALL")
    test=js_wasi.execute(root,spec["language"],proposed,spec["function"],
                         owner["cases"],timeout=75,dependencies=spec.get("dependencies",[]))
    write_json(folder/"test.json",test,new=True)
    event(folder/"journal.jsonl","OWNER_TEST_RECEIPT",{"testSha":sha_file(folder/"test.json"),
          "backend":test["backend"],"independentTestCount":test["independentTestCount"],
          "exitCode":test["exitCode"]})
    if test["status"]!="PASS":
        _state(folder,"FAILED",1,"owner tests failed; new repaired operation required")
        return summary(root,folder.name)
    result={
      "schema":1,"jobId":folder.name,"language":spec["language"],"editor":tool,
      "status":"CANDIDATE_ACCEPTED_NOT_INSTALLED",
      "originalOutputReceiptSha":sha_file(folder/"original-output.json"),
      "sourceProposalSha":sha_bytes(json_bytes(proposed)),
      "ownerAcceptanceSha":sha_file(folder/"owner-acceptance.json"),
      "testReceiptSha":sha_file(folder/"test.json"),
      "sourceHashes":{p:sha_bytes(s.encode("utf-8")) for p,s in proposed.items()},
      "testCount":test["testCount"],"independentTestCount":test["independentTestCount"],
      "guest":test["backend"],"dependencyHashes":test.get("dependencyHashes",{}),
      "javyExeSha":js_wasi.JAVY_EXE_SHA,
      "typescriptCompilerSha":js_wasi.TS_JS_SHA if spec["language"]=="typescript" else None,
      "originalGeneratedCodeExecutedOnHost":False,
      "acceptedUtc":utc()
    }
    write_json(folder/"manifest.json",result,new=True)
    event(folder/"journal.jsonl","ACCEPTANCE",{"manifestSha":sha_file(folder/"manifest.json"),
          "ownerAcceptanceSha":result["ownerAcceptanceSha"]})
    _state(folder,"PASS",1,"verified source-only candidate, no model replay")
    return summary(root,folder.name)

def run(root,jobid,tool):
    root=engine.init(root)
    folder=jobdir(root,jobid)
    state=load(folder/"state.json")
    if state["status"]=="PASS":return {"status":"ALREADY_PASS_NO_REPLAY","verify":verify(root,jobid)}
    if state["status"] not in ("PENDING","STOPPED"):
        raise RuntimeError("LANG_JOB_UNKNOWN_FAILED_OR_RUNNING_NO_REPLAY")
    if load(folder/"control.json")["command"]!="RUN":
        _state(folder,"STOPPED",0,"resume from original control boundary")
        return summary(root,jobid)
    if tool not in ("codex","opencode"):raise ValueError("LANG_EDITOR_NOT_SUPPORTED")
    spec=load(folder/"spec.json")
    _valid_spec(spec)
    js_wasi.preflight(root,spec["language"])
    npm_umd.preflight(root,spec.get("dependencies",[]))
    if (folder/"request.json").exists() or (folder/"original-output.json").exists():
        raise RuntimeError("LANG_ORIGINAL_CALL_EXISTS_NO_REPLAY")
    cfg=engine.settings(root)
    if cfg["provider"]!="llama_cpp" or sha_file(root/cfg["llama_cpp_model_path"])!=cfg["llama_cpp_model_sha256"]:
        raise RuntimeError("LANG_LOCAL_MODEL_IDENTITY_NOT_PROVEN")
    request={"schema":1,"editor":tool,"jobId":jobid,"goalSha":sha_bytes(spec["goal"].encode()),
             "specSha":sha_file(folder/"spec.json"),"ownerAcceptanceSha":sha_file(folder/"owner-acceptance.json"),
             "modelSha":cfg["llama_cpp_model_sha256"],"prompt":_prompt(spec)}
    write_json(folder/"request.json",request,new=True)
    command=source_editors._command(root,tool,request["prompt"],folder/"final.txt")
    _state(folder,"MODEL_PENDING",1,"editor generating sources")
    event(folder/"journal.jsonl","MODEL_INTENT",{"operationId":jobid+"."+tool+".1",
          "requestSha":sha_file(folder/"request.json"),"modelSha":request["modelSha"]})
    status=local_runtime.server_info(root)
    if status["state"]=="EXITED":
        local_runtime.stop(root);status=local_runtime.server_info(root)
    if status["state"] not in ("NOT_STARTED","READY"):
        raise RuntimeError("LANG_SERVER_STATUS_UNKNOWN")
    started=status["state"]=="NOT_STARTED"
    if started and local_runtime.start(root)["state"]!="READY":
        raise RuntimeError("LANG_SERVER_NOT_READY")
    began=time.monotonic()
    raw=None
    try:
        done=subprocess.run(command,cwd=str(root/"LAB-ADAPTERS"),
                            stdin=subprocess.DEVNULL,env=source_editors._env(root),
                            capture_output=True,timeout=170)
        raw=done.stdout
        evidence={"schema":1,"tool":tool,"exitCode":done.returncode,
                  "stdoutSha256":sha_bytes(raw),"stderrSha256":sha_bytes(done.stderr),
                  "durationMs":int((time.monotonic()-began)*1000),
                  "stderrTail":done.stderr.decode("utf-8","replace")[-1000:],
                  "stdout":raw.decode("utf-8","replace")[-95000:]}
    except subprocess.TimeoutExpired:
        _state(folder,"UNKNOWN",1,"timed out: reconcile child before any retry")
        return summary(root,jobid)
    finally:
        if started:
            local_runtime.stop(root)
    write_json(folder/"original-output.json",evidence,new=True)
    if done.returncode:
        _state(folder,"FAILED",1,"tool failed; new operation after review")
        return summary(root,jobid)
    try:
        proposed,tokens=_parse(tool,raw,list(spec["sources"]))
    except Exception as error:
        event(folder/"journal.jsonl","MODEL_OUTPUT_INVALID",{"type":type(error).__name__,
              "detail":str(error)[:240],"stdoutSha":evidence["stdoutSha256"]})
        _state(folder,"FAILED",1,"bad model format; original stdout retained")
        return summary(root,jobid)
    evidence["proposalSha"]=sha_bytes(json_bytes(proposed))
    # Re-read, CAS-protect model and owner input before admission.
    old=sha_file(folder/"original-output.json")
    from .storage import transition
    transition(folder/"original-output.json",evidence,folder/"history")
    if sha_file(folder/"spec.json")!=request["specSha"] or sha_file(folder/"owner-acceptance.json")!=request["ownerAcceptanceSha"]:
        _state(folder,"UNKNOWN",1,"owner or job spec changed during inference")
        return summary(root,jobid)
    event(folder/"journal.jsonl","MODEL_READBACK",{"originalOutputSha":sha_file(folder/"original-output.json"),
          "proposalSha":evidence["proposalSha"],"sourceCount":len(proposed)})
    _state(folder,"SOURCE_READY",1,"test WASI with owner-frozen acceptance")
    try:
        return _accept(root,folder,spec,tool,proposed,tokens,folder/"original-output.json",raw)
    except Exception as error:
        _state(folder,"UNKNOWN",1,"isolation uncertainty, reconcile receipts before replay")
        raise RuntimeError("LANG_ISOLATION_OR_RECEIPT_UNKNOWN:"+type(error).__name__+":"+str(error)[:180]) from error
