"""LLM-as-judge 评分模块。

用一个"裁判 LLM"把 agent 抽取结果（extracted）与标准答案（Ground Truth, gt）
做**一对一语义对齐**，再对匹配上的条目逐字段判定 ``正确/部分/错误``，据此计算：

- ``coverage``  = 匹配上的 GT 条目数 / GT 条目总数（GT 为空时为 None）；
- ``accuracy``  = 字段级正确率（正确=1，部分=0.5，错误=0，在所有匹配条目的
  所有可比字段上取平均；无可比字段时为 None）。

裁判调用被封装成注入函数 ``judge_fn(prompt: str) -> str``，因此本模块不直接依赖
boto3，便于单测注入假裁判。真实实现见 :func:`build_bedrock_judge`。

我方 schema 为 ``{设备主体,设备部件,指标名称,指标特征,原文}``；GT 为
``{主体,部件,特征值,原文}``。二者的字段差异（GT 的"特征值" ≈ 我方"指标名称+指标特征"）
交由裁判做语义对齐，因此 prompt 中会明确说明这一对应关系。
"""

from __future__ import annotations

import json
import re

# 每次裁判调用最多对齐这么多条 GT（分块，避免单次输出过大导致截断/摆烂）。
_GT_CHUNK = 20

# 裁判判定标签 -> 分值。兼容中/英文写法。
_VERDICT_SCORE = {
    "正确": 1.0,
    "部分": 0.5,
    "错误": 0.0,
    "correct": 1.0,
    "partial": 0.5,
    "wrong": 0.0,
    "incorrect": 0.0,
}


def _build_prompt(extracted: list[dict], gt_chunk: list[dict]) -> str:
    """构造裁判 prompt，要求其返回严格 JSON。

    gt_chunk 中每个元素需带全局键 ``gt_index``（分块评分时保留原始下标）。
    """
    extracted_json = json.dumps(
        [{"index": i, **rec} for i, rec in enumerate(extracted)],
        ensure_ascii=False,
        indent=2,
    )
    gt_json = json.dumps(
        [{"index": rec["gt_index"], **{k: v for k, v in rec.items() if k != "gt_index"}}
         for rec in gt_chunk],
        ensure_ascii=False,
        indent=2,
    )
    return f"""你是一个严格的工业文档信息抽取评测裁判。下面给出两组记录：

【抽取结果 extracted】（我方 agent 输出，字段：设备主体/设备部件/指标名称/指标特征/原文）：
{extracted_json}

【标准答案 gt】（Ground Truth，字段：主体/部件/特征值/原文）：
{gt_json}

任务：
1. 把 extracted 与 gt 做**一对一语义对齐**：为每个 gt 条目找出语义上对应的
   唯一 extracted 条目；找不到对应时记为无匹配（extracted_index = null）。
   一个 extracted 条目至多匹配一个 gt 条目。
2. 对每个"匹配上"的条目，逐字段判定，取值只能是 "正确"/"部分"/"错误"：
   - 主体   ↔ 设备主体
   - 部件   ↔ 设备部件
   - 特征值 ↔ 设备指标（我方的"指标名称"+"指标特征"合起来是否覆盖 gt 的"特征值"语义）
   - 原文   ↔ 原文（是否指向同一原始文本片段）
   某字段在 gt 中为空、无从比较时，可不列入该条目的 field_judgments。

只输出如下严格 JSON（不要输出任何多余文字或解释）：
{{
  "alignments": [
    {{
      "gt_index": 0,
      "extracted_index": 3,
      "field_judgments": {{"主体": "正确", "部件": "部分", "特征值": "正确", "原文": "正确"}}
    }},
    {{
      "gt_index": 1,
      "extracted_index": null,
      "field_judgments": {{}}
    }}
  ]
}}
"""


def _extract_json(text: str) -> dict:
    """从裁判返回文本中健壮地解析出 JSON 对象。

    容忍 ```json ... ``` 代码块包裹、以及 JSON 前后的多余文字：
    定位第一个 ``{`` 到最后一个 ``}`` 之间的内容进行解析。
    """
    # 去掉常见的 ```json / ``` 代码块围栏。
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    candidate = fenced.group(1) if fenced else text

    start = candidate.find("{")
    end = candidate.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError(f"裁判输出中未找到 JSON 对象: {text!r}")
    return json.loads(candidate[start : end + 1])


def score(extracted: list[dict], gt: list[dict], judge_fn) -> dict:
    """用 LLM 裁判对抽取结果打分。

    参数：
        extracted: 我方 agent 抽取出的记录列表。
        gt:        标准答案记录列表；为空表示该文档无 Ground Truth。
        judge_fn:  注入的裁判函数 ``(prompt: str) -> str``，返回严格 JSON 文本。

    返回::

        {
            "coverage": float|None,   # 匹配上的 GT 条目数 / len(gt)；gt 为空时 None
            "accuracy": float|None,   # 字段级正确率；无可比字段时 None
            "matches": [...],         # 裁判给出的对齐明细
            "num_extracted": int,
            "num_gt": int,
        }
    """
    num_extracted = len(extracted)
    num_gt = len(gt)

    # 无 Ground Truth：coverage/accuracy 记为 None，不调用裁判。
    if num_gt == 0:
        return {
            "coverage": None,
            "accuracy": None,
            "matches": [],
            "num_extracted": num_extracted,
            "num_gt": 0,
        }

    # 分块对齐：每次给全部 extracted + 一小批 gt，避免单次输出过大导致截断/摆烂。
    # 全局约束（修复 coverage 高估）：
    #   - 每个 gt_index 至多计一次（matched_gt）；
    #   - 每个 extracted_index **全局**至多被用一次（used_ext）——防止同一抽取项跨块重复匹配多个 GT；
    #   - 校验 gt_index 属于当前块、extracted_index 为合法且未用过的整数，否则视为无匹配。
    matched = 0
    field_scores: list[float] = []
    all_alignments: list[dict] = []
    matched_gt: set = set()
    used_ext: set = set()
    for start in range(0, num_gt, _GT_CHUNK):
        chunk_ids = set(range(start, min(start + _GT_CHUNK, num_gt)))
        chunk = [{"gt_index": i, **gt[i]} for i in sorted(chunk_ids)]
        prompt = _build_prompt(extracted, chunk)
        try:
            parsed = _extract_json(judge_fn(prompt))
        except (ValueError, json.JSONDecodeError):
            continue  # 该块裁判输出不可解析：跳过（保守，不误判为命中）
        for a in parsed.get("alignments", []):
            all_alignments.append(a)
            gi = a.get("gt_index")
            ei = a.get("extracted_index")
            # 结构校验 + 全局一对一约束
            if not isinstance(gi, int) or gi not in chunk_ids or gi in matched_gt:
                continue
            if not isinstance(ei, int) or not (0 <= ei < num_extracted) or ei in used_ext:
                continue  # 无匹配 / 越界 / 该抽取项已被其它 GT 用过
            matched += 1
            matched_gt.add(gi)
            used_ext.add(ei)
            for verdict in a.get("field_judgments", {}).values():
                key = str(verdict).strip().lower()
                if verdict in _VERDICT_SCORE:
                    field_scores.append(_VERDICT_SCORE[verdict])
                elif key in _VERDICT_SCORE:
                    field_scores.append(_VERDICT_SCORE[key])

    coverage = matched / num_gt
    accuracy = (sum(field_scores) / len(field_scores)) if field_scores else None
    alignments = all_alignments

    return {
        "coverage": coverage,
        "accuracy": accuracy,
        "matches": alignments,
        "num_extracted": num_extracted,
        "num_gt": num_gt,
    }


def build_bedrock_judge(model_id: str, region: str = "us-west-2"):
    """构造一个由 Amazon Bedrock Claude 支撑的裁判函数。

    返回 ``judge_fn(prompt: str) -> str``，内部用 bedrock-runtime 的 Converse API，
    ``temperature=0`` 保证判定稳定。

    注意：本工厂**不在 import 或调用工厂时创建 client**，而是在真正调用返回的
    ``judge_fn`` 时才惰性创建 boto3 client（避免在无 AWS 凭证/无网络的单测环境报错）。
    """

    def judge_fn(prompt: str) -> str:
        import boto3  # 惰性导入，避免模块级依赖 boto3。

        client = boto3.client("bedrock-runtime", region_name=region)
        resp = client.converse(
            modelId=model_id,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"temperature": 0, "maxTokens": 4096},
        )
        return resp["output"]["message"]["content"][0]["text"]

    return judge_fn
