# coding: utf-8
"""R65 original AUTOFABRICADOR relocatable, *manually* launched controller.

No Task Scheduler, SCM service, OS startup, registry or cloud calls. Root is
always folder holding THIS script; Python runtime is INSIDE the same folder.
It calls ORIGINAL autofab.supervisor for no-duplicate, PID+birth, journal,
pending-queue, STOP and immutable original receipts. A ZIP/directory COPY
can run on a compatible Windows PC only with necessary hardware/drivers.
"""
from __future__ import annotations
import argparse,json,os,sys,time,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
PYTHON=ROOT/"runtime/python.exe"
CLI=ROOT/"autofabricador.py"
def emit(x):
 print(json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2),flush=True)
def native():
 if os.name!="nt":raise RuntimeError("PORTABLE_R65_REQUIRES_WINDOWS_OS")
 if not CLI.is_file() or not PYTHON.is_file():
  raise RuntimeError("PORTABLE_R65_MISSING_ORIGINAL_BUNDLED_SOURCE_OR_PYTHON")
 if Path(sys.executable).resolve()!=PYTHON.resolve():
  raise RuntimeError("PORTABLE_R65_MUST_RUN_OWN_BUNDLED_PYTHON")
 if not (ROOT/"autofab/supervisor.py").is_file():
  raise RuntimeError("PORTABLE_R65_ORIGINAL_SUPERVISOR_MISSING")
 if (ROOT/"service.exe").exists():
  raise RuntimeError("PORTABLE_R65_UNEXPECTED_SERVICE_EXECUTABLE")
def source():
 native()
 # All outputs, owner databases and temp files belong to THIS folder.
 data=ROOT/"DATOS"
 tmp=data/"TEMP"
 tmp.mkdir(parents=True,exist_ok=True)
 os.environ["LOCALAPPDATA"]=str(data)
 os.environ["TEMP"]=str(tmp)
 os.environ["TMP"]=str(tmp)
 sys.path.insert(0,str(ROOT))
 from autofab import engine,supervisor,local_cuda7b
 return engine,supervisor,local_cuda7b
def state():
 _,supervisor,local_cuda7b=source()
 supervisor_state=supervisor.status(ROOT)
 gpu_state=local_cuda7b.server_info(ROOT)
 return {"status":supervisor_state["status"],
   "root":str(ROOT),"mode":"MANUAL_PORTABLE_NO_WINDOWS_AUTORUN",
   "originalSupervisor":supervisor_state,
   "originalLocalGPU":gpu_state["state"],
   "rootIndependentFromSystemPython":True,
   "windowsTaskSchedulerNeeded":False,
   "windowsSCMServiceNeeded":False,
   "newHostRegistryInstalled":False,
   "automaticStartAtWindowsLogon":False,
   "generalArbitrarySoftwareAccepted":False}
def check_queues(supervisor):
 directory=supervisor.directory(ROOT)/"queue"
 from autofab.storage import load
 statuses=[(f.name,load(f).get("status"))
           for f in directory.glob("SQ-*.json")]
 busy=[name for name,status in statuses if status in ("PENDING","RUNNING")]
 return {"queueCount":len(statuses),"activeCount":len(busy),"active":busy}
def start():
 _,supervisor,local_cuda7b=source()
 pre=supervisor.status(ROOT)
 if pre["status"]=="RUNNING":
  if not pre["processIdentityBirthVerified"]:
   raise RuntimeError("PORTABLE_R65_UNKNOWN_LEASE_DO_NOT_DUPLICATE")
  return {"status":"ALREADY_RUNNING_NO_DUPLICATE",
          "originalPid":pre["lease"]["pid"],"root":str(ROOT)}
 if pre["status"]!="STOPPED" or pre["control"]["command"] not in ("STOP","RUN"):
  raise RuntimeError("PORTABLE_R65_UNKNOWN_ORIGINAL_SUPERVISOR_STATE")
 jobs=check_queues(supervisor)
 if jobs["activeCount"]:
  raise RuntimeError("PORTABLE_R65_PENDING_OR_RUNNING_JOB_REQUIRES_ORIGINAL_RECONCILE")
 gpu=local_cuda7b.server_info(ROOT)
 if gpu["state"]!="NOT_STARTED":
  raise RuntimeError("PORTABLE_R65_GPU_LEASE_ACTIVE_OR_UNKNOWN:"+gpu["state"])
 result=supervisor.start(ROOT)
 if result["status"]!="RUNNING_VERIFIED":
  raise RuntimeError("PORTABLE_R65_ORIGINAL_SUPERVISOR_START_NOT_VERIFIED")
 live=supervisor.status(ROOT)
 if (live["status"]!="RUNNING" or not live["processIdentityBirthVerified"]
     or live["lease"]["pid"]!=result["lease"]["pid"]):
  raise RuntimeError("PORTABLE_R65_MANUAL_WORKER_PID_BIRTH_READBACK_FAILED")
 return {"status":"PASS_ORIGINAL_WORKER_MANUALLY_STARTED",
         "originalPid":live["lease"]["pid"],
         "originalProcessBornFiletime":live["lease"]["processBornFiletime"],
         "root":str(ROOT),"taskSchedulerNotUsed":True,
         "previousJobsNotReplayed":True}
def stop():
 _,supervisor,local_cuda7b=source()
 before=supervisor.status(ROOT)
 if before["status"]=="STOPPED":
  return {"status":"ALREADY_STOPPED_NO_REPLAY","root":str(ROOT)}
 if before["status"]!="RUNNING" or not before["processIdentityBirthVerified"]:
  raise RuntimeError("PORTABLE_R65_UNKNOWN_SUPERVISOR_PROCESS_NOT_SAFE_TO_STOP")
 old_pid=before["lease"]["pid"]
 requested=supervisor.stop(ROOT)
 deadline=time.monotonic()+30
 while time.monotonic()<deadline:
  current=supervisor.status(ROOT)
  if current["status"]=="STOPPED" and current["control"]["command"]=="STOP":
   gpu=local_cuda7b.server_info(ROOT)
   return {"status":"PASS_ORIGINAL_PORTABLE_SUPERVISOR_STOPPED",
           "oldPid":old_pid,"root":str(ROOT),
           "gpuAfterStop":gpu["state"],"shutdownSafe":True}
  time.sleep(.25)
 return {"status":"STOP_REQUESTED_ACTIVE_ORIGINAL_JOB_SAFE_BOUNDARY",
         "originalPid":old_pid,"root":str(ROOT),
         "noBlindKill":True,"noAutomaticReplay":True}
def console():
 start()
 # First-party original GUI (no second GUI code or autonomous agents outside).
 import runpy
 old=list(sys.argv)
 try:
  sys.argv=[str(ROOT/"autofab/job_console.py")]
  runpy.run_module("autofab.job_console",run_name="__main__",alter_sys=True)
 finally:
  sys.argv=old
def main(argv=None):
 parser=argparse.ArgumentParser(description="AUTOFABRICADOR original manual portable launcher")
 parser.add_argument("action",choices=["start","stop","status","console","assets","doctor"])
 args=parser.parse_args(argv)
 if args.action=="start":emit(start())
 elif args.action=="stop":emit(stop())
 elif args.action=="status":emit(state())
 elif args.action=="console":console()
 elif args.action=="assets":
  _,supervisor,local_cuda7b=source()
  pinned=local_cuda7b.pinned_assets(ROOT)
  emit({"status":"PASS_PORTABLE_GPU7B_PINNED_ASSETS",
        "modelSHA":local_cuda7b.MODEL_SHA,
        "runtime":str(PYTHON),"originalSource":str(CLI),
        "modelPath":str(pinned["model"]),
        "noWindowStartupDependency":True})
 elif args.action=="doctor":
  native()
  p=subprocess.run([str(PYTHON),"-B",str(CLI),"doctor"],
      stdin=subprocess.DEVNULL,capture_output=True,
      timeout=50,cwd=ROOT)
  if p.returncode:raise RuntimeError("PORTABLE_R65_ORIGINAL_DOCTOR_FAILED")
  emit({"status":"PORTABLE_R65_ORIGINAL_DOCTOR_EXIT_ZERO",
        "originalOutput":p.stdout.decode("utf-8","replace")[-3500:],
        "pythonInsideBundle":True,"noWindowsStartup":True})
if __name__=="__main__":main()
