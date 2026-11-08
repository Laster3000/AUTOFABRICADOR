# coding: utf-8
"""Pinned Javy+Wasmtime JS/TS tests, no Host JS execution.

Native Javy and TypeScript programs compile only; every model-authored JS
statement executes in fresh Wasmtime WASI with zero preopened directories or
network grants, finite instruction fuel and bounded memory. This is a small
stdlib-only JS/TS subset, not general Node/npm execution.
"""
from __future__ import annotations
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

from .isolation import IsolationUnavailable
from . import npm_umd
from .storage import sha_bytes,sha_file

JAVY_VERSION="9.1.0"
JAVY_EXE_SHA="4b298b147ba2d8656af174e266ca8f9de1a4d963795a95f4ce82f685b34d3c73"
JAVY_ARCHIVE_SHA="7148baab85d7426e8c18e2cc4deed4e9f03270cf3245dba5617a5be25a1de836"
TYPESCRIPT_VERSION="5.9.3"
TS_JS_SHA="3ae902c92cc44dace175c0e69e13a4b0899f6983c6121d76b9ab8dd5795e7675"
WASMTIME_INIT_SHA="bd4d388a475a422e70f8ddbb93ba628741d5fb359639e1035f0fe2ea032c62ba"
FUEL=350000000

def preflight(root,language):
    root=Path(root).resolve()
    if language not in ("javascript","typescript"):
        raise IsolationUnavailable("UNSUPPORTED_JS_WASI_LANGUAGE")
    exe=root/"VENDOR/javy-v9.1.0-windows-x64/javy.exe"
    wasm_package=root/"VENDOR/wasi-runtime/wasmtime/__init__.py"
    if not exe.is_file() or sha_file(exe)!=JAVY_EXE_SHA:
        raise IsolationUnavailable("JAVY_BINARY_SHA_NOT_VERIFIED")
    if not wasm_package.is_file() or sha_file(wasm_package)!=WASMTIME_INIT_SHA:
        raise IsolationUnavailable("WASMTIME_PACKAGE_SHA_NOT_VERIFIED")
    if language=="typescript":
        ts=root/"VENDOR/typescript/node_modules/typescript/lib/typescript.js"
        if not ts.is_file() or sha_file(ts)!=TS_JS_SHA:
            raise IsolationUnavailable("TYPESCRIPT_COMPILER_SHA_NOT_VERIFIED")
    return {"compiler":"javy-9.1.0","javySha256":JAVY_EXE_SHA,
            "wasmtimePackageSha256":WASMTIME_INIT_SHA,
            "guest":"wasmtime-core-wasi1-no-preopened-dirs-no-network",
            "hostFilesystemGrants":0,"networkGrants":0,"fuel":FUEL,
            "memoryBytes":192*1024*1024,
            "tsc":"typescript-5.9.3" if language=="typescript" else None}

def owner_harness(function,tests):
    if not re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]{0,45}",function):
        raise ValueError("JS_TEST_FUNCTION_NAME_UNSAFE")
    if not 3<=len(tests)<=80:
        raise ValueError("OWNER_ACCEPTANCE_TEST_COUNT_OUTSIDE_BOUNDS")
    # Owner values can contain NUL code points. Javy rejects JavaScript
    # literals that resolve to internal NUL during compilation. Transport
    # the original frozen JSON as safe ASCII base64 (not different tests).
    # Reconstruct the exact string at runtime within the WASI guest.
    owned=base64.b64encode(json.dumps(tests,ensure_ascii=True,separators=(",",":")).encode("ascii")).decode("ascii")
    # Tests are frozen before the model call; no generated tests are accepted.
    return (
      "\n;(function(){\n"
      "  const __af_alpha='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';\n"
      "  let __af_acc=0,__af_bits=0,__af_json='';\n"
      "  for(const __af_ch of '"+owned+"'){\n"
      "    if(__af_ch==='=')break;\n"
      "    const __af_v=__af_alpha.indexOf(__af_ch);\n"
      "    if(__af_v<0)throw Error('bad owner transport');\n"
      "    __af_acc=(__af_acc<<6)|__af_v;__af_bits+=6;\n"
      "    if(__af_bits>=8){__af_bits-=8;__af_json+=String.fromCharCode((__af_acc>>__af_bits)&255);__af_acc&=(1<<__af_bits)-1;}\n"
      "  }\n"
      "  const __af_cases=JSON.parse(__af_json);\n"
      "  const __af_fn="+function+";\n"
      "  const __af_canonical=(value)=>JSON.stringify(value,function(key,item){\n"
      "    if(item!==null && typeof item==='object' && !Array.isArray(item)){\n"
      "      const sorted={};for(const name of Object.keys(item).sort())sorted[name]=item[name];\n"
      "      return sorted;\n"
      "    }return item;\n"
      "  });\n"
      "  let __af_passed=0;\n"
      "  const __af_fail=[];\n"
      "  for(let __af_i=0;__af_i<__af_cases.length;__af_i++){\n"
      "    const __af_case=__af_cases[__af_i];\n"
      "    try {\n"
      "      const __af_result=__af_fn(...__af_case.args);\n"
            "      if(__af_canonical(__af_result)===__af_canonical(__af_case.expected))__af_passed++;\n"
      "      else __af_fail.push({i:__af_i,expected:__af_case.expected,got:__af_result});\n"
      "    } catch(__af_error){__af_fail.push({i:__af_i,error:String(__af_error).slice(0,150)});}\n"
      "  }\n"
      "  console.log('AF_WASI_JS_ACCEPTANCE='+JSON.stringify({count:__af_cases.length,passed:__af_passed,failed:__af_fail}));\n"
      "})();\n"
    )

def _transpile_typescript(root,code,work,files_order):
    tsc=root/"VENDOR/typescript/node_modules/typescript/bin/tsc"
    if not tsc.is_file():raise IsolationUnavailable("TS_COMPILER_ENTRY_MISSING")
    out=work/"typescript-output.js"
    source=[str(work/f) for f in files_order]
    # No tsconfig, plugins, transpile hooks, npm deps or downloaded packages.
    command=[r"C:\Program Files\nodejs\node.exe",str(tsc),
             "--target","ES2022","--module","none","--lib","ES2022",
             "--skipLibCheck","false","--noEmitOnError","true",
             "--outFile",str(out)]+source
    result=subprocess.run(command,stdin=subprocess.DEVNULL,capture_output=True,
                          cwd=str(work),timeout=45,
                          env={**os.environ,"NODE_OPTIONS":"","DOTNET_ADD_GLOBAL_TOOLS_TO_PATH":"false"})
    if result.returncode or not out.is_file():
        return None,{"status":"FAILED_TS_COMPILER",
                     "exitCode":result.returncode,
                     "stderrSha256":sha_bytes(result.stderr),
                     "stdoutTail":result.stdout.decode("utf-8","replace")[-2500:]}
    text=out.read_text("utf-8")
    if len(text.encode("utf-8"))>100000:
        raise IsolationUnavailable("TRANSPILED_TS_TOO_LARGE")
    return text,{"status":"COMPILED","typescriptOutputSha256":sha_file(out)}

def execute(root,language,files,function,tests,*,timeout=75,dependencies=None):
    root=Path(root).resolve()
    trust=preflight(root,language)
    vendor_source,dependency_hashes=npm_umd.trusted(root,dependencies)
    suffix=".js" if language=="javascript" else ".ts"
    if not isinstance(files,dict) or not 1<=len(files)<=8:
        raise ValueError("JS_SOURCE_FILE_COUNT_OUTSIDE_BOUNDS")
    if not isinstance(tests,list):raise ValueError("OWNER_CASES_NOT_ARRAY")
    if len(json.dumps(tests,ensure_ascii=False))>20000:
        raise ValueError("OWNER_CASES_TOO_LARGE")
    for case in tests:
        if not isinstance(case,dict) or set(case)!={"args","expected"} or not isinstance(case["args"],list):
            raise ValueError("INVALID_JS_OWNER_CASE")
    source_bytes=sum(len(x.encode("utf-8")) for x in files.values())
    if source_bytes>100000:raise ValueError("JS_SOURCE_SIZE_TOO_LARGE")
    start=time.monotonic()
    with tempfile.TemporaryDirectory(prefix="af-wasi-js-") as name:
        directory=Path(name)
        order=[]
        for filename,content in files.items():
            if not isinstance(filename,str) or not re.fullmatch(r"[a-z][a-z0-9_-]{0,45}"+re.escape(suffix),filename):
                raise ValueError("JS_SOURCE_FILENAME_UNSAFE")
            if not isinstance(content,str):
                raise ValueError("JS_SOURCE_CONTENT_NOT_TEXT")
            if re.search(r"(?m)^\s*(?:import|export)\s",content):
                raise ValueError("ONLY_STANDALONE_SCRIPTS_NO_IMPORTS")
            file=directory/filename
            file.write_text(content,encoding="utf-8")
            order.append(filename)
        if language=="typescript":
            body,compile_result=_transpile_typescript(root,files,directory,order)
            if body is None:return {**compile_result,"exitCode":-20,"testCount":0,
                                    "backend":"typescript-static-only-no-execution"}
        else:
            body="\n;\n".join(files[n] for n in order)
            compile_result={"status":"JAVASCRIPT"}
        wrapper=directory/"__af_owner_harness.js"
        body=(vendor_source+"\n;\n"+body) if vendor_source else body
        wrapper.write_text(body+"\n;\n"+owner_harness(function,tests),encoding="utf-8")
        wasm=directory/"__af_guest.wasm"
        javy=root/"VENDOR/javy-v9.1.0-windows-x64/javy.exe"
        result=subprocess.run([str(javy),"build",str(wrapper),"-o",str(wasm)],
                              stdin=subprocess.DEVNULL,cwd=str(directory),capture_output=True,
                              timeout=65)
        if result.returncode or not wasm.is_file():
            return {"status":"FAILED_JAVY_COMPILE","exitCode":-21,"testCount":0,
                    "compilerStderrTail":result.stderr.decode("utf-8","replace")[-2600:],
                    "compile":compile_result}
        data=wasm.read_bytes()
        if not data.startswith(b"\x00asm") or len(data)>7000000:
            raise IsolationUnavailable("WASM_MODULE_MAGIC_OR_SIZE_INVALID")
        # No guest filesystem grants, no host env inheritance, no sockets.
        vendor=root/"VENDOR/wasi-runtime"
        if str(vendor) not in sys.path:sys.path.insert(0,str(vendor))
        import wasmtime
        config=wasmtime.Config()
        config.consume_fuel=True
        engine=wasmtime.Engine(config)
        mod=wasmtime.Module(engine,data)
        if any(i.module not in ("wasi_snapshot_preview1",) for i in mod.imports):
            raise IsolationUnavailable("WASM_UNEXPECTED_IMPORT_NAMESPACE")
        store=wasmtime.Store(engine)
        store.set_fuel(FUEL)
        store.set_limits(memory_size=192*1024*1024,table_elements=10000,
                         instances=4,tables=10,memories=3)
        wasi=wasmtime.WasiConfig()
        wasi.argv=["af-wasi-js"]
        output=directory/"__af_guest.stdout.txt"
        errors=directory/"__af_guest.stderr.txt"
        wasi.stdout_file=str(output)
        wasi.stderr_file=str(errors)
        store.set_wasi(wasi)
        linker=wasmtime.Linker(engine)
        linker.define_wasi()
        trapped=None
        try:
            instance=linker.instantiate(store,mod)
            instance.exports(store)["_start"](store)
        except wasmtime.Trap as err:
            trapped=str(err)[:350]
        # Javy guest writes only to the explicitly assigned stdout/stderr streams.
        text=output.read_text("utf-8","replace")[-18000:] if output.exists() else ""
        errtext=errors.read_text("utf-8","replace")[-7000:] if errors.exists() else ""
        markers=[row for row in text.splitlines() if row.startswith("AF_WASI_JS_ACCEPTANCE=")]
        parsed=None
        if markers:
            try:parsed=json.loads(markers[-1].split("=",1)[1])
            except ValueError:pass
        passed=bool(not trapped and isinstance(parsed,dict) and
                    parsed.get("count")==len(tests) and parsed.get("passed")==len(tests)
                    and not parsed.get("failed"))
        return {
            "status":"PASS" if passed else "FAILED_OWNER_ACCEPTANCE",
            "exitCode":0 if passed else -7,"testCount":len(tests),
            "independentTestCount":len(tests),
            "testResult":parsed,"trapped":trapped,
            "sourceHashes":{filename:sha_bytes(text.encode("utf-8")) for filename,text in files.items()},
            "compiler":compile_result,
            "dependencyHashes":dependency_hashes,
            "moduleSha256":sha_bytes(data),
            "stdoutSha256":sha_bytes(text.encode("utf-8")),
            "stdoutTail":text[-4000:],"stderrTail":errtext[-2500:],
            "elapsedMs":int((time.monotonic()-start)*1000),
            "fuelConsumed":FUEL-store.get_fuel(),
            "backend":trust["guest"],"trust":trust
        }
