# 《Agent 记忆最佳实践｜结构化数据抽取场景》Speaker Notes

> 对应 17 页新版结构。每个章节对应一页幻灯片，可直接复制到 PowerPoint Notes。

## Slide 1｜Agent 记忆最佳实践

今天讨论一个具体问题：在结构化数据抽取场景中，怎样让 Harness Agent 从过去任务中学习，并在下一份文档中抽得更完整。

这里的 Memory 不应只是保存历史答案。更有价值的是保存 Review 发现的遗漏模式、检查方法和可复用抽取策略，再由 AgentCore Memory System 在后续任务中检索并注入给 Harness Agent。

接下来通过三项相互独立、前后递进的实验，说明什么样的学习信号能形成有用 Memory，以及 Memory 最终如何改变留出文档的抽取行为。

**过渡：** 先看结构化抽取真正困难的部分。

## Slide 2｜挑战：合法 JSON 不等于完整抽取

当前模型生成合法 JSON 并不困难，真正困难的是完整性。

工业文档的信息可能分散在正文、技术要求、BOM 表格、附注、图纸说明和 OCR 结果中。Harness Agent 往往优先关注明显的参数和数值，却可能把整张 BOM 或整个章节当成背景材料。

因此，结果即使格式完全正确，也可能只覆盖技术要求，没有覆盖表格中的零部件和组件。

核心挑战不是“Harness Agent 能不能输出 JSON”，而是“Harness Agent 如何发现自己漏了什么，并把这种发现带到下一次任务中”。

**过渡：** 这决定了 Memory 在抽取回路中应该承担什么角色。

## Slide 3｜Memory 的角色：保存方法，而不是历史答案

Harness Agent 先执行抽取和 Review；AgentCore Memory System 再保存 session events，并根据配置的策略提炼可复用记录。

在后续任务开始前，AgentCore Memory System 检索相关记录，Harness 将这些记录作为上下文注入新的 Harness Agent session。

有价值的 Memory 应描述方法，例如：

- Harness Agent 应检查哪些文档区域；
- Harness Agent 应如何处理遗漏、冲突和重复；
- Harness Agent 输出前应执行哪些明确动作；
- Harness Agent 应如何选择抽取粒度。

Memory 不应直接复制上一份文档的业务答案，因为历史答案既占上下文，也可能误导新任务。

**过渡：** 为了判断哪种方法有效，我们把探索拆成三项边界清晰的实验。

## Slide 4｜三项实验地图

三项实验回答三个不同问题。

实验一研究“只看输出能学到什么”。应用侧把 Harness Agent 的已有输出交给反思模型，再通过自定义 consolidation 维护 canonical memory，观察规则和抽取结果如何变化。

实验二研究“怎样产生可被托管 Memory 提炼的轨迹”。Harness Agent 同时查看原文和内部草稿，执行两阶段结构化 Self-review；AgentCore Memory System 使用内置 `EPISODIC` strategy 提炼完整 session。

实验三研究“已有 Memory 是否改变下一份文档的抽取”。Harness Agent 在留出文档上执行 Memory 开关对照；AgentCore Memory System 只在 Memory 组检索并注入 records。

三项实验依次对应：抽象规则学习、源任务 Memory 生成、目标任务效果验证。

**过渡：** 先进入实验一，只允许反思模型看到已经抽出的输出。

## Slide 5｜实验一：只看输出的抽象自省

这是第一项独立实验的章节页。

实验一的输入边界是：反思模型只能看到 Harness Agent 已经抽出的结果，看不到原文，也看不到被完全遗漏的章节或表格。

应用侧负责调用反思模型生成规则，再调用 consolidation prompt 合并、去重并维护 canonical memory。这里形成的是自定义规则记忆，不是 AgentCore Memory System 内置 `EPISODIC` strategy 生成的 episode 或 reflection。

本实验的目标是判断：仅依赖输出侧自省，规则是否会逐轮收敛，以及抽取数量增加究竟代表覆盖提升还是拆分变细。

**前后边界：** 前四页是问题定义和实验地图；从本页到第 8 页只讨论实验一。第 9 页开始切换到新的源任务流程，不沿用实验一的输入条件。

**过渡：** 下一页先展示实验一真实使用的 reflection 与 consolidation prompt。

## Slide 6｜真实 Reflection 与 Consolidation Prompt

第一步，应用侧把某轮 Harness Agent 输出交给反思模型。Reflection prompt 要求模型总结不超过十条、可用于未来任务的规则。

第二步，应用侧把已有规则和新规则一起交给 consolidation 模型。Consolidation prompt 负责合并同义项、删除重复项，并把规则集控制在十五条以内。

这个流程每轮都能产生新的规则，而且规则会持续合并，因此形式上像一个自进化闭环。

但反思模型的观察范围只包含“已经抽出来的内容”。如果 Harness Agent 完全漏掉了一张 BOM，这张表不会出现在输出里，反思模型也无法从缺失信息中推导出遗漏。

**过渡：** 因此要同时看规则内容、抽取条数和原文覆盖，而不能只看 Memory 数量。

## Slide 7｜15 条 Canonical Memory 与 90→102 观察

四轮 consolidation 最终形成了完整的 15 条 canonical memory：

1. 先识别指标所属主体，避免把部件指标错误归到整机；
2. 整体性能指标与部件性能指标分别记录；
3. 运输、交付和包装要求独立成条；
4. 子系统、附件和独立部件的要求分别记录；
5. 同一句涉及多个部件时，按部件拆分记录；
6. 同一句包含多个指标时，按指标拆分记录；
7. 指标名称应规范化，避免把完整句子直接作为名称；
8. 接管、接口和连接要求按接口对象分别记录；
9. 阀门、仪表和附件清单中的对象分别记录；
10. 不同部位、不同层次的材料要求分别记录；
11. 无损检测方法、比例、级别和标准应完整保留；
12. 制造工艺和结构要求应与性能指标区分；
13. 上下限、范围及大于小于符号必须忠实保留；
14. 功能性和描述性要求不能因为缺少数值而忽略；
15. 每条结果保留对应原文，支持追溯和复核。

这些规则并非都没有价值。限值符号保留、描述性要求保留和原文追溯都是合理的质量要求。

但规则集中有多条持续强调“分别成条”和“独立拆分”。四轮抽取条数从 90、93、95 增加到 102，最终 102 条只来自约 53 个唯一原文片段，平均每段原文被拆成 1.92 条。

因此，`90→102` 主要反映拆分粒度变细，不能直接证明覆盖了更多文档区域。

**过渡：** 实验一的结果需要用两类错误来解释。

## Slide 8｜实验一结论：抽取错误有两类

第一类是源覆盖问题：信息明确存在于原文，但 Harness Agent 没有输出，例如漏掉 BOM、漏掉章节、重复记录或字段为空。

第二类是任务边界问题：Harness Agent 不知道某类内容是否属于目标，或者不知道一段原文应该拆成几条。这需要任务规范、Reviewer 或人工反馈。

实验一说明，只看输出的抽象自省可以改善格式、规范化和局部拆分规则，但无法稳定发现完全未进入输出的区域。规则增加和条数增加也可能只是过度拆分。

因此，正确结论不是“Self-reflection 没用”，而是“只看输出时，反思模型获得的学习信号不足”。

**过渡：** 实验二改变输入条件，让 Harness Agent 的 Review 同时看到原文和内部草稿。

## Slide 9｜实验二：Harness Agent 产生可提炼轨迹

这是第二项独立实验的章节页。

实验二不再沿用实验一“只看输出”的抽象自省。Harness Agent 在同一个源任务 session 中读取 13 页液氮罐技术要求，先形成内部草稿，再输出结构化 self_review，最后根据 `next_actions` 修订并输出最终 JSON。

Harness Agent 负责抽取、自审和修订；AgentCore Memory System 负责保存 session events，并使用内置 `EPISODIC` strategy 异步执行 Extraction、Consolidation 和 Reflection。

本实验的目标不是直接比较最终条数，而是构造一条包含“原文、Review、修订结果”的高质量轨迹，观察托管 Memory 能否从中提炼出 episode 和 actor-level reflections。

**前后边界：** 第 5 至第 8 页的实验一到此结束；第 9 至第 12 页只讨论源任务如何产生托管 Memory。第 13 页才开始在另一份留出文档上验证效果。

**过渡：** 下一页先看 Harness Agent 如何执行两阶段 Self-review。

## Slide 10｜Harness Agent：两阶段结构化 Self-review

阶段一的执行主体是 Harness Agent。

Harness Agent 在内部形成草稿，但不向用户输出草稿，只输出结构化 `self_review`。固定检查项包括 `coverage`、`omissions`、`format`、`granularity` 和 `next_actions`。

阶段二仍由同一个 Harness Agent 执行。Harness Agent 重新读取原文和 `self_review`，逐项落实 `next_actions`，再输出最终五字段 JSON。

这个设计不要求模型暴露完整思维过程。它要求 Harness Agent 产生一个可观察、可执行的 Review artifact，并在同一 session 中留下修订前后的因果轨迹。

应用或 Harness 负责两阶段调用顺序和输出约束；此时 AgentCore Memory System 尚不负责抽取业务数据，也不替 Harness Agent 做 Review。

**过渡：** 完整 session 结束后，AgentCore Memory System 才开始提炼这条轨迹。

## Slide 11｜AgentCore Memory System：内置 EPISODIC 提炼流程

这一页的执行主体是 AgentCore Memory System，策略类型是内置 `EPISODIC` strategy。

Harness Agent 已经在 session events 中留下原文、结构化 `self_review`、最终 JSON 和任务结束信号。AgentCore Memory System 随后异步执行三个处理阶段：

1. Episode Extraction：分析 session 中的行为、Review 与结果；
2. Consolidation：形成 session-level episode；
3. Reflection：从 episode 中抽象 actor-level 可复用策略。

Session-level episode 的作用域是当前 actor 和 session，namespace 为 `/episodes/{actorId}/{sessionId}`。

Actor-level reflection 的作用域是当前 actor，namespace 为 `/episodes/{actorId}`，用于后续 session 的跨任务召回。

EPISODIC 提炼是异步过程，短 session 不保证一定生成 Memory。本次 13 页源任务提供了足够完整的执行轨迹。

**过渡：** 下一页展示 AgentCore Memory System 实际生成的 records，而不是概念示例。

## Slide 12｜实际生成：1 条 Episode + 2 条 Actor Reflections

AgentCore Memory System 的内置 `EPISODIC` strategy 最终生成了 1 条 session-level episode 和 2 条 actor-level reflections。

Session-level episode 总结了本次任务发生了什么：Harness Agent 使用两阶段流程，先输出 `self_review`，再执行修订；面对 OCR 错误、章节跳号、重复表格和图片限制时，应显式处理并保留可追溯信息。

两条 actor-level reflections 把本次经验抽象成未来可复用的方法：

- Harness Agent 应先系统检查 `coverage`、`omissions`、`format` 和 `granularity`，再执行明确的 `next_actions`；
- Harness Agent 应保留原文用于追溯，遇到冲突或无法完整结构化的内容时，不应静默丢弃信息。

Episode 回答“这一次任务发生了什么”；actor reflection 回答“未来遇到类似任务时应该怎么做”。

这些 records 的生成主体是 AgentCore Memory System，不是 Harness Agent 手工写入，也不是应用侧沿用实验一的自定义 canonical rules。

**过渡：** 实验二到此只证明 Memory 已经形成；实验三才验证这些 records 是否会改变新文档的抽取。

## Slide 13｜实验三：留出文档 Memory 开关对照

这是第三项独立实验的章节页，也是效果验证实验。

源任务仍是实验二的 13 页液氮罐技术要求；目标任务换成一页电机图纸“2477080009简图-8.16”，并使用全新的 runtime session。

Harness Agent 在目标文档上执行抽取。Memory 组由 AgentCore Memory System 检索实验二形成的 `EPISODIC` records，并由 Harness 注入给 Harness Agent；No Memory 组完全禁用 Memory。

本实验不再生成或比较新的自省规则，问题只有一个：在其他条件相同的情况下，Memory 注入是否改变 Harness Agent 对目标文档的覆盖重点。

**前后边界：** 第 9 至第 12 页的实验二是 Memory 生成阶段；从本页到第 15 页是留出文档验证阶段。源任务的答案不会提供给目标任务，目标 Harness Agent 只接收托管 Memory 中的方法性 records。

**过渡：** 为了让结果可解释，下一页先锁定控制变量。

## Slide 14｜控制变量：目标端只改变 Memory 开关

两组目标抽取都由 Harness Agent 执行，并保持以下条件一致：

- 相同的一页电机图纸；
- 相同的 invocation-level system prompt；
- 相同模型 `claude-sonnet-4-6`；
- 相同 `temperature=0`；
- 相同 `maxTokens=32768`；
- 都禁用 Skill 和 tools；
- 都使用全新 session；
- 都执行单次抽取，并在内部自审后输出最终 JSON。

唯一变量是 AgentCore Memory System 是否参与 Retrieval 和 context injection。

Memory 组使用 `extractor_ep_review`，复用 source actor `ep-review-1789102186`。AgentCore Memory System 检索该 actor 的 `EPISODIC` records，Harness 将其注入目标 Harness Agent。

No Memory 组使用 `extractor_ep_review_nomem`，Harness 的 Memory 配置为 disabled。

**过渡：** 在这组严格对照下，最重要的结果不是格式差异，而是 Harness Agent 是否开始系统覆盖两张 BOM。

## Slide 15｜重点结果：31 vs 11，新增内容主要来自两张 BOM

这是全套实验最重要的一页。

首次运行中，Memory 组由 Harness Agent 输出 31 条记录；No Memory 组由 Harness Agent 输出 11 条记录。这里不能表述为“质量提升三倍”，因为条数不是质量分数。

真正值得关注的是新增内容的来源。Memory 组多出的约 20 条记录主要来自图纸中的两张 BOM，Harness Agent 系统展开了其中的零部件和组件，例如机座、前端盖、转子、轴承、壳体组件、法兰盘组件和散热器组件。

No Memory 组主要关注标题栏和技术要求，只零散抽取了少量数量信息，没有同样系统地展开两张 BOM。

人眼核对后，这些新增条目基本能够在原文表格中找到依据，并非明显臆造。但这仍然不代表每一条都符合最终业务边界，条目是否应纳入正式结果仍需 Reviewer 或人工评审。

因此，本页的准确结论是：

> AgentCore Memory System 注入方法性 EPISODIC records 后，Harness Agent 改变了对“什么值得结构化”的判断，并显著扩大了对两张 BOM 的覆盖。

**过渡：** 把三项实验放在一起，可以得到一个比“Memory 有效或无效”更具体的结论。

## Slide 16｜三项实验的统一结论

实验一说明：当反思模型只看 Harness Agent 输出时，自定义 canonical memory 会学到格式、规范化和拆分规则，但无法稳定发现完全遗漏的文档区域，条数增长也可能来自过度拆分。

实验二说明：当 Harness Agent 同时查看原文和内部草稿，并输出结构化 `self_review` 与可执行 `next_actions` 时，完整 session 能为 AgentCore Memory System 的内置 `EPISODIC` strategy 提供更有价值的提炼轨迹。

实验三说明：AgentCore Memory System 在目标任务中检索并注入这些方法性 records 后，Harness Agent 的关注点发生变化；在一页电机图纸上，输出从 11 条变为 31 条，新增内容主要来自两张 BOM，且人眼看基本有原文依据。

统一结论不是“有 Memory 就一定更好”，而是：

- Memory 的价值取决于上游 Review 是否获得了足够的事实信号；
- 源覆盖问题适合由原文驱动的结构化 Self-review 改善；
- AgentCore `EPISODIC` Memory 适合沉淀和跨 session 复用方法；
- 任务边界与最终质量判断仍需规范、Reviewer 或人工反馈。

**过渡：** 最后把这些发现收敛成可执行的工程实践。

## Slide 17｜结构化数据抽取的 Memory 最佳实践

第一，Harness Agent 的 Review 必须同时查看原文和内部草稿，不能只看已有输出做抽象总结。

第二，Harness Agent 应输出结构化 Review artifact，固定检查覆盖、遗漏、格式和粒度，并形成明确、可执行的 `next_actions`。

第三，应用或 Harness 应明确控制两阶段调用、结束信号和实验变量，不要把编排动作误写成 Memory System 的能力。

第四，AgentCore Memory System 使用内置 `EPISODIC` strategy 时，应明确区分 session-level episode 与 actor-level reflection，以及 Extraction、Consolidation、Reflection 和 Retrieval 各阶段。

第五，AgentCore Memory System 保存和检索的重点应是方法性经验，而不是历史业务答案；Harness 将检索结果注入新的 Harness Agent session。

第六，团队应区分源覆盖问题和任务边界问题。前者可以通过原文驱动的 Self-review 改善，后者仍需任务规范、Reviewer 或人工反馈。

第七，评估时不能把记录条数直接当作质量分数。Reviewer 应分别检查忠实性、完整性、粒度、过度抽取和业务边界。

最终 takeaway 是：

> Memory 的价值不是让 Harness Agent 记住上一份答案，而是让 AgentCore Memory System 复用一次高质量 Review 中形成的抽取方法。
