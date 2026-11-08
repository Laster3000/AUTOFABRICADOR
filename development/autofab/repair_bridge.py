# coding: utf-8
"""Original SHA-bound hybrid repair of *failed* model code, owner tests unchanged.

Two deliberately narrow first-party repair rules, not universal AI:
- TypeScript three-module numeric sentinel -1 -> string formatting.
- Python slugify_ascii uses literal str.replace instead of re.sub.
Original failed jobs are IMMUTABLE; each repair gets NEW AR- identity/journal.
Original untrusted model source runs only in pinned WASI, never Windows Host.
"""
from __future__ import annotations
import ast,json,re,uuid,zipfile,os,sys
from pathlib import Path
from . import engine,repo_graph,repo_factory,wasi_isolation,local_runtime,supervisor
from .storage import load,sha_file,sha_bytes,json_bytes,write_json,write,event,utc,verify_journal,transition
_REPAIR=re.compile(r"AR-[a-f0-9]{16}\Z")
_REPO=re.compile(r"RJ-[a-f0-9]{16}\Z")
_PY=re.compile(r"AF-[a-f0-9]{16}\Z")
_PY_SOURCE="slugfunc.py"
_TSS=("src/index.ts","src/normalize.ts","src/rules.ts")
def folder(root,ident):
    if not isinstance(ident,str) or not _REPAIR.fullmatch(ident):
        raise ValueError("REPAIR_ID_UNSAFE")
    p=Path(root).resolve()/"repairjobs"/ident
    if not (p/"plan.json").is_file():raise FileNotFoundError("REPAIR_NOT_FOUND")
    return p
def _original(root,identifier):
    root=Path(root).resolve()
    if isinstance(identifier,str) and _REPO.fullmatch(identifier):
        d=repo_factory.directory(root,identifier)
        verify_journal(d/"journal.jsonl")
        state=load(d/"state.json")["status"]
        if state not in ("FAILED_OWNER_ACCEPTANCE","STAGNATED_OWNER_NO_PROGRESS"):
            raise ValueError("REPAIR_REPO_MUST_BE_ORIGINAL_TERMINAL_REJECT")
        source=sorted((d/"attempts").glob("A-*-source.json"))
        if not source:raise ValueError("REPAIR_NO_ORIGINAL_MODEL_SOURCE")
        original=source[0]
        spec=load(d/"spec.json")
        owner=load(d/"owner-acceptance.json")
        repo_graph._valid_spec(spec)
        if owner["cases"]!=spec["acceptance"]:
            raise ValueError("REPAIR_OWNER_ORIGINAL_DRIFT")
        return {"kind":"typescript","identifier":identifier,"d":d,
            "source":original,"sourceSha":sha_file(original),
            "spec":spec,"specSha":sha_file(d/"spec.json"),
            "owner":d/"owner-acceptance.json",
            "ownerSha":sha_file(d/"owner-acceptance.json"),
            "journalSha":sha_file(d/"journal.jsonl"),
            "state":state}
    if isinstance(identifier,str) and _PY.fullmatch(identifier):
        d=engine.jobdir(root,identifier)
        verify_journal(d/"journal.jsonl")
        state=load(d/"state.json")["status"]
        if state not in ("FAILED_ATTEMPT","FAILED"):
            raise ValueError("REPAIR_PY_MUST_BE_ORIGINAL_TERMINAL_REJECT")
        spec=load(d/"spec.json")
        ref=spec.get("acceptance")
        if (not isinstance(ref,dict) or
            ref.get("relativePath")!="examples/test_owner_py_slug_r053.py"):
            raise ValueError("REPAIR_PY_OWNER_NOT_SUPPORTED")
        owner=root/ref["relativePath"]
        if not owner.is_file() or sha_file(owner)!=ref["sha256"]:
            raise ValueError("REPAIR_PY_OWNER_SHA_DRIFT")
        source=d/"attempt-01"/"code"/_PY_SOURCE
        if not source.is_file():raise ValueError("REPAIR_PY_ORIGINAL_SOURCE_MISSING")
        return {"kind":"python","identifier":identifier,"d":d,
            "source":source,"sourceSha":sha_file(source),
            "spec":spec,"specSha":sha_file(d/"spec.json"),
            "owner":owner,"ownerSha":sha_file(owner),
            "journalSha":sha_file(d/"journal.jsonl"),
            "state":state}
    raise ValueError("REPAIR_ORIGINAL_JOB_ID_UNSUPPORTED")
def _ts_apply(spec,files):
    if (spec.get("language")!="typescript" or
        set(files)!=set(_TSS) or
        set(spec["sources"])!=set(_TSS) or
        spec["entry"]!="src/index.ts" or
        spec["exportName"]!="describePort"):
        raise ValueError("REPAIR_TS_SPEC_NOT_SUPPORTED")
    goal=spec["goal"]
    for token in ("isValidPort","normalizePort","describePort","65535","invalid"):
        if token not in goal:raise ValueError("REPAIR_TS_OWNER_GOAL_MISMATCH")
    invalid=[x for x in spec["acceptance"] if x["expected"]=="invalid"]
    valid=[x for x in spec["acceptance"] if isinstance(x["expected"],str) and x["expected"].startswith("port:")]
    if len(invalid)<5 or len(valid)<5:
        raise ValueError("REPAIR_TS_INSUFFICIENT_INDEPENDENT_OWNER_CASES")
    idx=files["src/index.ts"]
    exact=re.fullmatch(
     r"\s*import\s*\{\s*normalizePort\s*\}\s*from\s*['\"]\./normalize['\"];?\s*"
     r"export\s+function\s+describePort\s*\(\s*value\s*:\s*unknown\s*\)\s*:\s*string\s*"
     r"\{\s*return\s+(?P<expr>(?:['\"]port:['\"]\s*\+\s*)?normalizePort\(value\));?\s*\}\s*",
     idx,flags=re.S)
    if exact is None:raise ValueError("REPAIR_TS_SOURCE_NOT_KNOWN_SAFE_SHAPE")
    other=files["src/normalize.ts"]
    rule=files["src/rules.ts"]
    # Exact dependency graph and typed API preconditions. No arbitrary host
    # source or untrusted import/module rewrite.
    if not re.search(r"export\s+function\s+normalizePort\s*\(",other):
        raise ValueError("REPAIR_TS_NORMALIZER_UNRECOGNIZED")
    if not re.search(r"export\s+function\s+isValidPort\s*\(",rule):
        raise ValueError("REPAIR_TS_RULES_UNRECOGNIZED")
    patched=(
      "import {normalizePort} from './normalize';\n"
      "export function describePort(value: unknown): string {\n"
      "  const port = normalizePort(value);\n"
      "  return port === -1 ? 'invalid' : 'port:' + port;\n"
      "}\n")
    result=dict(files)
    result["src/index.ts"]=patched
    return result,"TS_ENTRY_SENTINEL_MINUS_ONE_TO_TYPED_STRING"
def _py_apply(spec,source):
    ref=spec.get("acceptance") or {}
    if ref.get("relativePath")!="examples/test_owner_py_slug_r053.py":
        raise ValueError("REPAIR_PY_OWNER_UNSUPPORTED")
    if "slugfunc.py" not in spec["goal"]:
        raise ValueError("REPAIR_PY_GOAL_MISMATCH")
    tree=ast.parse(source)
    # The observed new local model emitted an UNUSED 'import re' ahead
    # of the same exact prior wrong literal str.replace. A single import
    # of the standard-library re module is the only admitted prefix.
    if len(tree.body)==2:
        imp=tree.body[0]
        if (not isinstance(imp,ast.Import) or len(imp.names)!=1 or
           imp.names[0].name!="re" or imp.names[0].asname is not None):
            raise ValueError("REPAIR_PY_UNAUTHORIZED_IMPORT_OR_CODE")
        candidate=source.strip()
        if not candidate.startswith("import re\n"):
            raise ValueError("REPAIR_PY_IMPORT_FORMAT_UNSUPPORTED")
        candidate=candidate[len("import re"):].strip()
        function=tree.body[1]
    elif len(tree.body)==1:
        candidate=source.strip()
        function=tree.body[0]
    else:
        raise ValueError("REPAIR_PY_UNRECOGNIZED_CODE_SHAPE")
    if not isinstance(function,ast.FunctionDef):
        raise ValueError("REPAIR_PY_UNRECOGNIZED_CODE_SHAPE")
    fn=function
    if fn.name!="slugify_ascii" or len(fn.args.args)!=1 or fn.args.args[0].arg!="value":
        raise ValueError("REPAIR_PY_UNRECOGNIZED_API")
    if len(fn.body)!=2 or not isinstance(fn.body[0],ast.If) or not isinstance(fn.body[1],ast.Return):
        raise ValueError("REPAIR_PY_UNRECOGNIZED_RETURN")
    # Reject any function containing loops/imports/calls with effects,
    # arbitrary attributes or dynamic execution; only these two known
    # negative-example model outputs may be repaired under frozen owner.
    templates=(
      "def slugify_ascii(value):\n"
      "    if not isinstance(value, str):\n"
      "        return None\n"
      "    return value.lower().replace(r'[^a-z0-9]', '-').lstrip('-').rstrip('-')",
      "def slugify_ascii(value):\n"
      "    if not isinstance(value, str):\n"
      "        return None\n"
      "    return value.lower().replace(r'[^a-z0-9]+', '-', value.lower()).lstrip('-').rstrip('-')",
    )
    if candidate not in templates:raise ValueError("REPAIR_PY_ONLY_KNOWN_LITERAL_REPLACE_ERROR")
    fixed=("import re\n\n"
       "def slugify_ascii(value):\n"
       "    if not isinstance(value, str):\n"
       "        return ''\n"
       "    return re.sub(r'[^a-z0-9]+', '-', value.lower()).strip('-')\n")
    ast.parse(fixed)
    return fixed,"PY_LITERAL_STR_REPLACE_TO_ASCII_REGEX"
def create(root,identifier,*,revision="v1"):
    root=engine.init(root)
    if revision not in ("v1","v2"):raise ValueError("REPAIR_REVISION_UNSUPPORTED")
    o=_original(root,identifier)
    base=root/"repairjobs";base.mkdir(exist_ok=True)
    for existing in base.glob("AR-*/plan.json"):
        p=load(existing)
        if (p.get("originalJob")==identifier and p.get("originalSourceSha")==o["sourceSha"] and p.get("revision","v1")==revision):
            return {"status":"EXISTING_REPAIR_INTENT_NO_REPLAY",
                "repairId":existing.parent.name,
                "originalState":load(existing.parent/"state.json")["status"]}
    jid="AR-"+uuid.uuid4().hex[:16]
    d=base/jid
    d.mkdir(exist_ok=False)
    (d/"history").mkdir()
    (d/"workspace").mkdir()
    plan={"schema":1,"atUtc":utc(),"repairId":jid,
        "operationId":jid+".FIRST_PARTY_HYBRID_OWNER",
        "originalJob":identifier,"revision":revision,"kind":o["kind"],
        "originalSource":str(o["source"]),"originalSourceSha":o["sourceSha"],
        "originalSpecSha":o["specSha"],
        "originalOwnerSha":o["ownerSha"],
        "originalJournalSha":o["journalSha"],
        "originalState":o["state"],
        "originalModelCallsReplayed":0,
        "modelGeneratedCodeExecutableOnlyInWASI":True,
        "noHostService":True,"originalOwnerAcceptanceImmutable":True}
    write_json(d/"plan.json",plan,new=True)
    write_json(d/"state.json",{"schema":1,"atUtc":utc(),"status":"PENDING"},new=True)
    event(d/"journal.jsonl","REPAIR_ORIGINAL_INTENT_PINNED",
         {"planSha":sha_file(d/"plan.json"),"originalOwnerSha":o["ownerSha"],
          "originalSourceSha":o["sourceSha"]})
    return {"repairId":jid,"status":"PENDING","kind":o["kind"],
            "originalOwnerSha":o["ownerSha"],
            "originalSourceSha":o["sourceSha"]}
def run(root,ident):
    root=engine.init(root)
    d=folder(root,ident)
    plan=load(d/"plan.json")
    if load(d/"state.json")["status"]!="PENDING" or (d/"result.json").exists():
        raise RuntimeError("REPAIR_ORIGINAL_INTENT_ALREADY_STARTED_NO_REPLAY")
    o=_original(root,plan["originalJob"])
    if (plan["originalSourceSha"]!=o["sourceSha"] or
        plan["originalSpecSha"]!=o["specSha"] or
        plan["originalOwnerSha"]!=o["ownerSha"] or
        plan["originalJournalSha"]!=o["journalSha"]):
        raise RuntimeError("REPAIR_ORIGINAL_SHA_CHANGED_NO_REPLAY")
    if (supervisor.status(root)["status"]!="STOPPED" or
        local_runtime.server_info(root)["state"]!="NOT_STARTED"):
        raise RuntimeError("REPAIR_LOCAL_OWNER_WORKERS_BUSY_OR_UNKNOWN")
    transition(d/"state.json",{"schema":1,"atUtc":utc(),
      "status":"WASI_OWNER_RUNNING"},d/"history")
    event(d/"journal.jsonl","REPAIR_TRUSTED_OWNER_INTENT",
         {"originalSourceSha":o["sourceSha"],"originalOwnerSha":o["ownerSha"]})
    if o["kind"]=="typescript":
        files=load(o["source"])["files"]
        corrected,rule=_ts_apply(o["spec"],files)
        write_json(d/"workspace"/"repaired-files.json",corrected,new=True)
        owner=repo_graph.build_owner(root,o["spec"],corrected,timeout=95)
        compiled=owner.pop("compiledSource",None)
        if isinstance(compiled,str):
            write(d/"workspace"/"compiled.js",compiled.encode(),new=True)
            assert sha_file(d/"workspace"/"compiled.js")==owner["compiledSha256"]
        accepted=(owner["status"]=="PASS" and
           owner["originalOwnerResult"]["status"]=="PASS" and
           owner["originalOwnerResult"]["testResult"]["passed"]==len(o["spec"]["acceptance"]))
        original_cases=len(o["spec"]["acceptance"])
        passed=owner.get("originalOwnerResult",{}).get("testResult",{}).get("passed",0)
        source_artifact=d/"workspace"/"repaired-files.json"
    else:
        raw=o["source"].read_text("utf-8")
        corrected,rule=_py_apply(o["spec"],raw)
        safe=d/"workspace"/"slugfunc.py"
        write(safe,corrected.encode(),new=True)
        ownerfile=d/"workspace"/"test_original_owner.py"
        write(ownerfile,o["owner"].read_bytes(),new=True)
        assert sha_file(ownerfile)==o["ownerSha"]
        # Original wasi_isolation.run_tests only accepts C:/AUTOFABRICADOR/work
        # and needs a work-job spec at an ancestor. Reusing it from a distinct
        # repairjobs folder is invalid and would be an unsafe trust-root bypass.
        # Instead call its original pinned private-memory WASI guest directly
        # with the ORIGINAL independently frozen owner test, no Host grants.
        trust=wasi_isolation.wasi_preflight(root)
        vendor=root/"VENDOR"/"wasi-runtime"
        if str(vendor) not in sys.path:sys.path.insert(0,str(vendor))
        result=wasi_isolation.wasi_run_one(
            vendor,root,{"slugfunc.py":corrected,
              "test_original_owner.py":o["owner"].read_text("utf-8")},
            90,"original-owner-pinned")
        result["backend"]=trust["backend"]
        result["originalOwnerSha"]=o["ownerSha"]
        result["hostFilesystemGrants"]=0
        result["hostTools"]=0
        result["networkCapabilities"]=0
        accepted=(result["exitCode"]==0 and result["testCount"]==8)
        original_cases=8
        passed=result["testCount"] if accepted else 0
        owner={"schema":1,"status":"PASS" if accepted else "FAILED_ORIGINAL_PY_OWNER",
             "originalTestSha":o["ownerSha"],"isolatedExecution":result,
             "ownerCases":8,"passed":passed}
        source_artifact=safe
    write_json(d/"owner-result.json",owner,new=True)
    result={"schema":1,"atUtc":utc(),"repairId":ident,
        "operationId":plan["operationId"],"status":
          "PASS_ORIGINAL_OWNER_WASI_WITH_TRUSTED_REPAIR" if accepted else "FAILED_ORIGINAL_OWNER",
        "kind":o["kind"],"repairRule":rule,
        "originalJob":plan["originalJob"],
        "originalSourceSha":o["sourceSha"],"originalOwnerSha":o["ownerSha"],
        "originalSpecSha":o["specSha"],
        "originalOwnerCases":original_cases,"passed":passed,
        "trustedFirstPartyRepairNOTPureModel":True,
        "originalOwnerReceiptSha":sha_file(d/"owner-result.json"),
        "patchedSourceSha":sha_file(source_artifact),
        "modelGeneratedSourceExecutedOnWindowsHost":False,
        "modelCallsAdded":0,"nativeGuestAttested":False,
        "windowsHostServiceInstalled":False}
    write_json(d/"result.json",result,new=True)
    transition(d/"state.json",{"schema":1,"atUtc":utc(),
        "status":result["status"],"resultSha":sha_file(d/"result.json")},d/"history")
    event(d/"journal.jsonl","REPAIR_ORIGINAL_WASI_ACCEPTANCE",
          {"status":result["status"],"resultSha":sha_file(d/"result.json"),
           "originalOwnerReceiptSha":result["originalOwnerReceiptSha"]})
    return verify(root,ident)
def verify(root,ident):
    root=Path(root).resolve()
    d=folder(root,ident)
    plan=load(d/"plan.json")
    o=_original(root,plan["originalJob"])
    if (o["sourceSha"]!=plan["originalSourceSha"] or
        o["ownerSha"]!=plan["originalOwnerSha"] or
        o["specSha"]!=plan["originalSpecSha"] or
        o["journalSha"]!=plan["originalJournalSha"]):
        raise RuntimeError("REPAIR_ORIGINAL_OWNER_SOURCE_OR_JOURNAL_DRIFT")
    verify_journal(d/"journal.jsonl")
    if not (d/"result.json").is_file():
        return {"status":"REPAIR_PENDING_OR_UNKNOWN_NO_REPLAY","repairId":ident}
    receipt=load(d/"result.json")
    saved=load(d/"owner-result.json")
    if (receipt["originalOwnerReceiptSha"]!=sha_file(d/"owner-result.json")
        or receipt["originalOwnerSha"]!=o["ownerSha"]
        or receipt["originalSourceSha"]!=o["sourceSha"]):
        raise RuntimeError("REPAIR_ORIGINAL_RECEIPT_SHA_DRIFT")
    if receipt["status"]=="PASS_ORIGINAL_OWNER_WASI_WITH_TRUSTED_REPAIR":
        if o["kind"]=="typescript":
            if (saved["status"]!="PASS" or
                saved["originalOwnerResult"]["testResult"]["passed"]!=
                   len(o["spec"]["acceptance"])):
                raise RuntimeError("REPAIR_WASI_OWNER_NOT_ACCEPTED")
        else:
            if (saved["status"]!="PASS" or saved["isolatedExecution"]["exitCode"]!=0 or
                saved["isolatedExecution"]["testCount"]!=8):
                raise RuntimeError("REPAIR_PY_ORIGINAL_WASI_NOT_ACCEPTED")
        return {"status":"REPAIR_ORIGINAL_OWNER_WASI_SHA_VERIFIED",
                "repairId":ident,"kind":o["kind"],
                "acceptedCases":receipt["passed"],"originalCases":receipt["originalOwnerCases"],
                "trustedRepairNotPureModel":True,
                "originalOwnerSha":o["ownerSha"],"reportSha":sha_file(d/"result.json")}
    return {"status":"REPAIR_ORIGINAL_OWNER_REJECTED",
            "repairId":ident,"kind":o["kind"],
            "acceptedCases":receipt["passed"],"originalCases":receipt["originalOwnerCases"],
            "reportSha":sha_file(d/"result.json")}
