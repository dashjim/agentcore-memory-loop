#!/usr/bin/env python3
"""人类反馈被记忆捕获的场景验证。

问题：记忆的"注入路径"本身有没有用？还是之前只是"GT-free 自省"产出的内容太差？
做法：把 GT 错误分析得到的结论**当作人类专家反馈**，直接写进 AgentCore memory 的 canonical 分区，
然后用**基线抽取提示词**(opt=False) 跑 mem——这条教训只从记忆注入、不进提示词。
对照：
  - 基线 nomem: recall_fail=27, 探针 1/7, cov 0.642
  - nomem+opt-v2(教训在提示词里): recall_fail=1, 探针 7/7, cov 0.715
若本实验(教训在记忆里)也拿到 ≈7/7、recall_fail≈1 → 证明记忆注入路径没问题，坏的是自省内容。

落库 runs_v2_hf.db。用法：python3 scripts/run_experiment_human_feedback.py
"""
import sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import orchestrator, corpus, memory_tools, config  # noqa: E402

DB = "runs_v2_hf.db"

# 人类专家反馈（内容=GT 错误分析结论；与 opt-v2 提示词强化项同实质，但此处作为"记忆"注入）
HUMAN_FEEDBACK = """【人工审阅反馈·抽取经验（务必逐条应用）】
1. 不要只抽定量指标：定性要求、流程/工序要求、报告/测量要求、待确认/待细化事项也要逐条抽取。
   做法——把「要求类型」放入『指标名称』、「要求内容」放入『指标特征』（无数值也要成条）。示例：
   - “外观颜色及喷涂 LOGO 须与甲方确认” → 指标名称=外观颜色与喷涂确认；指标特征=须与甲方确认
   - “真空度测量报告 / 真空度测量要求”   → 指标名称=真空度测量；指标特征=需按要求测量并提供报告
   - “外部油漆等工序”                    → 指标名称=外部油漆工序；指标特征=按工序要求执行
   - “承制单位细化设计…提供全套地脚螺栓”  → 指标名称=地脚螺栓；指标特征=提供全套、按土建尺寸细化
2. 覆盖常被漏抽的类别：真空度/真空度测量、无损检测(RT/PT/UT 比例/合格级别/标准)、
   安装环境(温度/风/雪/地震)、主要受压元件、阀门仪表、管口接管/法兰、材料材质。
3. 粒度对齐 GT：默认一条原文=一条记录；仅当一句确含多个相互独立指标时才拆；严禁过度拆分。"""


def main():
    doc = next(d["name"] for d in corpus.list_docs() if d["name"].startswith("150方液氮罐"))
    mem_id = config.load_deployed().get("CUSTOM_MEMORY_ID")
    c = memory_tools._client(None)
    # 清空 canon，只留这条人类反馈（保证注入的就是它）
    sid = memory_tools.canon_session(config.ACTOR_ID)
    n = 0
    for ev in memory_tools._list_all_events(c, mem_id, config.ACTOR_ID, sid):
        eid = ev.get("eventId")
        if eid:
            c.delete_event(memoryId=mem_id, actorId=config.ACTOR_ID, sessionId=sid, eventId=eid)
            n += 1
    memory_tools.write_canonical(mem_id, config.ACTOR_ID, HUMAN_FEEDBACK, client=c)
    print(f"清空 canon {n} 条，写入人类反馈 {len(HUMAN_FEEDBACK)} 字符")
    # 校验注入的确实是人类反馈
    got = memory_tools.read_canonical(mem_id, config.ACTOR_ID, client=c)
    print(f"read_canonical 回读 {len(got)} 字符, 一致={got.strip()==HUMAN_FEEDBACK.strip()}")

    # 基线提示词(opt=False) + 注入的人类反馈记忆
    r = orchestrator.run_ablation(doc, use_memory=True, db_path=DB, opt=False)
    nn = json.loads(r["notes"])
    def f(x):
        return "None" if x is None else f"{x:.3f}"
    print(f"\nmem+人类反馈(基线提示词)  cov={f(r['coverage'])} P={f(nn['precision'])} "
          f"F1={f(nn['f1'])} n_ex={r['num_extracted']}")


if __name__ == "__main__":
    main()
