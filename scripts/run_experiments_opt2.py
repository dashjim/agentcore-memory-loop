#!/usr/bin/env python3
"""opt-v2 记忆验证：把"抓非定量要求"的优化提示词用到 mem 抽取之上。

流程：清空 canonical 分区（保证 mem#1 冷启动）→ mem×3（opt="v2"，串行累积）。
mem#1 canonical 为空≈nomem+opt-v2；mem#2/#3 注入累积的 v2 规则，看记忆是否在改进的提示词之上继续受益。
落库 runs_v2_opt2.db（与前面 nomem+opt-v2 同库，便于对照）。

用法：python3 scripts/run_experiments_opt2.py [mem_rounds=3]
"""
import sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import orchestrator, corpus, memory_tools, config  # noqa: E402

DB = "runs_v2_opt2.db"


def clear_canon():
    c = memory_tools._client(None)
    mem_id = config.load_deployed().get("CUSTOM_MEMORY_ID")
    sid = memory_tools.canon_session(config.ACTOR_ID)
    n = 0
    for ev in memory_tools._list_all_events(c, mem_id, config.ACTOR_ID, sid):
        eid = ev.get("eventId")
        if eid:
            c.delete_event(memoryId=mem_id, actorId=config.ACTOR_ID, sessionId=sid, eventId=eid)
            n += 1
    return n


def main():
    rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    doc = next(d["name"] for d in corpus.list_docs() if d["name"].startswith("150方液氮罐"))
    print(f"清空 canonical: 删除 {clear_canon()} 条 → mem#1 冷启动")
    def f(x):
        return "None" if x is None else f"{x:.3f}"

    for i in range(rounds):
        r = orchestrator.run_ablation(doc, use_memory=True, db_path=DB, opt="v2")
        n = json.loads(r["notes"])
        print(f"mem#{i+1} opt=v2  cov={f(r['coverage'])} P={f(n['precision'])} "
              f"F1={f(n['f1'])} n_ex={r['num_extracted']} "
              f"canon_in={n['canonical_in_len']}→out={n['canonical_out_len']}", flush=True)


if __name__ == "__main__":
    main()
