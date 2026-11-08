# coding: utf-8
"""Independent original owner contract for three different bounded GUI apps.

The model may plan, but never adds/removes schema, changes acceptance, grants
network/Host privileges or controls executable source. Open-domain arbitrary
applications remain deliberately unsupported. Current-user offline only.
"""
from __future__ import annotations
import hashlib,re,unicodedata
from pathlib import Path
def sha_bytes(data):return hashlib.sha256(data).hexdigest()

PROFILES={
 "inventory":{
   "title":"Inventario local",
   "keywords":("inventario","stock","existencias","almacen","inventory","warehouse"),
   "features":("items","sku","quantity","minimum","unit_price","low_stock","stock_value","csv","sqlite","gui"),
   "fields":[("sku","text"),("name","text"),("quantity","nonnegative"),("minimum","nonnegative"),("unit_cents","nonnegative")],
   "sample":[
    {"sku":"ART-01","name":"Cable USB","quantity":5,"minimum":7,"unit_cents":190},
    {"sku":"ART-02","name":"Cargador","quantity":15,"minimum":3,"unit_cents":1250}],
   "extra":{"type":"inventory","lowStockLogic":"quantity<=minimum","totalValue":"sum(quantity*unit_cents)"},
   "negative":("without stock","sin inventario")},
 "tasks":{
   "title":"Gestor de tareas",
   "keywords":("tareas","agenda","plazos","pendientes","tasks","due date"),
   "features":("tasks","due_dates","priority","completed","overdue","search","csv","sqlite","gui"),
   "fields":[("code","text"),("title","text"),("due_date","date"),("priority","priority"),("completed","bool")],
   "sample":[
     {"code":"TASK-01","title":"Enviar propuesta","due_date":"2020-01-01","priority":"high","completed":0},
     {"code":"TASK-02","title":"Archivar notas","due_date":"2099-12-31","priority":"low","completed":1}],
   "extra":{"type":"tasks","overdueLogic":"due_date<today and completed==0","completedLogic":"completed==1"},
   "negative":("sin tareas","without tasks")},
 "expenses":{
   "title":"Control de gastos",
   "keywords":("gastos","expense","egresos","spending","presupuesto domestico"),
   "features":("expenses","merchant","category","amount","date","monthly_totals","search","csv","sqlite","gui"),
   "fields":[("code","text"),("merchant","text"),("booking_date","date"),("category","category"),("amount_cents","positive")],
   "sample":[
     {"code":"EXP-01","merchant":"Papeleria","booking_date":"2026-11-07","category":"office","amount_cents":1250},
     {"code":"EXP-02","merchant":"Tren","booking_date":"2026-11-02","category":"travel","amount_cents":8700}],
   "extra":{"type":"expenses","monthlyTotals":"sum(amount_cents grouped by YYYY-MM)","categoryTotals":"sum(amount_cents grouped by category)"},
   "negative":("sin gastos","without expenses")}
}
_UNSUPPORTED=(
 "cloud","nube","api externa","oauth","usuarios y permisos","administrador",
 "stripe","paypal","bancaria","transferencia bancaria","multiequipo",
 "sin conexion local","online","conectado a internet","integracion remota",
 "email","correo electronico","smtp","pagos bancarios","bitcoin",
 "multitenant","inteligencia artificial que autoejecute python","sistema operativo")
_REQUIRED_COMMON=("interfaz","escritorio","local","sqlite","csv")
def normalize(value):
 if type(value) is not str or not 50<=len(value)<=5000 or "\x00" in value:
  raise ValueError("PORTFOLIO_GOAL_LENGTH_OR_TEXT_INVALID")
 value=unicodedata.normalize("NFKD",value).casefold()
 return " ".join("".join(c for c in value if not unicodedata.combining(c)).split())
def matches(text,phrase):
 return re.search(r"(?<![a-z0-9])"+re.escape(phrase)+r"(?![a-z0-9])",text) is not None
def scope(goal):
 raw=normalize(goal)
 found=[key for key,p in PROFILES.items() if any(matches(raw,k) for k in p["keywords"])]
 unsupported=[phrase for phrase in _UNSUPPORTED if matches(raw,phrase)]
 missing=[token for token in _REQUIRED_COMMON if not matches(raw,token)]
 negated=[key for key,p in PROFILES.items() if any(matches(raw,k) for k in p["negative"])]
 if len(found)!=1 or unsupported or missing or negated:
  return {"status":"BLOCKED_INDEPENDENT_OWNER_UNSUPPORTED_OR_AMBIGUOUS",
          "profilesDetected":found,"missing":missing,
          "unsupported":sorted(unsupported),"negated":sorted(negated),
          "modelCalled":False,"newSideEffects":False}
 key=found[0]
 profile=PROFILES[key]
 return {"status":"PASS_FROZEN_INDEPENDENT_FIRST_PARTY_SCOPE",
  "profile":key,"title":profile["title"],"features":list(profile["features"]),
  "fieldContract":[list(x) for x in profile["fields"]],
  "independentOwnerAcceptance":True,"modelCanApproveOwnTests":False,
  "trustedCodeOnly":True,"runtime":"LOCAL_WINDOWS_PYTHON_TK_SQLITE",
  "generalArbitrarySoftwareAccepted":False}
def from_file(root,goalfile):
 root=Path(root).resolve()
 p=Path(goalfile).resolve()
 if (p.parent!=root/"ENTRADAS" or p.suffix.lower()!=".txt"
     or not p.is_file() or p.is_symlink() or p.stat().st_size>7000):
  raise ValueError("PORTFOLIO_GOAL_ONLY_LOCAL_ENTRADAS")
 data=p.read_bytes()
 goal=data.decode("utf-8-sig").strip()
 result=scope(goal)
 ident="DP-"+sha_bytes(data)[:16]
 app="AFD-"+sha_bytes(data)[:16]
 return {"goal":goal,"goalPath":str(p),"inputSha":sha_bytes(data),
         "jobId":ident,"appId":app,"scope":result}
