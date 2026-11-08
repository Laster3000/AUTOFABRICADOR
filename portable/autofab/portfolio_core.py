# coding: utf-8
"""Original first-party schema-controlled persistent engine, three domains.

No external processes/network, no model-generated SQL/Host code, no plugins.
Input schema is exact local first-party profile and all column names originate
from portfolio_specs.PROFILES, never from untrusted file or AI output.
"""
from __future__ import annotations
import csv
import io
import os
import re
import sqlite3
from pathlib import Path
from datetime import date,datetime
if __package__:
 from .portfolio_specs import PROFILES
else:
 from portfolio_specs import PROFILES

_NONNEG=999_999_999
_TYPES={"text":"TEXT NOT NULL","nonnegative":"INTEGER NOT NULL",
        "positive":"INTEGER NOT NULL","date":"TEXT NOT NULL",
        "priority":"TEXT NOT NULL","bool":"INTEGER NOT NULL",
        "category":"TEXT NOT NULL"}
_CSV_DANGER=("=","+","-","@","\t","\r","\n")
def _validate_db(path):
 p=Path(path)
 if (not p.is_absolute() or p.suffix.lower()!=".sqlite3"
     or p.is_symlink() or (p.exists() and not p.is_file())
     or p.parent.is_symlink()):
  raise ValueError("PORTFOLIO_SQLITE_PATH_UNTRUSTED")
 if p.exists() and p.stat().st_size>100000000:
  raise ValueError("PORTFOLIO_DATABASE_EXCEEDS_TRUSTED_BOUND")
 return p
def _id(value):
 if type(value) is not int or value<1 or value>=2**63:
  raise ValueError("PORTFOLIO_ROW_ID_INVALID")
 return value
def _value(field,kind,value):
 if kind=="text":
  if (type(value) is not str or not 1<=len(value.strip())<=100 or
      any(ord(c)<32 for c in value)):
   raise ValueError("PORTFOLIO_TEXT_INVALID:"+field)
  text=value.strip()
  if field in ("sku","code") and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,39}",text):
   raise ValueError("PORTFOLIO_IDENTIFIER_INVALID:"+field)
  return text
 if kind in ("nonnegative","positive"):
  if type(value) is not int or value< int(kind=="positive") or value>_NONNEG:
   raise ValueError("PORTFOLIO_INT_BOUNDS_INVALID:"+field)
  return value
 if kind=="bool":
  if type(value) is not int or value not in (0,1):
   raise ValueError("PORTFOLIO_BOOLEAN_0_OR_1_REQUIRED")
  return value
 if kind=="date":
  if type(value) is not str or not re.fullmatch(r"\d{4}-\d{2}-\d{2}",value):
   raise ValueError("PORTFOLIO_DATE_ISO_INVALID")
  try:date.fromisoformat(value)
  except ValueError as e:raise ValueError("PORTFOLIO_DATE_NOT_REAL") from e
  return value
 if kind=="priority":
  if type(value) is not str or value not in ("low","medium","high"):
   raise ValueError("PORTFOLIO_PRIORITY_INVALID")
  return value
 if kind=="category":
  if type(value) is not str or value not in ("office","travel","other"):
   raise ValueError("PORTFOLIO_EXPENSE_CATEGORY_INVALID")
  return value
 raise ValueError("PORTFOLIO_UNTRUSTED_FIELD_KIND")

def _csv_safe(value):
 s=str(value)
 return "'"+s if s.lstrip().startswith(_CSV_DANGER) else s

def user_database(appid):
 if type(appid) is not str or not re.fullmatch(r"AFD-[a-f0-9]{16}",appid):
  raise ValueError("PORTFOLIO_APP_ID_INVALID")
 base=os.environ.get("LOCALAPPDATA")
 if not base:raise RuntimeError("LOCALAPPDATA_REQUIRED")
 return Path(base)/"AUTOFABRICADOR"/"apps"/appid/"records.sqlite3"

class Portfolio:
 def __init__(self,profile,path):
  if profile not in PROFILES:raise ValueError("PORTFOLIO_UNSUPPORTED_APP_PROFILE")
  self.profile=profile
  self.fields=tuple(PROFILES[profile]["fields"])
  self.path=_validate_db(path)
  self.path.parent.mkdir(parents=True,exist_ok=True)
  _validate_db(self.path)
  self.db=sqlite3.connect(str(self.path),timeout=8,isolation_level=None)
  self.db.row_factory=sqlite3.Row
  self.db.execute("PRAGMA foreign_keys=ON")
  self.db.execute("PRAGMA journal_mode=WAL")
  first=self.fields[0][0]
  declaration=["id INTEGER PRIMARY KEY AUTOINCREMENT"]
  for name,kind in self.fields:
   declaration.append(name+" "+_TYPES[kind]+(" UNIQUE COLLATE NOCASE" if name==first else ""))
  declaration.append("created_at TEXT NOT NULL")
  declaration.append("updated_at TEXT NOT NULL")
  self.db.execute("CREATE TABLE IF NOT EXISTS records ("+",".join(declaration)+")")
  self.db.execute("PRAGMA user_version=1")
 def __enter__(self):return self
 def __exit__(self,*exc):self.close()
 def close(self):
  if self.db is not None:
   self.db.close()
   self.db=None
 def _open(self):
  if self.db is None:raise RuntimeError("PORTFOLIO_STORAGE_ALREADY_CLOSED")
 def _params(self,record):
  if not isinstance(record,dict) or set(record)!={n for n,t in self.fields}:
   raise ValueError("PORTFOLIO_FROZEN_FIELDS_REQUIRED_EXACTLY")
  return [_value(n,t,record[n]) for n,t in self.fields]
 def _timestamp(self):
  return datetime.utcnow().isoformat(timespec="seconds")+"Z"
 def get(self,ident):
  self._open()
  row=self.db.execute("SELECT * FROM records WHERE id=?",(_id(ident),)).fetchone()
  return dict(row) if row else None
 def create(self,record):
  self._open()
  values=self._params(record)
  names=[n for n,t in self.fields]
  created=self._timestamp()
  try:
   with self.db:
    cur=self.db.execute(
      "INSERT INTO records ("+",".join(names)+",created_at,updated_at) VALUES ("+
      ",".join("?" for _ in range(len(values)+2))+")",
      values+[created,created])
   return self.get(cur.lastrowid)
  except sqlite3.IntegrityError as e:raise ValueError("PORTFOLIO_DUPLICATE_IDENTIFIER") from e
 def update(self,ident,record):
  self._open()
  ident=_id(ident);values=self._params(record)
  names=[n for n,t in self.fields]
  try:
   with self.db:
    cur=self.db.execute(
     "UPDATE records SET "+",".join(n+"=?" for n in names)+
     ",updated_at=? WHERE id=?",values+[self._timestamp(),ident])
   if cur.rowcount!=1:raise KeyError("PORTFOLIO_ROW_NOT_FOUND")
   return self.get(ident)
  except sqlite3.IntegrityError as e:raise ValueError("PORTFOLIO_DUPLICATE_IDENTIFIER") from e
 def delete(self,ident):
  self._open()
  with self.db:
   c=self.db.execute("DELETE FROM records WHERE id=?",(_id(ident),))
  return c.rowcount==1
 def count(self):
  self._open()
  return int(self.db.execute("SELECT COUNT(*) FROM records").fetchone()[0])
 def list(self,query="",limit=500):
  self._open()
  if type(query) is not str or "\x00" in query or len(query)>100:
   raise ValueError("PORTFOLIO_SEARCH_LIMIT")
  if type(limit) is not int or not 1<=limit<=5000:
   raise ValueError("PORTFOLIO_LIST_LIMIT")
  expression="SELECT * FROM records"
  params=[]
  if query:
   # Explicit LIKE wildcard escape: no model SQL or interpolated values.
   escaped=query.replace("\\","\\\\").replace("%","\\%").replace("_","\\_")
   cols=[n for n,t in self.fields if t=="text"]
   expression+=" WHERE "+" OR ".join(n+" LIKE ? ESCAPE '\\'" for n in cols)
   params=["%"+escaped+"%"]*len(cols)
  expression+=" ORDER BY id DESC LIMIT ?"
  return [dict(row) for row in self.db.execute(expression,params+[limit])]
 def metrics(self):
  self._open()
  rows=self.list(limit=5000)
  if self.profile=="inventory":
   return {"records":len(rows),
     "lowStock":sum(x["quantity"]<=x["minimum"] for x in rows),
     "totalCents":sum(x["quantity"]*x["unit_cents"] for x in rows)}
  if self.profile=="tasks":
   today=date.today().isoformat()
   return {"records":len(rows),
     "overdueOpen":sum(x["due_date"]<today and not x["completed"] for x in rows),
     "completed":sum(x["completed"] for x in rows)}
  months={}
  groups={}
  for x in rows:
   month=x["booking_date"][:7]
   months[month]=months.get(month,0)+x["amount_cents"]
   groups[x["category"]]=groups.get(x["category"],0)+x["amount_cents"]
  return {"records":len(rows),"totalCents":sum(x["amount_cents"] for x in rows),
          "monthlyTotals":months,"categoryTotals":groups}
 def export_csv(self,query=""):
  rows=self.list(query,limit=5000)
  out=io.StringIO(newline="")
  names=("id",)+tuple(n for n,t in self.fields)+("created_at","updated_at")
  writer=csv.writer(out,lineterminator="\r\n")
  writer.writerow(names)
  for row in rows:writer.writerow([_csv_safe(row[n]) for n in names])
  return out.getvalue().encode("utf-8-sig")
 def integrity(self):
  self._open()
  return self.db.execute("PRAGMA integrity_check").fetchone()[0]=="ok"
 def backup(self,path):
  self._open()
  dest=_validate_db(path)
  if dest.exists() or dest.resolve()==self.path.resolve():
   raise ValueError("PORTFOLIO_BACKUP_REQUIRES_NEW_DESTINATION")
  dest.parent.mkdir(parents=True,exist_ok=True)
  copy=sqlite3.connect(str(dest))
  try:
   self.db.backup(copy)
   if copy.execute("PRAGMA quick_check").fetchone()[0]!="ok":
    raise RuntimeError("PORTFOLIO_BACKUP_INTEGRITY_FAILURE")
  finally:copy.close()
  return dest
