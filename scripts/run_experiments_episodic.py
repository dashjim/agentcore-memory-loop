#!/usr/bin/env python3
"""Episodic 干净实验（据 review 修正 V1 episodic 的不足）：
- 冷启动：用**全新 actorId**（/episodes/{actor} 新分区，无历史污染），运行前确认检索为空。
- episodic 内部单变量：同一 extractor_ep harness，run1=冷(空记忆)、后续=记忆累积，只变"记忆内容"。
- 每轮后**等 AgentCore 异步提炼完成**（轮询 episode 记录数增长）再下一轮。
- 修复后一对一 scorer + judge token 单列。落库 runs_episodic.db。
- 另跑 nomem×2 作外部参照（注意 nomem 用 extractor、episodic 用 extractor_ep，非纯单变量）。
"""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import boto3
from src import config, corpus

TARGET_PREFIX = "150方液氮罐"
N_EPISODIC = 4
N_NOMEM = 2
DB = str(Path(__file__).resolve().parent.parent / "runs_episodic.db")
config.ACTOR_ID = f"eplab-{int(time.time())}"          # 全新 actor → episodic 冷启动分区

from src import orchestrator as O   # 在设置 ACTOR_ID 后 import 使用（O 内动态读 config.ACTOR_ID）

_dp = boto3.client("bedrock-agentcore", region_name=config.REGION)
_EPI = config.load_deployed()["EPISODIC_MEMORY_ID"]


def _episode_count():
    ns = f"/episodes/{config.ACTOR_ID}"
    try:
        r = _dp.retrieve_memory_records(memoryId=_EPI, namespace=ns,
                                        searchCriteria={"searchQuery": "抽取 规则 经验", "topK": 50})
        return len(r.get("memoryRecordSummaries", r.get("memoryRecords", [])))
    except Exception:
        return 0


def _wait_extraction(prev, timeout=420, interval=25):
    """等 episodic 异步提炼产出新记录（count>prev）或超时。"""
    t0 = time.time()
    while time.time() - t0 < timeout:
        time.sleep(interval)
        c = _episode_count()
        if c > prev:
            print(f"    …提炼完成 episode 记录 {prev}→{c}（等待 {time.time()-t0:.0f}s）", flush=True)
            return c
    print(f"    …等待提炼超时（仍 {prev} 条），继续", flush=True)
    return prev


def main():
    doc = next(d["name"] for d in corpus.list_docs() if d["name"].startswith(TARGET_PREFIX))
    print(f"ACTOR(冷启动)={config.ACTOR_ID}\nTARGET={doc[:30]}", flush=True)
    print("冷启动确认: episode 记录数 =", _episode_count(), "(应为0)", flush=True)

    for i in range(N_NOMEM):
        r = O.run_extraction(doc, "none", warm=False, deps={"db_path": DB})
        print(f"[nomem#{i+1}] cov={r['coverage']} acc={r['accuracy']} n_ex={r['num_extracted']}", flush=True)

    prev = _episode_count()
    for i in range(N_EPISODIC):
        r = O.run_extraction(doc, "episodic", warm=(i > 0), deps={"db_path": DB})
        print(f"[episodic#{i+1}] cov={r['coverage']} acc={r['accuracy']} n_ex={r['num_extracted']} "
              f"tok={r['total_tokens']}", flush=True)
        if i < N_EPISODIC - 1:
            prev = _wait_extraction(prev)   # 等提炼，保证下一轮能召回到新经验

    print("\n==== runs_episodic.db 汇总 ====", flush=True)
    from src import runstore
    import json as _j
    for r in sorted(runstore.list_runs(path=DB), key=lambda x: x["ts"]):
        jt = _j.loads(r["notes"]).get("judge_total_tokens")
        cov = f"{r['coverage']:.3f}" if r["coverage"] is not None else "None"
        acc = f"{r['accuracy']:.3f}" if r["accuracy"] is not None else "None"
        print(f"{r['memory_mode']:8} cov={cov} acc={acc} n_ex={r['num_extracted']} "
              f"抽取tok={r['total_tokens']} judge_tok={jt}", flush=True)
    print("最终 episode 记录数:", _episode_count(), flush=True)


if __name__ == "__main__":
    main()
