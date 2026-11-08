"""Native Codex/OpenCode proposals; original owner acceptance runs in isolated WASI.

No original MMC7 privileges, no generated source applied by editor, no shell
tool calls enabled. An UNKNOWN operation is never automatically replayed.
"""
import ast
import json
import os
from pathlib import Path
import re
import subprocess
import time
from . import advisors, engine, housekeeping, local_runtime
from .storage import atomic_snapshot, event, json_bytes, load, safe_source, sha_bytes, sha_file, utc, write, write_json

SMOKE=("import unittest\n"
       "class FactoryImport(unittest.TestCase):\n"
       "    def test_import(self):\n"
       "        import importlib\n"
       "        self.assertIsNotNone(importlib.import_module('TARGET_MODULE'))\n")

def parse_source(tool,raw):
    messages=[]
    usage={}
    for line in raw.decode("utf-8","replace").splitlines():
        try:row=json.loads(line)
        except ValueError:continue
        if tool=="codex":
            if row.get("type")=="item.completed":
                item=row.get("item") or {}
                if item.get("type") in ("command_execution","file_change","mcp_tool_call"):
                    raise ValueError("FORBIDDEN_CODEX_TOOL_EVENT")
                if item.get("type")=="agent_message":messages.append(item.get("text",""))
            if row.get("type")=="turn.completed":usage=row.get("usage") or {}
        else:
            if str(row.get("type","")).startswith("tool"):raise ValueError("FORBIDDEN_OPENCODE_TOOL_EVENT")
            if row.get("type")=="text":messages.append((row.get("part") or {}).get("text",""))
            if row.get("type")=="step_finish":usage=(row.get("part") or {}).get("tokens") or {}
    if not messages:raise ValueError("NO_MODEL_SOURCE_TEXT")
    text=messages[-1].strip()
    if len(text)>30000:raise ValueError("MODEL_RESPONSE_TOO_LONG")
    # Codex and OpenCode often wrap valid JSON in a Markdown fence.
    # Strip the wrapper before JSON parsing without altering source bytes.
    if text.startswith(chr(96)*3):
        lines=text.splitlines()
        if len(lines)>2 and lines[-1].strip()==chr(96)*3:
            text="\n".join(lines[1:-1]).strip()
    source=None
    try:
        data=json.loads(text)
        if isinstance(data,dict) and set(data)=={"source"} and isinstance(data["source"],str):
            source=data["source"]
    except ValueError:pass
    if source is None and text.startswith(chr(96)*3):
        lines=text.splitlines()
        if len(lines)>2 and lines[-1].strip()==chr(96)*3 and lines[0].lower().startswith((chr(96)*3+"python",chr(96)*3+"py",chr(96)*3)):
            source="\n".join(lines[1:-1])+"\n"
    if source is None and text.startswith(("def ","from ","import ")):
        source=text+"\n"
    if not isinstance(source,str) or len(source)>15000:raise ValueError("INVALID_WHOLE_SOURCE_FORMAT")
    tree=ast.parse(source)
    if not any(isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)) for n in tree.body):
        raise ValueError("NO_SOURCE_FUNCTION")
    return source,usage

def _command(root,tool,prompt,reply):
    path=advisors.binaries(root)[tool]
    expected=advisors.CODEX_SHA if tool=="codex" else advisors.OPEN_SHA
    if not path.is_file() or sha_file(path)!=expected:raise RuntimeError("EDITOR_BINARY_SHA_DRIFT")
    if tool=="codex":
        config=root/"VENDOR/editors/codex-home/config.toml"
        if sha_file(config)!=sha_file(root/"configs/codex-local.toml"):
            raise RuntimeError("CODEX_CONFIG_CAS_DRIFT")
        return [r"C:\Program Files\nodejs\node.exe",str(path),"exec",
                "--ephemeral","--sandbox","read-only","--disable","shell_tool",
                "--disable","unified_exec","--skip-git-repo-check","--json",
                "-C",str(root/"LAB-ADAPTERS"),"-o",str(reply),prompt]
    config=root/"VENDOR/editors/opencode-config.json"
    cfg=load(config)
    if sha_file(config)!=sha_file(root/"configs/opencode-local.json"):
        raise RuntimeError("OPENCODE_CONFIG_CAS_DRIFT")
    if cfg["permission"].get("*")!="deny" or cfg["agent"]["af-proposal"]["permission"].get("*")!="deny":
        raise RuntimeError("OPENCODE_TOOL_POLICY_NOT_DENIED")
    return [str(path),"run","--pure","--agent","af-proposal",
            "--model","aflocal/af-qwen-coder-1.5b","--format","json",prompt]

def _env(root):
    env={k:v for k,v in os.environ.items() if not k.endswith(("_API_KEY","_TOKEN"))}
    home=root/"VENDOR/editors/opencode-home"
    for sub in ("data","cache","config"):(home/sub).mkdir(parents=True,exist_ok=True)
    env.update(CODEX_HOME=str(root/"VENDOR/editors/codex-home"),AF_DUMMY_LOCAL_KEY="no-cloud-key",
               OPENCODE_CONFIG=str(root/"VENDOR/editors/opencode-config.json"),
               OPENCODE_DISABLE_DEFAULT_PLUGINS="true",OPENCODE_DISABLE_MODELS_FETCH="true",
               OPENCODE_DISABLE_LSP_DOWNLOAD="true",OPENCODE_DISABLE_SHARE="true",
               XDG_DATA_HOME=str(home/"data"),XDG_CACHE_HOME=str(home/"cache"),
               XDG_CONFIG_HOME=str(home/"config"),PYTHONDONTWRITEBYTECODE="1",
               DOTNET_ADD_GLOBAL_TOOLS_TO_PATH="false",NO_COLOR="1")
    return env

def run(root,tool,jobid,source_name,seed_rel):
    root=engine.init(root)
    folder=engine.jobdir(root,jobid)
    state=load(folder/"state.json")
    if state["status"] in ("PASS","PASS_FIXTURE"):
        return {"status":"ALREADY_PASSED_NO_REPLAY","jobId":jobid}
    if state["status"]!="PENDING":raise RuntimeError("NEW_PENDING_JOB_REQUIRED:"+state["status"])
    engine.gate(folder)
    if tool not in ("codex","opencode"):raise ValueError("UNSUPPORTED_NATIVE_EDITOR")
    cfg=engine.settings(root)
    spec=load(folder/"spec.json")
    if not spec.get("acceptance"):raise RuntimeError("OWNER_ACCEPTANCE_REQUIRED")
    if cfg["provider"]!="llama_cpp":raise RuntimeError("LOCAL_PINNED_MODEL_REQUIRED")
    if not re.fullmatch(r"[a-z][a-z0-9_]{0,42}\.py",source_name):raise ValueError("SOURCE_NAME_UNSAFE")
    if not re.fullmatch(r"examples/[a-z0-9_]{1,55}\.py",seed_rel):raise ValueError("SEED_UNSAFE")
    if source_name not in spec["goal"]:raise ValueError("GOAL_MUST_NAME_TARGET")
    seed=root/seed_rel
    if not seed.is_file() or seed.is_symlink() or seed.stat().st_size>10000:
        raise RuntimeError("SOURCE_SEED_UNSAFE")
    engine.runner_preflight(root,cfg)
    if sha_file(root/cfg["llama_cpp_model_path"])!=cfg["llama_cpp_model_sha256"]:
        raise RuntimeError("MODEL_SHA_MISMATCH")
    seed_sha=sha_file(seed)
    initial=seed.read_text("utf-8")
    prompt=("Return ONLY a JSON object with key source containing COMPLETE corrected Python file "
            "as a string with escaped newlines. No prose, no markdown, no commands, no tools, "
            "no tests, no other files. Use Python standard library. File: "+source_name+
            "\nCurrent source:\n"+initial+"\nGoal: "+spec["goal"][:700]+
            "\nJSON shape: {\"source\":\"def f(x):\\n    return x\\n\"}")
    attempt=folder/"attempt-01"
    if attempt.exists():raise RuntimeError("ATTEMPT_ALREADY_EXISTS")
    attempt.mkdir()
    copied=attempt/source_name
    write(copied,seed.read_bytes(),new=True)
    if sha_file(copied)!=seed_sha:raise RuntimeError("PREIMAGE_DRIFT")
    request={"schema":1,"tool":tool,"prompt":prompt,"promptSha":sha_bytes(prompt.encode()),
             "seedSha":seed_sha,"modelSha":cfg["llama_cpp_model_sha256"],"target":source_name}
    write_json(attempt/"EDITOR-REQUEST.json",request,new=True)
    cmd=_command(root,tool,prompt,attempt/"FINAL.txt")
    engine.set_state(folder,"MODEL_PENDING",1,"native editor call in progress; reconcile before replay")
    event(folder/"journal.jsonl","CODER_INTENT",{"operationId":jobid+"."+tool+".1",
          "requestSha":sha_file(attempt/"EDITOR-REQUEST.json"),
          "binarySha":sha_file(advisors.binaries(root)[tool]),"editor":tool})
    live=local_runtime.server_info(root)
    if live["state"]=="EXITED":
        local_runtime.stop(root)
        live=local_runtime.server_info(root)
    if live["state"] not in ("READY","NOT_STARTED"):raise RuntimeError("SERVER_STATE_UNCERTAIN")
    started=False
    if live["state"]=="NOT_STARTED":
        if local_runtime.start(root)["state"]!="READY":raise RuntimeError("MODEL_NOT_READY")
        started=True
    evidence={"schema":1,"atUtc":utc(),"tool":tool,"seedSha":seed_sha,
              "requestSha":sha_file(attempt/"EDITOR-REQUEST.json")}
    begin=time.monotonic()
    try:
        try:
            response=subprocess.run(cmd,cwd=str(root/"LAB-ADAPTERS"),env=_env(root),
                                    stdin=subprocess.DEVNULL,capture_output=True,timeout=155)
            evidence.update(returnCode=response.returncode,elapsedMs=int((time.monotonic()-begin)*1000),
                            stdoutSha=sha_bytes(response.stdout),stderrSha=sha_bytes(response.stderr),
                            stderrTail=response.stderr.decode("utf-8","replace")[-1200:])
            write(attempt/"EDITOR-STDOUT.bin",response.stdout[:1000000],new=True)
            write(attempt/"EDITOR-STDERR.bin",response.stderr[:150000],new=True)
            if response.returncode:
                evidence["status"]="FAILED_EDITOR_EXIT"
                engine.set_state(folder,"FAILED",1,"new operation after tool error review")
            else:
                try:code,usage=parse_source(tool,response.stdout)
                except (ValueError,SyntaxError) as error:
                    evidence.update(status="FAILED_INVALID_SOURCE",
                                    parseError=type(error).__name__+":"+str(error)[:250])
                    engine.set_state(folder,"FAILED",1,"review malformed output; new job only")
                else:
                    if sha_file(copied)!=seed_sha or sha_file(seed)!=seed_sha:
                        raise RuntimeError("SOURCE_PREIMAGE_CHANGED")
                    evidence.update(status="PROPOSED_UNTESTED",proposalSha=sha_bytes(code.encode()))
                    code_dir=attempt/"code"
                    code_dir.mkdir()
                    payload={"files":{source_name:code,
                             "test_factory_import.py":SMOKE.replace("TARGET_MODULE",source_name[:-3])}}
                    files=engine.validate_payload(code_dir,payload,cfg["max_source_bytes"])
                    for name,content in files.items():
                        write(safe_source(code_dir,name),content.encode(),new=True)
                    snap=atomic_snapshot(code_dir)
                    if snap[source_name]!=evidence["proposalSha"]:
                        raise RuntimeError("PROPOSAL_SHA_DRIFT")
                    usage_record={"provider":tool,"promptTokens":usage.get("input_tokens",usage.get("input",0)),
                                  "completionTokens":usage.get("output_tokens",usage.get("output",0)),
                                  "elapsedMs":evidence["elapsedMs"],"seedSha":seed_sha,
                                  "promptSha":request["promptSha"]}
                    write_json(attempt/"model.json",{"payload":payload,"usage":usage_record,
                                   "modelDigest":"sha256:"+cfg["llama_cpp_model_sha256"],
                                   "cached":False},new=True)
                    event(folder/"journal.jsonl","CODER_READBACK",{"attempt":1,
                          "responseSha":sha_file(attempt/"model.json"),"editor":tool})
                    event(folder/"journal.jsonl","VERIFIER_SOURCE",{"attempt":1,
                          "sha":sha_bytes(json_bytes(snap))})
                    engine.set_state(folder,"DRAFT_READY_UNTESTED",1,"run pinned WASI acceptance")
        except subprocess.TimeoutExpired:
            evidence["status"]="UNKNOWN_TIMEOUT"
            engine.set_state(folder,"UNKNOWN",1,"reconcile child process before any retry")
        except Exception as error:
            evidence.update(status="UNKNOWN_EXCEPTION",errorType=type(error).__name__,
                            detail=str(error)[:250])
            engine.set_state(folder,"UNKNOWN",1,"inspect receipt/journal before any retry")
    finally:
        if started:
            stopped=local_runtime.stop(root)
            evidence["ownedModelStop"]=stopped["state"]
            if stopped["state"] not in ("STOPPED","STOPPED_RECONCILED"):
                evidence["status"]="UNKNOWN_MODEL_STOP_NOT_VERIFIED"
    write_json(attempt/"EDITOR-EXECUTION.json",evidence,new=True)
    if load(folder/"state.json")["status"]=="DRAFT_READY_UNTESTED" and evidence["status"]=="PROPOSED_UNTESTED":
        summary=engine.run(root,jobid)
    else:
        summary=engine.summary(root,jobid)
    try:
        cleanup=housekeeping.maintain(root,apply=True)
        summary["housekeeping"]={"changed":cleanup["changed"],"affected":cleanup["filesAffected"]}
    except Exception as error:
        summary["housekeeping"]={"status":"ERROR","detail":str(error)[:120]}
    return summary


def reconcile_saved(root,jobid):
    """Admission-only recovery of a VALID source already returned by a CLI.

    Does not launch model, CLI, or replay the original effect; requires a
    deterministic parser failure receipt with complete stdout and original SHA.
    """
    root=engine.init(root)
    folder=engine.jobdir(root,jobid)
    engine.gate(folder)
    state=load(folder/"state.json")
    if state["status"]=="PASS":return {"status":"ALREADY_PASS_NO_REPLAY"}
    if state["status"]!="FAILED":
        raise RuntimeError("ONLY_DETERMINISTIC_FAILED_PARSER_RECEIPT_RECONCILABLE")
    attempt=folder/"attempt-01"
    receipt=load(attempt/"EDITOR-EXECUTION.json")
    request=load(attempt/"EDITOR-REQUEST.json")
    if receipt.get("status")!="FAILED_INVALID_SOURCE" or receipt.get("returnCode")!=0:
        raise RuntimeError("EDITOR_NOT_A_DETERMINISTIC_PARSER_FAILURE")
    if (attempt/"model.json").exists() or (attempt/"code").exists() or (attempt/"RECONCILED-SOURCE.json").exists():
        raise RuntimeError("RECONCILIATION_EFFECT_EXISTS_NO_REPLAY")
    stdout=(attempt/"EDITOR-STDOUT.bin").read_bytes()
    if sha_bytes(stdout)!=receipt["stdoutSha"]:
        raise RuntimeError("ORIGINAL_STDOUT_INCOMPLETE_OR_HASH_DRIFT")
    if receipt["requestSha"]!=sha_file(attempt/"EDITOR-REQUEST.json"):
        raise RuntimeError("REQUEST_RECEIPT_SHA_DRIFT")
    cfg=engine.settings(root)
    if cfg["llama_cpp_model_sha256"]!=request["modelSha"]:
        raise RuntimeError("MODEL_SHA_CHANGED_FROM_ORIGINAL")
    source=request["target"]
    if sha_file(attempt/source)!=request["seedSha"]:
        raise RuntimeError("SOURCE_PREIMAGE_CHANGED")
    tool=receipt["tool"]
    code,usage=parse_source(tool,stdout)
    code_dir=attempt/"code"
    code_dir.mkdir()
    payload={"files":{source:code,
                       "test_factory_import.py":SMOKE.replace("TARGET_MODULE",source[:-3])}}
    validated=engine.validate_payload(code_dir,payload,cfg["max_source_bytes"])
    for name,content in validated.items():
        write(safe_source(code_dir,name),content.encode(),new=True)
    snapshot=atomic_snapshot(code_dir)
    digest=sha_bytes(code.encode())
    if snapshot[source]!=digest:raise RuntimeError("ADMITTED_SHA_DRIFT")
    recovery={"schema":1,"atUtc":utc(),"source":"ORIGINAL_CLI_STDOUT_NO_MODEL_REPLAY",
              "tool":tool,"attempt":1,"originalFailureReceiptSha":sha_file(attempt/"EDITOR-EXECUTION.json"),
              "originalStdoutSha":receipt["stdoutSha"],
              "originalPromptSha":request["promptSha"],"proposedSha":digest,
              "modelCallsAdded":0,"reason":"valid JSON fenced in markdown, previous parser rejected"}
    write_json(attempt/"RECONCILED-SOURCE.json",recovery,new=True)
    write_json(attempt/"model.json",{
        "payload":payload,"cached":True,
        "modelDigest":"sha256:"+cfg["llama_cpp_model_sha256"],
        "usage":{"provider":tool,"promptTokens":usage.get("input_tokens",usage.get("input",0)),
                 "completionTokens":usage.get("output_tokens",usage.get("output",0)),
                 "elapsedMs":receipt["elapsedMs"],"reconciledFromOriginal":True,
                 "originalStdoutSha":receipt["stdoutSha"]}
    },new=True)
    event(folder/"journal.jsonl","MODEL_RESPONSE_RECONCILED",
          {"originalReceiptSha":sha_file(attempt/"EDITOR-EXECUTION.json"),
           "newReceiptSha":sha_file(attempt/"RECONCILED-SOURCE.json"),"modelCallsAdded":0})
    event(folder/"journal.jsonl","CODER_READBACK",{"attempt":1,
          "responseSha":sha_file(attempt/"model.json"),"editor":tool,"reconciled":True})
    event(folder/"journal.jsonl","VERIFIER_SOURCE",{"attempt":1,
          "sha":sha_bytes(json_bytes(snapshot))})
    engine.set_state(folder,"DRAFT_READY_UNTESTED",1,
                     "resume original model proposal as isolated acceptance only")
    return engine.run(root,jobid)
