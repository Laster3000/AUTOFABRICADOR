# coding: utf-8
"""Reproducible real llama.cpp HTTP streaming cancellation probe (no code acceptance).

Independent diagnostic operation, not a forged source job. The same
direct_agent._stream_text transport and STOP protocol are exercised.
Proof requires observing processing=true before STOP and all slots idle
after TCP disconnect; never claims that 0 tokens were consumed.
"""
from __future__ import annotations
from pathlib import Path
import json,re,uuid
from . import engine,direct_agent,local_runtime
from .storage import sha_bytes,sha_file,load,write_json,transition,utc,event,verify_journal

def path(root,ident):
    if not isinstance(ident,str) or not re.fullmatch(r"CP-[a-f0-9]{16}",ident):
        raise ValueError("CANCEL_PROBE_ID_INVALID")
    d=Path(root).resolve()/"cancelprobes"/ident
    if not d.is_dir():raise FileNotFoundError("CANCEL_PROBE_NOT_FOUND")
    return d

def create(root):
    root=engine.init(root)
    local_runtime.pinned_assets(root)
    ident="CP-"+uuid.uuid4().hex[:16]
    d=root/"cancelprobes"/ident
    d.mkdir(parents=True)
    write_json(d/"control.json",{"schema":1,"command":"RUN","atUtc":utc()},new=True)
    write_json(d/"state.json",{"schema":1,"status":"PENDING","atUtc":utc()},new=True)
    event(d/"journal.jsonl","CANCEL_PROBE_CREATED",
          {"operationId":ident+".1","modelSha":local_runtime.MODEL_SHA})
    return {"jobId":ident,"status":"PENDING"}

def stop(root,ident):
    d=path(root,ident)
    state=load(d/"state.json")["status"]
    if state not in ("MODEL_PENDING",):
        return {"status":"NO_ACTIVE_MODEL_TO_STOP","originalState":state}
    orig=load(d/"control.json")
    if orig["command"]=="STOP":return {"status":"ALREADY_REQUESTED"}
    transition(d/"control.json",{"schema":1,"command":"STOP",
           "previousSha":sha_file(d/"control.json"),"atUtc":utc()},d/"history")
    event(d/"journal.jsonl","CANCEL_PROBE_STOP_INTENT",
          {"controlSha":sha_file(d/"control.json"),
           "originalModelPending":True})
    return {"status":"STOP_REQUESTED","jobId":ident}

def run(root,ident):
    root=engine.init(root)
    d=path(root,ident)
    if load(d/"state.json")["status"]!="PENDING" or (d/"request.json").exists():
        raise RuntimeError("CANCEL_PROBE_ALREADY_SENT_NO_REPLAY")
    live=local_runtime.server_info(root)
    if live["state"]!="READY":raise RuntimeError("PROBE_NEEDS_ORIGINAL_VERIFIED_LLAMACPP_SERVER_READY")
    report={"schema":1,"operationId":ident+".1",
            "mode":"DIRECT_STREAMING_CANCEL_NO_SOURCE_ACCEPTANCE",
            "modelSha":local_runtime.MODEL_SHA,"atUtc":utc()}
    prompt=("Respond with a JSON object that has a key named chapters whose "
            "value is an array of exactly 900 lengthy, numbered paragraphs, "
            "each paragraph containing at least 35 distinct words about "
            "software engineering design tradeoffs. Start at chapter 1 and "
            "continue sequentially to 900 without summaries or truncation.")
    request={"model":local_runtime.ALIAS,"stream":True,
             "stream_options":{"include_usage":True},
             "temperature":0.3,"max_tokens":4096,
             "messages":[{"role":"system","content":"Produce long structured JSON only, no tools."},
                         {"role":"user","content":prompt}]}
    report["promptSha"]=sha_bytes(prompt.encode())
    write_json(d/"request.json",report,new=True)
    transition(d/"state.json",{"schema":1,"status":"MODEL_PENDING","atUtc":utc()},
               d/"history")
    event(d/"journal.jsonl","PROBE_NETWORK_INTENT",
          {"requestSha":sha_file(d/"request.json"),"modelSha":local_runtime.MODEL_SHA})
    result=direct_agent._stream_text(root,d,request,deadline=110)
    write_json(d/"stream.json",result,new=True)
    event(d/"journal.jsonl","PROBE_STREAM_READBACK",
          {"streamSha":sha_file(d/"stream.json"),
           "receivedChunks":result["receivedChunks"],
           "cancelled":result["cancelObserved"],
           "allSlotsIdle":result.get("idleAfterClientDisconnect",{}).get("idleVerified")})
    good=(result["cancelObserved"] is True and result["threadExited"] is True
          and result["idleAfterClientDisconnect"]["idleVerified"] is True)
    if good:
        state="CANCELLED_VERIFIED"
    elif result["done"] and not result["errors"]:
        state="COMPLETED_NO_CANCEL"
    else:
        state="UNKNOWN_NO_REPLAY"
    transition(d/"state.json",{"schema":1,"status":state,"atUtc":utc(),
                "sourceAcceptance":False},d/"history")
    event(d/"journal.jsonl","PROBE_STATE",
          {"status":state,"stateSha":sha_file(d/"state.json")})
    return {"status":state,"jobId":ident,
            "originalModelChunksReceived":result["receivedChunks"],
            "originalStreamSha":sha_file(d/"stream.json"),
            "allSlotsIdle":result.get("idleAfterClientDisconnect",{}).get("idleVerified",False),
            "noNewSourceWasAccepted":True}

def status(root,ident):
    d=path(root,ident)
    verify_journal(d/"journal.jsonl")
    return {"jobId":ident,"state":load(d/"state.json")["status"],
            "control":load(d/"control.json")["command"],
            "streamReceiptSha":sha_file(d/"stream.json") if (d/"stream.json").exists() else None}
