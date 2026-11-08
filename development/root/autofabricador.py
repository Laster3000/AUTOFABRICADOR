#!/usr/bin/env python3
"""Command line interface to reusable AUTOFABRICADOR (no third-party modules)."""
import argparse
import json
from pathlib import Path
import sys
sys.dont_write_bytecode=True  # Do not litter the project with disposable imports.

from autofab import VERSION
from autofab import gui_pipeline, portfolio_workflow, portfolio_installer, desktop_workflow, desktop_installer, autonomous_intake, reboot_audit, owner_proposals, owner_oracles, autorun, open_orders, engine, draft, local_runtime, operate, bootstrap, agents, housekeeping, aider_bridge, advisors, bootstrap_editors, source_editors, mission, multilang, supervisor, csharp_jobs, telemetry, bootstrap_languages, csharp_repair, bootstrap_extra, direct_agent, cancel_probe, webapps, vendor_capsule, ledger_project, repo_graph, repo_factory, repo_export, repo_archive, local_escalation, windows_sandbox, native_repo_bridge, native_cycle, factory_pipeline, intent_catalog, portable_delivery, service_rehearsal, service_worker, blackbox, self_audit, audit_inventory, repair_bridge, python_direct, python_general, python_general_repair, export_recovery
from autofab.package import build_bundle, verify_bundle
from autofab import reference_suite_r76
from autofab import family_router

ROOT = Path(__file__).resolve().parent

def print_json(data):
    print(json.dumps(data,ensure_ascii=True,sort_keys=True,indent=2))

def main():
    p=argparse.ArgumentParser(prog="autofabricador",description="Local AI software factory; model code requires independently verified WASI or Docker isolation.")
    p.add_argument("--root",type=Path,default=ROOT,help="Independent project root")
    sub=p.add_subparsers(dest="action",required=True)
    for name in ("init","doctor","list","metrics","capabilities","agents","editors","bootstrap","bootstrap-editors","bootstrap-languages","bootstrap-extra","serve-start","serve-status","serve-stop","bundle"):
        sub.add_parser(name)
    clean=sub.add_parser("housekeeping");clean.add_argument("--apply",action="store_true")
    native=sub.add_parser("run-aider");native.add_argument("jobid");native.add_argument("source_name");native.add_argument("seed_rel")
    src=sub.add_parser("run-source");src.add_argument("tool",choices=["codex","opencode"]);src.add_argument("jobid");src.add_argument("source_name");src.add_argument("seed_rel")
    rec=sub.add_parser("reconcile-source");rec.add_argument("jobid")
    mi=sub.add_parser("mission-create");mi.add_argument("jobid");mi.add_argument("editor",choices=["aider","codex","opencode"]);mi.add_argument("source_name");mi.add_argument("seed_rel");mi.add_argument("--reviewers",default="")
    for name in ("mission-run","mission-status","mission-stop","mission-resume","mission-reconcile"):
        one=sub.add_parser(name);one.add_argument("missionid")
    sub.add_parser("service-worker")
    sub.add_parser("autorun-inspect")
    sub.add_parser("autorun-worker")
    for name in ("supervisor-start","supervisor-stop","supervisor-status","supervisor-worker","supervisor-reconcile"):
        sub.add_parser(name)
    sr=sub.add_parser("supervisor-resume-task");sr.add_argument("queueid")
    sn=sub.add_parser("supervisor-requeue-vm-conflict");sn.add_argument("queueid")
    sn2=sub.add_parser("supervisor-requeue-log-collision");sn2.add_argument("queueid")
    sq=sub.add_parser("supervisor-queue");sq.add_argument("kind",choices=["selfcheck","mission","language","direct","repo","native","factory","gui","desktop","portfolio"]);sq.add_argument("--ref",default=None);sq.add_argument("--editor",default=None)
    cs=sub.add_parser("csharp-create");cs.add_argument("spec",type=Path)
    cr=sub.add_parser("csharp-run");cr.add_argument("jobid");cr.add_argument("tool",choices=["codex","opencode"])
    sub.add_parser("offline-vendor-inspect")
    sub.add_parser("offline-vendor-verify")
    for name in ("ledger-project-export","ledger-project-verify"):
        one=sub.add_parser(name);one.add_argument("jobid")
    for name in ("webapp-export","webapp-verify"):
        one=sub.add_parser(name);one.add_argument("jobid")
    sub.add_parser("cancel-probe-create")
    for n in ("cancel-probe-run","cancel-probe-stop","cancel-probe-status"):
        x=sub.add_parser(n);x.add_argument("jobid")
    sub.add_parser("sandbox-preflight")
    ss=sub.add_parser("sandbox-stage");ss.add_argument("zipfile",type=Path);ss.add_argument("owner",type=Path)
    sr48=sub.add_parser("service-guest-verify");sr48.add_argument("sandboxid")
    for n in ("sandbox-verify","sandbox-launch","sandbox-stop","sandbox-reconcile"):
        x=sub.add_parser(n);x.add_argument("jobid")
    rns=sub.add_parser("repo-native-stage");rns.add_argument("jobid")
    rnv=sub.add_parser("repo-native-verify");rnv.add_argument("jobid")
    nc=sub.add_parser("native-cycle-create");nc.add_argument("repoid")
    for n in ("native-cycle-run","native-cycle-status","native-cycle-stop","native-cycle-reconcile"):
        sub.add_parser(n).add_argument("cycleid")
    ri=sub.add_parser("repo-import");ri.add_argument("zipfile",type=Path);ri.add_argument("owner",type=Path)
    sub.add_parser("family-capabilities")
    fp=sub.add_parser("family-preview");fp.add_argument("request",type=Path)
    fsu=sub.add_parser("family-submit");fsu.add_argument("request",type=Path)
    fst=sub.add_parser("family-status");fst.add_argument("family");fst.add_argument("originalid")
    sub.add_parser("r76-suite-capabilities")
    sub.add_parser("r76-suite-verify")
    sub.add_parser("r76-suite-export")
    op=sub.add_parser("order-preview");op.add_argument("input",type=Path)
    osub=sub.add_parser("order-submit");osub.add_argument("input",type=Path);osub.add_argument("--provider",choices=["small","coder14b","cuda7b","cuda9b"],default="cuda7b");osub.add_argument("--acceptance-mode",choices=["wasi-browser","wasi-native"],default="wasi-browser")
    ost=sub.add_parser("order-status");ost.add_argument("orderid")
    ocp=sub.add_parser("contract-preview");ocp.add_argument("contract",type=Path)
    ocs=sub.add_parser("contract-submit");ocs.add_argument("contract",type=Path);ocs.add_argument("--provider",choices=["small","coder14b","cuda7b","cuda9b"],default="cuda7b");ocs.add_argument("--acceptance-mode",choices=["wasi-browser","wasi-native"],default="wasi-browser")
    oct=sub.add_parser("contract-status");oct.add_argument("contractid")
    agp=sub.add_parser("auto-goal-preview");agp.add_argument("goalfile",type=Path)
    ags=sub.add_parser("auto-goal-submit");ags.add_argument("goalfile",type=Path);ags.add_argument("--provider",choices=["small","coder14b","cuda7b","cuda9b"],default="cuda7b")
    agt=sub.add_parser("auto-goal-status");agt.add_argument("goalid")
    g=sub.add_parser("gui-preview");g.add_argument("spec",type=Path)
    g=sub.add_parser("gui-submit");g.add_argument("spec",type=Path)
    for n in ("gui-run","gui-status","gui-verify","gui-stop","gui-reconcile"):
        sub.add_parser(n).add_argument("guiid")
    dpre=sub.add_parser("desktop-preview");dpre.add_argument("goalfile",type=Path)
    ds=sub.add_parser("desktop-submit");ds.add_argument("goalfile",type=Path)
    dr=sub.add_parser("desktop-run");dr.add_argument("desktopid")
    st=sub.add_parser("desktop-status");st.add_argument("desktopid")
    di=sub.add_parser("desktop-install-verify");di.add_argument("appid")
    du=sub.add_parser("desktop-uninstall");du.add_argument("appid");du.add_argument("--confirm",action="store_true")
    pf=sub.add_parser("portfolio-preview");pf.add_argument("goalfile",type=Path)
    pf=sub.add_parser("portfolio-submit");pf.add_argument("goalfile",type=Path)
    pf=sub.add_parser("portfolio-run");pf.add_argument("portfolioid")
    pf=sub.add_parser("portfolio-status");pf.add_argument("portfolioid")
    pf=sub.add_parser("portfolio-install-verify");pf.add_argument("appid")
    pf=sub.add_parser("portfolio-uninstall");pf.add_argument("appid");pf.add_argument("--confirm",action="store_true")
    pp=sub.add_parser("proposal-preview");pp.add_argument("goalfile",type=Path)
    pd=sub.add_parser("proposal-draft");pd.add_argument("goalfile",type=Path)
    ps=sub.add_parser("proposal-status");ps.add_argument("proposalid")
    sub.add_parser("reboot-baseline")
    sub.add_parser("reboot-verify")
    fc=sub.add_parser("factory-create");fc.add_argument("spec",type=Path);fc.add_argument("--provider",choices=["small","coder14b","cuda7b","cuda9b"],default="small");fc.add_argument("--acceptance-mode",choices=["wasi-native","wasi-browser"],default="wasi-native")
    fs=sub.add_parser("factory-submit");fs.add_argument("spec",type=Path);fs.add_argument("--provider",choices=["small","coder14b","cuda7b","cuda9b"],default="small");fs.add_argument("--acceptance-mode",choices=["wasi-native","wasi-browser"],default="wasi-native")
    fd=sub.add_parser("factory-deliver");fd.add_argument("workflowid")
    fv=sub.add_parser("factory-deliver-verify");fv.add_argument("workflowid")
    for name in ("factory-request","factory-request-preview","factory-request-status"):
        sub.add_parser(name).add_argument("request",type=str)
    for n in ("factory-run","factory-status","factory-stop","factory-reconcile"):
        sub.add_parser(n).add_argument("workflowid")
    rc=sub.add_parser("repo-create");rc.add_argument("spec",type=Path)
    rr=sub.add_parser("repo-run");rr.add_argument("jobid");rr.add_argument("--max-tokens",type=int,default=2300);rr.add_argument("--max-attempts",type=int,default=3);rr.add_argument("--provider",choices=["small","coder14b","cuda7b","cuda9b"],default="small")
    for n in ("repo-status","repo-stop","repo-verify","repo-export","repo-export-verify"):
        x=sub.add_parser(n);x.add_argument("jobid")
    dr=sub.add_parser("direct-create");dr.add_argument("spec",type=Path)
    dn=sub.add_parser("direct-run");dn.add_argument("jobid");dn.add_argument("--max-tokens",type=int,default=900)
    for name in ("direct-stop","direct-status","direct-verify","direct-reconcile"):
        one=sub.add_parser(name);one.add_argument("jobid")
    ci=sub.add_parser("csharp-status");ci.add_argument("jobid")
    for name in ("csharp-accept-wasi","csharp-verify"):
        cli=sub.add_parser(name);cli.add_argument("jobid")
    cx=sub.add_parser("csharp-reconcile");cx.add_argument("jobid")
    cf=sub.add_parser("csharp-repair");cf.add_argument("jobid")
    cv=sub.add_parser("csharp-reconcile-refs");cv.add_argument("jobid")
    cu=sub.add_parser("csharp-repair-using");cu.add_argument("jobid")
    cc=sub.add_parser("csharp-repair-create");cc.add_argument("jobid")
    lg=sub.add_parser("language-create");lg.add_argument("spec",type=Path)
    lr=sub.add_parser("language-run");lr.add_argument("jobid");lr.add_argument("tool",choices=["codex","opencode"])
    for name in ("language-verify","language-status","language-stop","language-resume"):
        one=sub.add_parser(name);one.add_argument("jobid")
    advisor=sub.add_parser("advise");advisor.add_argument("tool",choices=["codex","opencode"]);advisor.add_argument("jobid")
    add=sub.add_parser("create");add.add_argument("spec",type=Path)
    for name in ("draft","run","status","verify","stop","resume"):
        one=sub.add_parser(name);one.add_argument("jobid")
    execute=sub.add_parser("run-queued");execute.add_argument("--limit",type=int,default=5)
    verify=sub.add_parser("verify-bundle");verify.add_argument("zipfile",type=Path)
    bbc=sub.add_parser("blackbox-create");bbc.add_argument("spec",type=Path)
    for name in ("blackbox-verify","blackbox-report"):
        x=sub.add_parser(name);x.add_argument("sessionid")
    st=sub.add_parser("audit-create");st.add_argument("spec",type=Path)
    for n in ("audit-run","audit-status","audit-stop","audit-verify"):
        t=sub.add_parser(n);t.add_argument("auditid")
    sub.add_parser("audit-inventory")
    repair=sub.add_parser("repair-create")
    repair.add_argument("sourcejob")
    repair.add_argument("--revision",default="v1",choices=["v1","v2"])
    for n in ("repair-run","repair-verify"):
        t=sub.add_parser(n);t.add_argument("repairid")
    python_job=sub.add_parser("python-create")
    python_job.add_argument("spec",type=Path)
    for name in ("python-run","python-stop","python-status","python-verify"):
        x=sub.add_parser(name);x.add_argument("jobid")
    pygen=sub.add_parser("pygen-create");pygen.add_argument("spec",type=Path)
    for n in ("pygen-run","pygen-stop","pygen-status","pygen-verify"):
        x=sub.add_parser(n);x.add_argument("jobid")
    resume=sub.add_parser("pygen-reconcile")
    resume.add_argument("jobid")
    resume.add_argument("--stop-receipt",type=Path,required=True)
    rnew=sub.add_parser("pygen-repair-create");rnew.add_argument("originaljob")
    for n in ("pygen-repair-run","pygen-repair-verify"):
        x=sub.add_parser(n);x.add_argument("repairid")
    for n in ("browser-close","browser-close-status"):
        x=sub.add_parser(n);x.add_argument("repoid")
    x=sub.add_parser("browser-close-verify");x.add_argument("closureid")
    args=p.parse_args()
    root=args.root.resolve()
    if args.action=="init":
        engine.init(root);print_json({"root":str(root),"version":VERSION,"initialized":True})
    elif args.action=="doctor":print_json(engine.doctor(root))
    elif args.action=="bootstrap":print_json(bootstrap.bootstrap(root))
    elif args.action=="bootstrap-editors":print_json(bootstrap_editors.bootstrap(root))
    elif args.action=="bootstrap-languages":print_json(bootstrap_languages.bootstrap(root))
    elif args.action=="bootstrap-extra":print_json(bootstrap_extra.bootstrap(root))
    elif args.action=="serve-start":print_json(local_runtime.start(root))
    elif args.action=="serve-status":print_json(local_runtime.server_info(root))
    elif args.action=="serve-stop":print_json(local_runtime.stop(root))
    elif args.action=="metrics":print_json(telemetry.combined(root))
    elif args.action=="agents":print_json(agents.discover(root))
    elif args.action=="editors":print_json(advisors.registry(root))
    elif args.action=="advise":print_json(advisors.advise(root,args.tool,args.jobid))
    elif args.action=="housekeeping":print_json(housekeeping.maintain(root,apply=args.apply))
    elif args.action=="capabilities":print_json(engine.capabilities())
    elif args.action=="create":print_json({"jobId":engine.create(root,args.spec)})
    elif args.action=="draft":print_json(draft.draft(root,args.jobid))
    elif args.action=="run":print_json(operate.run_job(root,args.jobid))
    elif args.action=="run-aider":print_json(aider_bridge.admit(root,args.jobid,args.source_name,args.seed_rel))
    elif args.action=="run-source":print_json(source_editors.run(root,args.tool,args.jobid,args.source_name,args.seed_rel))
    elif args.action=="reconcile-source":print_json(source_editors.reconcile_saved(root,args.jobid))
    elif args.action=="mission-create":print_json(mission.create(root,args.jobid,args.editor,args.source_name,args.seed_rel,[x for x in args.reviewers.split(',') if x]))
    elif args.action=="mission-run":print_json(mission.run(root,args.missionid))
    elif args.action=="mission-status":print_json(mission.summary(root,args.missionid))
    elif args.action=="mission-stop":print_json(mission.control(root,args.missionid,"STOP"))
    elif args.action=="mission-resume":print_json(mission.control(root,args.missionid,"RUN"))
    elif args.action=="mission-reconcile":print_json(mission.reconcile(root,args.missionid))
    elif args.action=="supervisor-start":print_json(supervisor.start(root))
    elif args.action=="supervisor-stop":print_json(supervisor.stop(root))
    elif args.action=="supervisor-status":print_json(supervisor.status(root))
    elif args.action=="supervisor-reconcile":print_json(supervisor.reconcile_stale(root))
    elif args.action=="supervisor-resume-task":print_json(supervisor.resume_task(root,args.queueid))
    elif args.action=="supervisor-requeue-vm-conflict":print_json(supervisor.requeue_vm_conflict(root,args.queueid))
    elif args.action=="supervisor-requeue-log-collision":print_json(supervisor.requeue_log_collision(root,args.queueid))
    elif args.action=="supervisor-worker":print_json(supervisor.worker(root))
    elif args.action=="service-worker":print_json(service_worker.begin(root))
    elif args.action=="autorun-inspect":print_json(autorun.inspect(root))
    elif args.action=="autorun-worker":print_json(autorun.boot(root))
    elif args.action=="supervisor-queue":print_json(supervisor.enqueue(root,args.kind,args.ref,args.editor))
    elif args.action=="offline-vendor-inspect":print_json(vendor_capsule.preflight(root))
    elif args.action=="offline-vendor-verify":print_json(vendor_capsule.verify(root,physical=True))
    elif args.action=="ledger-project-export":print_json(ledger_project.export(root,args.jobid))
    elif args.action=="ledger-project-verify":print_json(ledger_project.verify(root,args.jobid))
    elif args.action=="webapp-export":print_json(webapps.export(root,args.jobid))
    elif args.action=="webapp-verify":print_json(webapps.verify(root,args.jobid))
    elif args.action=="cancel-probe-create":print_json(cancel_probe.create(root))
    elif args.action=="cancel-probe-run":print_json(cancel_probe.run(root,args.jobid))
    elif args.action=="cancel-probe-stop":print_json(cancel_probe.stop(root,args.jobid))
    elif args.action=="cancel-probe-status":print_json(cancel_probe.status(root,args.jobid))
    elif args.action=="sandbox-preflight":print_json(windows_sandbox.preflight(root))
    elif args.action=="sandbox-stage":print_json(windows_sandbox.stage(root,args.zipfile,args.owner))
    elif args.action=="sandbox-verify":print_json(windows_sandbox.verify(root,args.jobid))
    elif args.action=="sandbox-launch":print_json(windows_sandbox.launch(root,args.jobid))
    elif args.action=="sandbox-stop":print_json(windows_sandbox.stop(root,args.jobid))
    elif args.action=="sandbox-reconcile":print_json(windows_sandbox.reconcile(root,args.jobid))
    elif args.action=="service-guest-verify":print_json(service_rehearsal.verify(root,args.sandboxid))
    elif args.action=="repo-native-stage":print_json(native_repo_bridge.stage_repo(root,args.jobid))
    elif args.action=="repo-native-verify":print_json(native_repo_bridge.verify_native(root,args.jobid))
    elif args.action=="native-cycle-create":print_json(native_cycle.create(root,args.repoid))
    elif args.action=="native-cycle-run":print_json(native_cycle.run(root,args.cycleid))
    elif args.action=="native-cycle-status":print_json(native_cycle.status(root,args.cycleid))
    elif args.action=="native-cycle-stop":print_json(native_cycle.stop(root,args.cycleid))
    elif args.action=="native-cycle-reconcile":print_json(native_cycle.reconcile(root,args.cycleid))
    elif args.action=="repo-import":print_json(repo_archive.create(root,args.zipfile,args.owner))
    elif args.action=="family-capabilities":print_json(family_router.capabilities())
    elif args.action=="family-preview":print_json(family_router.preview(root,args.request))
    elif args.action=="family-submit":print_json(family_router.submit(root,args.request))
    elif args.action=="family-status":print_json(family_router.status(root,args.family,args.originalid))
    elif args.action=="r76-suite-capabilities":print_json(reference_suite_r76.capabilities())
    elif args.action=="r76-suite-verify":print_json(reference_suite_r76.verify(root))
    elif args.action=="r76-suite-export":print_json(reference_suite_r76.export(root))
    elif args.action=="order-preview":print_json(open_orders.preview(root,args.input))
    elif args.action=="order-submit":print_json(open_orders.submit(root,args.input,provider=args.provider,acceptance_mode=args.acceptance_mode))
    elif args.action=="order-status":print_json(open_orders.status(root,args.orderid))
    elif args.action=="contract-preview":print_json(owner_oracles.preview(root,args.contract))
    elif args.action=="contract-submit":print_json(owner_oracles.submit(root,args.contract,provider=args.provider,acceptance_mode=args.acceptance_mode))
    elif args.action=="contract-status":print_json(owner_oracles.status(root,args.contractid))
    elif args.action=="auto-goal-preview":print_json(autonomous_intake.preview(root,args.goalfile))
    elif args.action=="auto-goal-submit":print_json(autonomous_intake.submit(root,args.goalfile,provider=args.provider))
    elif args.action=="auto-goal-status":print_json(autonomous_intake.status(root,args.goalid))
    elif args.action=="gui-preview":print_json(gui_pipeline.preview(root,args.spec))
    elif args.action=="gui-submit":
        answer=gui_pipeline.create(root,args.spec)
        if answer.get("status")=="PENDING":
            answer["originalSupervisorQueue"]=supervisor.enqueue(root,"gui",answer["jobId"])
        print_json(answer)
    elif args.action=="gui-run":print_json(gui_pipeline.run(root,args.guiid))
    elif args.action=="gui-status":print_json(gui_pipeline.status(root,args.guiid))
    elif args.action=="gui-verify":print_json(gui_pipeline.verify(root,args.guiid))
    elif args.action=="gui-stop":print_json(gui_pipeline.control(root,args.guiid,"STOP"))
    elif args.action=="gui-reconcile":print_json(gui_pipeline.reconcile(root,args.guiid))
    elif args.action=="desktop-preview":print_json(desktop_workflow.preview(root,args.goalfile))
    elif args.action=="desktop-submit":print_json(desktop_workflow.submit(root,args.goalfile))
    elif args.action=="desktop-run":print_json(desktop_workflow.run(root,args.desktopid))
    elif args.action=="desktop-status":print_json(desktop_workflow.status(root,args.desktopid))
    elif args.action=="desktop-install-verify":print_json(desktop_installer.verify(root,args.appid))
    elif args.action=="desktop-uninstall":print_json(desktop_installer.uninstall(root,args.appid,confirm=args.confirm))
    elif args.action=="portfolio-preview":print_json(portfolio_workflow.preview(root,args.goalfile))
    elif args.action=="portfolio-submit":print_json(portfolio_workflow.submit(root,args.goalfile))
    elif args.action=="portfolio-run":print_json(portfolio_workflow.run(root,args.portfolioid))
    elif args.action=="portfolio-status":print_json(portfolio_workflow.status(root,args.portfolioid))
    elif args.action=="portfolio-install-verify":print_json(portfolio_installer.verify(root,args.appid))
    elif args.action=="portfolio-uninstall":print_json(portfolio_installer.uninstall(root,args.appid,confirm=args.confirm))
    elif args.action=="proposal-preview":print_json(owner_proposals.preview(root,args.goalfile))
    elif args.action=="proposal-draft":print_json(owner_proposals.propose(root,args.goalfile))
    elif args.action=="proposal-status":print_json(owner_proposals.status(root,args.proposalid))
    elif args.action=="reboot-baseline":print_json(reboot_audit.establish(root))
    elif args.action=="reboot-verify":print_json(reboot_audit.verify(root))
    elif args.action=="factory-create":print_json(factory_pipeline.create(root,args.spec,provider=args.provider,acceptance_mode=args.acceptance_mode))
    elif args.action=="factory-submit":print_json(factory_pipeline.submit(root,args.spec,provider=args.provider,acceptance_mode=args.acceptance_mode))
    elif args.action=="factory-deliver":print_json(portable_delivery.deliver(root,args.workflowid))
    elif args.action=="factory-deliver-verify":print_json(portable_delivery.verify(root,args.workflowid))
    elif args.action=="factory-request":print_json(intent_catalog.request(root,args.request))
    elif args.action=="factory-request-preview":print_json(intent_catalog.preview(args.request))
    elif args.action=="factory-request-status":print_json(intent_catalog.status(root,args.request))
    elif args.action=="factory-run":print_json(factory_pipeline.run(root,args.workflowid))
    elif args.action=="factory-status":print_json(factory_pipeline.status(root,args.workflowid))
    elif args.action=="factory-stop":print_json(factory_pipeline.stop(root,args.workflowid))
    elif args.action=="factory-reconcile":print_json(factory_pipeline.reconcile(root,args.workflowid))
    elif args.action=="repo-create":print_json(repo_factory.create(root,args.spec))
    elif args.action=="repo-run":print_json(repo_factory.run(root,args.jobid,max_tokens=args.max_tokens,max_attempts=args.max_attempts,provider=args.provider))
    elif args.action=="repo-status":print_json(repo_factory.status(root,args.jobid))
    elif args.action=="repo-stop":print_json(repo_factory.stop(root,args.jobid))
    elif args.action=="repo-verify":print_json(repo_factory.verify(root,args.jobid))
    elif args.action=="repo-export":print_json(repo_export.export(root,args.jobid))
    elif args.action=="repo-export-verify":print_json(repo_export.verify(root,args.jobid))
    elif args.action=="direct-create":print_json(direct_agent.create(root,args.spec))
    elif args.action=="direct-run":print_json(direct_agent.run(root,args.jobid,max_tokens=args.max_tokens))
    elif args.action=="direct-stop":print_json(direct_agent.control(root,args.jobid,"STOP"))
    elif args.action=="direct-status":print_json(direct_agent.status(root,args.jobid))
    elif args.action=="direct-verify":print_json(direct_agent.verify(root,args.jobid))
    elif args.action=="direct-reconcile":print_json(direct_agent.reconcile_saved(root,args.jobid))
    elif args.action=="csharp-create":print_json(csharp_jobs.create(root,args.spec))
    elif args.action=="csharp-run":print_json(csharp_jobs.run(root,args.jobid,args.tool))
    elif args.action=="csharp-status":print_json(csharp_jobs.status(root,args.jobid))
    elif args.action=="csharp-accept-wasi":print_json(csharp_jobs.admit_wasi(root,args.jobid))
    elif args.action=="csharp-verify":print_json(csharp_jobs.verify(root,args.jobid))
    elif args.action=="csharp-reconcile":print_json(csharp_jobs.reconcile_saved(root,args.jobid))
    elif args.action=="csharp-repair":print_json(csharp_jobs.repair_compiler_delta(root,args.jobid))
    elif args.action=="csharp-reconcile-refs":print_json(csharp_jobs.reconcile_compiler_references(root,args.jobid))
    elif args.action=="csharp-repair-using":print_json(csharp_jobs.repair_missing_using(root,args.jobid))
    elif args.action=="csharp-repair-create":print_json(csharp_repair.create(root,args.jobid))
    elif args.action=="language-create":print_json(multilang.create(root,args.spec))
    elif args.action=="language-run":print_json(multilang.run(root,args.jobid,args.tool))
    elif args.action=="language-verify":print_json(multilang.verify(root,args.jobid))
    elif args.action=="language-status":print_json(multilang.summary(root,args.jobid))
    elif args.action=="language-stop":print_json(multilang.control(root,args.jobid,"STOP"))
    elif args.action=="language-resume":print_json(multilang.control(root,args.jobid,"RUN"))
    elif args.action=="status":print_json(engine.summary(root,args.jobid))
    elif args.action=="verify":print_json(engine.verify_job(root,args.jobid))
    elif args.action=="stop":print_json(engine.control(root,args.jobid,"STOP"))
    elif args.action=="resume":print_json(engine.control(root,args.jobid,"RUN"))
    elif args.action=="list":
        engine.init(root)
        result=[]
        for folder in sorted((root/"work").glob("AF-*")):
            if (folder/"state.json").is_file():
                result.append({"jobId":folder.name,"state":engine.load(folder/"state.json")["status"]})
        print_json(result)
    elif args.action=="run-queued":
        engine.init(root)
        result=[]
        count=0
        for folder in sorted((root/"work").glob("AF-*")):
            if count>=max(0,min(args.limit,100)):break
            if not (folder/"state.json").exists():continue
            status=engine.load(folder/"state.json")["status"]
            if status not in ("PENDING","FAILED_ATTEMPT","BLOCKED_PROVIDER","BLOCKED_ISOLATION"):continue
            count+=1
            try:result.append({"jobId":folder.name,"result":operate.run_job(root,folder.name)})
            except Exception as error:result.append({"jobId":folder.name,"error":str(error)})
        print_json(result)
    elif args.action=="pygen-create":
        print_json(python_general.create(root,args.spec))
    elif args.action=="pygen-run":
        print_json(python_general.run(root,args.jobid))
    elif args.action=="pygen-stop":
        print_json(python_general.stop(root,args.jobid))
    elif args.action=="pygen-status":
        print_json(python_general.status(root,args.jobid))
    elif args.action=="pygen-verify":
        print_json(python_general.verify(root,args.jobid))
    elif args.action=="pygen-reconcile":
        print_json(python_general.reconcile_saved(root,args.jobid,args.stop_receipt))
    elif args.action=="pygen-repair-create":
        print_json(python_general_repair.create(root,args.originaljob))
    elif args.action=="pygen-repair-run":
        print_json(python_general_repair.run(root,args.repairid))
    elif args.action=="pygen-repair-verify":
        print_json(python_general_repair.verify(root,args.repairid))
    elif args.action=="browser-close":
        print_json(export_recovery.close(root,args.repoid))
    elif args.action=="browser-close-status":
        print_json(export_recovery.classify(root,args.repoid))
    elif args.action=="browser-close-verify":
        print_json(export_recovery.verify(root,args.closureid))
    elif args.action=="python-create":
        print_json(python_direct.create(root,args.spec))
    elif args.action=="python-run":
        print_json(python_direct.run(root,args.jobid))
    elif args.action=="python-stop":
        print_json(python_direct.stop(root,args.jobid))
    elif args.action=="python-status":
        print_json(python_direct.status(root,args.jobid))
    elif args.action=="python-verify":
        print_json(python_direct.verify(root,args.jobid))
    elif args.action=="repair-create":
        print_json(repair_bridge.create(root,args.sourcejob,revision=args.revision))
    elif args.action=="repair-run":
        print_json(repair_bridge.run(root,args.repairid))
    elif args.action=="repair-verify":
        print_json(repair_bridge.verify(root,args.repairid))
    elif args.action=="audit-inventory":
        print_json(audit_inventory.snapshot(root,strict=True))
    elif args.action=="audit-create":
        print_json(self_audit.create(root,args.spec))
    elif args.action=="audit-run":
        print_json(self_audit.run(root,args.auditid))
    elif args.action=="audit-status":
        print_json(self_audit.status(root,args.auditid))
    elif args.action=="audit-stop":
        print_json(self_audit.stop(root,args.auditid))
    elif args.action=="audit-verify":
        print_json(self_audit.verify(root,args.auditid))
    elif args.action=="blackbox-create":
        plan=args.spec.resolve()
        if (not plan.is_file() or plan.is_symlink() or
            not plan.is_relative_to(root/"examples")):
            raise ValueError("BLACKBOX_PLAN_MUST_BE_FIRST_PARTY_EXAMPLE")
        spec=json.loads(plan.read_text("utf-8"))
        if set(spec)!={"objective","cases"}:
            raise ValueError("BLACKBOX_PLAN_CONTRACT_INVALID")
        print_json(blackbox.create(root,spec["cases"],objective=spec["objective"]))
    elif args.action=="blackbox-verify":
        print_json(blackbox.verify(root,args.sessionid))
    elif args.action=="blackbox-report":
        verified=blackbox.verify(root,args.sessionid)
        if verified["status"]!="BLACKBOX_ALL_RECORDED_SHA_VERIFIED":
            raise RuntimeError("BLACKBOX_NOT_FINAL")
        print_json({"verified":verified,
                    "report":json.loads((root/"blackbox"/args.sessionid/"report.json").read_text("utf-8"))})
    elif args.action=="bundle":print_json(build_bundle(root))
    elif args.action=="verify-bundle":print_json(verify_bundle(args.zipfile))
    return 0

if __name__=="__main__":
    try:sys.exit(main())
    except Exception as error:
        print_json({"status":"ERROR","type":type(error).__name__,"error":str(error)})
        sys.exit(2)
