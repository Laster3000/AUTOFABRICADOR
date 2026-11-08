# coding: utf-8
"""Owner-authored declarative oracle -> independent acceptance -> ORIGINAL agents.

This does NOT infer the user's intent from a free-text sentence. The original
owner signs off by writing a small auditable rule DSL; only deterministic
first-party code computes expected outputs. The local model NEVER writes the
independent oracle or test cases. No eval, exec, imports or arbitrary callbacks.

One original contract => one frozen derived input => one original work order.
UNKNOWN is read back only; never replay or silently overwrite any original.
"""
from __future__ import annotations
import hashlib
import itertools
import json
import math
import re
from pathlib import Path

from . import engine, open_orders, repo_graph
from .storage import event, json_bytes, load, sha_bytes, sha_file, utc, verify_journal, write, write_json

_TYPES={"number","integer","text","boolean"}
_SINGLE={"abs","floor","ceil","nonnegative","trim","upper","lower","collapse_space_hyphen","length","not","string"}
_BINARY={"sub","div","eq","lt","lte","gt","gte"}
_NARY={"add","mul","min","max","concat","and","or"}
_THREE={"if","clamp"}
_LIMIT=1_000_000_000
_DOMAINS={
 "number":[0,1,-1,2,-2,5,10,0.5,-0.5,11],
 "integer":[0,1,-1,2,-2,5,10,17,-17,101],
 "text":[""," ","a","Ab"," a b ","x-y","ZX","123","a  b","\tAlpha\nBeta"],
 "boolean":[False,True]}
_EXACT=frozenset({"schema","language","goal","exportName","argTypes","oracle","maxCases"})
_OPERATION=re.compile(r"OC-[a-f0-9]{16}\Z")
_MAX_SRC=24000

def _strict_json(data):
    def disallow(x):
        raise ValueError("CONTRACT_NON_FINITE_LITERAL:"+x)
    return json.loads(data.decode("utf-8-sig"),parse_constant=disallow)

def _input(root,path):
    parent=Path(root).resolve()/"ENTRADAS"
    q=Path(path)
    if (not q.is_file() or q.is_symlink() or q.suffix.lower()!=".json" or
        q.resolve().parent!=parent.resolve() or q.stat().st_size>_MAX_SRC):
        raise ValueError("CONTRACT_REQUIRE_SINGLE_OWNER_JSON_IN_ENTRADAS")
    return q

def _number(value):
    if type(value) not in (float,int) or not math.isfinite(value) or abs(value)>_LIMIT:
        raise ValueError("CONTRACT_NUMERIC_DOMAIN_OR_OVERFLOW")
    return value

def _text(value):
    if type(value) is not str or len(value)>500 or "\x00" in value:
        raise ValueError("CONTRACT_STRING_DOMAIN_INVALID")
    return value

def _result(value):
    if value is None:
        raise ValueError("CONTRACT_UNDEFINED_RESULT")
    if type(value) in (float,int):
        value=_number(value)
        if type(value) is float and value.is_integer():
            return int(value)
        return value
    if type(value) is str:
        return _text(value)
    if type(value) is bool:
        return value
    raise ValueError("CONTRACT_NON_SCALAR_RESULT_FORBIDDEN")

def _safe_node(node,argtypes,depth=0,counter=None):
    if counter is None:counter=[0]
    counter[0]+=1
    if depth>12 or counter[0]>120:
        raise ValueError("CONTRACT_AST_DEPTH_OR_NODE_LIMIT")
    if not isinstance(node,dict) or type(node.get("op")) is not str:
        raise ValueError("CONTRACT_NODE_MUST_BE_DECLARATIVE_OBJECT")
    op=node["op"]
    if op=="arg":
        if set(node)!={"op","index"} or type(node["index"]) is not int or not 0<=node["index"]<len(argtypes):
            raise ValueError("CONTRACT_ARG_INDEX_INVALID")
        return
    if op=="const":
        if set(node)!={"op","value"}:
            raise ValueError("CONTRACT_CONST_FORMAT")
        _result(node["value"])
        return
    if set(node)!={"op","args"} or not isinstance(node["args"],list):
        raise ValueError("CONTRACT_AST_OPERATION_ARGUMENTS_REQUIRED")
    n=len(node["args"])
    if (op in _SINGLE and n!=1 or op in _BINARY and n!=2 or
        op in _THREE and n!=3 or op in _NARY and not 2<=n<=5 or
        op not in _SINGLE|_BINARY|_THREE|_NARY):
        raise ValueError("CONTRACT_AST_UNSUPPORTED_OPERATOR_OR_ARITY:"+op)
    for child in node["args"]:
        _safe_node(child,argtypes,depth+1,counter)

def _evaluate(node,values):
    op=node["op"]
    if op=="arg":
        return values[node["index"]]
    if op=="const":
        return node["value"]
    # Intentional eager evaluation even for if/and/or, bounded no side effects.
    v=[_evaluate(child,values) for child in node["args"]]
    if op=="add":return _result(sum(_number(x) for x in v))
    if op=="mul":
        x=1
        for n in v:x=_number(x*_number(n))
        return _result(x)
    if op=="sub":return _result(_number(v[0])-_number(v[1]))
    if op=="div":
        y=_number(v[1])
        if y==0:raise ValueError("CONTRACT_DIVISION_BY_ZERO_IN_OWNER_DOMAIN")
        return _result(_number(v[0])/y)
    if op=="abs":return _result(abs(_number(v[0])))
    if op=="floor":return _result(math.floor(_number(v[0])))
    if op=="ceil":return _result(math.ceil(_number(v[0])))
    if op=="nonnegative":return _result(max(0,_number(v[0])))
    if op=="min":return _result(min(_number(x) for x in v))
    if op=="max":return _result(max(_number(x) for x in v))
    if op=="clamp":
        lo,hi=_number(v[1]),_number(v[2])
        if lo>hi:raise ValueError("CONTRACT_CLAMP_BAD_LIMITS")
        return _result(max(lo,min(hi,_number(v[0]))))
    if op in ("eq","lt","lte","gt","gte"):
        if op=="eq":return v[0]==v[1] and type(v[0]) is type(v[1])
        a,b=_number(v[0]),_number(v[1])
        return {"lt":a<b,"lte":a<=b,"gt":a>b,"gte":a>=b}[op]
    if op=="if":
        if type(v[0]) is not bool:raise ValueError("CONTRACT_IF_REQUIRES_BOOLEAN_CONDITION")
        return _result(v[1] if v[0] else v[2])
    if op=="and":
        if any(type(x) is not bool for x in v):raise ValueError("CONTRACT_AND_BOOLEAN_ONLY")
        return all(v)
    if op=="or":
        if any(type(x) is not bool for x in v):raise ValueError("CONTRACT_OR_BOOLEAN_ONLY")
        return any(v)
    if op=="not":
        if type(v[0]) is not bool:raise ValueError("CONTRACT_NOT_BOOLEAN_ONLY")
        return not v[0]
    if op=="trim":return _text(_text(v[0]).strip())
    if op=="upper":return _text(_text(v[0]).upper())
    if op=="lower":return _text(_text(v[0]).lower())
    if op=="collapse_space_hyphen":return _text("-".join(_text(v[0]).split()))
    if op=="length":return _result(len(_text(v[0])))
    if op=="string":
        if type(v[0]) not in (str,int,float,bool):raise ValueError("CONTRACT_STRING_CAST_UNSUPPORTED")
        return _text(str(v[0]))
    if op=="concat":return _text("".join(_text(x) for x in v))
    raise ValueError("CONTRACT_AST_OPERATION_NOT_IMPLEMENTED")

def _make_cases(spec):
    types=spec["argTypes"]
    total=math.prod(len(_DOMAINS[t]) for t in types)
    maxcount=min(spec["maxCases"],total)
    if maxcount<5:
        raise ValueError("CONTRACT_ORACLE_NEEDS_AT_LEAST_FIVE_INDEPENDENT_INPUTS")
    # Deterministic even spacing of independent first-party domains; no
    # model-generated test inputs, expected outputs or random entropy.
    allinputs=list(itertools.product(*(_DOMAINS[t] for t in types)))
    indexes=[i*(total-1)//(maxcount-1) for i in range(maxcount)]
    if len(set(indexes))!=maxcount:
        raise RuntimeError("CONTRACT_FIXED_DOMAIN_DIVERSITY_FAILURE")
    cases=[]
    for i in indexes:
        args=list(allinputs[i])
        value=_result(_evaluate(spec["oracle"],args))
        cases.append({"args":args,"expected":value})
    if len({json.dumps(c["args"],sort_keys=True) for c in cases})<5:
        raise ValueError("CONTRACT_INDEPENDENT_INPUT_DIVERSITY_LOW")
    return cases

def _prepare(root,path):
    candidate=_input(root,path)
    original=candidate.read_bytes()
    obj=_strict_json(original)
    if not isinstance(obj,dict) or set(obj)!=_EXACT:
        raise ValueError("CONTRACT_SCHEMA_KEYS_MISMATCH")
    if obj["schema"]!=1 or obj["language"]!="javascript":
        raise ValueError("CONTRACT_REQUIRES_JS_ESM")
    if type(obj["goal"]) is not str or not 24<=len(obj["goal"])<=4000 or "\x00" in obj["goal"]:
        raise ValueError("CONTRACT_GOAL_LENGTH_OR_CHARACTER_INVALID")
    if type(obj["exportName"]) is not str or not open_orders._IDENTIFIER.fullmatch(obj["exportName"]):
        raise ValueError("CONTRACT_EXPORT_IDENTIFIER_INVALID")
    types=obj["argTypes"]
    if not isinstance(types,list) or not 1<=len(types)<=3 or any(type(t) is not str or t not in _TYPES for t in types):
        raise ValueError("CONTRACT_ARGUMENT_TYPES_REQUIRE_ONE_TO_THREE")
    if type(obj["maxCases"]) is not int or not 5<=obj["maxCases"]<=80:
        raise ValueError("CONTRACT_CASE_LIMIT_INVALID")
    _safe_node(obj["oracle"],types)
    derived={"schema":1,"language":"javascript","goal":obj["goal"],
             "exportName":obj["exportName"],"acceptance":_make_cases(obj)}
    generated=json_bytes(derived)
    if len(generated)>_MAX_SRC:
        raise ValueError("CONTRACT_DERIVED_OWNER_TEST_FILE_TOO_LARGE")
    # Use original source hash to isolate different owner contracts, even if
    # two independently authored DSLs happen to generate same example set.
    contract_sha=sha_bytes(original)
    oid="OC-"+contract_sha[:16]
    target=Path(root).resolve()/"ENTRADAS"/("owner_contract_"+contract_sha[:16]+".json")
    # Original factory preflight is not run until all owner evidence is frozen.
    return {"contractId":oid,"contractSha":contract_sha,
       "source":str(candidate),"derivedPath":str(target),"derivedSha":sha_bytes(generated),
       "derivedBytes":generated,"ownerCaseCount":len(derived["acceptance"]),
       "previewCases":derived["acceptance"][:5],
       "evaluatorSha":sha_file(Path(__file__)),
       "workOrderId":"OJ-"+sha_bytes(generated)[:16],
       "ownerAuthoredOracle":True,"modelGeneratedAcceptance":False,
       "status":"OWNER_DECLARATIVE_ORACLE_COMPILED_READ_ONLY"}

def preview(root,path):
    r=_prepare(root,path)
    return {k:v for k,v in r.items() if k!="derivedBytes"}

def _folder(root,identifier):
    if not isinstance(identifier,str) or not _OPERATION.fullmatch(identifier):
        raise ValueError("CONTRACT_ID_INVALID")
    return Path(root).resolve()/"contractorders"/identifier

def status(root,identifier):
    d=_folder(root,identifier)
    if not d.exists():return {"contractId":identifier,"status":"NOT_SUBMITTED"}
    i=d/"intent.json"
    if not i.is_file():return {"contractId":identifier,"status":"UNKNOWN_PARTIAL_INTENT_NO_REPLAY"}
    obj=load(i)
    if (sha_file(Path(obj["contractPath"]))!=obj["contractSha"] or
        sha_file(Path(obj["derivedPath"]))!=obj["derivedSha"]):
        raise RuntimeError("CONTRACT_ORIGINAL_INPUT_DRIFT_NO_REPLAY")
    verify_journal(d/"journal.jsonl")
    result={"contractId":identifier,"status":"OWNER_CONTRACT_FROZEN",
            "derivedSha":obj["derivedSha"],"workOrderId":obj["workOrderId"],
            "ownerCaseCount":obj["ownerCaseCount"],"canBlindRetry":False}
    if not (d/"submission.json").is_file():
        result["status"]="UNKNOWN_ORIGINAL_SUBMISSION_RECONCILE_NO_REPLAY"
        result["originalReadback"]=open_orders.status(root,obj["workOrderId"])
        return result
    result["original"]=open_orders.status(root,obj["workOrderId"])
    result["status"]="CONTRACT_"+result["original"]["status"]
    return result

def submit(root,path,*,provider="cuda7b",acceptance_mode="wasi-browser"):
    root=engine.init(root)
    checked=_prepare(root,path)
    if provider not in open_orders._ALLOWED_PROVIDERS or acceptance_mode not in ("wasi-native","wasi-browser"):
        raise ValueError("CONTRACT_PROVIDER_OR_MODE_NOT_PINNED")
    dest=_folder(root,checked["contractId"])
    if dest.exists():return status(root,checked["contractId"])
    original_file=Path(checked["source"])
    derived=Path(checked["derivedPath"])
    if derived.exists() or derived.is_symlink():
        return {"status":"UNKNOWN_DERIVED_FILE_PREEXISTS_NO_REPLAY","contractId":checked["contractId"]}
    repo_graph.preflight(root)
    if sha_file(original_file)!=checked["contractSha"] or sha_file(Path(__file__))!=checked["evaluatorSha"]:
        raise RuntimeError("CONTRACT_PREINTENT_OWNER_OR_EVALUATOR_DRIFT")
    dest.mkdir(parents=True,exist_ok=False)
    (dest/"history").mkdir(exist_ok=False)
    write(derived,checked["derivedBytes"],new=True)
    if sha_file(derived)!=checked["derivedSha"]:
        raise RuntimeError("CONTRACT_PREMODEL_DERIVED_SHA_READBACK_FAILED")
    intent={"schema":1,"atUtc":utc(),"contractId":checked["contractId"],
            "operationId":checked["contractId"]+".OWNER-ORACLE-FACTORY.ONCE",
            "contractPath":str(original_file),"contractSha":checked["contractSha"],
            "derivedPath":str(derived),"derivedSha":checked["derivedSha"],
            "ownerCaseCount":checked["ownerCaseCount"],
            "evaluatorSha":checked["evaluatorSha"],
            "workOrderId":checked["workOrderId"],
            "provider":provider,"acceptanceMode":acceptance_mode,
            "oracleSource":"OWNER_DECLARATIVE_DSL_NOT_LOCAL_AI",
            "originalFactoryOwner":"ORIGINAL_SUPERVISOR",
            "protectedHostInstallAllowed":False}
    write_json(dest/"intent.json",intent,new=True)
    event(dest/"journal.jsonl","ORIGINAL_OWNER_DSL_AND_CASES_FROZEN",
          {"contractSha":checked["contractSha"],"derivedSha":checked["derivedSha"],
           "evaluatorSha":checked["evaluatorSha"],"cases":checked["ownerCaseCount"]})
    # Never retry partial/UNKNOWN. Existing status() is the sole reconciliation.
    answer=open_orders.submit(root,derived,provider=provider,acceptance_mode=acceptance_mode)
    write_json(dest/"submission.json",{"schema":1,"atUtc":utc(),"result":answer,
               "originalIntentSha":sha_file(dest/"intent.json")},new=True)
    event(dest/"journal.jsonl","OWNER_DECLARATIVE_ORACLE_DISPATCH_ONCE",
          {"originalSubmissionSha":sha_file(dest/"submission.json"),
           "originalWorkOrderId":checked["workOrderId"]})
    return {"status":"SUBMITTED_ONCE_TO_ORIGINAL_SUPERVISOR",
            "contractId":checked["contractId"],"derivedSha":checked["derivedSha"],
            "ownerCaseCount":checked["ownerCaseCount"],
            "original":answer}
