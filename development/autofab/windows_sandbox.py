# coding: utf-8
"""Windows Sandbox native source execution GATE; fail closed unless OS VM exists.

Windows Sandbox must be an enabled, independently authenticated Windows
feature, never an in-process subprocess/JOB-OBJECT/low-integrity token.
No native repo sources, scripts, generated code or executables are run
on the Windows host by any code path in this module.

This module can STAGE and test input/WSB policies offline with disabled OS
feature. It cannot claim native E2E acceptance without running a real VM.
Guest-written outputs are untrusted, including "passed" or "signed" claims.
"""
from __future__ import annotations
from pathlib import Path,PurePosixPath
import hashlib,json,os,re,secrets,shutil,stat,subprocess,uuid,zipfile
import xml.etree.ElementTree as ET
from . import engine
from .storage import load,sha_file,sha_bytes,json_bytes,utc,write,write_json,transition,event,verify_journal

JOB_ID=re.compile(r"SX-[a-f0-9]{16}\Z")
STEP=re.compile(r"(?:[A-Za-z0-9_-]+/)*[A-Za-z0-9_-]+\.ps1\Z")
FORBIDDEN_WIN=frozenset(("con","prn","aux","nul",*(f"com{i}" for i in range(1,10)),
                         *(f"lpt{i}" for i in range(1,10))))
LIMIT_BYTES=110*1024*1024
ZIP_LIMIT=45*1024*1024
MAX_FILES=600
GUEST_BOOT="qa/windows_sandbox_guest.ps1"
SECURITY={
 "vGPU":"Disable","Networking":"Disable","AudioInput":"Disable",
 "VideoInput":"Disable","ProtectedClient":"Enable",
 "PrinterRedirection":"Disable","ClipboardRedirection":"Disable",
 "MemoryInMB":"4096",
}
# A single computer allows at most one Windows Sandbox; NEVER auto-relaunch
# if any previous launch intent exists, even if the GUI process has exited.

def _path(root,jid):
    if not isinstance(jid,str) or not JOB_ID.fullmatch(jid):
        raise ValueError("SANDBOX_JOB_ID_UNSAFE")
    directory=Path(root).resolve()/"sandboxjobs"/jid
    if not directory.is_dir():raise FileNotFoundError("SANDBOX_JOB_DOES_NOT_EXIST")
    return directory

def _feature_status():
    if os.name!="nt":
        return {"state":"UNAVAILABLE_NON_WINDOWS","details":"Windows Sandbox is Windows-only"}
    query=("try {"
      "$p=Get-WindowsOptionalFeature -Online -FeatureName 'Containers-DisposableClientVM' -ErrorAction Stop;"
      "$p.State.ToString()"
      "}catch{'FEATURE_READ_ERROR'}")
    try:
        result=subprocess.run(["powershell.exe","-NoProfile","-NonInteractive",
                               "-Command",query],capture_output=True,
                              timeout=14,stdin=subprocess.DEVNULL)
        text=result.stdout.decode("utf-8","replace").strip()
        if result.returncode or text not in ("Enabled","Disabled",
             "EnablePending","DisablePending"):
            return {"state":"UNKNOWN_FEATURE_READBACK","details":text[:150]}
        return {"state":text}
    except (OSError,subprocess.TimeoutExpired):
        return {"state":"UNKNOWN_FEATURE_QUERY"}

def preflight(root):
    p=Path(root).resolve()
    feature=_feature_status()
    exe=Path(os.environ.get("SystemRoot",r"C:\Windows"))/"System32"/"WindowsSandbox.exe"
    # Never use PATH lookup or user-supplied binary for the security boundary.
    available=(feature["state"]=="Enabled" and exe.is_file() and
               os.name=="nt" and str(exe).casefold().startswith(
                     r"c:\windows\system32\windowssandbox.exe"))
    if available: status="AVAILABLE_NOT_YET_E2E_PROVEN"
    elif feature["state"]=="Disabled":status="BLOCKED_OS_SANDBOX_FEATURE_DISABLED"
    elif feature["state"] in ("EnablePending","DisablePending"):
        status="BLOCKED_OS_FEATURE_PENDING_REBOOT_OR_ACTIVATION"
    else:status="BLOCKED_OS_ISOLATION_NOT_VERIFIED"
    return {"schema":1,"status":status,"feature":"Containers-DisposableClientVM",
            "featureState":feature["state"],"windowsSandboxExe":str(exe),
            "windowsSandboxExePresent":exe.is_file(),
            "networkPolicy":"DISABLE","clipboardPolicy":"DISABLE",
            "mappingPolicy":"EXACTLY_PRIVATE_SOURCE_READ_ONLY_PLUS_EMPTY_OUTPUT",
            "nativeHostCodeExecutionAllowed":False,
            "guestUntrustedReportsAreAcceptance":False,
            "workspaceRoot":str(p),"realGuestBootProven":False}

def _check_entry_name(s):
    candidate=PurePosixPath(s)
    rawparts=s.split("/")
    if (candidate.is_absolute() or not s or "\\" in s or ":" in s
        or "\x00" in s or s.startswith("/") or s.endswith("/")
        or len(s)>240 or len(rawparts)>12
        or any(part in ("", ".", "..") or part[-1] in ". "
            or part.split(".")[0].lower() in FORBIDDEN_WIN for part in rawparts)):
        raise ValueError("SANDBOX_ZIP_UNSAFE_WIN_PATH")
    return True

def _zip_info(path):
    if not path.is_file() or path.is_symlink() or path.stat().st_size>ZIP_LIMIT:
        raise ValueError("SANDBOX_REPO_ZIP_MISSING_LINKED_OR_TOO_LARGE")
    if not zipfile.is_zipfile(path):
        raise ValueError("SANDBOX_REPO_INPUT_NOT_ZIP")
    original={}
    with zipfile.ZipFile(path) as z:
        members=z.infolist()
        if not 2<=len(members)<=MAX_FILES:raise ValueError("SANDBOX_ZIP_ENTRIES_LIMIT")
        for item in members:
            s=item.filename
            _check_entry_name(s)
            if stat.S_ISLNK(item.external_attr>>16) or item.is_dir():
                raise ValueError("SANDBOX_ZIP_LINK_OR_DIRECTORY_ENTRY")
            if (item.file_size>LIMIT_BYTES or item.file_size<0
                or item.compress_size<0 or
                (item.compress_size==0 and item.file_size>0)
                or (item.compress_size and item.file_size/item.compress_size>250)):
                raise ValueError("SANDBOX_ZIP_ENTRY_ZIP_BOMB")
            if s.casefold() in original:raise ValueError("SANDBOX_ZIP_DUPLICATE_WIN_NAME")
            original[s.casefold()]={"name":s,"bytes":item.file_size,"compressedBytes":item.compress_size}
        if sum(row["bytes"] for row in original.values())>LIMIT_BYTES:
            raise ValueError("SANDBOX_ZIP_TOTAL_DECOMPRESSED_LIMIT")
    return original

def _owner_contract(path,source_names):
    data=load(path)
    if not isinstance(data,dict) or set(data)!={"schema","goal","steps","kind"}:
        raise ValueError("SANDBOX_OWNER_CONTRACT_SCHEMA")
    if (data["schema"]!=1 or data["kind"]!="powershell"
        or not isinstance(data["goal"],str) or not 20<=len(data["goal"])<=3500
        or not isinstance(data["steps"],list) or not 1<=len(data["steps"])<=6):
        raise ValueError("SANDBOX_OWNER_CONTRACT_INVALID")
    for step in data["steps"]:
        if not isinstance(step,dict) or set(step)!={"script"}:
            raise ValueError("SANDBOX_OWNER_STEP_NOT_SCRIPT")
        script=step["script"]
        if not isinstance(script,str) or not STEP.fullmatch(script) or script.casefold() not in source_names:
            raise ValueError("SANDBOX_OWNER_SCRIPT_NOT_SOURCE_PINNED")
    return data

def _profile(input_path,output_path):
    config=ET.Element("Configuration")
    for key,value in SECURITY.items():
        ET.SubElement(config,key).text=value
    folders=ET.SubElement(config,"MappedFolders")
    for host,guest,ro in (
        (input_path,r"C:\AFInput","true"),
        (output_path,r"C:\AFOutput","false")):
        entry=ET.SubElement(folders,"MappedFolder")
        ET.SubElement(entry,"HostFolder").text=str(host)
        ET.SubElement(entry,"SandboxFolder").text=guest
        ET.SubElement(entry,"ReadOnly").text=ro
    command=ET.SubElement(config,"LogonCommand")
    ET.SubElement(command,"Command").text=(
        r"powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File C:\AFInput\boot.ps1")
    return ET.tostring(config,encoding="utf-8",xml_declaration=True)

def _assert_profile(jobdir):
    path=jobdir/"launch.wsb"
    if not path.is_file() or path.is_symlink():raise RuntimeError("SANDBOX_PROFILE_NOT_REGULAR")
    root=ET.parse(path).getroot()
    if root.tag!="Configuration" or set(x.tag for x in root)!=set(SECURITY)|{"MappedFolders","LogonCommand"}:
        raise RuntimeError("SANDBOX_WSB_UNEXPECTED_ELEMENTS")
    if any(root.findtext(key)!=value for key,value in SECURITY.items()):
        raise RuntimeError("SANDBOX_WSB_SECURITY_DOWNGRADED")
    entries=root.findall("./MappedFolders/MappedFolder")
    if len(entries)!=2:raise RuntimeError("SANDBOX_WSB_EXTRA_MOUNT")
    expected=((jobdir/"input",r"C:\AFInput","true"),
              (jobdir/"output",r"C:\AFOutput","false"))
    for entry,(host,guest,ro) in zip(entries,expected):
        if (entry.findtext("HostFolder")!=str(host)
            or entry.findtext("SandboxFolder")!=guest
            or entry.findtext("ReadOnly")!=ro
            or set(x.tag for x in entry)!={"HostFolder","SandboxFolder","ReadOnly"}):
            raise RuntimeError("SANDBOX_WSB_MAPPING_NOT_EXACT_OWNER")
    if root.findtext("./LogonCommand/Command")!=(
            r"powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File C:\AFInput\boot.ps1"):
        raise RuntimeError("SANDBOX_WSB_GUEST_BOOT_COMMAND_NOT_OWNED")
    return True

def stage(root,source_zip,contract_path):
    root=engine.init(root)
    root=Path(root).resolve()
    src=Path(source_zip).resolve()
    owner=Path(contract_path).resolve()
    # Only project-controlled intake; do not stage private user home, MMC7,
    # C:\Windows, D:\LABORATORIO or any implicit Host file.
    if (not src.is_relative_to(root/"examples") or
        not owner.is_relative_to(root/"examples") or
        src.is_symlink() or owner.is_symlink() or not owner.is_file()):
        raise ValueError("SANDBOX_SOURCE_AND_OWNER_MUST_BE_PROJECT_EXAMPLES")
    entries=_zip_info(src)
    spec=_owner_contract(owner,entries)
    bootstrap=root/GUEST_BOOT
    if not bootstrap.is_file() or bootstrap.is_symlink():
        raise RuntimeError("SANDBOX_TRUSTED_GUEST_SCRIPT_MISSING")
    if bootstrap.stat().st_size>30000:raise RuntimeError("SANDBOX_BOOT_SCRIPT_TOO_LARGE")
    original_zip_sha=sha_file(src)
    owner_sha=sha_file(owner)
    for folder in (root/"sandboxjobs").glob("SX-*"):
        manifest=folder/"manifest.json"
        if manifest.is_file():
            known=load(manifest)
            if known.get("sourceOriginalSha")==original_zip_sha and known.get("ownerOriginalSha")==owner_sha:
                return {"jobId":folder.name,"status":"EXISTING_STAGED_NO_DUPLICATE_SOURCE",
                        "verify":verify(root,folder.name)}
    jid="SX-"+uuid.uuid4().hex[:16]
    folder=root/"sandboxjobs"/jid
    inputs=folder/"input"
    outputs=folder/"output"
    inputs.mkdir(parents=True,exist_ok=False)
    outputs.mkdir()
    with src.open("rb") as a,(inputs/"source.zip").open("xb") as b:
        shutil.copyfileobj(a,b,1024*1024);b.flush();os.fsync(b.fileno())
    if sha_file(inputs/"source.zip")!=original_zip_sha:
        raise RuntimeError("SANDBOX_STAGED_SOURCE_COPY_SHA_DRIFT")
    with bootstrap.open("rb") as a,(inputs/"boot.ps1").open("xb") as b:
        shutil.copyfileobj(a,b,1024*1024);b.flush();os.fsync(b.fileno())
    if sha_file(inputs/"boot.ps1")!=sha_file(bootstrap):
        raise RuntimeError("SANDBOX_STAGED_BOOT_SOURCE_SHA_DRIFT")
    nonce=secrets.token_hex(16)
    guestowner={"schema":1,"jobId":jid,"nonce":nonce,
        "sourceSha256":original_zip_sha,"steps":spec["steps"]}
    write_json(inputs/"owner.json",guestowner,new=True)
    wsb=_profile(inputs,outputs)
    write(folder/"launch.wsb",wsb,new=True)
    _assert_profile(folder)
    manifest={"schema":1,"atUtc":utc(),"jobId":jid,
        "status":"STAGED_NO_VM_EXECUTION",
        "originalSourcePath":str(src),"sourceOriginalSha":original_zip_sha,
        "originalInputFileNames":sorted(row["name"] for row in entries.values()),
        "originalEntryCount":len(entries),
        "originalTotalUncompressedBytes":sum(row["bytes"] for row in entries.values()),
        "ownerOriginalPath":str(owner),"ownerOriginalSha":owner_sha,
        "originalGuestBootSha":sha_file(bootstrap),
        "inputSha256":{n:sha_file(inputs/n) for n in ("source.zip","boot.ps1","owner.json")},
        "wsbSha256":sha_file(folder/"launch.wsb"),
        "networkingDisabled":True,"clipboardDisabled":True,
        "guestInputReadOnly":True,"guestOutputIsolatedWritable":True,
        "hostNativeScriptsExecuted":False,
        "operatingSystemSandboxExecuted":False,
        "guestOutputReportsTrustLevel":"UNTRUSTED"}
    write_json(folder/"manifest.json",manifest,new=True)
    write_json(folder/"control.json",{"schema":1,"command":"RUN","version":1,"atUtc":utc()},new=True)
    write_json(folder/"state.json",{"schema":1,"status":"STAGED","atUtc":utc()},new=True)
    event(folder/"journal.jsonl","SANDBOX_STAGE_ORIGINAL",{
        "operationId":jid+".STAGE.1","manifestSha":sha_file(folder/"manifest.json"),
        "sourceSha":original_zip_sha,"ownerSha":owner_sha,
        "wsbSha":manifest["wsbSha256"],"hostNativeExecuted":False})
    return {"jobId":jid,"status":"STAGED_NO_VM_EXECUTION",
            "verify":verify(root,jid),
            "currentHostSandboxCapability":preflight(root)["status"]}

def verify(root,jid):
    jobdir=_path(root,jid)
    manifest=load(jobdir/"manifest.json")
    if manifest["status"]!="STAGED_NO_VM_EXECUTION" or manifest["jobId"]!=jid:
        raise RuntimeError("SANDBOX_MANIFEST_OR_JOB_DRIFT")
    for name,sha in manifest["inputSha256"].items():
        path=jobdir/"input"/name
        if path.is_symlink() or not path.is_file() or sha_file(path)!=sha:
            raise RuntimeError("SANDBOX_INPUT_PREIMAGE_DRIFT:"+name)
    if sha_file(jobdir/"launch.wsb")!=manifest["wsbSha256"]:
        raise RuntimeError("SANDBOX_WSB_SHA_DRIFT")
    _assert_profile(jobdir)
    if not (jobdir/"output").is_dir() or (jobdir/"output").is_symlink():
        raise RuntimeError("SANDBOX_HOST_OUTPUT_SYMLINK_OR_MISSING")
    if sha_file(Path(manifest["ownerOriginalPath"]))!=manifest["ownerOriginalSha"]:
        raise RuntimeError("SANDBOX_ORIGINAL_OWNER_SHA_DRIFT")
    guestowner=load(jobdir/"input/owner.json")
    if (guestowner["jobId"]!=jid or
        guestowner["sourceSha256"]!=manifest["sourceOriginalSha"]):
        raise RuntimeError("SANDBOX_GUEST_OWNER_NOT_PINNED")
    verify_journal(jobdir/"journal.jsonl")
    return {"verified":True,"status":"STAGING_POLICY_AND_SHA_VERIFIED",
        "jobId":jid,"sourceSha":manifest["sourceOriginalSha"],
        "inputReadOnly":True,"networkDisabled":True,
        "clipboardDisabled":True,"mappedPaths":2,
        "nativeCodeExecuted":False,"guestE2ePass":False}

def launch(root,jid):
    root=engine.init(root)
    data=verify(root,jid)
    jobdir=_path(root,jid)
    if load(jobdir/"state.json")["status"]!="STAGED":
        raise RuntimeError("SANDBOX_ORIGINAL_LAUNCH_STATE_NOT_STAGED_NO_REPLAY")
    if load(jobdir/"control.json")["command"]!="RUN":
        return {"jobId":jid,"status":"STOPPED_PRE_SANDBOX_INTENT",
                "originalNativeExecution":False}
    if (jobdir/"launch-intent.json").exists():
        raise RuntimeError("SANDBOX_PREVIOUS_LAUNCH_INTENT_NO_REPLAY")
    feature=preflight(root)
    if feature["status"]!="AVAILABLE_NOT_YET_E2E_PROVEN":
        return {"jobId":jid,"status":feature["status"],
                "featureState":feature["featureState"],
                "launchIntentWritten":False,"hostUntrustedCodeExecuted":False}
    # Execution is delegated EXCLUSIVELY to the real Windows Sandbox binary.
    # This branch requires OS feature Enabled + system32 binary and is NOT
    # yet demonstrated on this PC until Windows Sandbox activation/restart.
    exe=Path(feature["windowsSandboxExe"])
    intent={"schema":1,"atUtc":utc(),"operationId":jid+".WINDOWS_SANDBOX.LAUNCH.1",
        "sourceManifestSha":sha_file(jobdir/"manifest.json"),
        "wsbSha":sha_file(jobdir/"launch.wsb"),
        "osFeatureState":"Enabled","systemSandboxExeSha":sha_file(exe),
        "hostNativeCodeExecuted":False}
    write_json(jobdir/"launch-intent.json",intent,new=True)
    event(jobdir/"journal.jsonl","WINDOWS_SANDBOX_LAUNCH_INTENT",
          {"intentSha":sha_file(jobdir/"launch-intent.json"),
           "operationId":intent["operationId"]})
    transition(jobdir/"state.json",{"schema":1,"status":"LAUNCH_INTENT_WRITTEN",
                  "atUtc":utc()},jobdir/"history")
    proc=subprocess.Popen([str(exe),str(jobdir/"launch.wsb")],
            stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,close_fds=True)
    event(jobdir/"journal.jsonl","WINDOWS_SANDBOX_GUI_LAUNCH_RETURNED",
       {"originalWindowsSandboxPid":proc.pid,"featureStatus":"Enabled",
        "guestProcessOrOwnerReceiptIndependentlyVerified":False})
    transition(jobdir/"state.json",
       {"schema":1,"status":"LAUNCHED_GUEST_NOT_ATTESTED","atUtc":utc(),
        "originalWindowsSandboxPid":proc.pid},jobdir/"history")
    return {"jobId":jid,"status":"LAUNCHED_GUEST_NOT_ATTESTED",
            "windowsSandboxPid":proc.pid,"nativeAcceptance":False}

def stop(root,jid):
    d=_path(root,jid)
    state=load(d/"state.json")["status"]
    if state=="STAGED":
        state0=load(d/"control.json")
        if state0["command"]=="STOP":return {"status":"ALREADY_STOPPED_BEFORE_LAUNCH"}
        transition(d/"control.json",{"schema":1,"command":"STOP","version":state0["version"]+1,
            "previousSha":sha_file(d/"control.json"),"atUtc":utc()},d/"history")
        event(d/"journal.jsonl","STOP_PRE_LAUNCH",
              {"controlSha":sha_file(d/"control.json")})
        return {"status":"STOP_REQUESTED_PRE_LAUNCH","guestExecuted":False}
    if state in ("LAUNCH_INTENT_WRITTEN","LAUNCHED_GUEST_NOT_ATTESTED"):
        stopfile=d/"output/STOP.REQUEST"
        if not stopfile.exists():write(stopfile,b"STOP\n",new=True)
        event(d/"journal.jsonl","GUEST_COOPERATIVE_STOP_REQUESTED",
             {"stopSha":sha_file(stopfile),"guaranteedGuestStop":False})
        return {"status":"STOP_REQUESTED_GUEST_UNVERIFIED","guestMustCooperate":True}
    return {"status":"UNHANDLED_OR_TERMINAL_NO_REPLAY","originalState":state}

def reconcile(root,jid):
    verified=verify(root,jid)
    folder=_path(root,jid)
    report=folder/"output/guest-report.json"
    if not report.exists():
        return {**verified,"status":"NO_ORIGINAL_GUEST_RECEIPT",
                "nativeAcceptance":False}
    if report.is_symlink() or not report.is_file() or report.stat().st_size>15000:
        raise RuntimeError("SANDBOX_OUTPUT_GUEST_REPORT_UNSAFE")
    obj=load(report)
    owner=load(folder/"input/owner.json")
    if (not isinstance(obj,dict) or obj.get("originalJobId")!=jid or
        obj.get("nonce")!=owner["nonce"] or
        obj.get("originalZipSha256")!=owner["sourceSha256"]):
        raise RuntimeError("SANDBOX_GUEST_CLAIM_WRONG_JOB_OR_SOURCE")
    # The guest is administrator INSIDE THE VM and can rewrite output.
    # Output is never a cryptographically authenticated test acceptance.
    return {"jobId":jid,"status":"UNTRUSTED_GUEST_REPORT_READBACK_ONLY",
            "reported":str(obj.get("status","UNKNOWN"))[:100],
            "guestReceiptSha":sha_file(report),
            "nativeAcceptance":False,
            "needIndependentOwnerAcceptance":True}
