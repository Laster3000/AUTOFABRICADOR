"""Aider 0.86.2 proposal-only worker. Execute inside the project-owned aider venv.

The model may return an edit; its only effect is a receipt. Original seed code
must not change; no git, shell, web tools, auto edits, nor protected authority.
"""
from __future__ import annotations
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys
import time

def sha(raw):return hashlib.sha256(raw).hexdigest()
def main():
    request=Path(sys.argv[1]).resolve()
    cfg=json.loads(request.read_text("utf-8"))
    project=Path(cfg["projectRoot"]).resolve()
    if project.name.upper()!="AUTOFABRICADOR" or not request.is_relative_to(project/"work"):
        raise RuntimeError("AIDER_REQUEST_OUT_OF_FACTORY_SCOPE")
    target=Path(cfg["target"]).resolve()
    response=Path(cfg["response"]).resolve()
    if target.is_symlink() or not target.is_relative_to(request.parent):
        raise RuntimeError("AIDER_TARGET_ESCAPE")
    if not response.is_relative_to(request.parent) or response.exists():
        raise RuntimeError("AIDER_RESPONSE_PATH_NOT_NEW")
    if importlib.metadata.version("aider-chat")!="0.86.2":
        raise RuntimeError("AIDER_VERSION_NOT_PINNED")
    before=target.read_bytes()
    if sha(before)!=cfg["expectedSourceSha256"]:
        raise RuntimeError("AIDER_INPUT_SHA_DRIFT")
    if not isinstance(cfg["goal"],str) or not 10<len(cfg["goal"])<3000:
        raise RuntimeError("AIDER_GOAL_INVALID")
    # Complete API isolation: only local unauthenticated inference.
    for key in list(os.environ):
        if key.endswith(("_API_KEY","_ACCESS_TOKEN")):
            os.environ.pop(key,None)
    os.environ.update(OPENAI_API_BASE="http://127.0.0.1:11435/v1",
                      OPENAI_API_KEY="noncloud-local-key",AIDER_ANALYTICS="false",
                      DO_NOT_TRACK="1",HF_HUB_OFFLINE="1",
                      TRANSFORMERS_OFFLINE="1",LITELLM_LOCAL_MODEL_COST_MAP="True")
    from aider.models import Model
    from aider.io import InputOutput
    from aider.coders.wholefile_coder import WholeFileCoder
    class CaptureOnly(WholeFileCoder):
        def allowed_to_edit(self,path):
            return Path(self.abs_root_path(path)).resolve()==target
        def apply_edits(self,edits):
            self.captured_edits=list(edits)
        def run_shell_commands(self):
            return ""
    io=InputOutput(yes=True,dry_run=True,pretty=False,chat_history_file=None,input_history_file=None)
    model=Model("openai/af-qwen-coder-1.5b",weak_model=False,editor_model=False)
    model.weak_model=model
    model.editor_model=model
    model.extra_params={"api_base":"http://127.0.0.1:11435/v1","max_tokens":1000,"temperature":0.0,"timeout":85}
    model.info.update(max_input_tokens=9500,max_output_tokens=1200,
                      input_cost_per_token=0,output_cost_per_token=0)
    model.use_repo_map=False
    worker=CaptureOnly(main_model=model,io=io,fnames=[str(target)],
                       use_git=False,auto_commits=False,dirty_commits=False,
                       dry_run=True,auto_lint=False,auto_test=False,
                       map_tokens=0,stream=False,suggest_shell_commands=False,detect_urls=False)
    worker.max_reflections=0
    started=time.monotonic()
    result=worker.run(cfg["goal"],preproc=False) or ""
    edits=worker.get_edits()
    if sha(target.read_bytes())!=sha(before):
        raise RuntimeError("AIDER_UNEXPECTED_SOURCE_MUTATION")
    if len(edits)!=1:
        raise RuntimeError("AIDER_ONE_COMPLETE_PROPOSAL_REQUIRED")
    filename,_,lines=edits[0]
    if Path(worker.abs_root_path(filename)).resolve()!=target:
        raise RuntimeError("AIDER_EDIT_TARGET_MISMATCH")
    source="".join(lines)
    if not source or len(source.encode("utf-8"))>100000:
        raise RuntimeError("AIDER_BAD_SOURCE_SIZE")
    import ast
    ast.parse(source)
    record={
        "schema":1,"status":"PROPOSED_UNTESTED","tool":"aider",
        "editorVersion":"0.86.2","model":"af-qwen-coder-1.5b",
        "sourceUnchanged":True,"sourcePreimageSha256":sha(before),
        "proposedSha256":sha(source.encode("utf-8")),
        "proposedSource":source,
        "elapsedMs":int((time.monotonic()-started)*1000),
        "promptTokens":getattr(worker,"total_tokens_sent",None),
        "completionTokens":getattr(worker,"total_tokens_received",None),
        "finalResponseSha256":sha(result.encode("utf-8")),
        "authority":"SOURCE_PROPOSAL_ONLY_NO_APPLY_NO_SHELL"
    }
    raw=(json.dumps(record,ensure_ascii=False,sort_keys=True,indent=2)+"\n").encode()
    with response.open("xb") as f:f.write(raw);f.flush();os.fsync(f.fileno())
    if response.read_bytes()!=raw:raise RuntimeError("AIDER_RECEIPT_READBACK_FAILED")
    print(json.dumps({k:v for k,v in record.items() if k!="proposedSource"},ensure_ascii=False))
if __name__=="__main__":
    main()
