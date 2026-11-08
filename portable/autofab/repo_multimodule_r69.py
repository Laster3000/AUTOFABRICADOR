# coding: utf-8
"""R69 on-demand multi-agent ESM factory. Local model code runs in WASI only.

Owner freezes per-module and final cases BEFORE model calls. No Windows boot
service, no native generated code, no npm lifecycle, no replay of UNKNOWN.
"""
from pathlib import Path
import hashlib,json,os,re,uuid,zipfile
from . import engine,local_cuda9b,repo_graph,direct_agent
from .storage import load,sha_file,sha_bytes,utc,write_json,transition,event,verify_journal

NAME=re.compile(r"MR69-[a-f0-9]{16}\Z")
def folder(root,jid):
    if not NAME.fullmatch(str(jid)):raise ValueError("R69_BAD_JOB_ID")
    p=Path(root).resolve()/"r69jobs"/jid
    if not p.is_dir():raise FileNotFoundError("R69_JOB_NOT_FOUND")
    return p

def state(d,value,detail):
    transition(d/"state.json",{"schema":1,"status":value,"atUtc":utc(),
      "detail":detail[:220]},d/"history")
    event(d/"journal.jsonl","R69_STATE",{"value":value,
      "sha":sha_file(d/"state.json")})

def valid(spec,plan):
    repo_graph._valid_spec(spec)
    if set(plan)!={"schema","specSha","order","modules"} or plan["schema"]!=1:
        raise ValueError("R69_BAD_OWNER_MODULE_PLAN")
    if plan["order"][-1]!=spec["entry"] or set(plan["order"])!=set(spec["sources"]):
        raise ValueError("R69_BAD_MODULE_GRAPH")
    if not 2<=len(plan["order"])<=5 or len(set(plan["order"]))!=len(plan["order"]):
        raise ValueError("R69_MODULE_GRAPH_UNSUPPORTED")
    if set(plan["modules"])!=set(plan["order"]):
        raise ValueError("R69_MODULE_PLAN_MISSING")
    for name,v in plan["modules"].items():
        if (set(v)!={"exportName","prompt","cases"}
            or not isinstance(v["exportName"],str)
            or not isinstance(v["prompt"],str)
            or not 60<=len(v["prompt"])<=2300
            or not isinstance(v["cases"],list)
            or (name!=spec["entry"] and not 5<=len(v["cases"])<=30)):
            raise ValueError("R69_BAD_INDEPENDENT_MODULE_CONTRACT")
    return True

def create(root,spec_path,plan_path,holdout_path):
    root=engine.init(root)
    paths=[Path(x).resolve() for x in (spec_path,plan_path,holdout_path)]
    if any(not p.is_file() or p.is_symlink() or not
       (p.is_relative_to(root/"examples") or p.is_relative_to(root/"CONTINUIDAD"))
       for p in paths):
        raise ValueError("R69_OWNER_PATH_NOT_IN_PORTABLE_ROOT")
    spec,plan,holdout=(load(p) for p in paths)
    valid(spec,plan)
    if plan["specSha"]!=sha_file(paths[0]) or holdout.get("specSha")!=plan["specSha"]:
        raise RuntimeError("R69_OWNER_SPEC_OR_PLAN_SHA_MISMATCH")
    if set(holdout)!={"schema","cases","specSha"} or holdout["schema"]!=1:
        raise ValueError("R69_HOLDOUT_INVALID")
    repo_graph._valid_spec({**spec,"acceptance":holdout["cases"]})
    repo_graph.preflight(root)
    for old in (root/"r69jobs").glob("MR69-*/owner.json"):
        if load(old).get("specSha")==sha_file(paths[0]):
            raise RuntimeError("R69_DUPLICATE_OWNER_INTENT_NO_REPLAY")
    jid="MR69-"+uuid.uuid4().hex[:16]
    d=root/"r69jobs"/jid
    d.mkdir(parents=True)
    (d/"attempts").mkdir()
    for name,value in (("spec.json",spec),("plan.json",plan),("holdout.json",holdout)):
        write_json(d/name,value,new=True)
    owner={"schema":1,"jobId":jid,"atUtc":utc(),
       "specSha":sha_file(d/"spec.json"),"planSha":sha_file(d/"plan.json"),
       "holdoutSha":sha_file(d/"holdout.json"),
       "modelSha":local_cuda9b.MODEL_SHA,
       "modelCannotModifyOwnerContracts":True}
    write_json(d/"owner.json",owner,new=True)
    write_json(d/"control.json",{"schema":1,"command":"RUN","atUtc":utc()},new=True)
    write_json(d/"state.json",{"schema":1,"status":"PENDING","atUtc":utc()},new=True)
    event(d/"journal.jsonl","R69_OWNER_CONTRACT_FROZEN",
       {"ownerSha":sha_file(d/"owner.json"),"cases":len(spec["acceptance"]),
        "holdout":len(holdout["cases"])})
    return {"jobId":jid,"status":"PENDING","ownerSHA":sha_file(d/"owner.json")}

def module_spec(spec,name,desc,code):
    if name==spec["entry"]:return {**spec,"sources":dict(code)}
    exp=desc["exportName"]
    shim=("import {"+exp+"} from './"+Path(name).name+"';\n"
          "export function qaOwner(...args){ return "+exp+"(...args); }\n")
    stage={"schema":1,"language":spec["language"],"goal":desc["prompt"],
      "entry":"src/index.js","exportName":"qaOwner",
      "sources":{"src/index.js":shim,name:code[name]},
      "acceptance":desc["cases"],"dependencies":spec["dependencies"]}
    repo_graph._valid_spec(stage)
    return stage

def extract(raw,exp):
    raw=raw.strip()
    raw=re.sub(r"(?s)^\s*<think>.*?</think>\s*","",raw)
    fence=chr(96)*3
    if raw.startswith(fence):
        lines=raw.splitlines()
        if len(lines)<3 or not lines[-1].strip().startswith(fence):
            raise ValueError("R69_UNCLOSED_CODE_FENCE")
        raw="\n".join(lines[1:-1]).strip()
    if raw.startswith("javascript\n"):raw=raw[11:].strip()
    if raw.startswith("{"):
        try:
            val=json.loads(raw)
            if isinstance(val,dict) and set(val)=={"code"}:
                raw=val["code"]
        except (ValueError,TypeError):pass
    if not isinstance(raw,str) or not 24<=len(raw)<=13500:
        raise ValueError("R69_EMPTY_OR_TOO_LONG_MODEL_CODE")
    if not re.search(r"\bexport\s+(?:async\s+)?function\s+"+re.escape(exp)+r"\s*\(",raw):
        raise ValueError("R69_EXPORTED_FUNCTION_MISSING:"+exp)
    if fence in raw or "PENDIENTE_" in raw:
        raise ValueError("R69_MODEL_SOURCE_PLACEHOLDER")
    repo_graph._static_source_guard({"src/test.js":raw})
    return raw.rstrip()+"\n"

def feedback(result,cases):
    status=result.get("status")
    if status=="FAILED_ESM_GRAPH_COMPILE":
        return "Compiler error: "+str(result.get("compiler",{}).get("compilerStderrTail",""))[-800:]
    if status=="FAILED_OWNER_WASI":
        rows=(result.get("originalOwnerResult") or {}).get("testResult") or {}
        snippets=[]
        for row in (rows.get("failed") or [])[:2]:
            ix=row.get("i")
            if type(ix) is int and 0<=ix<len(cases):
                snippets.append({"args":cases[ix]["args"],
                   "expected":cases[ix]["expected"],"got":row.get("got")})
        diagnosis=""
        for sample in snippets:
            got=sample.get("got")
            wanted=sample.get("expected")
            if (isinstance(got,dict) and isinstance(wanted,dict)
                and got.get("error")=="DATOS_INVALIDOS" and wanted.get("error") is None):
                diagnosis=("ROOT CAUSE: q.inventario is ARRAY of product rows, "
                  "each product row contains stock,minimo,precioCent,sku. "
                  "q.pedido is ARRAY of rows {sku,cantidad}. "
                  "There is NO q.stock, q.minimo, q.precioCent or q.quantities. "
                  "Never destructure product-row fields from q. ")
                break
        return diagnosis+" Independent WASI owner failure: "+json.dumps(snippets,ensure_ascii=True)[:1130]
    return "Independent compiler/owner result "+str(status)

def prompt_for(module,desc,last,reason):
    msg=("Implement one business JS ES module, write ONLY raw source code. "
      "NO JSON, no fences, no comments about task, no tests, no shell, "
      "no use of process, Node, network or filesystem. File "+module+
      ". Required export "+desc["exportName"]+". Owner-approved rules: "+
      desc["prompt"]+". Finish function completely with no placeholders.")
    if reason:msg+=(". CRITICAL INDEPENDENT VERIFIER FEEDBACK: "+reason[:1650]+
        ". Write a DIFFERENT corrected source. Do not reuse prior solution. "
        "Prior wrong source excerpt: "+last[:650])
    return msg

def model_attempt(root,d,aid,name,desc,current,reason,max_tokens):
    p=d/"attempts"/aid
    prompt=prompt_for(name,desc,current,reason)
    owner=load(d/"owner.json")
    for key,path in (("specSha",d/"spec.json"),
       ("planSha",d/"plan.json"),("holdoutSha",d/"holdout.json")):
        if sha_file(path)!=owner[key]:
            state(d,"UNKNOWN","immutable owner input changed")
            raise RuntimeError("R69_OWNER_CASE_SHA_CHANGED_NO_REPLAY")
    intent={"schema":1,"operationId":d.name+"."+aid,"atUtc":utc(),
      "module":name,"modelSha":local_cuda9b.MODEL_SHA,
      "promptSha":sha_bytes(prompt.encode()),"ownerSha":sha_file(d/"owner.json"),
      "tokens":max_tokens,"modelHostCodeExecutionAllowed":False}
    write_json(Path(str(p)+"-intent.json"),intent,new=True)
    state(d,"MODEL_PENDING",name+" "+aid)
    event(d/"journal.jsonl","R69_MODULE_MODEL_INTENT",
      {"aid":aid,"sha":sha_file(Path(str(p)+"-intent.json"))})
    request={"model":local_cuda9b.ALIAS,"stream":True,
      "stream_options":{"include_usage":True},
      "temperature":0,"max_tokens":max_tokens,
      "chat_template_kwargs":{"enable_thinking":False},
      "messages":[
       {"role":"system","content":"Return ONLY raw JavaScript ES module code; no JSON, prose, Markdown or tools."},
       {"role":"user","content":prompt}]}
    raw=direct_agent._stream_text(root,d,request,deadline=215,port=local_cuda9b.PORT)
    write_json(Path(str(p)+"-stream.json"),raw,new=True)
    event(d/"journal.jsonl","R69_MODEL_STREAM_READBACK",
      {"aid":aid,"streamSha":sha_file(Path(str(p)+"-stream.json")),
       "complete":raw["done"],"reason":raw["lastFinishReason"]})
    if raw["cancelObserved"] or not raw["done"] or raw["errors"] or not raw["threadExited"]:
        state(d,"UNKNOWN","incomplete or uncertain model stream, no replay")
        raise RuntimeError("R69_ORIGINAL_MODEL_STREAM_INCOMPLETE_NO_BLIND_RETRY")
    if raw.get("lastFinishReason")=="length":
        write_json(Path(str(p)+"-failure.json"),
           {"status":"FAILED_MODEL_TRUNCATED_AT_TOKEN_LIMIT","atUtc":utc()},new=True)
        return None,"Model output truncated. Write shorter complete JS code, no explanation."
    try:src=extract(raw["resultText"],desc["exportName"])
    except (ValueError,TypeError) as exc:
        write_json(Path(str(p)+"-failure.json"),
          {"status":"FAILED_MODEL_MODULE_FORMAT","reason":str(exc)[:160],
           "atUtc":utc()},new=True)
        return None,"Invalid model JS format: "+str(exc)[:150]
    write_json(Path(str(p)+"-source.json"),
       {"schema":1,"module":name,"source":src},new=True)
    event(d/"journal.jsonl","R69_UNTRUSTED_MODEL_MODULE_SOURCE_PINNED",
       {"aid":aid,"sourceSha":sha_file(Path(str(p)+"-source.json"))})
    return src,""

def run(root,jid,*,max_attempts=3):
    root=engine.init(root);d=folder(root,jid)
    if load(d/"state.json")["status"]!="PENDING" or list((d/"attempts").iterdir()):
        raise RuntimeError("R69_ORIGINAL_JOB_ALREADY_STARTED_NO_REPLAY")
    if type(max_attempts) is not int or not 1<=max_attempts<=3:
        raise ValueError("R69_ATTEMPT_LIMIT")
    spec=load(d/"spec.json");plan=load(d/"plan.json");holdout=load(d/"holdout.json")
    valid(spec,plan)
    repo_graph.preflight(root);local_cuda9b.pinned_assets(root)
    owner=load(d/"owner.json")
    srv=local_cuda9b.server_info(root)
    if srv["state"]=="EXITED":
        local_cuda9b.stop(root);srv=local_cuda9b.server_info(root)
    if srv["state"] not in ("NOT_STARTED","READY"):
        raise RuntimeError("R69_GPU_LEASE_UNRECONCILED")
    owned=srv["state"]=="NOT_STARTED"
    if owned and local_cuda9b.start(root)["state"]!="READY":
        raise RuntimeError("R69_PINNED_GPU_NOT_READY")
    files=dict(spec["sources"])
    final=None
    try:
        for index,name in enumerate(plan["order"],1):
            desc=plan["modules"][name];last=files[name];reason="";passed=False
            for attempt in range(1,max_attempts+1):
                if load(d/"control.json")["command"]!="RUN":
                    state(d,"STOPPED_SAFE_BOUNDARY","before next module request")
                    return {"status":"STOPPED_SAFE_BOUNDARY","jobId":jid}
                aid="M"+str(index)+"-A"+str(attempt)
                code,model_feedback=model_attempt(root,d,aid,name,desc,last,reason,
                          1850 if name!=spec["entry"] else 1450)
                if code is None:
                    reason=model_feedback
                    continue
                last=code;files[name]=code
                tests=module_spec(spec,name,desc,files)
                state(d,"MODULE_QA",name+" "+aid)
                try:result=repo_graph.build_owner(root,tests,tests["sources"],timeout=105)
                except Exception as exc:
                    state(d,"UNKNOWN","unclassified original compiler/WASI exception")
                    raise RuntimeError("R69_COMPILER_CHILD_UNKNOWN_DO_NOT_REPLAY") from exc
                out={k:v for k,v in result.items() if k!="compiledSource"}
                rec=d/"attempts"/(aid+"-owner.json")
                write_json(rec,out,new=True)
                event(d/"journal.jsonl","R69_ORIGINAL_INDEPENDENT_OWNER_QA",
                     {"module":name,"aid":aid,
                      "result":out["status"],"receiptSha":sha_file(rec)})
                if out["status"].startswith("UNKNOWN"):
                    state(d,"UNKNOWN","original compiler or guest unknown")
                    return {"status":"UNKNOWN","jobId":jid,"originalOwnerSHA":sha_file(rec)}
                if out["status"]=="PASS":
                    if name==spec["entry"]:final=result
                    passed=True
                    write_json(d/("M"+str(index)+"-accepted.json"),
                       {"schema":1,"module":name,"source":code,"atUtc":utc(),
                        "independentOwnerSha":sha_file(rec)},new=True)
                    break
                reason=feedback(out,tests["acceptance"])
                if attempt>=2:
                    previous=d/"attempts"/("M"+str(index)+"-A"+str(attempt-1)+"-source.json")
                    current=d/"attempts"/(aid+"-source.json")
                    if previous.is_file() and current.is_file():
                        old_source=load(previous)["source"]
                        current_source=load(current)["source"]
                        if old_source==current_source and out["status"]!="PASS":
                            receipt={"schema":1,"status":"STAGNATED_IDENTICAL_MODEL_CODE",
                              "module":name,"attempts":attempt,"sourceSHA":sha_bytes(current_source.encode()),
                              "originalOwnerReceiptSHA":sha_file(rec),
                              "newModelCallForbidden":True,"atUtc":utc()}
                            write_json(d/"stagnation.json",receipt,new=True)
                            state(d,"STAGNATED_IDENTICAL_MODEL_CODE",name+" no semantic change")
                            return {"jobId":jid,"status":"STAGNATED_IDENTICAL_MODEL_CODE",
                              "module":name,"modelCallsInModule":attempt}
            if not passed:
                status="FAILED_MODULE_OWNER_OR_FORMAT"
                state(d,status,name+" after "+str(max_attempts)+" model attempts")
                return {"jobId":jid,"status":status,"module":name,
                  "modelCallsInModule":max_attempts}
        if final is None or final["status"]!="PASS":
            raise RuntimeError("R69_ORIGINAL_INTEGRATION_WAS_NOT_ACCEPTED")
        other={**spec,"acceptance":holdout["cases"]}
        # Hidden holdout original independent owner cases, not used in model prompts.
        try:second=repo_graph.build_owner(root,other,files,timeout=105)
        except Exception as exc:
            state(d,"UNKNOWN","holdout child exception")
            raise RuntimeError("R69_HOLDOUT_UNKNOWN_DO_NOT_REPLAY") from exc
        hold={k:v for k,v in second.items() if k!="compiledSource"}
        write_json(d/"holdout-original-wasi.json",hold,new=True)
        event(d/"journal.jsonl","R69_ORIGINAL_HOLDOUT_RECEIPT",
             {"result":hold["status"],
              "receiptSha":sha_file(d/"holdout-original-wasi.json")})
        if hold["status"]!="PASS":
            state(d,"FAILED_HIDDEN_OWNER_HOLDOUT","unseen owner cases failed")
            return {"jobId":jid,"status":"FAILED_HIDDEN_OWNER_HOLDOUT",
             "mainOwnerPass":len(spec["acceptance"]),"holdoutReceiptSHA":sha_file(d/"holdout-original-wasi.json")}
        if second["compiledSha256"]!=final["compiledSha256"]:
            state(d,"UNKNOWN","WASI source binary SHA non-deterministic")
            raise RuntimeError("R69_COMPILED_SOURCE_NONDETERMINISTIC")
        src=d/"generated-sources.json"
        write_json(src,{"schema":1,"sources":files},new=True)
        bundle=d/"compiled-bundle.js"
        with bundle.open("xb") as stream:
            stream.write(final["compiledSource"].encode())
            stream.flush();os.fsync(stream.fileno())
        if sha_file(bundle)!=final["compiledSha256"]:
            state(d,"UNKNOWN","original compiled bytes SHA drift")
            raise RuntimeError("R69_BUNDLE_SHA_MISMATCH")
        m={"schema":1,"operationId":jid+".RELEASE.CANDIDATE",
          "status":"PASS_MODEL_AUTHORED_NEW_COMPLEX_ESM_MODULES_WASI",
          "atUtc":utc(),"ownerSHA":sha_file(d/"owner.json"),
          "specSHA":sha_file(d/"spec.json"),
          "planSHA":sha_file(d/"plan.json"),
          "holdoutSHA":sha_file(d/"holdout.json"),
          "sourceSHA":sha_file(src),
          "bundleSHA":sha_file(bundle),
          "holdoutReceiptSHA":sha_file(d/"holdout-original-wasi.json"),
          "modelSHA":local_cuda9b.MODEL_SHA,
          "moduleCount":len(files),"ownerCases":len(spec["acceptance"]),
          "holdoutCases":len(holdout["cases"]),
          "modelGeneratedAllModules":True,
          "compiledAndRunOnlyInsideOriginalWASI":True,
          "modelCodeExecutedAsNativeHostProcess":False,
          "modelModifiedOriginalOwnerTests":False,
          "WindowsTaskSchedulerRequired":False,
          "isNativeWindowsGUIProgram":False,
          "originalFactoryReleasePromoted":False}
        write_json(d/"manifest.json",m,new=True)
        artifact=d/"ERP-R69-AI-GENERATED-ESM-CANDIDATE.zip"
        with zipfile.ZipFile(artifact,"x",compression=zipfile.ZIP_DEFLATED) as z:
            for name,code in sorted(files.items()):z.writestr(name,code)
            z.write(bundle,"bundle.js")
            z.write(d/"manifest.json","MANIFEST.json")
            z.writestr("README.txt","AUTOFABRICADOR R68: AI-authored ESM business module. Original WASI independent QA. Not native Windows executable. Do not run untrusted JS on Windows Host.")
        event(d/"journal.jsonl","R69_CANDIDATE_ARTIFACT_FROZEN",
          {"manifestSHA":sha_file(d/"manifest.json"),"artifactSHA":sha_file(artifact)})
        state(d,"PASS","original module+integration+hidden owner all pass")
        return {"jobId":jid,"status":"PASS","ownerCases":len(spec["acceptance"]),
           "holdoutCases":len(holdout["cases"]),"moduleCount":len(files),
           "artifactSHA":sha_file(artifact),"verify":verify(root,jid)}
    finally:
        if owned:
            local_cuda9b.stop(root)

def verify(root,jid):
    d=folder(root,jid)
    if load(d/"state.json")["status"]!="PASS":
        raise RuntimeError("R69_ONLY_ACCEPTED_JOB_CAN_VERIFY")
    verify_journal(d/"journal.jsonl")
    m=load(d/"manifest.json")
    for key,p in (("ownerSHA","owner.json"),("specSHA","spec.json"),
       ("planSHA","plan.json"),("holdoutSHA","holdout.json"),
       ("sourceSHA","generated-sources.json"),("bundleSHA","compiled-bundle.js"),
       ("holdoutReceiptSHA","holdout-original-wasi.json")):
        if sha_file(d/p)!=m[key]:raise RuntimeError("R69_FINAL_ORIGINAL_"+key+"_SHA_DRIFT")
    files=load(d/"generated-sources.json")["sources"]
    plan=load(d/"plan.json");spec=load(d/"spec.json")
    if set(files)!=set(spec["sources"]):raise RuntimeError("R69_FINAL_SOURCE_SET_DRIFT")
    for i,name in enumerate(plan["order"],1):
        original=load(d/("M"+str(i)+"-accepted.json"))
        if original["module"]!=name or original["source"]!=files[name]:
            raise RuntimeError("R69_MODEL_MODULE_SELECTED_SOURCE_CHANGED")
    hold=load(d/"holdout-original-wasi.json")
    if hold["status"]!="PASS" or hold["originalOwnerResult"]["status"]!="PASS":
        raise RuntimeError("R69_HOLDOUT_WASI_ORIGINAL_NOT_PASS")
    if hold["originalOwnerResult"]["testCount"]!=m["holdoutCases"]:
        raise RuntimeError("R69_HOLDOUT_COUNT_DRIFT")
    if not m["modelGeneratedAllModules"] or m["modelCodeExecutedAsNativeHostProcess"]:
        raise RuntimeError("R69_MODEL_CODE_TRUST_BOUNDARY_DRIFT")
    return {"verified":True,"ownerCases":m["ownerCases"],
       "holdoutCases":m["holdoutCases"],"modules":m["moduleCount"],
       "bundleSHA":m["bundleSHA"]}

def status(root,jid):
    d=folder(root,jid)
    verify_journal(d/"journal.jsonl")
    state_name=load(d/"state.json")["status"]
    return {"jobId":jid,"status":state_name,
      "attempts":len(list((d/"attempts").glob("*-intent.json"))),
      "originalOwnerSHA":sha_file(d/"owner.json"),
      "verified":verify(root,jid) if state_name=="PASS" else None}
