"""语料加载模块。

负责扫描工业技术文档语料库，提供三类能力：
1. `list_docs()`  —— 列出全部文档及其元信息；
2. `load_doc_text(name)` —— 拼接某文档的抽取输入文本（含表格补充）；
3. `load_gt(name)` —— 解析该文档的 Ground Truth（标准答案）记录。

语料目录结构（每个文档一个子目录）::

    <CORPUS_ROOT>/<文档名>/
        markdown_corrected/page_N.md          # 抽取输入（按页）
        tables/page_N_tables.{md,csv}         # 表格补充（部分页有）
        csv/flattened_data_restructured_*.csv # Ground Truth（部分文档有）

Ground Truth CSV 结构：首行为 ``参数,值1,值2,...,值20``；第 0 列是参数类别，
其余单元格若非空则是一个多行记录块，形如::

    主体：液氮储罐
    部件：下进液管
    特征值：末端设置防涡装置
    原文：(16) 下进液管末端（容器内）设置防涡装置...

冒号为中文 ``：``。同一块内 ``特征值`` 可能出现多次；``部件``/``原文`` 可能缺失。
表格类单元格（如 ``序号``、``27.7°C``）不含上述字段前缀，一律忽略。
"""

from __future__ import annotations

import csv
import os
import re
from pathlib import Path

# 语料根目录（绝对路径常量）；可用环境变量 CORPUS_ROOT 覆盖，便于测试/迁移。
_DEFAULT_CORPUS_ROOT = "/home/ubuntu/g-repo/memory-loop/input/corpus/output"


def _corpus_root() -> Path:
    """返回当前生效的语料根目录。"""
    return Path(os.environ.get("CORPUS_ROOT", _DEFAULT_CORPUS_ROOT))


# GT 记录块中识别的字段前缀 -> 归一化后的字段名。
# 注意：GT 只有"特征值"，没有把"指标名称/指标特征"分开，这是我方 schema 与 GT 的已知差异。
_FIELD_PREFIXES = {
    "主体": "主体",
    "部件": "部件",
    "特征值": "特征值",
    "原文": "原文",
}

# 匹配行首的 "字段名：" 或 "字段名:"（兼容中/英文冒号）。
_PREFIX_RE = re.compile(r"^\s*([^：:]{1,6})[：:]\s*(.*)$")

# 从 page_N.md / page_N_tables.md 中抽取页码。
_PAGE_NUM_RE = re.compile(r"page_(\d+)")


def _page_num(path: Path) -> int:
    """从文件名解析页码，用于排序。"""
    m = _PAGE_NUM_RE.search(path.name)
    return int(m.group(1)) if m else 0


def _find_gt_csv(doc_dir: Path) -> Path | None:
    """定位文档的 Ground Truth CSV（restructured 版本）。

    只在 ``csv/`` 顶层查找，排除 ``csv/backup/`` 下的历史备份。
    """
    csv_dir = doc_dir / "csv"
    if not csv_dir.is_dir():
        return None
    candidates = sorted(csv_dir.glob("flattened_data_restructured_*.csv"))
    return candidates[0] if candidates else None


def list_docs() -> list[dict]:
    """扫描语料根目录，返回全部文档的元信息列表。

    每个元素为::

        {
            "name": str,             # 文档目录名
            "md_dir": str,           # markdown_corrected 目录绝对路径
            "tables_dir": str|None,  # tables 目录绝对路径（不存在则 None）
            "gt_csv": str|None,      # Ground Truth CSV 绝对路径（无则 None）
            "num_pages": int,        # markdown_corrected 下 page_*.md 数量
            "has_gt": bool,          # 是否有 Ground Truth
        }

    只有包含 ``markdown_corrected/page_*.md`` 的子目录才视为文档。
    结果按文档名排序，保证顺序稳定。
    """
    root = _corpus_root()
    docs: list[dict] = []
    if not root.is_dir():
        return docs

    for doc_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        md_dir = doc_dir / "markdown_corrected"
        pages = list(md_dir.glob("page_*.md")) if md_dir.is_dir() else []
        if not pages:
            # 非文档目录（无抽取输入）跳过。
            continue

        tables_dir = doc_dir / "tables"
        gt_csv = _find_gt_csv(doc_dir)

        docs.append(
            {
                "name": doc_dir.name,
                "md_dir": str(md_dir),
                "tables_dir": str(tables_dir) if tables_dir.is_dir() else None,
                "gt_csv": str(gt_csv) if gt_csv is not None else None,
                "num_pages": len(pages),
                "has_gt": gt_csv is not None,
            }
        )
    return docs


def _doc_dir(name: str) -> Path:
    return _corpus_root() / name


def load_doc_text(name: str) -> str:
    """拼接指定文档的抽取输入文本。

    - 将 ``markdown_corrected/page_*.md`` 按页码升序拼接（页间以空行分隔）；
    - 若存在 ``tables/page_*_tables.md``，按页码升序追加到末尾，并以
      ``【表格】`` 标注表格区起始。

    返回纯文本。文档不存在或无内容时返回空串。
    """
    doc_dir = _doc_dir(name)
    md_dir = doc_dir / "markdown_corrected"
    parts: list[str] = []

    if md_dir.is_dir():
        for page in sorted(md_dir.glob("page_*.md"), key=_page_num):
            parts.append(page.read_text(encoding="utf-8").strip())

    tables_dir = doc_dir / "tables"
    if tables_dir.is_dir():
        table_files = sorted(tables_dir.glob("page_*_tables.md"), key=_page_num)
        if table_files:
            parts.append("【表格】")
            for tf in table_files:
                parts.append(tf.read_text(encoding="utf-8").strip())

    return "\n\n".join(p for p in parts if p)


def _parse_gt_cell(cell: str) -> dict | None:
    """把一个 GT 单元格解析为记录 dict。

    识别行首字段前缀（主体/部件/特征值/原文）；不带前缀的续行并入上一字段
    （处理 ``原文`` 跨行）；``特征值`` 多次出现时用 ``; `` 拼接。

    若单元格不含任何可识别字段（如表格碎片 ``序号``、``27.7°C``），返回 None。
    """
    fields: dict[str, str] = {"主体": "", "部件": "", "特征值": "", "原文": ""}
    current: str | None = None
    matched_any = False

    for line in cell.split("\n"):
        m = _PREFIX_RE.match(line)
        key = _FIELD_PREFIXES.get(m.group(1).strip()) if m else None
        if key is not None:
            matched_any = True
            value = m.group(2).strip()
            if key == "特征值" and fields[key]:
                fields[key] = f"{fields[key]}; {value}" if value else fields[key]
            else:
                fields[key] = value
            current = key
        elif current is not None:
            # 续行：并入当前字段（保留一个空格分隔）。
            extra = line.strip()
            if extra:
                fields[current] = f"{fields[current]} {extra}".strip()

    if not matched_any:
        return None
    return fields


def load_gt(name: str) -> list[dict]:
    """解析指定文档的 Ground Truth，返回记录列表。

    每条记录为 ``{"主体","部件","特征值","原文"}``（缺字段留空串）。
    文档无 Ground Truth CSV 时返回 ``[]``。
    """
    doc_dir = _doc_dir(name)
    gt_csv = _find_gt_csv(doc_dir)
    if gt_csv is None:
        return []

    records: list[dict] = []
    # utf-8-sig 自动去除 BOM。
    with open(gt_csv, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.reader(fh))

    # 跳过首行表头（参数,值1,...）。第 0 列为参数类别，其余列为记录块。
    for row in rows[1:]:
        for cell in row[1:]:
            text = cell.strip()
            if not text:
                continue
            rec = _parse_gt_cell(text)
            if rec is not None:
                records.append(rec)
    return records
