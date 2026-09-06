#!/usr/bin/env python3
"""单 run 召回错误分析（确定性，无 LLM）：某次抽取漏了哪些 GT、为什么。

对指定 db 里最后一次（或指定 memory_mode 的最后一次）运行：
  - 逐条 GT 关键词重叠判命中(≥50%)；
  - 漏抽拆分：真召回失败(零重叠) vs 粒度/对齐问题(部分重叠)；
  - 按类别拆分漏抽；
  - **散文/流程类探针**：检查一组"非定量三元组"的代表 GT 是否被抓出来（opt-v2 的验证重点）。

用法：python3 scripts/analyze_recall.py <db_path> [memory_mode]
"""
import sys, json, re
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import corpus, runstore  # noqa: E402

CATS = {"检测": ("检测", "RT", "PT", "UT", "无损", "探伤", "射线", "渗透", "真空度"),
        "安装环境": ("环境", "温度", "风速", "风压", "雪压", "地震", "海拔"),
        "受压元件": ("受压", "内罐", "外壳", "封头", "筒体"),
        "焊接": ("焊",),
        "材料": ("材料", "材质", "钢"),
        "阀门仪表": ("阀", "仪表", "压力表", "液位"),
        "管口接管": ("管口", "接管", "法兰", "通径", "接口"),}

# 散文/流程/待确认类探针（reflection 分析里 recall_fail 的代表）：opt-v2 应把它们抓出来
PROBES = ["真空度测量", "外观颜色", "喷涂", "油漆", "地脚螺栓", "与甲方确认", "细化设计"]


def kw(s):
    return set(re.findall(r'[一-鿿]{2,}|[A-Za-z0-9]{2,}', s or ''))


def cat_of(g):
    blob = (g.get("部件") or "") + (g.get("原文") or "") + (g.get("特征值") or "")
    for name, kws in CATS.items():
        if any(w in blob for w in kws):
            return name
    return "其他"


def main():
    db = sys.argv[1] if len(sys.argv) > 1 else "runs_v2_opt2.db"
    mode = sys.argv[2] if len(sys.argv) > 2 else None
    doc = next(d["name"] for d in corpus.list_docs() if d["name"].startswith("150方液氮罐"))
    gt = corpus.load_gt(doc)
    rows = sorted(runstore.list_runs(path=db), key=lambda x: x["ts"])
    if mode:
        rows = [r for r in rows if r["memory_mode"] == mode]
    if not rows:
        print("无匹配运行"); return
    r = rows[-1]
    ex = json.loads(r["extracted_json"])
    exk = [kw(e.get("原文")) for e in ex]

    def best(gk):
        return max((len(gk & ek) / len(gk) for ek in exk), default=0.0) if gk else 0.0

    recall_fail = granularity = 0
    miss_cat = Counter()
    for g in gt:
        gk = kw(g.get("原文") or g.get("特征值"))
        if not gk:
            continue
        b = best(gk)
        if b >= 0.5:
            continue
        miss_cat[cat_of(g)] += 1
        if b == 0:
            recall_fail += 1
        else:
            granularity += 1

    print(f"db={db} mode={r['memory_mode']} variant={json.loads(r['notes']).get('variant')}")
    print(f"覆盖率(judge)={r['coverage']} 精确率={json.loads(r['notes']).get('precision')} "
          f"F1={json.loads(r['notes']).get('f1')} n_ex={len(ex)} GT={len(gt)}")
    print(f"漏抽拆分：真召回失败(零重叠)={recall_fail}  粒度/对齐问题={granularity}")
    print(f"漏抽按类别：{dict(miss_cat.most_common())}")
    print("\n散文/流程类探针（opt-v2 应抓出；命中=在抽取结果里找到含该词的原文）：")
    allex = " ".join((e.get("原文") or "") + (e.get("指标名称") or "") + (e.get("指标特征") or "") for e in ex)
    for p in PROBES:
        in_gt = any(p in (g.get("原文") or g.get("特征值") or "") for g in gt)
        print(f"  {'✓抓到' if p in allex else '✗漏 '} 「{p}」" + ("" if in_gt else "  (GT中无此词,忽略)"))


if __name__ == "__main__":
    main()
