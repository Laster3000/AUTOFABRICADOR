# coding: utf-8
"""R68 portable manual-only CLI to owner-pinned module agent + original WASI."""
from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from autofab import repo_multimodule_r69 as factory

def main():
    p=argparse.ArgumentParser(description="AUTOFABRICADOR portable R69 multi-module")
    p.add_argument("action",choices=("create","run","status","verify"))
    p.add_argument("--job")
    p.add_argument("--spec",default=str(ROOT/"examples/r69_erp_cuatro_modulos_owner.json"))
    p.add_argument("--plan",default=str(ROOT/"examples/r69_erp_cuatro_modulos_plan.json"))
    p.add_argument("--holdout",default=str(ROOT/"examples/r69_erp_holdout_21.json"))
    p.add_argument("--attempts",type=int,default=3)
    a=p.parse_args()
    if a.action=="create":result=factory.create(ROOT,a.spec,a.plan,a.holdout)
    else:
        if not a.job:p.error("--job obligatorio para trabajos existentes")
        if a.action=="run":result=factory.run(ROOT,a.job,max_attempts=a.attempts)
        elif a.action=="status":result=factory.status(ROOT,a.job)
        else:result=factory.verify(ROOT,a.job)
    print(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2),flush=True)
if __name__=="__main__":main()
