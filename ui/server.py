"""Memory-Loop 本地 Web UI 后端（FastAPI）。

- 仅绑定 127.0.0.1:8600（禁止 0.0.0.0 / 公网）。
- 依赖 src/{corpus,runstore,orchestrator}.py（其他并行模块提供，import 即可）。
- 若 src 不可用，或设置 MEMORY_LOOP_UI_MOCK=1，则降级到内置 mock 数据。
- 所有对 src 的调用均 try/except，失败返回明确错误 JSON，不抛 500。

启动：
    MEMORY_LOOP_UI_MOCK=1 python server.py
    # 或
    MEMORY_LOOP_UI_MOCK=1 uvicorn server:app --host 127.0.0.1 --port 8600
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

# --- 定位路径：ui/ 的父目录即项目根，src/ 与 ui/ 平级 ---
UI_DIR = Path(__file__).resolve().parent
ROOT = UI_DIR.parent
STATIC_DIR = UI_DIR / "static"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# --- 尝试导入真实 src 模块；失败则记录原因并走 mock ---
FORCE_MOCK = os.environ.get("MEMORY_LOOP_UI_MOCK") == "1"
SRC_IMPORT_ERROR = None
corpus = runstore = orchestrator = None
if not FORCE_MOCK:
    try:
        from src import corpus, orchestrator, runstore  # type: ignore
    except Exception as exc:  # noqa: BLE001 - src 尚未就绪属预期
        SRC_IMPORT_ERROR = f"{type(exc).__name__}: {exc}"
        corpus = runstore = orchestrator = None

USE_MOCK = FORCE_MOCK or corpus is None

# TODO(src): 当 src/{corpus,runstore,orchestrator}.py 就绪后，
# 未设置 MEMORY_LOOP_UI_MOCK=1 时将自动切换到真实实现，无需改动本文件。
from mockdata import MOCK  # noqa: E402  (本地降级数据源)

app = FastAPI(title="Memory-Loop UI", docs_url=None, redoc_url=None)


def _err(msg: str, detail: str | None = None):
    """统一错误响应（HTTP 200 + error 字段，避免前端因 500 崩溃）。"""
    body = {"error": msg}
    if detail:
        body["detail"] = detail
    return JSONResponse(body, status_code=200)


# ---------------------------------------------------------------------------
# 请求体模型
# ---------------------------------------------------------------------------
class RunReq(BaseModel):
    doc_name: str
    memory_mode: str  # none | episodic | custom
    warm: bool = False


class ClearReq(BaseModel):
    memory_mode: str


# ---------------------------------------------------------------------------
# 元信息（便于前端提示当前是否 mock）
# ---------------------------------------------------------------------------
@app.get("/api/status")
def api_status():
    return {
        "mock": USE_MOCK,
        "forced_mock": FORCE_MOCK,
        "src_import_error": SRC_IMPORT_ERROR,
    }


# ---------------------------------------------------------------------------
# GET /api/docs → 文档列表
# ---------------------------------------------------------------------------
@app.get("/api/docs")
def api_docs():
    if USE_MOCK:
        return MOCK.list_docs()
    try:
        return corpus.list_docs()
    except Exception as exc:  # noqa: BLE001
        return _err("读取文档列表失败", str(exc))


# ---------------------------------------------------------------------------
# GET /api/runs?doc=&mode= → 运行历史
# ---------------------------------------------------------------------------
@app.get("/api/runs")
def api_runs(doc: str | None = None, mode: str | None = None):
    if USE_MOCK:
        return MOCK.list_runs(doc=doc, mode=mode)
    try:
        return runstore.list_runs(doc=doc, mode=mode)
    except Exception as exc:  # noqa: BLE001
        return _err("读取运行历史失败", str(exc))


# ---------------------------------------------------------------------------
# POST /api/run → 触发一次抽取（同步返回 run dict）
# ---------------------------------------------------------------------------
@app.post("/api/run")
async def api_run(req: RunReq):
    if req.memory_mode not in ("none", "episodic", "custom"):
        return _err("非法记忆模式", req.memory_mode)
    if USE_MOCK:
        run = await run_in_threadpool(
            MOCK.run_extraction, req.doc_name, req.memory_mode, req.warm
        )
        return run
    try:
        run = await run_in_threadpool(
            orchestrator.run_extraction,
            req.doc_name,
            req.memory_mode,
            req.warm,
        )
        return run
    except Exception as exc:  # noqa: BLE001
        return _err("抽取运行失败", str(exc))


# ---------------------------------------------------------------------------
# GET /api/memory?scope=strat|tact → 学到的规则列表
# ---------------------------------------------------------------------------
@app.get("/api/memory")
def api_memory(scope: str = "strat"):
    if scope not in ("strat", "tact"):
        return _err("非法 scope", scope)
    if USE_MOCK:
        return {"scope": scope, "lessons": MOCK.read_lessons(scope)}
    try:
        return {"scope": scope, "lessons": orchestrator.read_lessons(scope)}
    except Exception as exc:  # noqa: BLE001
        return _err("读取记忆规则失败", str(exc))


# ---------------------------------------------------------------------------
# POST /api/clear-memory → 清除指定模式的记忆
# ---------------------------------------------------------------------------
@app.post("/api/clear-memory")
async def api_clear_memory(req: ClearReq):
    if USE_MOCK:
        return MOCK.clear_memory_for_mode(req.memory_mode)
    try:
        result = await run_in_threadpool(
            orchestrator.clear_memory_for_mode, req.memory_mode
        )
        return result if result is not None else {"ok": True, "cleared": req.memory_mode}
    except Exception as exc:  # noqa: BLE001
        return _err("清除记忆失败", str(exc))


# ---------------------------------------------------------------------------
# 静态前端
# ---------------------------------------------------------------------------
@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


if __name__ == "__main__":
    import uvicorn

    # 硬编码 127.0.0.1：严禁 0.0.0.0 / 公网绑定。
    uvicorn.run(app, host="127.0.0.1", port=8600, log_level="info")
