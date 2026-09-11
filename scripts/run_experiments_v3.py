#!/usr/bin/env python3
"""V3: explicit self-review -> managed episodic memory -> single-page ablation.

The target extraction is a strict Memory on/off comparison:
- same user document
- same invocation-level system prompt
- same model and inference parameters
- skills and tools disabled
- fresh runtime session per condition

The only target-time variable is whether the Harness is bound to AgentCore Memory.
No GT or automated judge is used.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import boto3
from botocore.config import Config

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import config, corpus, orchestrator as O  # noqa: E402


SOURCE_PREFIX = "150方液氮罐技术要求"
TARGET_PREFIX = "2477080009简图-8.16"
WAIT_TIMEOUT_SECONDS = 1800
WAIT_INTERVAL_SECONDS = 30
OUTPUT_JSON = Path(__file__).resolve().parents[1] / "docs" / "memory-loop-v3-results.json"
OUTPUT_MARKDOWN = (
    Path(__file__).resolve().parents[1] / "docs" / "memory-loop-v3-results.md"
)

PHASE1_SYSTEM = """你是工业技术文档抽取任务的自审代理。
用户会提供一份文档。先在内部形成完整抽取草稿，再审查该草稿；不要输出草稿。
只输出一个合法 JSON 对象，不要 Markdown、标题、代码块或解释，严格使用：
{"self_review":{"coverage":{"发现":[],"结论":"..."},"omissions":{"发现":[],"结论":"..."},"format":{"发现":[],"结论":"..."},"granularity":{"发现":[],"结论":"..."},"next_actions":["..."]}}
你看不到标准答案，只能基于用户文档和已注入的历史经验审查。"""

PHASE2_SYSTEM = """你是工业技术文档抽取任务的修订代理。
读取用户提供的原始文档和 self_review，根据 next_actions 重新完成抽取。
只输出最终合法 JSON 数组；每条都含设备主体、设备部件、指标名称、指标特征、原文五个非空字段。
数组后另起一行输出 __META__ {"revision_count": N}。不要输出解释或 Markdown。
你看不到标准答案。"""

TARGET_SYSTEM = """你是工业技术文档信息抽取助手。
根据用户文档抽取所有可识别的技术要求/参数，每条输出设备主体、设备部件、指标名称、
指标特征、原文五个非空字段。先在内部自审覆盖、遗漏、格式和粒度，再只输出最终合法
JSON 数组，随后一行 __META__ {"revision_count":N}。只抽原文明确存在的信息，不臆造。"""

CLOSE_SYSTEM = "当前任务已经结束。只回复“任务已结束。”，不要继续抽取或解释。"


def new_session_id() -> str:
    return (uuid4().hex + uuid4().hex)[:40]


def deployed_resources() -> dict:
    state = json.loads(config.DEPLOYED_STATE_PATH.read_text(encoding="utf-8"))
    return state["targets"]["default"]["resources"]


def doc_name(prefix: str) -> str:
    return next(doc["name"] for doc in corpus.list_docs() if doc["name"].startswith(prefix))


def invoke(
    client,
    harness_arn: str,
    actor_id: str,
    session_id: str,
    system_prompt: str,
    user_text: str,
) -> dict:
    kwargs = {
        "harnessArn": harness_arn,
        "runtimeSessionId": session_id,
        "actorId": actor_id,
        "messages": [{"role": "user", "content": [{"text": user_text}]}],
        "systemPrompt": [{"text": system_prompt}],
        "skills": [],
        "tools": [],
        "model": {
            "bedrockModelConfig": {
                "modelId": config.MODEL_ID,
                "temperature": 0,
                "maxTokens": 32768,
            }
        },
        "maxIterations": 2,
        "timeoutSeconds": 900,
    }
    last_error = None
    for attempt in range(4):
        try:
            return O._consume_stream(client.invoke_harness(**kwargs)["stream"])
        except Exception as exc:
            last_error = exc
            lowered = str(exc).lower()
            if not any(term in lowered for term in ("502", "503", "throttl")):
                raise
            time.sleep(5 * (attempt + 1))
    raise last_error


def extract_json_object(text: str) -> dict:
    decoder = json.JSONDecoder()
    for start, char in enumerate(text):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text[start:])
        except json.JSONDecodeError:
            continue
        review = value.get("self_review") if isinstance(value, dict) else None
        required = {"coverage", "omissions", "format", "granularity", "next_actions"}
        if isinstance(review, dict) and required.issubset(review):
            return value
    raise ValueError("阶段一输出中没有有效 self_review artifact")


def source_two_phase(client, harness_arn: str, actor_id: str, text: str) -> dict:
    session_id = new_session_id()
    phase1 = invoke(
        client,
        harness_arn,
        actor_id,
        session_id,
        PHASE1_SYSTEM,
        text + "\n\n先在内部形成草稿，然后只输出 self_review artifact。",
    )
    artifact = extract_json_object(phase1["text"])
    phase2 = invoke(
        client,
        harness_arn,
        actor_id,
        session_id,
        PHASE2_SYSTEM,
        "原始文档如下：\n"
        + text
        + "\n\nself_review 如下：\n"
        + json.dumps(artifact["self_review"], ensure_ascii=False),
    )
    extracted, revision_count = O._parse_final(phase2["text"])
    if not O._passes_gate(extracted):
        raise ValueError("源文档阶段二未通过五字段门禁")
    close = invoke(
        client,
        harness_arn,
        actor_id,
        session_id,
        CLOSE_SYSTEM,
        "【会话结束】最终结果已确认，本任务到此结束。",
    )
    return {
        "session_id": session_id,
        "self_review": artifact["self_review"],
        "records": len(extracted),
        "revision_count": revision_count,
        "close_text": close["text"],
    }


def memory_records(client, memory_id: str, actor_id: str) -> list[dict]:
    namespace = f"/episodes/{actor_id}"
    response = client.retrieve_memory_records(
        memoryId=memory_id,
        namespace=namespace,
        searchCriteria={
            "searchQuery": "两阶段 self_review 工业技术文档 抽取 经验",
            "topK": 50,
        },
    )
    records = []
    for record in response.get(
        "memoryRecordSummaries", response.get("memoryRecords", [])
    ):
        raw = (record.get("content") or {}).get("text", "")
        try:
            content = json.loads(raw)
        except json.JSONDecodeError:
            content = {"raw": raw}
        records.append(
            {
                "memoryRecordId": record.get("memoryRecordId"),
                "namespaces": record.get("namespaces"),
                "createdAt": str(record.get("createdAt")),
                "record_type": (
                    "actor_reflection"
                    if content.get("title")
                    else "episode"
                    if content.get("situation")
                    else "unknown"
                ),
                "content": content,
            }
        )
    return records


def wait_for_memory(client, memory_id: str, actor_id: str) -> list[dict]:
    deadline = time.monotonic() + WAIT_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        records = memory_records(client, memory_id, actor_id)
        episodes = [record for record in records if record["record_type"] == "episode"]
        reflections = [
            record for record in records if record["record_type"] == "actor_reflection"
        ]
        if episodes and len(reflections) >= 2:
            return records
        print(
            f"waiting for managed memory: episodes={len(episodes)}, "
            f"actor_reflections={len(reflections)}",
            flush=True,
        )
        time.sleep(WAIT_INTERVAL_SECONDS)
    raise TimeoutError("AgentCore 未在等待窗口内生成 1 episode + 2 actor reflections")


def target_extract(
    client, harness_arn: str, actor_id: str, text: str
) -> dict:
    session_id = new_session_id()
    response = invoke(
        client,
        harness_arn,
        actor_id,
        session_id,
        TARGET_SYSTEM,
        text,
    )
    extracted, revision_count = O._parse_final(response["text"])
    if not O._passes_gate(extracted):
        raise ValueError("目标文档输出未通过五字段门禁")
    return {
        "session_id": session_id,
        "revision_count": revision_count,
        "usage": response["usage"],
        "extracted": extracted,
    }


def write_markdown(result: dict) -> None:
    lines = [
        "# Memory-Loop V3 完整结果",
        "",
        "> 本附件保存 managed memory records 与两组完整抽取，不包含自动评分。",
        "",
        f"- source actor：`{result['source_actor']}`",
        f"- 源文档：`{result['source_document']}`",
        f"- 测试文档：`{result['target_document']}`",
        f"- Memory：{len(result['memory_condition']['extracted'])} 条",
        f"- No Memory：{len(result['no_memory_condition']['extracted'])} 条",
        "",
        "## AgentCore EPISODIC Memory 产物",
        "",
    ]
    for record in result["managed_memory_records"]:
        lines.extend(
            [
                f"### {record['record_type']} | `{record['memoryRecordId']}`",
                "",
                "```json",
                json.dumps(record["content"], ensure_ascii=False, indent=2),
                "```",
                "",
            ]
        )
    lines.extend(
        [
            "## Memory 组完整抽取",
            "",
            "```json",
            json.dumps(
                result["memory_condition"]["extracted"], ensure_ascii=False, indent=2
            ),
            "```",
            "",
            "## No Memory 组完整抽取",
            "",
            "```json",
            json.dumps(
                result["no_memory_condition"]["extracted"],
                ensure_ascii=False,
                indent=2,
            ),
            "```",
            "",
        ]
    )
    OUTPUT_MARKDOWN.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    resources = deployed_resources()
    harnesses = resources["harnesses"]
    memory_id = resources["memories"]["episodicMem"]["memoryId"]
    actor_id = f"ep-v3-{int(time.time())}"
    client = boto3.client(
        "bedrock-agentcore",
        region_name=config.REGION,
        config=Config(connect_timeout=30, read_timeout=900, retries={"max_attempts": 3}),
    )
    source = doc_name(SOURCE_PREFIX)
    target = doc_name(TARGET_PREFIX)
    source_run = source_two_phase(
        client,
        harnesses["extractor_ep_review"]["harnessArn"],
        actor_id,
        corpus.load_doc_text(source),
    )
    records = wait_for_memory(client, memory_id, actor_id)
    target_text = corpus.load_doc_text(target)
    with_memory = target_extract(
        client,
        harnesses["extractor_ep_review"]["harnessArn"],
        actor_id,
        target_text,
    )
    without_memory = target_extract(
        client,
        harnesses["extractor_ep_review_nomem"]["harnessArn"],
        actor_id + "-nomem",
        target_text,
    )
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_actor": actor_id,
        "source_document": source,
        "source_run": source_run,
        "managed_memory_records": records,
        "target_document": target,
        "memory_condition": with_memory,
        "no_memory_condition": without_memory,
    }
    OUTPUT_JSON.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    write_markdown(result)
    print(f"json={OUTPUT_JSON}\nmarkdown={OUTPUT_MARKDOWN}", flush=True)


if __name__ == "__main__":
    main()
