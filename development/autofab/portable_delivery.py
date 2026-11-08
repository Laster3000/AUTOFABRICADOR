# coding: utf-8
"""Immutable, useful portable output from ORIGINAL WASI + native-guest-approved source.

Builds a static offline UI and complete source ZIP with trusted first-party
templates. No model-generated program is run on Windows Host by this exporter.
Browser E2E, native owner authentication, and installed application are NOT
claimed. Original WASI owner acceptance is independently verified.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import zipfile

from . import engine,repo_factory,repo_graph,native_cycle,webapps
from .storage import event,load,sha_file,sha_bytes,json_bytes,utc,verify_journal,write_json

NAME=re.compile(r"FC-[0-9a-f]{16}\Z")

def _base(root,workflow):
    if not isinstance(workflow,str) or not NAME.fullmatch(workflow):
        raise ValueError("PORTABLE_DELIVERY_WORKFLOW_ID_INVALID")
    root=Path(root).resolve()
    where=root/"factoryexports"/workflow
    archive=where/("AUTOFABRICADOR-"+workflow+"-PORTABLE.zip")
    return where,archive

def _source(root,workflow):
    from . import factory_pipeline
    root=engine.init(root)
    original=factory_pipeline.reconcile(root,workflow)
    if original["status"]!=factory_pipeline.SUCCESS or original.get("resultReceiptSha") is None:
        raise RuntimeError("PORTABLE_DELIVERY_REQUIRES_ORIGINAL_PASS")
    result=load(root/"factoryjobs"/workflow/"result.json")
    if (result["status"]!=factory_pipeline.SUCCESS
        or not result["originalOwnerWasiAccepted"]
        or result["nativeGuestCryptographicOwnerAcceptance"]
        or not result["sandboxGuestSessionClosed"]):
        raise RuntimeError("PORTABLE_DELIVERY_ORIGINAL_CONTRACT_INVALID")
    repo=result["originalRepoJobId"]
    accepted=repo_factory.verify(root,repo)
    if not accepted["verified"] or accepted["ownerCases"]!=result["originalOwnerCases"]:
        raise RuntimeError("PORTABLE_DELIVERY_OWNER_WASI_ACCEPTANCE_DRIFT")
    n=native_cycle.reconcile(root,result["nativeCycleId"])
    if n["status"]!=native_cycle.OK or n.get("originalResultStatus")!=native_cycle.OK:
        raise RuntimeError("PORTABLE_DELIVERY_NATIVE_ORIGINAL_RECEIPT_DRIFT")
    rp=root/"repojobs"/repo
    manifest=load(rp/"manifest.json")
    spec=load(rp/"spec.json")
    repo_graph._valid_spec(spec)
    if sha_file(rp/"manifest.json")!=result["originalRepoManifestSha"]:
        raise RuntimeError("PORTABLE_DELIVERY_REPO_MANIFEST_DRIFT")
    if sha_file(rp/"spec.json")!=manifest["specSha"]:
        raise RuntimeError("PORTABLE_DELIVERY_OWNER_SPEC_DRIFT")
    prefix=rp/"attempts"/("A-%02d"%manifest["selectedAttempt"])
    source=Path(str(prefix)+"-source.json")
    bundle=Path(str(prefix)+"-bundle.js")
    if sha_file(source)!=manifest["originalSourceSha"] or sha_file(bundle)!=manifest["bundleSha"]:
        raise RuntimeError("PORTABLE_DELIVERY_MODEL_SOURCE_DRIFT")
    files=load(source)["files"]
    repo_graph._static_source_guard(files)
    if set(files)!=set(spec["sources"]):
        raise RuntimeError("PORTABLE_DELIVERY_SOURCE_MODULES_CHANGED")
    if result["originalOwnerCases"]!=len(spec["acceptance"]):
        raise RuntimeError("PORTABLE_DELIVERY_OWNER_COUNT_CHANGED")
    return root,result,spec,files,bundle,manifest

def _payload(root,workflow,result,spec,files,bundle,manifest):
    # All HTML/JS wrappers here are ORIGINAL first-party strings, not
    # model inference, and are NOT executed on Windows Host.
    browser={"function":spec["exportName"],"acceptance":spec["acceptance"]}
    payload={
      "index.html":webapps._page(result["originalRepoJobId"],browser,{}).encode("utf-8"),
      "styles.css":webapps._css().encode("utf-8"),
      "controller.js":webapps._controller(
          spec["exportName"],len(spec["acceptance"][0]["args"])).encode("utf-8"),
      "logic.js":bundle.read_bytes(),
      "owner-cases.json":json_bytes(spec["acceptance"]),
      "package.json":json_bytes({
          "name":"autofabricador-"+workflow.lower(),"version":"0.1.0",
          "type":"module","private":True,"scripts":{},
          "description":"AI-generated sources independently accepted under WASI"
      }),
      "README.txt":(
          "AUTOFABRICADOR portable candidate; not installed or ACTIVE.\n"
          "Open index.html manually in a compatible web browser.\n"
          "The model-generated source has passed the original independent WASI\n"
          "owner cases and its native Sandbox guest report was correlated.\n"
          "The browser interface included here was NOT independently tested\n"
          "by a browser in this delivery; its runtime remains untrusted until verified.\n"
          "No npm installation or lifecycle commands are authorized.\n"
          "Do not treat guest output as cryptographic native owner attestation.\n"
      ).encode("utf-8")
    }
    for name,value in files.items():
        payload[name]=value.encode("utf-8")
    checks={key:sha_bytes(value) for key,value in payload.items()}
    receipt={"schema":1,"atUtc":utc(),"workflowId":workflow,
          "status":"PORTABLE_SOURCE_WASI_OWNER_PASS_NATIVE_GUEST_CORRELATED",
          "files":checks,"originalOwnerCaseCount":len(spec["acceptance"]),
          "originalFactoryResultSha":sha_file(root/"factoryjobs"/workflow/"result.json"),
          "originalRepoManifestSha":sha_file(
               root/"repojobs"/result["originalRepoJobId"]/"manifest.json"),
          "originalWasiOwnerReceiptSha":manifest["originalWasiReceiptSha"],
          "originalCompiledModelBundleSha":manifest["bundleSha"],
          "originalNativeCycleReceiptSha":result["originalNativeCycleReceiptSha"],
          "nativeGuestOutputUntrusted":True,
          "nativeGuestCryptographicOwnerAcceptance":False,
          "browserExecutionClaimed":False,
          "noModelCodeExecutedOnHostByExporter":True,
          "protectedHostInstallation":False}
    payload["MANIFEST.json"]=json_bytes(receipt)
    return payload,receipt

def deliver(root,workflow):
    root=engine.init(root)
    where,archive=_base(root,workflow)
    if where.exists():
        if archive.is_file() and (where/"receipt.json").is_file():
            return {"status":"PREEXISTING_VERIFIED_NO_REPLAY",
                    "result":verify(root,workflow)}
        raise RuntimeError("PORTABLE_DELIVERY_ORIGINAL_INTENT_PARTIAL_RECONCILE")
    root,result,spec,files,bundle,manifest=_source(root,workflow)
    payload,record=_payload(root,workflow,result,spec,files,bundle,manifest)
    where.parent.mkdir(exist_ok=True)
    where.mkdir(exist_ok=False)
    event(where/"journal.jsonl","DELIVERY_OWNER_INTENT",
          {"workflowId":workflow,
           "factoryResultSha":record["originalFactoryResultSha"],
           "sourceBundleSha":record["originalCompiledModelBundleSha"]})
    write_json(where/"manifest.json",record,new=True)
    with zipfile.ZipFile(archive,"x",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,bytesval in sorted(payload.items()):
            z.writestr(name,bytesval)
    with zipfile.ZipFile(archive) as z:
        assert set(z.namelist())==set(payload)
        for name,content in payload.items():
            if z.read(name)!=content:raise RuntimeError("PORTABLE_DELIVERY_ZIP_READBACK_DRIFT")
    receipt={"schema":1,"workflowId":workflow,"atUtc":utc(),
             "status":"PORTABLE_DELIVERY_SHA_VERIFIED_NOT_INSTALLED",
             "manifestSha":sha_file(where/"manifest.json"),
             "archiveSha":sha_file(archive),
             "files":len(payload),"ownerCases":len(spec["acceptance"]),
             "guestTrusted":False,"browserOwnerVerified":False,
             "originalWasiAccepted":True}
    write_json(where/"receipt.json",receipt,new=True)
    event(where/"journal.jsonl","DELIVERY_ORIGINAL_RECEIPT",
          {"archiveSha":sha_file(archive),"receiptSha":sha_file(where/"receipt.json")})
    return {"status":"DELIVERED_PORTABLE_SOURCE_CANDIDATE",
            "result":verify(root,workflow)}

def verify(root,workflow):
    root=engine.init(root)
    where,archive=_base(root,workflow)
    if not archive.is_file() or not (where/"receipt.json").is_file():
        raise RuntimeError("PORTABLE_DELIVERY_REQUIRED_FILES_MISSING")
    root,result,spec,files,bundle,manifest=_source(root,workflow)
    row=load(where/"receipt.json")
    data=load(where/"manifest.json")
    if (row["status"]!="PORTABLE_DELIVERY_SHA_VERIFIED_NOT_INSTALLED"
        or row["archiveSha"]!=sha_file(archive)
        or row["manifestSha"]!=sha_file(where/"manifest.json")
        or row["ownerCases"]!=len(spec["acceptance"])
        or row["browserOwnerVerified"] is not False
        or data["originalFactoryResultSha"]!=sha_file(
            root/"factoryjobs"/workflow/"result.json")
        or data["originalCompiledModelBundleSha"]!=sha_file(bundle)):
        raise RuntimeError("PORTABLE_DELIVERY_SOURCE_OR_RECEIPT_MISMATCH")
    with zipfile.ZipFile(archive) as z:
        names=z.namelist()
        if len(names)!=len(set(names)) or set(names)!=set(data["files"])|{"MANIFEST.json"}:
            raise RuntimeError("PORTABLE_DELIVERY_FILES_SET_DRIFT")
        if json.loads(z.read("MANIFEST.json"))!=data:
            raise RuntimeError("PORTABLE_DELIVERY_INTERNAL_MANIFEST_DRIFT")
        for name,expected in data["files"].items():
            if sha_bytes(z.read(name))!=expected:
                raise RuntimeError("PORTABLE_DELIVERY_ARCHIVE_FILE_SHA_DRIFT:"+name)
        if sha_bytes(z.read("logic.js"))!=manifest["bundleSha"]:
            raise RuntimeError("PORTABLE_DELIVERY_EXECUTABLE_DIFFERS_FROM_WASI")
    verify_journal(where/"journal.jsonl")
    return {"verified":True,"status":row["status"],"archive":str(archive),
            "archiveSha":sha_file(archive),"files":row["files"],
            "ownerWasiCases":row["ownerCases"],"nativeGuestUntrusted":True,
            "browserRuntimeNotOwnerVerified":True,
            "installStatus":"CANDIDATE_NOT_INSTALLED"}
