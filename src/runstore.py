"""运行指标存储（SQLite，默认 <BASE>/runs.db）。

单表 runs，供 orchestrator 落盘、UI 读取。所有函数接受可选 path 便于单测隔离。
"""
import sqlite3

from . import config

_COLUMNS = [
    "run_id", "ts", "doc_name", "memory_mode", "warm", "revision_count",
    "elapsed_sec", "input_tokens", "output_tokens", "total_tokens",
    "coverage", "accuracy", "self_review_pass", "num_extracted", "num_gt",
    "extracted_json", "notes",
]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    ts TEXT,
    doc_name TEXT,
    memory_mode TEXT,
    warm INTEGER,
    revision_count INTEGER,
    elapsed_sec REAL,
    input_tokens INTEGER,
    output_tokens INTEGER,
    total_tokens INTEGER,
    coverage REAL,
    accuracy REAL,
    self_review_pass INTEGER,
    num_extracted INTEGER,
    num_gt INTEGER,
    extracted_json TEXT,
    notes TEXT
);
"""


def _db_path(path):
    return str(path) if path else str(config.RUNS_DB_PATH)


def _connect(path=None):
    conn = sqlite3.connect(_db_path(path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(path=None):
    conn = _connect(path)
    try:
        conn.execute(_SCHEMA)
        conn.commit()
    finally:
        conn.close()


def insert_run(d: dict, path=None) -> str:
    """插入一条 run（run_id 冲突时覆盖）。返回 run_id。"""
    init_db(path)
    conn = _connect(path)
    try:
        cols = ",".join(_COLUMNS)
        placeholders = ",".join("?" for _ in _COLUMNS)
        conn.execute(
            f"INSERT OR REPLACE INTO runs ({cols}) VALUES ({placeholders})",
            [d.get(k) for k in _COLUMNS],
        )
        conn.commit()
    finally:
        conn.close()
    return d.get("run_id")


def list_runs(doc=None, mode=None, path=None) -> list:
    """按文档/模式过滤，按时间倒序返回。"""
    init_db(path)
    conn = _connect(path)
    try:
        query = "SELECT * FROM runs"
        clauses, params = [], []
        if doc:
            clauses.append("doc_name = ?")
            params.append(doc)
        if mode:
            clauses.append("memory_mode = ?")
            params.append(mode)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY ts DESC"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_run(run_id, path=None) -> dict:
    """按 run_id 取单条；不存在返回 None。"""
    init_db(path)
    conn = _connect(path)
    try:
        row = conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()
