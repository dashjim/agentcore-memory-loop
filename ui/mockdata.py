"""内置 mock 数据与 mock 后端。

当 src/ 模块尚未就绪（其他并行 workstream 提供），或设置环境变量
MEMORY_LOOP_UI_MOCK=1 时，UI 使用本模块提供的确定性假数据，
以便在无 AWS / 无真实抽取的情况下自测前端与接口。

真实实现请见 src/{corpus,runstore,orchestrator}.py（import 即可）。
"""

from __future__ import annotations

import threading
import time
import uuid
from copy import deepcopy

# ---------------------------------------------------------------------------
# 文档列表（对应 corpus.list_docs()）
# ---------------------------------------------------------------------------
_DOCS = [
    {"name": "150方液氮罐技术要求", "num_pages": 12, "has_gt": True},
    {"name": "CFL-150-1.0低温液体贮罐评审报告", "num_pages": 8, "has_gt": True},
    {"name": "2477080009流程图", "num_pages": 3, "has_gt": False},
]

# ---------------------------------------------------------------------------
# 学到的规则（对应 orchestrator.read_lessons(scope)）
# ---------------------------------------------------------------------------
_LESSONS = {
    # M_strat：跨任务的战略规则
    "strat": [
        "低温储罐类文档优先抽取：设计压力、设计温度、有效容积、介质、材质。",
        "遇到「公开」「令号」等水印/批注文字应忽略，不计入抽取项。",
        "单位需归一化：压力统一 MPa，容积统一 m³，温度统一 ℃。",
        "同一参数在正文与表格重复出现时，以表格值为准。",
    ],
    # M_tact：与当前文档强相关的战术技巧
    "tact": [
        "本文档「技术要求」章节的表 2 含全部关键设计参数，优先解析。",
        "第 5 页手写批注非正式参数，抽取时排除。",
        "型号 150m³ 出现在标题与图签两处，取图签为准。",
    ],
}

# ---------------------------------------------------------------------------
# 运行历史种子（对应 runstore.list_runs / get_run）
# 设计为可直接支撑三个实验面板：
#   A：同一文档 custom 模式多次运行，revision_count 递减（4 -> 2 -> 1）
#   B：同一文档在 none/episodic/custom 三模式下首轮覆盖率/准确率对比递增
#   C：规则列表见 _LESSONS
# ---------------------------------------------------------------------------
_BASE_TS = 1_724_900_000  # 固定基准时间戳，保证确定性排序


def _run(rid, ts_off, doc, mode, warm, rev, elapsed, itok, otok, cov, acc,
         passed, n_ext, n_gt, notes):
    return {
        "run_id": rid,
        "ts": _BASE_TS + ts_off,
        "doc_name": doc,
        "memory_mode": mode,
        "warm": warm,
        "revision_count": rev,
        "elapsed_sec": elapsed,
        "input_tokens": itok,
        "output_tokens": otok,
        "total_tokens": itok + otok,
        "coverage": cov,
        "accuracy": acc,
        "self_review_pass": passed,
        "num_extracted": n_ext,
        "num_gt": n_gt,
        "extracted_json": {
            "设计压力": "1.0 MPa",
            "有效容积": "150 m³",
            "介质": "液氮",
        },
        "notes": notes,
    }


_SEED_RUNS = [
    # --- 实验 B：三模式首轮对比（同一文档、warm=0、每模式取时间最早的一条为首轮） ---
    _run("r-b-none", 10, "150方液氮罐技术要求", "none", 0, 4, 41.2, 5200, 900,
         0.62, 0.71, 0, 8, 13, "无记忆基线：首轮覆盖率偏低"),
    _run("r-b-epi", 20, "150方液氮罐技术要求", "episodic", 0, 3, 38.7, 5400, 880,
         0.77, 0.80, 0, 10, 13, "Episodic：情景记忆带来小幅提升"),
    # --- 实验 A：custom 模式同一文档多次运行，反思轮数递减 ---
    _run("r-a-1", 30, "150方液氮罐技术要求", "custom", 0, 4, 45.9, 5600, 1020,
         0.85, 0.83, 1, 11, 13, "custom 首轮：规则尚空，反思 4 轮"),
    _run("r-a-2", 40, "150方液氮罐技术要求", "custom", 0, 2, 33.1, 5300, 780,
         0.92, 0.88, 1, 12, 13, "custom 第 2 次：命中战术记忆，反思降到 2 轮"),
    _run("r-a-3", 50, "150方液氮罐技术要求", "custom", 0, 1, 27.4, 5100, 690,
         0.95, 0.91, 1, 13, 13, "custom 第 3 次：反思 1 轮即通过自审"),
    # --- 实验 B 的 custom 首轮，用第一条 custom（r-a-1）即可；此处再加一条 warm 对比 ---
    _run("r-b-warm", 60, "150方液氮罐技术要求", "custom", 1, 1, 24.8, 5000, 670,
         0.96, 0.93, 1, 13, 13, "预热记忆后首轮：覆盖率/准确率显著高于空记忆"),
]


class MockBackend:
    """线程安全的内存后端，模拟 src 三个模块的行为。"""

    def __init__(self):
        self._lock = threading.Lock()
        self._runs = deepcopy(_SEED_RUNS)
        self._lessons = deepcopy(_LESSONS)
        self._seq = 0

    # -- corpus.list_docs --
    def list_docs(self):
        return deepcopy(_DOCS)

    # -- runstore.list_runs --
    def list_runs(self, doc=None, mode=None):
        with self._lock:
            rows = deepcopy(self._runs)
        if doc:
            rows = [r for r in rows if r["doc_name"] == doc]
        if mode:
            rows = [r for r in rows if r["memory_mode"] == mode]
        rows.sort(key=lambda r: r["ts"])
        return rows

    # -- runstore.get_run --
    def get_run(self, run_id):
        with self._lock:
            for r in self._runs:
                if r["run_id"] == run_id:
                    return deepcopy(r)
        return None

    # -- orchestrator.read_lessons --
    def read_lessons(self, scope):
        with self._lock:
            return list(self._lessons.get(scope, []))

    # -- orchestrator.clear_memory_for_mode --
    def clear_memory_for_mode(self, memory_mode):
        with self._lock:
            if memory_mode == "custom":
                self._lessons = {"strat": [], "tact": []}
            elif memory_mode == "episodic":
                # episodic 无显式规则列表，清除为空操作
                pass
            return {"ok": True, "cleared": memory_mode}

    # -- orchestrator.run_extraction --
    def run_extraction(self, doc_name, memory_mode, warm=False):
        # 模拟耗时（短），便于前端观察转圈
        time.sleep(0.4)
        with self._lock:
            self._seq += 1
            # 依据同一文档 + 模式的历史次数，模拟反思轮数递减
            prior = [
                r for r in self._runs
                if r["doc_name"] == doc_name and r["memory_mode"] == memory_mode
            ]
            n_prior = len(prior)
            if memory_mode == "none":
                rev = 4
                cov, acc = 0.63, 0.72
            elif memory_mode == "episodic":
                rev = max(2, 3 - n_prior)
                cov, acc = min(0.9, 0.77 + 0.03 * n_prior), min(0.9, 0.80 + 0.02 * n_prior)
            else:  # custom
                base_rev = 4 if not warm else 1
                rev = max(1, base_rev - n_prior)
                cov = min(0.98, (0.90 if warm else 0.85) + 0.02 * n_prior)
                acc = min(0.96, (0.92 if warm else 0.83) + 0.02 * n_prior)
            passed = 1 if (cov >= 0.9 and rev <= 3) else 0
            n_gt = 13
            n_ext = round(cov * n_gt)
            new = _run(
                rid=f"r-live-{self._seq}",
                ts_off=1000 + self._seq * 10 + int(time.time()) % 1000,
                doc=doc_name,
                mode=memory_mode,
                warm=1 if warm else 0,
                rev=rev,
                elapsed=round(20 + rev * 5.5, 1),
                itok=5000 + rev * 120,
                otok=650 + rev * 90,
                cov=round(cov, 3),
                acc=round(acc, 3),
                passed=passed,
                n_ext=n_ext,
                n_gt=n_gt,
                notes=f"mock 实时运行 #{self._seq}（模式={memory_mode}，预热={bool(warm)}）",
            )
            new["ts"] = int(time.time())  # 真实当前时间，排最新
            self._runs.append(new)
            # 模拟：custom 运行会沉淀一条新战术规则
            if memory_mode == "custom":
                self._lessons["tact"].append(
                    f"[运行 #{self._seq}] 针对《{doc_name}》记录的新战术：优先核对表格单位。"
                )
            return deepcopy(new)


# 单例，供 server 在 mock 模式下复用（保持运行历史累积）
MOCK = MockBackend()
