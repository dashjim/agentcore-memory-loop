# Memory-Loop V3：显式自审经验的跨任务复用

V3 验证一个简单问题：Agent 在复杂文档上形成的自审经验，被 AgentCore
EPISODIC Memory 提炼后，是否会影响下一份文档的抽取行为。

## 1. 生成 Memory

- 源文档：13 页液氮罐技术要求。
- Agent 采用两阶段流程：
  1. 内部形成草稿，只输出结构化 `self_review`；
  2. 根据 `self_review.next_actions` 修订并输出最终 JSON。
- 本次源任务完成后，AgentCore EPISODIC Memory 实际生成：
  - 1 条 session-level episode；
  - 2 条 actor-level reflection。
- source actor：`ep-review-1789102186`。

## 2. 测试单页文档

- 测试文档：`2477080009简图-8.16`，一页电机图纸。
- Memory 组：`extractor_ep_review`，复用 source actor，使用全新 session。
- No Memory 组：`extractor_ep_review_nomem`，使用全新 session。

## 3. 目标抽取的单变量控制

两组目标调用使用完全相同的：

- invocation-level system prompt；
- 模型 `claude-sonnet-4-6`；
- `temperature=0`；
- `maxTokens=32768`；
- `skills=[]`、`tools=[]`；
- 单次抽取与内部自审流程；
- 五字段 JSON 输出要求。

唯一变量是 Harness 是否启用 AgentCore Memory。

## 4. 结果

- Memory 首次运行输出 31 条。
- No Memory 首次运行输出 11 条；为导出完整结果重新运行时输出 10 条。
- `31 vs 11` 是本轮对照结果；10 条仅作为后续完整输出附件。
- Memory 主要多抽取了两张 BOM 表中的零部件和组件。
- 人工初步检查显示，这些新增条目基本能在原文中找到依据，没有明显臆造。

### 4.1 实际生成的 Memory

**Episode reflection**

> 两阶段流程设计有效：先输出 self_review 再执行修订，避免了一次性处理复杂文档时遗漏问题的风险。将自审发现的注释内嵌到对应 JSON 字段（而非单独输出）是良好实践，保证了可追溯性。对于包含 OCR 错误、章节跳号、重复表格和图片内容的复杂技术文档，分阶段结构化抽取是推荐模式。

**Actor-level reflection 1**

- Title：`Two-Phase Structured Extraction for Complex Technical Documents`
- 核心经验：先检查覆盖、遗漏、格式和粒度，再执行结构化抽取；保留原文用于追溯；对无法抽取的图形内容明确说明。

**Actor-level reflection 2**

- Title：`Inline Annotation of Document Quality Issues in Structured Output`
- 核心经验：遇到 OCR 错误、重复表格和冲突信息时，将质量说明放在对应 JSON 记录中，不静默丢弃问题字段。

完整 Memory 原文见 [`memory-loop-v3-results.md`](memory-loop-v3-results.md)。

### 4.2 Memory 组抽取示例

```json
[
  {
    "设备主体": "Y2系列三相异步电动机",
    "设备部件": "整机",
    "指标名称": "型号规格",
    "指标特征": "Y2-160M-4",
    "原文": "型号规格: Y2-160M-4"
  },
  {
    "设备主体": "Y2系列三相异步电动机",
    "设备部件": "转子",
    "指标名称": "装配后运动要求",
    "指标特征": "装配后转子应能灵活转动",
    "原文": "装配后转子应能灵活转动"
  },
  {
    "设备主体": "Y2系列三相异步电动机",
    "设备部件": "机座",
    "指标名称": "零件明细（表1-序号1）",
    "指标特征": "数量：1；代号/材料/重量：原文未填写（均为「-」）",
    "原文": "1 | - | 机座 | 1 | - | - | -"
  },
  {
    "设备主体": "Y2系列三相异步电动机",
    "设备部件": "壳体组件",
    "指标名称": "组件明细（表2-序号1）",
    "指标特征": "数量：1；代号/材料/重量：原文未填写（均为「-」）",
    "原文": "1 | - | 壳体组件 | 1 | - | - | -"
  }
]
```

Memory 组除标题栏和技术要求外，还展开了两张 BOM 表中的零部件和组件。

### 4.3 No Memory 组抽取示例

```json
[
  {
    "设备主体": "Y2系列三相异步电动机",
    "设备部件": "整机",
    "指标名称": "型号规格",
    "指标特征": "Y2-160M-4",
    "原文": "型号规格: Y2-160M-4"
  },
  {
    "设备主体": "Y2系列三相异步电动机",
    "设备部件": "整机",
    "指标名称": "未注公差等级",
    "指标特征": "GB/T 1804-m级",
    "原文": "未注公差按GB/T 1804-m级"
  },
  {
    "设备主体": "Y2系列三相异步电动机",
    "设备部件": "轴承",
    "指标名称": "装配数量",
    "指标特征": "2件",
    "原文": "轴承 | 2"
  }
]
```

No Memory 组主要抽取标题栏、技术要求和少量数量信息，没有系统展开两张 BOM 表。

V3 不报告自动评分，完整输出交由人工比较。

## 5. 完整结果

- Markdown：[`memory-loop-v3-results.md`](memory-loop-v3-results.md)
- JSON：[`memory-loop-v3-results.json`](memory-loop-v3-results.json)
- PPTX：[`记忆能让Agent越跑越好吗-V3.pptx`](记忆能让Agent越跑越好吗-V3.pptx)

复现实验：

```bash
cd memory-loop
python3 scripts/run_experiments_v3.py
```
