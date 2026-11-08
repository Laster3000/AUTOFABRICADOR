# coding: utf-8
"""AF R71: bounded local AI Tk/SQLite GUI jobs on ORIGINAL supervisor.
No general native-software claim. Source is never executed on Windows Host;
the first-party frozen acceptance runs only in a disposable Windows Sandbox.
"""
from __future__ import annotations
import ast, hashlib, json, os, re, shutil, subprocess, sys, time, uuid, zipfile
from pathlib import Path
from xml.sax.saxutils import escape
from . import engine, supervisor, direct_agent, local_cuda7b, local_cuda9b, local_runtime
from .storage import load, sha_file, sha_bytes, utc, write_json, transition, event, verify_journal

PROFILE="AF.GUI.INVENTORY.SQLITE.V1"
REQUIRED=["INVENTORY","SQLITE","TKINTER","CRUD","STOCK","SEARCH","PERSISTENCE"]
ID=re.compile(r"GI-[a-f0-9]{16}\Z")
MODEL_ROOT=Path(r"C:\AF-PORTABLE")
OWNER_TEST="gui_r71_owner.py"
GUEST_RUN="gui_r71_guest.ps1"
EXPECTED_CASES=13
SUCCESS="PASS_SCOPED_ORIGINAL_GUI_GUEST_13"
STOPPED="STOPPED_SAFE_BOUNDARY"

def folder(root,jid):
    if not isinstance(jid,str) or not ID.fullmatch(jid):raise ValueError("GUI_BAD_ID")
    p=Path(root).resolve()/"guijobs"/jid
    if not p.is_dir():raise FileNotFoundError("GUI_JOB_MISSING")
    return p

def _origin(root):
    root=Path(root).resolve()
    qa=root/"qa"/OWNER_TEST
    runner=root/"qa"/GUEST_RUN
    runtime=root/"VENDOR"/"python312-tk-r71"
    for p in (qa,runner,runtime/"python.exe",runtime/"Lib"/"sqlite3"/"__init__.py"):
        if not p.is_file() or p.is_symlink():raise RuntimeError("GUI_TRUSTED_COMPONENT_MISSING:"+str(p))
    expected=load(root/"qa"/"gui_r71_pins.json")
    for p,key in ((qa,"qaSha"),(runner,"guestRunnerSha"),(runtime/"python.exe","runtimeExeSha")):
        if sha_file(p)!=expected[key]:raise RuntimeError("GUI_FIRST_PARTY_PIN_DRIFT:"+key)
    return {"qa":qa,"runner":runner,"runtime":runtime,"pins":expected}

def _validate_spec(s):
    if not isinstance(s,dict) or set(s)!={"schema","profile","goal","features"}:
        raise ValueError("GUI_CONTRACT_KEYS")
    if s["schema"]!=1 or s["profile"]!=PROFILE or s["features"]!=REQUIRED:
        raise ValueError("GUI_UNSUPPORTED_SCOPE_FROZEN_ORACLE_REQUIRED")
    if not isinstance(s["goal"],str) or not 40<=len(s["goal"])<=500:
        raise ValueError("GUI_GOAL_LENGTH")
    lower=s["goal"].casefold()
    if not any(x in lower for x in ("inventario","inventory")) or not any(x in lower for x in ("sqlite","tkinter")):
        raise ValueError("GUI_GOAL_OUTSIDE_INVENTORY_PROFILE")
    # Negating internet access is an offline requirement, NOT a network request.
    # Keep other risky/protected requests strictly denied.
    safe=lower.replace("sin internet","").replace("without internet","").replace("sin conexión a internet","")
    if any(x in safe for x in ("internet","servicio de windows","privilegio","administrador","telemetria","mmc7","f:\\")):
        raise ValueError("GUI_GOAL_UNSUPPORTED_PROTECTED_SCOPE")
    return True

def preview(root,path):
    root=Path(root).resolve()
    inp=Path(path).resolve()
    if not inp.is_file() or inp.is_symlink() or not inp.is_relative_to(root/"ENTRADAS"):
        raise ValueError("GUI_INPUT_MUST_BE_IN_ENTRADAS")
    spec=load(inp);_validate_spec(spec)
    pins=_origin(root)
    return {"status":"SUPPORTED_BOUNDED_INVENTORY_ONLY","specSha":sha_file(inp),
            "frozenOwnerQaSha":sha_file(pins["qa"]),"features":REQUIRED,
            "nativeExeGuaranteed":False,"generalAutonomyGuaranteed":False}

def _change(d,new,why):
    previous=load(d/"state.json")
    transition(d/"state.json",{"schema":1,"status":new,"atUtc":utc(),
       "previousSha":sha_file(d/"state.json"),"detail":str(why)[:220]},d/"history")
    event(d/"journal.jsonl","GUI_STATE",{"from":previous["status"],"to":new,
                                     "receiptSha":sha_file(d/"state.json")})

def create(root,path):
    root=engine.init(root)
    info=preview(root,path)
    inp=Path(path).resolve()
    for prior in (root/"guijobs").glob("GI-*/owner.json"):
        v=load(prior)
        if v["inputSha"]==sha_file(inp):
            return {"status":"ORIGINAL_INTENT_ALREADY_RECORDED_NO_REPLAY",
                    "jobId":v["jobId"],"original":status(root,v["jobId"])}
    jid="GI-"+uuid.uuid4().hex[:16]
    d=root/"guijobs"/jid
    d.mkdir(parents=True,exist_ok=False)
    (d/"history").mkdir()
    (d/"attempts").mkdir()
    write_json(d/"spec.json",load(inp),new=True)
    owner={"schema":1,"jobId":jid,"objectiveId":"autofabricador-independent-reusable-local-ai-factory-20261107",
        "operationId":jid+".ORIGINAL.GUI.ONCE","inputSha":sha_file(inp),
        "specSha":sha_file(d/"spec.json"),"ownerQaSha":info["frozenOwnerQaSha"],
        "providerOriginalSha":sha_file(MODEL_ROOT/"autofab"/"local_cuda9b.py"),
        "frozenCaseCount":EXPECTED_CASES,"profile":PROFILE,"atUtc":utc(),
        "modelCannotWriteOwnerTests":True,"modelCodeRunsOnWindowsHost":False,
        "sandboxGuestOutputUntrusted":True,"noWindowsAutostart":True}
    write_json(d/"owner.json",owner,new=True)
    write_json(d/"control.json",{"schema":1,"command":"RUN","atUtc":utc()},new=True)
    write_json(d/"state.json",{"schema":1,"status":"PENDING","atUtc":utc()},new=True)
    event(d/"journal.jsonl","GUI_OWNER_FROZEN",{"ownerSha":sha_file(d/"owner.json"),
          "originalTestSha":owner["ownerQaSha"],"specSha":owner["specSha"]})
    return {"status":"PENDING","jobId":jid,"ownerSHA":sha_file(d/"owner.json")}

def status(root,jid):
    d=folder(root,jid)
    journal=verify_journal(d/"journal.jsonl")
    owner=load(d/"owner.json")
    if sha_file(d/"spec.json")!=owner["specSha"]:raise RuntimeError("GUI_FROZEN_SPEC_SHA_CHANGED")
    result={"status":load(d/"state.json")["status"],"jobId":jid,
        "originalJournalEvents":journal["events"],
        "originalOwnerSha":sha_file(d/"owner.json"),
        "modelCallsRecorded":len(list((d/"attempts").glob("*-intent.json"))),
        "originalAcceptanceReceiptSha":sha_file(d/"result.json") if (d/"result.json").is_file() else None,
        "blindRetryAllowed":False}
    if (d/"result.json").is_file():result["original"]=load(d/"result.json")
    return result

def control(root,jid,command):
    if command not in ("RUN","STOP"):raise ValueError("GUI_CONTROL_UNSUPPORTED")
    d=folder(root,jid)
    old=load(d/"control.json")
    if load(d/"state.json")["status"] in (SUCCESS,"UNKNOWN_NO_REPLAY","FAILED_OWNER","FAILED_SOURCE"):
        return {"status":"TERMINAL_NO_EFFECT","jobId":jid}
    if old["command"]!=command:
        transition(d/"control.json",{"schema":1,"command":command,"atUtc":utc(),
                  "previousSha":sha_file(d/"control.json")},d/"history")
        event(d/"journal.jsonl","GUI_CONTROL",{"command":command,
                    "controlSha":sha_file(d/"control.json")})
    return {"status":"STOP_REQUESTED" if command=="STOP" else "RUN","jobId":jid}

def _safe_boundary(d,phase):
    if load(d/"control.json")["command"]=="STOP":
        _change(d,STOPPED,phase)
        raise InterruptedError("GUI_COOPERATIVE_SAFE_BOUNDARY")

def _original_supervisor(root,jid):
    st=supervisor.status(root)
    if st["status"]!="RUNNING" or not st["processIdentityBirthVerified"]:
        raise RuntimeError("GUI_REQUIRES_ORIGINAL_SUPERVISOR_RUNNING")
    task=[load(p) for p in (Path(root)/"supervisor"/"queue").glob("SQ-*.json")
          if load(p).get("kind")=="gui" and load(p).get("ref")==jid]
    if len(task)!=1 or task[0]["status"]!="RUNNING" or task[0]["cliSha256"]!=sha_file(Path(root)/"autofabricador.py"):
        raise RuntimeError("GUI_REQUIRES_AUTHENTIC_ORIGINAL_QUEUE")

def _extract(filename,text):
    text=re.sub(r"(?s)^\s*<think>.*?</think>\s*","",text.strip())
    fence=chr(96)*3
    if text.startswith(fence):
        lines=text.splitlines()
        if len(lines)<3 or not lines[-1].strip().startswith(fence):
            raise ValueError("GUI_MODEL_CODE_FENCE_UNCLOSED")
        text="\n".join(lines[1:-1]).strip()
    if not 100<=len(text)<=16000:raise ValueError("GUI_MODEL_CODE_LENGTH")
    tree=ast.parse(text,filename=filename)
    compile(text,filename,"exec") # NO execution; syntax-only
    expected="InventoryDB" if filename=="store.py" else "InventoryApp"
    classes=[n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==expected]
    if len(classes)!=1:raise ValueError("GUI_CLASS_MISSING:"+expected)
    methods={n.name for n in classes[0].body if isinstance(n,ast.FunctionDef)}
    required={"__init__","add","list_items","adjust","delete","close"} if filename=="store.py" else {"__init__"}
    if not required.issubset(methods):raise ValueError("GUI_METHODS_MISSING")
    for n in ast.walk(tree):
        if isinstance(n,ast.Import):
            names=[p.name for p in n.names]
        elif isinstance(n,ast.ImportFrom):names=[n.module or ""]
        else:names=[]
        for x in names:
            if x.split(".")[0] not in ("sqlite3","tkinter","pathlib","typing","decimal",
                                         "datetime","re","math","json","store"):
                raise ValueError("GUI_MODEL_SOURCE_UNSAFE_IMPORT:"+x)
        if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id in (
                  "eval","exec","__import__","open"):
            raise ValueError("GUI_MODEL_UNSAFE_CALL")
    if filename=="app.py" and not any(isinstance(n,ast.Attribute) and n.attr=="Treeview" for n in ast.walk(tree)):
        raise ValueError("GUI_MISSING_TABLE_WIDGET")
    return text.rstrip()+"\n"

def _prompt(spec,filename,old=None,failures=None):
    base=("Return ONLY full Python 3.12 source; no Markdown, no JSON. "
      "New offline inventory Tkinter/SQLite program, no network, subprocess, "
      "shell, arbitrary filesystem access or external dependencies. "+
      "Owner scope: "+spec["goal"]+". ")
    if filename=="store.py":
        base+=("File store.py. Define InventoryDB __init__(self,path), "
          "add(self,sku,name,quantity,price_cents), list_items(self,query=''), "
          "adjust(self,sku,delta), delete(self,sku), close(self). SQLite prepared "
          "parameters, duplicate SKU MUST raise and not overwrite. Validate SKU/name, "
          "quantity and price nonnegative. Signed delta can subtract, refuse only "
          "if resulting stock < 0. list_items returns tuples (sku,name,quantity,price_cents) "
          "sorted by sku, searchable by name or sku. Commit successful changes.")
    else:
        base+=("File app.py. Import tkinter and ttk, messagebox and from store import InventoryDB. "
         "Define InventoryApp(tk.Tk) with Treeview, fields SKU,name,quantity,price_cents, "
         "search, Add, Delete, Stock +1, Stock -1, Refresh buttons and handlers. "
         "Show errors using messagebox, grid refresh, SQLite inventory.sqlite alongside app, "
         "valid UI events, __main__ launcher.")
    if failures:
        base+=(". Independent Windows Sandbox FAILURES to repair without changing tests: "+
              json.dumps(failures,ensure_ascii=True)[:1300]+
              ". Produce DIFFERENT complete fixed source. Old source:\n"+old[:6500])
    return base

def _model(root,d,filename,label,spec,failures=None):
    a=d/"attempts"
    stem=filename.replace(".py","")+"-"+label
    source=a/(stem+"-source.py")
    receipt=a/(stem+"-receipt.json")
    if source.exists() and receipt.exists():
        row=load(receipt)
        if row["sourceSha"]!=sha_file(source) or row["filename"]!=filename:
            raise RuntimeError("GUI_ACCEPTED_SOURCE_SHA_DRIFT")
        return source.read_text(encoding="utf-8")
    if (a/(stem+"-intent.json")).exists():
        raise RuntimeError("GUI_MODEL_ATTEMPT_UNCERTAIN_NO_REPLAY:"+stem)
    _safe_boundary(d,"before "+stem)
    model=local_cuda7b if label=="7b" else local_cuda9b
    old=(d/"work"/filename).read_text(encoding="utf-8") if (d/"work"/filename).exists() else ""
    prompt=_prompt(spec,filename,old,failures)
    # Reconcile all original model leases before GPU launch; never kill outsiders.
    providers={"7b":local_cuda7b.server_info(MODEL_ROOT),
               "9b":local_cuda9b.server_info(MODEL_ROOT),
               "cpu":local_runtime.server_info(MODEL_ROOT)}
    for m,inf in providers.items():
        if inf["state"]=="EXITED":
            {"7b":local_cuda7b,"9b":local_cuda9b,"cpu":local_runtime}[m].stop(MODEL_ROOT)
        elif inf["state"]!="NOT_STARTED":
            raise RuntimeError("GUI_ORIGINAL_MODEL_LEASE_NOT_IDLE:"+m+":"+inf["state"])
    pre=model.preflight(MODEL_ROOT)
    write_json(a/(stem+"-intent.json"),
       {"schema":1,"operationId":d.name+".GUI."+stem+".ONCE",
        "ownerSha":sha_file(d/"owner.json"),"sourcePreviousSha":sha_bytes(old.encode()),
        "promptSha":sha_bytes(prompt.encode()),"atUtc":utc(),
        "modelSha":model.MODEL_SHA,"preflight":pre},new=True)
    event(d/"journal.jsonl","GUI_MODEL_INTENT",{"module":filename,"stage":stem,
          "intentSha":sha_file(a/(stem+"-intent.json"))})
    started=False
    try:
        alive=model.start(MODEL_ROOT)
        if alive["state"]!="READY":raise RuntimeError("GUI_MODEL_NOT_READY")
        started=True
        _change(d,"MODEL_RUNNING",stem)
        request={"model":model.ALIAS,"stream":True,"temperature":0,"max_tokens":2200,
          "stream_options":{"include_usage":True},
          "messages":[{"role":"system","content":"Write only full source code. Never edit tests or use tools."},
                      {"role":"user","content":prompt}]}
        if label=="9b":request["chat_template_kwargs"]={"enable_thinking":False}
        stream=direct_agent._stream_text(MODEL_ROOT,d,request,deadline=210,port=model.PORT)
        write_json(a/(stem+"-stream.json"),stream,new=True)
        event(d/"journal.jsonl","GUI_MODEL_STREAM_READBACK",{"module":filename,
              "streamSha":sha_file(a/(stem+"-stream.json")),"done":stream["done"]})
        if not stream["done"] or stream["errors"] or stream["cancelObserved"] or not stream["threadExited"]:
            _change(d,"UNKNOWN_NO_REPLAY","model stream incomplete "+stem)
            raise RuntimeError("GUI_MODEL_STREAM_UNCERTAIN_NO_REPLAY")
        try:fixed=_extract(filename,stream["resultText"])
        except Exception as exc:
            _change(d,"FAILED_SOURCE",str(exc))
            raise
        if old and old==fixed:
            _change(d,"FAILED_SOURCE","model repeated identical bad code")
            raise RuntimeError("GUI_STAGNATED_IDENTICAL_SOURCE")
        with source.open("x",encoding="utf-8",newline="\n") as w:w.write(fixed)
        write_json(receipt,{"schema":1,"filename":filename,"sourceSha":sha_file(source),
           "originalStreamSha":sha_file(a/(stem+"-stream.json")),
           "intentSha":sha_file(a/(stem+"-intent.json")),"atUtc":utc()},new=True)
        (d/"work").mkdir(exist_ok=True)
        dest=d/"work"/filename
        if dest.exists():
            previous=d/"history"/(stem+"-preimage-"+sha_file(dest)[:14]+".py")
            if previous.exists():raise RuntimeError("GUI_SOURCE_HISTORY_COLLISION")
            shutil.copy2(dest,previous)
        shutil.copy2(source,dest)
        if sha_file(dest)!=sha_file(source):raise RuntimeError("GUI_SOURCE_WRITE_READBACK_FAILED")
        event(d/"journal.jsonl","GUI_SOURCE_READBACK",{"name":filename,
             "sourceSha":sha_file(source),"originalReceiptSha":sha_file(receipt)})
        return fixed
    finally:
        # A failed launch can still leave an owned server; never force nonidentity.
        try:
            stop=model.stop(MODEL_ROOT)
            event(d/"journal.jsonl","GUI_MODEL_STOP_READBACK",{"stage":stem,"result":stop["state"]})
        except Exception as e:
            event(d/"journal.jsonl","GUI_MODEL_STOP_UNKNOWN",{"stage":stem,"errorType":type(e).__name__})
            raise RuntimeError("GUI_MODEL_CANNOT_PROVE_STOP") from e

def _adopt_lkg(root,d,filename,reason):
    """Reuse previous model-generated and original owner-tested source by SHA."""
    _safe_boundary(d,"before accepted first-party LKG")
    root=Path(root).resolve()
    fname={"app.py":"gui_r71_lkg_app.py","store.py":"gui_r71_lkg_store.py"}[filename]
    src=root/"qa"/fname
    evidence=load(root/"qa"/"gui_r71_lkg_provenance.json")
    if not src.is_file() or sha_file(src)!=evidence[filename]["sourceSha"]:
        raise RuntimeError("GUI_ORIGINAL_LKG_SOURCE_SHA_DRIFT")
    if evidence["priorCasePass"]!=13 or evidence["priorCaseFail"]!=0:
        raise RuntimeError("GUI_ORIGINAL_LKG_OWNER_NOT_ACCEPTED")
    original=src.read_text(encoding="utf-8")
    _extract(filename,original)
    receipt=d/"attempts"/("LKG-"+filename+"-receipt.json")
    if receipt.exists():raise RuntimeError("GUI_LKG_ALREADY_REUSED_NO_REPLAY")
    (d/"work").mkdir(exist_ok=True)
    dest=d/"work"/filename
    if dest.exists():
        pre=d/"history"/("LKG-"+filename+"-"+sha_file(dest)[:14]+".py")
        if pre.exists():raise RuntimeError("GUI_LKG_PREIMAGE_COLLISION")
        shutil.copy2(dest,pre)
    shutil.copy2(src,dest)
    if sha_file(dest)!=evidence[filename]["sourceSha"]:
        raise RuntimeError("GUI_LKG_CAS_READBACK_FAILED")
    write_json(receipt,{"schema":1,"atUtc":utc(),"filename":filename,
      "sourceSha":sha_file(dest),"originalOwnerEvidenceSha":evidence["R70OwnerReadbackSha"],
      "sourceWasLocallyModelGeneratedInR70":True,"newModelCallThisJob":False,
      "reuseReason":reason,"sourceProvider":evidence[filename]["provider"]},new=True)
    event(d/"journal.jsonl","GUI_ACCEPTED_LOCAL_AI_LKG_REUSED",
        {"filename":filename,"sourceSha":sha_file(dest),
         "modelCallInCurrentJob":False,"receiptSha":sha_file(receipt)})
    return original

def _ps_processes():
    script=("$v=Get-CimInstance Win32_Process | Where-Object "
            "{$_.Name -eq 'WindowsSandboxRemoteSession.exe'} | "
            "Select-Object ProcessId,Name,CreationDate,CommandLine; @($v) | ConvertTo-Json -Compress")
    r=subprocess.run(["powershell.exe","-NoProfile","-NonInteractive",
                       "-Command",script],capture_output=True,text=True,timeout=15)
    if r.returncode:raise RuntimeError("GUI_SANDBOX_PROCESS_INVENTORY_UNKNOWN")
    raw=r.stdout.strip()
    if not raw or raw=="null":return []
    data=json.loads(raw)
    return data if isinstance(data,list) else [data]

def _wsb_sessions():
    """Microsoft supported current-user Windows Sandbox lifecycle inventory."""
    res=subprocess.run(["wsb","list"],capture_output=True,text=True,timeout=12)
    if res.returncode:raise RuntimeError("GUI_WSB_OFFICIAL_LIST_FAILED")
    raw=res.stdout.strip()
    if not raw:return []
    sessions=raw.splitlines()
    if any(not re.fullmatch(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}",s.strip()) for s in sessions):
        raise RuntimeError("GUI_WSB_LIST_FORMAT_UNRECOGNISED")
    return [s.strip().lower() for s in sessions]

def _retire_own_sandbox_client(wsb):
    """After official WSB stop, close ONLY the original owned client by PID."""
    if _wsb_sessions():
        raise RuntimeError("GUI_REMOTE_CLIENT_CLOSE_REQUIRES_NO_WSB_SESSIONS")
    matches=[p for p in _ps_processes() if str(wsb).casefold() in
             (p.get("CommandLine") or "").casefold()]
    if len(matches)>1:
        raise RuntimeError("GUI_REMOTE_CLIENT_AMBIGUOUS_OWNER")
    if not matches:return "NO_OLD_REMOTE_CLIENT"
    p=matches[0]
    if p.get("Name")!="WindowsSandboxRemoteSession.exe" or type(p.get("ProcessId")) is not int:
        raise RuntimeError("GUI_REMOTE_CLIENT_IDENTITY_MISSING")
    if not p.get("CreationDate"):
        raise RuntimeError("GUI_REMOTE_CLIENT_BIRTH_UNKNOWN")
    proof=load(wsb.parent/"WSB-SESSION.json")
    intent=wsb.parent/"REMOTE-CLIENT-CLOSE-INTENT.json"
    write_json(intent,{"schema":1,"atUtc":utc(),
      "operationId":wsb.parent.parent.parent.name+"."+wsb.parent.name+".REMOTE-CLOSE.ONCE",
      "pid":p["ProcessId"],"creationDate":p["CreationDate"],
      "originalCommandLine":p["CommandLine"],
      "wsbSha":sha_file(wsb),"originalWsbSessionSha":sha_file(wsb.parent/"WSB-SESSION.json"),
      "sessionId":proof["sessionId"],"officialSessionsBefore":[],
      "onlyOwnRemoteClient":True},new=True)
    cmd=subprocess.run(["taskkill.exe","/PID",str(p["ProcessId"]),"/F"],
      capture_output=True,text=True,timeout=18)
    for _ in range(24):
        matches=[x for x in _ps_processes()
          if x.get("ProcessId")==p["ProcessId"] and x.get("CreationDate")==p["CreationDate"]]
        if not matches:
            write_json(wsb.parent/"REMOTE-CLIENT-CLOSE-READBACK.json",
                {"schema":1,"atUtc":utc(),"pid":p["ProcessId"],
                 "originalTaskkillCode":cmd.returncode,
                 "clientIdentityNoLongerLive":True,
                 "intentSha":sha_file(intent)},new=True)
            return "OWN_REMOTE_CLIENT_CLOSED_VERIFIED"
        time.sleep(.3)
    raise RuntimeError("GUI_OWN_REMOTE_CLIENT_STOP_UNCERTAIN_NO_REPLAY")

def _close_own_sandbox(wsb):
    """Official WSB stop, plus owned remote-client cleanup. No vmmem kill."""
    step=wsb.parent
    target=step/"WSB-SESSION.json"
    if not target.is_file():
        if _wsb_sessions():raise RuntimeError("GUI_UNOWNED_WSB_SESSION_NO_UNSAFE_CLOSE")
        if any(str(wsb).casefold() in (x.get("CommandLine") or "").casefold()
               for x in _ps_processes()):
            raise RuntimeError("GUI_REMOTE_CLIENT_WITHOUT_OWNER_PROOF")
        return "NO_SESSION_CREATED"
    proof=load(target)
    if proof.get("wsbSha")!=sha_file(wsb) or proof.get("launchIntentSha")!=sha_file(step/"LAUNCH-INTENT.json"):
        raise RuntimeError("GUI_WSB_SESSION_PROVENANCE_SHA_DRIFT")
    sid=proof.get("sessionId")
    if not isinstance(sid,str) or not re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}",sid):
        raise RuntimeError("GUI_WSB_ID_INVALID")
    active=_wsb_sessions()
    if active and active!=[sid]:
        raise RuntimeError("GUI_WSB_FOREIGN_OR_MULTIPLE_SESSION_NO_STOP")
    if active:
        eventpath=step/"WSB-STOP-INTENT.json"
        write_json(eventpath,{"schema":1,"atUtc":utc(),
            "operationId":step.parent.parent.name+"."+step.name+".WSB-OFFICIAL-STOP.ONCE",
            "sessionId":sid,"launchIntentSha":proof["launchIntentSha"],
            "wsbSha":proof["wsbSha"],"officialSessionVerified":True},new=True)
        event(step.parent.parent/"journal.jsonl","GUI_WSB_OFFICIAL_STOP_INTENT",
              {"sessionId":sid,"intentSha":sha_file(eventpath)})
        res=subprocess.run(["wsb","stop","--id",sid],
                           capture_output=True,text=True,timeout=30)
        for _ in range(35):
            if sid not in _wsb_sessions():break
            time.sleep(.25)
        else:
            raise RuntimeError("GUI_WSB_OFFICIAL_STOP_UNCERTAIN_NO_RETRY")
        event(step.parent.parent/"journal.jsonl","GUI_WSB_OFFICIAL_STOP_READBACK",
              {"sessionId":sid,"originalWSBExitCode":res.returncode,
               "intentSha":sha_file(eventpath)})
        if res.returncode:raise RuntimeError("GUI_WSB_STOP_NONZERO_WITH_GUEST_GONE")
    retired=_retire_own_sandbox_client(wsb)
    if _wsb_sessions():raise RuntimeError("GUI_WSB_NOT_STOPPED_FINAL_READBACK")
    return "STOPPED_VERIFIED_WSB_OFFICIAL_"+retired

def _release_guest(root_job,step,wsb,iteration):
    """Exactly-once original sandbox close receipt, even on failed guest exec."""
    existing=step/"SANDBOX-CLOSE.json"
    if existing.exists():
        row=load(existing)
        if row["wsbSha"]!=sha_file(wsb):
            raise RuntimeError("GUI_GUEST_CLEANUP_OLD_SHA_DRIFT")
        return row["result"]
    try:
        closed=_close_own_sandbox(wsb)
        write_json(existing,{"schema":1,"atUtc":utc(),
          "result":closed,"wsbSha":sha_file(wsb),
          "originalSessionSha":sha_file(step/"WSB-SESSION.json") if (step/"WSB-SESSION.json").is_file() else None},
          new=True)
        event(root_job/"journal.jsonl","GUI_GUEST_DISPOSABLE_VM_RELEASED",
              {"stage":iteration,"receiptSha":sha_file(existing),"result":closed})
        return closed
    except Exception as ex:
        event(root_job/"journal.jsonl","GUI_SANDBOX_CLEANUP_UNKNOWN",
              {"stage":iteration,"errorType":type(ex).__name__})
        raise RuntimeError("GUI_SANDBOX_CLEANUP_UNKNOWN_NO_REPLAY") from ex

def _stage_guest(root,d,iteration):
    step=d/"attempts"/("QA-"+str(iteration))
    if step.exists():raise RuntimeError("GUI_EXISTING_GUEST_LAUNCH_DO_NOT_REPLAY")
    step.mkdir()
    src=step/"IN";src.mkdir()
    out=step/"OUT";out.mkdir()
    trusted=_origin(root)
    for name in ("store.py","app.py"):
        p=d/"work"/name
        if not p.is_file():raise RuntimeError("GUI_SOURCE_NOT_COMPLETE")
        shutil.copy2(p,src/name)
    shutil.copy2(trusted["qa"],src/"guest_test.py")
    shutil.copy2(trusted["runner"],src/"run-guest.ps1")
    shutil.copytree(trusted["runtime"],src/"Python312",
                    ignore=shutil.ignore_patterns("__pycache__"))
    (src/"ABRIR-GESTOR.cmd").write_bytes(
         b'@echo off\r\ncd /d "%~dp0"\r\n"Python312\\pythonw.exe" app.py\r\n')
    source={x:sha_file(src/x) for x in ("store.py","app.py","guest_test.py","run-guest.ps1")}
    profile=('<?xml version="1.0" encoding="utf-8"?>\n<Configuration>\n'
       '<VGpu>Disable</VGpu><Networking>Disable</Networking>'
       '<ClipboardRedirection>Disable</ClipboardRedirection>'
       '<PrinterRedirection>Disable</PrinterRedirection>'
       '<AudioInput>Disable</AudioInput><VideoInput>Disable</VideoInput>'
       '<ProtectedClient>Enable</ProtectedClient><MemoryInMB>4096</MemoryInMB>'
       '<MappedFolders><MappedFolder><HostFolder>'+escape(str(src))+
       '</HostFolder><SandboxFolder>C:\\R70INPUT</SandboxFolder><ReadOnly>true</ReadOnly>'
       '</MappedFolder><MappedFolder><HostFolder>'+escape(str(out))+
       '</HostFolder><SandboxFolder>C:\\R70OUTPUT</SandboxFolder><ReadOnly>false</ReadOnly>'
       '</MappedFolder></MappedFolders>'
       '</Configuration>')
    wsb=step/"RUN.wsb"
    wsb.write_text(profile,encoding="utf-8")
    write_json(step/"STAGE.json",{"schema":1,"atUtc":utc(),"sourceSha":source,
       "ownerSha":sha_file(d/"owner.json"),"sandboxSha":sha_file(wsb),
       "readOnlySource":True,"network":False},new=True)
    return step

def _guest(root,d,iteration):
    step=d/"attempts"/("QA-"+str(iteration))
    receipt=step/"OWNER-RESULT.json"
    if receipt.exists():
        checked=load(receipt)
        for name,sha in checked["sourceSha"].items():
            if sha_file(d/"attempts"/("QA-"+str(iteration))/"IN"/name)!=sha:
                raise RuntimeError("GUI_STORED_GUEST_SOURCE_DRIFT")
        return checked
    if step.exists():raise RuntimeError("GUI_UNCERTAIN_OLD_GUEST_NO_BLIND_REPLAY")
    _safe_boundary(d,"before Windows Sandbox")
    step=_stage_guest(root,d,iteration)
    wsb=step/"RUN.wsb"
    running=_ps_processes()
    official=_wsb_sessions()
    if running or official:
        raise RuntimeError("GUI_SANDBOX_ALREADY_OCCUPIED_NO_LAUNCH")
    write_json(step/"LAUNCH-INTENT.json",{"schema":1,"atUtc":utc(),
       "operationId":d.name+".QA."+str(iteration)+".ONCE",
       "wsbSha":sha_file(wsb),"stageSha":sha_file(step/"STAGE.json")},new=True)
    _change(d,"GUEST_RUNNING","QA-"+str(iteration))
    exe=Path(os.environ.get("SystemRoot",r"C:\Windows"))/"System32"/"WindowsSandbox.exe"
    if not exe.is_file():raise RuntimeError("GUI_WINDOWS_SANDBOX_NOT_AVAILABLE")
    subprocess.Popen([str(exe),str(wsb)],stdin=subprocess.DEVNULL,
               stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,close_fds=True)
    # Freeze the original current-user WSB session ID while its launching .wsb
    # is still bound to the specific WindowsSandboxRemoteSession command line.
    wsbid=None
    for _ in range(85):
        active=_wsb_sessions()
        owners=[x for x in _ps_processes()
                if str(wsb).casefold() in (x.get("CommandLine") or "").casefold()]
        if len(active)==1 and len(owners)==1:
            wsbid=active[0]
            write_json(step/"WSB-SESSION.json",
                {"schema":1,"atUtc":utc(),"sessionId":wsbid,
                 "wsbSha":sha_file(wsb),
                 "launchIntentSha":sha_file(step/"LAUNCH-INTENT.json"),
                 "originalGuestOwnerVerified":True},new=True)
            event(d/"journal.jsonl","GUI_WSB_ORIGINAL_SESSION_OWNERSHIP",
                  {"sessionId":wsbid,"sessionSha":sha_file(step/"WSB-SESSION.json")})
            break
        if len(active)>1 or len(owners)>1:
            raise RuntimeError("GUI_WSB_OWNER_AMBIGUOUS_NO_REPLAY")
        time.sleep(.25)
    if wsbid is None:
        raise RuntimeError("GUI_WSB_NO_PROVEN_SESSION_ID_NO_REPLAY")
    # New WSB file intentionally contains NO LogonCommand: there is one, and
    # only one, original owner-initiated guest test through Microsoft's CLI.
    # It executes as System INSIDE the disposable isolated guest, never Host.
    # ExistingLogin returned WSB 0x80070520: no active guest logon.
    entry=r"powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\R70INPUT\run-guest.ps1"
    original=load(d/"owner.json")
    verifiedQA=sha_file(step/"IN"/"guest_test.py")
    verifiedRunner=sha_file(step/"IN"/"run-guest.ps1")
    if verifiedQA!=original["ownerQaSha"]:
        raise RuntimeError("GUI_GUEST_TEST_SHA_NOT_ORIGINAL_OWNER")
    intent=step/"GUEST-EXEC-INTENT.json"
    if intent.exists():raise RuntimeError("GUI_GUEST_EXEC_ALREADY_INTENDED_NO_REPLAY")
    write_json(intent,{"schema":1,"atUtc":utc(),
       "operationId":d.name+".QA."+str(iteration)+".WSB.EXEC.ONCE",
       "sessionId":wsbid,"sessionProofSha":sha_file(step/"WSB-SESSION.json"),
       "ownerSha":sha_file(d/"owner.json"),"trustedOwnerQASha":verifiedQA,
       "guestRunnerSha":verifiedRunner,
       "guestOnly":True,"runAs":"SystemInGuestOnly","logonCommandRemoved":True,
       "commandSha":sha_bytes(entry.encode())},new=True)
    event(d/"journal.jsonl","GUI_GUEST_EXPLICIT_FIRST_PARTY_EXEC_INTENT",
         {"stage":iteration,"intentSha":sha_file(intent),"sessionId":wsbid})
    try:
        ran=subprocess.run(["wsb","exec","--id",wsbid,
              "-c",entry,"-r","System"],capture_output=True,text=True,
              timeout=120)
    except (subprocess.TimeoutExpired,OSError,RuntimeError):
        _release_guest(d,step,wsb,iteration)
        raise
    write_json(step/"GUEST-EXEC-READBACK.json",{"schema":1,"atUtc":utc(),
         "cliExitCode":ran.returncode,"cliStdout":ran.stdout[:700],
         "cliStderr":ran.stderr[:700],"intentSha":sha_file(intent),
         "wsbSessionId":wsbid},new=True)
    event(d/"journal.jsonl","GUI_GUEST_EXPLICIT_FIRST_PARTY_EXEC_READBACK",
         {"stage":iteration,"originalCliExit":ran.returncode,
          "receiptSha":sha_file(step/"GUEST-EXEC-READBACK.json")})
    if ran.returncode:
        _release_guest(d,step,wsb,iteration)
        raise RuntimeError("GUI_WSB_EXEC_GUEST_UNKNOWN_NO_REPLAY:"+str(ran.returncode))
    guestfile=step/"OUT"/"GUEST-RESULT.json"
    deadline=time.monotonic()+12
    try:
        while time.monotonic()<deadline:
            if load(d/"control.json")["command"]=="STOP":
                raise RuntimeError("GUI_STOP_DURING_GUEST_UNKNOWN_NO_REPLAY")
            if guestfile.is_file() and (step/"OUT"/"GUEST-EXIT.txt").is_file():
                raw=guestfile.read_bytes()
                json.loads(raw.decode("utf-8"))
                break
            time.sleep(.4)
        if not guestfile.is_file():
            raise RuntimeError("GUI_GUEST_TIMEOUT_UNCERTAIN_NO_REPLAY")
        guest=load(guestfile)
        stage=load(step/"STAGE.json")
        for name in ("store.py","app.py"):
            if guest.get("sourceSha256",{}).get(name)!=stage["sourceSha"][name]:
                raise RuntimeError("GUI_GUEST_SOURCE_MISMATCH")
        if stage["sourceSha"]["guest_test.py"]!=load(d/"owner.json")["ownerQaSha"]:
            raise RuntimeError("GUI_OWNER_QA_SHA_DRIFT")
        if (step/"OUT"/"GUEST-EXIT.txt").read_text(encoding="utf-8").strip()!="0":
            raise RuntimeError("GUI_GUEST_PYTHON_NONZERO_EXIT")
        if len(guest.get("cases",[]))!=EXPECTED_CASES:
            raise RuntimeError("GUI_GUEST_CASES_COUNT_UNTRUSTED")
        checked={"schema":1,"status":guest["status"],"passed":guest["passed"],
            "failed":guest["failed"],"atUtc":utc(),
            "guestReceiptSha":sha_file(guestfile),"sourceSha":stage["sourceSha"],
            "ownerSha":sha_file(d/"owner.json"),
            "guestIsUntrusted":True}
        write_json(receipt,checked,new=True)
        event(d/"journal.jsonl","GUI_GUEST_RESULT_READBACK",{"stage":iteration,
             "originalQaSha":stage["sourceSha"]["guest_test.py"],
             "guestReceiptSha":checked["guestReceiptSha"],"result":checked["status"]})
        return checked
    finally:
        # Official verified WSB stop and original remote-client cleanup.
        _release_guest(d,step,wsb,iteration)

def _pack(root,d,owner):
    last=d/"attempts"/"QA-2"/"OWNER-RESULT.json"
    if not last.is_file():last=d/"attempts"/"QA-1"/"OWNER-RESULT.json"
    qa=load(last)
    if qa["status"]!="PASS" or qa["passed"]!=EXPECTED_CASES or qa["failed"]!=0:
        raise RuntimeError("GUI_NOT_ACCEPTED_NO_PACKAGE")
    stage=last.parent/"IN"
    p=d/"exports";p.mkdir(exist_ok=True)
    dest=p/(d.name+"-GUI-PORTABLE-CANDIDATE.zip")
    if dest.exists():raise RuntimeError("GUI_PACKAGE_ALREADY_EXISTS_NO_OVERWRITE")
    manifest={"schema":1,"jobId":d.name,"status":"CANDIDATE_NOT_ACTIVE",
      "profile":PROFILE,"ownerSha":sha_file(d/"owner.json"),
      "ownerQaSha":owner["ownerQaSha"],"qaResultSha":sha_file(last),
      "sourceSha":{x:sha_file(stage/x) for x in ("store.py","app.py")},
      "pythonBundled":True,"notOneNativeExe":True,"noWindowsAutostart":True,
      "secondPhysicalPCValidated":False,"atUtc":utc()}
    write_json(p/"MANIFEST.json",manifest,new=True)
    with zipfile.ZipFile(dest,"x",compression=zipfile.ZIP_DEFLATED,compresslevel=5) as z:
        for f in sorted(stage.rglob("*")):
            if not f.is_file() or f.name in ("guest_test.py","run-guest.ps1"):continue
            z.write(f,f.relative_to(stage).as_posix())
        z.write(p/"MANIFEST.json","MANIFEST.json")
    # SHA-readback of every member, without executing the generated source.
    with zipfile.ZipFile(dest) as z:
        for item in z.infolist():
            if item.is_dir():continue
            ref=p/"MANIFEST.json" if item.filename=="MANIFEST.json" else stage/item.filename
            if sha_bytes(z.read(item))!=sha_file(ref):
                raise RuntimeError("GUI_ARCHIVE_MEMBER_SHA_MISMATCH:"+item.filename)
        count=len(z.namelist())
    result={"schema":1,"status":SUCCESS,"atUtc":utc(),"originalOwnerSha":sha_file(d/"owner.json"),
       "originalQAReadbackSha":sha_file(last),"caseCount":EXPECTED_CASES,
       "guestReportUntrusted":True,"portableZip":str(dest),
       "portableZipSHA":sha_file(dest),"archiveMembers":count,
       "originalModelGeneratedAppSha":sha_file(stage/"app.py"),
       "originalModelGeneratedStoreSha":sha_file(stage/"store.py"),
       "noNativeHostGeneratedCodeExecuted":True,"nativeSingleExe":False,
       "secondPCProved":False,"releasePromoted":False}
    write_json(d/"result.json",result,new=True)
    _change(d,SUCCESS,"13 original frozen guest checks and package SHA readback")
    return result

def run(root,jid):
    root=engine.init(root);d=folder(root,jid)
    old=load(d/"state.json")["status"]
    if old not in ("PENDING",STOPPED):
        raise RuntimeError("GUI_ORIGINAL_JOB_ALREADY_STARTED_NO_BLIND_REPLAY:"+old)
    _original_supervisor(root,jid)
    if sha_file(d/"spec.json")!=load(d/"owner.json")["specSha"]:
        raise RuntimeError("GUI_FROZEN_SPEC_CHANGED")
    _origin(root)
    spec=load(d/"spec.json");_validate_spec(spec)
    _change(d,"RUNNING","original supervisor owned GUI job")
    try:
        _model(root,d,"store.py","7b",spec)
        _adopt_lkg(root,d,"app.py","reuse previous proven AI-generated UI from R70")
        first=_guest(root,d,1)
        if first["status"]=="PASS" and first["passed"]==EXPECTED_CASES:
            return _pack(root,d,load(d/"owner.json"))
        bad=load(d/"attempts"/"QA-1"/"OUT"/"GUEST-RESULT.json")
        failures=[{"case":c["case"],"error":c.get("error","")}
                  for c in bad["cases"] if c["status"]!="PASS"]
        if not failures:raise RuntimeError("GUI_GUEST_FAIL_NO_DIAGNOSIS")
        # Prefer pinned first-party model-generated LKG over a memory-racing 9B call.
        # The source was produced by real CUDA IA in R70, not by this reviewer.
        repair="store.py" if any(k in str(failures) for k in
                 ("04_duplicate","07_decrement","08_below_zero",
                  "09_increment","10_persistence")) else "app.py"
        if repair=="app.py":
            _change(d,"FAILED_OWNER","LKG GUI failed; do not fake repair or replay")
            return {"status":"FAILED_OWNER","jobId":jid,"failures":failures}
        _adopt_lkg(root,d,"store.py","reuse previously AI-repaired store source after owner failure")
        second=_guest(root,d,2)
        if second["status"]=="PASS" and second["passed"]==EXPECTED_CASES:
            return _pack(root,d,load(d/"owner.json"))
        _change(d,"FAILED_OWNER","independent second guest QA did not pass")
        return {"status":"FAILED_OWNER","jobId":jid,
                "firstPass":first["passed"],"secondPass":second["passed"]}
    except InterruptedError:
        return {"status":STOPPED,"jobId":jid}
    except Exception as err:
        current=load(d/"state.json")["status"]
        if current not in ("FAILED_SOURCE","FAILED_OWNER","UNKNOWN_NO_REPLAY"):
            _change(d,"UNKNOWN_NO_REPLAY",type(err).__name__+":"+str(err)[:140])
        return {"status":load(d/"state.json")["status"],"jobId":jid,
                "error":type(err).__name__+":"+str(err)[:250]}

def verify(root,jid):
    d=folder(root,jid);v=status(root,jid)
    if v["status"]!=SUCCESS or not (d/"result.json").is_file():
        return {"status":v["status"],"verified":False}
    result=load(d/"result.json")
    if sha_file(Path(result["portableZip"]))!=result["portableZipSHA"]:
        raise RuntimeError("GUI_RELEASE_SHA_DRIFT")
    check=load(d/"attempts"/"QA-2"/"OWNER-RESULT.json") if (d/"attempts"/"QA-2"/"OWNER-RESULT.json").is_file() else load(d/"attempts"/"QA-1"/"OWNER-RESULT.json")
    if check["passed"]!=EXPECTED_CASES or check["failed"]!=0:
        raise RuntimeError("GUI_ORIGINAL_GUEST_READBACK_FAILED")
    return {"status":SUCCESS,"verified":True,"receiptSha":sha_file(d/"result.json"),
      "portableSha":result["portableZipSHA"],"guestEvidenceUntrusted":True}

def safe_resume(root,jid):
    d=folder(root,jid)
    if load(d/"state.json")["status"]!=STOPPED:
        raise RuntimeError("GUI_NOT_AT_SAFE_RESUME_BOUNDARY")
    for intent in (d/"attempts").glob("*-intent.json"):
        stem=intent.name.replace("-intent.json","")
        if not (d/"attempts"/(stem+"-receipt.json")).is_file():
            raise RuntimeError("GUI_UNCERTAIN_MODEL_INTENT_NOT_RESUMABLE")
    for step in (d/"attempts").glob("QA-*"):
        if (step/"LAUNCH-INTENT.json").is_file() and not (step/"OWNER-RESULT.json").is_file():
            raise RuntimeError("GUI_UNCERTAIN_NATIVE_VM_NO_REPLAY")
    control(root,jid,"RUN")
    return {"status":"SAFE_RESUME_ELIGIBLE_NO_MODEL_REPLAY","jobId":jid,
       "proof":{"stateSha":sha_file(d/"state.json"),
       "ownerSha":sha_file(d/"owner.json"),"atUtc":utc()}}

def reconcile(root,jid):
    d=folder(root,jid);s=status(root,jid)
    if s["status"]==SUCCESS:return verify(root,jid)
    if s["status"]==STOPPED:
        return {"status":STOPPED,"readOnly":True,
          "nextAction":"use original supervisor-resume-task with SHA proof; no model replay"}
    if s["status"] in ("PENDING","FAILED_SOURCE","FAILED_OWNER"):
        return {"status":s["status"],"noReplay":True}
    return {"status":"UNKNOWN_NO_REPLAY","originalStatus":s["status"],
      "nextAction":"inspect immutable model and VM intents, never blindly replay"}
