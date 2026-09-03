# V3 设计文档：self-managed 策略托管的自学习记忆（仅设计，未实现）

> 状态：**设计稿**，尚未实现/未跑实验。定位：在 V1（内置 EPISODIC 托管、schema 固定）与 V2（完全自管、不用 strategy）之外的第三条路径。
> 依据：官方 `memory-self-managed-strategies.html` + boto3 `create_memory` schema（见 [V1 §A.4](技术报告-memory-loop.md)）。

## 1. 目标与定位

保留 **V2 的 Agent 抽取方式**（Agent 单次 invoke 抽取文档，我们不用内置策略、也不用 built-in override），但把**记忆的提炼/合并**交给 **AgentCore Memory 的 self-managed 策略**托管触发，并用 **`BatchCreateMemoryRecords` 按我们自定义的规则 schema** 写回。

| | V1 episodic | V2 custom | **V3 self-managed** |
|---|---|---|---|
| 记忆提炼由谁做 | AgentCore 内置 EPISODIC（托管、AWS 提示词） | 我们 orchestrator 同步调 LLM | **AgentCore 触发 + 我们的 Lambda**（异步、我们的逻辑） |
| 记录 schema | 固定（situation/intent/reflection…） | 自定义（我们存事件文本） | **自定义 memoryRecordSchema**（唯一能定制结构的托管方式） |
| 触发/存储 | 托管 | 我们自管 | 托管触发 + 托管存储 |
| 召回 | topK 语义自动注入 | 确定性全量注入 canonical | topK 语义（retrieve/自动注入） |

即 V3 = **"托管的触发+存储+调度" + "我们自定义的提炼逻辑与规则结构"**。

## 2. 架构

```mermaid
flowchart TD
  A["Agent 单次 invoke 抽取文档<br/>(同 V2, 无工具回路)"] --> EV["create_event 写会话事件<br/>(doc + 抽取结果)"]
  EV --> TRG{"self-managed 触发条件<br/>messageCount / idleTimeout / tokenCount 满足?"}
  TRG -- 否 --> WAIT["累积, 暂不提炼"]
  TRG -- 是 --> SNS["AgentCore: 发 SNS 通知<br/>+ 投递会话 payload 到我们的 S3"]
  SNS --> LMB["我们的 Lambda: 读 S3 payload<br/>→ 反思/合并(沿用 V2 的 reflect+consolidate 逻辑)<br/>→ 产出**自定义 schema** 的规则记录"]
  LMB --> WB["BatchCreateMemoryRecords / Update / Delete 写回<br/>(自定义 memoryRecordSchema + namespace)"]
  WB --> MEM[("AgentCore Memory<br/>规则记录")]
  MEM -. "下轮 retrieve / 自动注入(topK语义)" .-> A
  classDef mgd fill:#fff4e5,stroke:#f5a623; class TRG,SNS,WB,MEM mgd;
  classDef ours fill:#e6f4ea,stroke:#34a853; class A,EV,LMB ours;
```
🟧=AgentCore 托管（触发/投递/存储）；🟩=我们（抽取/Lambda 提炼/写回逻辑）。

## 3. 关键配置（`create_memory` 的 self-managed 策略）
- `customMemoryStrategy.configuration.selfManagedConfiguration`：
  - `triggerConditions`：`messageBasedTrigger.messageCount` / `tokenBasedTrigger` / `timeBasedTrigger.idleSessionTimeout`。
  - `invocationConfiguration`：`topicArn`(SNS) + `payloadDeliveryBucketName`(S3)。
  - `historicalContextWindowSize`：投递给 Lambda 的历史窗口大小。
- 自定义 `memoryRecordSchema`（我们的规则字段结构）+ `namespaceTemplates`。
- **前置资源**：S3 桶、SNS Topic、Lambda、IAM 执行角色（信任 `bedrock-agentcore.amazonaws.com`，且不开公网）。
- 写回用 `BatchCreateMemoryRecords`/`BatchUpdateMemoryRecords`/`BatchDeleteMemoryRecords`。

## 4. 需注意的点（含首读者 review 要求）
1. **异步等待**：触发→SNS→Lambda→写回是异步（分钟级）。两次运行间必须**轮询提炼完成**（`ListMemoryExtractionJobs` 或 retrieve 到稳定）再进行下一轮；实验更慢。
2. **单变量与对照**：与 nomem 比时，"有记忆"的 harness 需绑定该 memory、"无记忆"不绑→**harness 绑定这一残留变量**。建议定位为"**托管管道(V3) vs 自管(V2)**"对照，或用 update_harness 挂/摘保持同一 harness。
3. **冷启动确认**：首轮前确认 retrieve 结果为空（记录运行前/后记录数），否则基线不干净（V1 episodic 的教训）。
4. **召回 topK 语义**：非 V2 的确定性全量；需固定 topK、注入 token 上限，并记录**实际注入了哪些记录**（不能只证明"能读出"，要证明"被注入并起作用"）。
5. **评分**：用**修复后的一对一 scorer**（V2 已修）；judge token 单列；提交脱敏 `runs.db`。
6. **重置**：self-managed 记录可用 `BatchDeleteMemoryRecords` 清（比内置 episodic 好清）；或删/重建 memory 资源。
7. **成本/运维**：多了 S3+SNS+Lambda 与托管提炼调用，运维与成本更重。
8. **安全**：S3/SNS/IAM 最小权限、不开公网；payload 含文档内容→注意机密数据边界（本项目语料机密，S3 桶须私有、不进公开仓库）。

## 5. 实施步骤（若批准建设）
1. 建 S3(私有)+SNS+IAM 角色 → `create_memory` 配 self-managed 策略（triggerConditions + invocationConfiguration + 自定义 memoryRecordSchema）。
2. 写 Lambda：读 S3 payload → 复用 V2 的 reflect+consolidate 逻辑 → `BatchCreateMemoryRecords` 写回。
3. 建/绑定 harness → 抽取沿用 V2 单次 invoke。
4. 实验：nomem vs V3-mem，**每轮等异步提炼完成**再下一轮；冷启动确认；记录注入内容。
5. 用修复后 scorer 评分；出 V3 结果与对 V2 的对照。

## 6. 我的建议
- 先确认**是否值得**为 demo 引入 S3+SNS+Lambda（较重）。若目标是"展示 AgentCore 全托管记忆管道 + 自定义规则结构"，则值得；若只想验证"记忆是否有用"，V2 的单变量已够、无需 V3。
- 若做，规模宜小（few docs），并严格按上面第 4 点的 review 要求执行。
