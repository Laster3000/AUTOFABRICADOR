# coding: utf-8
"""Bounded user-session autologon runner for the ORIGINAL AUTOFABRICADOR.

Not a Windows SCM service. Uses original service_worker/supervisor, no new
job engine. Original stale lease/journal is reconciled before any new worker.
Never replays SUCCEEDED or UNKNOWN. Designed for Task Scheduler Interactive
LogonType so Windows Sandbox GUI remains in user's own session.
"""
from __future__ import annotations
from . import engine, service_worker, supervisor
from .storage import utc

def inspect(root):
    """Read-only original source of truth, no process effects."""
    root=engine.init(root)
    prior=supervisor.status(root)
    return {"schema":1,"atUtc":utc(),
            "status":prior["status"],
            "control":prior["control"]["command"],
            "pendingQueue":prior["pendingQueue"],
            "lease":prior["lease"],
            "canBoot":prior["status"] in ("STOPPED","UNKNOWN_LEASE_STALE_RECONCILE"),
            "owner":"autofab.supervisor original",
            "noWindowsService":True,
            "noBlindReplay":True}

def boot(root):
    """Run original worker in foreground until native STOP; task stays RUNNING."""
    root=engine.init(root)
    before=supervisor.status(root)
    if before["status"]=="RUNNING":
        return {"status":"ALREADY_RUNNING_ORIGINAL_NO_DUPLICATE",
                "lease":before["lease"]}
    if before["status"]=="UNKNOWN_LEASE_STALE_RECONCILE":
        reconciled=supervisor.reconcile_stale(root)
        if reconciled["status"]!="STOPPED_RECONCILED_NO_NEW_MODEL_CALLS":
            raise RuntimeError("AUTORUN_ORIGINAL_STALE_LEASE_NOT_RECONCILED")
        before=supervisor.status(root)
    if before["status"]!="STOPPED":
        raise RuntimeError("AUTORUN_ORIGINAL_SUPERVISOR_UNSAFE:"+before["status"])
    if before["pendingQueue"]!=0:
        raise RuntimeError("AUTORUN_PENDING_ORIGINAL_QUEUE_REQUIRES_OWNER_RECONCILIATION")
    if before["control"]["command"]!="STOP":
        raise RuntimeError("AUTORUN_ORIGINAL_CONTROL_NOT_STOP")
    return service_worker.begin(root)
