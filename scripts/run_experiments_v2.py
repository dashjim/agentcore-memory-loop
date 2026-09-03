#!/usr/bin/env python3
"""V2 单变量消融实验：唯一变量 = 是否注入并沉淀记忆（其余 harness/抽取提示/单次invoke/模型全相同）。

- nomem×N_NOMEM：纯抽取基线。
- mem×N_MEM：抽取前注入 canonical 规则集；抽取后 反思→consolidation→更新 canonical（串行累积）。
运行前清空 canonical，落库 runs_v2.db。
"""
import sys, time, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import boto3
from src import orchestrator as O, corpus, memory_tools as MT, config

TARGET_PREFIX = "150方液氮罐"
N_NOMEM = 2
N_MEM = 4
DB = str(Path(__file__).resolve().parent.parent / "runs_v2.db")


def _clear_canonical():
    dp = boto3.client("bedrock-agentcore", region_name=config.REGION)
    mid = config.load_deployed()["CUSTOM_MEMORY_ID"]
    sid = MT.canon_session(config.ACTOR_ID)
    n = 0
    for ev in MT._list_all_events(dp, mid, config.ACTOR_ID, sid):
        dp.delete_event(memoryId=mid, actorId=config.ACTOR_ID, sessionId=sid, eventId=ev["eventId"])
        n += 1
    return n


def main():
    doc = next(d["name"] for d in corpus.list_docs() if d["name"].startswith(TARGET_PREFIX))
    print("TARGET:", doc[:34], flush=True)
    print("cleared canonical events:", _clear_canonical(), flush=True)
    if os.path.exists(DB):
        os.remove(DB)

    for i in range(N_NOMEM):
        t = time.time(); r = O.run_ablation(doc, use_memory=False, db_path=DB)
        print(f"[nomem#{i+1}] {time.time()-t:.0f}s n_ex={r['num_extracted']} cov={r['coverage']} "
              f"acc={r['accuracy']} tok={r['total_tokens']}", flush=True)
    for i in range(N_MEM):
        t = time.time(); r = O.run_ablation(doc, use_memory=True, db_path=DB)
        print(f"[mem#{i+1}]   {time.time()-t:.0f}s n_ex={r['num_extracted']} cov={r['coverage']} "
              f"acc={r['accuracy']} tok={r['total_tokens']}", flush=True)

    print("\n==== canonical 最终（前 200 字）====", flush=True)
    print(MT.read_canonical(config.load_deployed()["CUSTOM_MEMORY_ID"], config.ACTOR_ID)[:200], flush=True)
    print("\n==== runs_v2.db 汇总 ====", flush=True)
    from src import runstore
    for r in sorted(runstore.list_runs(path=DB), key=lambda x: x["ts"]):
        print(f"{r['ts'][11:19]} {r['memory_mode']:6} cov={r['coverage']} acc={r['accuracy']} "
              f"tok={r['total_tokens']} n_ex={r['num_extracted']}", flush=True)


if __name__ == "__main__":
    main()
