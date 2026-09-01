"""薄驱动 orchestrator。

编排（recall→抽取→自审→修订→reflect→record）在 harness 的 scope-extract skill 里由
agent 自主完成；本模块只负责：单次/续调 invoke_harness、消费流、执行 inline_function
工具回路（custom 模式）、采集 token/耗时、结果合规兜底门禁、评分、落盘。

所有 boto3 调用集中在此并可注入（deps），便于 mock，单测不触任何 AWS。
"""
import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import uuid4

import boto3

from . import config
from . import memory_tools
from . import runstore as _runstore

# corpus / scorer 由并行模块提供；此处宽容 import，缺失则为 None（运行时可注入）。
try:
    from . import corpus as _corpus  # 接口: load_doc_text(name)/load_gt(name)/list_docs()
except Exception:  # pragma: no cover - 并行模块尚未落地
    _corpus = None  # TODO(接口): 上线前确保 src/corpus.py 存在或通过 deps 注入
try:
    from . import scorer as _scorer  # 接口: score(extracted,gt,judge_fn)/build_bedrock_judge(model_id,region)
except Exception:  # pragma: no cover
    _scorer = None  # TODO(接口): 上线前确保 src/scorer.py 存在或通过 deps 注入


REQUIRED_FIELDS = ["设备主体", "设备部件", "指标名称", "指标特征", "原文"]
_META_MARKER = "__META__"
_GATE_RETRY_PROMPT = (
    "上一轮输出不合规（必须是非空 JSON 数组，且每条含"
    "设备主体/设备部件/指标名称/指标特征/原文 且非空）。"
    "请仅重新输出修正后的最终 JSON 数组，并在末行给出 "
    '__META__ {"revision_count":N}。'
)
# 客户端侧 invoke 续调的次数上限（防御，防止工具回路失控）
_MAX_CLIENT_LOOPS = 12
_STREAM_ERROR_EVENTS = (
    "internalServerException", "validationException", "runtimeClientError",
    "modelStreamErrorException", "throttlingException", "serviceUnavailableException",
)


class HarnessStreamError(RuntimeError):
    """invoke_harness 流中返回的错误事件。"""


@dataclass
class Deps:
    """可注入依赖集合；None 字段在 _resolve_deps 中填充默认实现。"""
    invoke_harness: Callable = None      # (**kwargs) -> {"stream": <事件迭代器>}
    memory_client: Any = None            # 记忆工具用的 boto3 数据面 client（可注入 fake）
    corpus: Any = None                   # load_doc_text/load_gt/list_docs
    scorer: Any = None                   # score(extracted,gt,judge_fn)
    runstore: Any = None                 # insert_run/list_runs/get_run
    judge_fn: Any = None                 # scorer 用的 judge 回调
    deployed: dict = None                # {HARNESS_ARN, EPISODIC_MEMORY_ID, CUSTOM_MEMORY_ID}
    db_path: Any = None                  # runstore 落盘路径（None -> 默认 runs.db）
    system_prompt: str = None
    harness_config: dict = None


# --------------------------------------------------------------------------- #
# 默认实现 / 依赖解析
# --------------------------------------------------------------------------- #
def _default_invoke_harness(**kwargs):
    client = boto3.client("bedrock-agentcore", region_name=config.REGION)
    return client.invoke_harness(**kwargs)


_JUDGE_SYSTEM = (
    "你是严格的评审器（LLM-as-judge），只输出符合要求的 JSON，不要任何解释、不要调用任何工具。"
)


def _build_harness_judge(deps):
    """用 harness 本身充当 LLM-as-judge（会话角色无直连 Bedrock 权限，harness 执行角色有）。

    每次调用 = 一次独立 invoke_harness（override 评审系统提示、清空 skills、不带 tools、新 session）。
    """
    def judge_fn(prompt: str) -> str:
        kwargs = {
            "harnessArn": deps.deployed["HARNESS_ARN"],
            "runtimeSessionId": _new_session_id(),
            "messages": [{"role": "user", "content": [{"text": prompt}]}],
            "systemPrompt": [{"text": _JUDGE_SYSTEM}],
            "skills": [],
            "model": {"bedrockModelConfig": {
                "modelId": config.MODEL_ID, "temperature": 0, "maxTokens": 8192}},
            "maxIterations": 2,
            "timeoutSeconds": 300,
        }
        resp = deps.invoke_harness(**kwargs)
        return _consume_stream(resp["stream"])["text"]
    return judge_fn


def _read_system_prompt():
    try:
        return config.SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return ""  # TODO: 部署前确保 system-prompt.md 存在


def _read_harness_config():
    try:
        return json.loads(config.HARNESS_CONFIG_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return {}  # TODO: 部署前确保 harness.json 存在


def _resolve_deps(deps):
    if deps is None:
        deps = Deps()
    elif isinstance(deps, dict):
        deps = Deps(**deps)
    if deps.invoke_harness is None:
        deps.invoke_harness = _default_invoke_harness
    if deps.deployed is None:
        deps.deployed = config.load_deployed()
    if deps.system_prompt is None:
        deps.system_prompt = _read_system_prompt()
    if deps.harness_config is None:
        deps.harness_config = _read_harness_config()
    if deps.corpus is None:
        deps.corpus = _corpus
    if deps.scorer is None:
        deps.scorer = _scorer
    # judge：用 harness 当 LLM-as-judge（会话角色无直连 Bedrock 权限）。
    if deps.judge_fn is None and deps.invoke_harness is not None and deps.deployed.get("HARNESS_ARN"):
        deps.judge_fn = _build_harness_judge(deps)
    if deps.runstore is None:
        deps.runstore = _runstore
    return deps


def _new_session_id():
    """runtimeSessionId 必须 ≥33 字符——用两个 uuid4().hex 拼接后截断到 40。"""
    return (uuid4().hex + uuid4().hex)[:40]


def _memory_id_for_mode(mode, deployed):
    if mode == "episodic":
        return deployed.get("EPISODIC_MEMORY_ID")
    if mode == "custom":
        return deployed.get("CUSTOM_MEMORY_ID")
    return None  # none 模式：不带 memory


def _harness_arn_for_mode(mode, deployed):
    """episodic 用绑定了 episodicMem 的 extractor_ep；none/custom 用 extractor。"""
    if mode == "episodic":
        return deployed.get("EPISODIC_HARNESS_ARN") or deployed.get("HARNESS_ARN")
    return deployed.get("HARNESS_ARN")


_NONE_REFLECT = (
    "\n## 工作方式\n你没有任何记忆或外部工具。请：1) 逐段抽取；2) 自我审查（完整性/无臆造/"
    "合法JSON+字段齐全/一致无重复）并在需要时修订（最多4轮）；3) 只输出最终 JSON 数组，"
    "其后另起一行 `__META__ {\"revision_count\": <自审-修订循环次数>}`。你看不到标准答案。\n"
)


def _none_system_prompt(deps) -> str:
    """none 基线：抽取 schema（取自 system-prompt.md 的"工作方式"之前部分）+ 内联无工具反思。"""
    base = deps.system_prompt or ""
    head = base.split("## 工作方式")[0].rstrip()
    return head + "\n" + _NONE_REFLECT


# --------------------------------------------------------------------------- #
# 流消费：累积文本 + 累积 toolUse.input 片段
# --------------------------------------------------------------------------- #
def _consume_stream(stream) -> dict:
    """消费一次 invoke 的事件流，返回：
    {text, tool_uses:[{toolUseId,name,input}], assistant_message, usage, stop_reason}

    关键点：
    - contentBlockStart 里拿 toolUse 的 toolUseId/name；
    - contentBlockDelta.delta.toolUse.input 是**字符串片段**，需按 contentBlockIndex 累积，
      全部拼接后再 json.loads 得到工具入参；
    - contentBlockDelta.delta.text 也按 index 累积拼接。
    """
    blocks = {}   # index -> {"text","input_buf","tool_use_id","tool_name"}
    order = []
    usage = {"inputTokens": 0, "outputTokens": 0, "totalTokens": 0}
    stop_reason = None

    def _block(idx):
        if idx not in blocks:
            blocks[idx] = {"text": "", "input_buf": "", "tool_use_id": None, "tool_name": None}
            order.append(idx)
        return blocks[idx]

    for event in stream:
        if not isinstance(event, dict) or not event:
            continue
        etype, body = next(iter(event.items()))
        body = body or {}

        if etype in _STREAM_ERROR_EVENTS:
            msg = body.get("message") if isinstance(body, dict) else str(body)
            raise HarnessStreamError(f"{etype}: {msg}")

        if etype == "messageStart":
            continue
        if etype == "contentBlockStart":
            idx = body.get("contentBlockIndex", len(order))
            b = _block(idx)
            tu = (body.get("start") or {}).get("toolUse")
            if tu:
                b["tool_use_id"] = tu.get("toolUseId")
                b["tool_name"] = tu.get("name")
        elif etype == "contentBlockDelta":
            idx = body.get("contentBlockIndex", order[-1] if order else 0)
            b = _block(idx)
            delta = body.get("delta") or {}
            if delta.get("text") is not None:
                b["text"] += delta["text"]
            tu = delta.get("toolUse")
            if tu and tu.get("input") is not None:
                b["input_buf"] += tu["input"]
        elif etype == "contentBlockStop":
            continue
        elif etype == "messageStop":
            stop_reason = body.get("stopReason")
        elif etype == "metadata":
            u = body.get("usage") or {}
            for k in usage:
                if isinstance(u.get(k), int):
                    usage[k] += u[k]

    # 按出现顺序重建 assistant 消息内容 + 抽出 tool_uses / 文本
    content = []
    tool_uses = []
    text_parts = []
    for idx in order:
        b = blocks[idx]
        if b["tool_use_id"]:
            parsed = {}
            buf = b["input_buf"]
            if buf.strip():
                try:
                    parsed = json.loads(buf)
                except json.JSONDecodeError:
                    parsed = {"_raw": buf}  # 防御：片段拼接后仍非法 JSON
            content.append({"toolUse": {
                "name": b["tool_name"], "toolUseId": b["tool_use_id"],
                "input": parsed, "type": "tool_use",
            }})
            tool_uses.append({"toolUseId": b["tool_use_id"], "name": b["tool_name"], "input": parsed})
        elif b["text"]:
            content.append({"text": b["text"]})
            text_parts.append(b["text"])

    return {
        "text": "".join(text_parts),
        "tool_uses": tool_uses,
        "assistant_message": {"role": "assistant", "content": content},
        "usage": usage,
        "stop_reason": stop_reason,
    }


# --------------------------------------------------------------------------- #
# 工具执行 + invoke 回路
# --------------------------------------------------------------------------- #
def _execute_tool(tool_use, deps, memory_id, doc_name):
    """执行一个 inline_function toolUse，返回 (result_text, status)。

    记忆分区由 (scope, doc_name) 决定（见 memory_tools），与 harness 的 runtimeSessionId 解耦。
    """
    name = tool_use.get("name")
    args = tool_use.get("input") or {}
    try:
        if name == "recall_lessons":
            scope = args.get("scope", "strat")
            lessons = memory_tools.recall_lessons(
                scope, memory_id, config.ACTOR_ID, doc_name=doc_name, client=deps.memory_client)
            return json.dumps({"lessons": lessons}, ensure_ascii=False), "success"
        if name == "record_lesson":
            scope = args.get("scope", "tact")
            text = args.get("text", "")
            memory_tools.record_lesson(
                scope, text, memory_id, config.ACTOR_ID, doc_name=doc_name, client=deps.memory_client)
            return json.dumps({"status": "recorded", "scope": scope}, ensure_ascii=False), "success"
        return json.dumps({"error": f"unknown tool: {name}"}, ensure_ascii=False), "error"
    except Exception as exc:  # 工具失败不应中断回路——回传错误让 agent 决策
        return json.dumps({"error": str(exc)}, ensure_ascii=False), "error"


def _build_invoke_kwargs(deps, messages, session_id, mode):
    """按模式构造 invoke 入参：
    - none    : extractor harness（无记忆），override 自包含无工具提示、skills=[]、不带 tools。
    - custom  : extractor harness，scope-extract 技能 + record/recall 工具（客户端回路→customMem）。
    - episodic: extractor_ep harness（绑定 episodicMem），依赖其烤入的 native 技能/提示，不 override。
    """
    kwargs = {
        "harnessArn": _harness_arn_for_mode(mode, deps.deployed),
        "runtimeSessionId": session_id,
        "messages": messages,
        "actorId": config.ACTOR_ID,
        "maxIterations": 30,
        "timeoutSeconds": 900,
    }
    if mode == "none":
        kwargs["systemPrompt"] = [{"text": _none_system_prompt(deps)}]
        kwargs["skills"] = []
    elif mode == "custom":
        kwargs["systemPrompt"] = [{"text": deps.system_prompt}]
        kwargs["skills"] = [{"path": config.SKILL_PATH}]
        kwargs["tools"] = deps.harness_config.get("tools", [])
    # episodic: 不 override，用 extractor_ep 烤入的 native 技能 + episodic 提示 + episodicMem
    return kwargs


def _run_invoke_loop(deps, messages, session_id, memory_id, mode, usage, doc_name=None):
    """反复 invoke（同一 runtimeSessionId 续调）直到某轮无待响应 toolUse，返回 (final_text, loops)。

    每轮：invoke -> 消费流 -> 追加 assistant 消息 -> 若有 toolUse 则执行工具、追加 toolResult
    用户消息、continue；否则记录最终文本并结束。
    """
    loops = 0
    final_text = ""
    while loops < _MAX_CLIENT_LOOPS:
        loops += 1
        resp = deps.invoke_harness(**_build_invoke_kwargs(deps, messages, session_id, mode))
        consumed = _consume_stream(resp["stream"])
        for k in usage:
            usage[k] += consumed["usage"].get(k, 0)
        messages.append(consumed["assistant_message"])

        if consumed["tool_uses"]:
            tool_result_blocks = []
            for tu in consumed["tool_uses"]:
                text, status = _execute_tool(tu, deps, memory_id, doc_name)
                tool_result_blocks.append({"toolResult": {
                    "toolUseId": tu["toolUseId"],
                    "content": [{"text": text}],
                    "status": status,
                }})
            messages.append({"role": "user", "content": tool_result_blocks})
            continue

        final_text = consumed["text"]
        break
    return final_text, loops


# --------------------------------------------------------------------------- #
# 最终文本解析 + 合规门禁
# --------------------------------------------------------------------------- #
def _array_ending_at(text, end):
    """在以 text[end]==']' 为收尾的前提下，尝试对其前的每个 '[' 起点解析 JSON 数组，
    取**最早**能解析成非空 list 的片段（对散文里的杂散方括号鲁棒：草稿/散文起点会解析失败）。"""
    starts = [m.start() for m in re.finditer(r"\[", text) if m.start() < end]
    for s in starts:
        try:
            val = json.loads(text[s:end + 1])
            if isinstance(val, list) and val:
                return val
        except json.JSONDecodeError:
            continue
    return None


def _extract_json_array(text):
    """健壮提取最终 JSON 数组，适配冗长反思输出（散文 + 草稿数组 + 杂散括号 + ```json``` 围栏）：
    从右侧每个 ']' 出发回溯匹配的 '['，返回最先解析成功的非空 list。"""
    text = (text or "").strip()
    # 快路径：整体或最后一个 ```json``` 块直接就是数组
    fenced = [m.group(1).strip()
              for m in re.finditer(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)]
    for cand in [*reversed(fenced), text]:
        try:
            val = json.loads(cand)
            if isinstance(val, list):
                return val
        except json.JSONDecodeError:
            pass
    # 通用路径：从最靠后的 ']' 逐个回溯（合法 JSON 情形）
    ends = [m.start() for m in re.finditer(r"\]", text)]
    for end in reversed(ends):
        arr = _array_ending_at(text, end)
        if arr is not None:
            return arr
    # 兜底：模型常在字符串值内混入未转义引号（如原文里的"液封"）导致 JSON 非法，
    # 用 json_repair 救回 first '[' .. last ']' 区间。
    s, e = text.find("["), text.rfind("]")
    if s != -1 and e != -1 and e > s:
        try:
            from json_repair import repair_json
            val = repair_json(text[s:e + 1], return_objects=True)
            if isinstance(val, list):
                return [r for r in val if isinstance(r, dict)]
        except Exception:
            pass
    return []


def _parse_final(text):
    """解析最终文本：JSON 数组 + 末行 __META__ {"revision_count":N}。返回 (extracted, revision_count)。"""
    text = text or ""
    revision_count = None
    body = text
    if _META_MARKER in text:
        body, meta = text.rsplit(_META_MARKER, 1)
        try:
            meta_obj = json.loads(meta.strip())
            if isinstance(meta_obj, dict):
                revision_count = meta_obj.get("revision_count")
        except json.JSONDecodeError:
            revision_count = None
    return _extract_json_array(body), revision_count


def _passes_gate(extracted):
    """兜底门禁：JSON 合法(list) / 条目数>0 / 每条必填字段非空。"""
    if not isinstance(extracted, list) or len(extracted) == 0:
        return False
    for item in extracted:
        if not isinstance(item, dict):
            return False
        for field in REQUIRED_FIELDS:
            val = item.get(field)
            if val is None or (isinstance(val, str) and val.strip() == ""):
                return False
    return True


# --------------------------------------------------------------------------- #
# 主入口
# --------------------------------------------------------------------------- #
def run_extraction(doc_name, memory_mode, warm=False, deps=None) -> dict:
    """跑一次抽取，采集指标并落盘，返回 run dict。

    memory_mode: none | episodic | custom
      - none: 不带 memory、不启用工具回路
      - episodic: 选 EPISODIC_MEMORY_ID（episodic 记忆由 harness 资源侧原生托管）
      - custom: 选 CUSTOM_MEMORY_ID，并启用 recall/record inline_function 工具回路
    """
    deps = _resolve_deps(deps)
    if deps.corpus is None:
        raise RuntimeError(
            "corpus 模块缺失：需 src.corpus（load_doc_text/load_gt/list_docs）或通过 deps 注入。")

    doc_text = deps.corpus.load_doc_text(doc_name)
    try:
        gt = deps.corpus.load_gt(doc_name)
    except Exception:
        gt = []  # TODO: GT 缺失时评分不可用，落盘 num_gt=0

    memory_id = _memory_id_for_mode(memory_mode, deps.deployed)
    session_id = _new_session_id()

    messages = [{"role": "user", "content": [{"text": doc_text}]}]
    usage = {"inputTokens": 0, "outputTokens": 0, "totalTokens": 0}

    t0 = time.monotonic()
    final_text, loops = _run_invoke_loop(
        deps, messages, session_id, memory_id, memory_mode, usage, doc_name=doc_name)
    extracted, revision_count = _parse_final(final_text)

    # 合规门禁：仅兜底补一次（补 invoke 仍走完整工具回路）
    gate_retry = False
    if not _passes_gate(extracted):
        gate_retry = True
        messages.append({"role": "user", "content": [{"text": _GATE_RETRY_PROMPT}]})
        final_text2, loops2 = _run_invoke_loop(
            deps, messages, session_id, memory_id, memory_mode, usage, doc_name=doc_name)
        loops += loops2
        extracted2, revision_count2 = _parse_final(final_text2)
        if _passes_gate(extracted2):
            extracted, revision_count, final_text = extracted2, revision_count2, final_text2

    elapsed = time.monotonic() - t0
    passed = _passes_gate(extracted)

    # 评分（scorer 缺失/异常不阻断落盘）
    coverage = accuracy = None
    if deps.scorer is not None:
        try:
            result = deps.scorer.score(extracted, gt, deps.judge_fn)
            if isinstance(result, dict):
                coverage = result.get("coverage")
                accuracy = result.get("accuracy")
        except Exception:
            pass  # TODO: 上线接真实 scorer 后校对返回结构

    run = {
        "run_id": uuid4().hex,
        "ts": datetime.now(timezone.utc).isoformat(),
        "doc_name": doc_name,
        "memory_mode": memory_mode,
        "warm": int(bool(warm)),
        "revision_count": revision_count,
        "elapsed_sec": round(elapsed, 3),
        "input_tokens": usage["inputTokens"],
        "output_tokens": usage["outputTokens"],
        "total_tokens": usage["totalTokens"],
        "coverage": coverage,
        "accuracy": accuracy,
        "self_review_pass": int(bool(passed)),
        "num_extracted": len(extracted),
        "num_gt": len(gt) if isinstance(gt, list) else 0,
        "extracted_json": json.dumps(extracted, ensure_ascii=False),
        "notes": json.dumps({
            "session_id": session_id,
            "memory_id": memory_id,
            "client_invoke_loops": loops,
            "gate_retry": gate_retry,
        }, ensure_ascii=False),
    }
    deps.runstore.insert_run(run, path=deps.db_path)
    return run


# --------------------------------------------------------------------------- #
# UI 便捷封装
# --------------------------------------------------------------------------- #
def clear_memory_for_mode(memory_mode, deps=None, scope=None, doc_names=None) -> int:
    """清除指定模式对应 memory 下该 actor 的记忆（none 模式无 memory，返回 0）。

    tact 记忆按文档分区，需 doc_names 才能定位；未提供时从 corpus 全量文档推导。
    """
    deps = _resolve_deps(deps)
    memory_id = _memory_id_for_mode(memory_mode, deps.deployed)
    if not memory_id:
        return 0
    if doc_names is None and deps.corpus is not None:
        try:
            doc_names = [d["name"] for d in deps.corpus.list_docs()]
        except Exception:
            doc_names = []
    return memory_tools.clear_memory(
        memory_id, config.ACTOR_ID, doc_names=doc_names, client=deps.memory_client, scope=scope)


def read_lessons(scope, deps=None, doc_name=None) -> list:
    """读取 custom memory 中某 scope 已沉淀的经验，供 UI 规则面板展示。

    tact 为按文档分区，需传 doc_name；strat 为全局。
    """
    deps = _resolve_deps(deps)
    memory_id = deps.deployed.get("CUSTOM_MEMORY_ID")
    if scope == "tact" and not doc_name:
        return []  # tact 需指定文档
    return memory_tools.read_all_lessons(
        scope, memory_id, config.ACTOR_ID, doc_name=doc_name, client=deps.memory_client)
