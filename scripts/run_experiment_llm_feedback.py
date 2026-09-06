#!/usr/bin/env python3
"""LLM 检查器反馈被记忆捕获的效果验证（模拟大模型质检 / 人类反馈回路）。

真实 agent 任务里往往有人类反馈、或大模型对比 GT 的反馈。问题：这种反馈被记忆系统
捕获后，实际有没有效果？本实验让一个 LLM 检查器对比抽取结果与 GT，自动产出可迁移反馈，
写进记忆，下一次抽取注入——用它模拟"有大模型检查/人类反馈"的场景。GT 只进检查器，不进抽取器。

对照：基线(r1, 无反馈) vs 注入检查器反馈(r2)。落库 runs_llm_fb.db。
用法：python3 scripts/run_experiment_llm_feedback.py
"""
import sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import orchestrator, corpus  # noqa: E402

DB = "runs_llm_fb.db"


def main():
    doc = next(d["name"] for d in corpus.list_docs() if d["name"].startswith("150方液氮罐"))
    r = orchestrator.run_llm_feedback(doc, db_path=DB)

    def f(x):
        return "None" if x is None else f"{x:.3f}"
    print("=== LLM 检查器对比 GT 产出的反馈（写进了记忆）===")
    print(r["feedback"])
    print("\n=== 效果对照 ===")
    for tag, d in (("r1 基线(无反馈)", r["r1"]), ("r2 注入检查器反馈", r["r2"])):
        print(f"{tag}: cov={f(d['coverage'])} P={f(d['precision'])} F1={f(d['f1'])} n_ex={d['num_extracted']}")


if __name__ == "__main__":
    main()
