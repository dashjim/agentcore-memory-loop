# Design: Memory-Loop 自学习信息抽取 Demo

> 承载方式：**AgentCore Harness（Model A）** — 用户指定、build-agent 首选、无容器、最快 time-to-demo。
> 编排：**Harness Skill 驱动、Agent 自主执行**（非外层 Python 循环）。区域：us-west-2。

## 1. Architecture Overview

```
                         ┌───────────────────────────────────────────┐
  本地 Python 驱动(薄)     │              AWS (us-west-2)                │
  (单次invoke+采指标+门禁)  │                                            │
        │  invoke_harness   │   ┌─────────────────────────────────┐      │
        ├──────────────────►│   │  Extraction Harness             │      │
        │                   │   │  (Bedrock Claude Sonnet 4.6)    │      │
        │ ◄── stream ───────┤   │  system-prompt: 人设+红线(短)    │      │
        │  (结果+token+耗时)  │   │  skill: scope-extract(SOP/循环) │      │
        │                   │   │  tools: recall_lessons/record   │──┐   │
        │                   │   └─────────────────────────────────┘  │   │
        │  create_event /   │        agent 内部自主跑:                 ▼   │
        │  retrieve_memories│   recall→抽取→自审→修订(≤4)→reflect→record  │
        ├──────────────────►│   ┌─────────────────────────────────┐      │
        │                   │   │  AgentCore Memory               │      │
        │                   │   │  mode: none | episodic | custom │      │
        │                   │   │  custom: M_strat + M_tact 双 ns  │      │
        │                   │   └─────────────────────────────────┘      │
        ▼                   └───────────────────────────────────────────┘
  本地 runs 存储(SQLite/JSON) ◄── scorer.py (LLM-as-judge vs GT)
        ▲
        │  读
  本地 Web UI (FastAPI+单页): 清除记忆/跑抽取/轮数·耗时·Token/完成判定/A·B·C 面板
```

**Components:**

| Component | Responsibility | AgentCore Service |
|-----------|---------------|-------------------|
| Extraction Harness | 承载抽取 agent，执行 skill 驱动的反思循环 | Harness |
| scope-extract Skill | 过程化 SOP：recall→抽取→自审→修订→reflect→record | Skills |
| memory_tools（record/recall） | 双 namespace 记忆读写工具 | Memory + inline_function/MCP |
| AgentCore Memory | 长期记忆沉淀与检索注入（3 模式） | Memory |
| orchestrator.py（薄驱动） | 单次 invoke、采指标、结果合规门禁、落盘 | — |
| scorer.py | LLM-as-judge 对齐+打分 vs GT | Bedrock |
| runstore.py | 指标存储（SQLite/JSON） | — |
| ui/ | 本地 Web UI（控件+A/B/C 面板） | — |

## 2. Project Structure

```
memory-loop/
├── docs/
│   ├── requirements-memory-loop.md
│   ├── design-memory-loop.md
│   └── e2e-test-report-memory-loop.md   # Phase 3 生成
├── input/                    # extraction-item.txt + input-samples-output.zip(+解压语料)
├── agent/
│   ├── agentcore.json        # 工程配置
│   ├── app/memory-loop/harness.json
│   ├── app/memory-loop/system-prompt.md
│   └── skills/scope-extract/SKILL.md
├── src/
│   ├── orchestrator.py       # 薄驱动：invoke+采指标+门禁+落盘
│   ├── memory_tools.py       # record_lesson/recall_lessons + create_event/retrieve
│   ├── scorer.py             # LLM-as-judge 评分(可单测)
│   └── runstore.py           # SQLite/JSON 指标存储
├── ui/                       # FastAPI + 单页(控件+A/B/C 面板)
├── scripts/                  # 初始化Memory、解压语料、本地运行/部署、cleanup
└── tests/                    # scorer 等单测
```

## 3. Component Design

### 3.1 Extraction Harness
**Purpose:** 承载抽取 agent。
**Reference Code:** `01-features/01-harness/02-use-cases/01-travel-agent/travel_agent.py`
**Key Adaptations:** 挂 `scope-extract` skill + 双记忆工具；system-prompt 精简为人设+红线（流程放 skill）；`maxIterations` 调足以容纳内部反思循环。
**Implementation Details:**
- model `global.anthropic.claude-sonnet-4-6`；`invoke_harness(harnessArn, runtimeSessionId=UUID(≥33), messages, skills=[{"path":".agents/skills/scope-extract"}], actorId=...)`。
- 从响应流 `metadata` 事件取 token；`messageStop` 判定结束。

### 3.2 scope-extract Skill
**Purpose:** 把 ReAct/反思编排写成 agent 自主执行的 SOP。
**Reference Code:** `.../05-agent-skills/`、`.../multi-quarter-trend-analysis/SKILL.md`（证明 Skill 可含步骤/循环/条件/工具调用）。
**Implementation Details:** frontmatter `allowed-tools: [recall_lessons, record_lesson]`；正文编号 Steps：
1. `recall_lessons("strat")`+`recall_lessons("tact")` 读规则入上下文
2. 按 extraction-item schema 抽取（应用规则）→ JSON
3. 自审：对照 criteria（schema完整/无幻觉/格式/一致性）列违规
4. 若有违规且 `revision_count<4`：修订→自增→回 Step 3；否则继续
5. 反思：跨任务规则→`record_lesson("strat",…)`；本文档技巧→`record_lesson("tact",…)`
6. 输出最终 JSON，并自报 `revision_count`

### 3.3 memory_tools（record_lesson / recall_lessons）
**Purpose:** 双 namespace 记忆读写。
**Reference Code:** `06-workshops/04-AgentCore-memory/.../meeting-notes-assistant.py`
**Implementation Details:**
- `record_lesson(scope,text)` → `create_event(memory_id, actor_id, session_id, messages=[(text,"ASSISTANT")])`，namespace 由 scope 决定（`/strategy/{actorId}/` 或 `/tactic/{actorId}/{sessionId}/`）。
- `recall_lessons(scope,query)` → `retrieve_memories(memory_id, namespace, query)`。
- 暴露方式：Phase 1 用 **inline_function**（agent 发 tool_use → 驱动执行 → 回传 toolResult），或 remote MCP（无需外层介入）。默认 inline_function（本地可控）。

### 3.4 scorer.py（LLM-as-judge）
**Purpose:** vs GT 覆盖率+准确率。
**Implementation Details:** judge（Bedrock Claude, `temperature=0`）输入抽取项+GT 项 → 输出一对一对齐 + 逐字段 `正确/部分/错误` + 理由（JSON）。覆盖率=匹配GT数/GT总数；准确率=字段级正确率（部分=0.5）。存档 judge 输出。降级：`原文+部件` 归一化模糊匹配。**可单测**。

### 3.5 orchestrator.py（薄驱动，不做编排）
载入 markdown+tables → `invoke_harness`（新 session、带 skill、传 actorId）→ 结果合规门禁（仅判 JSON 合法/必填非空/条目非空，不合规补一次 invoke）→ 落盘（反思轮数/耗时/token）。

### 3.6 ui/（本地 Web UI）
FastAPI + 单页。控件：文档、记忆模式、清除记忆、跑抽取。面板：完成（自审✓/覆盖率/准确率/指示灯）、A（轮数折线）、B（三模式对比柱）、C（M_strat/M_tact 规则列表，实时查 Memory）、历史表。中文。

## 4. AgentCore Integration

### 4.1 Harness
```python
import boto3
cp = boto3.client("bedrock-agentcore-control", region_name="us-west-2")
dp = boto3.client("bedrock-agentcore", region_name="us-west-2")
# create/update harness: systemPrompt / tools(inline_function) / model / memory / maxIterations
resp = dp.invoke_harness(harnessArn=ARN, runtimeSessionId=str(uuid4())*2[:36],
                         actorId="memory-loop", skills=[{"path":".agents/skills/scope-extract"}],
                         messages=[{"role":"user","content":[{"text": doc_text}]}])
for ev in resp["stream"]:
    ...  # contentBlockDelta 取文本; metadata 取 token
```
**Configuration:** `HARNESS_ARN`、`MEMORY_ID`、`AWS_REGION=us-west-2`、`ACTOR_ID`、`MEMORY_MODE`。
**Error Handling:** poll harness 到 `READY`（非裸 FAILED）；invoke 流里 `runtimeClientError` 需捕获重试。

### 4.2 Memory
```python
# create_memory(memoryStrategies=[{... SEMANTIC / EPISODIC / CUSTOM ...}]) ; poll ACTIVE(3-5min)
dp.create_event(memoryId=MID, actorId=ACTOR, sessionId=SID, messages=[(text,"ASSISTANT")])   # 写
recs = MemoryClient(...).retrieve_memories(memory_id=MID, namespace=NS, query=q)             # 读
```
**Configuration:** namespaces `M_strat=/strategy/{actorId}/`、`M_tact=/tactic/{actorId}/{sessionId}/`；`retrievalConfig` 按 ns 设 topK/relevanceScore。
**Error Handling:** Memory 建成需 poll 到 ACTIVE；episodic 异步提炼有延迟，UI 标注/轮询。

## 5. Data Flow

```
1. UI → orchestrator：选文档+记忆模式+跑抽取
2. orchestrator → invoke_harness(带 scope-extract skill, actorId)
3. Harness/agent 内部：recall_lessons(Memory) → 抽取 → 自审 → 修订(≤4) → reflect → record_lesson(Memory)
4. agent → orchestrator：最终 JSON + revision_count；流中带 token
5. orchestrator → 结果合规门禁 → 落盘(runstore) 抽取CSV+指标
6. scorer(LLM-as-judge) → 覆盖率/准确率 vs GT → 落盘
7. UI ← runstore + Memory(实时)：更新 A/B/C 面板与完成指示
```

## 6. Configuration

### Environment Variables
| Variable | Purpose | Example |
|----------|---------|---------|
| AWS_REGION | 区域 | us-west-2 |
| HARNESS_ARN | 抽取 harness | arn:aws:bedrock-agentcore:us-west-2:...:harness/... |
| MEMORY_ID | Memory 资源 | mem-... |
| ACTOR_ID | 记忆作用域实体 | memory-loop |
| MEMORY_MODE | none/episodic/custom | custom |
| JUDGE_MODEL_ID | 评分模型 | global.anthropic.claude-sonnet-4-6 |

### IAM Permissions
```json
{
  "Effect": "Allow",
  "Action": ["bedrock:InvokeModel","bedrock:InvokeModelWithResponseStream",
             "bedrock-agentcore:InvokeHarness","bedrock-agentcore:CreateEvent",
             "bedrock-agentcore:RetrieveMemoryRecords","bedrock-agentcore:ListEvents",
             "bedrock-agentcore:GetEvent"],
  "Resource": "arn:aws:bedrock-agentcore:us-west-2:<account>:*"
}
```
（Resource 实现时收紧到具体 harness/memory ARN。）

## 7. Security Design

**MANDATORY.**

### Authentication
- **Phase 1（本次）：** UI 仅 localhost，无对外认证（Method: None，本地开发）；不暴露公网。
- **Phase 2：** WebUI 加 **Cognito JWT**（User Pool + Web Client GenerateSecret=false + OIDC discovery + Runtime customJWTAuthorizer），CloudFront 托管。见 `references/webui-auth-patterns.md`。

### IAM Permissions (Least Privilege)
| Role | Permissions | Resource Scope |
|------|------------|----------------|
| 执行角色 | bedrock:InvokeModel*、Memory CreateEvent/Retrieve/List/Get、InvokeHarness | 具体 harness/memory ARN，非 `*` |

### Security Prohibitions
- [x] 无 Lambda Principal:"*"（本项目无 Lambda）
- [x] 无 EC2 端口开放 0.0.0.0/0
- [x] 无 S3 公开访问
- [x] 无硬编码凭据（用 AWS profile/env）
- [x] GT 数据绝不喂给 agent（防泄漏）

### WebUI Deployment Architecture
Phase 2 才涉及：`CloudFront → Browser → Cognito → AgentCore`（非 proxy/Lambda 模式）。Phase 1 无。

## 8. Deployment Design

**Method:** **AgentCore CLI `@aws/agentcore`（1.0.0-preview.29，已装 `~/.npm-global/bin/agentcore`）**。注意与旧的 `bedrock-agentcore-starter-toolkit`（同名 `agentcore`，在 `~/.local/bin`）区分——**本项目用前者**。
**Steps:**
1. `agentcore create`（默认建 harness 项目）→ `agentcore add memory`（按模式 none/shortTerm/longAndShortTerm）→ `add tool`（记忆工具）→ `add skill`（scope-extract）。
2. **本地测试 = `agentcore dev`**（`--skip-deploy` 纯本地；无 `deploy --local`）；或本地 Python 驱动经 boto3 `invoke_harness` 打云端 harness。跑通 A/B/C。
3. `agentcore deploy`（CDK）到 us-west-2（agent 侧）。
4. cleanup：`agentcore remove ...` 或 `delete-harness`/`delete-memory`。

**Infrastructure Resources:**
| Resource | Type | Purpose |
|----------|------|---------|
| Extraction Harness | AgentCore Harness | 承载 agent |
| Memory 资源 | AgentCore Memory | 长期记忆（按模式建/删） |
| 执行角色 | IAM Role | 最小权限 |

## 9. Testing Plan

### Unit Tests
- `scorer.py`：对已知抽取/GT 小样本，覆盖率/准确率给出稳定值；judge 输出解析健壮性。
- `memory_tools.py`：scope→namespace 路由正确。

### Integration Tests
- 三模式各跑一次单文档，能拿到抽取结果+指标+评分。

### End-to-End Demo Script
1. 清除记忆 → custom 模式跑文档A 3 次 → 反思轮数递减（SC-1）。
2. custom 预热后跑新文档B vs 空记忆跑B → 首轮覆盖率/准确率对比（SC-2）。
3. UI 规则面板显示累积 guidelines（SC-3）。
4. 完成面板显示自审✓+覆盖率+准确率（SC-4）。
5. （部署后）用 agentcore-browser 对本地 UI 做 E2E 截图存证。

## 10. Implementation Plan

**Parallel workstreams（多 agent 并行实现）:**

| Agent | Scope | Files | Dependencies |
|-------|-------|-------|-------------|
| A1 | 语料解压+索引+GT 加载 | scripts/prepare_corpus.py、src/corpus.py | input.zip |
| A2 | Harness/Skill/system-prompt/工具配置 | agent/*、src/memory_tools.py | harness-guide |
| A3 | scorer(LLM-as-judge)+单测 | src/scorer.py、tests/ | GT 结构 |
| A4 | 薄驱动 orchestrator + runstore | src/orchestrator.py、src/runstore.py | A2 接口约定 |
| A5 | 本地 UI（控件+A/B/C 面板） | ui/* | runstore/Memory 读接口 |

**Sequential steps（须按序）:**
1. 先核对 CLI 本地运行命令 + 解压语料（阻塞后续）。
2. 建 Harness+Memory+Skill+工具（A2）→ 打通单次 invoke。
3. 接入 scorer/orchestrator/runstore → 跑通指标。
4. UI 接线 → A/B/C 可视化。
5. 本地 E2E 验证 → agentcore deploy。

## 11. Lessons Learned (Post-Implementation)

| Issue | Root Cause | Fix Applied |
|-------|-----------|-------------|
| 覆盖率大面积 0.0（假零） | 模型抽取 JSON 的字符串值内含**未转义英文引号**（如原文「"液封"」）→ 整个数组非法→解析为空 | parser 加 `json_repair` 兜底（救回 100 条）；system-prompt 增"值内引号用中文「」" |
| LLM-judge 时而返回全 null | ~90×123 条一次性对齐→输出过大截断/摆烂 | scorer 改 **GT 分块对齐**（每块 20 条）+ judge temperature=0 + maxTokens 8192 |
| judge 直连 Bedrock 报 API Key 错 | 会话角色 `My_EC2_SSM_Role` 无 Bedrock 直连权限 | LLM-judge **复用 harness 承载**（override 评审提示、清空 skills/tools） |
| 记忆刚写读不到 / namespace 不符 | SEMANTIC 策略异步抽取、其记录 namespace 与写入 metadata 不一致 | 改 `create_event` 写 + `list_events` **精确即时读**；`create_event` 必带 eventTimestamp、`list_events` sessionId 必填 |
| InvokeHarness 无 memoryId 入参 | 记忆绑定是资源侧的 | episodic 用单独 harness `extractor_ep`（`add harness --memory-name episodicMem`）；custom 走客户端工具回路写 customMem |
| 装的 `agentcore` 是旧 starter-toolkit | 两工具同名、PATH 冲突 | 用 `@aws/agentcore` CLI；harness 无 `deploy --local`，本地=`agentcore dev` 或 boto3 invoke_harness |
| custom 工具回路 token 暴涨（最高 959k） | 客户端多轮 invoke + 冗长反思 | 已知成本项；本场景 Episodic 效果更优、成本更低（见 e2e 报告） |

**效果结论：** 见 `e2e-test-report-memory-loop.md`——Memory 效果在本工业抽取场景主要体现在 **Episodic 覆盖率随运行上升(0.82→0.87)、准确率高(~0.90)、成本低**；custom SCOPE 机制完整且规则可观测自进化（M_strat v1→增补→v2），但 token 昂贵。与博客"反思轮数递减"不同。

## 12. Cleanup
```bash
# 删 Memory / Harness（占位，实现时以实际命令为准）
agentcore remove all         # 或按 CLI --help
aws bedrock-agentcore-control delete-memory --memory-id "$MEMORY_ID" --region us-west-2
```

---

## 附：Phase 划分
- **Phase 1（本次）**：本地 UI + agent 侧（Harness/Memory）部署 us-west-2；三记忆模式；SCOPE skill 反思循环；LLM-as-judge 评分；A/B/C 可视化。无 Cognito、无 ALP。
- **Phase 2（后续）**：WebUI Cognito JWT 认证 + UI 上 CloudFront；ALP portal 包；θ_base 的 Optimization 慢环演化。
