# coding: utf-8
"""R76 original first-party reference app exporter for existing AUTOFABRICADOR.

Exports only a SHA-pinned candidate package built from accepted R75 model code,
reviewed R76 runtime code, and separately built native Android debug APK.
This is not open-domain autonomous programming, runtime Host installation,
or permission to execute untrusted packages.
"""
from __future__ import annotations
import hashlib,json,os,shutil,stat,zipfile
from pathlib import Path,PurePosixPath

VERSION="AF.R76.REFERENCE-APPS.1"
PIN="80a1eabc202926a1690df840732899bce2f015f65b0d86efe1e82e3413c359e6"
NAME="AUTOFABRICADOR-R76-REFERENCE-SUITE-CANDIDATE.zip"
DEST="AF-R76-REFERENCE-SUITE-"+PIN[:16]+".zip"
STATUS="PASS_BOUNDED_REFERENCE_NOT_UNIVERSAL"
R75_2D_SHA="20ff069b2506c99d9c74d9cc804169d99f548baa1adbe5da17bfb77934350412"
R75_3D_SHA="aeeff001662f47210319c5fcc28ec6409088209441f7f433466ec8152575d124"
R76_REPAIRED_API_SHA="4c02da570012293726767ae21360456beafb68ccfecabfbec641080e7788a663"
APK_SHA="ce33408272e14db655cb3137b7f568755b5dc4c59e8a109b35b9f47020e0295a"

def _sha(path):
 h=hashlib.sha256()
 with Path(path).open("rb") as f:
  for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
 return h.hexdigest()
def capabilities():
 return {"schema":1,"version":VERSION,
   "status":STATUS,"generalFactoryActive":False,
   "families":{
      "web-local-sqlite-auth":"PASS_REFERENCE_APP_ORIGINAL_E2E",
      "game-2d-canvas":"PASS_REFERENCE_APP_ORIGINAL_E2E",
      "game-3d-webgl2":"PASS_REFERENCE_APP_ORIGINAL_E2E",
      "ai-local-qwen9b":"PASS_ORIGINAL_AUTHENTICATED_HTTP_REAL_MODEL",
      "android-csharp":"PASS_SIGNED_DEBUG_APK_BUILD_DEVICE_E2E_BLOCKED"},
   "packageFullySelfContained":False,
   "requiresPythonRuntime":True,"requiresExternalModelForAI":True,
   "androidPhysicalDeviceE2E":False,
   "secondPhysicalPCVerified":False,
   "noBootServiceOrAutoStart":True,
   "notGeneralAutonomousCodeGeneration":True}
def preflight(root):
 path=Path(root).resolve()/"TEMPLATES"/"R76"/NAME
 if not path.is_file() or path.is_symlink() or _sha(path)!=PIN:
  raise RuntimeError("R76_TEMPLATE_PINNED_ARCHIVE_MISSING_OR_SHA_DRIFT")
 with zipfile.ZipFile(path) as z:
  names=z.namelist()
  if len(names)!=len(set(names)) or len(names)>64 or z.testzip() is not None:
   raise RuntimeError("R76_ZIP_CRC_OR_DUPLICATE_NAMES")
  manifest=json.loads(z.read("MANIFEST.json"))
  if manifest.get("product")!="AF.R76.INTEGRATED-REFERENCE-CANDIDATE" or manifest.get("status")!="CANDIDATE_NOT_ACTIVE":
   raise RuntimeError("R76_TEMPLATE_MANIFEST_SCOPE_CHANGED")
  entries=manifest.get("entries")
  if not isinstance(entries,dict) or set(names)!=set(entries)|{"MANIFEST.json"}:
   raise RuntimeError("R76_ZIP_ENTRY_SET_DRIFT")
  total=0
  for entry in z.infolist():
   parts=PurePosixPath(entry.filename).parts
   if (not parts or entry.is_dir() or entry.filename.startswith("/") or
       "\\" in entry.filename or ".." in parts or ":" in entry.filename):
    raise RuntimeError("R76_ZIP_UNSAFE_PATH")
   if stat.S_IFMT(entry.external_attr >> 16) == stat.S_IFLNK:
    raise RuntimeError("R76_ZIP_SYMLINK_DENIED")
   total+=entry.file_size
   if total>35*1024*1024:raise RuntimeError("R76_ZIP_EXPANSION_LIMIT")
   if entry.filename in entries and hashlib.sha256(z.read(entry.filename)).hexdigest()!=entries[entry.filename]:
    raise RuntimeError("R76_ZIP_INDIVIDUAL_SOURCE_SHA_CHANGED:"+entry.filename)
  expected={
   "application/logic-2d-r75.js":R75_2D_SHA,
   "application/logic-3d-r75.js":R75_3D_SHA,
   "application/logic-api-r76.js":R76_REPAIRED_API_SHA,
   "android-debug/AF-R76-Labyrinth-debug-signed.apk":APK_SHA}
  for name,pin in expected.items():
   if entries.get(name)!=pin:raise RuntimeError("R76_R75_OR_ANDROID_ORIGINAL_SOURCE_SHA_DRIFT:"+name)
  if manifest.get("nativeAPKDeviceE2E") is not False or manifest.get("generalAutofabricadorComplete") is not False:
   raise RuntimeError("R76_UNPROVEN_ACTIVE_CLAIM_DENIED")
 return {"schema":1,"status":STATUS,"version":VERSION,
   "archive":str(path),"archiveSha":PIN,"entryCount":len(names),
   "applicationReferenceTestsClaimed":manifest.get("backendHTTPAndChromiumTests"),
   "noModelBinaryBundled":not manifest.get("modelBinaryBundled"),
   "notUniversal":True,"mobileHardwareNotProven":True}
def _receipt_file(root):
 return Path(root).resolve()/"apps"/("R76-REFERENCE-SUITE-"+PIN[:16]+".receipt.json")
def verify(root):
 trusted=preflight(root)
 path=Path(root).resolve()/"apps"/DEST
 receipt=_receipt_file(root)
 if not path.exists() and not receipt.exists():
  return {**trusted,"deliveryStatus":"NOT_EXPORTED_YET","verified":True}
 if not path.is_file() or not receipt.is_file():
  raise RuntimeError("R76_EXPORT_UNCERTAIN_MISSING_PAIR_RECONCILE")
 if _sha(path)!=PIN:raise RuntimeError("R76_EXPORTED_ARCHIVE_SHA_DRIFT")
 row=json.loads(receipt.read_text(encoding="utf8"))
 if row.get("archiveSHA")!=PIN or row.get("status")!="PASS_EXPORTED_BOUND_REFERENCE_NOT_ACTIVE":
  raise RuntimeError("R76_ORIGINAL_EXPORT_RECEIPT_CHANGED")
 return {**trusted,"deliveryStatus":"PASS_EXPORTED_BOUND_REFERENCE_NOT_ACTIVE",
   "export":str(path),"receipt":str(receipt),"receiptSHA":_sha(receipt),
   "verified":True}
def export(root):
 found=preflight(root)
 directory=Path(root).resolve()/"apps"
 dest=directory/DEST;receipt=_receipt_file(root)
 if dest.exists() or receipt.exists():
  return {**verify(root),"replayed":False}
 directory.mkdir(parents=True,exist_ok=True)
 temp=directory/(DEST+".R76-STAGED-TEMP")
 if temp.exists():raise RuntimeError("R76_STAGING_UNCERTAIN_DO_NOT_OVERWRITE")
 source=Path(found["archive"])
 shutil.copy2(source,temp)
 if _sha(temp)!=PIN:raise RuntimeError("R76_STAGED_ARCHIVE_SHA_MISMATCH")
 os.replace(temp,dest)
 if _sha(dest)!=PIN:raise RuntimeError("R76_EXPORT_READBACK_SHA_CHANGED")
 row={"schema":1,"version":VERSION,"status":"PASS_EXPORTED_BOUND_REFERENCE_NOT_ACTIVE",
   "archiveSHA":PIN,"archive":str(dest),
   "originalTemplateSHA":PIN,"noSystemInstall":True,"noModelCalls":True,
   "notUniversallyAccepted":True}
 with receipt.open("x",encoding="utf8") as f:
  json.dump(row,f,indent=2,sort_keys=True);f.write("\n")
 return {**verify(root),"replayed":False}
