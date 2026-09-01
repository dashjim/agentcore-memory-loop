# E2E 测试报告：Memory-Loop 自学习信息抽取

> 复现博客核心"Memory 效果"，工业技术文档抽取，AgentCore Harness + Memory，us-west-2。
> 日期：2026-08-30。本报告按 STAR（Situation/Task/Action/Result）组织。

## Situation（背景）
博客用 AgentCore Runtime + Strands 多 agent + SCOPE 提示进化，展示 agent 靠长期记忆"越跑越好"。本项目在**单 AgentCore Harness + Memory** 上复现其**核心 Memory 效果**，场景换为工业技术文档（低温液氮储罐技术要求）的"设备—部件—指标"抽取，先本地跑通、资源部署到 us-west-2。

## Task（目标）
- 单 Harness + Skill 驱动反思 + 长期记忆自学习；三记忆模式可切换：`无记忆(none) / Episodic(内置) / 自定义双策略(custom, SCOPE)`。
- 用 GT（各文档 `flattened_data_restructured_*.csv`）经 LLM-as-judge 算覆盖率/准确率，如实呈现全部指标。
- 本地 UI 展示 A/B/C 实验；部署到 AWS。

## Action（做法与真机验证）
**已部署（us-west-2, stack `AgentCore-memoryloop-default`）：** Harness `extractor`（none/custom，含 record/recall inline_function 工具）、`extractor_ep`（绑定 episodicMem，native 反思 skill）、Memory `customMem`(SEMANTIC) / `episodicMem`(EPISODIC)、最小权限 IAM 角色。用 **AgentCore CLI `@aws/agentcore`**（`create/add/deploy`，CDK）。

**编排：** 反思循环写进 Harness Skill `scope-extract`（recall→抽取→自审→修订≤4→反思→record），agent 在自身 loop 内执行；外层 Python 仅"单次 invoke + 采指标 + 结果合规门禁 + 落库"。

**记忆（经真机实测确定）：** 用 `create_event` 写 + `list_events` **精确即时**读（弃用异步的 `retrieve_memory_records`）；分区用 sessionId：strat 全局 / tact 按文档。

**评分：** LLM-as-judge 复用 harness 承载（会话角色无直连 Bedrock 权限）；GT 分块对齐、temperature=0。

**E2E：** 13 次真实运行（Phase A 同文档 none×2/episodic×4/custom×4；Phase B 新文档三模式）全部落库；本地 UI 真实模式（`真实模式 src 已接入` 徽标）渲染 A/B/C；本地 headless 浏览器截图存于 `docs/e2e_*.png`（UI 仅 localhost、未暴露公网）。

## Result（真实数据 · 全指标如实呈现）

### Phase A：同一 13 页文档、每模式跨运行
| 模式 | 覆盖率（4 次） | 准确率 | 总 token（典型） | 反思轮 |
|---|---|---|---|---|
| 无记忆 none | 0.764 → 0.780 | ~0.84 | ~35k | 2–3 |
| **Episodic** | **0.821 → 0.837 → 0.870 → 0.854（上升）** | **0.88–0.90** | **~28k（低且稳）** | 1 |
| 自定义 custom | 0.73–0.78（持平） | 0.84–0.89 | **207k–959k（暴涨）** | 多为 None |

### Phase B：新文档（小、GT=6）三模式首轮
| 模式 | 覆盖率 | 准确率 | token |
|---|---|---|---|
| none | 0.667 | 0.692 | ~10k |
| Episodic | 0.667 | 0.5625 | ~18k |
| custom | 0.667 | 0.6875 | ~11k |

### 结论（诚实）
1. **最清晰的"Memory 效果"出现在 Episodic（AgentCore 原生记忆）**：13 页文档上覆盖率随运行上升（0.821→0.870）、准确率最高（~0.90）、token 最低（~28k）、单轮完成。UI 实验B 柱图直观（Episodic 82%/90% 高于 none 76%/85%、custom 75%/84%）。
2. **自定义 SCOPE 工具回路**：机制完整可用，并**可观测地自进化**——M_strat 沉淀出 3 条逐步增补的抽取规则（"经验"→"增补"→"增补v2"，UI 实验C 可见）；但**成本高**（客户端工具回路 + 冗长反思使 token 从 20 万涨到 96 万），覆盖率未见提升。
3. **本场景的效果体现在覆盖率与成本，而非"反思轮数递减"**（博客场景）：Episodic 恒为 1 轮、custom 轮数不稳定。实验A（轮数）面板如实反映这一点。
4. none 基线覆盖率稳定 ~0.77，验证了记忆带来的增量。

### 关键 bug 与修复（过程留痕）
| 现象 | 根因 | 修复 |
|---|---|---|
| 覆盖率大面积 0.0 | 抽取 JSON 字符串值内含**未转义英文引号**（如原文「"液封"」）→ JSON 非法→解析空 | parser 加 `json_repair` 兜底（救回 100 条）+ 提示模型值内用中文引号「」 |
| judge 时而返回假 0 | ~90×123 一次性对齐输出过大→截断/摆烂 | GT 分块对齐 + temperature=0 + 大 maxTokens |
| 会话角色无直连 Bedrock | Converse 报 API Key 错 | LLM-judge 复用 harness 承载 |
| 记忆刚写读不到 | SEMANTIC 异步抽取 + namespace 语义不符 | 改 `list_events` 精确即时读 |

### 复现实验
```bash
cd memory-loop && python3 scripts/run_experiments.py     # 需 AWS 凭据 + config.local.json
cd memory-loop/ui && python3 server.py                   # 本地 UI: http://127.0.0.1:8600
```

### 截图
`docs/e2e_overview.png`（全景）、`e2e_expA_coverage.png`（**A：三模式覆盖率随重跑折线，Episodic 82→84→87→85% 明显上升**）、`e2e_expB_modes.png`（B 柱图）、`e2e_expC_lessons.png`（C 规则自进化）、`e2e_history.png`（13 行历史表）。

### 遗留 / Phase 2
- WebUI Cognito 认证 + CloudFront 部署；ALP portal 包；θ_base 的 Optimization 慢环。
- Episodic 记忆无法经客户端逐条清除（harness 托管）；跨实验重置需删/重建 memory 资源。
- custom SCOPE 工具回路 token 成本高，可优化（减少反思冗长度 / 限制迭代）。
