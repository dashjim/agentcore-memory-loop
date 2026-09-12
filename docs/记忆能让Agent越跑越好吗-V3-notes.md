# 《Agent 记忆最佳实践：结构化数据抽取场景》Speaker Notes

## Slide 1｜Agent 记忆最佳实践

本次汇报讨论一个具体问题：在结构化数据抽取场景中，怎样设计 `Harness Agent` 的执行轨迹，才能让 `AgentCore Memory System` 形成可复用的经验，并在新文档中发挥作用。

本次实验包含两个连续环节：

- 实验一验证 Memory 如何形成：`Application/Orchestrator` 顺序调用 `Harness Agent` 完成两阶段结构化 Self-review；`AgentCore Memory System` 使用内置 `EPISODIC` strategy，从 source session events 中生成 session-level episode 和 actor-level reflection records。
- 实验二验证 Memory 如何使用：`Application/Orchestrator` 在留出文档上控制 Retrieval 开关；`AgentCore Harness` 只在 Memory 组把检索到的 `EPISODIC` records 注入目标 `Harness Agent` 的新 session。

最终观察是：目标 `Harness Agent` 在接收 Memory 上下文后输出 31 条记录；未接收 Memory 时输出 11 条。新增内容主要来自图纸中的两张 BOM。

**过渡：** 在解释这个结果之前，先明确结构化抽取真正困难的地方。

## Slide 2｜结构化抽取真正难在哪里

`Harness Agent` 生成合法 JSON 并不困难，真正困难的是完整覆盖原文。

工业文档的信息可能分散在正文、技术要求、BOM 表格、附注、图纸说明和 OCR 结果中。`Harness Agent` 往往优先识别明显的参数和数值，却可能把整张 BOM、某个章节或图片区域当成背景材料。

因此，`Harness Agent` 输出的 JSON 即使格式正确，也可能只覆盖技术要求，没有覆盖表格中的零部件和组件。

这个问题涉及四类责任：

- `Harness Agent` 负责阅读当前文档、形成抽取草稿、执行 Self-review、修订并输出最终 JSON。
- `Application/Orchestrator` 负责调用顺序、session 管理、模型配置、Memory 开关和实验控制。
- `AgentCore Memory System` 负责 event storage、托管 Extraction、Consolidation、Reflection 和 Retrieval。
- `Reviewer/Human` 负责对照原文判断忠实性、完整性、粒度和业务边界。

核心挑战不是“是否生成了 JSON”，而是“`Harness Agent` 如何发现自己漏了什么，以及 `AgentCore Memory System` 如何把有效的 Review 轨迹转化为后续任务可复用的方法”。

**过渡：** 下一页用一条端到端责任链说明四个主体如何协作。

## Slide 3｜端到端责任链：从源任务到新文档

整套实验应按以下责任链理解：

1. **源文档提交：** `Application/Orchestrator` 为 source actor 创建 source session，并把 13 页液氮罐技术要求、抽取指令和运行配置提交给 `Harness Agent`。
2. **两阶段 Self-review：** `Application/Orchestrator` 顺序发起两次调用；`Harness Agent` 第一阶段对照原文形成结构化 `self_review` 和 `next_actions`，第二阶段根据 `next_actions` 修订并输出最终 JSON。
3. **Event Storage：** `AgentCore Memory System` 按 actor/session 保存源文档输入、结构化 `self_review`、修订请求和最终输出等 raw events。
4. **EPISODIC 处理：** `AgentCore Memory System` 使用内置 `EPISODIC` strategy，异步执行 Extraction、Consolidation 和 Reflection，生成 session-level episode 与 actor-level reflection records。
5. **目标任务 Retrieval：** `Application/Orchestrator` 使用同一 actor 创建新的 target session；`AgentCore Memory System` 按 actor 检索相关 `EPISODIC` records。
6. **上下文注入与抽取：** `AgentCore Harness` 把 Retrieval 返回的 records 注入目标 `Harness Agent` 的上下文；目标 `Harness Agent` 依据当前留出文档完成抽取、自审和最终输出。
7. **结果评审：** `Reviewer/Human` 对照目标原文评判新增记录是否有依据，以及拆分粒度是否符合业务要求。

这条链路中，`Harness Agent` 负责业务推理，`Application/Orchestrator` 负责实验编排，`AgentCore Memory System` 负责托管记忆处理，`AgentCore Harness` 负责 Retrieval 结果的上下文注入，`Reviewer/Human` 负责质量判断。

**过渡：** 为了分别验证 Memory 的生成和使用，我们把责任链拆成两项边界清晰的实验。

## Slide 4｜两项实验地图

**实验一：源任务生成托管 EPISODIC Records。**

`Application/Orchestrator` 把 13 页液氮罐技术要求提交给 `Harness Agent`，并顺序组织两阶段结构化 Self-review。`AgentCore Memory System` 保存 source session events，再使用内置 `EPISODIC` strategy 执行 Extraction、Consolidation 和 Reflection。

实验一回答两个问题：

- `Harness Agent` 应留下怎样的 Review 与修订轨迹？
- `AgentCore Memory System` 能否从该轨迹中形成可检索的 session-level episode 和 actor-level reflection records？

**实验二：留出文档 Retrieval 开关对照。**

`Application/Orchestrator` 为 Memory 组和 No Memory 组分别创建全新 target session，并保持目标文档、system prompt、模型参数及工具配置一致。唯一变量是 `AgentCore Memory System` 是否执行 Retrieval，以及 `AgentCore Harness` 是否向目标 `Harness Agent` 注入检索 records。

实验二回答一个问题：

- 相同目标任务中，接收 `EPISODIC` records 是否会改变目标 `Harness Agent` 的抽取覆盖范围？

实验一产生 Memory，实验二使用并验证 Memory。两个实验前后衔接，但证据边界不同。

**过渡：** 先进入实验一，观察 source session 如何形成可被托管 Memory 处理的轨迹。

## Slide 5｜实验一：源任务生成托管 EPISODIC Records

实验一的 source document 是 13 页液氮罐技术要求，source actor 是 `ep-review-1789102186`。

三个主体承担不同责任：

- `Application/Orchestrator` 创建 source session，顺序发起两阶段调用，并保证原文、`self_review`、`next_actions` 和最终 JSON 位于连续的任务轨迹中。
- `Harness Agent` 阅读源文档、形成内部抽取草稿、对照原文执行结构化 Self-review，并根据 Review 结果完成修订。
- `AgentCore Memory System` 保存 source session events，并使用内置 `EPISODIC` strategy 异步提炼 records。

实验一不是让 `AgentCore Memory System` 直接抽取液氮罐业务字段。业务抽取、自审和修订均由 `Harness Agent` 执行；托管 Memory 处理发生在这些 events 已形成之后。

实验一的成功标准也不是输出记录越多越好，而是 source session 是否形成了明确的“原文输入、Review 发现、修订动作、最终结果”证据链，以及 `AgentCore Memory System` 是否据此生成了可检索 records。

**过渡：** 下一页展开 `Application/Orchestrator` 和 `Harness Agent` 如何共同完成两阶段 Self-review。

## Slide 6｜Application 顺序调用 Harness Agent 两阶段 Self-review

第一阶段由 `Application/Orchestrator` 发起，由 `Harness Agent` 执行。

`Application/Orchestrator` 向 `Harness Agent` 提供 13 页源文档和第一阶段指令。`Harness Agent` 在内部形成抽取草稿，并对照原文检查：

- `coverage`：正文、表格、附注和图示区域是否得到覆盖；
- `omissions`：是否遗漏章节、参数、组件或限制条件；
- `format`：最终结构是否满足字段和 JSON 约束；
- `granularity`：内容是否存在不合理合并或过度拆分。

第一阶段的可观察产物是结构化 `self_review` 与可执行的 `next_actions`，而不是最终 JSON。

第二阶段仍由 `Application/Orchestrator` 发起，并由同一 source session 中的 `Harness Agent` 执行。`Application/Orchestrator` 把源文档、`self_review.next_actions` 和最终输出约束提交给 `Harness Agent`；`Harness Agent` 逐项落实修订动作并输出最终 JSON。

`Harness Agent` 负责 Review 内容和业务修订；`Application/Orchestrator` 负责调用顺序、输入连续性和输出门控。`AgentCore Memory System` 在这两个阶段只保存 events，不负责生成 `self_review` 或最终业务 JSON。

**过渡：** source session 形成完整轨迹后，处理主体切换为 `AgentCore Memory System`。

## Slide 7｜Memory System EPISODIC 处理与 Harness Retrieval/Injection

`AgentCore Memory System` 使用的是内置 `EPISODIC` strategy，处理分为以下阶段：

1. **Event Storage：** `AgentCore Memory System` 按 actor/session 保存 `Application/Orchestrator` 与 `Harness Agent` 交互形成的 raw events。
2. **Extraction：** `AgentCore Memory System` 从 source session events 中识别值得保留的任务过程、Review 发现、修订动作和结果。
3. **Consolidation：** `AgentCore Memory System` 把当前 source session 的关键过程整理为 session-level episode，作用域为当前 actor/session，namespace 为 `/episodes/{actorId}/{sessionId}`。
4. **Reflection：** `AgentCore Memory System` 从 episode 中抽象跨 session 可复用的方法，形成 actor-level reflection records，作用域为当前 actor，namespace 为 `/episodes/{actorId}`。

当实验二的新 target session 开始时：

5. **Retrieval：** `AgentCore Memory System` 按 source actor 检索相关 session-level episode 和 actor-level reflection records。
6. **Injection：** `AgentCore Harness` 把 Retrieval 返回的 records 放入目标 `Harness Agent` 的新 session 上下文。
7. **Target reasoning：** 目标 `Harness Agent` 使用当前留出文档、抽取指令和注入的方法性 Memory 完成抽取与内部自审。

`EPISODIC` 处理是异步的，短 session 不保证一定生成 records。本次 source session 包含完整的原文、Review、修订和结果轨迹，最终形成了可检索记录。

**过渡：** 下一页展示 `AgentCore Memory System` 实际生成的 record 数量、类型、作用域和内容。

## Slide 8｜实际生成：1 Episode + 2 Actor Reflections

`AgentCore Memory System` 使用内置 `EPISODIC` strategy，从 source session 中实际生成了：

- **1 条 session-level episode：** 由 Consolidation 阶段形成，作用域是 actor `ep-review-1789102186` 的当前 source session。
- **2 条 actor-level reflections：** 由 Reflection 阶段形成，作用域是 actor `ep-review-1789102186`，可供该 actor 的后续新 session 检索。

session-level episode 主要总结本次任务发生了什么：`Harness Agent` 使用两阶段流程，先输出结构化 `self_review`，再根据 `next_actions` 修订；面对 OCR 错误、章节跳号、重复表格和图片内容限制时，`Harness Agent` 应显式处理并保留可追溯信息。

两条 actor-level reflections 主要抽象未来可复用的方法：

- `Harness Agent` 应系统检查 `coverage`、`omissions`、`format` 和 `granularity`，再执行明确的 `next_actions`。
- `Harness Agent` 应保留原文供 `Reviewer/Human` 追溯；遇到冲突或无法完整结构化的内容时，`Harness Agent` 不应静默丢弃信息。

这些 records 的生成主体是 `AgentCore Memory System`。`Harness Agent` 提供 source session 行为轨迹，`Application/Orchestrator` 提供运行编排，`Reviewer/Human` 没有参与 record 生成。

实验一只证明托管 `EPISODIC` records 已经形成，还不能单独证明它们改善了新文档的抽取效果。

**过渡：** 实验二把这组 records 带到一份留出文档，通过 Retrieval 开关隔离其影响。

## Slide 9｜实验二：留出文档 Retrieval 开关对照

实验二的目标文档是一页电机图纸“2477080009简图-8.16”。`Application/Orchestrator` 为 Memory 组和 No Memory 组分别创建全新的 target session。

Memory 组的责任链是：

1. `Application/Orchestrator` 使用 `extractor_ep_review` 和 actor `ep-review-1789102186` 发起 target session。
2. `AgentCore Memory System` 在 Retrieval 阶段按 actor 检索实验一形成的 `EPISODIC` records。
3. `AgentCore Harness` 把 Retrieval 返回的方法性 records 注入目标 `Harness Agent` 的上下文。
4. 目标 `Harness Agent` 阅读目标文档和 Memory 上下文，执行抽取、内部自审并输出最终 JSON。

No Memory 组的责任链是：

1. `Application/Orchestrator` 使用 `extractor_ep_review_nomem` 发起另一条全新 target session。
2. `Application/Orchestrator` 禁用 Harness Memory 配置，因此 `AgentCore Memory System` 不执行目标端 Retrieval，`AgentCore Harness` 不注入历史 records。
3. 目标 `Harness Agent` 只依据目标文档和相同抽取指令完成抽取、内部自审并输出最终 JSON。

`Reviewer/Human` 仅在两组输出完成后进行人工核对，不参与实验一的 Memory 形成过程，也不向实验二的目标 `Harness Agent` 提供反馈。

**过渡：** 为了把目标输出差异归因于 Retrieval 和 Injection，下一页逐项说明控制变量。

## Slide 10｜控制变量：目标端只改变 Memory 开关

两组目标抽取都由 `Harness Agent` 执行。`Application/Orchestrator` 保持以下条件一致：

- 相同目标文档：一页电机图纸“2477080009简图-8.16”；
- 相同 invocation-level system prompt；
- 相同模型：`claude-sonnet-4-6`；
- 相同 `temperature=0`；
- 相同 `maxTokens=32768`；
- 两组均禁用 Skill 和 tools；
- 两组分别使用全新 target session；
- 两组 `Harness Agent` 均执行单次抽取，并在内部自审后输出最终 JSON。

唯一变量是托管 Memory 链路：

- Memory 组中，`AgentCore Memory System` 执行 `EPISODIC` Retrieval，`AgentCore Harness` 把返回 records 注入目标 `Harness Agent` 上下文。
- No Memory 组中，`Application/Orchestrator` 禁用 Memory；`AgentCore Memory System` 不执行目标端 Retrieval，`AgentCore Harness` 不注入历史 records。

`Application/Orchestrator` 负责记录两组最终输出及记录条数；`Reviewer/Human` 负责对照目标原文检查新增记录是否有依据。记录条数是行为观察，不是自动质量分数。

**过渡：** 在这些控制条件下，核心结果是目标 `Harness Agent` 是否开始系统覆盖两张 BOM。

## Slide 11｜重点结果：31 vs 11

这是整套实验最重要的结果。

首次运行中：

- Memory 组的目标 `Harness Agent` 输出 **31 条**记录。
- No Memory 组的目标 `Harness Agent` 输出 **11 条**记录。

这两个数字由 `Application/Orchestrator` 从两组最终 JSON 中统计。它们表示记录数量，不表示质量分数，因此不能表述为“质量提升三倍”。

真正关键的差异来自内容覆盖：

- Memory 组中，`AgentCore Memory System` 检索实验一形成的方法性 `EPISODIC` records，`AgentCore Harness` 把 records 注入目标 `Harness Agent` 上下文；目标 `Harness Agent` 随后系统展开了图纸中的两张 BOM。
- No Memory 组中，目标 `Harness Agent` 主要关注标题栏和技术要求，只零散抽取少量数量信息，没有同样系统地展开两张 BOM。

Memory 组新增的约 20 条记录主要包括机座、前端盖、转子、轴承、壳体组件、法兰盘组件和散热器组件等零部件与组件。

`Reviewer/Human` 对照目标图纸后认为，这些新增条目基本能够在两张 BOM 中找到原文依据，并非明显臆造。但 `Reviewer/Human` 仍需判断每个零部件是否属于最终业务边界，以及拆分粒度是否符合实际使用要求。

本页能够支持的准确结论是：在这份留出文档上，目标 `Harness Agent` 接收方法性 `EPISODIC` records 后，改变了对“什么值得结构化”的判断，输出从 11 条变为 31 条，新增内容主要来自两张 BOM。

**过渡：** 下一页把 Memory 的生成证据和目标端的行为证据连接起来，同时明确结论边界。

## Slide 12｜两项实验的统一证据链与结论边界

两项实验构成一条连续证据链：

1. `Application/Orchestrator` 在源任务中顺序调用 `Harness Agent`，形成“原文输入、结构化 Self-review、修订动作、最终 JSON”的完整 source session 轨迹。
2. `AgentCore Memory System` 使用内置 `EPISODIC` strategy，从 source session events 中生成 1 条 session-level episode 和 2 条 actor-level reflection records。
3. 在留出文档的 Memory 组中，`AgentCore Memory System` 按 actor 检索这些 records，`AgentCore Harness` 将 records 注入新的目标 `Harness Agent` session。
4. 在相同目标任务与运行配置下，Memory 组的目标 `Harness Agent` 输出 31 条，No Memory 组输出 11 条；新增内容主要来自两张 BOM。
5. `Reviewer/Human` 对照原文后确认新增条目基本有原文依据，但仍保留业务边界和拆分粒度的人工判断。

两项实验共同支持以下结论：

- 高质量 Memory 的前提是 `Harness Agent` 在 source session 中留下清晰、可执行、可追溯的 Review 与修订轨迹。
- `AgentCore Memory System` 的内置 `EPISODIC` strategy 能把该轨迹提炼为跨 session 可检索的方法性 records。
- `AgentCore Harness` 把 Retrieval records 注入目标 `Harness Agent` 后，Memory 上下文可以改变目标 `Harness Agent` 的覆盖重点。
- 本次证据来自单个 source document 和单个留出文档，能够证明行为差异，不能直接证明普遍的质量提升或跨领域泛化。
- `AgentCore Memory System` 不能替代 `Reviewer/Human` 定义任务边界，也不能用记录条数替代忠实性、完整性和粒度评审。

**过渡：** 最后一页把这条证据链收敛为可以复用的工程实践。

## Slide 13｜结构化数据抽取的 Memory 最佳实践

第一，`Application/Orchestrator` 应把 source task 设计为明确的两阶段调用，确保原文、结构化 `self_review`、`next_actions` 和最终 JSON 在同一 source session 中形成连续轨迹。

第二，`Harness Agent` 的 Self-review 必须同时依据当前原文和内部草稿。`Harness Agent` 应固定检查 `coverage`、`omissions`、`format` 和 `granularity`，再根据明确的 `next_actions` 修订最终 JSON。

第三，`AgentCore Memory System` 使用内置 `EPISODIC` strategy 时，团队应分别观察 Event Storage、Extraction、Consolidation、Reflection 和 Retrieval，并明确 raw event、session-level episode 与 actor-level reflection 的作用域。

第四，后续任务开始时，`AgentCore Memory System` 负责按 actor 执行 Retrieval；`AgentCore Harness` 负责把返回 records 注入新的目标 `Harness Agent` session；目标 `Harness Agent` 仍必须依据当前文档原文完成抽取，不能复制历史业务答案。

第五，`Application/Orchestrator` 应在对照实验中控制 actor、target session、prompt、模型参数、tools、Skill 和 Memory 开关，避免把编排差异误判为 Memory 效果。

第六，`Reviewer/Human` 应分别检查忠实性、完整性、粒度、过度抽取和业务边界，不能把 Memory 数量或输出记录数量直接当作质量分数。

最终 takeaway 是：

> `Harness Agent` 负责产生高质量 Review 与修订轨迹；`AgentCore Memory System` 负责使用 `EPISODIC` strategy 提炼并检索方法性 records；`AgentCore Harness` 负责把检索 records 注入新的 `Harness Agent` session；`Reviewer/Human` 负责判断这些方法是否真正改善业务结果。

**过渡（收束）：** 本次最重要的证据不是 Memory 中保存了多少文字，而是同一留出任务中，接收方法性 `EPISODIC` records 的目标 `Harness Agent` 系统覆盖了两张 BOM，并输出 31 条；未接收 Memory 的目标 `Harness Agent` 输出 11 条。
