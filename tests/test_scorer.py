"""scorer 模块单测：用假 judge_fn 注入预设 JSON，验证 coverage/accuracy 计算。

不触碰 AWS，不真调 Bedrock。
"""

import json

from src import scorer


def make_judge(payload):
    """返回一个忽略 prompt、总是吐出给定文本的假裁判。

    payload 为 str 时原样返回；为 dict 时序列化成 JSON。
    """

    def judge_fn(prompt: str) -> str:
        return payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)

    return judge_fn


# 两条抽取 / 两条 GT 的公共样例数据。
EXTRACTED = [
    {"设备主体": "液氮储罐", "设备部件": "下进液管", "指标名称": "结构", "指标特征": "末端防涡装置", "原文": "下进液管末端设置防涡装置"},
    {"设备主体": "内罐", "设备部件": "对接接头", "指标名称": "焊接", "指标特征": "全焊透", "原文": "内罐所有对接接头采用全焊透结构"},
]
GT = [
    {"主体": "液氮储罐", "部件": "下进液管", "特征值": "末端设置防涡装置", "原文": "(16) 下进液管末端设置防涡装置"},
    {"主体": "内罐", "部件": "对接接头", "特征值": "全焊透结构", "原文": "内罐所有对接接头采用全焊透结构"},
]


def test_full_match():
    """两条全部匹配且四字段全对 -> coverage=1.0, accuracy=1.0。"""
    payload = {
        "alignments": [
            {"gt_index": 0, "extracted_index": 0,
             "field_judgments": {"主体": "正确", "部件": "正确", "特征值": "正确", "原文": "正确"}},
            {"gt_index": 1, "extracted_index": 1,
             "field_judgments": {"主体": "正确", "部件": "正确", "特征值": "正确", "原文": "正确"}},
        ]
    }
    result = scorer.score(EXTRACTED, GT, make_judge(payload))
    assert result["coverage"] == 1.0
    assert result["accuracy"] == 1.0
    assert result["num_extracted"] == 2
    assert result["num_gt"] == 2


def test_partial_and_missed():
    """gt0 匹配但含部分/错误字段，gt1 漏抽 -> coverage=0.5, accuracy=0.625。

    gt0 字段判定 [正确=1, 部分=0.5, 错误=0, 正确=1] = 2.5 / 4 = 0.625
    gt1 extracted_index=null（漏抽），不贡献字段分。
    """
    payload = {
        "alignments": [
            {"gt_index": 0, "extracted_index": 0,
             "field_judgments": {"主体": "正确", "部件": "部分", "特征值": "错误", "原文": "正确"}},
            {"gt_index": 1, "extracted_index": None, "field_judgments": {}},
        ]
    }
    result = scorer.score(EXTRACTED, GT, make_judge(payload))
    assert result["coverage"] == 0.5
    assert result["accuracy"] == 0.625


def test_all_missed():
    """全部漏抽 -> coverage=0.0；无可比字段 -> accuracy=None。"""
    payload = {
        "alignments": [
            {"gt_index": 0, "extracted_index": None, "field_judgments": {}},
            {"gt_index": 1, "extracted_index": None, "field_judgments": {}},
        ]
    }
    result = scorer.score(EXTRACTED, GT, make_judge(payload))
    assert result["coverage"] == 0.0
    assert result["accuracy"] is None


def test_no_gt():
    """无 Ground Truth -> coverage/accuracy 均为 None，且不调用裁判。"""
    def exploding_judge(prompt: str) -> str:
        raise AssertionError("gt 为空时不应调用裁判")

    result = scorer.score(EXTRACTED, [], exploding_judge)
    assert result["coverage"] is None
    assert result["accuracy"] is None
    assert result["num_gt"] == 0
    assert result["num_extracted"] == 2


def test_robust_json_parsing():
    """裁判输出被 ```json 围栏和多余文字包裹时仍能解析。"""
    inner = {
        "alignments": [
            {"gt_index": 0, "extracted_index": 0,
             "field_judgments": {"主体": "正确", "特征值": "部分"}},
            {"gt_index": 1, "extracted_index": None, "field_judgments": {}},
        ]
    }
    wrapped = "好的，这是我的判定结果：\n```json\n" + json.dumps(inner, ensure_ascii=False) + "\n```\n以上。"
    result = scorer.score(EXTRACTED, GT, make_judge(wrapped))
    # 匹配 1 条 -> coverage=0.5；字段 [正确=1, 部分=0.5] -> accuracy=0.75
    assert result["coverage"] == 0.5
    assert result["accuracy"] == 0.75


def test_english_verdicts():
    """兼容英文判定标签 correct/partial/wrong。"""
    payload = {
        "alignments": [
            {"gt_index": 0, "extracted_index": 0,
             "field_judgments": {"主体": "correct", "部件": "partial", "特征值": "wrong"}},
            {"gt_index": 1, "extracted_index": None, "field_judgments": {}},
        ]
    }
    result = scorer.score(EXTRACTED, GT, make_judge(payload))
    assert result["coverage"] == 0.5
    # [1, 0.5, 0] / 3 = 0.5
    assert result["accuracy"] == 0.5
