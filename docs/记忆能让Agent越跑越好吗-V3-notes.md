# 《Agent 记忆最佳实践｜结构化数据抽取场景》Speaker Notes

> 对应文件：`记忆能让Agent越跑越好吗-V3.pptx`
> 使用方式：每个章节对应一页幻灯片，可直接复制到 PowerPoint Notes。

## Slide 1｜Agent 记忆最佳实践

今天讨论的不是一个通用聊天记忆问题，而是一个非常具体的工程问题：在结构化数据抽取场景中，怎样让 Agent 从一次任务中学习，并在下一份文档中抽得更完整。

我们希望 Memory 保存的不是历史答案，也不是整段对话，而是一次 Review 中发现的遗漏模式、检查方法和可复用抽取策略。

接下来会从结构化抽取的真实挑战开始，然后展示我们尝试过的两种自省方式、AgentCore 实际生成的 Memory，以及 Memory 开关对下一份文档抽取行为的影响。

**过渡：** 首先要明确，结构化抽取真正困难的部分是什么。

## Slide 2｜结构化抽取真正难在哪里

生成合法 JSON 对当前模型并不困难。困难的是完整性。

同一份工业文档中，信息可能同时出现在正文、技术要求、BOM 表格、附注、图纸说明和 OCR 结果中。模型通常会优先关注明显的参数和数值，但可能把整张 BOM 当成背景材料。

这一页左侧是真实测试文档的简化内容：上面有技术要求，下面有零部件表。一个结果即使 JSON 完全合法，也可能只抽了技术要求，没有处理表格。

所以我们真正需要回答的问题不是“能不能输出 JSON”，而是“Agent 如何知道自己漏了什么”。

**过渡：** 这正是 Memory 可以介入的位置。

## Slide 3｜Memory 应该在抽取回路中做什么

Memory 不应该简单保存上一次抽取出的所有记录。

更有价值的回路是：先完成一次抽取，再 Review 哪些区域容易漏、哪些字段容易错、什么粒度更合适，然后把这些经验沉淀下来，在下一份文档开始前召回。

例如，Review 可以发现：

- 容易漏掉表格和附注；
- 应该检查重复与冲突；
- 输出前要检查字段完整性；
- 下一次应先扫描章节和表格，再开始逐条抽取。

因此 Memory 保存的是方法，而不是业务答案。

**过渡：** 但“反思”本身也有不同质量，关键在于它能看到什么信息。

## Slide 4｜三种 Memory 学习信号

这里把常见的 Memory 生成方式分为三类。

第一类是抽象自省。模型只看自己的输出，总结格式和拆分规则。它能发现一些局部问题，但看不到自己完全没有抽出的区域。

第二类是结构化 Self-review。Review 同时看原文和内部草稿，因此可以检查漏段、漏表、重复、冲突和粒度。

第三类是任务目标 Review。它还会参考业务规范、Reviewer 或人工反馈，用来解决“什么应该抽”和“什么算一条”这类任务边界问题。

这三种方式不是互相替代，而是解决不同层次的问题。

**过渡：** 我们最初采用的是第一种，也就是只看输出的抽象自省。

## Slide 5｜尝试一：只看输出的抽象自省

左侧是真实使用过的反思 Prompt：给模型一次抽取结果，让它总结不超过十条、可用于未来任务的规则。

右侧是 Consolidation Prompt：把已有规则和新规则合并、去重，维护成一份不超过十五条的规则集。

从形式上看，这个方案很合理：每次运行都会生成经验，经验还会持续合并。

问题在于，反思器的输入只有“已经抽出来的内容”。如果 Agent 完全漏掉了一张表，那么这张表不会出现在它的输出里，反思器自然也不知道自己漏过。

**过渡：** 下面看这种反思实际形成了什么 Memory。

## Slide 6｜抽象自省实际记住了什么

这一页完整展示了 consolidation 后的 15 条 canonical Memory，而不只是挑选三条负面例子。

规则大致可以分成五类：

- 主体和部件归属：规则 1、2、4；
- 运输、材料和工艺类别：规则 3、10、12；
- 拆分与规范化：规则 5、6、7、8、9、11；
- 限值和描述性文本保留：规则 13、14；
- 原文溯源：规则 15。

这里需要客观看待：这些规则并不是都没有价值。例如限值符号保留、功能性描述保留和原文溯源，都是合理的质量规则。

问题在于，规则集中有多条持续强调“分别成条”和“独立拆分”。四轮抽取条数从 90 增加到 102，但最终 102 条只来自约 53 个唯一原文片段，平均每段原文被拆成 1.92 条。

因此数量增加主要体现为拆分变细，不等于覆盖了更多文档区域。模型仍然无法通过只看自己的输出，知道自己是否漏掉了整张 BOM 或整个章节。

因此正确结论不是“Self-reflection 没用”，而是“只看输出的抽象自省，学习信号不足”。

**过渡：** 要改进它，必须先区分两种不同类型的抽取错误。

## Slide 7｜抽取错误其实有两类

第一类是源覆盖问题：信息明确存在于原文，但输出里没有。例如漏掉 BOM、漏掉某个章节、重复记录或字段为空。

这种问题可以由 Agent 自己发现，只要 Review 同时看到原文和草稿。

第二类是任务边界问题：模型并不知道某类内容属于抽取目标。例如流程要求、报告要求、待确认事项，或者一条原文应该拆成几条记录。

这类问题不能只靠原文解决，需要任务规范、Reviewer 或人工反馈。

所以结构化 Self-review 的目标主要是解决源覆盖和一致性问题，而不是替代所有业务判断。

**过渡：** 基于这个判断，我们重新设计了 Self-review 流程。

## Slide 8｜Harness Agent：两阶段结构化 Self-review

这一页的执行主体是 Harness Agent，不是 Memory System。

阶段一由 Harness Agent 先在内部形成草稿，但不输出草稿，只输出一个结构化的 self_review。

self_review 固定检查五项：

- coverage；
- omissions；
- format；
- granularity；
- next_actions。

阶段二仍由同一个 Harness Agent 重新读取原文和 self_review，逐项执行 next_actions，再生成最终五字段 JSON。

关键变化是：Harness Agent 的 Review 不再只是模型内部一句“我检查过了”，而是 session 中真实存在、可观察、可执行、随后可以被 AgentCore Memory System 提炼的 Artifact。

这里不要求模型暴露完整思维过程，只要求它输出结构化检查结果和修订动作。

**过渡：** 接下来看看 AgentCore 如何把这一整段执行轨迹转成 Memory。

## Slide 9｜AgentCore Memory System：用 EPISODIC 策略提炼轨迹

这一页的执行主体是 AgentCore Memory System。使用的策略类型是 AgentCore Memory 内置的 `EPISODIC` strategy。

Harness Agent 先产生原文、self_review、最终 JSON 等 session events。Memory System 随后异步执行：

1. Episode Extraction：逐 turn 分析行为与结果；
2. Consolidation：形成 session-level episode；
3. Reflection：形成 actor-level 可复用策略。

在本次源任务中，session 包含：

- 13 页液氮罐技术要求；
- 结构化 self_review；
- 根据 next_actions 修订后的最终 JSON；
- 明确的任务结束信号。

最终实际生成了一条 session-level episode 和两条 actor-level reflection。Episode namespace 为 `/episodes/{actorId}/{sessionId}`，reflection namespace 为 `/episodes/{actorId}`。

这里需要注意：提炼是异步的，不保证每个短 session 都一定形成 Memory。

**过渡：** 下一页直接展示托管策略实际生成的内容。

## Slide 10｜AgentCore Memory System 实际生成的 Records

这一页所有内容的生成主体都是 AgentCore Memory System 的内置 EPISODIC strategy，不是 Harness Agent 手工写入的规则。

左侧是 Consolidation 生成的 session-level episode 中的 reflection。它总结的是这一次任务的经验：两阶段流程降低了复杂文档的一次性遗漏风险，OCR、章节跳号、重复表格和图片限制应该显式处理。

中间和右侧是 EPISODIC Reflection 阶段生成的 actor-level reflection，它们抽象成了更可复用的方法：

- 先检查 coverage、omissions、format 和 granularity；
- 再系统执行 next_actions；
- 保留原文用于追溯；
- 遇到冲突时不静默丢弃信息。

Episode 回答“这一次任务发生了什么”，actor reflection 回答“未来遇到什么场景时应该怎么做”。

这些内容是 AgentCore 托管策略实际生成的，不是我们手工编写后塞进 Memory 的规则。

**过渡：** 有了这些 Memory，下一步是在一份全新文档上做 Memory 开关对照。

## Slide 11｜Harness Agent 留出实验：目标端只改变 Memory 开关

目标抽取的执行主体是 Harness Agent。源文档是 13 页液氮罐技术要求，目标文档是一页电机图纸。两个任务使用不同的设备和文档格式，目标调用使用全新 runtime session。

两组目标调用保持一致：

- 相同测试文档；
- 相同 invocation-level system prompt；
- 相同模型；
- `temperature=0`；
- `maxTokens=32768`；
- `skills=[]`；
- `tools=[]`。

唯一变量是 Memory System 是否参与目标调用：

- Memory 组：Harness 绑定 AgentCore Memory，自动检索并注入 EPISODIC records；
- No Memory 组：Harness 的 Memory 配置为 disabled。

目标端没有接收源文档答案，只会由 Harness 自动召回 source actor 的托管 Memory。

**过渡：** 下一页看两组实际输出关注点发生了什么变化。

## Slide 12｜Harness Agent 输出：Memory 注入后关注点发生变化

两组结果都由 Harness Agent 生成。左侧 Memory 组在调用前接收了 Memory System 自动注入的 records；右侧 No Memory 组没有任何持久记忆上下文。

Memory 组进一步把两张 BOM 系统展开。例如：

- 机座；
- 前端盖；
- 转子；
- 轴承；
- 壳体组件；
- 法兰盘组件；
- 散热器组件。

No Memory 组主要关注标题栏和技术要求，只零散抽出了少量数量信息。

首次运行中，Memory 组输出 31 条，No Memory 组输出 11 条。

这里不能直接解释成“质量提升了三倍”。正确解读是：Memory 改变了 Agent 对“什么值得结构化”的判断，使它更主动覆盖表格。

这些新增条目是否全部属于业务目标，仍需要人工评审。

**过渡：** 现在可以统一解释为什么前后两种自省方式表现不同。

## Slide 13｜Harness Agent 的两种 Review，为何产生不同 Memory

两种 Review 都由 Agent/LLM 执行，但 Memory 的形成主体不同。

抽象自省只看到模型输出，应用侧再调用 LLM 合并规则，生成的是通用拆分和格式规则，因此作用有限，还可能造成过度拆分。

结构化 Self-review 由 Harness Agent 同时查看原文和内部草稿；完整 session 随后由 AgentCore Memory System 的 EPISODIC strategy 提炼，因此能形成覆盖、遗漏、表格和冲突等可复用经验。

它们并不是同一种学习信号，所以结果不同并不矛盾。

统一结论是：

- 源覆盖和一致性问题，可以通过原文驱动的 Self-review 改善；
- 任务边界问题，仍然需要规范、Reviewer 或人工反馈。

**过渡：** 最后一页将这些观察收敛成可复用的工程原则。

## Slide 14｜结构化数据抽取的 Memory 最佳实践

第一，Harness Agent 的 Review 必须看原文，不能只看输出做抽象总结。

第二，Harness Agent 应输出结构化 Artifact，固定检查覆盖、遗漏、格式和粒度。

第三，建议必须可执行，形成明确的 next_actions。

第四，区分源覆盖问题和任务边界问题，不要让 Self-review 承担它无法完成的业务判断。

第五，Memory 内容应保存方法，不保存历史答案。

第六，Memory System 使用 EPISODIC strategy 时，要区分 episode 与 actor reflection：前者描述一次任务，后者沉淀跨任务方法。

第七，在 Harness Memory 配置中控制召回数量、清理噪声，避免长 episode 撑爆上下文。

第八，对结果进行人工校准，分别检查忠实性、完整性、粒度和过度抽取。

最后的 takeaway 是：

> Memory 的价值不是记住历史答案，而是复用经过 Review 得到的抽取策略。
