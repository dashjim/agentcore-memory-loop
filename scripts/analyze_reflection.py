#!/usr/bin/env python3
"""Reflection 实验的确定性错误分析（无 LLM 调用）：为什么 GT 没被召回？

对 runs_reflection.db 里成对的 refl_r1 / refl_r2：
  - 逐条 GT 用关键词重叠判"是否被某抽取项覆盖"(重叠≥50% 记命中)；
  - 分类：两轮都命中 / round2 救回(r1漏 r2中) / round2 丢失(r1中 r2漏) / 两轮都漏；
  - 对"漏"的 GT 再分：真召回失败(与任何抽取项零重叠) vs 粒度对齐问题(有部分重叠 0<x<0.5)；
  - 按部件类别(检测/环境/受压/焊接/材料/阀门/管口…)拆分漏抽，并举例。

用法：python3 scripts/analyze_reflection.py
"""
import sys, json, re
from pathlib import Path
from collections import Counter, defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import corpus, runstore  # noqa: E402

CATS = {"检测": ("检测", "RT", "PT", "UT", "无损", "探伤", "射线", "渗透"),
        "安装环境": ("环境", "温度", "风速", "风压", "雪压", "地震", "海拔"),
        "受压元件": ("受压", "内罐", "外壳", "封头", "筒体"),
        "焊接": ("焊",),
        "材料": ("材料", "材质", "钢"),
        "阀门仪表": ("阀", "仪表", "压力表", "液位"),
        "管口接管": ("管口", "接管", "法兰", "通径", "接口"),}


def kw(s):
    return set(re.findall(r'[一-鿿]{2,}|[A-Za-z0-9]{2,}', s or ''))


def overlap(gk, ek):
    return len(gk & ek) / len(gk) if gk else 0.0


def cat_of(gt_row):
    blob = (gt_row.get("部件") or "") + (gt_row.get("原文") or "") + (gt_row.get("特征值") or "")
    for name, kws in CATS.items():
        if any(w in blob for w in kws):
            return name
    return "其他"


def analyze_pair(gt, ex1, ex2):
    gtk = [(kw(g.get("原文") or g.get("特征值")), g) for g in gt]
    k1 = [kw(e.get("原文")) for e in ex1]
    k2 = [kw(e.get("原文")) for e in ex2]

    def status(gk, exk):
        if not gk:
            return "na", 0.0
        best = max((overlap(gk, ek) for ek in exk), default=0.0)
        if best >= 0.5:
            return "hit", best
        if best > 0:
            return "granularity", best   # 抽了但对齐不足
        return "recall_fail", best       # 零重叠：根本没抽

    recovered, regressed, missed_both = [], [], []
    for gk, g in gtk:
        s1, _ = status(gk, k1)
        s2, b2 = status(gk, k2)
        h1, h2 = (s1 == "hit"), (s2 == "hit")
        if h2 and not h1:
            recovered.append(g)
        elif h1 and not h2:
            regressed.append(g)
        elif not h1 and not h2:
            missed_both.append((g, s2, b2))  # 用 round2 的状态判 recall_fail vs granularity
    return recovered, regressed, missed_both, len(gtk)


def main():
    doc = next(d["name"] for d in corpus.list_docs() if d["name"].startswith("150方液氮罐"))
    gt = corpus.load_gt(doc)
    rows = sorted(runstore.list_runs(path="runs_reflection.db"), key=lambda x: x["ts"])
    pairs = defaultdict(dict)
    for r in rows:
        n = json.loads(r["notes"])
        pairs[n.get("pair_id")][r["memory_mode"]] = r
    pairs = [p for p in pairs.values() if "refl_r1" in p and "refl_r2" in p]
    print(f"文档 GT={len(gt)}  |  {len(pairs)} 对\n")

    agg_missed = Counter()
    agg_kind = Counter()
    for i, p in enumerate(pairs, 1):
        r1, r2 = p["refl_r1"], p["refl_r2"]
        ex1 = json.loads(r1["extracted_json"]); ex2 = json.loads(r2["extracted_json"])
        rec, reg, missed, ngt = analyze_pair(gt, ex1, ex2)
        print(f"=== 对 {i}  round1 cov={r1['coverage']:.3f}(n_ex={len(ex1)}) "
              f"→ round2 cov={r2['coverage']:.3f}(n_ex={len(ex2)}) ===")
        print(f"  round2 救回(r1漏→r2中): {len(rec)}   round2 丢失(r1中→r2漏): {len(reg)}   两轮都漏: {len(missed)}")
        # 两轮都漏的：recall_fail vs granularity + 类别
        kind = Counter(k for _, k, _ in missed)
        catc = Counter(cat_of(g) for g, _, _ in missed)
        print(f"  两轮都漏拆分：真召回失败(零重叠)={kind.get('recall_fail',0)}  粒度/对齐问题(部分重叠)={kind.get('granularity',0)}")
        print(f"  两轮都漏按类别：{dict(catc.most_common())}")
        for g, k, b in missed[:6]:
            src = (g.get("原文") or g.get("特征值") or "")[:48]
            print(f"    - [{k} best={b:.2f}][{cat_of(g)}] {src}")
        print()
        agg_missed.update(catc); agg_kind.update(kind)

    if len(pairs) > 1:
        print("==== 汇总（全部对，两轮都漏）====")
        print(f"  真召回失败 vs 粒度问题：{dict(agg_kind)}")
        print(f"  按类别：{dict(agg_missed.most_common())}")


if __name__ == "__main__":
    main()
