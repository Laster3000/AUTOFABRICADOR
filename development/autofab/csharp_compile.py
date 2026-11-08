# coding: utf-8
"""Bounded C# compile-only via trusted Roslyn csc, never run generated assemblies.

No MSBuild, analyzers, NuGet restore, source generators, post-build commands,
output execution, Host service installation, or generated-code privilege.
Not a functional WASI acceptance: status remains COMPILED_UNEXECUTED.
"""
from __future__ import annotations
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import tempfile
import time

from .storage import sha_file,sha_bytes
from .isolation import IsolationUnavailable

SDK="10.0.401"
REF_PACK="10.0.13"
CSC=r"C:\Program Files\dotnet\sdk\10.0.401\Roslyn\bincore\csc.dll"
REFERENCES=r"C:\Program Files\dotnet\packs\Microsoft.NETCore.App.Ref\10.0.13\ref\net10.0"
BASE_REFS=("System.Runtime.dll","System.Console.dll","System.Collections.dll",
           "System.Linq.dll","System.Runtime.Extensions.dll","System.Numerics.Vectors.dll",
           "netstandard.dll","System.Private.CoreLib.dll")

def preflight(root):
    csc=Path(CSC)
    refs=Path(REFERENCES)
    host=Path(r"C:\Program Files\dotnet\dotnet.exe")
    if not csc.is_file() or not host.is_file() or not refs.is_dir():
        raise IsolationUnavailable("PINNED_DOTNET_10_ROSLYN_NOT_PRESENT")
    selected=[]
    for name in BASE_REFS:
        path=refs/name
        if name=="System.Private.CoreLib.dll" and not path.exists():
            path=refs/"System.Runtime.dll"
        if not path.is_file():raise IsolationUnavailable("CSHARP_REFERENCE_MISSING:"+name)
        selected.append(path)
    return {"status":"TRUSTED_COMPILER_AVAILABLE_COMPILE_ONLY",
            "SDK":SDK,"refPack":REF_PACK,"cscSha256":sha_file(csc),
            "refSha256":{file.name:sha_file(file) for file in set(selected)},
            "executeGeneratedAssembly":False,
            "hostCommandAuthority":False,
            "functionalAcceptance":"BLOCKED_NO_ISOLATED_CSHARP_RUNTIME"}

def compile_only(root,sources,*,timeout=45):
    trust=preflight(root)
    if not isinstance(sources,dict) or not 1<=len(sources)<=8:
        raise ValueError("CSHARP_SOURCE_COUNT")
    if sum(len(v.encode()) for v in sources.values())>60000:
        raise ValueError("CSHARP_SOURCE_BYTES_LIMIT")
    start=time.monotonic()
    with tempfile.TemporaryDirectory(prefix="af-csharp-compileonly-") as temporary:
        work=Path(temporary)
        names=[]
        for name,text in sources.items():
            if not isinstance(name,str) or not re.fullmatch(r"[a-z][a-z0-9_-]{0,40}\.cs",name):
                raise ValueError("CSHARP_SOURCE_FILENAME_UNSAFE")
            if not isinstance(text,str):
                raise ValueError("CSHARP_SOURCE_TEXT_INVALID")
            if re.search(r"(?m)^\s*#\s*(?:r|load)\b",text):
                raise ValueError("CSHARP_SCRIPT_REFERENCE_DIRECTIVES_FORBIDDEN")
            path=work/name
            path.write_text(text,encoding="utf-8")
            names.append(path)
        refs=Path(REFERENCES)
        # Only trusted reference assemblies. No user supplied DLL/Analyzer.
        present=[]
        for filename in BASE_REFS:
            p=refs/filename
            if p.is_file() and p not in present:present.append(p)
        args=[
            r"C:\Program Files\dotnet\dotnet.exe","exec",CSC,
            "-noconfig","-nostdlib+","-deterministic+",
            "-target:library","-optimize+","-debug-",
            "-unsafe-","-warnaserror+","-langversion:latest",
            "-out:"+str(work/"AF-COMPILEONLY.dll")
        ]+["-reference:"+str(file) for file in present]+[str(p) for p in names]
        try:
            run=subprocess.run(args,cwd=str(work),capture_output=True,
                               stdin=subprocess.DEVNULL,timeout=timeout,
                               env={**os.environ,"DOTNET_ADD_GLOBAL_TOOLS_TO_PATH":"false",
                                    "DOTNET_CLI_TELEMETRY_OPTOUT":"1",
                                    "DOTNET_SKIP_FIRST_TIME_EXPERIENCE":"1"})
        except subprocess.TimeoutExpired:
            return {"status":"UNKNOWN_COMPILE_TIMEOUT_RECONCILE","exitCode":-9,
                    "sourceFiles":len(sources),"functionalTests":0}
        dll=work/"AF-COMPILEONLY.dll"
        ok=run.returncode==0 and dll.is_file() and dll.read_bytes()[:2]==b"MZ"
        return {
           "status":"COMPILED_UNEXECUTED" if ok else "FAILED_COMPILATION",
           "exitCode":0 if ok else run.returncode,
           "sourceCount":len(sources),
           "sourceHashes":{n:sha_bytes(v.encode()) for n,v in sources.items()},
           "assemblySha256":sha_file(dll) if ok else None,
           "assemblyBytes":dll.stat().st_size if ok else 0,
           "compilerStdoutTail":run.stdout.decode("utf-8","replace")[-2400:],
           "compilerStderrTail":run.stderr.decode("utf-8","replace")[-2400:],
           "elapsedMs":int((time.monotonic()-start)*1000),
           "functionalTests":0,
           "ownerAcceptance":"BLOCKED_NO_WASI_CSHARP_GUEST",
           "noAssemblyExecuted":True,"noMsbuild":True,
           "compilerSha256":trust["cscSha256"]
        }
