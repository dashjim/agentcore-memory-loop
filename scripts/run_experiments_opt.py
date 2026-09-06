#!/usr/bin/env python3
"""优化验证（据 §3.4 误差分析改进提示词后重跑）：
- 抽取提示词补"易漏类别(检测/环境/受压元件/焊接)"+ "抑制过度拆分(默认一原文一记录)"；
- reflect/consolidate 提示词同向优化。
对比基线(runs_v2.db, opt=False)看 覆盖率/精确率/F1、过度拆分度、易漏类别召回 是否改善。
落库 runs_v2_opt.db。
"""
import sys, time, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import boto3
from src import orchestrator as O, corpus, memory_tools as MT, config

TARGET_PREFIX = "150方液氮罐"; N_NOMEM = 2; N_MEM = 3
DB = str(Path(__file__).resolve().parent.parent / "runs_v2_opt.db")


def main():
    doc = next(d["name"] for d in corpus.list_docs() if d["name"].startswith(TARGET_PREFIX))
    mid = config.load_deployed()["CUSTOM_MEMORY_ID"]
    dp = boto3.client("bedrock-agentcore", region_name=config.REGION); sid = MT.canon_session(config.ACTOR_ID)
    n = 0
    for ev in MT._list_all_events(dp, mid, config.ACTOR_ID, sid):
        dp.delete_event(memoryId=mid, actorId=config.ACTOR_ID, sessionId=sid, eventId=ev["eventId"]); n += 1
    print(f"TARGET={doc[:30]} | cleared canonical={n}", flush=True)
    if os.path.exists(DB): os.remove(DB)
    for i in range(N_NOMEM):
        r = O.run_ablation(doc, use_memory=False, db_path=DB, opt=True)
        print(f"[opt-nomem#{i+1}] cov={r['coverage']} acc={r['accuracy']} n_ex={r['num_extracted']}", flush=True)
    for i in range(N_MEM):
        r = O.run_ablation(doc, use_memory=True, db_path=DB, opt=True)
        import json; nt = json.loads(r["notes"])
        print(f"[opt-mem#{i+1}] cov={r['coverage']} P={nt.get('precision')} F1={nt.get('f1')} "
              f"acc={r['accuracy']} n_ex={r['num_extracted']}", flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
