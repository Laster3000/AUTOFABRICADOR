"""Codex/OpenCode local read-only advisors; never edit source or call shell tools."""
import json,os,subprocess,time
from pathlib import Path
from . import engine,local_runtime
from .storage import load,sha_file,sha_bytes,utc,write_json

CODEX_SHA="e14fc83739c13c1074b12bd1acce4010c893c7f6fbfc1593b4a31d74cabb57af"
OPEN_SHA="d7b473388cb62555970e400ce54cdfb6d6573608beea6f8fdf382cd1a698a3fa"

def binaries(root):
    return {"codex":root/"VENDOR/editors/node/node_modules/@openai/codex/bin/codex.js",
            "opencode":root/"VENDOR/editors/node/node_modules/opencode-windows-x64/bin/opencode.exe"}

def registry(root):
    root=Path(root).resolve()
    historical=root/"CONTINUIDAD/R032"
    accepted={"aider":[],"codex":[],"opencode":[]}
    for folder in sorted((root/"work").glob("AF-*")):
        receipt=folder/"manifest.json"
        state=folder/"state.json"
        if not receipt.is_file() or not state.is_file():
            continue
        if load(state).get("status")!="PASS":
            continue
        manifest=load(receipt)
        if manifest.get("independentTestCount",0)<1:
            continue
        data=folder/f"attempt-{manifest['attempt']:02d}"/"model.json"
        if not data.is_file():
            continue
        name=load(data).get("usage",{}).get("provider")
        if name not in accepted:
            continue
        try:
            if engine.verify_job(root,folder.name).get("verified"):
                accepted[name].append(folder.name)
        except (ValueError,RuntimeError,OSError,KeyError):
            continue
    result={}
    for tool,sha,filename in (("codex",CODEX_SHA,"CODEX-PROBE-12K-RESULT.json"),
                              ("opencode",OPEN_SHA,"OPENCODE-PROBE-RESULT.json")):
        path=binaries(root)[tool]
        good=path.is_file() and sha_file(path)==sha
        proof=historical/filename
        info=load(proof) if proof.is_file() else {}
        result[tool]={"version":"0.167.0" if tool=="codex" else "1.19.5",
                      "installedShaVerified":good,
                      "localInferenceReadOnlyVerified":bool(good and info.get("returnCode")==0
                                                           and "READY" in str(info.get("stdoutTail",""))),
                      "sourceOwnerAcceptanceVerified":len(accepted[tool])>0,
                      "sourceAcceptedJobIds":accepted[tool],
                      "role":"LOCAL_READONLY_ADVICE_AND_SOURCE_PROPOSAL_WITH_INDEPENDENT_WASI_ACCEPTANCE"}
    result["aider"]={"version":"0.86.2",
                      "sourceOwnerAcceptanceVerified":len(accepted["aider"])>0,
                      "sourceAcceptedJobIds":accepted["aider"],
                      "role":"SINGLE_SOURCE_PROPOSAL_PLUS_WASI_TEST"}
    completed=[]
    for file in (root/"missions").glob("AM-*/state.json"):
        st=load(file)
        if st.get("status")=="PASS" and st.get("acceptedManifestSha"):
            completed.append(file.parent.name)
    return {"tools":result,"MMC7OriginalAuthorityImported":False,
            "boundedMultiRoleMissionsAccepted":completed,
            "wholeMultiagentE2E":False}

def parse(tool,stdout):
    parts=[]
    for line in stdout.decode("utf-8","replace").splitlines():
        try:row=json.loads(line)
        except ValueError:continue
        if tool=="codex" and row.get("type")=="item.completed":
            item=row.get("item") or {}
            if item.get("type") in ("command_execution","file_change","mcp_tool_call"):
                raise RuntimeError("CODEX_TOOL_EFFECT_NOT_ALLOWED")
            if item.get("type")=="agent_message":parts.append(item.get("text",""))
        elif tool=="opencode":
            if str(row.get("type","")).startswith("tool"):
                raise RuntimeError("OPENCODE_TOOL_EFFECT_NOT_ALLOWED")
            if row.get("type")=="text":parts.append((row.get("part") or {}).get("text",""))
    if not parts:raise RuntimeError("NO_ADVICE_TEXT")
    text=parts[-1].strip()
    if text.startswith(chr(96)*3):
        text="\n".join(text.splitlines()[1:-1]).strip()
    try:hint=json.loads(text).get("suggestion")
    except ValueError:raise RuntimeError("ADVICE_NOT_JSON")
    if not isinstance(hint,str) or not 3<=len(hint)<=1500:
        raise RuntimeError("INVALID_ADVICE")
    return hint

def advise(root,tool,jobid):
    root=engine.init(root)
    job=engine.jobdir(root,jobid)
    engine.gate(job)
    if load(job/"state.json")["status"] in ("PASS","PASS_FIXTURE"):
        return {"status":"ALREADY_PASSED_DO_NOT_SPEND_TOKENS"}
    if tool not in ("codex","opencode"):raise ValueError("NOT_A_SUPPORTED_ADVISOR")
    cfg=engine.settings(root)
    if cfg["provider"]!="llama_cpp":raise RuntimeError("LOCAL_MODEL_REQUIRED")
    prompt="Return JSON object with one string key suggestion: one concise way to repair the following Python task. No commands/tools. "+load(job/"spec.json")["goal"][:900]
    key=sha_bytes(json.dumps([tool,prompt,cfg["llama_cpp_model_sha256"]]).encode())
    storage=job/"advice";storage.mkdir(exist_ok=True)
    receipt=storage/(tool+"-"+key+".json")
    if receipt.exists():return {"status":"CACHE_REUSE_NO_MODEL_CALL","receipt":load(receipt)}
    if local_runtime.server_info(root)["state"]!="READY":
        raise RuntimeError("LOCAL_INFERENCE_NOT_READY")
    binary=binaries(root)[tool]
    if sha_file(binary)!=({"codex":CODEX_SHA,"opencode":OPEN_SHA}[tool]):
        raise RuntimeError("ADVISOR_BINARY_SHA_DRIFT")
    if tool=="codex":
        cmd=[r"C:\Program Files\nodejs\node.exe",str(binary),"exec","--ephemeral",
             "--sandbox","read-only","--disable","shell_tool","--disable","unified_exec",
             "--skip-git-repo-check","--json","-C",str(root/"LAB-ADAPTERS"),
             "-o",str(storage/(key+".txt")),prompt]
    else:
        profile=load(root/"VENDOR/editors/opencode-config.json")
        if profile["permission"].get("*")!="deny" or profile["agent"]["af-proposal"]["permission"].get("*")!="deny":
            raise RuntimeError("ADVISOR_TOOLS_NOT_DENIED")
        cmd=[str(binary),"run","--pure","--agent","af-proposal",
             "--model","aflocal/af-qwen-coder-1.5b","--format","json",prompt]
    home=root/"VENDOR/editors/opencode-home"
    env={k:v for k,v in os.environ.items() if not k.endswith(("_API_KEY","_TOKEN"))}
    env.update(CODEX_HOME=str(root/"VENDOR/editors/codex-home"),
               AF_DUMMY_LOCAL_KEY="dummy-local",
               OPENCODE_CONFIG=str(root/"VENDOR/editors/opencode-config.json"),
               OPENCODE_DISABLE_DEFAULT_PLUGINS="true",
               OPENCODE_DISABLE_MODELS_FETCH="true",
               OPENCODE_DISABLE_SHARE="true",
               XDG_DATA_HOME=str(home/"data"),XDG_CACHE_HOME=str(home/"cache"),
               XDG_CONFIG_HOME=str(home/"config"))
    start=time.monotonic()
    try:
        done=subprocess.run(cmd,cwd=str(root/"LAB-ADAPTERS"),stdin=subprocess.DEVNULL,
                            env=env,capture_output=True,timeout=140)
        hint=parse(tool,done.stdout) if done.returncode==0 else None
        result={"status":"ADVICE_ONLY_NOT_APPLIED" if hint else "ADVISOR_FAILED",
                "suggestion":hint,"exitCode":done.returncode,
                "stdoutSha256":sha_bytes(done.stdout),"stderrSha256":sha_bytes(done.stderr)}
    except Exception as error:
        result={"status":"UNKNOWN_NO_AUTOMATIC_REPLAY","exception":type(error).__name__,
                "error":str(error)[:350]}
    result.update(tool=tool,jobId=jobid,atUtc=utc(),
                  elapsedMs=int((time.monotonic()-start)*1000),
                  jobStateUnchanged=load(job/"state.json")["status"])
    write_json(receipt,result,new=True)
    return result
