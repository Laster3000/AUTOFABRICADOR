"""Durable SHA-reconciled files and chained, readback-verified journals."""
from __future__ import annotations
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import tempfile
import uuid

def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()

def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def sha_file(path: Path) -> str:
    return sha_bytes(Path(path).read_bytes())

def json_bytes(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")

def load(path: Path):
    return json.loads(Path(path).read_text("utf-8-sig"))

def write(path: Path, data: bytes, expected_sha: str | None = None, *, new: bool = False):
    """Atomic replacement, optional compare-and-swap and mandatory readback."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if new and path.exists():
        raise FileExistsError(f"ALREADY_EXISTS_NO_REPLAY:{path}")
    if expected_sha is not None:
        if not path.exists() or sha_file(path) != expected_sha:
            raise RuntimeError(f"CAS_MISMATCH:{path}")
    temp = path.with_name(path.name + ".NEW." + uuid.uuid4().hex)
    try:
        with temp.open("xb") as out:
            out.write(data)
            out.flush()
            os.fsync(out.fileno())
        if new and path.exists():
            raise FileExistsError(f"ALREADY_EXISTS_NO_REPLAY:{path}")
        if expected_sha is not None and sha_file(path) != expected_sha:
            raise RuntimeError(f"CAS_CHANGED_DURING_WRITE:{path}")
        os.replace(temp, path)
        if path.read_bytes() != data:
            raise RuntimeError(f"READBACK_FAILED:{path}")
    finally:
        if temp.exists():
            temp.unlink()

def write_json(path: Path, value, expected_sha: str | None = None, *, new: bool = False):
    write(path, json_bytes(value), expected_sha, new=new)

def transition(path: Path, value, history: Path):
    """Preimage retained by SHA. Prevent overwrite on unexpected drift."""
    if path.exists():
        old = path.read_bytes()
        previous = sha_bytes(old)
        image = history / f"{path.stem}-{previous}.json"
        if not image.exists():
            write(image, old, new=True)
        write_json(path, value, expected_sha=previous)
    else:
        write_json(path, value, new=True)
    return sha_file(path)

def event(journal: Path, operation: str, detail: dict):
    """Append one record with previous-event hash and an explicit event checksum."""
    journal = Path(journal)
    journal.parent.mkdir(parents=True, exist_ok=True)
    previous = None
    if journal.exists() and journal.stat().st_size:
        lines = journal.read_bytes().splitlines()
        last = json.loads(lines[-1])
        previous = last["eventSha"]
        if previous != sha_bytes(json_bytes({k:v for k,v in last.items() if k != "eventSha"})):
            raise RuntimeError("JOURNAL_LAST_EVENT_CORRUPT")
    row = {"atUtc":utc(), "operation":operation, "detail":detail, "previousEventSha":previous}
    row["eventSha"] = sha_bytes(json_bytes(row))
    with journal.open("ab") as out:
        out.write((json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8"))
        out.flush()
        os.fsync(out.fileno())
    if not journal.read_bytes().splitlines()[-1].endswith(b"}"):
        raise RuntimeError("JOURNAL_APPEND_READBACK_FAILED")
    return row["eventSha"]

def verify_journal(journal: Path):
    previous = None
    total = 0
    for line in Path(journal).read_bytes().splitlines():
        x = json.loads(line)
        actual = sha_bytes(json_bytes({k:v for k,v in x.items() if k != "eventSha"}))
        if x.get("eventSha") != actual or x.get("previousEventSha") != previous:
            raise RuntimeError(f"BROKEN_JOURNAL_CHAIN_AT:{total}")
        previous = actual
        total += 1
    return {"events":total,"lastEventSha":previous}

def validate_job_id(value: str):
    if not isinstance(value, str) or not value.startswith("AF-") or len(value) > 48 or not all(c.isascii() and (c.isalnum() or c in "-_") for c in value):
        raise ValueError("INVALID_JOB_ID")
    return value

def safe_source(work: Path, name: str, extensions=(".py",)):
    """Forbid escaping workspaces, link traversal, foreign drives, special files."""
    if not isinstance(name, str) or len(name) > 160 or "\\" in name or ":" in name or "\x00" in name:
        raise ValueError("INVALID_SOURCE_PATH")
    # PurePosixPath normalizes away empty and '.' members; check raw input
    # before normalizing. Windows device basenames are forbidden regardless
    # of extension or case. These source names reach a local Host filesystem.
    raw=name.split("/")
    reserved={"con","prn","aux","nul"}|{f"com{i}" for i in range(1,10)}|{f"lpt{i}" for i in range(1,10)}
    if (not name or name.startswith("/") or len(raw)>6 or
        any(not part or part in (".","..") or part.endswith((".", " ")) or
            part.split(".")[0].casefold() in reserved for part in raw)):
        raise ValueError("SOURCE_PATH_ESCAPE_OR_WINDOWS_DEVICE")
    pure = __import__("pathlib").PurePosixPath(name)
    if pure.is_absolute() or not pure.parts or len(pure.parts) > 6 or any(p in ("", "..", ".") or p.startswith(".") for p in pure.parts):
        raise ValueError("SOURCE_PATH_ESCAPE")
    if pure.suffix not in extensions or any(p.lower() in ("__pycache__", "site-packages", ".git") for p in pure.parts):
        raise ValueError("SOURCE_EXTENSION_NOT_ALLOWED")
    work = Path(work).resolve()
    target = work.joinpath(*pure.parts)
    if any(p.is_symlink() for p in (target, *target.parents)):
        raise ValueError("SOURCE_SYMLINK")
    if not target.resolve().is_relative_to(work):
        raise ValueError("SOURCE_OUTSIDE_WORKSPACE")
    return target

def atomic_snapshot(work: Path):
    """Create manifest for all regular files, with no symlinks."""
    manifest = {}
    for path in sorted(work.rglob("*")):
        if path.is_symlink():
            raise ValueError("SYMLINK_IN_WORKSPACE")
        if path.is_file():
            name = path.relative_to(work).as_posix()
            manifest[name] = sha_file(path)
    return manifest
