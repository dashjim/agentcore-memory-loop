"""AgentCore Memory 读写工具（显式经验的精确即时存取）。

设计（经真机实测确定，2026-08-30）：
- 我们的"经验/规则"是已提炼的短文本，需要**逐字、即时**存取，
  因此用 `create_event` 写原始事件、`list_events` 读原始事件，
  **不走** SEMANTIC 策略的 `retrieve_memory_records`（异步抽取、有延迟、namespace 语义不符）。
- `list_events` 的 `sessionId` 必填、`create_event` 的 `eventTimestamp` 必填（均已实测）。
- 记忆分区用 sessionId 承载，与 harness 的 runtimeSessionId 解耦：
    strat（战略，跨文档/跨运行）-> 固定全局 session `strat-{actor}`
    tact （战术，按文档累积）    -> 按文档派生 session `tact-{actor}-{md5(doc)[:8]}`
  这样：strat 跨运行累积；同一文档重跑时其 tact 也持续累积。

约定：client 为 None 时内部建 boto3 数据面 client（bedrock-agentcore, us-west-2），单测注入 fake。
"""
import hashlib
from datetime import datetime, timezone

import boto3

from . import config


def _client(client):
    return client if client is not None else boto3.client(
        "bedrock-agentcore", region_name=config.REGION)


def _pad_session(s: str) -> str:
    """AgentCore sessionId 需 ≥33 字符；不足则用 'x' 右填充。"""
    return s if len(s) >= 33 else s.ljust(33, "x")


def strat_session(actor_id: str) -> str:
    return _pad_session(f"strat-{actor_id}")


def tact_session(actor_id: str, doc_name: str) -> str:
    h = hashlib.md5((doc_name or "").encode("utf-8")).hexdigest()[:8]
    return _pad_session(f"tact-{actor_id}-{h}")


def _session_for(scope: str, actor_id: str, doc_name: str = None) -> str:
    if scope == "strat":
        return strat_session(actor_id)
    if scope == "tact":
        if not doc_name:
            raise ValueError("tact scope 需要 doc_name 才能确定 session")
        return tact_session(actor_id, doc_name)
    raise ValueError(f"未知 scope: {scope!r}（仅支持 'strat'/'tact'）")


def record_lesson(scope, text, memory_id, actor_id, doc_name=None, client=None) -> None:
    """写入一条经验到对应分区（原始事件）。"""
    c = _client(client)
    sid = _session_for(scope, actor_id, doc_name)
    c.create_event(
        memoryId=memory_id,
        actorId=actor_id,
        sessionId=sid,
        eventTimestamp=datetime.now(timezone.utc),
        payload=[{"conversational": {"content": {"text": text}, "role": "ASSISTANT"}}],
    )


def _texts_from_events(events) -> list:
    """从 list_events 返回的事件里逐条取出文本（新→旧、去重、保序）。"""
    texts = []
    for ev in events or []:
        for p in (ev.get("payload") or []):
            conv = p.get("conversational") if isinstance(p, dict) else None
            if isinstance(conv, dict):
                t = (conv.get("content") or {}).get("text")
                if isinstance(t, str) and t:
                    texts.append(t)
    # 去重保序
    seen, out = set(), []
    for t in texts:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def _list_all_events(c, memory_id, actor_id, session_id, cap=200) -> list:
    events, token = [], None
    while len(events) < cap:
        kw = {"memoryId": memory_id, "actorId": actor_id, "sessionId": session_id,
              "includePayloads": True, "maxResults": 100}
        if token:
            kw["nextToken"] = token
        resp = c.list_events(**kw)
        events.extend(resp.get("events", []))
        token = resp.get("nextToken")
        if not token:
            break
    return events


def recall_lessons(scope, memory_id, actor_id, doc_name=None, client=None, query=None) -> list:
    """召回某 scope 分区下的全部经验（逐字、即时）。query 仅保留以兼容工具签名，未用于过滤。"""
    c = _client(client)
    sid = _session_for(scope, actor_id, doc_name)
    return _texts_from_events(_list_all_events(c, memory_id, actor_id, sid))


def read_all_lessons(scope, memory_id, actor_id, doc_name=None, client=None) -> list:
    """供 UI 展示：等价 recall。"""
    return recall_lessons(scope, memory_id, actor_id, doc_name=doc_name, client=client)


def clear_memory(memory_id, actor_id, doc_names=None, client=None, scope=None) -> int:
    """清空经验：遍历相关 session（strat 全局 + 各文档 tact），list_events + delete_event。

    - scope=None：清 strat + 所有给定 doc 的 tact。
    - scope='strat'：只清 strat。
    - scope='tact'：只清给定 doc 的 tact。
    返回删除条数。
    """
    c = _client(client)
    sessions = []
    if scope in (None, "strat"):
        sessions.append(strat_session(actor_id))
    if scope in (None, "tact"):
        for d in (doc_names or []):
            sessions.append(tact_session(actor_id, d))

    deleted = 0
    for sid in sessions:
        for ev in _list_all_events(c, memory_id, actor_id, sid):
            eid = ev.get("eventId")
            if not eid:
                continue
            c.delete_event(memoryId=memory_id, actorId=actor_id, sessionId=sid, eventId=eid)
            deleted += 1
    return deleted
