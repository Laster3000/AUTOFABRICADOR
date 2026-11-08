#!/usr/bin/env python3
# coding: utf-8
"""AF R76 first-party localhost reference application server.

SQLite CRUD with single-admin in-memory sessions, CSRF and version locking.
AI endpoint never starts unless explicit opt-in + original CUDA backend passes
its own lease/pinning/memory policy. No model-generated Python runs on Host.
This proves a bounded interactive reference app, not arbitrary fullstack AI code.
"""
from __future__ import annotations
import argparse,base64,contextlib,datetime,hashlib,hmac,http.cookies,http.server
import json,os,re,secrets,signal,sqlite3,sys,threading,time,urllib.parse,urllib.request
from pathlib import Path

VERSION="AF.R76.REFERENCE.FULLSTACK.1"
ALLOWED=("index.html","app.css","app.js","game2d.js","game3d.js",
         "logic-2d-r75.js","logic-3d-r75.js","logic-api-r76.js","manifest.webmanifest",
         "service-worker.js","icon-192.png","icon-512.png")
MIME={".html":"text/html",".css":"text/css",".js":"text/javascript",
      ".webmanifest":"application/manifest+json",".png":"image/png"}
SKU=re.compile(r"[A-Z0-9-]{1,12}\Z")
_ORIGIN_HEADERS=("Origin","Referer")
MODEL_ROOT=Path(r"C:\AF-PORTABLE")

def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def compare(a,b):return hmac.compare_digest(a,b)
def compact(value):return json.dumps(value,ensure_ascii=False,separators=(",",":")).encode("utf-8")
def valid_item(obj,*,create=False):
 if type(obj) is not dict or set(obj)!=( {"sku","name","qty"} if create else {"qty","expectedVersion"}):
  raise ValueError("FIELD_SET_INVALID")
 if create:
  if type(obj["sku"]) is not str or not SKU.fullmatch(obj["sku"]):
   raise ValueError("SKU_INVALID")
  if type(obj["name"]) is not str or not 1<=len(obj["name"].strip())<=70:
   raise ValueError("NAME_INVALID")
 if type(obj["qty"]) is not int or not 0<=obj["qty"]<=100000:
  raise ValueError("QTY_INVALID")
 if not create and (type(obj["expectedVersion"]) is not int or obj["expectedVersion"]<1):
  raise ValueError("VERSION_INVALID")
 return obj

class Inventory:
 def __init__(self,path):
  self.path=Path(path).resolve()
  self.path.parent.mkdir(parents=True,exist_ok=True)
  self.lock=threading.RLock()
  with self.connection() as db:
   db.execute("PRAGMA journal_mode=WAL")
   db.execute("CREATE TABLE IF NOT EXISTS items(sku TEXT PRIMARY KEY, name TEXT NOT NULL,qty INTEGER NOT NULL CHECK(qty BETWEEN 0 AND 100000),version INTEGER NOT NULL DEFAULT 1)")
   db.execute("CREATE TABLE IF NOT EXISTS audit(seq INTEGER PRIMARY KEY AUTOINCREMENT,ts TEXT NOT NULL, action TEXT NOT NULL,sku TEXT NOT NULL)")
 def connection(self):
  db=sqlite3.connect(self.path,timeout=12,isolation_level="DEFERRED")
  db.row_factory=sqlite3.Row
  db.execute("PRAGMA busy_timeout=12000")
  return db
 def items(self):
  with self.lock,self.connection() as db:
   return [dict(r) for r in db.execute("SELECT sku,name,qty,version FROM items ORDER BY sku")]
 def audit(self):
  with self.lock,self.connection() as db:
   return [dict(r) for r in db.execute("SELECT seq,ts,action,sku FROM audit ORDER BY seq DESC LIMIT 50")]
 def add(self,doc):
  valid_item(doc,create=True)
  with self.lock,self.connection() as db:
   try:
    db.execute("INSERT INTO items(sku,name,qty,version) VALUES(?,?,?,1)",
               (doc["sku"],doc["name"].strip(),doc["qty"]))
   except sqlite3.IntegrityError:
    return 409,{"error":"SKU_DUPLICADO"}
   db.execute("INSERT INTO audit(ts,action,sku) VALUES(?,?,?)",(now(),"CREATE",doc["sku"]))
   return 201,{"sku":doc["sku"],"version":1}
 def update(self,sku,doc):
  valid_item(doc)
  with self.lock,self.connection() as db:
   cur=db.execute("UPDATE items SET qty=?,version=version+1 WHERE sku=? AND version=?",
      (doc["qty"],sku,doc["expectedVersion"]))
   if cur.rowcount!=1:return 409,{"error":"VERSION_CONFLICT"}
   db.execute("INSERT INTO audit(ts,action,sku) VALUES(?,?,?)",(now(),"UPDATE",sku))
   return 200,{"sku":sku,"version":doc["expectedVersion"]+1}
 def delete(self,sku,doc):
  if type(doc) is not dict or set(doc)!={"expectedVersion"} or type(doc["expectedVersion"]) is not int:
   raise ValueError("VERSION_INVALID")
  with self.lock,self.connection() as db:
   cur=db.execute("DELETE FROM items WHERE sku=? AND version=?",
     (sku,doc["expectedVersion"]))
   if cur.rowcount!=1:return 409,{"error":"VERSION_CONFLICT"}
   db.execute("INSERT INTO audit(ts,action,sku) VALUES(?,?,?)",(now(),"DELETE",sku))
   return 200,{"removed":sku}

class Application:
 def __init__(self,static,db,username,password,*,enable_ai=False,qa_ai_stub=False,model_root=MODEL_ROOT):
  self.root=Path(static).resolve()
  self.database=Inventory(db)
  if not username or not password or len(password)<12:
   raise ValueError("ADMIN_CREDENTIALS_REQUIRED_AT_RUNTIME")
  self.username=username
  self.salt=os.urandom(24)
  self.password_hash=hashlib.pbkdf2_hmac("sha256",password.encode(),self.salt,240000)
  self.sessions={}
  self.sessions_lock=threading.RLock()
  self.attempts={}
  self.enable_ai=enable_ai
  self.qa_ai_stub=qa_ai_stub
  self.model_root=Path(model_root).resolve()
  self.ai_lock=threading.Lock()
  self.bound_port=None
 def auth(self,header):
  cookie=http.cookies.SimpleCookie()
  try:cookie.load(header or "")
  except Exception:return None
  morsel=cookie.get("af_session")
  if not morsel:return None
  with self.sessions_lock:
   row=self.sessions.get(morsel.value)
   if not row:return None
   if row["expiry"]<time.time():
    self.sessions.pop(morsel.value,None)
    return None
   return row
 def login(self,username,password):
  nowsec=time.monotonic()
  with self.sessions_lock:
   recent=[v for v in self.attempts.get("local",[]) if nowsec-v<60]
   if len(recent)>=10:return 429,{"error":"RATE_LIMIT"},None
   recent.append(nowsec);self.attempts["local"]=recent
  expected=hashlib.pbkdf2_hmac("sha256",password.encode(),self.salt,240000)
  if username!=self.username or not compare(expected,self.password_hash):
   return 401,{"error":"INVALID_CREDENTIALS"},None
  token=secrets.token_urlsafe(32)
  csrf=secrets.token_urlsafe(32)
  with self.sessions_lock:
   self.sessions[token]={"username":username,"csrf":csrf,"expiry":time.time()+3600}
  return 200,{"username":username,"csrf":csrf},token
 def ai_answer(self,prompt):
  if not self.enable_ai:return 503,{"error":"LOCAL_AI_DISABLED_BY_DEFAULT"}
  if self.qa_ai_stub:
   return 200,{"text":"QA: "+prompt[:100],"mode":"FIRST_PARTY_FAKE_MODEL_TEST_ONLY","tokenBudget":96}
  # Original provider owns GPU leases, memory floors and backend hashes.
  sys.path.insert(0,str(self.model_root))
  from autofab import local_cuda9b
  if not self.ai_lock.acquire(blocking=False):
   return 429,{"error":"AI_BUSY"}
  started=False
  try:
   if local_cuda9b.server_info(self.model_root)["state"]!="NOT_STARTED":
    return 409,{"error":"AI_PREEXISTING_LEASE_REQUIRES_RECONCILIATION"}
   state=local_cuda9b.start(self.model_root)
   if state["state"]!="READY":raise RuntimeError("GPU_SERVER_NOT_READY")
   started=True
   payload={"model":local_cuda9b.ALIAS,"stream":False,"temperature":0,
     "max_tokens":144,"response_format":{"type":"json_object"},
     "messages":[{"role":"system","content":"Return exactly one JSON object {\"answer\":\"...\"} with a concise helpful response in Spanish, no extra keys, no HTML or code execution."},
                 {"role":"user","content":prompt}]}
   req=urllib.request.Request("http://127.0.0.1:11479/v1/chat/completions",
       data=compact(payload),headers={"Content-Type":"application/json"},method="POST")
   with urllib.request.urlopen(req,timeout=125) as response:
    body=json.loads(response.read(64000))
   raw=body["choices"][0]["message"]["content"]
   obj=json.loads(raw)
   if type(obj) is not dict or set(obj)!={"answer"} or type(obj["answer"]) is not str:
    return 502,{"error":"MODEL_INVALID_JSON"}
   return 200,{"text":obj["answer"][:1000],"mode":"REAL_LOCAL_QWEN35_GPU9B","tokenBudget":144}
  except Exception as ex:
   return 503,{"error":"LOCAL_MODEL_UNAVAILABLE","reason":type(ex).__name__+":"+str(ex)[:180]}
  finally:
   if started:
    try:
     stopped=local_cuda9b.stop(self.model_root)
     if stopped["state"]!="STOPPED_VERIFIED":sys.stderr.write("AI_STOP_UNCERTAIN\n")
    except Exception as exc:
     sys.stderr.write("AI_STOP_UNKNOWN_VERIFY_LEASE:"+type(exc).__name__+"\n")
   self.ai_lock.release()

def handler_factory(app):
 class Handler(http.server.BaseHTTPRequestHandler):
  server_version="AF-R76-Local"
  def log_message(self,fmt,*args):
   # Deliberately never print user content, cookies or credentials.
   sys.stderr.write("R76_HTTP "+self.command+" "+str(self.path).split("?")[0][:90]+" "+
                    str(args[1] if len(args)>1 else "?")+"\n")
  def respond(self,code,obj,cookie=None):
   body=compact(obj)
   self.send_response(code)
   self.headers_safe()
   self.send_header("Content-Type","application/json; charset=utf-8")
   self.send_header("Cache-Control","no-store")
   if cookie:self.send_header("Set-Cookie",cookie)
   self.send_header("Content-Length",str(len(body)))
   self.end_headers()
   self.wfile.write(body)
  def headers_safe(self):
   self.send_header("X-Content-Type-Options","nosniff")
   self.send_header("Referrer-Policy","no-referrer")
   self.send_header("X-Frame-Options","DENY")
   self.send_header("Content-Security-Policy","default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; connect-src 'self'; worker-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'")
  def guard(self):
   host=self.headers.get("Host","")
   if host!="127.0.0.1:"+str(app.bound_port):return False
   origin=self.headers.get("Origin")
   if origin and origin!="http://127.0.0.1:"+str(app.bound_port):return False
   referer=self.headers.get("Referer")
   if referer and not referer.startswith("http://127.0.0.1:"+str(app.bound_port)+"/"):
    return False
   return True
  def json_input(self):
   if self.headers.get("Content-Type","").split(";")[0].strip()!="application/json":
    raise ValueError("JSON_CONTENT_TYPE_REQUIRED")
   text=self.headers.get("Content-Length","0")
   if not text.isdigit() or not 0<int(text)<=4096:raise ValueError("JSON_SIZE_INVALID")
   raw=self.rfile.read(int(text))
   def strict(pairs):
    d={}
    for k,v in pairs:
     if k in d:raise ValueError("DUPLICATE_JSON_KEY")
     d[k]=v
    return d
   return json.loads(raw.decode("utf8"),object_pairs_hook=strict,
      parse_constant=lambda v: (_ for _ in ()).throw(ValueError("NONFINITE_DENIED")))
  def require(self,*,mutation=False):
   state=app.auth(self.headers.get("Cookie"))
   if state is None:
    self.respond(401,{"error":"LOGIN_REQUIRED"});return None
   if mutation and not compare(self.headers.get("X-CSRF-Token",""),state["csrf"]):
    self.respond(403,{"error":"CSRF_DENIED"});return None
   return state
  def static(self):
   uri=urllib.parse.urlsplit(self.path).path
   if uri in ("/","/inventory","/game2d","/game3d","/ai"):
    filename="index.html"
   else:
    filename=uri.lstrip("/")
   if filename not in ALLOWED:
    return self.respond(404,{"error":"NOT_FOUND"})
   file=app.root/filename
   if not file.is_file() or file.is_symlink() or file.resolve().parent!=app.root:
    return self.respond(404,{"error":"STATIC_NOT_FOUND"})
   data=file.read_bytes()
   self.send_response(200);self.headers_safe()
   self.send_header("Content-Type",MIME.get(file.suffix,"application/octet-stream"))
   self.send_header("Cache-Control","no-cache")
   self.send_header("Content-Length",str(len(data)))
   self.end_headers();self.wfile.write(data)
  def do_GET(self):
   if not self.guard():return self.respond(403,{"error":"HOST_OR_ORIGIN_REJECTED"})
   route=urllib.parse.urlsplit(self.path).path
   if route=="/api/health":
    return self.respond(200,{"status":"ok","version":VERSION,"aiEnabled":app.enable_ai})
   if route=="/api/session":
    user=self.require()
    if user is None:return
    return self.respond(200,{"username":user["username"],"csrf":user["csrf"]})
   if route=="/api/items":
    user=self.require()
    if user is None:return
    return self.respond(200,{"items":app.database.items()})
   if route=="/api/audit":
    user=self.require()
    if user is None:return
    return self.respond(200,{"events":app.database.audit()})
   if route.startswith("/api/"):return self.respond(404,{"error":"API_NOT_FOUND"})
   return self.static()
  def do_POST(self):return self.mutate("POST")
  def do_PATCH(self):return self.mutate("PATCH")
  def do_DELETE(self):return self.mutate("DELETE")
  def mutate(self,method):
   if not self.guard():return self.respond(403,{"error":"HOST_OR_ORIGIN_REJECTED"})
   route=urllib.parse.urlsplit(self.path).path
   if route=="/api/login" and method=="POST":
    try:
     obj=self.json_input()
     if type(obj) is not dict or set(obj)!={"username","password"} or any(type(v) is not str for v in obj.values()):
      raise ValueError("CREDENTIALS_INVALID")
     status,result,token=app.login(obj["username"],obj["password"])
     return self.respond(status,result,
       "af_session="+token+"; HttpOnly; SameSite=Strict; Path=/; Max-Age=3600" if token else None)
    except (ValueError,UnicodeError,json.JSONDecodeError):
     return self.respond(400,{"error":"INVALID_LOGIN_REQUEST"})
   state=self.require(mutation=True)
   if state is None:return
   try:
    obj=self.json_input()
    if route=="/api/logout" and method=="POST":
     c=http.cookies.SimpleCookie()
     c.load(self.headers.get("Cookie",""))
     token=c.get("af_session")
     if token:
      with app.sessions_lock:app.sessions.pop(token.value,None)
     return self.respond(200,{"loggedOut":True},
       "af_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0")
    if route=="/api/items" and method=="POST":
     code,response=app.database.add(obj)
     return self.respond(code,response)
    if route.startswith("/api/items/") and method in ("PATCH","DELETE"):
     sku=route.removeprefix("/api/items/")
     if not SKU.fullmatch(sku):raise ValueError("SKU_INVALID")
     code,response=(app.database.update(sku,obj) if method=="PATCH"
                    else app.database.delete(sku,obj))
     return self.respond(code,response)
    if route=="/api/ai" and method=="POST":
     if type(obj) is not dict or set(obj)!={"prompt"} or type(obj["prompt"]) is not str or not 1<=len(obj["prompt"])<=450:
      raise ValueError("PROMPT_INVALID")
     code,response=app.ai_answer(obj["prompt"])
     return self.respond(code,response)
    return self.respond(404,{"error":"API_NOT_FOUND"})
   except (ValueError,UnicodeError,json.JSONDecodeError):
    return self.respond(400,{"error":"VALIDATION_ERROR"})
 class SafeThreadingServer(http.server.ThreadingHTTPServer):
  daemon_threads=True
  allow_reuse_address=False
 return Handler,SafeThreadingServer
def main():
 parser=argparse.ArgumentParser()
 parser.add_argument("--static",type=Path,default=Path(__file__).resolve().parent)
 parser.add_argument("--db",type=Path,required=True)
 parser.add_argument("--port",type=int,default=0)
 parser.add_argument("--ready",type=Path,required=True)
 parser.add_argument("--enable-local-ai",action="store_true")
 parser.add_argument("--qa-stub-ai",action="store_true")
 args=parser.parse_args()
 if args.port<0 or args.port>65535:parser.error("invalid port")
 if args.qa_stub_ai and os.environ.get("AF_R76_QA_STUB")!="1":
  parser.error("stub strictly for QA test")
 passwd=os.environ.get("AF_R76_ADMIN_PASSWORD")
 if not passwd or len(passwd)<12:parser.error("AF_R76_ADMIN_PASSWORD required")
 app=Application(args.static,args.db,"admin",passwd,
   enable_ai=args.enable_local_ai,qa_ai_stub=args.qa_stub_ai)
 Handler,Server=handler_factory(app)
 with Server(("127.0.0.1",args.port),Handler) as srv:
  app.bound_port=srv.server_address[1]
  ready={"status":"BOUND_127_0_0_1","version":VERSION,
         "port":app.bound_port,"pid":os.getpid(),"atUtc":now(),
         "database":str(app.database.path),"aiEnabled":app.enable_ai,
         "qaStub":app.qa_ai_stub,"noWindowsStartup":True}
  with args.ready.open("x",encoding="utf-8") as file:
   json.dump(ready,file,indent=2)
  print(json.dumps({"status":"READY","port":app.bound_port,"pid":os.getpid()}),flush=True)
  srv.serve_forever(poll_interval=.25)
if __name__=="__main__":main()
