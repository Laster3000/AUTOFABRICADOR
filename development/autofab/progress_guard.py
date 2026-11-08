"""Generic failure-repeat guard adapted from MMC7 Codex progress-guard strategy.

No MMC7 imports, no assumption that a compiler error is a model-code error.
Only deterministic, original, locally recorded failed candidate evidence counts.
"""
from __future__ import annotations
import hashlib
import io
import json
from pathlib import Path
import tokenize

from .storage import load, sha_bytes

def semantic_source(content):
    if not isinstance(content,str):raise ValueError("SOURCE_NOT_TEXT")
    # Whitespace and comments are trivia, whereas literals, numbers, identifiers
    # and operator tokens must stay in the semantic fingerprint.
    try:
        tokens=list(tokenize.generate_tokens(io.StringIO(content).readline))
        # Python indentation and statement boundaries are meaningful tokens.
        relevant=[(t.type,"" if t.type in (tokenize.INDENT,tokenize.DEDENT,tokenize.NEWLINE) else t.string)
                  for t in tokens
                  if t.type not in (tokenize.ENCODING,tokenize.COMMENT,
                                    tokenize.NL,tokenize.ENDMARKER)]
        return hashlib.sha256(json.dumps(relevant,separators=(",",":"),ensure_ascii=False).encode("utf-8")).hexdigest()
    except (tokenize.TokenError,IndentationError,UnicodeError):
        # Conservatively use exact bytes for malformed sources.
        return sha_bytes(content.encode("utf-8"))

def candidate_fingerprint(payload):
    sources=payload.get("files",{}) if isinstance(payload,dict) else {}
    if not isinstance(sources,dict):return None
    if not sources:return None
    try:
        items=[(name,semantic_source(text)) for name,text in sorted(sources.items())]
    except (ValueError,TypeError):
        return None
    return sha_bytes(json.dumps(items,separators=(",",":"),ensure_ascii=False).encode("utf-8"))

def repeated_failed_candidate(job, new_payload):
    """Return concrete prior deterministic failure receipt or None."""
    job=Path(job)
    current=candidate_fingerprint(new_payload)
    if current is None:return None
    for old_model in sorted(job.glob("attempt-*/model.json")):
        attempt=old_model.parent
        test=attempt/"test.json"
        if not test.is_file():continue
        previous=load(test)
        # Exclude UNKNOWN, infrastructure problems, non-executed receipt-less
        # responses. Only explicit test/static failures with real receipts count.
        explicit=previous.get("exitCode")
        if not isinstance(explicit,int) or explicit==0:continue
        if previous.get("reason") not in ("STATIC_VALIDATION","STATIC_VALIDATION_ONLY") and not previous.get("testCount",0):
            continue
        old_payload=load(old_model).get("payload")
        if candidate_fingerprint(old_payload)==current:
            return {"attempt":attempt.name,"fingerprint":current,
                    "testReceipt":str(test),"errorFamily":previous.get("reason","UNIT_TEST_FAILURE"),
                    "exitCode":explicit}
    return None
