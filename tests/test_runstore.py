"""runstore：init / insert / list / get 往返正确。"""
import json

from src import runstore


def _sample(run_id="r1", doc="docA", mode="custom"):
    return {
        "run_id": run_id,
        "ts": "2026-08-30T00:00:00+00:00",
        "doc_name": doc,
        "memory_mode": mode,
        "warm": 1,
        "revision_count": 2,
        "elapsed_sec": 12.5,
        "input_tokens": 100,
        "output_tokens": 20,
        "total_tokens": 120,
        "coverage": 0.8,
        "accuracy": 0.9,
        "self_review_pass": 1,
        "num_extracted": 3,
        "num_gt": 4,
        "extracted_json": json.dumps([{"设备部件": "排液管线"}], ensure_ascii=False),
        "notes": "n",
    }


def test_insert_and_get_roundtrip(tmp_path):
    db = tmp_path / "runs.db"
    runstore.init_db(str(db))
    rid = runstore.insert_run(_sample(), path=str(db))
    assert rid == "r1"

    got = runstore.get_run("r1", path=str(db))
    assert got is not None
    assert got["doc_name"] == "docA"
    assert got["memory_mode"] == "custom"
    assert got["revision_count"] == 2
    assert got["total_tokens"] == 120
    assert got["coverage"] == 0.8
    assert json.loads(got["extracted_json"]) == [{"设备部件": "排液管线"}]


def test_get_missing_returns_none(tmp_path):
    db = tmp_path / "runs.db"
    assert runstore.get_run("nope", path=str(db)) is None


def test_list_filters(tmp_path):
    db = tmp_path / "runs.db"
    runstore.insert_run(_sample("r1", "docA", "none"), path=str(db))
    runstore.insert_run(_sample("r2", "docA", "custom"), path=str(db))
    runstore.insert_run(_sample("r3", "docB", "custom"), path=str(db))

    assert len(runstore.list_runs(path=str(db))) == 3
    assert {r["run_id"] for r in runstore.list_runs(doc="docA", path=str(db))} == {"r1", "r2"}
    assert {r["run_id"] for r in runstore.list_runs(mode="custom", path=str(db))} == {"r2", "r3"}
    assert {r["run_id"] for r in runstore.list_runs(doc="docA", mode="custom", path=str(db))} == {"r2"}


def test_insert_replace_on_same_id(tmp_path):
    db = tmp_path / "runs.db"
    runstore.insert_run(_sample("r1", "docA"), path=str(db))
    d2 = _sample("r1", "docA")
    d2["num_extracted"] = 99
    runstore.insert_run(d2, path=str(db))
    assert runstore.get_run("r1", path=str(db))["num_extracted"] == 99
    assert len(runstore.list_runs(path=str(db))) == 1
