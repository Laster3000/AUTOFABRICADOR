# coding: utf-8
"""Deterministic bounded ESM/TypeScript project graph compiler and WASI owner QA.

Untrusted code is parsed by SHA-pinned esbuild-wasm on trusted Node harness,
but NEVER run/eval/require'd on Node or host. All model code and vendored
libraries execute ONLY inside the original fuel/memory-limited Javy+Wasmtime
WASI guest with no network, environment, sockets or preopened directories.

This is a restricted portable JS/TS ESM repository executor, not a native
Host shell/npm install agent or arbitrary full-repository runner.
"""
from __future__ import annotations
from pathlib import Path,PurePosixPath
import base64,hashlib,json,os,re,subprocess,tempfile,sys
from . import engine,js_wasi,npm_umd
from .storage import load,sha_file,sha_bytes,json_bytes,utc
from .isolation import IsolationUnavailable

VERSION="0.25.12"
BUNDLER_TAR_SHA="e0712c0e7a9bcfb53c648f63222b07d6ef052897da093498441b8ac5fcfc5342"
BUNDLER_WASM_SHA="92c182cd141115f33ad08ad1d29b38f00f6292d38c3fe7ef85c11775407b54fb"
BUNDLER_LOCK_SHA="7a7f02e78e04e22d6fcbcc7ccb7648521a7a2076b392be709fa571b872261a9b"
PATH=re.compile(r"src/[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*\.(?:js|ts)\Z")
IDENTIFIER=re.compile(r"[A-Za-z_$][A-Za-z0-9_$]{0,45}\Z")
SUPPORTED=frozenset(("javascript","typescript"))
def preflight(root):
    root=Path(root).resolve()
    lockfile=root/"MODULE-BUNDLER.lock.json"
    if not lockfile.is_file():
        raise IsolationUnavailable("ESBUILD_WASM_PINNED_LOCK_NOT_PRESENT")
    lock=load(lockfile)
    if (lock["name"]!="esbuild-wasm" or lock["version"]!=VERSION
        or lock["packageTarSha256"]!=BUNDLER_TAR_SHA
        or lock["filesCount"]!=15
        or lock["files"]["esbuild.wasm"]["sha256"]!=BUNDLER_WASM_SHA
        or lock["packageLifecycleScriptsExecuted"] is not False):
        raise IsolationUnavailable("ESBUILD_WASM_LOCK_POLICY_DRIFT")
    tar=root/"VENDOR/module-bundler/esbuild-wasm-0.25.12.tgz"
    if not tar.is_file():
        raise IsolationUnavailable("PINNED_BUNDLER_TARBALL_NOT_IN_SOURCE_ONLY_ARCHIVE")
    if sha_file(tar)!=BUNDLER_TAR_SHA:
        raise IsolationUnavailable("PINNED_BUNDLER_NPM_TARBALL_SHA_DRIFT")
    base=root/"VENDOR/module-bundler/package"
    for name,row in lock["files"].items():
        p=base/name
        if (not p.is_file() or p.is_symlink()
            or p.stat().st_size!=row["size"] or sha_file(p)!=row["sha256"]):
            raise IsolationUnavailable("PINNED_ESBUILD_WASM_SOURCE_SHA_DRIFT:"+name)
    harness=root/"qa/esm_bundle.js"
    if not harness.is_file():raise IsolationUnavailable("REPO_FIRST_PARTY_BUNDLER_SCRIPT_MISSING")
    js_wasi.preflight(root,"javascript")
    return {"compiler":"esbuild-wasm-"+VERSION,
            "compilerTarSha256":BUNDLER_TAR_SHA,
            "compilerWasmSha256":BUNDLER_WASM_SHA,
            "bundlerLockSha256":sha_file(lockfile),
            "firstPartyBundlerSha256":sha_file(harness),
            "modelCodeRanOnNode":False,
            "modelCodeExecution":"WASI_CORE_WASMTIME_FUEL_NO_NETWORK_NO_FS",
            "npmLifecycleRun":False}

def _valid_spec(spec):
    if not isinstance(spec,dict):
        raise ValueError("REPO_SPEC_NOT_OBJECT")
    keys={"schema","language","goal","entry","exportName","sources","acceptance","dependencies"}
    if set(spec)!=keys:
        raise ValueError("REPO_SPEC_SCHEMA_KEYS_INVALID")
    if spec["schema"]!=1 or spec["language"] not in SUPPORTED:
        raise ValueError("REPO_LANGUAGE_OR_SCHEMA_UNSUPPORTED")
    if not isinstance(spec["goal"],str) or not 24<=len(spec["goal"])<=4500:
        raise ValueError("REPO_GOAL_LENGTH_OUT_OF_RANGE")
    sources=spec["sources"]
    if not isinstance(sources,dict) or not 2<=len(sources)<=20:
        raise ValueError("REPO_SOURCE_COUNT_LIMIT")
    ext=".ts" if spec["language"]=="typescript" else ".js"
    if any(not isinstance(name,str) or not PATH.fullmatch(name)
           or len(name)>120 or not name.endswith(ext) for name in sources):
        raise ValueError("REPO_SOURCE_PATH_INVALID")
    if len({name.casefold() for name in sources})!=len(sources):
        raise ValueError("REPO_CASE_INSENSITIVE_PATH_COLLISION")
    if any(not isinstance(text,str) or len(text)<12
           or len(text.encode("utf-8"))>14000 for text in sources.values()):
        raise ValueError("REPO_SOURCE_TEXT_SIZE_INVALID")
    if sum(len(text.encode("utf-8")) for text in sources.values())>90000:
        raise ValueError("REPO_SOURCE_TREE_SIZE_EXCEEDED")
    if spec["entry"] not in sources:
        raise ValueError("REPO_ENTRY_MUST_BE_DECLARED_SOURCE")
    if not isinstance(spec["exportName"],str) or not IDENTIFIER.fullmatch(spec["exportName"]):
        raise ValueError("REPO_ENTRY_EXPORT_INVALID")
    deps=spec["dependencies"]
    if not isinstance(deps,list) or len(deps)>2 or len(set(deps))!=len(deps):
        raise ValueError("REPO_NPM_DEPENDENCY_GRAPH_INVALID")
    if any(dep not in npm_umd.ALLOW for dep in deps):
        raise ValueError("REPO_UNPINNED_NPM_PACKAGE_FORBIDDEN")
    cases=spec["acceptance"]
    if not isinstance(cases,list) or not 5<=len(cases)<=80:
        raise ValueError("REPO_OWNER_TEST_COUNT_OUTSIDE_BOUNDS")
    if len(json.dumps(cases,ensure_ascii=False))>18000:
        raise ValueError("REPO_OWNER_TESTS_TOO_LARGE")
    for row in cases:
        if (not isinstance(row,dict) or set(row)!={"args","expected"}
            or not isinstance(row["args"],list) or len(row["args"])>9):
            raise ValueError("REPO_OWNER_CASE_FORMAT_INVALID")
    return True

def _static_source_guard(files):
    # The compiler accepts imports/exports, but never grants Node builtins or
    # runtime network/filesystem APIs. Verified source execution stays in WASI.
    for name,src in files.items():
        if not isinstance(src,str) or not 12<=len(src)<=14000:
            raise ValueError("REPO_UNTRUSTED_SOURCE_STRING_INVALID")
        if re.search(r"(?<![A-Za-z0-9_$])(?:importScripts|eval|Function|WebSocket|fetch|XMLHttpRequest|child_process|process\.|globalThis\.process)\s*\(",src):
            raise ValueError("REPO_SOURCE_DYNAMIC_HOST_API_UNSUPPORTED:"+name)
        if re.search(r"\bimport\s*\(",src):
            raise ValueError("REPO_DYNAMIC_IMPORT_FORBIDDEN:"+name)
        if re.search(r"\brequire\s*\(",src):
            raise ValueError("REPO_REQUIRE_IMPORT_FORBIDDEN:"+name)
        # Conservative first-party defense; executing generated code remains
        # forbidden outside original no-network/no-FS WASI or isolated guest.
        if re.search(r"(?<![A-Za-z0-9_$])(?:process|globalThis\s*\.\s*process)\s*(?:\?\.|\.|\[)",src):
            raise ValueError("REPO_NODE_PROCESS_API_FORBIDDEN:"+name)
        if re.search(r'''globalThis\s*\[\s*['"]process['"]\s*\]''',src):
            raise ValueError("REPO_GLOBAL_PROCESS_BRACKET_FORBIDDEN:"+name)
        if re.search(r'''globalThis\s*\?\.\s*\[\s*['"]process['"]\s*\]''',src):
            raise ValueError("REPO_GLOBAL_PROCESS_OPTIONAL_BRACKET_FORBIDDEN:"+name)


def build_owner(root,spec,files,*,timeout=85):
    root=engine.init(root)
    pre=preflight(root)
    _valid_spec(spec)
    if not isinstance(files,dict) or set(files)!=set(spec["sources"]):
        raise ValueError("REPO_SOURCE_SET_MUST_EQUAL_OWNER_CONTRACT")
    speccopy={**spec,"sources":files}
    _valid_spec(speccopy)
    _static_source_guard(files)
    dependencies=npm_umd.preflight(root,spec["dependencies"])
    # Explicit exact paths and SHA for only two vetted UMD JS libraries,
    # no npm installs, transitive lifecycle hooks, Node addons or downloads.
    pinned={}
    for name in spec["dependencies"]:
        row=dependencies[name]
        library=root/"VENDOR/npm-pin"/name/row["version"]/(name+".min.js" if name=="dayjs" else "lodash.min.js")
        if not library.is_file() or sha_file(library)!=row["fileSha256"]:
            raise IsolationUnavailable("REPO_VENDOR_SNAPSHOT_CHANGED:"+name)
        pinned[name]={"path":str(library),"sha256":row["fileSha256"]}
    with tempfile.TemporaryDirectory(prefix="af-repo-graph-") as tmp:
        folder=Path(tmp)
        for name,raw in files.items():
            path=folder/name
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(raw.encode("utf-8"))  # Windows newline translation forbidden in SHA-defined source
            if sha_file(path)!=sha_bytes(raw.encode()):
                raise RuntimeError("REPO_OWNER_SOURCE_WORKTREE_SHA_DRIFT")
        contract={"schema":1,"files":list(files),
                  "entry":spec["entry"],"exportName":spec["exportName"],
                  "dependencies":pinned}
        c=folder/"AF-COMPILER-INPUT.json"
        c.write_bytes(json_bytes(contract))
        bundle=folder/"AF-PROJECT-BUNDLE.js"
        cmd=[r"C:\Program Files\nodejs\node.exe",
             str(root/"qa/esm_bundle.js"),str(folder),str(c),str(bundle)]
        try:
            child=subprocess.run(cmd,cwd=str(root),stdin=subprocess.DEVNULL,
                capture_output=True,timeout=45,
                env={**os.environ,"NODE_OPTIONS":"","PYTHONDONTWRITEBYTECODE":"1",
                     "DOTNET_ADD_GLOBAL_TOOLS_TO_PATH":"false"})
        except subprocess.TimeoutExpired:
            return {"status":"UNKNOWN_BUNDLER_CHILD_TIMED_OUT",
                    "cannotBlindRetry":True,"modelRuntimeExecuted":False}
        observed={"schema":1,"compiler":"esbuild-wasm-"+VERSION,
                  "compilerExit":child.returncode,
                  "compilerStderrSha256":sha_bytes(child.stderr),
                  "compilerStderrTail":child.stderr.decode("utf-8","replace")[-1500:],
                  "bundlerScriptSha256":pre["firstPartyBundlerSha256"],
                  "modelCodeRanOnNode":False,
                  "compilerStdOutSha256":sha_bytes(child.stdout)}
        if child.returncode or not bundle.is_file() or not (folder/"AF-PROJECT-BUNDLE.js.receipt.json").is_file():
            return {"status":"FAILED_ESM_GRAPH_COMPILE","compiler":observed,
                    "ownerCount":len(spec["acceptance"]),"modelRuntimeExecuted":False}
        compiled=bundle.read_text("utf-8")
        compile_receipt=load(folder/"AF-PROJECT-BUNDLE.js.receipt.json")
        if (compile_receipt["status"]!="ESBUILD_WASM_SOURCE_BUNDLE_ONLY"
            or compile_receipt["generatedBundleSha256"]!=sha_file(bundle)
            or compile_receipt["moduleCount"]<2
            or compile_receipt["loadedInputSha256"]!={n:sha_bytes(files[n].encode()) for n in files}
            or len(compiled.encode())>95000
            or compile_receipt["pinnedDependencySha256"]!={n:row["fileSha256"] for n,row in dependencies.items()}):
            return {"status":"FAILED_COMPILE_GRAPH_SHA_OR_SOURCE_CLOSURE",
                    "compiler":observed,"modelRuntimeExecuted":False}
        guest=js_wasi.execute(root,"javascript",{"project.js":compiled},
                  spec["exportName"],spec["acceptance"],timeout=timeout)
        return {"status":"PASS" if guest["status"]=="PASS" else "FAILED_OWNER_WASI",
            "compiler":observed,
            "compileReceipt":compile_receipt,
            "compiledSource":compiled,
            "compiledSha256":sha_bytes(compiled.encode()),
            "originalOwnerResult":guest,
            "ownerCaseCount":len(spec["acceptance"]),
            "npmPinnedDependencies":dependencies,
            "executionMode":"WASI_NO_HOST_NETWORK_FS",
            "modelCodeRanOnNode":False}
