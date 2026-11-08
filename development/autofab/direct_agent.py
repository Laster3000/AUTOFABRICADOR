# coding: utf-8
"""Direct local HTTP source-only AI with owned cancel and original SHA receipts.

No Codex/OpenCode/Aider native subprocess is launched. All generated JS runs
only in the pre-existing pinned Wasmtime WASI guest, never Node/Chrome/Host.
An in-flight model request is cancelled by closing its socket and waiting
for llama.cpp /slots is_processing=false. Intent is never replayed blindly.
"""
from __future__ import annotations
import hashlib,http.client,json,os
from pathlib import Path
import queue,re,socket,threading,time,uuid
from . import engine,local_runtime,multilang,js_wasi,npm_umd
from .storage import event,load,sha_bytes,sha_file,json_bytes,transition,utc,write_json,verify_journal
from .isolation import IsolationUnavailable

def folder(root,ident):
    if not isinstance(ident,str) or not re.fullmatch(r"AD-[a-f0-9]{16}",ident):
        raise ValueError("DIRECT_JOB_ID_INVALID")
    path=Path(root).resolve()/"directjobs"/ident
    if not path.is_dir():raise FileNotFoundError("DIRECT_JOB_NOT_FOUND")
    return path

def _current_state(d):
    return load(d/"state.json")["status"]

def _state(d,status,note):
    transition(d/"state.json",
               {"schema":1,"status":status,"atUtc":utc(),"detail":note},d/"history")
    event(d/"journal.jsonl","DIRECT_STATE",
          {"status":status,"stateSha":sha_file(d/"state.json")})

def create(root,spec_path):
    root=engine.init(root)
    path=Path(spec_path).resolve()
    if not path.is_file() or path.is_symlink() or not path.is_relative_to(root/"examples"):
        raise ValueError("DIRECT_SPEC_MUST_BE_PROJECT_EXAMPLE")
    spec=load(path)
    multilang._valid_spec(spec)
    if spec["language"]!="javascript":
        raise ValueError("DIRECT_CURRENTLY_JS_ONLY")
    js_wasi.preflight(root,"javascript")
    npm_umd.preflight(root,spec.get("dependencies",[]))
    local_runtime.pinned_assets(root)
    for old in (root/"directjobs").glob("AD-*/spec.json"):
        if load(old)==spec:
            prior=old.parent
            if _current_state(prior)=="PASS":
                verify(root,prior.name)
                return {"jobId":prior.name,"status":"EXISTING_PASS_NO_NEW_MODEL_CALL",
                        "ownerAcceptanceSha":sha_file(prior/"owner-acceptance.json")}
            raise RuntimeError("IDENTICAL_DIRECT_JOB_REQUIRES_RECONCILIATION_NO_REPLAY")
    ident="AD-"+uuid.uuid4().hex[:16]
    d=root/"directjobs"/ident
    d.mkdir(parents=True)
    write_json(d/"spec.json",spec,new=True)
    owner={"schema":1,"cases":spec["acceptance"],"function":spec["function"],"language":"javascript"}
    write_json(d/"owner-acceptance.json",owner,new=True)
    write_json(d/"control.json",{"schema":1,"command":"RUN","version":1,"atUtc":utc()},new=True)
    write_json(d/"state.json",{"schema":1,"status":"PENDING","atUtc":utc(),
                             "detail":"no network call has been initiated"},new=True)
    event(d/"journal.jsonl","INTAKE",
          {"jobId":ident,"ownerSha":sha_file(d/"owner-acceptance.json"),
           "specSha":sha_file(d/"spec.json"),"modelSha":local_runtime.MODEL_SHA})
    return {"jobId":ident,"status":"PENDING","ownerAcceptanceSha":sha_file(d/"owner-acceptance.json")}

def control(root,ident,command):
    d=folder(root,ident)
    if command not in ("STOP","RUN"):raise ValueError("DIRECT_COMMAND_UNSUPPORTED")
    s=_current_state(d)
    previous=load(d/"control.json")
    if s in ("PASS","FAILED_MODEL_FORMAT","FAILED_OWNER_ACCEPTANCE","CANCELLED_VERIFIED","UNKNOWN"):
        return {"status":"TERMINAL_NO_CONTROL_CHANGE","jobId":ident,"originalState":s}
    if command=="RUN":
        if s!="PENDING" or (d/"request.json").exists():
            raise RuntimeError("DIRECT_ALREADY_SENT_TO_MODEL_NO_RUN_REPLAY")
    if previous["command"]==command:
        return {"status":"UNCHANGED","jobId":ident,"state":s}
    updated={"schema":1,"command":command,"version":previous["version"]+1,
             "atUtc":utc(),"previousSha":sha_file(d/"control.json")}
    transition(d/"control.json",updated,d/"history")
    event(d/"journal.jsonl","CONTROL",{"command":command,
          "version":updated["version"],"controlSha":sha_file(d/"control.json")})
    return {"status":"STOP_REQUESTED" if command=="STOP" else "RUN_PRE_INTENT",
            "jobId":ident,"state":s,"controlSha":sha_file(d/"control.json")}

def _json_http(path,timeout=4,port=None):
    con=http.client.HTTPConnection("127.0.0.1",port or local_runtime.PORT,timeout=timeout)
    try:
        con.request("GET",path)
        response=con.getresponse()
        raw=response.read(20000)
        if response.status!=200:raise RuntimeError("LLAMACPP_STATUS_"+str(response.status))
        return json.loads(raw)
    finally:con.close()

def idle_receipt(root,seconds=14,port=None):
    previous=None
    started=time.monotonic()
    while time.monotonic()-started<seconds:
        try:
            state=_json_http("/slots",timeout=2.5,port=port)
            if (isinstance(state,list) and state and
                all(slot.get("is_processing") is False for slot in state)):
                health=_json_http("/health",timeout=2.5,port=port)
                if health.get("status")=="ok":
                    return {"idleVerified":True,"slotCount":len(state),
                        "allSlotsNotProcessing":True,"health":"ok",
                        "atUtc":utc(),"elapsedMs":round((time.monotonic()-started)*1000)}
            previous="SLOTS_PROCESSING"
        except Exception as e:
            previous=type(e).__name__
        time.sleep(.2)
    return {"idleVerified":False,"lastObserved":previous,
            "elapsedMs":round((time.monotonic()-started)*1000)}

def _stream_text(root,d,request,*,deadline=125,port=None):
    """Receive SSE on separate thread; own disconnect is guaranteed local."""
    ch=queue.Queue()
    finish=threading.Event()
    handle={"conn":None,"error":None}
    parts=[]
    usage={}
    finish_reasons=[]
    def worker():
        conn=http.client.HTTPConnection("127.0.0.1",port or local_runtime.PORT,timeout=45)
        handle["conn"]=conn
        try:
            conn.request("POST","/v1/chat/completions",
                    body=json.dumps(request,ensure_ascii=True).encode(),
                    headers={"Content-Type":"application/json",
                             "Accept":"text/event-stream"})
            answer=conn.getresponse()
            if answer.status!=200:
                ch.put(("error","MODEL_HTTP_"+str(answer.status)))
                return
            while True:
                line=answer.readline(200000)
                if not line:break
                if line.startswith(b"data: "):
                    value=line[6:].strip()
                    if value==b"[DONE]":
                        ch.put(("done",None));return
                    try:row=json.loads(value)
                    except (ValueError,UnicodeDecodeError):
                        ch.put(("error","INVALID_SSE_JSON"));return
                    ch.put(("chunk",row))
        except Exception as error:
            ch.put(("error",type(error).__name__+":"+str(error)[:100]))
        finally:
            try:conn.close()
            except Exception:pass
            finish.set()
    thread=threading.Thread(target=worker,daemon=True,name="AF-Direct-HTTP-Read")
    thread.start()
    began=time.monotonic()
    terminated=False
    done=False
    errors=[]
    while True:
        if load(d/"control.json")["command"]=="STOP":
            terminated=True
            break
        if time.monotonic()-began>deadline:
            errors.append("LOCAL_DIRECT_MODEL_DEADLINE")
            break
        try:
            typ,payload=ch.get(timeout=.15)
        except queue.Empty:
            if finish.is_set() and ch.empty():break
            continue
        if typ=="chunk":
            choice=(payload.get("choices") or [])
            if choice:
                reason=choice[0].get("finish_reason")
                if reason is not None:finish_reasons.append(reason)
                delta=choice[0].get("delta") or {}
                fragment=delta.get("content")
                if isinstance(fragment,str):
                    parts.append(fragment)
                    if sum(map(len,parts))>65000:
                        errors.append("DIRECT_SOURCE_RESPONSE_TOO_LARGE")
                        break
            if payload.get("usage"):usage=payload["usage"]
        elif typ=="done":
            done=True
            break
        else:
            errors.append(payload)
            break
    if terminated or errors:
        connection=handle.get("conn")
        if connection is not None:
            try:
                if connection.sock:connection.sock.shutdown(socket.SHUT_RDWR)
            except OSError:pass
            try:connection.close()
            except OSError:pass
    thread.join(timeout=5)
    if thread.is_alive():
        errors.append("NETWORK_THREAD_STILL_ALIVE_UNCERTAIN")
    else:
        # Consume any buffered terminal chunk. Never add chunks after STOP.
        pass
    result={"schema":1,"atUtc":utc(),
         "receivedChunks":len(parts),"receivedBytes":sum(len(x.encode()) for x in parts),
         "partialOrCompleteSha256":sha_bytes("".join(parts).encode()),
         "resultText":"".join(parts)[:65000],
         "usage":usage,"done":bool(done),
          "lastFinishReason":finish_reasons[-1] if finish_reasons else None,
          "cancelObserved":terminated,
         "errors":errors,"threadExited":not thread.is_alive(),
         "elapsedMs":round((time.monotonic()-began)*1000)}
    if terminated:
        result["idleAfterClientDisconnect"]=idle_receipt(root,port=port)
    return result

def run(root,ident,*,max_tokens=900):
    root=engine.init(root)
    d=folder(root,ident)
    if _current_state(d)!="PENDING" or (d/"request.json").exists():
        raise RuntimeError("DIRECT_REQUEST_NOT_PENDING_OR_ALREADY_SENT_NO_REPLAY")
    if load(d/"control.json")["command"]!="RUN":
        _state(d,"STOPPED_PRE_INTENT","model not contacted")
        return {"jobId":ident,"status":"STOPPED_PRE_INTENT"}
    spec=load(d/"spec.json")
    js_wasi.preflight(root,"javascript")
    npm_umd.preflight(root,spec.get("dependencies",[]))
    local_runtime.pinned_assets(root)
    if type(max_tokens)!=int or not 100<=max_tokens<=3000:
        raise ValueError("DIRECT_TOKEN_BUDGET_INVALID")
    old_owner_sha=sha_file(d/"owner-acceptance.json")
    old_spec_sha=sha_file(d/"spec.json")
    prompt=("Return a strict JSON object with exactly key files, mapping each filename "
          "to complete JavaScript source as a string with escaped newlines. "
          "Do not produce explanations, Markdown, imports, exports, require, "
          "shell commands, tests or extra files. Implement fully rather than "
          "returning unchanged placeholder functions. The JS executes in isolated "
          "WASI. Global allowlisted dependencies: "+",".join(spec.get("dependencies",[]))+
          ". Goal: "+spec["goal"]+
          "\nOriginal source files: "+json.dumps(spec["sources"],sort_keys=True))
    request={"model":local_runtime.ALIAS,"stream":True,
        "stream_options":{"include_usage":True},
        "temperature":0,"max_tokens":max_tokens,
        "response_format":{"type":"json_object"},
        "messages":[{"role":"system","content":"Return only valid JSON. You cannot use tools or execute commands."},
                    {"role":"user","content":prompt}]}
    record={"schema":1,"atUtc":utc(),"promptSha":sha_bytes(prompt.encode()),
            "specSha":old_spec_sha,"ownerSha":old_owner_sha,
            "modelSha":local_runtime.MODEL_SHA,
            "transport":"direct-http-127.0.0.1-only",
            "modelCodeCannotCallHostTools":True,"maxTokens":max_tokens}
    # Launch only pinned local server; existing lease must be reconciled first.
    current=local_runtime.server_info(root)
    if current["state"]=="EXITED":
        local_runtime.stop(root)
        current=local_runtime.server_info(root)
    if current["state"] not in ("NOT_STARTED","READY"):
        raise RuntimeError("DIRECT_SERVER_NOT_RECONCILED")
    owned=current["state"]=="NOT_STARTED"
    if owned and local_runtime.start(root)["state"]!="READY":
        raise RuntimeError("DIRECT_SERVER_NOT_READY")
    write_json(d/"request.json",record,new=True)
    _state(d,"MODEL_PENDING","direct local HTTP streaming; STOP closes socket")
    event(d/"journal.jsonl","DIRECT_MODEL_INTENT",
          {"operationId":ident+".STREAM.1","requestSha":sha_file(d/"request.json"),
           "modelSha":local_runtime.MODEL_SHA,"mode":"NO_EDITOR_SUBPROCESS"})
    try:
        transport=_stream_text(root,d,request)
        # Never hide the original stream (even partial). Receipt is one-shot.
        write_json(d/"stream-receipt.json",transport,new=True)
        event(d/"journal.jsonl","DIRECT_STREAM_READBACK",
              {"receiptSha":sha_file(d/"stream-receipt.json"),
               "chunks":transport["receivedChunks"],
               "cancelObserved":transport["cancelObserved"]})
        if transport["cancelObserved"]:
            idle=transport.get("idleAfterClientDisconnect",{})
            if idle.get("idleVerified") and transport["threadExited"]:
                _state(d,"CANCELLED_VERIFIED","client disconnected and original llama slots idle; terminal no model replay")
                return {"jobId":ident,"status":"CANCELLED_VERIFIED",
                        "idle":idle,"streamReceiptSha":sha_file(d/"stream-receipt.json")}
            _state(d,"UNKNOWN","client disconnected but original slot or thread not proven idle")
            return {"jobId":ident,"status":"UNKNOWN_RECONCILE",
                    "idle":idle}
        if not transport["done"] or transport["errors"]:
            _state(d,"UNKNOWN","SSE incomplete; reconcile original no replay")
            return {"jobId":ident,"status":"UNKNOWN_STREAM_INCOMPLETE",
                    "errors":transport["errors"]}
        if old_owner_sha!=sha_file(d/"owner-acceptance.json") or old_spec_sha!=sha_file(d/"spec.json"):
            _state(d,"UNKNOWN","immutable owner contract changed")
            return {"jobId":ident,"status":"UNKNOWN_OWNER_DRIFT"}
        try:
            payload=json.loads(transport["resultText"])
            if not isinstance(payload,dict):raise ValueError("MODEL_SOURCE_MAP_NOT_OBJECT")
            if set(payload)=={"files"} and isinstance(payload["files"],dict):
                files=payload["files"]
            elif set(payload)==set(spec["sources"]):
                files=payload
            else:
                raise ValueError("MODEL_SOURCE_MAP_KEYS_INVALID")
            if set(files)!=set(spec["sources"]):
                raise ValueError("MODEL_SOURCE_MAP_MISSING_EXPECTED")
            if not all(isinstance(v,str) and 10<=len(v)<=16000 for v in files.values()):
                raise ValueError("MODEL_SOURCE_CONTENT_INVALID")
        except (ValueError,TypeError) as err:
            _state(d,"FAILED_MODEL_FORMAT",type(err).__name__+":"+str(err)[:130])
            return {"jobId":ident,"status":"FAILED_MODEL_FORMAT"}
        write_json(d/"proposed.json",{"files":files,"schema":1},new=True)
        event(d/"journal.jsonl","DIRECT_SOURCE_ADMITTED",
              {"sourceSha":sha_file(d/"proposed.json"),"rawModelSha":sha_file(d/"stream-receipt.json")})
        acceptance=js_wasi.execute(root,"javascript",files,spec["function"],spec["acceptance"],
                      dependencies=spec.get("dependencies",[]))
        write_json(d/"owner-wasi.json",acceptance,new=True)
        event(d/"journal.jsonl","DIRECT_OWNER_RESULT",
              {"receiptSha":sha_file(d/"owner-wasi.json"),
               "status":acceptance["status"]})
        if acceptance["status"]!="PASS":
            _state(d,"FAILED_OWNER_ACCEPTANCE","source failed owner tests")
            return {"jobId":ident,"status":"FAILED_OWNER_ACCEPTANCE",
                    "testResult":acceptance["status"]}
        manifest={"schema":1,"jobId":ident,"status":"CANDIDATE_ACCEPTED_NOT_INSTALLED",
                  "specSha":sha_file(d/"spec.json"),
                  "ownerAcceptanceSha":sha_file(d/"owner-acceptance.json"),
                  "requestSha":sha_file(d/"request.json"),
                  "streamReceiptSha":sha_file(d/"stream-receipt.json"),
                  "sourceReceiptSha":sha_file(d/"proposed.json"),
                  "ownerWasiReceiptSha":sha_file(d/"owner-wasi.json"),
                  "modelSha":local_runtime.MODEL_SHA,
                  "ownerTestCount":len(spec["acceptance"]),
                  "isolatedExecution":True,"nativeEditorLaunched":False,
                  "acceptedAtUtc":utc()}
        write_json(d/"manifest.json",manifest,new=True)
        _state(d,"PASS","owner-pinned WASI tests all PASS")
        return {"jobId":ident,"status":"PASS",
                "ownerTestCount":len(spec["acceptance"]),"verify":verify(root,ident)}
    finally:
        if owned:
            local_runtime.stop(root)

def verify(root,ident):
    root=engine.init(root)
    d=folder(root,ident)
    if _current_state(d)!="PASS":raise RuntimeError("DIRECT_JOB_NOT_ACCEPTED")
    m=load(d/"manifest.json")
    for key,path in [
        ("specSha","spec.json"),("ownerAcceptanceSha","owner-acceptance.json"),
        ("requestSha","request.json"),("streamReceiptSha","stream-receipt.json"),
        ("sourceReceiptSha","proposed.json"),("ownerWasiReceiptSha","owner-wasi.json")]:
        if sha_file(d/path)!=m[key]:raise RuntimeError("DIRECT_MANIFEST_SHA_DRIFT:"+key)
    req=load(d/"request.json")
    if req["modelSha"]!=m["modelSha"] or req["modelSha"]!=local_runtime.MODEL_SHA:
        raise RuntimeError("DIRECT_MODEL_SHA_DRIFT")
    outcome=load(d/"owner-wasi.json")
    owner=load(d/"owner-acceptance.json")
    spec=load(d/"spec.json")
    if (outcome["status"]!="PASS" or outcome["testCount"]!=len(owner["cases"])
        or owner["cases"]!=spec["acceptance"]
        or m["ownerTestCount"]!=len(owner["cases"])
        or m["nativeEditorLaunched"] is not False
        or load(d/"stream-receipt.json")["done"] is not True):
        raise RuntimeError("DIRECT_OWNER_ACCEPTANCE_OR_STREAM_UNVERIFIED")
    if outcome.get("dependencyHashes",{})!=npm_umd.preflight(root,spec.get("dependencies",[])):
        raise RuntimeError("DIRECT_VENDOR_DRIFT")
    verify_journal(d/"journal.jsonl")
    return {"verified":True,"jobId":ident,"status":"PASS",
            "ownerTestCount":m["ownerTestCount"],
            "nativeEditorLaunched":False,
            "modelSha":local_runtime.MODEL_SHA}

def status(root,ident):
    d=folder(root,ident)
    verify_journal(d/"journal.jsonl")
    s=_current_state(d)
    return {"jobId":ident,"status":s,"control":load(d/"control.json")["command"],
            "modelIntentWritten":(d/"request.json").exists(),
            "originalStreamReceiptSha":sha_file(d/"stream-receipt.json") if (d/"stream-receipt.json").exists() else None,
            "accepted":verify(root,ident)["verified"] if s=="PASS" else False}


def reconcile_saved(root,ident):
    """Accept original finished JSON exact-source-map output without model replay."""
    root=engine.init(root)
    d=folder(root,ident)
    if _current_state(d)=="PASS":
        return {"status":"ALREADY_ACCEPTED_NO_REPLAY","verify":verify(root,ident)}
    if _current_state(d)!="FAILED_MODEL_FORMAT":
        raise RuntimeError("DIRECT_RECONCILE_ONLY_DETERMINISTIC_FORMAT_FAILURE")
    if any((d/name).exists() for name in ("proposed.json","owner-wasi.json","manifest.json","reconciliation.json")):
        raise RuntimeError("DIRECT_PRIOR_RECONCILIATION_EXISTS")
    stream=load(d/"stream-receipt.json")
    if not stream["done"] or stream["cancelObserved"] or stream["errors"]:
        raise RuntimeError("DIRECT_ORIGINAL_STREAM_NOT_COMPLETE")
    raw=stream["resultText"]
    if sha_bytes(raw.encode())!=stream["partialOrCompleteSha256"]:
        raise RuntimeError("DIRECT_ORIGINAL_STREAM_SHA_DRIFT")
    spec=load(d/"spec.json")
    pinned=load(d/"request.json")
    if sha_file(d/"spec.json")!=pinned["specSha"] or sha_file(d/"owner-acceptance.json")!=pinned["ownerSha"]:
        raise RuntimeError("DIRECT_OWNER_OR_SPEC_CHANGED")
    data=json.loads(raw)
    if not isinstance(data,dict) or set(data)!=set(spec["sources"]):
        raise RuntimeError("DIRECT_ORIGINAL_RESPONSE_NOT_EXACT_SOURCE_MAP")
    if any(not isinstance(v,str) or not 10<=len(v)<=16000 for v in data.values()):
        raise RuntimeError("DIRECT_ORIGINAL_SOURCE_SIZE_BAD")
    reconciliation={"schema":1,"status":"REUSED_ORIGINAL_MODEL_BYTES_NO_SECOND_INFERENCE",
                    "previousState":"FAILED_MODEL_FORMAT",
                    "modelCallsAdded":0,
                    "originalResponseSha":sha_file(d/"stream-receipt.json"),
                    "cause":"llama.cpp returned exact bare map rather than files wrapper"}
    write_json(d/"reconciliation.json",reconciliation,new=True)
    event(d/"journal.jsonl","DIRECT_ORIGINAL_JSON_FORMAT_RECONCILED",
          {"receiptSha":sha_file(d/"reconciliation.json"),"newModelCalls":0})
    write_json(d/"proposed.json",{"schema":1,"files":data},new=True)
    result=js_wasi.execute(root,"javascript",data,spec["function"],spec["acceptance"],
                           dependencies=spec.get("dependencies",[]))
    write_json(d/"owner-wasi.json",result,new=True)
    event(d/"journal.jsonl","DIRECT_OWNER_RESULT",
          {"receiptSha":sha_file(d/"owner-wasi.json"),"status":result["status"]})
    if result["status"]!="PASS":
        _state(d,"FAILED_OWNER_ACCEPTANCE","original reinterpreted source rejected")
        return {"jobId":ident,"status":"FAILED_OWNER_ACCEPTANCE",
                "newModelCalls":0,"testResult":result["status"]}
    original={"schema":1,"jobId":ident,"status":"CANDIDATE_ACCEPTED_NOT_INSTALLED",
          "specSha":sha_file(d/"spec.json"),
          "ownerAcceptanceSha":sha_file(d/"owner-acceptance.json"),
          "requestSha":sha_file(d/"request.json"),
          "streamReceiptSha":sha_file(d/"stream-receipt.json"),
          "sourceReceiptSha":sha_file(d/"proposed.json"),
          "ownerWasiReceiptSha":sha_file(d/"owner-wasi.json"),
          "modelSha":local_runtime.MODEL_SHA,
          "ownerTestCount":len(spec["acceptance"]),
          "isolatedExecution":True,"nativeEditorLaunched":False,
          "acceptedAtUtc":utc(),"reconciledFormatOnly":True,
          "reconciliationReceiptSha":sha_file(d/"reconciliation.json")}
    write_json(d/"manifest.json",original,new=True)
    _state(d,"PASS","original model source accepted without second inference")
    return {"status":"PASS","jobId":ident,"newModelCalls":0,"verify":verify(root,ident)}
