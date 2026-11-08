# coding: utf-8
"""One-window first-party local job console, no new factory or web service.

The local CUDA model can propose a bounded DSL only. A human independently
reviews the proposed rules and must explicitly confirm them before the original
owner contract is committed and the original supervisor receives the job.
This GUI never runs model-authored code on Windows or calls cloud services.
"""
from __future__ import annotations
import hashlib
import json
import os
import re
import subprocess
import sys
import threading
import queue
from pathlib import Path

from . import owner_proposals,owner_oracles,autonomous_intake,desktop_requirements,portfolio_specs

ROOT=Path(__file__).resolve().parent.parent
_PY=Path(sys.executable)
_CLI=ROOT/"autofabricador.py"
_ALLOWED=re.compile(r"(?:OP|OC|OJ)-[a-f0-9]{16}\Z")
_MAX_GOAL=3800
_MAX_DRAFT=24000

def _stable_file(folder,prefix,suffix,body):
    """One-shot SHA keyed owner files, never overwrite or silently modify."""
    if not isinstance(body,bytes) or not 1<=len(body)<=24000:
        raise ValueError("GUI_OWNER_BYTES_OUTSIDE_BOUNDS")
    digest=hashlib.sha256(body).hexdigest()
    folder=Path(folder).resolve()
    if folder!=ROOT/"ENTRADAS" or not folder.is_dir():
        raise ValueError("GUI_OWNER_PATH_NOT_PROJECT_ENTRADAS")
    dest=folder/(prefix+digest[:16]+suffix)
    if dest.exists():
        if dest.is_symlink() or dest.read_bytes()!=body:
            raise RuntimeError("GUI_EXISTING_OWNER_INPUT_SHA_DRIFT_NO_REPLACE")
        return dest,digest,False
    with dest.open("xb") as f:
        f.write(body);f.flush();os.fsync(f.fileno())
    if dest.read_bytes()!=body:
        raise RuntimeError("GUI_NEW_INPUT_READBACK_SHA_FAILED")
    return dest,digest,True

def save_goal(goal):
    if type(goal) is not str:
        raise ValueError("GUI_GOAL_MUST_BE_STRING")
    goal=goal.strip()
    if not 24<=len(goal)<=_MAX_GOAL or "\x00" in goal:
        raise ValueError("GUI_GOAL_LENGTH_INVALID")
    blob=(goal+"\n").encode("utf-8")
    return _stable_file(ROOT/"ENTRADAS","gui_goal_",".txt",blob)

def review_contract(raw):
    """Syntactic and deterministic semantic validator, NOT an owner approval."""
    if type(raw) is not str or not 1<=len(raw.encode("utf-8"))<=_MAX_DRAFT:
        raise ValueError("GUI_REVIEW_JSON_TOO_LARGE_OR_MISSING")
    def reject(v):
        raise ValueError("GUI_NONFINITE_VALUE:"+v)
    data=json.loads(raw,parse_constant=reject)
    if not isinstance(data,dict) or set(data)!={"schema","language","goal",
                                                   "exportName","argTypes","oracle","maxCases"}:
        raise ValueError("GUI_REVIEW_CONTRACT_KEYS_INVALID")
    if data["schema"]!=1 or data["language"]!="javascript":
        raise ValueError("GUI_UNSUPPORTED_REVIEW_CONTRACT")
    if not isinstance(data["goal"],str) or not 24<=len(data["goal"])<=4000:
        raise ValueError("GUI_GOAL_NOT_VALID")
    if not isinstance(data["exportName"],str) or not owner_oracles.open_orders._IDENTIFIER.fullmatch(data["exportName"]):
        raise ValueError("GUI_FUNCTION_NAME_INVALID")
    if (not isinstance(data["argTypes"],list) or
        not 1<=len(data["argTypes"])<=3 or
        any(type(x) is not str or x not in owner_oracles._TYPES for x in data["argTypes"])):
        raise ValueError("GUI_ORACLE_TYPES_INVALID")
    if type(data["maxCases"]) is not int or not 5<=data["maxCases"]<=80:
        raise ValueError("GUI_ORACLE_CASES_INVALID")
    owner_oracles._safe_node(data["oracle"],data["argTypes"])
    cases=owner_oracles._make_cases(data)
    if len(cases)<5:
        raise ValueError("GUI_INDEPENDENT_REFERENCE_CASE_COUNT_INVALID")
    blob=(json.dumps(data,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+"\n").encode("utf-8")
    if len(blob)>_MAX_DRAFT:
        raise ValueError("GUI_SERIALIZED_CONTRACT_TOO_LARGE")
    return data,blob,len(cases)

def save_owner_contract(confirmed_data):
    """Call ONLY after explicit human review; no autoapproval from model."""
    if type(confirmed_data) is not str:
        raise ValueError("GUI_REVIEWED_CONTRACT_REQUIRED")
    spec,bytes_,count=review_contract(confirmed_data)
    path,sha,created=_stable_file(ROOT/"ENTRADAS","gui_reviewed_",".json",bytes_)
    return {"path":str(path),"sha":sha,"created":created,"cases":count,
            "ownerReviewDeclared":True,
            "modelDidNotIndependentlyApproveItsOwnTests":True}

def _call(action,*args,timeout=300):
    if action not in ("portfolio-preview","portfolio-submit","portfolio-status",
                      "desktop-preview","desktop-submit","desktop-status",
                      "auto-goal-preview","auto-goal-submit",
                      "auto-goal-status","proposal-draft","contract-preview","contract-submit",
                      "contract-status","proposal-status","reboot-verify",
                      "supervisor-status"):
        raise ValueError("GUI_ORIGINAL_CLI_COMMAND_NOT_ALLOWLISTED")
    argv=[str(_PY),"-B",str(_CLI),action]+[str(a) for a in args]
    result=subprocess.run(argv,cwd=str(ROOT),stdin=subprocess.DEVNULL,
       capture_output=True,text=True,timeout=timeout,
       env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1",
            "DOTNET_ADD_GLOBAL_TOOLS_TO_PATH":"false"})
    if result.returncode:
        raise RuntimeError("ORIGINAL_CLI_REJECTED_"+action+": "+
            (result.stderr or result.stdout)[-1000:])
    obj=json.loads(result.stdout)
    if not isinstance(obj,dict):
        raise RuntimeError("GUI_ORIGINAL_CLI_RETURN_NOT_JSON_OBJECT")
    return obj

def main():
    import tkinter as tk
    from tkinter import messagebox,scrolledtext,ttk
    app=tk.Tk()
    app.title("AUTOFABRICADOR | Entregar trabajo LOCAL")
    app.geometry("1030x790")
    app.minsize(790,620)
    app.configure(background="#edf1f5")
    background="#edf1f5";navy="#14293b"
    top=ttk.Frame(app,padding=(18,12))
    top.pack(fill="x")
    ttk.Label(top,text="AUTOFABRICADOR · Agentes locales + IA GPU",
              font=("Segoe UI",16,"bold")).pack(anchor="w")
    ttk.Label(top,text="La IA propone. Tú compruebas la regla. El supervisor original construye, prueba y entrega.",
              wraplength=990).pack(anchor="w",pady=(4,0))
    content=ttk.Frame(app,padding=(18,4,18,8))
    content.pack(fill="both",expand=True)
    ttk.Label(content,text="1 · Describe tu trabajo",font=("Segoe UI",11,"bold")).pack(anchor="w")
    goal=scrolledtext.ScrolledText(content,height=5,font=("Consolas",10),wrap="word")
    goal.pack(fill="x",pady=(3,8))
    ttk.Label(content,text="2 · Revisa y edita el contrato propuesto (JSON; no es una prueba aprobada)",
              font=("Segoe UI",11,"bold")).pack(anchor="w",pady=(4,0))
    editor=scrolledtext.ScrolledText(content,height=17,font=("Consolas",10),wrap="none")
    editor.pack(fill="both",expand=True,pady=(3,8))
    summary=tk.StringVar(value="Listo. Puedes pegar un objetivo en el primer recuadro.")
    ttk.Label(content,textvariable=summary,wraplength=950,foreground=navy).pack(fill="x")
    status_box=scrolledtext.ScrolledText(content,height=6,font=("Consolas",9),wrap="word",state="disabled")
    status_box.pack(fill="x",pady=(6,8))
    buttons=ttk.Frame(content)
    buttons.pack(fill="x")
    inflight=[False]
    lastcontract=[None]
    lastautogoal=[None]
    events=queue.Queue()
    controls=[]
    def log(msg):
        status_box.configure(state="normal")
        status_box.insert("end",str(msg)+"\n")
        status_box.see("end")
        status_box.configure(state="disabled")
    def busy(value):
        inflight[0]=value
        for widget in controls:
            widget.configure(state="disabled" if value else "normal")
    def work(name,func):
        if inflight[0]:
            return
        busy(True)
        summary.set(name+"…")
        def runner():
            try:events.put(("ok",name,func()))
            except Exception as exc:events.put(("error",name,str(exc)))
        threading.Thread(target=runner,daemon=True,name="AF-GUI-Original-CLI").start()
    def drain():
        try:
            while True:
                typ,name,data=events.get_nowait()
                busy(False)
                if typ=="error":
                    summary.set(name+" · no completado")
                    log("ERROR: "+data)
                elif name=="PROPONER":
                    info,draft=data
                    lastcontract[0]=None
                    editor.delete("1.0","end")
                    editor.insert("1.0",draft)
                    summary.set("Propuesta de IA NO APROBADA · Revisa toda la regla antes de entregar.")
                    log("Propuesta "+info["proposalId"]+
                        " | estado "+info["status"]+
                        " | origen GPU local · no se ha enviado a fabricar")
                elif name=="AUTO":
                    pre,submitted=data
                    if submitted.get("status")=="SUBMITTED_TO_ORIGINAL_AUTOFABRICADOR_QUEUE" and "profile" in submitted:
                        lastautogoal[0]=submitted["jobId"]
                        summary.set("Aplicación "+submitted["profile"]+" aceptada por agentes internos LOCAL.")
                        log("Trabajo original "+submitted["jobId"]+" / cola "+submitted["queueId"])
                        log("Pruebas originales independientes de cada dominio y persistencia SQLite.")
                    elif submitted.get("status")=="SUBMITTED_ONCE_TO_ORIGINAL_LOCAL_SUPERVISOR" and "appId" in submitted:
                        lastautogoal[0]=submitted["jobId"]
                        summary.set("Proyecto de escritorio admitido: los agentes originales trabajan en local.")
                        log("Proyecto "+submitted["jobId"]+" / cola "+submitted["queueId"])
                        log("Verificador independiente: GUI, SQLite, CRUD, CSV, instalación y restauración.")
                        log("La IA planifica; la ejecución de Python proviene de componentes confiables.")
                    elif submitted.get("status")=="AUTO_SUBMITTED_TO_ORIGINAL_LOCAL_FACTORY":
                        lastautogoal[0]=submitted["goalId"]
                        summary.set("Orden admitida. Los agentes locales ya construyen y verifican.")
                        log("Orden "+submitted["goalId"]+" -> "+submitted["originalJobId"])
                        log("Reglas deterministas independientes: "+str(submitted["independentCases"]))
                        log("Consulta Estado para ver la aceptacion y el ZIP.")
                    else:
                        summary.set("Orden no autorizada automaticamente: semantica no verificable.")
                        log(json.dumps(submitted,ensure_ascii=False,indent=2)[:2000])
                elif name=="ENTREGAR":
                    info,pre,submitted=data
                    lastcontract[0]=submitted.get("contractId")
                    summary.set("Entrega registrada en el supervisor ORIGINAL. Consulta el estado.")
                    log("Contrato "+str(submitted.get("contractId"))+
                        " · "+str(submitted.get("status")))
                    log("Ruta de contrato revisado: "+info["path"])
                    log("Pruebas generadas ANTES del modelo: "+str(pre.get("ownerCaseCount"))+
                        " · SHA "+str(pre.get("derivedSha")))
                    log("Trabajo original: "+json.dumps(submitted.get("original",{}),
                         ensure_ascii=False)[:1400])
                else:
                    summary.set(name+" · consulta completada")
                    log(json.dumps(data,ensure_ascii=False,indent=2)[:4000])
        except queue.Empty:
            pass
        if app.winfo_exists():
            app.after(150,drain)
    def auto():
        contents=goal.get("1.0","end-1c")
        def run():
            f,hash_,created=save_goal(contents)
            if len(contents.strip())>=50 and portfolio_specs.scope(contents)["status"]=="PASS_FROZEN_INDEPENDENT_FIRST_PARTY_SCOPE":
                pre=_call("portfolio-preview",f,timeout=70)
                sent=_call("portfolio-submit",f,timeout=90)
                return pre,sent
            if desktop_requirements.compile(contents)["status"]=="FROZEN_FIRST_PARTY_DESKTOP_ORDERS_SCOPE":
                pre=_call("desktop-preview",f,timeout=70)
                sent=_call("desktop-submit",f,timeout=90)
                return pre,sent
            pre=_call("auto-goal-preview",f,timeout=70)
            if pre.get("status")!="INDEPENDENT_FIRST_PARTY_RECIPE_COMPILED":
                return pre,pre
            result=_call("auto-goal-submit",f,timeout=80)
            return pre,result
        work("AUTO",run)
    def propose():
        contents=goal.get("1.0","end-1c")
        def run():
            f,hash_,created=save_goal(contents)
            response=_call("proposal-draft",f,timeout=260)
            if response.get("status")!="UNTRUSTED_DRAFT_REVIEW_REQUIRED":
                raise RuntimeError("PROPOSAL_NOT_APPROVABLE:"+str(response.get("status")))
            draft_path=ROOT/"proposals"/response["proposalId"]/"DRAFT-UNTRUSTED.json"
            if not draft_path.is_file() or draft_path.is_symlink():
                raise RuntimeError("UNTRUSTED_ORIGINAL_DRAFT_NOT_SAVED")
            raw=draft_path.read_text("utf-8")
            if hashlib.sha256(raw.encode()).hexdigest()!=response["untrustedDraftSha"]:
                raise RuntimeError("ORIGINAL_MODEL_DRAFT_SHA_DRIFT")
            return response,raw
        work("PROPONER",run)
    def deliver():
        text=editor.get("1.0","end-1c")
        try:
            data,blob,count=review_contract(text)
        except Exception as exc:
            messagebox.showerror("Contrato inválido",str(exc),parent=app)
            return
        approved=messagebox.askyesno("Confirmar revisión independiente",
            "¿Has COMPROBADO personalmente que las reglas del contrato representan "
            "el trabajo solicitado y que los casos esperados se pueden calcular "
            "con ellas?\n\n"+str(count)+" casos se generarán ANTES de la inferencia. "
            "Esta confirmación es tu revisión de la especificación, no una "
            "autovalidación de la IA.\n\nSi la propuesta es dudosa, pulsa No y corrígela.",
            parent=app,icon="warning")
        if not approved:
            return
        def run():
            file=save_owner_contract(text)
            pre=_call("contract-preview",file["path"],timeout=60)
            if pre.get("ownerCaseCount")!=file["cases"]:
                raise RuntimeError("INDEPENDENT_PREVIEW_CASES_CHANGED")
            answer=_call("contract-submit",file["path"],timeout=75)
            return file,pre,answer
        work("ENTREGAR",run)
    def check():
        aid=lastautogoal[0]
        if aid and re.fullmatch(r"DP-[a-f0-9]{16}",aid):
            work("ESTADO",lambda:_call("portfolio-status",aid,timeout=65))
            return
        if aid and re.fullmatch(r"DW-[a-f0-9]{16}",aid):
            work("ESTADO",lambda:_call("desktop-status",aid,timeout=65))
            return
        if aid and re.fullmatch(r"AG-[a-f0-9]{16}",aid):
            work("ESTADO",lambda:_call("auto-goal-status",aid,timeout=65))
            return
        cid=lastcontract[0]
        if cid and _ALLOWED.fullmatch(cid):
            work("ESTADO",lambda:_call("contract-status",cid,timeout=65))
        else:
            work("ESTADO",lambda:_call("supervisor-status",timeout=65))
    def reboot():
        work("REINICIO",lambda:_call("reboot-verify",timeout=75))
    for name,fn in (
        ("Encargar automaticamente",auto),
        ("1 · Proponer con IA local",propose),
        ("2 · Revisado: entregar",deliver),
        ("Estado del trabajo",check),
        ):
        button=ttk.Button(buttons,text=name,command=fn)
        button.pack(side="left",padx=(0,8))
        controls.append(button)
    ttk.Label(content,text="Ejecución directa de JS acotado, pedidos, inventario, tareas y gastos Tk/SQLite con alcance independiente verificado. Los demás trabajos requieren requisitos comprobables. No instala en Host ni convierte una propuesta de IA en aceptación independiente.",
              wraplength=970).pack(anchor="w",pady=(8,0))
    app.after(150,drain)
    app.mainloop()

if __name__=="__main__":
    main()
