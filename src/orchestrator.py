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
        return _stream_consume_retry(deps, kwargs)["text"]
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


_TRANSIENT = ("502", "500", "503", "runtimeclienterror", "throttl",
              "serviceunavailable", "service unavailable", "timed out", "timeout")


def _stream_consume_retry(deps, kwargs, retries=6, base_sleep=5):
    """invoke_harness + 消费流，对瞬时错误（502/5xx/限流）重试；MaxTokens 类不重试（上抛）。"""
    last = None
    for i in range(retries):
        try:
            return _consume_stream(deps.invoke_harness(**kwargs)["stream"])
        except Exception as e:
            s = str(e).lower()
            if "maximum token" in s or "maxtokens" in s:
                raise
            last = e
            if not any(t in s for t in _TRANSIENT) or i == retries - 1:
                raise
            time.sleep(base_sleep * (i + 1))
    raise last


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

    # 评分（scorer 缺失/异常不阻断落盘）；judge token 单列
    coverage = accuracy = None
    judge_usage = {"inputTokens": 0, "outputTokens": 0, "totalTokens": 0}
    if deps.scorer is not None:
        def _judge(prompt):
            jt, ju = _invoke_llm(deps, _JUDGE_SYSTEM, prompt, max_tokens=8192)
            for k in judge_usage:
                judge_usage[k] += ju.get(k, 0)
            return jt
        try:
            result = deps.scorer.score(extracted, gt, _judge)
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
            "actor_id": config.ACTOR_ID,
            "client_invoke_loops": loops,
            "gate_retry": gate_retry,
            "judge_total_tokens": judge_usage["totalTokens"],
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


# =========================================================================== #
# V2：单变量消融（同一 harness/抽取提示/单次 invoke；唯一变量=是否注入并沉淀记忆）
# 记忆改为 canonical 规则集 + consolidation（合并/去重/控体量，借 SEMANTIC 两步范式）
# =========================================================================== #
_REFLECT_SYS = (
    "你是「抽取经验提炼器」。给你一次从工业技术文档抽取出的结构化结果，"
    "请总结出**可复用于同类文档**的抽取规则（要点式、每条可操作、只讲规则不讲具体数值、≤10 条）。只输出规则要点。"
)
_CONSOLIDATE_SYS = (
    "你是「规则库维护器」。把「现有规则集」与「本轮新提炼规则」合并成**一份规范规则集**："
    "去重、合并同类项、保持每条可操作、总数 ≤15 条、不要堆叠版本或近重复项。只输出合并后的最终规则集（编号列表）。"
)

# ---- opt 变体（据 §3.4 误差分析：补易漏类别 + 抑制过度拆分；不覆盖上面 V2 原版）----
_OPT_EXTRACT_ADDON = (
    "\n## 本轮强化要求（务必遵守）\n"
    "1. **覆盖常被漏抽的类别**：无损检测(RT/PT/UT 的比例/合格级别/标准编号)、"
    "安装环境条件(温度/风速/风压/雪压/地震)、主要受压元件、焊接接头——逐条抽取，勿遗漏。\n"
    "2. **粒度对齐 GT**：默认**一条原文=一条记录**；仅当一句原文确含多个**相互独立**的指标时才拆分；"
    "**严禁把同一句过度拆成大量细条**（过度拆分会降低精确率与覆盖率）。"
)
_REFLECT_SYS_OPT = (
    "你是「抽取经验提炼器」。总结**可复用于同类文档**的抽取规则（≤10 条、可操作、只讲规则不讲具体值）。"
    "规则要**帮助覆盖易漏类别（无损检测/安装环境/主要受压元件/焊接）**，并**控制拆分粒度（默认一原文一记录、勿鼓励过度拆分）**。只输出规则要点。"
)
_CONSOLIDATE_SYS_OPT = (
    "你是「规则库维护器」。合并「现有规则集」与「本轮新提炼规则」成**一份规范规则集**（去重、≤15 条、可操作）。"
    "**要点**：兼顾①覆盖易漏类别（无损检测/安装环境/受压元件/焊接）②粒度适中——"
    "若已有规则过度强调'拆分/独立成条'，改写为'粒度对齐 GT、默认一原文一记录'。只输出最终规则集（编号列表）。"
)

# ---- opt v2 变体（据 reflection 误差分析：漏抽主体是"散文/流程/报告/定性类要求"——不符合定量三元组
#      → 显式指示把非定量要求也映射进 指标名称/指标特征；schema 不变）----
_OPT2_EXTRACT_ADDON = (
    "\n## 本轮强化要求（务必遵守）\n"
    "1. **不要只抽定量指标**：除带数值/规格的技术指标外，**定性要求、流程/工序要求、报告/测量要求、"
    "待确认/待细化事项**同样要逐条抽取。做法——把「要求类型」放入『指标名称』、「要求内容」放入『指标特征』"
    "（即使没有数值也要成条）。示例：\n"
    "   - “外观颜色及喷涂 LOGO 须与甲方确认” → 指标名称=外观颜色与喷涂确认；指标特征=须与甲方确认\n"
    "   - “真空度测量报告 / 真空度测量要求” → 指标名称=真空度测量；指标特征=需按要求测量并提供报告\n"
    "   - “外部油漆等工序” → 指标名称=外部油漆工序；指标特征=按工序要求执行\n"
    "   - “承制单位细化设计…提供全套地脚螺栓” → 指标名称=地脚螺栓；指标特征=提供全套、按土建尺寸细化\n"
    "2. **覆盖常被漏抽的类别**：真空度/真空度测量、无损检测(RT/PT/UT 比例/合格级别/标准)、"
    "安装环境(温度/风/雪/地震)、主要受压元件、阀门仪表、管口接管/法兰、材料材质——逐条抽取，勿遗漏。\n"
    "3. **粒度对齐 GT**：默认**一条原文=一条记录**；仅当一句确含多个**相互独立**的指标时才拆；严禁过度拆分。"
)
_REFLECT_SYS_OPT2 = (
    "你是「抽取经验提炼器」。总结**可复用于同类文档**的抽取规则（≤10 条、可操作、只讲规则不讲具体值）。"
    "规则必须强调：①**非定量要求也要抽**（定性/流程/工序/报告/待确认类，用 指标名称=要求类型、指标特征=要求内容）；"
    "②覆盖易漏类别（真空度测量/无损检测/安装环境/受压元件/阀门仪表/管口接管/材料）；"
    "③粒度对齐 GT（默认一原文一记录、勿过度拆分）。只输出规则要点。"
)
_CONSOLIDATE_SYS_OPT2 = (
    "你是「规则库维护器」。合并「现有规则集」与「本轮新提炼规则」成**一份规范规则集**（去重、≤15 条、可操作）。"
    "**必须保留**：①非定量要求（定性/流程/报告/待确认）也要抽、映射进 指标名称/指标特征；"
    "②易漏类别覆盖（真空度测量/无损检测/安装环境/受压元件/阀门仪表/管口接管/材料）；"
    "③粒度对齐 GT（默认一原文一记录）。只输出最终规则集（编号列表）。"
)


def _v2_extract_system(deps, canonical: str) -> str:
    """V2 抽取系统提示：schema+红线（取自 system-prompt.md 的"工作方式"之前）+ 内联反思 + (可选)注入已积累规则。"""
    base = (deps.system_prompt or "").split("## 工作方式")[0].rstrip()
    p = base + _NONE_REFLECT
    if canonical.strip():
        p += ("\n## 已积累的抽取经验（跨文档规则，务必逐条应用）\n" + canonical.strip() + "\n")
    return p


def _invoke_llm(deps, system_text, user_text, max_tokens=32768):
    """单次 invoke（override 提示、无 skill、**显式 tools=[] 禁用 harness 烤入的工具**、无工具回路），返回 (text, usage)。

    注意：抽取输出可能很大（实测 ~25k output tokens），max_tokens 需给足，否则触发
    MaxTokensReached（截断报错）。默认 32768。
    """
    kwargs = {
        "harnessArn": deps.deployed["HARNESS_ARN"],
        "runtimeSessionId": _new_session_id(),
        "messages": [{"role": "user", "content": [{"text": user_text}]}],
        "systemPrompt": [{"text": system_text}],
        "skills": [],
        "tools": [],   # 禁用 extractor 烤入的 record/recall 工具（v2 不走工具回路）
        "model": {"bedrockModelConfig": {"modelId": config.MODEL_ID, "temperature": 0, "maxTokens": max_tokens}},
        "maxIterations": 2,
        "timeoutSeconds": 900,
    }
    try:
        consumed = _stream_consume_retry(deps, kwargs)
        return consumed["text"], consumed["usage"]
    except Exception as e:  # 含 HarnessStreamError 与 botocore EventStreamError
        # MaxTokensReached 等截断：返回空文本让上层门禁处理（一般是 max_tokens 给少了）
        if "maximum token" in str(e).lower() or "maxtokens" in str(e).lower():
            return "", {"inputTokens": 0, "outputTokens": max_tokens, "totalTokens": max_tokens}
        raise


def run_ablation(doc_name, use_memory, deps=None, db_path=None, opt=False) -> dict:
    """V2 单变量消融：唯一变量=use_memory。其余（harness/抽取提示/单次invoke/模型）全相同。

    use_memory=True：抽取前注入 canonical 规则集；抽取后 反思→consolidation→更新 canonical。
    use_memory=False：纯抽取基线。
    opt：优化提示词变体——False=原版；True/"v1"=补易漏类别+抑制过度拆分；
         "v2"=在 v1 基础上进一步"非定量要求(定性/流程/报告/待确认)也抽"（据 reflection 误差分析）。
    """
    deps = _resolve_deps(deps)
    if deps.corpus is None:
        raise RuntimeError("corpus 模块缺失")
    doc_text = deps.corpus.load_doc_text(doc_name)
    try:
        gt = deps.corpus.load_gt(doc_name)
    except Exception:
        gt = []
    mem_id = deps.deployed.get("CUSTOM_MEMORY_ID")
    usage = {"inputTokens": 0, "outputTokens": 0, "totalTokens": 0}

    def _acc(u):
        for k in usage:
            usage[k] += u.get(k, 0)

    # 选择 opt 变体的三段提示词 + 落库标签
    if opt == "v2":
        _addon, _refl_sys, _consol_sys, _vtag = _OPT2_EXTRACT_ADDON, _REFLECT_SYS_OPT2, _CONSOLIDATE_SYS_OPT2, "v2-opt2"
    elif opt:
        _addon, _refl_sys, _consol_sys, _vtag = _OPT_EXTRACT_ADDON, _REFLECT_SYS_OPT, _CONSOLIDATE_SYS_OPT, "v2-opt"
    else:
        _addon, _refl_sys, _consol_sys, _vtag = "", _REFLECT_SYS, _CONSOLIDATE_SYS, "v2"

    canonical = ""
    if use_memory:
        canonical = memory_tools.read_canonical(mem_id, config.ACTOR_ID, client=deps.memory_client)

    ext_sys = _v2_extract_system(deps, canonical) + _addon
    t0 = time.monotonic()
    text, u = _invoke_llm(deps, ext_sys, doc_text, max_tokens=32768)
    _acc(u)
    extracted, revision_count = _parse_final(text)
    first_pass = _passes_gate(extracted)   # 首次模型输出是否合规(与门禁后区分)
    gate_retry = False
    if not first_pass:  # 兜底补一次
        gate_retry = True
        text2, u2 = _invoke_llm(deps, ext_sys,
                                doc_text + "\n\n请只输出合法 JSON 数组 + __META__ 行。", max_tokens=32768)
        _acc(u2)
        e2, r2 = _parse_final(text2)
        if _passes_gate(e2):
            extracted, revision_count = e2, r2
    elapsed = time.monotonic() - t0
    passed = _passes_gate(extracted)

    # 评分：单列 judge token（review 要求：extraction-path 与 judge 成本分开计）
    coverage = accuracy = precision = f1 = None
    judge_usage = {"inputTokens": 0, "outputTokens": 0, "totalTokens": 0}
    if deps.scorer is not None:
        def _judge(prompt):
            jt, ju = _invoke_llm(deps, _JUDGE_SYSTEM, prompt, max_tokens=8192)
            for k in judge_usage:
                judge_usage[k] += ju.get(k, 0)
            return jt
        try:
            res = deps.scorer.score(extracted, gt, _judge)
            coverage, accuracy = res.get("coverage"), res.get("accuracy")
            precision, f1 = res.get("precision"), res.get("f1")
        except Exception:
            pass

    # 记忆沉淀：反思本轮 → 与现有 canonical 合并（consolidation）
    candidate = new_canon = ""
    if use_memory and extracted:
        candidate, u = _invoke_llm(deps, _refl_sys,
                                   json.dumps(extracted, ensure_ascii=False), max_tokens=2048)
        _acc(u)
        new_canon, u = _invoke_llm(deps, _consol_sys,
                                   f"现有规则集：\n{canonical or '（空）'}\n\n本轮新提炼规则：\n{candidate}",
                                   max_tokens=3072)
        _acc(u)
        if new_canon.strip():
            memory_tools.write_canonical(mem_id, config.ACTOR_ID, new_canon.strip(),
                                         client=deps.memory_client)

    run = {
        "run_id": uuid4().hex, "ts": datetime.now(timezone.utc).isoformat(),
        "doc_name": doc_name, "memory_mode": ("mem" if use_memory else "nomem"),
        "warm": int(bool(use_memory)), "revision_count": revision_count,
        "elapsed_sec": round(elapsed, 3), "input_tokens": usage["inputTokens"],
        "output_tokens": usage["outputTokens"], "total_tokens": usage["totalTokens"],
        "coverage": coverage, "accuracy": accuracy, "self_review_pass": int(bool(passed)),
        "num_extracted": len(extracted), "num_gt": len(gt) if isinstance(gt, list) else 0,
        "extracted_json": json.dumps(extracted, ensure_ascii=False),
        "notes": json.dumps({"variant": _vtag,
                             "precision": precision, "f1": f1,
                             "canonical_in_len": len(canonical), "canonical_out_len": len(new_canon),
                             "first_output_pass": bool(first_pass), "gate_retry": gate_retry,
                             "judge_total_tokens": judge_usage["totalTokens"],
                             "extraction_path_tokens": usage["totalTokens"]},
                            ensure_ascii=False),
    }
    deps.runstore.insert_run(run, path=db_path)
    return run


# =========================================================================== #
# LLM 检查器（对比 GT 自动产出可迁移反馈）→ 写进记忆 → 下一次抽取注入。
# 模拟真实回路：大模型质检 / 人类审阅对比标准答案给反馈，记忆负责捕获并复用。
# GT 只进"检查器"这一步，绝不进抽取器。
# =========================================================================== #
_CHECKER_SYS = (
    "你是抽取质检专家。给你【某次抽取结果】和【标准答案 GT】。对比两者，产出**可迁移、指导未来抽取**的改进反馈"
    "（自然语言要点，≤10 条，每条可操作）。重点：①指出**系统性漏抽的类别/类型**（是哪一类东西整片没抽，如无损检测/环境/散文式要求）；"
    "②指出**粒度问题**（过度拆分/该合并）；③给出**规则性、可复用**的纠正指引（如'非定量要求也要抽、映射进某字段'）。"
    "**不要逐条罗列标准答案里的具体条目**——要给出下次遇到同类文档能照做的规则。只输出反馈要点。"
)


def run_llm_feedback(doc_name, deps=None, db_path=None) -> dict:
    """LLM 检查器反馈被记忆捕获的效果验证（模拟大模型质检/人类反馈回路）。

    步骤：①基线抽取(无记忆)→②LLM 检查器对比 GT 产出可迁移反馈→③反馈写进记忆(canonical)→
    ④用**基线提示词**重新抽取、注入该反馈记忆→⑤评分。GT 只进检查器，不进抽取器。
    落库两条：llm_fb_r1(基线) / llm_fb_r2(注入检查器反馈后)，notes 存反馈全文。
    """
    deps = _resolve_deps(deps)
    doc_text = deps.corpus.load_doc_text(doc_name)
    try:
        gt = deps.corpus.load_gt(doc_name)
    except Exception:
        gt = []
    mem_id = deps.deployed.get("CUSTOM_MEMORY_ID")
    base_sys = _v2_extract_system(deps, "")   # 基线抽取提示（无 opt 强化）
    pair_id = uuid4().hex

    def _extract(system_text):
        u_acc = {"inputTokens": 0, "outputTokens": 0, "totalTokens": 0}
        text, u = _invoke_llm(deps, system_text, doc_text, max_tokens=32768)
        for k in u_acc:
            u_acc[k] += u.get(k, 0)
        ex, rev = _parse_final(text)
        fp = _passes_gate(ex)
        gr = not fp
        if gr:
            t2, u2 = _invoke_llm(deps, system_text, doc_text + "\n\n请只输出合法 JSON 数组 + __META__ 行。", max_tokens=32768)
            for k in u_acc:
                u_acc[k] += u2.get(k, 0)
            e2, r2 = _parse_final(t2)
            if _passes_gate(e2):
                ex, rev = e2, r2
        return ex, rev, u_acc, fp, gr

    def _score(ex):
        cov = acc = prec = f1 = None; jt = 0
        if deps.scorer is not None and ex:
            box = {"t": 0}
            def _j(prompt):
                jtxt, ju = _invoke_llm(deps, _JUDGE_SYSTEM, prompt, max_tokens=8192)
                box["t"] += ju.get("totalTokens", 0); return jtxt
            try:
                r = deps.scorer.score(ex, gt, _j)
                cov, acc, prec, f1 = r.get("coverage"), r.get("accuracy"), r.get("precision"), r.get("f1")
            except Exception:
                pass
            jt = box["t"]
        return cov, acc, prec, f1, jt

    def _persist(mode, ex, rev, u, cov, acc, prec, f1, jt, fp, gr, extra):
        run = {
            "run_id": uuid4().hex, "ts": datetime.now(timezone.utc).isoformat(),
            "doc_name": doc_name, "memory_mode": mode, "warm": 0, "revision_count": rev,
            "elapsed_sec": 0.0, "input_tokens": u["inputTokens"], "output_tokens": u["outputTokens"],
            "total_tokens": u["totalTokens"], "coverage": cov, "accuracy": acc,
            "self_review_pass": int(_passes_gate(ex)), "num_extracted": len(ex),
            "num_gt": len(gt) if isinstance(gt, list) else 0,
            "extracted_json": json.dumps(ex, ensure_ascii=False),
            "notes": json.dumps({"variant": "llm-feedback", "pair_id": pair_id, "precision": prec,
                                 "f1": f1, "judge_total_tokens": jt, "first_output_pass": bool(fp),
                                 "gate_retry": gr, **extra}, ensure_ascii=False),
        }
        deps.runstore.insert_run(run, path=db_path)
        return run

    # 清空 canon，保证注入的就是本轮检查器反馈
    c = memory_tools._client(deps.memory_client)
    sid = memory_tools.canon_session(config.ACTOR_ID)
    for ev in memory_tools._list_all_events(c, mem_id, config.ACTOR_ID, sid):
        if ev.get("eventId"):
            c.delete_event(memoryId=mem_id, actorId=config.ACTOR_ID, sessionId=sid, eventId=ev["eventId"])

    # ① 基线抽取
    ex1, rev1, u1, fp1, gr1 = _extract(base_sys)
    cov1, acc1, prec1, f1_1, jt1 = _score(ex1)
    _persist("llm_fb_r1", ex1, rev1, u1, cov1, acc1, prec1, f1_1, jt1, fp1, gr1, {})

    # ② LLM 检查器对比 GT 产出可迁移反馈
    feedback, _ = _invoke_llm(
        deps, _CHECKER_SYS,
        f"【某次抽取结果】\n{json.dumps(ex1, ensure_ascii=False)}\n\n【标准答案 GT】\n{json.dumps(gt, ensure_ascii=False)}",
        max_tokens=2048,
    )
    # ③ 反馈写进记忆
    memory_tools.write_canonical(mem_id, config.ACTOR_ID,
                                 "【质检反馈·务必逐条应用】\n" + (feedback or "").strip(), client=c)

    # ④ 基线提示词 + 注入检查器反馈记忆，重新抽取
    canonical = memory_tools.read_canonical(mem_id, config.ACTOR_ID, client=c)
    ex2, rev2, u2, fp2, gr2 = _extract(_v2_extract_system(deps, canonical))
    cov2, acc2, prec2, f2_2, jt2 = _score(ex2)
    _persist("llm_fb_r2", ex2, rev2, u2, cov2, acc2, prec2, f2_2, jt2, fp2, gr2,
             {"feedback": feedback or "", "feedback_len": len(feedback or "")})

    return {"pair_id": pair_id, "feedback": feedback,
            "r1": {"coverage": cov1, "precision": prec1, "f1": f1_1, "num_extracted": len(ex1)},
            "r2": {"coverage": cov2, "precision": prec2, "f1": f2_2, "num_extracted": len(ex2)}}


# =========================================================================== #
# Reflection（Level-2 验证循环）：抽取→批评者(看原文+本次输出,不看GT)→带批评重抽同一篇
# 用于回答：用户此前观察到"有效"的 reflection 模式，在我们 harness 里能否复现？
# 与 run_ablation(mem) 的关键差异：反馈是"针对本次输出的具体整改意见"(而非抽象规则)、
# 由外部批评者产生(而非自省)、立刻作用于同一篇重抽(而非存给未来)。
# =========================================================================== #
_CRITIC_SYS = (
    "你是严格的抽取质检员。给你【原始技术文档】和【某次从中抽取的结构化结果】。"
    "在**不知道标准答案**的前提下，仅对照原文找出这次抽取的问题："
    "①漏抽——原文出现但结果里没有的指标/部件/类别（尤其无损检测RT/PT/UT、安装环境条件、"
    "主要受压元件、焊接接头、材料分层等）；②拆分不当——同一条原文被过度拆成多条、或本应分开的被合并；"
    "③字段错配——设备主体/设备部件/指标名称/指标特征/原文 明显对不上。"
    "输出一份**具体、可操作**的整改清单（指名漏了哪些原文片段/类别、哪些条目该合并或拆分），"
    "不要重写抽取结果本身。你看不到标准答案，只能对照原文判断。"
)


def run_reflection(doc_name, deps=None, db_path=None) -> dict:
    """Level-2 验证循环单次运行：round1 单遍抽取 → 批评(无GT) → round2 带批评重抽同一篇。

    两轮用同一评分器打分（GT 仅用于评分，绝不进 agent 上下文）。落库两条：refl_r1 / refl_r2，
    共享 pair_id，便于成对比较 round2 相对 round1 的增量。
    """
    deps = _resolve_deps(deps)
    if deps.corpus is None:
        raise RuntimeError("corpus 模块缺失")
    doc_text = deps.corpus.load_doc_text(doc_name)
    try:
        gt = deps.corpus.load_gt(doc_name)
    except Exception:
        gt = []
    ext_sys = _v2_extract_system(deps, "")   # == nomem 基线抽取提示（无记忆注入）
    pair_id = uuid4().hex

    def _extract(user_text):
        usage = {"inputTokens": 0, "outputTokens": 0, "totalTokens": 0}
        text, u = _invoke_llm(deps, ext_sys, user_text, max_tokens=32768)
        for k in usage:
            usage[k] += u.get(k, 0)
        extracted, rev = _parse_final(text)
        first_pass = _passes_gate(extracted)
        gate_retry = not first_pass
        if gate_retry:
            text2, u2 = _invoke_llm(deps, ext_sys,
                                    user_text + "\n\n请只输出合法 JSON 数组 + __META__ 行。", max_tokens=32768)
            for k in usage:
                usage[k] += u2.get(k, 0)
            e2, r2 = _parse_final(text2)
            if _passes_gate(e2):
                extracted, rev = e2, r2
        return extracted, rev, usage, first_pass, gate_retry

    def _score(extracted):
        cov = acc = prec = f1 = None
        ju_total = 0
        if deps.scorer is not None and extracted:
            box = {"t": 0}
            def _judge(prompt):
                jt, ju = _invoke_llm(deps, _JUDGE_SYSTEM, prompt, max_tokens=8192)
                box["t"] += ju.get("totalTokens", 0)
                return jt
            try:
                res = deps.scorer.score(extracted, gt, _judge)
                cov, acc = res.get("coverage"), res.get("accuracy")
                prec, f1 = res.get("precision"), res.get("f1")
            except Exception:
                pass
            ju_total = box["t"]
        return cov, acc, prec, f1, ju_total

    def _persist(mode, extracted, rev, usage, cov, acc, prec, f1, ju_total, first_pass, gate_retry, extra):
        run = {
            "run_id": uuid4().hex, "ts": datetime.now(timezone.utc).isoformat(),
            "doc_name": doc_name, "memory_mode": mode, "warm": 0, "revision_count": rev,
            "elapsed_sec": 0.0, "input_tokens": usage["inputTokens"],
            "output_tokens": usage["outputTokens"], "total_tokens": usage["totalTokens"],
            "coverage": cov, "accuracy": acc, "self_review_pass": int(_passes_gate(extracted)),
            "num_extracted": len(extracted), "num_gt": len(gt) if isinstance(gt, list) else 0,
            "extracted_json": json.dumps(extracted, ensure_ascii=False),
            "notes": json.dumps({"variant": "reflection", "pair_id": pair_id,
                                 "precision": prec, "f1": f1, "judge_total_tokens": ju_total,
                                 "first_output_pass": bool(first_pass), "gate_retry": gate_retry,
                                 **extra}, ensure_ascii=False),
        }
        deps.runstore.insert_run(run, path=db_path)
        return run

    # ---- round 1：单遍抽取 ----
    ex1, rev1, u1, fp1, gr1 = _extract(doc_text)
    cov1, acc1, prec1, f1_1, jt1 = _score(ex1)
    _persist("refl_r1", ex1, rev1, u1, cov1, acc1, prec1, f1_1, jt1, fp1, gr1, {})

    # ---- 批评者：看原文 + round1 输出，不看 GT ----
    critique, uc = _invoke_llm(
        deps, _CRITIC_SYS,
        f"【原始技术文档】\n{doc_text}\n\n【本次抽取结果】\n{json.dumps(ex1, ensure_ascii=False)}",
        max_tokens=4096,
    )

    # ---- round 2：带批评重抽同一篇（唯一新增变量 = critique）----
    r2_user = (f"{doc_text}\n\n【你上一轮的抽取结果】\n{json.dumps(ex1, ensure_ascii=False)}\n\n"
               f"【质检整改意见（对照原文，未参考标准答案）】\n{critique}\n\n"
               "请据此重新抽取：补上漏抽的类别/条目、修正不当的拆分与字段错配。只输出合法 JSON 数组 + __META__ 行。")
    ex2, rev2, u2, fp2, gr2 = _extract(r2_user)
    cov2, acc2, prec2, f2_2, jt2 = _score(ex2)
    _persist("refl_r2", ex2, rev2, u2, cov2, acc2, prec2, f2_2, jt2, fp2, gr2,
             {"critique_len": len(critique or ""), "critique": critique or ""})

    return {
        "pair_id": pair_id,
        "r1": {"coverage": cov1, "precision": prec1, "f1": f1_1, "num_extracted": len(ex1)},
        "r2": {"coverage": cov2, "precision": prec2, "f1": f2_2, "num_extracted": len(ex2)},
    }
