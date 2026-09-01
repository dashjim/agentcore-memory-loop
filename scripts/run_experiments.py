#!/usr/bin/env python3
"""跑 A/B/C 实验并把每次运行落库（runstore），最后打印汇总表。

设计：记忆累积需**串行**同模式多次运行。
- Phase A（同文档、三模式各重跑，看累积趋势）：目标文档上 none×N_NONE、episodic×N、custom×N。
  custom/episodic 每轮把经验写入各自记忆，下一轮受益；none 无记忆应基本持平。
- Phase B（跨文档迁移）：在一个"新文档"上跑 none 与 custom（custom 复用 A 积累的 strat），
  对比首轮覆盖率/准确率是否更高。
运行前清空 custom + episodic 记忆，保证从零开始。
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import orchestrator, corpus  # noqa: E402

# ---- 实验参数（可调）----
TARGET_DOC_PREFIX = "150方液氮罐"     # Phase A 目标文档（13 页，有 GT）
B_DOC_PREFIX = "2477080009简图"       # Phase B 新文档（小、有 GT）
N_CUSTOM = 4
N_EPISODIC = 4
N_NONE = 2


def _find(prefix):
    for d in corpus.list_docs():
        if d["name"].startswith(prefix):
            return d["name"]
    raise SystemExit(f"未找到文档：{prefix}")


def _run(doc, mode, warm, tag):
    t0 = time.time()
    r = orchestrator.run_extraction(doc, mode, warm=warm)
    print(f"[{tag}] mode={mode} rev={r['revision_count']} "
          f"cov={r['coverage']} acc={r['accuracy']} "
          f"tok={r['total_tokens']} loops={_loops(r)} {time.time()-t0:.0f}s", flush=True)
    return r


def _loops(r):
    import json
    try:
        return json.loads(r["notes"]).get("client_invoke_loops")
    except Exception:
        return None


def main():
    target = _find(TARGET_DOC_PREFIX)
    bdoc = _find(B_DOC_PREFIX)
    print(f"TARGET={target[:34]}...\nB_DOC={bdoc[:34]}...", flush=True)

    # 清空记忆（custom 的 strat+两文档 tact；episodic 的两文档 session 无法直接清，靠 actor 隔离——
    # 这里清 custom；episodic 记忆若需重置可另删 memory 资源。）
    cleared = orchestrator.clear_memory_for_mode("custom", scope=None, doc_names=[target, bdoc])
    print(f"cleared custom events: {cleared}", flush=True)

    # Phase A：none 基线
    for i in range(N_NONE):
        _run(target, "none", warm=False, tag=f"A-none#{i+1}")
    # Phase A：episodic 累积
    for i in range(N_EPISODIC):
        _run(target, "episodic", warm=(i > 0), tag=f"A-episodic#{i+1}")
    # Phase A：custom 累积
    for i in range(N_CUSTOM):
        _run(target, "custom", warm=(i > 0), tag=f"A-custom#{i+1}")

    # Phase B：跨文档迁移（custom 复用 A 积累的 strat）
    _run(bdoc, "none", warm=False, tag="B-none")
    _run(bdoc, "episodic", warm=False, tag="B-episodic")
    _run(bdoc, "custom", warm=True, tag="B-custom")

    print("\n==== 汇总（runstore 全部）====", flush=True)
    for r in orchestrator._resolve_deps(None).runstore.list_runs():
        print(f"{r['ts'][11:19]} {r['doc_name'][:14]:<14} {r['memory_mode']:<8} "
              f"rev={r['revision_count']} cov={r['coverage']} acc={r['accuracy']} tok={r['total_tokens']}",
              flush=True)


if __name__ == "__main__":
    main()
