"""orchestrator：用 fake invoke_harness 驱动完整工具回路，不触任何 AWS。

脚本序列：先请求 recall_lessons 工具 → 再请求 record_lesson 工具 → 最后产出 JSON + __META__。
断言：工具回路正确执行、toolUse.input 片段累积正确、token/revision_count 采集正确、run 正确落库。
"""
import json

from src import orchestrator, runstore

_ACTOR = "memory-loop"

# 最终抽取结果 + META（跨两个 text delta 分片，验证文本累积）
_FINAL_JSON = json.dumps(
    [{"设备主体": "150m³液氮储罐", "设备部件": "排液管线", "指标名称": "口径",
      "指标特征": "48.3×3.6", "原文": "排液管线 48.3×3.6"}],
    ensure_ascii=False,
)
_FINAL_TEXT = _FINAL_JSON + '\n__META__ {"revision_count":2}'


def _recall_stream():
    # toolUse.input 拆成两段字符串片段，验证累积后 json.loads
    return [
        {"messageStart": {"role": "assistant"}},
        {"contentBlockStart": {"contentBlockIndex": 0,
                               "start": {"toolUse": {"toolUseId": "tu-1", "name": "recall_lessons"}}}},
        {"contentBlockDelta": {"contentBlockIndex": 0, "delta": {"toolUse": {"input": '{"scope":"st'}}}},
        {"contentBlockDelta": {"contentBlockIndex": 0, "delta": {"toolUse": {"input": 'rat","query":"口径规则"}'}}}},
        {"contentBlockStop": {"contentBlockIndex": 0}},
        {"messageStop": {"stopReason": "tool_use"}},
        {"metadata": {"usage": {"inputTokens": 100, "outputTokens": 20, "totalTokens": 120}}},
    ]


def _record_stream():
    return [
        {"messageStart": {"role": "assistant"}},
        {"contentBlockStart": {"contentBlockIndex": 0,
                               "start": {"toolUse": {"toolUseId": "tu-2", "name": "record_lesson"}}}},
        {"contentBlockDelta": {"contentBlockIndex": 0,
                               "delta": {"toolUse": {"input": '{"scope":"tact","text":"排液管线口径记为 48.3×3.6"}'}}}},
        {"contentBlockStop": {"contentBlockIndex": 0}},
        {"messageStop": {"stopReason": "tool_use"}},
        {"metadata": {"usage": {"inputTokens": 80, "outputTokens": 10, "totalTokens": 90}}},
    ]


def _final_stream():
    half = len(_FINAL_TEXT) // 2
    return [
        {"messageStart": {"role": "assistant"}},
        {"contentBlockStart": {"contentBlockIndex": 0, "start": {}}},
        {"contentBlockDelta": {"contentBlockIndex": 0, "delta": {"text": _FINAL_TEXT[:half]}}},
        {"contentBlockDelta": {"contentBlockIndex": 0, "delta": {"text": _FINAL_TEXT[half:]}}},
        {"contentBlockStop": {"contentBlockIndex": 0}},
        {"messageStop": {"stopReason": "end_turn"}},
        {"metadata": {"usage": {"inputTokens": 200, "outputTokens": 50, "totalTokens": 250}}},
    ]


class FakeHarness:
    def __init__(self, streams):
        self.streams = list(streams)
        self.calls = []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        return {"stream": iter(self.streams.pop(0))}


class FakeMemoryClient:
    """模拟数据面：recall 走 list_events，record 走 create_event（新机制）。"""

    def __init__(self):
        self.listed = []
        self.created = []

    def list_events(self, **kw):
        self.listed.append(kw)
        return {"events": [{"eventId": "ev-1", "payload": [
            {"conversational": {"content": {"text": "口径不要补单位"}, "role": "ASSISTANT"}}]}]}

    def create_event(self, **kw):
        self.created.append(kw)
        return {"event": {"eventId": "ev-1"}}


class FakeScorer:
    def __init__(self):
        self.calls = []

    def score(self, extracted, gt, judge_fn):
        self.calls.append((extracted, gt, judge_fn))
        return {"coverage": 1.0, "accuracy": 0.9}

    def build_bedrock_judge(self, model_id, region):
        return lambda *a, **k: {}


class FakeCorpus:
    def load_doc_text(self, name):
        return "文档正文……排液管线 48.3×3.6"

    def load_gt(self, name):
        return [{"设备主体": "150m³液氮储罐", "设备部件": "排液管线", "指标名称": "口径",
                 "指标特征": "48.3×3.6", "原文": "排液管线 48.3×3.6"}]

    def list_docs(self):
        return ["docA"]


def _deps(tmp_path, harness, memory_client=None, scorer=None):
    return {
        "invoke_harness": harness,
        "memory_client": memory_client or FakeMemoryClient(),
        "corpus": FakeCorpus(),
        "scorer": scorer or FakeScorer(),
        "runstore": runstore,
        "judge_fn": None,
        "deployed": {
            "HARNESS_ARN": "arn:aws:bedrock-agentcore:us-west-2:123456789012:harness/test",
            "EPISODIC_MEMORY_ID": "mem-episodic",
            "CUSTOM_MEMORY_ID": "mem-custom",
        },
        "db_path": str(tmp_path / "runs.db"),
        "system_prompt": "system prompt",
        "harness_config": {"tools": [{"type": "inline_function", "name": "recall_lessons"},
                                      {"type": "inline_function", "name": "record_lesson"}]},
    }


def test_custom_mode_tool_loop(tmp_path):
    harness = FakeHarness([_recall_stream(), _record_stream(), _final_stream()])
    mem = FakeMemoryClient()
    scorer = FakeScorer()
    deps = _deps(tmp_path, harness, mem, scorer)

    run = orchestrator.run_extraction("docA", "custom", warm=True, deps=deps)

    # 三次 invoke：recall -> record -> final
    assert len(harness.calls) == 3
    # 全程同一 runtimeSessionId，且 ≥33 字符
    sids = {c["runtimeSessionId"] for c in harness.calls}
    assert len(sids) == 1
    assert len(next(iter(sids))) >= 33
    # custom 模式带 tools
    assert all("tools" in c for c in harness.calls)

    # 工具回路执行到位：一次 recall（strat 分区，list_events）、一次 record（tact 分区，create_event）
    assert len(mem.listed) == 1
    assert mem.listed[0]["sessionId"].startswith(f"strat-{_ACTOR}")  # recall scope=strat

    assert len(mem.created) == 1
    created = mem.created[0]
    assert created["sessionId"].startswith(f"tact-{_ACTOR}")          # record scope=tact，按文档分区
    assert "eventTimestamp" in created                                # 必填项已带
    assert created["payload"][0]["conversational"]["content"]["text"] == "排液管线口径记为 48.3×3.6"
    assert created["payload"][0]["conversational"]["role"] == "ASSISTANT"

    # 指标采集
    assert run["revision_count"] == 2
    assert run["input_tokens"] == 100 + 80 + 200
    assert run["output_tokens"] == 20 + 10 + 50
    assert run["total_tokens"] == 120 + 90 + 250
    assert run["num_extracted"] == 1
    assert run["num_gt"] == 1
    assert run["self_review_pass"] == 1
    assert run["warm"] == 1
    assert run["coverage"] == 1.0
    assert run["accuracy"] == 0.9

    # scorer 收到抽取结果
    assert scorer.calls and scorer.calls[0][0] == json.loads(_FINAL_JSON)

    # 正确落库
    stored = runstore.get_run(run["run_id"], path=deps["db_path"])
    assert stored is not None
    assert stored["memory_mode"] == "custom"
    assert json.loads(stored["extracted_json"]) == json.loads(_FINAL_JSON)
    notes = json.loads(stored["notes"])
    assert notes["client_invoke_loops"] == 3
    assert notes["gate_retry"] is False


def test_none_mode_no_tools_no_memory(tmp_path):
    harness = FakeHarness([_final_stream()])
    mem = FakeMemoryClient()
    deps = _deps(tmp_path, harness, mem)

    run = orchestrator.run_extraction("docA", "none", deps=deps)

    assert len(harness.calls) == 1
    assert "tools" not in harness.calls[0]          # none 模式不带工具
    assert mem.listed == [] and mem.created == []    # 无任何记忆调用
    assert run["memory_mode"] == "none"
    assert run["self_review_pass"] == 1
    assert run["total_tokens"] == 250


def test_gate_retry_on_bad_first_output(tmp_path):
    # 第一次产出非法（空数组），触发一次兜底补 invoke，第二次合规
    bad_stream = [
        {"messageStart": {"role": "assistant"}},
        {"contentBlockStart": {"contentBlockIndex": 0, "start": {}}},
        {"contentBlockDelta": {"contentBlockIndex": 0, "delta": {"text": "[]\n__META__ {\"revision_count\":0}"}}},
        {"contentBlockStop": {"contentBlockIndex": 0}},
        {"messageStop": {"stopReason": "end_turn"}},
        {"metadata": {"usage": {"inputTokens": 10, "outputTokens": 5, "totalTokens": 15}}},
    ]
    harness = FakeHarness([bad_stream, _final_stream()])
    deps = _deps(tmp_path, harness)

    run = orchestrator.run_extraction("docA", "none", deps=deps)

    assert len(harness.calls) == 2          # 原始 + 兜底补 invoke
    assert run["self_review_pass"] == 1     # 补 invoke 后合规
    assert run["num_extracted"] == 1
    assert run["revision_count"] == 2
    assert run["total_tokens"] == 15 + 250  # token 跨门禁累加
    notes = json.loads(runstore.get_run(run["run_id"], path=deps["db_path"])["notes"])
    assert notes["gate_retry"] is True
