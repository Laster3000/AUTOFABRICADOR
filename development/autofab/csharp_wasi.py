# coding: utf-8
"""Bounded owner-pinned C# functional execution in WASI 0.2 component.

Trust boundaries:
- Roslyn/componentize-dotnet and their build-time targets are a separately
  installed, trusted third-party toolchain with pinned paths and versions.
- Model-authored C# is treated only as source, never MSBuild project/target,
  analyzer, NuGet plugin, generated workflow, shell command or Host DLL.
- The only execution of the compiled program is private Wasmtime CLI with
  no host preopened folders, inherited env, network, stdin, or WASI HTTP,
  and an execution timeout + memory limit.
- The owner test harness is generated after fixing acceptance cases *before*
  the AI call; a random witness marker is supplied to the trusted harness,
  not the model. This is an independent software test, not a proof that
  arbitrary hostile Wasm can never exploit a runtime vulnerability.
"""
from __future__ import annotations
import hashlib,json,os
from pathlib import Path
import re,subprocess,tempfile,time,uuid
import xml.sax.saxutils

from .storage import sha_bytes,sha_file,load
from .isolation import IsolationUnavailable

DOTNET=Path(r"C:\Program Files\dotnet\dotnet.exe")
SDK="10.0.401"
WASMTIME_SHA="d10847f5cbcdabcb455ca46a5c8d6999fd56955cdd058e46d8028fb9d0b9ed42"
COMPONENTIZE_VERSION="0.8.0-preview00011"
LLVM_VERSION="10.0.0-rc.1.26306.1"
MAX_SOURCE=80000
MEMORY=536870912

def preflight(root):
    root=Path(root).resolve()
    cli=root/"VENDOR/wasmtime-cli-50.0.1/wasmtime.exe"
    lab=root/"LAB-CSHARP-WASI-R035"
    packages=root/"VENDOR/componentize-packages"
    if not (DOTNET.is_file() and cli.is_file() and
            sha_file(cli)==WASMTIME_SHA and packages.is_dir()):
        raise IsolationUnavailable("CSHARP_WASI_PRIVATE_RUNTIME_NOT_VERIFIED")
    original=lab/"bin/Release/net10.0/wasi-wasm/publish/WasiProbe.wasm"
    if not original.is_file() or original.read_bytes()[:4]!=b"\x00asm":
        raise IsolationUnavailable("CSHARP_WASI_ORIGINAL_TRUSTED_PROBE_NOT_BUILT")
    refs=packages/"bytecodealliance.componentize.dotnet.wasm.sdk"/COMPONENTIZE_VERSION
    if not refs.is_dir():raise IsolationUnavailable("COMPONENTIZE_TOOLCHAIN_NOT_CACHED")
    return {"backend":"C#-AOT-WASI02-Wasmtime-CLI50.0.1",
            "wasmtimeSha256":WASMTIME_SHA,"componentizeVersion":COMPONENTIZE_VERSION,
            "sdk":SDK,"hostDirectoryGrants":0,"networkCapabilities":0,
            "inheritedEnv":False,"maxWasmMemory":MEMORY}

def validate_contract(contract):
    if not isinstance(contract,dict) or set(contract)!={"class","method","parameterTypes","returnType","cases"}:
        raise ValueError("CS_ACCEPTANCE_SCHEMA_KEYS")
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,38}(\.[A-Za-z][A-Za-z0-9_]{0,38}){0,5}",contract["class"]):
        raise ValueError("CS_ACCEPTANCE_CLASS_UNSAFE")
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,40}",contract["method"]):
        raise ValueError("CS_ACCEPTANCE_METHOD_UNSAFE")
    types=contract["parameterTypes"]
    if not isinstance(types,list) or not 1<=len(types)<=6 or any(t not in ("int","int[]","bool","string") for t in types):
        raise ValueError("CS_ACCEPTANCE_TYPES_UNSUPPORTED")
    if contract["returnType"] not in ("int","bool","string"):
        raise ValueError("CS_RETURN_TYPE_UNSUPPORTED")
    cases=contract["cases"]
    if not isinstance(cases,list) or not 5<=len(cases)<=60:
        raise ValueError("CS_ACCEPTANCE_CASE_COUNT")
    if len(json.dumps(cases))>15000:raise ValueError("CS_ACCEPTANCE_TOTAL_BYTES")
    for item in cases:
        if not isinstance(item,dict) or set(item)!={"args","expected"} or not isinstance(item["args"],list) or len(item["args"])!=len(types):
            raise ValueError("CS_ACCEPTANCE_CASE_SHAPE")
        for value,t in zip(item["args"],types):
            literal(value,t) # validate types, bounds, dangerous symbols
        literal(item["expected"],contract["returnType"])
    return True

def literal(value,type_name):
    if type_name=="int":
        if type(value) is not int or value<-(2**31) or value>2**31-1:
            raise ValueError("CS_INT32_LITERAL_UNSAFE")
        return str(value)
    if type_name=="bool":
        if type(value) is not bool:raise ValueError("CS_BOOL_LITERAL_BAD")
        return "true" if value else "false"
    if type_name=="string":
        if not isinstance(value,str) or len(value)>500:
            raise ValueError("CS_STRING_LITERAL_TOO_LARGE")
        return json.dumps(value,ensure_ascii=True)
    if type_name=="int[]":
        if not isinstance(value,list) or len(value)>200:
            raise ValueError("CS_ARRAY_TOO_LARGE")
        return "new int[]{"+",".join(literal(x,"int") for x in value)+"}"
    raise ValueError("UNSUPPORTED_CS_TYPE")

def harness(contract,nonce):
    validate_contract(contract)
    if not re.fullmatch(r"[a-f0-9]{32}",nonce):
        raise ValueError("CS_WITNESS_NONCE_BAD")
    fn=contract["class"]+"."+contract["method"]
    commands=[]
    for item in contract["cases"]:
        args=",".join(literal(x,t) for x,t in zip(item["args"],contract["parameterTypes"]))
        expected=literal(item["expected"],contract["returnType"])
        commands.append("try{if(System.Collections.Generic.EqualityComparer<"+
                  contract["returnType"]+">.Default.Equals("+
                  fn+"("+args+"),"+expected+"))ok++;}catch(System.Exception){failures++;}")
    return (
        "using System;\ninternal static class AfTrustedAcceptance {\n"
        "public static int Main() { int ok=0;int failures=0;\n"+
        "\n".join(commands)+"\n"+
        "Console.WriteLine(\"AF_CS_WASI_OWNER_"+nonce+"=\"+ok+\"/"+str(len(commands))+
        ";EX=\"+failures);\n"
        "return (ok=="+str(len(commands))+" && failures==0)?0:7;\n"
        "}}\n")

def run(root,files,contract,*,timeout=180):
    root=Path(root).resolve()
    verified=preflight(root)
    validate_contract(contract)
    if not isinstance(files,dict) or not 1<=len(files)<=8:
        raise ValueError("CS_SOURCE_FILE_COUNT")
    if sum(len(s.encode("utf-8")) for s in files.values())>MAX_SOURCE:
        raise ValueError("CS_SOURCE_TOTAL_TOO_LARGE")
    for name,src in files.items():
        if (not re.fullmatch(r"[a-z][a-z0-9_-]{0,40}\.cs",name)
            or not isinstance(src,str) or not src.strip()):
            raise ValueError("CS_SOURCE_FILE_NAME_OR_CONTENT_INVALID")
        if re.search(r"(?m)^\s*#\s*(?:r|load)\b",src):
            raise ValueError("CS_SCRIPT_REFERENCE_FORBIDDEN")
    if any(re.search(r"(?m)\bAfTrustedAcceptance\b",src) for src in files.values()):
        raise ValueError("SOURCE_MUST_NOT_DEFINE_OWNER_HARNESS_CLASS")
    t0=time.monotonic()
    lab=root/"LAB-CSHARP-WASI-R035"
    temporary=lab/"isolated-jobs"
    temporary.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=str(temporary),prefix="cs-owner-") as name:
        work=Path(name)
        for filename,text in files.items():
            (work/filename).write_text(text,encoding="utf-8")
        nonce=uuid.uuid4().hex
        trusted=harness(contract,nonce)
        (work/"owner_runner.cs").write_text(trusted,encoding="utf-8")
        (work/"global.json").write_text('{"sdk":{"version":"10.0.401","rollForward":"disable"}}\n',encoding="utf-8")
        (work/"NuGet.Config").write_bytes((lab/"NuGet.Config").read_bytes())
        csproj=(
          '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup>\n'
          '<OutputType>Exe</OutputType><TargetFramework>net10.0</TargetFramework>\n'
          '<RuntimeIdentifier>wasi-wasm</RuntimeIdentifier><UseAppHost>false</UseAppHost>\n'
          '<PublishTrimmed>true</PublishTrimmed><InvariantGlobalization>true</InvariantGlobalization>\n'
          '<SelfContained>true</SelfContained><EnableDefaultCompileItems>false</EnableDefaultCompileItems>\n'
          '</PropertyGroup><ItemGroup>\n'
          '<PackageReference Include="BytecodeAlliance.Componentize.DotNet.Wasm.SDK" Version="'+COMPONENTIZE_VERSION+'"/>\n'
          '<PackageReference Include="runtime.win-x64.Microsoft.DotNet.ILCompiler.LLVM" Version="'+LLVM_VERSION+'"/>\n'
          '<Compile Include="owner_runner.cs"/>\n'
          +"\n".join('<Compile Include="'+xml.sax.saxutils.escape(filename)+'"/>' for filename in files)
          +'\n</ItemGroup></Project>\n')
        (work/"Acceptance.csproj").write_text(csproj,encoding="utf-8")
        env={**os.environ,"NUGET_PACKAGES":str(root/"VENDOR/componentize-packages"),
             "NUGET_HTTP_CACHE_PATH":str(root/"VENDOR/componentize-http-cache"),
             "DOTNET_ADD_GLOBAL_TOOLS_TO_PATH":"false",
             "DOTNET_CLI_HOME":str(lab/".dotnet-home"),
             "DOTNET_CLI_TELEMETRY_OPTOUT":"1",
             "DOTNET_SKIP_FIRST_TIME_EXPERIENCE":"1"}
        # The trusted .NET SDK may launch native compiler tools; it never
        # executes model-authored assembly as a Windows program.
        compilecmd=[str(DOTNET),"build","Acceptance.csproj",
                   "-c","Release","--verbosity","minimal"]
        try:
            compiled=subprocess.run(compilecmd,cwd=work,env=env,capture_output=True,
                                    stdin=subprocess.DEVNULL,timeout=timeout)
        except subprocess.TimeoutExpired:
            return {"status":"UNKNOWN_BUILD_TIMEOUT_RECONCILE","exitCode":-40,
                    "testCount":0,"functionalAcceptance":False}
        if compiled.returncode:
            return {"status":"FAILED_CSHARP_WASI_BUILD","exitCode":-41,
                    "testCount":0,"independentTestCount":0,
                    "compileStdoutTail":compiled.stdout.decode("utf-8","replace")[-3000:],
                    "compileStderrTail":compiled.stderr.decode("utf-8","replace")[-1000:],
                    "compileOutputSha256":sha_bytes(compiled.stdout),
                    "elapsedMs":round((time.monotonic()-t0)*1000)}
        wasm=work/"bin/Release/net10.0/wasi-wasm/publish/Acceptance.wasm"
        if not wasm.is_file() or wasm.stat().st_size>18000000 or wasm.read_bytes()[:4]!=b"\x00asm":
            raise IsolationUnavailable("CSHARP_WASI_COMPONENT_MAGIC_OR_SIZE_INVALID")
        exe=root/"VENDOR/wasmtime-cli-50.0.1/wasmtime.exe"
        runargs=[str(exe),"run",
                 "-W","timeout=20s,max-memory-size=536870912,max-instances=50",
                 "-S","inherit-network=n,tcp=n,udp=n,http=n,inherit-env=n,inherit-stdin=n",
                 str(wasm)]
        # Distinct host process limits as well; no user-supplied CLI flags,
        # no "--dir", no env passthrough or module args.
        try:
            guest=subprocess.run(runargs,cwd=work,stdin=subprocess.DEVNULL,
                        capture_output=True,timeout=35,
                        env={"SystemRoot":os.environ.get("SystemRoot","C:\\Windows"),
                             "WINDIR":os.environ.get("WINDIR","C:\\Windows")})
        except subprocess.TimeoutExpired:
            return {"status":"UNKNOWN_GUEST_TIMEOUT_RECONCILE","exitCode":-42,
                    "testCount":0,"functionalAcceptance":False,
                    "wasmSha256":sha_file(wasm)}
        out=guest.stdout.decode("utf-8","replace")
        lines=[x for x in out.splitlines() if x.startswith("AF_CS_WASI_OWNER_"+nonce+"=")]
        marker="AF_CS_WASI_OWNER_"+nonce+"="+str(len(contract["cases"]))+"/"+str(len(contract["cases"]))+";EX=0"
        accepted=guest.returncode==0 and len(lines)==1 and lines[0]==marker
        return {
            "status":"PASS" if accepted else "FAILED_OWNER_ACCEPTANCE",
            "exitCode":0 if accepted else -7,
            "compileExitCode":compiled.returncode,
            "guestExitCode":guest.returncode,
            "testCount":len(contract["cases"]),
            "independentTestCount":len(contract["cases"]) if accepted else 0,
            "ownerAcceptance":accepted,
            "backend":verified["backend"],
            "noNativeAssemblyExecuted":True,"hostDirectoryGrants":0,"networkCapabilities":0,
            "wasmSha256":sha_file(wasm),"wasmBytes":wasm.stat().st_size,
            "compiledOutputSha256":sha_bytes(compiled.stdout),
            "stdoutSha256":sha_bytes(guest.stdout),
            "stdoutTail":out[-1300:],
            "stderrTail":guest.stderr.decode("utf-8","replace")[-1300:],
            "sourceSha256":{k:sha_bytes(v.encode("utf-8")) for k,v in files.items()},
            "ownerCasesSha256":sha_bytes(json.dumps(contract,sort_keys=True).encode()),
            "elapsedMs":round((time.monotonic()-t0)*1000),
            "witnessPresent":len(lines)==1,
            "privateWasmtimeExeSha256":WASMTIME_SHA
        }
