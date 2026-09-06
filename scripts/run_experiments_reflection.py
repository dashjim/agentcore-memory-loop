#!/usr/bin/env python3
"""Reflection（Level-2 验证循环）实验：复现用户观察到"有效"的 reflection 模式。

每轮 run_reflection = round1 单遍抽取 → 批评者(看原文+输出,不看GT) → round2 带批评重抽同一篇。
成对比较 round2 相对 round1 的覆盖率/精确率/F1 增量。跑 N 对（默认 3），观察是否稳定提升。

用法：python3 scripts/run_experiments_reflection.py [N]
落库：runs_reflection.db（含机密文档抽取内容，已在 .gitignore）。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import orchestrator  # noqa: E402
from src import corpus  # noqa: E402

DB = "runs_reflection.db"


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    doc = next(d["name"] for d in corpus.list_docs() if d["name"].startswith("150方液氮罐"))
    print(f"文档：{doc}  |  {n} 对 (round1 单遍 vs round2 带批评重抽)  |  落库 {DB}\n")
    for i in range(n):
        r = orchestrator.run_reflection(doc, db_path=DB)
        r1, r2 = r["r1"], r["r2"]
        def fmt(x):
            return "None" if x is None else f"{x:.3f}"
        print(f"[{i+1}/{n}] round1  cov={fmt(r1['coverage'])} P={fmt(r1['precision'])} "
              f"F1={fmt(r1['f1'])} n_ex={r1['num_extracted']}")
        print(f"      round2  cov={fmt(r2['coverage'])} P={fmt(r2['precision'])} "
              f"F1={fmt(r2['f1'])} n_ex={r2['num_extracted']}")
        if r1["coverage"] is not None and r2["coverage"] is not None:
            print(f"      Δcov={r2['coverage']-r1['coverage']:+.3f}  "
                  f"ΔF1={(r2['f1'] or 0)-(r1['f1'] or 0):+.3f}\n")


if __name__ == "__main__":
    main()
