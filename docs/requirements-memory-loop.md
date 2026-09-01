# Requirements: Memory-Loop 自学习信息抽取 Demo

## 1. Overview

**Demo Name:** memory-loop
**Description:** 复现博客《Self-learning evolvable agents for cultural tourism info extraction with AgentCore》的**核心 Memory 效果**——用单个 AgentCore Harness + AgentCore Memory 构建一个"自学习/可进化"信息抽取 agent：agent 在自己的 Agent Loop 内按一份 Harness Skill 做"回忆经验→抽取→自我 reflection 自审→修订→反思沉淀经验"，把学到的经验写入长期记忆，下次运行检索注入 prompt（SCOPE：`θ_{t+1} ← θ_base ⊕ M_strat ⊕ M_tact`），从而跨运行越跑越好。场景为**工业技术文档信息抽取**（低温储罐技术要求等）。
**Target Audience:** 内部/客户演示——展示 AgentCore Memory 带来的 agent 自学习进化效果。
**Date:** 2026-08-28

## 2. AgentCore Services

| Service | Role in Demo | Key API Operations |
|---------|-------------|-------------------|
| AgentCore Harness | 承载抽取 agent（Model A，配置驱动，无容器） | `create_harness`/`update_harness`/`invoke_harness`（含 `skills`、`tools`、`memory`、`actorId`） |
| AgentCore Memory | 长期记忆：跨运行经验沉淀与检索注入 | `create_memory`、`create_event`、`retrieve_memories`/`retrieve_memory_records`、`list_events` |
| AgentCore Skills | 承载编排/反思循环 SOP（`scope-extract/SKILL.md`），由 agent 自主执行 | `invoke_harness(..., skills=[...])` / `--skill-path` |
| Amazon Bedrock | 抽取模型 + LLM-as-judge 评分模型 | `bedrock:InvokeModel*`（Claude Sonnet 4.6） |
| （可选）Observability | 追踪反思轮数/token（CloudWatch Transaction Search） | trace/log 读取 |

## 3. Functional Requirements

### FR-1: 按 schema 抽取工业技术文档
- **Description:** 从文档的 `markdown_corrected/*.md`（+ `tables/*`）抽取结构化记录 `[{设备主体, 设备部件, 指标名称, 指标特征, 原文}]`（依据 `input/extraction-item.txt`），输出 JSON/CSV。忠实抽取、不臆造、不加单位符号。
- **AgentCore API:** `invoke_harness`
- **Reference Code:** `01-features/01-harness/02-use-cases/01-travel-agent/travel_agent.py`

### FR-2: Skill 驱动的反思（self-review）循环
- **Description:** 编排逻辑写进 `scope-extract/SKILL.md`（编号 Steps：recall→抽取→自审→若违规且轮数<N 则修订回自审→reflect→record→输出），由 agent 在自己的 agent loop 内执行；最多 N=4 轮。外层 Python 不做编排。
- **AgentCore API:** `invoke_harness(..., skills=[{"path":".agents/skills/scope-extract"}])`
- **Reference Code:** `01-features/01-harness/01-advanced-examples/05-agent-skills/`、`.../03-registry/.../multi-quarter-trend-analysis/SKILL.md`

### FR-3: 记忆读写工具（双 namespace）
- **Description:** 挂两个 harness 工具：`record_lesson(scope,text)` 写、`recall_lessons(scope,query)` 读，路由到 `M_strat=/strategy/{actorId}/`（跨任务）与 `M_tact=/tactic/{actorId}/{sessionId}/`（当前任务）。
- **AgentCore API:** `create_event`（写）、`retrieve_memories`（读）；工具经 inline_function 或 remote MCP 暴露。
- **Reference Code:** `06-workshops/04-AgentCore-memory/.../meeting-notes-assistant.py`

### FR-4: 三种记忆模式可切换
- **Description:** `none`（baseline，不挂 Memory）/ `episodic`（内置 EPISODIC 策略）/ `custom`（双 namespace 显式 record/recall）。UI 可切换，用于对比自学习增量价值。
- **AgentCore API:** `create_memory(memoryStrategies=...)` + `update_harness` attach/detach memory

### FR-5: vs GT 的 LLM-as-judge 评分
- **Description:** 抽取结果与 ground-truth CSV（`csv/flattened_data_restructured_*.csv`）用 Bedrock Claude 做 judge：先语义对齐条目，再逐字段判正确；输出覆盖率（召回）+ 字段准确率。judge 用 `temperature=0`、固定 prompt，评分理由存档可复核；judge 不可用时降级为 `原文+部件` 归一化模糊匹配。
- **AgentCore API:** `bedrock:InvokeModel`（judge）

### FR-6: 本地 Web UI
- **Description:** 控件：文档选择 / 记忆模式选择 / **清除记忆** / **跑抽取**；运行态显示当前反思轮次、耗时、token；完成面板显示自审✓、覆盖率%、准确率%、"抽取完成"指示灯；A/B/C 三实验面板 + 历史表。中文 UI。
- **实现:** FastAPI + 单页；数据源=本地 runs 存储（SQLite/JSON）+ 实时查 Memory。

### FR-7: 指标采集与完成判定
- **Description:** 采集反思轮数（从轨迹解析或 agent 自报 `revision_count`）、耗时（wall clock）、token（invoke 响应流 `metadata` 事件）。**完成** = 自审通过 且 覆盖率≥阈值（默认 0.9）；**正确性** = 字段准确率 vs GT。

## 4. Non-Functional Requirements

- **Performance:** 单文档抽取 + ≤4 轮反思在分钟级；episodic 策略异步提炼有 3–5 min 生效延迟，UI 需标注/轮询。
- **Security:** **Phase 1（本地）**：UI 仅 localhost、无 Cognito；agent 侧（Harness+Memory）部署到 AWS。**Phase 2**：WebUI 加 Cognito JWT + CloudFront。IAM 最小权限，Resource 限定 ARN，绝不 0.0.0.0/0、绝不 `Resource:"*"`。GT 绝不喂给 agent。
- **Cost:** Bedrock 抽取 + judge 调用 + Memory 存储；按需建/删资源；提供 cleanup 脚本。
- **Region:** us-west-2

## 5. Tech Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Language | Python | AgentCore SDK/boto3、评分、UI 后端统一 |
| Framework | FastAPI + 单页 HTML | 轻量本地 UI，符合"先本地"与不过度工程 |
| Agent 承载 | AgentCore Harness (Model A) | 用户指定、build-agent 首选、无容器最快 |
| 编排 | Harness Skill（`scope-extract`）+ agent 自主执行 | 用户要求"编排通过 Skill、Agent 执行" |
| IaC | 无（用 agentcore CLI / starter toolkit） | 本地优先、资源少 |
| Deployment | 本地运行 + Harness/Memory 到 AWS us-west-2 | Phase 1 本地；Phase 2 再上 UI |

## 6. Referenced Resources

### Official Documentation
- AgentCore Harness 文档（本地权威底稿 `build-agent/references/harness-guide.md`）：Harness config、CLI、boto3、memory、IAM、streaming。
- AgentCore Memory 策略（SEMANTIC/EPISODIC/CUSTOM）与检索注入机制。

### GitHub Samples（本地 `g-repo/amazon-bedrock-agentcore-samples/`）
- `01-features/01-harness/02-use-cases/01-travel-agent/`：最小 harness + memory 多轮。
- `01-features/01-harness/01-advanced-examples/05-agent-skills/`：harness 装/用 skill。
- `06-workshops/04-AgentCore-memory/.../meeting-notes-assistant.py`：memory 读写/hook 范式。
- `.../04-weather-agent/optimize.py`：θ_base 演化（Optimization，Phase 2 慢环）。

### Other References
- 博客原文（图3 架构、图4 ReAct、图5 SCOPE、图7/8 时序图）已通过 AgentCore Browser 查看，图存 `/tmp/ct-blog-figs/`。
- 抽取 schema：`input/extraction-item.txt`；GT：各文档 `csv/flattened_data_restructured_*.csv`。

## 7. Success Criteria

| # | Criterion | How to Verify |
|---|-----------|---------------|
| SC-1 | 战术记忆生效 | custom 模式同一文档重跑 N 次，反思轮数呈下降趋势（UI 折线图） |
| SC-2 | 战略记忆迁移 | 新文档"预热记忆" vs "空记忆"，首轮覆盖率/准确率更高（UI 柱图） |
| SC-3 | 学习过程可观测 | UI 规则面板实时展示 M_strat/M_tact 累积的 guidelines |
| SC-4 | 完成与正确性可证 | UI 显示自审✓ + 覆盖率% + 准确率%（vs GT，LLM-as-judge） |
| SC-5 | UI 核心功能 | 清除记忆、跑抽取、显示轮数/耗时/token 均可用 |
| SC-6 | 评分可复现 | `scorer.py` 单测对已知样本给出稳定分值 |
| SC-7 | 本地跑通并可上云 | 本地运行成功；`agentcore deploy` 到 us-west-2 成功 |

## 8. Out of Scope

- S3 / EventBridge / Lambda 无服务器 plumbing（用户明确砍掉）。
- 3 子 Agent 拓扑（用单 Harness + Skill 驱动反思替代）。
- **Phase 2 内容（本次不做）**：WebUI Cognito JWT 认证、UI 部署到 AWS（CloudFront）、ALP portal 包生成、θ_base 的 Optimization 慢环演化。

## 9. Open Questions

- （无——设计要点已与用户逐条确认。实现首步需用 CLI `--help` 核对本地运行确切命令：`agentcore dev` vs `agentcore deploy --local`。）
