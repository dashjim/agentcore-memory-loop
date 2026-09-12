# 《Agent 记忆最佳实践｜结构化数据抽取场景》Speaker Notes

> 对应当前 17 页 PPT。以下 Notes 使用统一角色词表：`Application/Orchestrator` 负责编排与实验控制；`Harness Agent` 负责抽取、自审和修订；应用侧 `Reflection LLM` 负责从已有输出归纳候选规则；应用侧 `Consolidation LLM` 负责合并 canonical rules；`AgentCore Memory System` 使用内置 `EPISODIC` strategy 执行 event storage、Extraction、Consolidation、Reflection 和 Retrieval；`Reviewer/Human` 负责质量判断与任务边界确认。

## Slide 1｜Agent 记忆最佳实践

今天讨论一个具体问题：在结构化数据抽取场景中，`Application/Orchestrator` 应如何组织抽取与学习回路，使 `Harness Agent` 能复用过去任务中形成的方法，并在下一份文档中抽得更完整。

这里的 Memory 不应只是保存历史业务答案。更有价值的做法是：`Harness Agent` 在源任务中形成可观察的 Review 轨迹，`AgentCore Memory System` 再使用内置 `EPISODIC` strategy 从 session events 中提炼 session-level episode 和 actor-level reflection。后续任务开始时，`AgentCore Memory System` 执行 Retrieval，Harness 集成层把返回的 records 放入新的 `Harness Agent` session 上下文。

本次汇报包含三项边界独立、前后递进的实验：

- 实验一由应用侧 `Reflection LLM` 和 `Consolidation LLM` 执行输出侧抽象自省；
- 实验二由 `Harness Agent` 产生结构化 Self-review 轨迹，再由 `AgentCore Memory System` 提炼 `EPISODIC` records；
- 实验三由 `Application/Orchestrator` 控制 Memory 开关，比较同一目标文档上的 `Harness Agent` 输出。

**过渡：** 在讨论 Memory 之前，先明确 `Harness Agent` 在结构化抽取中最容易失败的地方。

## Slide 2｜结构化抽取真正难在哪里

`Harness Agent` 使用的模型生成合法 JSON 并不困难，真正困难的是完整性。

工业文档的信息可能分散在正文、技术要求、BOM 表格、附注、图纸说明和 OCR 结果中。`Harness Agent` 往往优先识别明显的参数和数值，却可能把整张 BOM、某个章节或图片区域当成背景材料。

因此，`Harness Agent` 输出的 JSON 即使格式完全正确，也可能只覆盖技术要求，没有覆盖表格中的零部件和组件。

这里需要区分两个责任：

- `Harness Agent` 负责在给定任务定义下识别、审查并结构化原文信息；
- `Reviewer/Human` 负责判断哪些内容属于业务目标，以及某段原文应该合并还是拆分。

核心挑战不是“`Harness Agent` 能不能输出 JSON”，而是“`Harness Agent` 如何发现自己漏了什么，`Application/Orchestrator` 又如何把这种发现变成后续任务可复用的学习信号”。

**过渡：** 这决定了抽取回路中每个组件应该承担什么责任。

## Slide 3｜Memory 应该在抽取回路中做什么

这一页的五个步骤应按以下端到端责任链理解：

1. **当前文档与抽取草稿：** `Application/Orchestrator` 把当前文档、抽取指令和运行配置提交给 `Harness Agent`；`Harness Agent` 阅读原文并形成内部抽取草稿。
2. **Review：** `Harness Agent` 对照原文检查草稿的覆盖、遗漏、格式、粒度和冲突，并形成结构化 `self_review` 与可执行的 `next_actions`。
3. **可复用经验：** `Harness Agent` 根据 `next_actions` 修订并输出最终 JSON；同时，`AgentCore Memory System` 的 event storage 保存该 actor/session 中的原文输入、Review artifact、修订动作和最终输出等 events。
4. **Memory：** 源 session 结束后，`AgentCore Memory System` 使用内置 `EPISODIC` strategy 异步执行 Extraction、Consolidation 和 Reflection，分别形成 session-level episode 与 actor-level reflection records。
5. **下一份文档：** `Application/Orchestrator` 使用同一 actor 创建新的 session 并提交下一份文档；`AgentCore Memory System` 执行 Retrieval，Harness 集成层把检索到的方法性 records 放入目标 `Harness Agent` 的上下文；`Harness Agent` 再根据新文档原文完成抽取、自审和最终输出。

最后，`Reviewer/Human` 对目标输出进行忠实性、完整性、粒度和业务边界评判。`Reviewer/Human` 的判断不能由记录条数替代。

因此，`AgentCore Memory System` 保存和检索的重点应是“容易漏什么、应该检查什么、下一次应该执行什么动作”等方法性经验，而不是上一份文档的业务答案。

**过渡：** 为了验证这条责任链，我们把探索拆成三项主体、输入和产物都不同的实验。

## Slide 4｜三个实验，回答三个不同问题

三项实验的端到端流程如下。

**实验一：输出侧抽象自省。**

1. `Application/Orchestrator` 调用 `Harness Agent` 执行一轮文档抽取；
2. `Application/Orchestrator` 只把该轮已有抽取输出交给应用侧 `Reflection LLM`，不提供原文；
3. 应用侧 `Reflection LLM` 从已有输出中归纳候选规则；
4. `Application/Orchestrator` 把旧规则和新候选规则交给应用侧 `Consolidation LLM`；
5. 应用侧 `Consolidation LLM` 合并、去重并输出 canonical rules；
6. `Application/Orchestrator` 把 canonical rules 作为下一轮抽取的附加指导，再次调用 `Harness Agent`。

实验一形成的是应用侧自定义规则记忆，不是 `AgentCore Memory System` 内置 `EPISODIC` records。

**实验二：源任务产生托管 EPISODIC Memory。**

1. `Application/Orchestrator` 把 13 页液氮罐文档提交给 `Harness Agent`；
2. `Harness Agent` 在同一 source session 中先输出结构化 `self_review`，再根据 `next_actions` 修订并输出最终 JSON；
3. `AgentCore Memory System` 的 event storage 保存该 source session 的 events；
4. `AgentCore Memory System` 使用内置 `EPISODIC` strategy 执行 Extraction、Consolidation 和 Reflection，生成 1 条 session-level episode 和 2 条 actor-level reflections。

**实验三：留出文档 Memory 开关对照。**

1. `Application/Orchestrator` 为 Memory 组和 No Memory 组分别创建全新 target session，并保持目标文档、prompt、模型参数及工具配置一致；
2. Memory 组中，`AgentCore Memory System` 执行 Retrieval，Harness 集成层把检索 records 放入目标 `Harness Agent` 上下文；
3. No Memory 组中，`Application/Orchestrator` 禁用 Harness Memory 配置，因此 `Harness Agent` 不接收任何历史 records；
4. 两组 `Harness Agent` 分别完成抽取、自审和最终 JSON 输出；
5. `Reviewer/Human` 对两组结果进行原文核对和业务边界判断。

三项实验依次回答：应用侧抽象规则能学到什么、托管 Memory 如何形成、托管 Memory 是否改变新任务中的抽取行为。

**过渡：** 先进入实验一，明确“只看输出的抽象自省”究竟由谁执行。

## Slide 5｜实验一：抽象自省，只看输出能学到什么

本页所说的“抽象自省”不是 `Harness Agent` 在同一次抽取中对照原文做 Self-review，也不是 `AgentCore Memory System` 的 Reflection 阶段。

实验一中的主体分工是：

- `Harness Agent` 只负责先完成文档抽取并输出结构化结果；
- `Application/Orchestrator` 只收集 `Harness Agent` 已经输出的结果；
- 应用侧 `Reflection LLM` 只阅读这些已有输出，并生成候选抽取规则；
- 应用侧 `Consolidation LLM` 把候选规则与已有规则合并为 canonical rules；
- `Application/Orchestrator` 保存 canonical rules，并在下一轮调用中把这些规则提供给 `Harness Agent`。

应用侧 `Reflection LLM` 看不到原文，因此它也看不到 `Harness Agent` 完全遗漏的章节、表格或图片区域。本实验测试的是“输出侧规则归纳能力”，而不是“原文覆盖检查能力”。

**实验边界：** 第 5 至第 8 页只讨论应用侧自定义 Reflection/Consolidation 回路；这一回路没有使用 `AgentCore Memory System` 内置 `EPISODIC` strategy。

**过渡：** 下一页展示的两个 Prompt，分别属于应用侧 `Reflection LLM` 和应用侧 `Consolidation LLM`。

## Slide 6｜实验一：应用侧 Reflection 与 Consolidation Prompt

左侧 Reflection Prompt 的执行主体是应用侧 `Reflection LLM`。

`Application/Orchestrator` 把某一轮 `Harness Agent` 的抽取输出作为 Reflection Prompt 的输入。应用侧 `Reflection LLM` 根据“每条必须可操作、只讲规则、不讲具体数值、不超过十条”等要求，生成本轮候选规则。

右侧 Consolidation Prompt 的执行主体是另一次应用侧 `Consolidation LLM` 调用。

`Application/Orchestrator` 把已有 canonical rules 和本轮候选规则一起提交给应用侧 `Consolidation LLM`。应用侧 `Consolidation LLM` 负责合并同义项、删除重复项，并把最终规则集控制在十五条以内。`Application/Orchestrator` 再保存新的 canonical rules，并将其提供给下一轮 `Harness Agent` 抽取。

这个应用侧闭环每轮都能形成新的规则，但它有一个结构性限制：应用侧 `Reflection LLM` 只能观察 `Harness Agent` 已经输出的内容。如果 `Harness Agent` 完全漏掉一张 BOM，该 BOM 不会进入 Reflection Prompt，应用侧 `Reflection LLM` 就没有事实依据发现这块遗漏。

这里的 Reflection 和 Consolidation 都是应用侧 LLM 调用，不是 `AgentCore Memory System` 内置 `EPISODIC` strategy 中的 Reflection 或 Consolidation 阶段。

**过渡：** 接下来检查应用侧 `Consolidation LLM` 最终保留了什么，以及这些规则实际改变了什么。

## Slide 7｜实验一：应用侧 Consolidation LLM 形成的 15 条 Canonical Rules

四轮运行后，应用侧 `Consolidation LLM` 最终输出了 15 条 canonical rules；`Application/Orchestrator` 把这 15 条规则作为自定义规则记忆维护，并提供给后续 `Harness Agent` 调用。

这 15 条规则主要覆盖以下方法：

1. `Harness Agent` 应先识别指标所属主体；
2. `Harness Agent` 应区分整体性能与部件性能；
3. `Harness Agent` 应把运输、交付和包装要求独立记录；
4. `Harness Agent` 应把子系统、附件和独立部件分别记录；
5. `Harness Agent` 遇到多部件语句时应按部件拆分；
6. `Harness Agent` 遇到复合指标时应按指标拆分；
7. `Harness Agent` 应规范化指标名称；
8. `Harness Agent` 应按接口对象记录接管和连接要求；
9. `Harness Agent` 应分别记录阀门、仪表和附件清单对象；
10. `Harness Agent` 应区分不同部位和层次的材料要求；
11. `Harness Agent` 应完整保留无损检测方法、比例、级别和标准；
12. `Harness Agent` 应区分制造工艺、结构要求和性能指标；
13. `Harness Agent` 应忠实保留上下限、范围及比较符号；
14. `Harness Agent` 不应因缺少数值而忽略功能性和描述性要求；
15. `Harness Agent` 应保留对应原文，支持 `Reviewer/Human` 追溯。

这些规则并非没有价值。限值符号保留、描述性要求保留和原文追溯都是合理的质量要求。

但多条规则持续要求 `Harness Agent` “分别成条”或“独立拆分”。`Application/Orchestrator` 记录到四轮输出条数从 90、93、95 增加到 102；最终 102 条只对应约 53 个唯一原文片段，平均每段原文被拆成 1.92 条。

因此，`Reviewer/Human` 不能把 `90→102` 直接解释为覆盖提升。现有数据更支持“应用侧规则让 `Harness Agent` 的拆分粒度变细”。

**过渡：** 实验一的局限，需要通过“源覆盖问题”和“任务边界问题”来解释。

## Slide 8｜实验一结论：输出侧反思无法发现整块遗漏

实验一暴露了两类不同错误。

**第一类是源覆盖问题。** 原文中明确存在信息，但 `Harness Agent` 没有输出，例如整张 BOM、某个章节或某类附注被完全遗漏。要发现这类问题，执行 Review 的主体必须同时看到原文和内部草稿。应用侧 `Reflection LLM` 在实验一中只看已有输出，因此无法稳定发现完全未进入输出的区域。

**第二类是任务边界问题。** 例如某类内容是否属于目标、某段原文应该合并还是拆分、BOM 零部件是否都应进入正式结果。这类判断需要任务规范，最终应由 `Reviewer/Human` 或明确的业务 rubric 给出事实信号。

实验一能够支持的结论是：

- 应用侧 `Reflection LLM` 可以从已有输出中归纳格式、命名、追溯和局部拆分规则；
- 应用侧 `Consolidation LLM` 可以把候选规则压缩成稳定的 canonical rules；
- 但当应用侧 `Reflection LLM` 看不到原文时，这套回路无法稳定发现整块遗漏；
- `Application/Orchestrator` 观察到的规则数或记录数增长，不能替代 `Reviewer/Human` 对原文覆盖的检查。

因此，正确结论不是“Reflection 没用”，而是“输出侧 Reflection 的事实输入不足以解决源覆盖问题”。

**过渡：** 实验二改变 Review 的输入条件：由 `Harness Agent` 同时查看原文和内部草稿，并留下可被 `AgentCore Memory System` 提炼的完整轨迹。

## Slide 9｜实验二：Harness Agent 产生可提炼的源任务轨迹

实验二不再使用实验一的输出侧抽象自省回路。

实验二的端到端流程是：

1. `Application/Orchestrator` 选择 13 页液氮罐技术要求作为 source document，并为 actor `ep-review-1789102186` 创建 source session；
2. `Application/Orchestrator` 在第一阶段调用 `Harness Agent`，要求 `Harness Agent` 阅读原文、形成内部草稿，并只输出结构化 `self_review`；
3. `Application/Orchestrator` 在第二阶段把原文和 `self_review.next_actions` 继续提供给同一 source session 中的 `Harness Agent`；
4. `Harness Agent` 根据 `next_actions` 修订内部草稿并输出最终 JSON；
5. `AgentCore Memory System` 的 event storage 保存 source session 中的输入、`self_review`、修订请求和最终输出等 events；
6. source session 形成完整轨迹后，`AgentCore Memory System` 使用内置 `EPISODIC` strategy 异步执行 Extraction、Consolidation 和 Reflection。

`Harness Agent` 负责业务抽取、自审和修订；`Application/Orchestrator` 负责两阶段调用顺序、输出约束和 session 控制；`AgentCore Memory System` 不替 `Harness Agent` 抽取业务字段，也不替 `Reviewer/Human` 判断业务边界。

**实验边界：** 第 9 至第 12 页只讨论 source session 如何形成托管 `EPISODIC` records；目标文档的效果验证从第 13 页开始。

**过渡：** 下一页聚焦两阶段流程中 `Application/Orchestrator` 与 `Harness Agent` 各自执行的动作。

## Slide 10｜Harness Agent：两阶段结构化 Self-review

第一阶段由 `Application/Orchestrator` 发起，由 `Harness Agent` 执行。

`Application/Orchestrator` 向 `Harness Agent` 提供源文档和第一阶段指令。`Harness Agent` 在内部形成抽取草稿，但不把草稿作为最终答案返回；`Harness Agent` 对照原文检查 `coverage`、`omissions`、`format` 和 `granularity`，并输出结构化 `self_review` 与 `next_actions`。

第二阶段仍由 `Application/Orchestrator` 发起，并由同一 source session 中的 `Harness Agent` 执行。

`Application/Orchestrator` 把原文、结构化 `self_review` 和第二阶段输出约束提交给 `Harness Agent`。`Harness Agent` 逐项落实 `next_actions`，修订内部草稿，并输出最终五字段 JSON。

这套设计不要求 `Harness Agent` 暴露完整思维过程；它要求 `Harness Agent` 留下一个可观察、可执行的 Review artifact。`Application/Orchestrator` 负责保证两个阶段的顺序和输入连续性。

在两个阶段运行期间，`AgentCore Memory System` 的 event storage 保存 session events；`AgentCore Memory System` 此时不负责业务抽取，也不负责生成 `self_review`。托管 Extraction、Consolidation 和 Reflection 在完整轨迹形成后异步执行。

**过渡：** source session 结束后，处理主体从 `Harness Agent` 切换为 `AgentCore Memory System`。

## Slide 11｜AgentCore Memory System：内置 EPISODIC 提炼轨迹

这一页的执行主体是 `AgentCore Memory System`，策略类型是内置 `EPISODIC` strategy。

处理过程包含四个明确阶段：

1. **Event storage：** `AgentCore Memory System` 按 actor 和 session 保存 `Application/Orchestrator` 与 `Harness Agent` 交互形成的 raw events，包括源文档输入、结构化 `self_review`、修订动作和最终 JSON。
2. **Extraction：** `AgentCore Memory System` 从 source session events 中识别值得保留的任务过程、Review 发现、修订动作和结果。
3. **Consolidation：** `AgentCore Memory System` 把当前 source session 的关键信息整理为 session-level episode，作用域为当前 actor/session，namespace 为 `/episodes/{actorId}/{sessionId}`。
4. **Reflection：** `AgentCore Memory System` 从 episode 中抽象跨 session 可复用的方法，形成 actor-level reflection records，作用域为当前 actor，namespace 为 `/episodes/{actorId}`。

这里的 Consolidation 和 Reflection 都属于 `AgentCore Memory System` 的托管 `EPISODIC` 处理，不是实验一中的应用侧 `Consolidation LLM` 与应用侧 `Reflection LLM`。

`EPISODIC` 处理是异步的，短 session 不保证一定生成 records。本次 13 页源任务留下了原文、Review、修订和结果之间的完整轨迹，因此 `AgentCore Memory System` 最终形成了可检索记录。

**过渡：** 下一页展示 `AgentCore Memory System` 实际形成的 record 数量、类型和作用域。

## Slide 12｜AgentCore Memory System 实际生成的 Records

`AgentCore Memory System` 使用内置 `EPISODIC` strategy，最终从 source session 中生成了：

- 1 条 session-level episode，作用域是 actor `ep-review-1789102186` 的当前 source session；
- 2 条 actor-level reflections，作用域是 actor `ep-review-1789102186`，可供该 actor 的后续新 session 检索。

session-level episode 由 `AgentCore Memory System` 的 Consolidation 阶段形成，主要总结本次任务发生了什么：`Harness Agent` 使用两阶段流程，先输出结构化 `self_review`，再执行修订；`Harness Agent` 面对 OCR 错误、章节跳号、重复表格和图片限制时，应显式处理并保留可追溯信息。

两条 actor-level reflections 由 `AgentCore Memory System` 的 Reflection 阶段形成，主要抽象未来可复用的方法：

- `Harness Agent` 应系统检查 `coverage`、`omissions`、`format` 和 `granularity`，再执行明确的 `next_actions`；
- `Harness Agent` 应保留原文用于 `Reviewer/Human` 追溯；遇到冲突或无法完整结构化的内容时，`Harness Agent` 不应静默丢弃信息。

这些 records 的生成主体是 `AgentCore Memory System`。`Harness Agent` 提供的是 source session 行为轨迹，`Application/Orchestrator` 提供的是运行编排，`Reviewer/Human` 没有参与 record 撰写。

实验二到此只证明托管 records 已形成，还没有证明这些 records 能提高新文档的抽取质量。

**过渡：** 实验三把这组 records 带到一份留出文档，并通过 Memory 开关隔离其影响。

## Slide 13｜实验三：留出文档 Memory 开关对照

实验三由 `Application/Orchestrator` 负责分组、配置和运行控制。

源任务仍是实验二中的 13 页液氮罐技术要求；目标任务换成一页电机图纸“2477080009简图-8.16”。`Application/Orchestrator` 为 Memory 组和 No Memory 组分别创建全新的 target session。

Memory 组的责任链是：

1. `Application/Orchestrator` 使用 `extractor_ep_review` 和 source actor `ep-review-1789102186` 发起 target session；
2. `AgentCore Memory System` 在 Retrieval 阶段按 actor 检索实验二形成的 `EPISODIC` records；
3. Harness 集成层把 Retrieval 返回的方法性 records 放入目标 `Harness Agent` 的上下文；
4. 目标 `Harness Agent` 阅读目标文档和注入的 Memory 上下文，执行抽取、内部自审并输出最终 JSON。

No Memory 组的责任链是：

1. `Application/Orchestrator` 使用 `extractor_ep_review_nomem` 发起另一条全新 target session；
2. `Application/Orchestrator` 禁用 Harness Memory 配置，因此 `AgentCore Memory System` 不参与 Retrieval，目标 `Harness Agent` 不接收历史 records；
3. 目标 `Harness Agent` 只依据目标文档和相同抽取指令完成抽取、内部自审并输出最终 JSON。

`Reviewer/Human` 在两组输出完成后进行人工对比。本实验不让 `Reviewer/Human` 的评分参与前面的 Memory 形成过程。

**过渡：** 为了把差异归因于 Memory 上下文，下一页逐项说明 `Application/Orchestrator` 锁定了哪些控制变量。

## Slide 14｜Harness Agent 留出实验：目标端只改变 Memory 开关

两组目标抽取都由 `Harness Agent` 执行；`Application/Orchestrator` 保持以下条件一致：

- `Application/Orchestrator` 向两组提供相同的一页电机图纸；
- `Application/Orchestrator` 向两组提供相同的 invocation-level system prompt；
- `Application/Orchestrator` 为两组配置相同模型 `claude-sonnet-4-6`；
- `Application/Orchestrator` 为两组配置相同的 `temperature=0`；
- `Application/Orchestrator` 为两组配置相同的 `maxTokens=32768`；
- `Application/Orchestrator` 为两组禁用 Skill 和 tools；
- `Application/Orchestrator` 为两组分别创建全新 target session；
- 两组 `Harness Agent` 都执行单次抽取，并在内部自审后输出最终 JSON。

唯一变量是托管 Memory 链路：

- Memory 组中，`AgentCore Memory System` 执行 `EPISODIC` Retrieval，Harness 集成层把返回 records 放入 `Harness Agent` 上下文；
- No Memory 组中，`Application/Orchestrator` 禁用 Memory，因此 `AgentCore Memory System` 不执行目标端 Retrieval，`Harness Agent` 不接收历史 records。

`Application/Orchestrator` 记录两组最终输出；`Reviewer/Human` 再对照目标原文检查新增记录是否有依据。记录条数本身不是自动质量评分。

**过渡：** 在这组控制条件下，最重要的观察是 `Harness Agent` 是否开始系统覆盖两张 BOM。

## Slide 15｜重点结果：Harness Agent 输出 31 vs 11

这是全套实验最重要的一页。

首次运行中：

- Memory 组的目标 `Harness Agent` 输出 31 条记录；
- No Memory 组的目标 `Harness Agent` 输出 11 条记录。

这两个数字由 `Application/Orchestrator` 从两组最终 JSON 中统计。它们表示记录数量，不表示质量分数，因此不能表述为“质量提升三倍”。

真正关键的差异来自内容覆盖：

- Memory 组中，`AgentCore Memory System` 先执行 Retrieval，Harness 集成层把方法性 `EPISODIC` records 放入目标 `Harness Agent` 上下文；目标 `Harness Agent` 随后系统展开了图纸中的两张 BOM；
- No Memory 组中，目标 `Harness Agent` 主要关注标题栏和技术要求，只零散抽取少量数量信息，没有同样系统地展开两张 BOM。

Memory 组新增的约 20 条记录主要包括机座、前端盖、转子、轴承、壳体组件、法兰盘组件和散热器组件等零部件与组件。

`Reviewer/Human` 对照目标图纸后认为，这些新增条目基本能够在两张 BOM 中找到原文依据，并非明显臆造。但 `Reviewer/Human` 仍需判断每个零部件是否属于最终业务边界，以及拆分粒度是否符合实际使用要求。

因此，本页能够支持的准确结论是：

> 在这份留出文档上，`AgentCore Memory System` 检索方法性 `EPISODIC` records，并由 Harness 集成层将其提供给目标 `Harness Agent` 后，目标 `Harness Agent` 改变了对“什么值得结构化”的判断，输出从 11 条变为 31 条，新增内容主要来自两张 BOM。

**过渡：** 最后一部分把三项实验的主体、证据和结论边界合并起来。

## Slide 16｜三个实验合起来，结论才完整

**实验一的主体与结论：**

`Harness Agent` 先输出抽取结果；应用侧 `Reflection LLM` 只阅读已有输出并归纳候选规则；应用侧 `Consolidation LLM` 合并 canonical rules；`Application/Orchestrator` 把规则提供给下一轮 `Harness Agent`。这套回路学到了格式、规范化和拆分方法，但因为应用侧 `Reflection LLM` 看不到原文，所以无法稳定发现整块遗漏，`90→102` 也主要体现拆分变细。

**实验二的主体与结论：**

`Application/Orchestrator` 组织两阶段调用；`Harness Agent` 同时查看原文和内部草稿，输出结构化 `self_review`，再根据 `next_actions` 修订；`AgentCore Memory System` 保存 source session events，并使用内置 `EPISODIC` strategy 执行 Extraction、Consolidation 和 Reflection。这条源任务轨迹最终形成 1 条 session-level episode 和 2 条 actor-level reflections。

**实验三的主体与结论：**

`Application/Orchestrator` 控制目标端变量；`AgentCore Memory System` 只在 Memory 组执行 Retrieval；Harness 集成层只在 Memory 组把 records 放入目标 `Harness Agent` 上下文；两组 `Harness Agent` 分别输出最终 JSON。结果是 31 条对 11 条，新增内容主要来自两张 BOM；`Reviewer/Human` 核对后认为新增内容基本有原文依据。

三项实验共同支持的结论是：

- `Harness Agent` 的源覆盖能力取决于 Review 是否能同时看到原文和内部草稿；
- `AgentCore Memory System` 的价值取决于 source session 是否包含足够清晰的 Review 与修订轨迹；
- `AgentCore Memory System` 的 `EPISODIC` records 可以跨 session 复用方法，但不能替 `Reviewer/Human` 定义任务边界；
- 在本次单个留出文档实验中，Memory 上下文改变了目标 `Harness Agent` 的覆盖重点，但仍需要更多文档与人工评审验证泛化性。

**过渡：** 最后一页把这些角色分工收敛成可执行的工程实践。

## Slide 17｜结构化数据抽取的 Memory 最佳实践

第一，`Application/Orchestrator` 应把源任务 Review 设计成明确的两阶段调用，并保证原文、结构化 `self_review` 和 `next_actions` 在同一 source session 中形成连续轨迹。

第二，`Harness Agent` 的 Review 必须同时查看原文和内部草稿；`Harness Agent` 应固定检查 `coverage`、`omissions`、`format` 和 `granularity`，再根据明确的 `next_actions` 修订最终 JSON。

第三，应用侧 `Reflection LLM` 与应用侧 `Consolidation LLM` 适合维护自定义规则，但团队必须明确：这两种应用侧调用不是 `AgentCore Memory System` 内置 `EPISODIC` strategy 的 Reflection 与 Consolidation。

第四，`AgentCore Memory System` 使用内置 `EPISODIC` strategy 时，团队应分别观察 event storage、Extraction、Consolidation、Reflection 和 Retrieval，并明确 session-level episode 与 actor-level reflection 的作用域。

第五，后续任务开始时，`AgentCore Memory System` 负责按 actor 执行 Retrieval；Harness 集成层负责把返回 records 放入新的 `Harness Agent` session 上下文；新的 `Harness Agent` 仍应依据当前文档原文完成抽取，不能复制历史业务答案。

第六，`Application/Orchestrator` 应在对照实验中分别控制 source actor、target session、prompt、模型参数、tools、Skill 和 Memory 开关，避免把编排差异误判为 Memory 效果。

第七，`Reviewer/Human` 应分别检查忠实性、完整性、粒度、过度抽取和业务边界，不能把规则数量或输出记录数量直接当作质量分数。

最终 takeaway 是：

> `Harness Agent` 负责产生高质量 Review 轨迹，`AgentCore Memory System` 负责把轨迹提炼并跨 session 检索，Harness 集成层负责把检索 records 提供给新的 `Harness Agent`，`Reviewer/Human` 负责判断这些方法是否真正改善了业务结果。

**过渡（收束）：** 本次最有价值的证据不是“Memory 里多了几条记录”，而是同一目标任务中，接收方法性 `EPISODIC` records 的 `Harness Agent` 系统覆盖了两张 BOM，并输出 31 条；未接收 Memory 的 `Harness Agent` 输出 11 条。
