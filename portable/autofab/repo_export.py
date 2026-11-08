# coding: utf-8
"""Portable multi-file ESM project browser output from WASI-accepted source.

Trusted page/controller CSS, original model-approved esbuild bundle, independent
offline Chrome E2E. No model-generated code executed on Node/Windows Host.
"""
from __future__ import annotations
from pathlib import Path
import json,os,shutil,subprocess,tempfile,zipfile
from . import engine,repo_factory,webapps
from .storage import load,sha_file,sha_bytes,utc,write_json,event,verify_journal,json_bytes

def _original(root,jobid):
    repo_factory.verify(root,jobid)
    d=repo_factory.directory(root,jobid)
    spec=load(d/"spec.json")
    m=load(d/"manifest.json")
    prefix=d/"attempts"/f"A-{m['selectedAttempt']:02d}"
    source=load(Path(str(prefix)+"-source.json"))["files"]
    compiled=Path(str(prefix)+"-bundle.js")
    if sha_file(compiled)!=m["bundleSha"]:
        raise RuntimeError("REPO_ORIGINAL_ACCEPTED_BUNDLE_SHA_DRIFT")
    return d,spec,m,compiled,source

def export(root,jobid):
    root=engine.init(root)
    webapps.preflight(root)
    d,spec,m,bundle,source=_original(root,jobid)
    store=root/"repoexports"
    store.mkdir(exist_ok=True)
    path=store/("AF-REPO-"+jobid+".zip")
    evidence=store/("AF-REPO-"+jobid+"-receipts")
    if path.exists() or evidence.exists():
        # Original browser export may have persisted REPO_APP_INTENT and failed
        # before a package/owner browser receipt existed. Never call verify()
        # on an incomplete state (which used to raise FileNotFoundError),
        # and NEVER repeat that original effect or overwrite its journal.
        if not evidence.is_dir():
            return {"status":"UNKNOWN_ORIGINAL_EXPORT_ARTIFACT_NO_REPLAY",
                    "jobId":jobid,"archiveExists":path.is_file(),
                    "requiresOriginalReadback":True}
        journal=evidence/"journal.jsonl"
        evidence_status=verify_journal(journal) if journal.is_file() else None
        package=evidence/"PACKAGE-RECEIPT.json"
        if (path.is_file() and package.is_file()
            and (evidence/"PROJECT-MANIFEST.json").is_file()
            and (evidence/"BROWSER-RECEIPT.json").is_file()):
            return {"status":"PREEXISTING_RECONCILE_NO_REPLAY",
                    "verify":verify(root,jobid)}
        return {"status":"ORIGINAL_EXPORT_INCOMPLETE_INTENT_NO_REPLAY",
                "jobId":jobid,"archiveExists":path.is_file(),
                "originalJournalEvents":evidence_status["events"] if evidence_status else None,
                "originalJournalSha":sha_file(journal) if journal.is_file() else None,
                "originalBrowserReceiptExists":(evidence/"BROWSER-RECEIPT.json").is_file(),
                "originalPackageReceiptExists":package.is_file(),
                "manualOriginalReconciliationRequired":True}
    evidence.mkdir()
    event(evidence/"journal.jsonl","REPO_APP_INTENT",
        {"jobId":jobid,"ownerOriginalSha":m["originalOwnerSha"],
         "compiledOriginalSha":m["bundleSha"]})
    with tempfile.TemporaryDirectory(prefix="af-repo-browser-") as tmp:
        stage=Path(tmp)
        app={"function":spec["exportName"],"acceptance":spec["acceptance"]}
        (stage/"index.html").write_bytes(webapps._page(jobid,app,{}).encode())
        (stage/"styles.css").write_bytes(webapps._css().encode())
        (stage/"controller.js").write_bytes(webapps._controller(
            spec["exportName"],len(spec["acceptance"][0]["args"])).encode())
        shutil.copyfile(bundle,stage/"logic.js")
        if sha_file(stage/"logic.js")!=m["bundleSha"]:
            raise RuntimeError("REPO_BROWSER_BUNDLE_SHA_DRIFT")
        for rel,raw in source.items():
            output=stage/rel
            output.parent.mkdir(exist_ok=True,parents=True)
            output.write_bytes(raw.encode())
            if sha_file(output)!=sha_bytes(raw.encode()):
                raise RuntimeError("REPO_PROJECT_SOURCE_SHA_DRIFT")
        package={"name":"autofabricador-repo-"+jobid.lower(),
                 "version":"0.1.0","private":True,"type":"module",
                 "description":"Accepted AI-generated multi-file source and offline browser output",
                 "scripts":{},
                 "dependencies":{name:"PINNED_PRIVATE_SNAPSHOT" for name in spec["dependencies"]}}
        (stage/"package.json").write_bytes(json_bytes(package))
        readme=("AUTOFABRICADOR portable offline project.\n"
          "Open index.html in a browser; no npm installation or network required.\n"
          "All generated source first passed original WASI owner tests.\n"
          "The browser controller and stylesheet are first-party templates.\n"
          "Do not execute model-authored npm lifecycle scripts or Node shell.\n")
        (stage/"README.txt").write_bytes(readme.encode())
        cases=stage/"owner-browser-cases.json"
        write_json(cases,spec["acceptance"],new=True)
        browser_path=stage/"browser-result.json"
        try:
            result=subprocess.run([str(webapps.NODE),str(root/"qa/browser_probe.js"),
                 str(stage),str(cases),str(webapps.CHROME),str(browser_path)],
                 cwd=str(root),stdin=subprocess.DEVNULL,capture_output=True,
                 timeout=95,env={**os.environ,"NODE_OPTIONS":"",
                 "DOTNET_ADD_GLOBAL_TOOLS_TO_PATH":"false"})
        except subprocess.TimeoutExpired:
            raise RuntimeError("REPO_CHROME_E2E_TIMEOUT_UNKNOWN_NO_REPLAY")
        if result.returncode or not browser_path.exists():
            raise RuntimeError("REPO_CHROME_ORIGINAL_OWNER_NOT_PASS:"+
              result.stderr.decode("utf-8","replace")[-1600:])
        browser=load(browser_path)
        if (browser["status"]!="PASS" or
            browser["passed"]!=len(spec["acceptance"]) or
            browser["testCount"]!=len(spec["acceptance"]) or
            browser["externalFetchBlocked"] is not True):
            raise RuntimeError("REPO_CHROME_OWNER_OR_NETWORK_TEST_REJECTED")
        write_json(evidence/"BROWSER-RECEIPT.json",browser,new=True)
        event(evidence/"journal.jsonl","REPO_BROWSER_OWNER_ACCEPTED",
            {"testCount":browser["testCount"],
             "receiptSha":sha_file(evidence/"BROWSER-RECEIPT.json")})
        files={p.relative_to(stage).as_posix():sha_file(p)
               for p in stage.rglob("*")
               if p.is_file() and p not in (browser_path,cases)}
        manifest={"schema":1,"atUtc":utc(),"jobId":jobid,
          "status":"CANDIDATE_ACCEPTED_NOT_INSTALLED",
          "type":"ESM_REPOSITORY_COMPILED_WASI_AND_BROWSER",
          "files":files,
          "originalOwnerModelManifestSha":sha_file(d/"manifest.json"),
          "originalWasiOwnerReceiptSha":m["originalWasiReceiptSha"],
          "originalModelBundleSha":m["bundleSha"],
          "originalBrowserReceiptSha":sha_file(evidence/"BROWSER-RECEIPT.json"),
          "originalAcceptanceCases":len(spec["acceptance"]),
          "pinnedNpmDependencies":m["dependencies"],
          "nodeExecutedModelJS":False,"npmInstallHooks":False,
          "browserNetworkBlocked":True}
        write_json(evidence/"PROJECT-MANIFEST.json",manifest,new=True)
        with zipfile.ZipFile(path,"x",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
            for relative in sorted(files):
                z.write(stage/relative,relative)
            z.writestr("MANIFEST.json",json_bytes(manifest))
            z.writestr("BROWSER-RECEIPT.json",json_bytes(browser))
        receipt={"schema":1,"atUtc":utc(),"jobId":jobid,
             "status":"REPO_BROWSER_WASI_E2E_PASS",
             "archiveSha256":sha_file(path),
             "originalModelManifestSha":sha_file(d/"manifest.json"),
             "originalManifestSha":sha_file(evidence/"PROJECT-MANIFEST.json"),
             "originalBrowserReceiptSha":sha_file(evidence/"BROWSER-RECEIPT.json"),
             "sourceFiles":len(source),
             "originalWasiCases":len(spec["acceptance"]),
             "originalBrowserCases":browser["testCount"]}
        write_json(evidence/"PACKAGE-RECEIPT.json",receipt,new=True)
        event(evidence/"journal.jsonl","REPO_ACCEPTED_EXPORT",
            {"archiveSha":receipt["archiveSha256"],
             "receiptSha":sha_file(evidence/"PACKAGE-RECEIPT.json")})
    return {"status":"REPO_BROWSER_WASI_E2E_PASS","verify":verify(root,jobid)}

def verify(root,jobid):
    root=engine.init(root)
    d,spec,m,compiled,source=_original(root,jobid)
    folder=root/"repoexports"
    archive=folder/("AF-REPO-"+jobid+".zip")
    receipt_dir=folder/("AF-REPO-"+jobid+"-receipts")
    report=load(receipt_dir/"PACKAGE-RECEIPT.json")
    manifest=load(receipt_dir/"PROJECT-MANIFEST.json")
    browser=load(receipt_dir/"BROWSER-RECEIPT.json")
    if (report["status"]!="REPO_BROWSER_WASI_E2E_PASS"
        or not archive.is_file() or sha_file(archive)!=report["archiveSha256"]
        or sha_file(d/"manifest.json")!=report["originalModelManifestSha"]
        or manifest["originalModelBundleSha"]!=sha_file(compiled)
        or manifest["originalBrowserReceiptSha"]!=sha_file(receipt_dir/"BROWSER-RECEIPT.json")
        or report["originalBrowserCases"]!=len(spec["acceptance"])
        or browser["status"]!="PASS" or browser["passed"]!=len(spec["acceptance"])
        or browser["externalFetchBlocked"] is not True):
        raise RuntimeError("REPO_BROWSER_PACKAGE_OR_ORIGINAL_WASI_SHA_DRIFT")
    with zipfile.ZipFile(archive) as z:
        names=z.namelist()
        if len(names)!=len(set(names)) or set(names)!=set(manifest["files"])|{"MANIFEST.json","BROWSER-RECEIPT.json"}:
            raise RuntimeError("REPO_ARCHIVE_ENTRY_SET_CHANGED")
        if json.loads(z.read("MANIFEST.json"))!=manifest:
            raise RuntimeError("REPO_ARCHIVE_MANIFEST_NOT_ORIGINAL")
        for relative,sha in manifest["files"].items():
            if sha_bytes(z.read(relative))!=sha:
                raise RuntimeError("REPO_ARCHIVE_FILE_HASH_CHANGED:"+relative)
        if sha_bytes(z.read("logic.js"))!=m["bundleSha"]:
            raise RuntimeError("BROWSER_EXECUTED_CODE_NOT_ORIGINAL_WASI_SOURCE")
    verify_journal(receipt_dir/"journal.jsonl")
    return {"verified":True,"status":"REPO_BROWSER_WASI_E2E_PASS",
            "jobId":jobid,"archive":str(archive),
            "archiveSha256":sha_file(archive),
            "ownerWasiCases":len(spec["acceptance"]),
            "browserE2eCases":len(spec["acceptance"]),
            "modelSourceFiles":len(source),
            "pinnedDependencies":spec["dependencies"],
            "nativeEditorRan":False}
