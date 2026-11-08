# coding: utf-8
"""First-party trusted offline SQLite CRUD engine for bounded desktop orders.

This module is authored by the factory's trusted owner, never by a model.
The GPU agent may plan/configure the application but cannot rewrite SQL or
the independent acceptance oracle. No network, plugins, shell or arbitrary
filesystem grants. SQLite parameters for all external fields, WAL for durable
transactions, restrictive input validation and formula-safe CSV.
"""
from __future__ import annotations
import csv
import io
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

VERSION="1"
STATUSES=("pending","paid","cancelled")
_REFERENCE=re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,39}\Z")
_CSV_DANGER=("=","+","-","@","\t","\r","\n")
_AMOUNT_MAX=999_999_999
_SCHEMA=(
    "CREATE TABLE IF NOT EXISTS orders ("
    "id INTEGER PRIMARY KEY AUTOINCREMENT,"
    "reference TEXT NOT NULL UNIQUE COLLATE NOCASE,"
    "customer TEXT NOT NULL,"
    "amount_cents INTEGER NOT NULL CHECK(amount_cents>=0 AND amount_cents<=999999999),"
    "status TEXT NOT NULL CHECK(status IN ('pending','paid','cancelled')),"
    "created_at TEXT NOT NULL,updated_at TEXT NOT NULL)"
)
_INDEX="CREATE INDEX IF NOT EXISTS idx_order_status ON orders(status)"

def _stamp():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def _is_valid_dbpath(path):
    if isinstance(path,bytes) or not isinstance(path,(str,os.PathLike)):
        raise ValueError("ORDERS_DB_PATH_TYPE")
    p=Path(path)
    if not p.is_absolute() or p.suffix.lower()!=".sqlite3":
        raise ValueError("ORDERS_DB_REQUIRES_ABSOLUTE_SQLITE3")
    if p.is_symlink() or (p.exists() and not p.is_file()):
        raise ValueError("ORDERS_DB_REJECT_SYMLINK_OR_DIRECTORY")
    if p.exists() and p.stat().st_size>100_000_000:
        raise ValueError("ORDERS_DB_TOO_LARGE")
    return p

def _ref(value):
    if type(value) is not str or not _REFERENCE.fullmatch(value):
        raise ValueError("ORDER_REFERENCE_REQUIRED_SAFE_ASCII")
    return value

def _customer(value):
    if type(value) is not str:
        raise ValueError("ORDER_CUSTOMER_TEXT_REQUIRED")
    if any(ord(c)<32 for c in value):
        raise ValueError("ORDER_CUSTOMER_CONTROL_DENIED")
    text=value.strip()
    if not 1<=len(text)<=100:
        raise ValueError("ORDER_CUSTOMER_LENGTH_OR_CONTROL")
    return text

def _amount(value):
    if type(value) is not int or not 0<=value<=_AMOUNT_MAX:
        raise ValueError("ORDER_AMOUNT_CENTS_INVALID")
    return value

def _status(value):
    if type(value) is not str or value not in STATUSES:
        raise ValueError("ORDER_STATUS_UNSUPPORTED")
    return value

def _id(value):
    if type(value) is not int or not 0<value<2**63:
        raise ValueError("ORDER_ID_INVALID")
    return value

def _csv_safe(value):
    text=str(value)
    if text.lstrip().startswith(_CSV_DANGER):
        return "'"+text
    return text

class Orders:
    """Bounded single-application storage. Connections are never global."""
    def __init__(self,path):
        self.path=_is_valid_dbpath(path)
        if self.path.parent.is_symlink():
            raise ValueError("ORDERS_DB_PARENT_SYMLINK_REJECTED")
        self.path.parent.mkdir(parents=True,exist_ok=True)
        # Do not follow a created link. A local-user process cannot protect
        # against malicious same-user TOCTOU, so never run as Administrator.
        _is_valid_dbpath(self.path)
        self.conn=sqlite3.connect(str(self.path),timeout=8,isolation_level=None)
        self.conn.row_factory=sqlite3.Row
        self.conn.execute("PRAGMA busy_timeout=8000")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute(_SCHEMA)
        self.conn.execute(_INDEX)
        self.conn.execute("PRAGMA user_version=1")
    def close(self):
        if self.conn is not None:
            self.conn.close()
            self.conn=None
    def __enter__(self):return self
    def __exit__(self,*_):self.close()
    def _assert_open(self):
        if self.conn is None:
            raise RuntimeError("ORDERS_STORAGE_ALREADY_CLOSED")
    @staticmethod
    def _mapping(row):
        return dict(row) if row is not None else None
    def create(self,reference,customer,amount_cents,status="pending"):
        self._assert_open()
        reference=_ref(reference);customer=_customer(customer)
        amount_cents=_amount(amount_cents);status=_status(status)
        timestamp=_stamp()
        try:
            with self.conn:
                cursor=self.conn.execute(
                    "INSERT INTO orders(reference,customer,amount_cents,status,created_at,updated_at)"
                    " VALUES (?,?,?,?,?,?)",
                    (reference,customer,amount_cents,status,timestamp,timestamp))
            return self.get(cursor.lastrowid)
        except sqlite3.IntegrityError as exc:
            raise ValueError("ORDER_REFERENCE_DUPLICATE_OR_INTEGRITY") from exc
    def get(self,order_id):
        self._assert_open()
        rows=self.conn.execute("SELECT * FROM orders WHERE id=?",(_id(order_id),)).fetchone()
        return self._mapping(rows)
    def update(self,order_id,reference,customer,amount_cents,status):
        self._assert_open();order_id=_id(order_id)
        reference=_ref(reference);customer=_customer(customer)
        amount_cents=_amount(amount_cents);status=_status(status)
        try:
            with self.conn:
                cur=self.conn.execute(
                    "UPDATE orders SET reference=?,customer=?,amount_cents=?,status=?,updated_at=?"
                    " WHERE id=?",
                    (reference,customer,amount_cents,status,_stamp(),order_id))
            if cur.rowcount!=1:
                raise KeyError("ORDER_NOT_FOUND")
            return self.get(order_id)
        except sqlite3.IntegrityError as exc:
            raise ValueError("ORDER_REFERENCE_DUPLICATE_OR_INTEGRITY") from exc
    def delete(self,order_id):
        self._assert_open()
        with self.conn:
            cur=self.conn.execute("DELETE FROM orders WHERE id=?",(_id(order_id),))
        return cur.rowcount==1
    def list(self,query="",status=None,limit=500):
        self._assert_open()
        if type(query) is not str or len(query)>100 or "\x00" in query:
            raise ValueError("ORDER_SEARCH_QUERY_INVALID")
        if status is not None:_status(status)
        if type(limit) is not int or not 1<=limit<=5000:
            raise ValueError("ORDER_LIST_LIMIT_INVALID")
        sql="SELECT * FROM orders WHERE 1=1"
        params=[]
        if query:
            # Literal substrings: escaping LIKE specials is essential.
            needle=query.replace("\\","\\\\").replace("%","\\%").replace("_","\\_")
            sql+=" AND (reference LIKE ? ESCAPE '\\' OR customer LIKE ? ESCAPE '\\')"
            params.extend(("%"+needle+"%","%"+needle+"%"))
        if status is not None:
            sql+=" AND status=?"
            params.append(status)
        sql+=" ORDER BY id DESC LIMIT ?"
        params.append(limit)
        return [dict(row) for row in self.conn.execute(sql,params).fetchall()]
    def count(self):
        self._assert_open()
        return int(self.conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0])
    def export_csv(self,query="",status=None):
        """Portable UTF-8 CSV using formula mitigation for spreadsheets."""
        rows=self.list(query,status,limit=5000)
        buffer=io.StringIO(newline="")
        writer=csv.writer(buffer,lineterminator="\r\n")
        writer.writerow(("id","reference","customer","amount_cents","status","created_at","updated_at"))
        for row in rows:
            writer.writerow([_csv_safe(row[col]) for col in
                ("id","reference","customer","amount_cents","status","created_at","updated_at")])
        return buffer.getvalue().encode("utf-8-sig")
    def backup(self,destination):
        """Snapshot while database may be in WAL mode; no raw SQLite copy."""
        self._assert_open()
        target=Path(destination)
        if (not target.is_absolute() or target.suffix.lower()!=".sqlite3" or
            target.exists() or target.is_symlink() or target.resolve()==self.path.resolve()):
            raise ValueError("ORDER_BACKUP_REQUIRES_NEW_ABSOLUTE_SQLITE3")
        target.parent.mkdir(parents=True,exist_ok=True)
        copy=sqlite3.connect(str(target))
        try:
            self.conn.backup(copy)
            quick=copy.execute("PRAGMA quick_check").fetchone()[0]
            if quick!="ok":
                raise RuntimeError("ORDER_BACKUP_INTEGRITY_FAILED")
        finally:
            copy.close()
        return target
    def integrity(self):
        self._assert_open()
        return self.conn.execute("PRAGMA integrity_check").fetchone()[0]=="ok"

def user_database(app_id):
    if not isinstance(app_id,str) or not re.fullmatch(r"AFD-[a-f0-9]{16}",app_id):
        raise ValueError("APP_ID_NOT_FIRST_PARTY")
    base=os.environ.get("LOCALAPPDATA")
    if not base:raise RuntimeError("LOCALAPPDATA_NOT_AVAILABLE")
    return Path(base)/"AUTOFABRICADOR"/"apps"/app_id/"orders.sqlite3"
