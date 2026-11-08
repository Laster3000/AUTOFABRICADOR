# coding: utf-8
"""Pinned WASI sandbox for generated code and separate owner-pinned acceptance.

Guest code is not run on native host Python. No host mounts, network, tools,
process grants, or inherited host environment are offered to WASI.
"""
from __future__ import annotations
import json
from pathlib import Path
import sys
import time

from .storage import load, sha_file, safe_source
from .isolation import IsolationUnavailable

WASI_PKG="0.1.4"
WASMTIME_PKG="50.0.1"
WASI_INIT_SHA="47b29c09840586450ee4d9f1a840c35705c365306c30402f7b04cd63364177a6"
WASMTIME_INIT_SHA="bd4d388a475a422e70f8ddbb93ba628741d5fb359639e1035f0fe2ea032c62ba"

def wasi_preflight(root):
    root=Path(root).resolve()
    vendor=root/"VENDOR"/"wasi-runtime"
    receipt=root/"CONTINUIDAD"/"R023"/"WASI-INSTALL-RECEIPT.json"
    negative=root/"CONTINUIDAD"/"R023"/"WASI-ISOLATION-RECEIPT.json"
    paths=[vendor/"wasi_python"/"__init__.py",vendor/"wasmtime"/"__init__.py"]
    if not receipt.is_file() or not negative.is_file() or any(not p.is_file() for p in paths):
        raise IsolationUnavailable("WASI_RUNTIME_OR_NEGATIVE_TEST_RECEIPT_MISSING")
    if sha_file(paths[0])!=WASI_INIT_SHA or sha_file(paths[1])!=WASMTIME_INIT_SHA:
        raise IsolationUnavailable("WASI_RUNTIME_PACKAGE_SHA_DRIFT")
    if load(negative).get("status")!="NEGATIVE_ISOLATION_TESTS_PASS":
        raise IsolationUnavailable("WASI_NEGATIVE_TEST_NOT_ACCEPTED")
    install=load(receipt)
    if install.get("status")!="WASI_PORTABLE_INSTALLED_SHA_VERIFIED":
        raise IsolationUnavailable("WASI_INSTALL_RECEIPT_INVALID")
    return {"backend":"wasi-python-webassembly-no-host-grants",
            "wasiVersion":WASI_PKG,"wasmtimeVersion":WASMTIME_PKG,
            "wasiPackageSha":WASI_INIT_SHA,"negativeReceiptSha":sha_file(negative)}

def guest_code(files):
    """Construct a test harness entirely inside guest memory."""
    stored=json.dumps(files,ensure_ascii=False,sort_keys=True)
    return (
       "import sys, types, unittest, json\n"
       "FILES=json.loads("+repr(stored)+")\n"
       "NAMES=sorted(FILES,key=lambda n:(n.startswith('test_'),n))\n"
       "for filename in NAMES:\n"
       "    name=filename[:-3]\n"
       "    module=types.ModuleType(name)\n"
       "    module.__file__='/sandbox/'+filename\n"
       "    sys.modules[name]=module\n"
       "for filename in NAMES:\n"
       "    exec(compile(FILES[filename],filename,'exec'),sys.modules[filename[:-3]].__dict__)\n"
       "loader=unittest.defaultTestLoader\n"
       "suite=unittest.TestSuite()\n"
       "for filename in NAMES:\n"
       "    if filename.startswith('test_'):\n"
       "        suite.addTests(loader.loadTestsFromModule(sys.modules[filename[:-3]]))\n"
       "declared=suite.countTestCases()\n"
       "result=unittest.TextTestRunner(verbosity=2).run(suite)\n"
       "print('AF_WASI_TEST_RECEIPT='+json.dumps({'executed':result.testsRun,"
       "'failures':len(result.failures),'errors':len(result.errors),"
       "'successful':result.wasSuccessful(),'declared':declared},sort_keys=True))\n"
       "raise SystemExit(0 if declared>0 and result.testsRun==declared and result.wasSuccessful() else 1)\n"
    )

def wasi_run_one(runtime, root, files, timeout, label):
    from wasi_python import run
    started=time.monotonic()
    guest=guest_code(files)
    done=run(["-c",guest],root=False,grants=(),mounts=(),host=None,tools=None,
             deadline_s=max(1,min(int(timeout),120)),memory_bytes=536870912,
             output_bytes=64000,fuel=900000000,
             cache_dir=str(root/"VENDOR"/"wasi-cache"))
    out=done.stdout.decode("utf-8","replace")
    err=done.stderr.decode("utf-8","replace")
    markers=[s for s in out.splitlines() if s.startswith("AF_WASI_TEST_RECEIPT=")]
    data=json.loads(markers[-1].split("=",1)[1]) if markers else None
    count=data.get("executed",0) if isinstance(data,dict) else 0
    success=(done.exit_code==0 and done.trapped is None and count>=1
             and data.get("failures")==0 and data.get("errors")==0
             and data.get("declared")==count and data.get("successful") is True)
    return {"label":label,"exitCode":0 if success else -7,"testCount":count,
            "testResult":data,"stdout":out[-16000:],"stderr":err[-16000:],
            "durationMs":round((time.monotonic()-started)*1000),
            "fuelUsed":done.fuel_used,"trapped":done.trapped}

def run_tests(work,root,*,timeout=60,max_output=16000):
    root=Path(root).resolve()
    trust=wasi_preflight(root)
    work=Path(work).resolve()
    if not work.is_dir() or not work.is_relative_to(root/"work"):
        raise IsolationUnavailable("WORKSPACE_OUTSIDE_FACTORY")
    files={}
    for path in sorted(work.rglob("*.py")):
        if path.is_symlink() or not path.is_file():
            raise IsolationUnavailable("SYMLINK_OR_NONREGULAR_SOURCE")
        name=path.relative_to(work).as_posix()
        safe_source(work,name)
        if "/" in name:raise IsolationUnavailable("WASI_PILOT_ONLY_TOP_LEVEL_PYTHON_FILES")
        files[name]=path.read_text("utf-8")
    if not files or not any(name.startswith("test_") for name in files):
        raise IsolationUnavailable("WASI_TEST_SOURCES_MISSING")
    if sum(len(v.encode("utf-8")) for v in files.values())>160000:
        raise IsolationUnavailable("WASI_SOURCE_LIMIT")
    vendor=root/"VENDOR"/"wasi-runtime"
    if str(vendor) not in sys.path:sys.path.insert(0,str(vendor))
    primary=wasi_run_one(vendor,root,files,timeout,"model-authored")
    job=work.parent.parent
    spec=load(job/"spec.json")
    owner=None
    expected_sha=None
    if spec.get("acceptance"):
        expected_sha=spec["acceptance"]["sha256"]
        source=job/"acceptance"/"test_owner_acceptance.py"
        if not source.is_file() or source.is_symlink() or sha_file(source)!=expected_sha:
            raise IsolationUnavailable("OWNER_ACCEPTANCE_PIN_DRIFT")
        # Crucially isolate owner tests from all model-authored tests and from
        # the earlier WASI guest; the model cannot edit source pinned outside work.
        own_files={k:v for k,v in files.items() if not k.startswith("test_")}
        own_files["test_owner_acceptance.py"]=source.read_text("utf-8")
        owner=wasi_run_one(vendor,root,own_files,timeout,"owner-pinned")
    all_ok=primary["exitCode"]==0 and (owner is None or owner["exitCode"]==0)
    executed=primary["testCount"]+(owner["testCount"] if owner else 0)
    return {"exitCode":0 if all_ok else -7,
            "testCount":executed,
            "modelTestCount":primary["testCount"],
            "independentTestCount":owner["testCount"] if owner else 0,
            "independentTestSha":expected_sha,
            "testResult":primary["testResult"],
            "ownerTestResult":owner["testResult"] if owner else None,
            "stdout":(primary["stdout"]+(owner["stdout"] if owner else ""))[-max_output:],
            "stderr":(primary["stderr"]+(owner["stderr"] if owner else ""))[-max_output:],
            "durationMs":primary["durationMs"]+(owner["durationMs"] if owner else 0),
            "fuelUsed":primary["fuelUsed"]+(owner["fuelUsed"] if owner else 0),
            "trapped":primary["trapped"] or (owner["trapped"] if owner else None),
            "backend":trust["backend"],"wasiVersion":WASI_PKG,
            "wasmtimeVersion":WASMTIME_PKG,
            "hostFilesystemGrants":0,"hostTools":0,"networkCapabilities":0,
            "negativeIsolationReceiptSha":trust["negativeReceiptSha"]}
