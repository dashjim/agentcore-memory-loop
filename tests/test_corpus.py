"""corpus 模块单测：对真实语料运行（只读文件，不触碰 AWS）。"""

from src import corpus

# 目标文档名（150 方液氮罐技术要求，含 Ground Truth）。
LIQUID_N2_DOC = "150方液氮罐技术要求20240910(公开)(数量：2台)（令号：TP-2425、TP-2426）"
FLOWCHART_DOC = "2477080009流程图8.8"  # 已知无 Ground Truth


def test_list_docs_count():
    """语料库应有 7 个文档。"""
    docs = corpus.list_docs()
    assert len(docs) == 7
    names = {d["name"] for d in docs}
    assert LIQUID_N2_DOC in names
    assert FLOWCHART_DOC in names


def test_list_docs_schema():
    """每个文档元信息字段齐全、类型正确。"""
    for d in corpus.list_docs():
        assert set(d) == {"name", "md_dir", "tables_dir", "gt_csv", "num_pages", "has_gt"}
        assert d["num_pages"] >= 1
        assert d["has_gt"] == (d["gt_csv"] is not None)


def test_flowchart_has_no_gt():
    """流程图文档无 Ground Truth。"""
    docs = {d["name"]: d for d in corpus.list_docs()}
    assert docs[FLOWCHART_DOC]["has_gt"] is False
    assert corpus.load_gt(FLOWCHART_DOC) == []


def test_load_gt_parses_records():
    """150 方液氮罐能解析出 >0 条 GT，且字段非空、结构正确。"""
    records = corpus.load_gt(LIQUID_N2_DOC)
    assert len(records) > 0
    for r in records:
        assert set(r) == {"主体", "部件", "特征值", "原文"}
    # 至少存在一条主体与特征值都非空的记录。
    assert any(r["主体"] and r["特征值"] for r in records)
    # 抽查首条记录的字段确有内容。
    first = records[0]
    assert first["主体"]
    assert first["特征值"]


def test_load_doc_text_nonempty():
    """抽取输入文本非空，且表格区被标注。"""
    text = corpus.load_doc_text(LIQUID_N2_DOC)
    assert text.strip()
    # 该文档有 tables，应出现【表格】标注。
    assert "【表格】" in text
