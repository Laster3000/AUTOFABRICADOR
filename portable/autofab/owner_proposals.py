# coding: utf-8
"""Local GPU agent proposes (never approves) a user-owned deterministic oracle.

Untrusted AI output is stored OUTSIDE ENTRADAS. Only a human-reviewed copy
made by the owner can be submitted as a contract; AI-generated tests alone
NEVER count as independent acceptance. Uses original pinned model and safe
direct HTTP client, no shell/editor/model tools or cloud credentials.
"""
from __future__ import annotations
import json
import re
from pathlib import Path

from . import engine, local_cuda7b, direct_agent, owner_oracles, supervisor
from .storage import event,load,sha_bytes,sha_file,utc,verify_journal,write_json

_PROPOSAL=re.compile(r"OP-[a-f0-9]{16}\Z")

def _text(root,path):
    q=Path(path)
    entry=Path(root).resolve()/"ENTRADAS"
    if (not q.is_file() or q.is_symlink() or q.suffix.lower()!=".txt" or
        q.resolve().parent!=entry.resolve() or q.stat().st_size>7500):
        raise ValueError("PROPOSAL_GOAL_REQUIRE_PLAIN_TXT_IN_ENTRADAS")
    data=q.read_bytes()
    goal=data.decode("utf-8-sig").strip()
    if len(data)>7500 or not 24<=len(goal)<=3800 or "\x00" in goal:
        raise ValueError("PROPOSAL_GOAL_ENCODING_OR_LENGTH_BAD")
    return q,goal,sha_bytes(data)

def _folder(root,ident):
    if not isinstance(ident,str) or not _PROPOSAL.fullmatch(ident):
        raise ValueError("PROPOSAL_ID_BAD")
    return Path(root).resolve()/"proposals"/ident

def preview(root,path):
    q,goal,source_sha=_text(root,path)
    identifier="OP-"+source_sha[:16]
    return {"proposalId":identifier,"status":"GOAL_ONLY_UNVERIFIED_NO_ACCEPTANCE",
            "goal":goal,"originalGoalSha":source_sha,"source":str(q),
            "localModel":"CUDA7B_PINNED_ON_DEMAND","canRunAI":False,
            "humanReviewRequired":True,
            "notIndependentOwnerAcceptance":True,
            "requiresUserToWriteReviewedContractIntoENTRADAS":True}

def status(root,identifier):
    d=_folder(root,identifier)
    if not d.exists():
        return {"proposalId":identifier,"status":"NOT_STARTED"}
    intent=d/"intent.json"
    if not intent.is_file():
        return {"proposalId":identifier,"status":"UNKNOWN_PARTIAL_INTENT_NO_REPLAY"}
    original=load(intent)
    if sha_file(Path(original["source"]))!=original["originalGoalSha"]:
        raise RuntimeError("PROPOSAL_ORIGINAL_GOAL_DRIFT")
    verify_journal(d/"journal.jsonl")
    state=load(d/"state.json")
    return {"proposalId":identifier,"status":state["status"],
            "originalGoalSha":original["originalGoalSha"],
            "localModelSha":original["modelSha"],
            "streamReceiptSha":sha_file(d/"stream.json") if (d/"stream.json").exists() else None,
            "untrustedDraftSha":sha_file(d/"DRAFT-UNTRUSTED.json") if (d/"DRAFT-UNTRUSTED.json").exists() else None,
            "reviewRequired":True,"dispatchToOriginalFactory":False,
            "canBlindRetry":False}

def _prompt(goal):
    return (
      "Act as a local planning agent for a restricted, testable JavaScript ESM "
      "pure function. You MUST propose a concrete formula consistent with the "
      "owner's Spanish goal, but your answer is NOT independent acceptance. "
      "Do not produce source code, commands, paths, or arbitrary Python. "
      "Return only exact JSON with three keys: "
      '{"exportName":"validIdentifier","argTypes":["number"|"integer"|"text"|"boolean", ...],'
      '"oracle": { declarative abstract syntax tree } }. '
      "argTypes has 1 to 3 entries. The oracle AST grammar is: "
      'argument {"op":"arg","index":0}; literal {"op":"const","value":0}; '
      'operator {"op":"OP","args":[subtrees...]}. '
      "Allowed OPs: add,sub,mul,div,abs,floor,ceil,nonnegative,min,max,clamp,"
      "eq,lt,lte,gt,gte,if,and,or,not,trim,upper,lower,collapse_space_hyphen,"
      "length,string,concat. "
      "For clamp args are [value,lower,upper], not a property. "
      "For if args are [booleanCondition,ifTrue,ifFalse]. "
      "Generate no test cases, no owner approval, no tools. "
      "If you cannot express the precise requested semantics with the safe "
      "AST, return {\"exportName\":\"cannotDetermine\",\"argTypes\":[\"number\"],"
      "\"oracle\":{\"op\":\"const\",\"value\":0}} as an explicit uncertain draft. "
      "GOAL (original, untrusted text):\n"+goal
    )

def _validate_candidate(raw,goal):
    if not isinstance(raw,dict) or set(raw)!={"exportName","argTypes","oracle"}:
        raise ValueError("PROPOSAL_GENERATED_SCHEMA_NOT_EXACT")
    spec={"schema":1,"goal":goal,"language":"javascript","exportName":raw["exportName"],
          "argTypes":raw["argTypes"],"oracle":raw["oracle"],"maxCases":64}
    # Runs FIRST-PARTY syntax and deterministic oracle in-memory. It does NOT
    # establish alignment between user intent and AI-proposed formula.
    if (not isinstance(spec["exportName"],str) or
        not owner_oracles.open_orders._IDENTIFIER.fullmatch(spec["exportName"])):
        raise ValueError("PROPOSAL_FUNCTION_NAME_BAD")
    if (not isinstance(spec["argTypes"],list) or
        not 1<=len(spec["argTypes"])<=3 or
        any(type(t) is not str or t not in owner_oracles._TYPES for t in spec["argTypes"])):
        raise ValueError("PROPOSAL_ARGUMENT_TYPES_BAD")
    owner_oracles._safe_node(spec["oracle"],spec["argTypes"])
    cases=owner_oracles._make_cases(spec)
    if len(cases)<5:raise ValueError("PROPOSAL_TOO_FEW_REFERENCE_CASES")
    return spec

def propose(root,path):
    root=engine.init(root)
    q,goal,source_sha=_text(root,path)
    ident="OP-"+source_sha[:16]
    d=_folder(root,ident)
    if d.exists():
        return status(root,ident)
    live=supervisor.status(root)
    if live["status"] not in ("STOPPED","RUNNING") or live["pendingQueue"]!=0:
        raise RuntimeError("PROPOSAL_SUPERVISOR_BUSY_OR_LEASE_UNCERTAIN")
    original_queue=root/"supervisor"/"queue"
    if any(load(p)["status"]=="RUNNING" for p in original_queue.glob("SQ-*.json")):
        raise RuntimeError("PROPOSAL_ORIGINAL_QUEUE_BUSY")
    current=local_cuda7b.server_info(root)
    if current["state"] not in ("NOT_STARTED","READY"):
        raise RuntimeError("PROPOSAL_LOCAL_MODEL_LEASE_UNCERTAIN_NO_REPLAY")
    local_cuda7b.pinned_assets(root)
    prompt=_prompt(goal)
    d.mkdir(parents=True,exist_ok=False)
    (d/"history").mkdir(exist_ok=False)
    intent={"schema":1,"atUtc":utc(),
        "proposalId":ident,"operationId":ident+".UNTRUSTED-PROPOSAL.ONCE",
        "source":str(q),"originalGoalSha":source_sha,
        "modelSha":local_cuda7b.MODEL_SHA,
        "localHost":"127.0.0.1","localPort":local_cuda7b.PORT,
        "promptSha":sha_bytes(prompt.encode("utf-8")),
        "notIndependentAcceptance":True,
        "cloudOrHostToolsAllowed":False}
    write_json(d/"intent.json",intent,new=True)
    write_json(d/"control.json",{"schema":1,"command":"RUN","atUtc":utc()},new=True)
    write_json(d/"state.json",{"schema":1,"status":"INTENT_FROZEN_NO_AUTO_OWNER_APPROVAL","atUtc":utc()},new=True)
    event(d/"journal.jsonl","LOCAL_MODEL_PROPOSAL_INTENT",
        {"originalGoalSha":source_sha,"promptSha":intent["promptSha"],
         "intentSha":sha_file(d/"intent.json"),"modelSha":local_cuda7b.MODEL_SHA})
    owned=current["state"]=="NOT_STARTED"
    try:
        if owned and local_cuda7b.start(root)["state"]!="READY":
            raise RuntimeError("PROPOSAL_PINNED_LOCAL_MODEL_START_UNVERIFIED")
        request={"model":local_cuda7b.ALIAS,"stream":True,
                 "stream_options":{"include_usage":True},"temperature":0,
                 "max_tokens":1700,"response_format":{"type":"json_object"},
                 "messages":[{"role":"system","content":
                   "Return only valid JSON; you cannot use tools, execute programs or approve tests."},
                  {"role":"user","content":prompt}]}
        stream=direct_agent._stream_text(root,d,request,deadline=180,port=local_cuda7b.PORT)
        write_json(d/"stream.json",stream,new=True)
        event(d/"journal.jsonl","UNTRUSTED_ORIGINAL_MODEL_STREAM",
          {"streamSha":sha_file(d/"stream.json"),"done":stream["done"],
           "chunks":stream["receivedChunks"]})
        if stream["cancelObserved"] or not stream["done"] or stream["errors"]:
            state="UNKNOWN_INCOMPLETE_MODEL_NO_REPLAY"
            final={"schema":1,"status":state,"atUtc":utc(),
                   "notIndependentAcceptance":True}
        else:
            try:
                raw=json.loads(stream["resultText"])
                spec=_validate_candidate(raw,goal)
                write_json(d/"DRAFT-UNTRUSTED.json",spec,new=True)
                event(d/"journal.jsonl","UNTRUSTED_DSL_DRAFT_CREATED",
                      {"draftSha":sha_file(d/"DRAFT-UNTRUSTED.json"),
                       "ownerApproved":False,"modelSource":True})
                state="UNTRUSTED_DRAFT_REVIEW_REQUIRED"
                final={"schema":1,"status":state,"atUtc":utc(),
                       "notIndependentAcceptance":True,
                       "ownerApproved":False,
                       "draftSha":sha_file(d/"DRAFT-UNTRUSTED.json"),
                       "copyReviewedTo":"ENTRADAS/your-reviewed-contract.json"}
            except (ValueError,TypeError,KeyError) as error:
                state="UNTRUSTED_DRAFT_INVALID_REVIEW_REQUIRED"
                final={"schema":1,"status":state,"atUtc":utc(),
                       "notIndependentAcceptance":True,
                       "errorType":type(error).__name__,
                       "errorText":str(error)[:180]}
        write_json(d/"state.json.final",final,new=True)
        # No in-place mutation of initial state without preserving preimage.
        from .storage import transition
        transition(d/"state.json",final,d/"history")
        return status(root,ident)
    except Exception:
        # The model start or transport may have had effects; never replay ID.
        from .storage import transition
        if (d/"state.json").is_file():
            transition(d/"state.json",{"schema":1,"atUtc":utc(),
                       "status":"UNKNOWN_MODEL_EFFECTS_RECONCILE_NO_REPLAY"},
                       d/"history")
        raise
    finally:
        if owned:
            # The original server owns process identity and checks birth/SHA.
            local_cuda7b.stop(root)
