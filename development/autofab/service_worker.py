# coding: utf-8
"""Windows ServiceBase child adapter to ORIGINAL AUTOFABRICADOR supervisor.

No new factory, no queue replay, no privileged Host install. The sole owner
of worker state is autofab.supervisor.worker. It refuses stale leases, live
workers and non-STOP controls. Windows service parent calls original
supervisor-stop for cooperative shutdown at original safe boundaries.
"""
from __future__ import annotations
from pathlib import Path

from . import engine,supervisor
from .storage import load


def begin(root):
    root=engine.init(root)
    state=supervisor.status(root)
    if state["status"]!="STOPPED":
        raise RuntimeError("SERVICE_WORKER_ORIGINAL_SUPERVISOR_NOT_STOPPED")
    if state["control"]["command"]!="STOP":
        raise RuntimeError("SERVICE_WORKER_REQUIRES_ORIGINAL_STOP_PREIMAGE")
    if state["pendingQueue"]!=0:
        # Pending original tasks must be reconciled and deliberately released;
        # the service cannot silently consume inherited work on installation.
        raise RuntimeError("SERVICE_WORKER_EXISTING_PENDING_QUEUE_RECONCILE")
    previous=state["lease"]
    if previous and previous.get("status") not in ("STOPPED","STOPPED_RECONCILED"):
        raise RuntimeError("SERVICE_WORKER_ORIGINAL_LEASE_NOT_STOPPED")
    p=supervisor.directory(root)
    supervisor._control(p,"RUN")
    try:
        return supervisor.worker(root)
    finally:
        # If worker exits abruptly, STOP cannot justify replay of jobs.
        # The original lease/journal determines whether status is UNKNOWN.
        if load(p/"control.json")["command"]=="RUN":
            supervisor._control(p,"STOP")
