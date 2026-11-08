# coding: utf-8
"""One user goal -> original local AI/software factory, independently accepted.

Trust boundary: the model can design/repair code, but the decision to accept
it must originate from user tests or an independent first-party reference.
A strictly recognized small domain of FULL natural-language sentences can
be compiled into an independent reference WITHOUT human authoring test cases.
Unrecognized, compound, contradictory, risky or ambiguous goals BLOCK.
No parallel factory, unbounded executors, unsafe code, or false universal PASS.

The original repo_factory does up to 3 model+compile+WASI repair attempts.
The original factory_pipeline then runs independent offline Chrome and delivers.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import re
import unicodedata
from pathlib import Path

from . import engine, open_orders, owner_oracles, repo_graph, supervisor
from .storage import event, json_bytes, load, sha_bytes, sha_file, utc, verify_journal, write, write_json

_GOAL_ID = re.compile(r"AG-[0-9a-f]{16}\Z")
_MAX_BYTES = 4200
_MAX_CASES = 80

def _arg(i):
    return {"op":"arg","index":i}

def _const(x):
    return {"op":"const","value":x}

def _expr(op,*args):
    return {"op":op,"args":list(args)}

_NUMERIC = (
    -100,-50,-25,-11,-10,-5,-3,-2,-1,-0.5,0,0.5,1,2,3,4,5,7,8,9,
    10,11,12,17,20,25,50,99,100,101,150,300,0.25,1.5
)
_INTEGERS = (-100,-25,-10,-5,-2,-1,0,1,2,3,5,7,9,10,20,50,100,101)
_STRINGS = (
    ""," ","a","Ab","X-Y","007"," caja  12 "," A  B ","hello"," HOLA ",
    "a-b  c","a  b","\tA B","X\tY","abc\nxyz"," abc  ","ñ","AAA   BBB",
    "  0001   LOTE ","a_b c","A 9","  x-y z  ","ref  14"," CAJA\tDOS ",
    "\t","qwerty","123  456","  U  N  O   "," CAJA-8 ","R  5"," A \n B "
)

# Only complete, explicitly unambiguous input sentences are authorized.
# The original goal can be phrased in Spanish or English with limited aliases.
# Matching never merely scans for a keyword inside a larger instruction.
_PATTERNS = (
    ("triple",re.compile(
        r"(?:crea (?:un programa|una funcion) local (?:que )?)?"
        r"(?:calcula|calcular|calcule) el triple de un numero")),
    ("double",re.compile(
        r"(?:crea (?:un programa|una funcion) local (?:que )?)?"
        r"(?:calcula|calcular|calcule) el doble de un numero")),
    ("absolute",re.compile(
        r"(?:crea (?:un programa|una funcion) local (?:que )?)?"
        r"(?:calcula|calcular|calcule) el valor absoluto de un numero")),
    ("uppercase",re.compile(
        r"(?:crea (?:un programa|una funcion) local (?:que )?)?"
        r"(?:convierte|convertir) (?:un )?texto a mayusculas")),
    ("normalize",re.compile(
        r"(?:crea (?:un programa|una funcion) local (?:que )?)?"
        r"(?:normaliza|normalizar) codigos de envio")),
    ("total",re.compile(
        r"(?:crea (?:un programa|una funcion) local (?:que )?)?"
        r"(?:calcula|calcular|calcule) el total de (?:un )?pedido "
        r"(?:multiplicando )?precio por unidades "
        r"(?:con negativos a cero y maximo 100|sin negativos y maximo 100)")),
    ("triple",re.compile(
        r"(?:create (?:a )?local (?:program|function) (?:that )?)?"
        r"(?:calculate|compute) the triple of a number")),
    ("uppercase",re.compile(
        r"(?:create (?:a )?local (?:program|function) (?:that )?)?"
        r"(?:convert|converts) text to uppercase"))
)

def _normalized_goal(text):
    if type(text) is not str or "\x00" in text or len(text)>3800:
        raise ValueError("AUTOGOAL_TEXT_OUTSIDE_BOUNDS")
    # Unicode accents, case and outer punctuation may vary; inner clauses may not.
    text=unicodedata.normalize("NFKD",text).casefold()
    text="".join(c for c in text if not unicodedata.combining(c))
    text=" ".join(text.strip().split())
    return text.strip(" .!?¡¿")

def _source(root,path):
    root=Path(root).resolve()
    folder=root/"ENTRADAS"
    item=Path(path)
    if (not item.is_file() or item.is_symlink() or
        item.resolve().parent!=folder.resolve() or
        item.suffix.lower()!=".txt" or
        not 24<=item.stat().st_size<=_MAX_BYTES):
        raise ValueError("AUTOGOAL_REQUIRE_USER_TXT_IN_ENTRADAS")
    data=item.read_bytes()
    try:goal=data.decode("utf-8-sig").strip()
    except UnicodeError as err:raise ValueError("AUTOGOAL_NOT_UTF8") from err
    if len(data)>_MAX_BYTES or not 24<=len(goal)<=3800 or "\x00" in goal:
        raise ValueError("AUTOGOAL_GOAL_BAD")
    return item,data,goal

def _recognized(text):
    norm=_normalized_goal(text)
    hits={name for name,pattern in _PATTERNS if pattern.fullmatch(norm)}
    if len(hits)!=1:
        return None
    return next(iter(hits))

def _definition(kind):
    if kind=="triple":
        return ("calculateTriple",["number"],_expr("mul",_arg(0),_const(3)),
                "Given one finite number, return precisely its product times 3. Negative numbers and decimals are valid.")
    if kind=="double":
        return ("calculateDouble",["number"],_expr("mul",_arg(0),_const(2)),
                "Given one finite number, return precisely its product times 2. Negative numbers and decimals are valid.")
    if kind=="absolute":
        return ("calculateAbsolute",["number"],_expr("abs",_arg(0)),
                "Given one finite number, return its nonnegative absolute value. Support negatives, zero and fractions.")
    if kind=="uppercase":
        return ("convertUppercase",["text"],_expr("upper",_arg(0)),
                "Given a string return the same text in uppercase without trimming, collapsing or changing spaces.")
    if kind=="normalize":
        return ("normalizeShipmentCode",["text"],
                _expr("upper",_expr("collapse_space_hyphen",_expr("trim",_arg(0)))),
                "Given one shipment code string, strip surrounding whitespace, replace each internal whitespace run with one ASCII hyphen, then uppercase all letters. Preserve other punctuation; blanks become empty.")
    if kind=="total":
        a=_expr("nonnegative",_arg(0))
        b=_expr("nonnegative",_arg(1))
        return ("calculateOrderTotal",["number","integer"],
                _expr("clamp",_expr("mul",a,b),_const(0),_const(100)),
                "Given price and integer units: replace each negative with zero, multiply price by units, then clamp total to [0, 100]. Return numeric output.")
    raise ValueError("AUTOGOAL_UNSUPPORTED_RECIPE")

def _cases(types,oracle):
    # Inputs originate from a vetted source catalog, not the code-producing AI.
    if types==["text"]:
        candidates=[(v,) for v in _STRINGS]
    elif types==["number"]:
        candidates=[(v,) for v in _NUMERIC]
    elif types==["number","integer"]:
        candidates=list(itertools.product(_NUMERIC,_INTEGERS))
        indexes=[i*(len(candidates)-1)//(_MAX_CASES-1) for i in range(_MAX_CASES)]
        candidates=[candidates[i] for i in indexes]
        # We require boundary cases for each argument, including zero/negative.
        for c in ((-5,7),(5,-7),(0,5),(5,0),(2,10),(10,50),
                  (100,1),(100,2),(0.5,5),(-1,-1),(100,100)):
            if c not in candidates:
                candidates.append(c)
        if len(candidates)>_MAX_CASES:
            candidates=candidates[-_MAX_CASES:]
    else:
        raise RuntimeError("AUTOGOAL_CASE_GENERATOR_NOT_VETTED")
    if not 5<=len(candidates)<=_MAX_CASES:
        raise RuntimeError("AUTOGOAL_OWNER_CASE_COUNT_INVALID")
    result=[]
    seen=set()
    for args in candidates:
        raw=json.dumps(args,ensure_ascii=False)
        if raw in seen:continue
        seen.add(raw)
        output=owner_oracles._result(owner_oracles._evaluate(oracle,list(args)))
        result.append({"args":list(args),"expected":output})
    if len(result)<5:
        raise RuntimeError("AUTOGOAL_OWNER_EXAMPLES_NOT_DIVERSE")
    return result

def _compile(goal):
    kind=_recognized(goal)
    if not kind:
        return {"status":"BLOCKED_UNRECOGNIZED_GOAL_INDEPENDENT_ORACLE_MISSING",
                "reason":"This goal cannot be independently specified by the current verified natural-language recipe catalog. No model-self-approval; use AI proposal and independent review or provide owner acceptance.",
                "autoAccepted":False,"modelCalled":False}
    name,types,oracle,meaning=_definition(kind)
    cases=_cases(types,oracle)
    # Always freeze independent reference constraints, not just a model prompt.
    spec={"schema":1,"language":"javascript","exportName":name,
          "goal":meaning+" Input user request: "+goal,
          "acceptance":cases}
    return {"status":"INDEPENDENT_FIRST_PARTY_RECIPE_COMPILED",
            "recipe":kind,"spec":spec,"cases":len(cases),
            "catalogRule":"TRUSTED_STATIC_FIRST_PARTY_NOT_MODEL",
            "semanticCoverage":"FULL_EXACT_PHRASE_ONLY",
            "autoAccepted":True,"modelCalled":False}

def _id(original):
    return "AG-"+sha_bytes(original)[:16]

def _folder(root,identity):
    if not isinstance(identity,str) or not _GOAL_ID.fullmatch(identity):
        raise ValueError("AUTOGOAL_ID_INVALID")
    return Path(root).resolve()/"autogoals"/identity

def preview(root,path):
    file,blob,goal=_source(root,path)
    row=_compile(goal)
    base={"goalId":_id(blob),"originalGoalSHA":sha_bytes(blob),"originalGoalPath":str(file),
          "goal":goal,"requiresHumanGeneratedTests":False}
    if row["status"].startswith("BLOCKED"):
        return {**base,**row}
    candidate=json_bytes(row["spec"])
    if len(candidate)>24000:
        raise ValueError("AUTOGOAL_ORIGINAL_OWNER_SPEC_TOO_LARGE")
    return {**base,"status":row["status"],"recipe":row["recipe"],
            "verifiedSemanticsScope":row["semanticCoverage"],
            "independentCases":row["cases"],
            "originalOwnerSpecSHA":sha_bytes(candidate),
            "noModelCreatedCriteria":True,"reviewRequired":False,
            "originalFunction":row["spec"]["exportName"]}

def status(root,identity):
    root=Path(root).resolve()
    folder=_folder(root,identity)
    if not folder.exists():
        return {"goalId":identity,"status":"NOT_SUBMITTED"}
    if not (folder/"intent.json").is_file():
        return {"goalId":identity,"status":"UNKNOWN_PARTIAL_PREINTENT_DO_NOT_RESUBMIT"}
    intent=load(folder/"intent.json")
    if (sha_file(Path(intent["originalGoalPath"]))!=intent["originalGoalSHA"] or
        sha_file(Path(intent["derivedOwnerPath"]))!=intent["derivedOwnerSHA"]):
        raise RuntimeError("AUTOGOAL_ORIGINAL_INPUT_SHA_DRIFT")
    verify_journal(folder/"journal.jsonl")
    result={"goalId":identity,"status":"FROZEN_FIRST_PARTY_ORACLE",
            "originalGoalSHA":intent["originalGoalSHA"],
            "recipe":intent["recipe"],"independentCases":intent["independentCases"],
            "derivedOwnerSHA":intent["derivedOwnerSHA"],
            "independentFromCodeModel":True,"blindRetryAllowed":False}
    if not (folder/"submission.json").is_file():
        result["status"]="UNKNOWN_ORIGINAL_SUBMISSION_RECONCILE_NO_REPLAY"
        return result
    origin=load(folder/"submission.json")["original"]
    result["originalJobId"]=intent["originalJobId"]
    result["original"]=open_orders.status(root,intent["originalJobId"])
    status_now=result["original"]["status"]
    result["status"]="AUTO_"+status_now
    if result["original"].get("portableProgram",{}).get("verified") is True:
        result["verifiedPortableProgram"]=result["original"]["portableProgram"]
    return result

def submit(root,path,*,provider="cuda7b"):
    root=engine.init(root)
    checked=preview(root,path)
    if checked["status"].startswith("BLOCKED"):
        return checked
    if provider not in open_orders._ALLOWED_PROVIDERS:
        raise ValueError("AUTOGOAL_UNPINNED_MODEL_PROVIDER")
    folder=_folder(root,checked["goalId"])
    if folder.exists():
        return status(root,checked["goalId"])
    worker=supervisor.status(root)
    if (worker["status"]!="RUNNING" or
        not worker["processIdentityBirthVerified"] or
        worker["control"]["command"]!="RUN"):
        raise RuntimeError("AUTOGOAL_ORIGINAL_SUPERVISOR_NOT_READY")
    if worker["pendingQueue"]:
        return {**checked,"status":"BLOCKED_ORIGINAL_QUEUE_BUSY_NO_EFFECT"}
    repo_graph.preflight(root)
    source,original,goal=_source(root,path)
    if sha_bytes(original)!=checked["originalGoalSHA"]:
        raise RuntimeError("AUTOGOAL_GOAL_CAS_CHANGED")
    prepared=_compile(goal)
    if prepared["status"]!="INDEPENDENT_FIRST_PARTY_RECIPE_COMPILED":
        raise RuntimeError("AUTOGOAL_RECIPE_CHANGED_BEFORE_INTENT")
    contents=json_bytes(prepared["spec"])
    if sha_bytes(contents)!=checked["originalOwnerSpecSHA"]:
        raise RuntimeError("AUTOGOAL_ORACLE_CAS_CHANGED")
    suffix=checked["goalId"][3:]
    derived=root/"ENTRADAS"/("autogoal_independent_"+suffix+".json")
    if derived.exists() or derived.is_symlink():
        return {**checked,"status":"UNKNOWN_DERIVED_ORIGINAL_OWNER_SPEC_PREEXISTS"}
    folder.mkdir(parents=True,exist_ok=False)
    (folder/"history").mkdir(exist_ok=False)
    write(derived,contents,new=True)
    if sha_file(derived)!=sha_bytes(contents):
        raise RuntimeError("AUTOGOAL_FROZEN_ORIGINAL_CASES_SHA_FAILED")
    # Independent acceptance is locked BEFORE any agent receives its task.
    frozen=open_orders.preview(root,derived)
    if (frozen["status"]!="FROZEN_OWNER_INPUT_READY" or
        frozen["originalOwnerCases"]!=checked["independentCases"]):
        raise RuntimeError("AUTOGOAL_ORIGINAL_INTAKE_DISAGREES_WITH_CATALOG")
    intent={
       "schema":1,"atUtc":utc(),
       "operationId":checked["goalId"]+".LOCAL-INTERNAL-AGENTS.ONCE",
       "goalId":checked["goalId"],
       "originalGoalPath":str(source),
       "originalGoalSHA":checked["originalGoalSHA"],
       "derivedOwnerPath":str(derived),
       "derivedOwnerSHA":checked["originalOwnerSpecSHA"],
       "originalJobId":frozen["jobId"],
       "independentCases":checked["independentCases"],
       "recipe":prepared["recipe"],
       "originalCatalogSHA":sha_file(Path(__file__)),
       "independentReferenceSource":"FIRST_PARTY_PINNED_EXACT_SEMANTIC_RECIPE",
       "modelDidNotCreateTests":True,
       "originalSupervisorOnly":True,
       "originalAcceptanceMode":"wasi-browser",
       "modelProvider":provider,
       "hostInstallationAuthorized":False,
       "generalPurposeJobAcceptance":False
    }
    write_json(folder/"intent.json",intent,new=True)
    event(folder/"journal.jsonl","INDEPENDENT_EXACT_OWNER_RECIPE_FROZEN",
          {"originalGoalSHA":intent["originalGoalSHA"],
           "originalIndependentSpecSHA":intent["derivedOwnerSHA"],
           "referenceCatalogSHA":intent["originalCatalogSHA"],
           "originalJobId":intent["originalJobId"],
           "cases":intent["independentCases"]})
    # A lost connection after this call is UNKNOWN. Never repeat this ID.
    dispatched=open_orders.submit(root,derived,provider=provider,
                                  acceptance_mode="wasi-browser")
    write_json(folder/"submission.json",{"schema":1,"atUtc":utc(),
        "original":dispatched,"originalIntentSHA":sha_file(folder/"intent.json")},new=True)
    event(folder/"journal.jsonl","ORIGINAL_INTERNAL_GPU_AGENTS_DISPATCHED_ONCE",
          {"originalSubmissionSHA":sha_file(folder/"submission.json"),
           "originalJobId":intent["originalJobId"]})
    return {"status":"AUTO_SUBMITTED_TO_ORIGINAL_LOCAL_FACTORY",
            "goalId":checked["goalId"],"originalJobId":intent["originalJobId"],
            "independentCases":intent["independentCases"],
            "modelDidNotMakeAcceptance":True,
            "original":dispatched}
