# coding: utf-8
"""Bridge an originally owner-accepted ESM repo to a real Windows Sandbox VM.

The only Host execution here is trusted Python archive construction and
SHA checks. Model-written JavaScript is NEVER run on Windows Host.
The bundled Node runtime is locally signed and SHA-pinned; guest outputs
are untrusted and cannot replace independent original WASI acceptance.
"""
from __future__ import annotations
import io,json,os,re,zipfile
from pathlib import Path
from . import engine,repo_factory,windows_sandbox
from .storage import load,sha_file,sha_bytes,write_json,verify_journal,utc

NODE_SHA="5c976096e04e5c2c1f091938926234cc9fbebfe9787ddd149351b3b0ecc707b5"
NODE_SIZE=93381448
RUNTIME=Path(r"C:\Program Files\nodejs\node.exe")
ID=re.compile(r"RJ-[0-9a-f]{16}\Z")
RUNNER=r"""'use strict';
const fs=require('node:fs'), vm=require('node:vm'), assert=require('node:assert/strict');
const p=require('node:path');
const root=__dirname;
const owner=JSON.parse(fs.readFileSync(p.join(root,'owner.json'),'utf8'));
const code=fs.readFileSync(p.join(root,'logic.js'),'utf8');
if(!Array.isArray(owner.cases) || owner.cases.length < 5 || owner.cases.length > 80)
  throw new Error('OWNER_CASES_INVALID');
const sandbox=Object.create(null);
const context=vm.createContext(sandbox,{codeGeneration:{strings:false,wasm:false}});
vm.runInContext(code,context,{timeout:2500,filename:'original-ai-bundle.js'});
if(!context.AFProject || typeof context.AFProject[owner.function] !== 'function')
  throw new Error('ORIGINAL_EXPORT_MISSING');
for(let i=0;i<owner.cases.length;i++){
  const row=owner.cases[i];
  context.__af_args=JSON.parse(JSON.stringify(row.args));
  const got=vm.runInContext('AFProject['+JSON.stringify(owner.function)+'](...__af_args)',
      context,{timeout:2500});
  assert.deepStrictEqual(JSON.parse(JSON.stringify(got)),row.expected,'CASE_'+i);
}
console.log('OWNER_NATIVE_CASES_PASS '+owner.cases.length);
"""
def _pinned_node(root):
    lock=load(Path(root)/"NATIVE-NODE.lock.json")
    if (lock.get("schema")!=1 or lock.get("nodeSha256")!=NODE_SHA
        or lock.get("size")!=NODE_SIZE or lock.get("mode")!="COPY_ONLY_TO_WINDOWS_SANDBOX"):
        raise RuntimeError("UNTRUSTED_NATIVE_NODE_LOCK")
    if not RUNTIME.is_file() or RUNTIME.is_symlink() or RUNTIME.stat().st_size!=NODE_SIZE:
        raise RuntimeError("NODE_RUNTIME_MISSING_OR_CHANGED")
    if sha_file(RUNTIME)!=NODE_SHA:raise RuntimeError("NODE_RUNTIME_SHA_MISMATCH")
    return RUNTIME

def _ps_build(node_sha,bundle_sha,owner_sha):
    return (
      "Set-StrictMode -Version Latest\n$ErrorActionPreference='Stop'\n"
      "$base=Split-Path -Parent $PSScriptRoot\n"
      "$node=Join-Path $base 'bin\\node.exe'\n"
      "$app=Join-Path $base 'app\\logic.js'\n"
      "$owner=Join-Path $base 'app\\owner.json'\n"
      "if((Get-FileHash -LiteralPath $node -Algorithm SHA256).Hash.ToLowerInvariant() -ne '"+node_sha+"'){throw 'NODE_SHA_DRIFT'}\n"
      "if((Get-FileHash -LiteralPath $app -Algorithm SHA256).Hash.ToLowerInvariant() -ne '"+bundle_sha+"'){throw 'APP_SHA_DRIFT'}\n"
      "if((Get-FileHash -LiteralPath $owner -Algorithm SHA256).Hash.ToLowerInvariant() -ne '"+owner_sha+"'){throw 'OWNER_SHA_DRIFT'}\n"
      "& $node '--check' $app\n"
      "if($LASTEXITCODE -ne 0){throw 'NATIVE_NODE_JS_SYNTAX_FAILED'}\n"
      "Write-Output 'OWNER_NATIVE_BUILD_OK'\n"
    ).encode("utf-8")
def _ps_test():
    return (
      "Set-StrictMode -Version Latest\n$ErrorActionPreference='Stop'\n"
      "$base=Split-Path -Parent $PSScriptRoot\n"
      "$node=Join-Path $base 'bin\\node.exe'\n"
      "$runner=Join-Path $base 'app\\runner.cjs'\n"
      "& $node $runner\n"
      "if($LASTEXITCODE -ne 0){throw 'OWNER_NATIVE_NODE_CASES_FAILED'}\n"
    ).encode("utf-8")

def stage_repo(root,jobid):
    root=engine.init(root)
    if not isinstance(jobid,str) or not ID.fullmatch(jobid):
        raise ValueError("BAD_REPO_JOB_ID")
    evidence=repo_factory.verify(root,jobid)
    if not evidence.get("verified") or evidence["status"]!="PASS":
        raise RuntimeError("REPO_ORIGINAL_WASI_OWNER_ACCEPTANCE_REQUIRED")
    node=_pinned_node(root)
    repo=Path(root)/"repojobs"/jobid
    m=load(repo/"manifest.json")
    spec=load(repo/"spec.json")
    original=load(repo/"owner-acceptance.json")
    prefix=repo/"attempts"/("A-%02d"%m["selectedAttempt"])
    bundle=Path(str(prefix)+"-bundle.js")
    if sha_file(bundle)!=m["bundleSha"]:raise RuntimeError("BUNDLE_SHA_DRIFT")
    if sha_file(repo/"owner-acceptance.json")!=m["originalOwnerSha"]:
        raise RuntimeError("OWNER_PREIMAGE_DRIFT")
    if original["function"]!=spec["exportName"] or original["cases"]!=spec["acceptance"]:
        raise RuntimeError("OWNER_TESTS_MISMATCH")
    name="windows_native_repo_"+jobid
    zipped=Path(root)/"examples"/(name+".zip")
    contract=Path(root)/"examples"/(name+".json")
    if zipped.exists() or contract.exists():
        raise RuntimeError("NATIVE_REPO_BRIDGE_PREVIOUS_INTENT_RECONCILE_NOT_REBUILD")
    source=bundle.read_bytes()
    owner_bytes=json.dumps({"schema":1,"function":original["function"],"cases":original["cases"]},
        ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")
    run_bytes=RUNNER.encode("utf-8")
    files={"app/logic.js":source,"app/owner.json":owner_bytes,
           "app/runner.cjs":run_bytes,
           "src/build.ps1":_ps_build(NODE_SHA,sha_bytes(source),sha_bytes(owner_bytes)),
           "src/test.ps1":_ps_test()}
    # One compressed ZIP is the only user/model-code container. Node is trusted
    # runtime, and must fit the existing 45MiB/110MiB sandbox intake limits.
    with zipped.open("xb") as raw:
        with zipfile.ZipFile(raw,"w",zipfile.ZIP_DEFLATED,compresslevel=6) as z:
            for k,v in sorted(files.items()):z.writestr(k,v)
            z.write(node,arcname="bin/node.exe",compress_type=zipfile.ZIP_DEFLATED,compresslevel=6)
        raw.flush();os.fsync(raw.fileno())
    contract_data={"schema":1,"kind":"powershell",
      "goal":"Run a real originally model-generated ESM project in a disposable Windows Sandbox with pinned Node and independent owner cases.",
      "steps":[{"script":"src/build.ps1"},{"script":"src/test.ps1"}]}
    with contract.open("xb") as f:
        v=(json.dumps(contract_data,ensure_ascii=False,indent=2)+"\n").encode()
        f.write(v);f.flush();os.fsync(f.fileno())
    source_rows=windows_sandbox._zip_info(zipped)
    if len(source_rows)!=6 or "bin/node.exe" not in source_rows:
        raise RuntimeError("SANDBOX_NATIVE_REPO_ZIP_INVALID")
    stage=windows_sandbox.stage(root,zipped,contract)
    job=Path(root)/"sandboxjobs"/stage["jobId"]
    receipt={"schema":1,"atUtc":utc(),"sourceRepoJob":jobid,
      "sandboxJob":stage["jobId"],"repoOriginalOwnerSha":m["originalOwnerSha"],
      "repoOriginalWasiReceiptSha":m["originalWasiReceiptSha"],
      "repoModelSha":m["modelSha"],"repoModelProvider":m["provider"],
      "repoBundleSha":m["bundleSha"],"nodeRuntimeSha":NODE_SHA,
      "originalOwnerCaseCount":len(original["cases"]),
      "portablePackageSha":sha_file(zipped),"contractSha":sha_file(contract),
      "originalSandboxManifestSha":sha_file(job/"manifest.json"),
      "nativeHostModelCodeExecuted":False,
      "guestResultCannotAttestOwnerAcceptance":True,"status":"STAGED_NOT_LAUNCHED"}
    write_json(job/"repo-native-bridge.json",receipt,new=True)
    return {"status":"NATIVE_REPO_STAGED","sandboxJob":stage["jobId"],
       "originalRepo":jobid,"originalWasiAccepted":True,
       "ownerCaseCount":len(original["cases"]),"zipSha":sha_file(zipped),
       "nodeSha":NODE_SHA,"sandboxPolicy":stage["verify"]["status"]}

def verify_native(root,jid):
    root=engine.init(root)
    info=windows_sandbox.verify(root,jid)
    folder=Path(root)/"sandboxjobs"/jid
    rec=load(folder/"repo-native-bridge.json")
    if rec["sandboxJob"]!=jid:raise RuntimeError("REPO_BRIDGE_JOB_ID_DRIFT")
    original=repo_factory.verify(root,rec["sourceRepoJob"])
    if original["compiledSha256"]!=rec["repoBundleSha"] or original["ownerCases"]!=rec["originalOwnerCaseCount"]:
        raise RuntimeError("ORIGINAL_WASI_ACCEPTANCE_DRIFT")
    verify_journal(folder/"journal.jsonl")
    orig=windows_sandbox.reconcile(root,jid)
    if orig["status"]!="UNTRUSTED_GUEST_REPORT_READBACK_ONLY":
        return {"status":"GUEST_NOT_YET_REPORTED","nativeOwnerAcceptance":False,"sourceWasiAccepted":True}
    report=load(folder/"output/guest-report.json")
    owner=load(folder/"input/owner.json")
    assert owner["jobId"]==jid and owner["nonce"]==report["nonce"]
    if not (report.get("status")=="GUEST_REPORTED_ALL_OK_UNATTESTED"
       and report.get("originalJobId")==jid and len(report.get("steps",[]))==2
       and all(type(row.get("exitCode")) is int and row["exitCode"]==0
               and row.get("status")=="GUEST_REPORTED_OK" for row in report["steps"])):
        return {"status":"GUEST_REPORTED_FAILURE_OR_UNKNOWN","originalStatus":report.get("status"),
                "nativeOwnerAcceptance":False}
    out=folder/"output"
    a=(out/"STEP-1-stdout.txt").read_text("utf-8-sig").strip()
    b=(out/"STEP-2-stdout.txt").read_text("utf-8-sig").strip()
    if a!="OWNER_NATIVE_BUILD_OK" or b!=("OWNER_NATIVE_CASES_PASS "+str(rec["originalOwnerCaseCount"])):
        raise RuntimeError("GUEST_OUTPUT_MARKER_MISMATCH")
    if (out/"STEP-1-stderr.txt").stat().st_size or (out/"STEP-2-stderr.txt").stat().st_size:
        raise RuntimeError("GUEST_STDERR_NOT_EMPTY")
    return {"status":"ORIGINAL_WASI_AND_NATIVE_GUEST_READBACK_CORRELATED",
        "nativeOwnerAcceptance":False,"originalWasiAccepted":True,
        "guestClaimsTrusted":False,"originalOwnerCases":rec["originalOwnerCaseCount"],
        "originalGuestReportSha":orig["guestReceiptSha"],
        "nativeNodeSha":rec["nodeRuntimeSha"],"originalRepo":rec["sourceRepoJob"]}
