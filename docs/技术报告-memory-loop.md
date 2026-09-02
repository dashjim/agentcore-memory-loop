# Memory-Loop 技术报告：AgentCore Harness + Memory 上的自学习信息抽取

> 复现自 AWS 博客 [Self-learning evolvable agents for cultural tourism info extraction with AgentCore](https://aws.amazon.com/cn/blogs/china/self-learning-evolvable-agents-for-cultural-tourism-info-extraction-with-agentcore/)。
> 本报告给出**完整的设计细节、提示词/Skill 全文、评分方法与实验全过程数据**。区域 us-west-2，日期 2026-08~09。

---

## 摘要

在**单个 AgentCore Harness + Memory** 上复现博客的"agent 靠长期记忆越跑越好"，场景换为**工业技术文档抽取**（低温液氮储罐技术要求 → 结构化 `设备主体/设备部件/指标名称/指标特征/原文`）。对比三种记忆方案：`无记忆(none)`、`Episodic(AgentCore 内置策略)`、`自定义双策略(custom, 复现 SCOPE)`。在同一份 13 页文档上各重跑多次，用 Ground Truth 经 LLM-as-judge 量化覆盖率/准确率。

**主要发现（如实）**：
- **Episodic 呈现最清晰的记忆自学习效果**：覆盖率随重跑上升（0.821→0.837→0.870→0.854），准确率高（~0.88），抽取条数收敛到 GT 条数（123），token 低且稳（~28k）。
- **自定义 SCOPE**：机制完整，且**规则可观测地自进化**（战略记忆从 7 条→12 条→15 条抽取指南）；但客户端工具回路使 token 昂贵（20 万~96 万），本轮覆盖率未见提升。
- `none` 基线覆盖率稳定 ~0.77，验证记忆带来的增量。
- 与博客"反思轮数递减"不同：本工业场景效果体现在**覆盖率/抽取完整度与成本**上。

---

## 术语速查（基础概念，先读）

理解本报告需要的核心概念，按"设计里怎么用到"来解释：

- **AgentCore Runtime vs Harness**：Runtime = 你把 agent 代码打包成容器托管；**Harness = 配置驱动的托管 agent**——只声明 `model / tools / skills / memory / systemPrompt` 即可运行，无需写容器。本项目用 **Harness**（博客用 Runtime，这是主要差异）。
- **Harness Skill**：挂在 harness 上的一份 **SOP 文档（`SKILL.md`，编号步骤）**，agent 在自己的推理循环里**按这套步骤执行**。本项目把"回忆→抽取→自审→修订→沉淀"的**反思编排写成 Skill**（见 §3.2），而不是用外部代码编排。
- **inline_function 工具 + "工具回路"**：harness 声明的函数型工具，**没有服务端实现**；agent 调用它时，会把"要调工具"（toolUse）**流式返回给客户端**，由客户端（我们的 `orchestrator`）真正执行、再把结果（toolResult）用**同一会话**回传给 agent 续跑。这一来一回就是**"工具回路"**——custom 模式的 `recall_lessons`/`record_lesson` 就这么工作（见 §2.3）。
- **AgentCore Memory 的 event / strategy / record / namespace / actorId / sessionId**：见 **§2.2.0**（记忆的两层数据、两条读路径、三个作用域键——这是"记忆隔离"设计的基础）。
- **Episodic 记忆（情节记忆）**：AgentCore Memory 的一种策略——把一次交互当作一个"情节"，自动提炼 `situation/intent/assessment/reflection` 存下，下次同类任务自动注入上下文。本项目 **episodic 模式的自学习就靠它**（详见 §2.2.0 与 §6.4）。
- **SCOPE**：博客提出的机制——agent **从执行轨迹里学习、把经验进化成提示**，区分**战略记忆（跨任务通用）**与**战术记忆（当前任务即时）**。本项目 custom 模式复现之。
- **ReAct**：`Thought→Action→Observation` 的推理-行动循环，是本项目"抽取→自审→修订"反思循环的思想基础。
- **Ground Truth（GT）**：既有的标准抽取结果（`csv/flattened_data_restructured_*.csv`），**只用于评分**，绝不进入 agent 上下文。
- **LLM-as-judge**：用一个"裁判 LLM"给抽取结果打分（把抽取项与 GT 语义对齐、逐字段判对错），见 §4。
- **覆盖率 / 准确率**：覆盖率=对齐上的 GT 条目/GT 总数；准确率=匹配条目的字段级正确率。定义见 §4。
- **`__META__`**：agent 在最终 JSON 之后另起一行输出的 `{"revision_count": N}`，供外层采集"本次自审-修订循环发生了几次"。

---

## 1. 背景与目标

博客用 **AgentCore Runtime + Strands 多 agent（Orchestrator + CSV Analyzer/MD Extractor/Validator）+ SCOPE 提示进化** 做文旅酒店合同抽取。本项目差异化：

| 维度 | 博客 | 本项目 |
|---|---|---|
| 承载 | Runtime 容器 + Strands 多 agent | **单 AgentCore Harness**（Model A，配置驱动） |
| 编排 | Orchestrator 编排 3 子 agent | **Harness Skill 驱动、单 agent 在自身 loop 内反思** |
| 场景 | 文旅酒店报价单 | 工业技术文档（液氮储罐技术要求） |
| 记忆 | Runtime 侧 Memory | Harness 侧 Memory，对比 none/episodic/custom |

---

## 2. 系统设计

### 2.1 架构与数据流
```
UI / 实验脚本 ── run_extraction(doc, mode, warm) ──► orchestrator（薄驱动，不做编排）
  1) corpus 载入 markdown_corrected/*.md + tables
  2) invoke_harness（按 mode 选 harness/override）── 反思编排在 harness 内的 Skill 执行
       custom: 流里出现 recall/record 的 toolUse → 本地 memory_tools 执行 → 回传 toolResult → 同 session 续调
  3) _parse_final：从冗长输出健壮提取最终 JSON 数组（json_repair 兜底）
  4) _passes_gate：合规门禁（空/字段缺→补一次 invoke）
  5) scorer.score：LLM-as-judge（judge 复用 harness）vs GT → 覆盖率/准确率
  6) runstore：落库（轮数/耗时/token/覆盖率/准确率）
runs.db(SQLite) ─► FastAPI(127.0.0.1:8600) ─► 单页 A/B/C 面板；/api/memory 实时读沉淀规则
```

### 2.2 记忆隔离设计（核心）

#### 2.2.0 先厘清 AgentCore Memory 的几个原语（否则下面看不懂）
AgentCore Memory 有**两层数据**和**两条读路径**：

- **事件 event（原始层）**：一次对话/消息的原始记录。用 **`create_event`** 写入（按 `actorId`+`sessionId` 归档，需 `eventTimestamp`）；用 **`list_events`** 读回——**逐字、即时、按 `actorId`+`sessionId` 精确取**，写完立刻能读到。
- **策略 strategy（抽取管线）**：给 Memory 挂的"提炼器"，类型有 `SEMANTIC/EPISODIC/SUMMARIZATION/USER_PREFERENCE`。它**异步**扫描原始事件，提炼出更高层的**记忆记录 memory record**，写进策略自己定义的 **namespace**（模板决定，如 SEMANTIC=`/users/{actorId}/facts`、EPISODIC=`/episodes/{actorId}`）。
- **记忆记录 memory record（提炼层）**：策略产出的结构化条目。用 **`retrieve_memory_records`** 读——**语义检索**（给 query + topK，返回最相关的记录），是"按意思找"，不是"逐字取"。

**本项目用到的两种策略**：
- **SEMANTIC**：从事件里抽取零散"事实/知识点"，适合语义问答。本项目给 customMem 挂了它（但 custom 模式其实**没依赖它的提炼**，只把 customMem 当事件存储用，见 §2.2.1）。
- **EPISODIC（＝"情节记忆"，本项目 episodic 模式的核心）**：把**一次完整交互当作一个"情节 episode"**，自动提炼成结构化反思——`situation(发生了什么)` / `intent(目标)` / `assessment(是否达成：Yes/Partially/No)` / `reflection(教训)`，写入 `/episodes/{actorId}` namespace。下次同类任务时，这些情节被**自动注入**上下文，让 agent"记得上次是怎么做的、错在哪、要覆盖哪些类别"。这就是 episodic 模式"越跑越好"的来源——§6.4 展示了真机提炼出的 5 条情节原文。它与 custom 的"显式规则列表"互补：**episodic=经验情节（隐式、AgentCore 自动提炼与注入）** vs **custom=提炼规则（显式、我们自管存取）**。

一句话：**`create_event`/`list_events` 操作原始事件（精确、即时）；`retrieve_memory_records` 操作策略提炼出的记录（语义、异步生成）**。两者读的是不同层的东西。

**三个作用域键（记忆隔离就是靠它们，是本设计的核心）**：
- **`actorId`（谁的记忆）**：实体/用户标识。所有事件、记录都挂在某个 actor 下，天然隔离不同实体。本项目固定 `memory-loop`。
- **`sessionId`（哪个分区/哪次会话）**：事件按 `actorId + sessionId` 归档；`list_events` **必须**同时给 `actorId` 和 `sessionId` 才能取（不能只按 actor 列全部）。→ **本项目正是用 `sessionId` 作为"记忆分区"的隔离键**：战略记忆放一个固定 session、每份文档的战术记忆放各自的 session（见 §2.2.1）。
- **`namespace`（提炼记录的归类路径）**：**属于"提炼层"**——策略把提炼出的记忆记录按一个**路径模板**归类，如 SEMANTIC 用 `/users/{actorId}/facts`、EPISODIC 用 `/episodes/{actorId}`（`{actorId}` 会被实际值替换）。`retrieve_memory_records` 就是"在某个 namespace 下按语义 query 检索记录"。namespace 由**策略**决定，我们改不了；所以 custom 模式**不靠 namespace 做隔离**（改用 sessionId），episodic 模式则由策略自动用 namespace（§6.4 我们就是从 `/episodes/memory-loop` 这个 namespace 读出情节的）。

> 小结：**actorId=谁、sessionId=哪个分区（我们用它做隔离）、namespace=策略给提炼记录归类的路径（提炼层专用）**。三者层层缩小作用域。

#### 2.2.1 我们的选择：自定义记忆用"事件层"，不用"提炼层"
**为什么 custom 模式不用 `retrieve_memory_records`**：
1. **异步延迟**——策略提炼是后台异步的，`record_lesson` 刚写完的经验，`retrieve_memory_records` 当下读不到（提炼还没跑），破坏"本轮写、下轮立刻用"的确定性；
2. **namespace 不由我们控**——记录落在策略模板决定的 namespace，与我们想要的 `/strategy`、`/tactic` 分区语义对不上；
3. **我们的"经验"本就是已提炼好的短规则**，不需要再被语义抽取一遍，只要**逐字存、逐字取**。

因此 custom 模式改用**事件层**：`create_event` 写规则、`list_events` 读规则（精确、即时、可控分区）。
> 注：`retrieve_memory_records` 并非没用——**episodic 模式正是依赖策略提炼**，其自动注入靠的就是 EPISODIC 策略产出的记录；§6.4 里我们也正是用 `retrieve_memory_records` 去**读出 episodic 记住的 5 条情节**。即：**custom=事件层（我们自管），episodic=提炼层（AgentCore 托管）**，两种模式刻意用了两条不同路径。

**分区（隔离）方案** —— 用 **sessionId 承载记忆分区**，与 harness 的 `runtimeSessionId` 完全解耦：

| 记忆层 | sessionId 设计 | 作用域 | 何时检索 |
|---|---|---|---|
| **战略记忆 M_strat** | `strat-{actorId}`（右填充至 ≥33 字符） | **全局、跨文档、跨运行** | 每次抽取前 |
| **战术记忆 M_tact** | `tact-{actorId}-{md5(doc_name)[:8]}`（右填充至 ≥33） | **按文档**（同一文档重跑累积其技巧） | 处理该文档时 |

- `actorId` 固定 `memory-loop`（实体级隔离）。
- sessionId 必须 ≥33 字符（AgentCore 约束），故对短名右填充 `x`。
- 按文档派生用 `md5(doc_name)[:8]`，保证不同文档进入不同分区、同一文档跨运行落到同一分区从而累积。
- 写入（`memory_tools.record_lesson`）：
  ```python
  create_event(memoryId, actorId, sessionId=_session_for(scope, actor, doc),
      eventTimestamp=now(),                                 # ← 必填，曾遗漏
      payload=[{"conversational":{"content":{"text": 规则文本},"role":"ASSISTANT"}}])
  ```
- 读取（`memory_tools.recall_lessons`）：`list_events(memoryId, actorId, sessionId=分区, includePayloads=True)` → 取 payload 文本、去重保序。`list_events` 的 `sessionId` 必填（不能只按 actor 列）。

> 该方案是**真机实测后定的**：`list_events(sessionId)` 立即返回逐字 payload；`create_event` 必带 `eventTimestamp`；SEMANTIC 异步检索不适合"即时精确召回"。

### 2.3 三种模式的承载与记忆绑定

`InvokeHarness` **无 memoryId 入参**——记忆绑定是**资源侧**的，故用两个 harness：

| 模式 | Harness | 记忆 | 自学习机制 | 客户端工具回路 |
|---|---|---|---|---|
| **none** | `extractor` | 无 | 无（基线，每次从零） | 否（override：自包含无工具提示） |
| **episodic** | `extractor_ep`（`memory={mode:existing,name:episodicMem}`） | episodicMem（EPISODIC 策略） | AgentCore **原生**：自动把过往回合经验注入上下文 | 否（原生托管） |
| **custom** | `extractor`（工具 recall/record + skill scope-extract） | customMem（写事件、双 namespace） | **SCOPE**：recall→抽取→自审→record，战略/战术双分区 | 是 |

---

## 3. Agent 提示词与 Skill（全文）

### 3.1 system-prompt（extractor，抽取人设 + 红线）
```markdown
你是一个工业技术文档信息抽取助手，从中文工业技术文档的 Markdown 抽取"设备—部件—指标"信息。
## 抽取目标（严格遵循）
- 设备主体：最大的设备（如"150m³ 液氮储罐"）
- 设备部件：构成主体的子部件/零件（排液管线、法兰、防呆接头…）
- 指标名称：部件的设计指标名（口径、数量、材质、压力、容积…）
- 指标特征：取值，数值(48.3×3.6) 或 文本(不锈钢/防呆/可拆卸)
- 原文：对应的原始文本片段
## 红线（绝不违反）
1. 忠实抽取，不臆造。
2. 输出严格 JSON 数组，无多余文字；**值内引号一律用中文「」/全角""，绝不用英文双引号**（否则破坏 JSON）。
3. 不擅自补单位/符号。
4. 不因格式不规范而跳过。
## 工作方式
配备 scope-extract 技能与 recall_lessons/record_lesson 工具；严格按技能步骤：回忆→抽取→自审修订→沉淀经验。你看不到标准答案。
```

### 3.2 scope-extract Skill（custom 模式，SCOPE 反思循环，全文）
```markdown
---
name: scope-extract
allowed-tools: [recall_lessons, record_lesson]
---
## Steps
1. 回忆：recall_lessons(scope="strat") + recall_lessons(scope="tact")，把规则读入上下文，逐条应用。
2. 抽取：逐段按字段抽取，一个部件多指标各成一条，形成草稿 JSON。
3. 自审：对照 criteria 列出每条违规——
   a.完整性(有无漏抽/主体是否对) b.无臆造(能否在原文找到) c.格式(合法JSON/字段齐全) d.一致性(无重复)
   无违规→跳第5步。
4. 修订：有违规且 revision_count<4 → 修正、+1、回第3步；达4则停。
5. 沉淀：可跨文档复用经验→record_lesson("strat",…)；仅当前文档技巧→record_lesson("tact",…)。
6. 输出：只输出最终 JSON 数组；其后一行 __META__ {"revision_count": N}（供外层采集反思轮数）。
```

### 3.3 scope-extract-native Skill（episodic 模式，无显式工具，靠原生记忆）
```markdown
---
name: scope-extract-native
---
## Steps
1. 参考经验：回顾上下文中自动注入的过往同类任务经验（episodic memory）。
2. 抽取 → 3. 自审 → 4. 修订(≤4轮) → 5. 输出 JSON + __META__。
```

### 3.4 none 基线内联提示（`_none_system_prompt`）
= system-prompt 的抽取 schema 部分 + 一段"你没有任何记忆或外部工具，逐段抽取→自审修订(≤4)→输出 JSON + __META__"。无 Skill、无工具、无记忆——纯基线。

---

## 4. 评分方法（LLM-as-judge）

**为何 judge 复用 harness**：本环境的会话角色（EC2 SSM Role）**无 Bedrock 直连权限**（`converse` 报 API Key 错），而 harness 执行角色有。故 judge = 一次 `invoke_harness`，override 评审系统提示、清空 skills/tools、`temperature=0`、`maxTokens=8192`。

- **judge 系统提示**：`你是严格的评审器（LLM-as-judge），只输出符合要求的 JSON，不要任何解释、不要调用任何工具。`
- **对齐 prompt（要点）**：给出【抽取结果】与【GT】两组带 index 的记录，要求：① 为每个 GT 条目找语义对应的唯一 extracted 条目（找不到记 `extracted_index=null`）；② 对匹配条目逐字段判 `正确/部分/错误`（字段对应：主体↔设备主体、部件↔设备部件、特征值↔指标名称+指标特征、原文↔原文）；只输出 `{"alignments":[{gt_index,extracted_index,field_judgments}]}`。
- **GT 分块**：GT 每 20 条一块（连同全部 extracted）单独送 judge，避免一次性 ~90×123 对齐导致输出截断/摆烂；聚合各块结果。
- **指标定义**：`覆盖率 = 对齐上的 GT 条目数 / GT 总数`；`准确率 = 匹配条目的字段级正确率`（正确=1/部分=0.5/错误=0 的均值）。
- **GT 隔离**：GT（`csv/flattened_data_restructured_*.csv`）**只用于评分，绝不进入 agent 上下文**。

---

## 5. 实验设计

**公共设置**：脚本 `scripts/run_experiments.py`。目标文档 = 13 页"150方液氮罐技术要求"（GT 123 条）；B 文档 = 小文档"2477080009简图"（GT 6 条）。抽取与裁判模型均为 `claude-sonnet-4-6`。**运行前 `clear_memory_for_mode("custom")` 清空自定义记忆**，保证从零开始（episodic 记忆由 AgentCore 托管、按 `actorId` 累积，无法逐条清空，是一处局限，见 §9）。

**每一次"运行"的统一流程**（三个实验里的每次运行都走这条）：
```
载入文档文本(markdown_corrected + tables)
 → invoke_harness（按 mode 选 harness / skill / 是否带 recall|record 工具）
 → agent 在 harness 内按 Skill 执行：回忆经验 → 抽取 → 自审 → 修订(≤4) →(custom)沉淀经验
 → 客户端解析最终 JSON 数组 + __META__（json_repair 兜底）
 → 合规门禁（空/字段缺 → 补一次 invoke）
 → LLM-as-judge 对齐 GT → 覆盖率/准确率
 → 落库 runs.db（mode/warm/反思轮数/耗时/token/覆盖率/准确率/抽取数）
```

### 实验 A · 记忆生效（越跑越好）
- **假设**：带记忆的模式（episodic/custom）在**同一文档上重跑会越来越好**（覆盖率/完整度上升或轮数下降）；无记忆（none）应基本持平。
- **输入**：固定的目标 13 页文档 × 三模式；`none×2`、`episodic×4`、`custom×4`，**同模式内串行**执行。
- **过程**：先清空 custom 记忆 → 依次跑 `none#1,#2`（warm=False）→ `episodic#1..4`（#1 warm=False，其后 warm=True）→ `custom#1..4`（同）。**"串行"是关键**：episodic/custom 每轮把经验写回记忆，下一轮开工前自动注入(episodic)或主动 `recall_lessons`(custom)，形成"跑一次→学一点→下次更好"的闭环；warm 标记该轮是否已有先验记忆。
- **输出 / 度量**：每次运行的 覆盖率、准确率、反思轮数、抽取条数、token。
- **预期与判读**：把每模式覆盖率按"第 N 次运行"连成折线（UI 实验A面板）；带记忆模式应见**上升趋势**、none 持平。→ 结果见 **§6.1**。

### 实验 B · 战略记忆迁移
- **假设**：实验A 里积累的**战略记忆（跨文档通用规则）能迁移到一份没见过的新文档**，使带记忆模式的首轮就优于无记忆。
- **输入**：一份**新文档**（B 文档，A 阶段未跑过）× 三模式各一次；`custom` 用 `warm=True`（复用 A 积累的 M_strat），`none/episodic` 为首见。
- **过程**：紧接实验A 之后（此时 M_strat 已增补到 15 条）在 B 文档上跑 `none / episodic / custom` 各一次。
- **输出 / 度量**：三模式在 B 文档上的**首轮** 覆盖率、准确率、token。
- **预期与判读**：分组柱图对比（UI 实验B面板）；带经验（尤其 custom warm）应不差于 none。→ 结果见 **§6.2**（注：本次 B 文档 GT 仅 6 条，区分度不足，是设计缺陷）。

### 实验 C · 记忆可观测
- **假设**：agent 的"自学习"是**可检视**的——能读出它到底记住 / 进化出了什么内容。
- **输入**：无需额外运行；对象是实验A/B 跑完后 AgentCore Memory 里沉淀的内容。
- **过程**：直接读记忆——custom 用 `list_events` 读 `strat`/`tact` 两个分区的规则；episodic 用 `retrieve_memory_records` 读 `/episodes/{actorId}` 的情节记录。
- **输出 / 度量**：M_strat / M_tact 的规则条目与版本演进；episodic 的情节反思条目（situation/intent/assessment/reflection）。
- **预期与判读**：应看到 custom 规则**跨运行逐步增补/进化**、episodic 情节记录累积。→ 结果见 **§6.3（custom）/ §6.4（episodic）**。

---

## 6. 实验结果（完整数据，取自 runs.db）

> 严格对应 §5 的**实验 A / B / C**。（脚本 `run_experiments.py` 内部把同文档重跑那批叫 "Phase A"、新文档那批叫 "Phase B"，即此处的实验A、实验B；实验C 无需额外运行，直接读记忆。）
> **记忆的完整导出**（M_strat 全文 + episodic 全部 15 条情节）见附件 [`docs/memory-dump.md`](memory-dump.md) / [`memory-dump.json`](memory-dump.json)（由 `scripts/dump_memory.py` 真机导出；§6.3/6.4 仅摘录）。

### 6.1 实验 A · 记忆生效（越跑越好）—— 同一 13 页文档（GT=123）逐次重跑

| 序 | 模式 | warm | 反思轮 | 覆盖率 | 准确率 | 抽取条数 | 总 token |
|---|---|---|---|---|---|---|---|
| 1 | none | ✗ | 2 | 0.764 | 0.846 | 91 | 32,388 |
| 2 | none | ✗ | 3 | 0.780 | 0.840 | 98 | 40,876 |
| 3 | **episodic** | ✗ | 1 | **0.821** | 0.896 | 123 | 28,189 |
| 4 | **episodic** | ✓ | 1 | **0.837** | 0.881 | 126 | 28,276 |
| 5 | **episodic** | ✓ | 1 | **0.870** | 0.875 | 122 | 28,177 |
| 6 | **episodic** | ✓ | 1 | **0.854** | 0.878 | 123 | 28,312 |
| 7 | custom | ✗ | – | 0.748 | 0.839 | 80 | 246,707 |
| 8 | custom | ✓ | 1 | 0.732 | 0.890 | 83 | 207,468 |
| 9 | custom | ✓ | – | 0.748 | 0.843 | 89 | **959,072** |
| 10 | custom | ✓ | – | 0.780 | 0.872 | 95 | 76,483 |

**解读（如实）**：
- **Episodic**：覆盖率 0.821→0.837→0.870（升）→0.854（微降），抽取条数稳定收敛到 GT 的 123 条附近，准确率 ~0.88，token ~28k、单轮完成——**记忆自学习效果最清晰、成本最低**。
- **none**：0.764→0.780，基本持平（无记忆，符合预期）。
- **custom**：覆盖率 0.73~0.78 无明显上升，抽取条数偏少（80~95<123，欠抽），准确率高(~0.87)；反思轮数多为 None（工具回路里 __META__ 未稳定输出）。**token 极贵（20 万~96 万/次）——原因如下**：
  > custom 每调一次 `recall/record` 工具，因 inline_function 无服务端实现，agent 会把控制权交回客户端，我们执行后**用同一会话重新 `invoke_harness`**——而**每一次重调都要把"系统提示 + Skill + 整份 13 页文档 + 之前所有轮次对话"作为输入 token 再发一遍**。custom#3 做了 6 个来回（`client_invoke_loops=6`）+ 冗长自审文本，于是**单次抽取累计 959,072 token**（≈15 万输入 × 6 轮）。对比 episodic 单次 invoke、~2.8 万 token——**贵在"同一份大文档被反复整体重发"**，这是客户端工具回路 + 长文档的固有代价。

### 6.2 实验 B · 战略记忆迁移 —— 新文档（GT=6）三模式首轮
| 模式 | 覆盖率 | 准确率 | token |
|---|---|---|---|
| none | 0.667 | 0.692 | 9,797 |
| episodic | 0.667 | 0.562 | 17,988 |
| custom | 0.667 | 0.688 | 11,260 |
覆盖率均 0.667（4/6），GT 太小不足以区分模式；准确率上 none/custom 略优于 episodic（首见新文档、无先验）。

### 6.3 实验 C · 记忆可观测（一）：custom 的战略/战术记忆
> 实验C 不需额外运行，直接读 AgentCore Memory 里 custom 与 episodic 两种模式各自沉淀的内容。本小节看 custom（自管的显式规则），§6.4 看 episodic（AgentCore 自动提炼的情节）。

custom 模式跨 4 次运行，`record_lesson("strat", …)` 沉淀出 **3 个版本、规则从 7 条增补到 15 条**的抽取指南（`/strategy/memory-loop` 分区，`list_events` 读出）：

**v1（初版，7 条，197 字）**
> 液氮储罐技术要求文档抽取经验：1.整机参数归属「储罐整体」部件；2.接口通径(DN)和验收管口规格(Φ外径×壁厚)分别用「通径」和「管口规格」区分；3.配套清单每个部件的规格和数量分成两条记录；4.英寸符号用「英寸」替代以保证JSON合法；5.环境条件（温度/风速/风压/地震烈度）不是设备部件指标不抽取；6.运输保护参数和交货状态保护气露点属于设备要求可抽取；7.字段值内引号用中文引号「」。

**v2（增补，12 条，345 字）** —— 在 v1 基础上新增：8.地脚螺栓规格/数量/配套件分别抽取；9.供液管道双阀、下进液管防涡装置等功能性要求也作指标；10.外罐/内罐/管道阀门材料分三条；11.自增压器能力归属「自增压器」而非整体；12.表2 仅有数量无规格的条目只抽数量一条。

**v3（增补v2，15 条，468 字）** —— 再新增：13.焊接检测要求（RT/PT 比例、合格级别）按焊缝类型（A/B、C/D/E 类）分组、归属「内罐焊接接头(X类)」；14.外增压进气管 DN 通径与 Φ 管口规格均抽；15.充装法兰备注（含配套法兰及紧固件）单独抽一条。

> 这直观展示了 SCOPE 的"自我进化"：agent 把每轮学到的抽取规则不断增补进战略记忆（7→12→15 条），且规则高度领域具体、可操作。这是本项目 custom 模式的核心价值，尽管它未在覆盖率数字上体现。

**战略 vs 战术两种记忆（对应博客）**：本设计的自定义双策略实现了博客提出的两类记忆——**战略记忆 M_strat**（`/strategy/{actorId}`，跨文档通用，即上述 3 条规则）与**战术记忆 M_tact**（`/tactic/{actorId}/{md5(doc)}`，仅当前文档）。实测本轮 **M_strat=3 条（自进化到 15 条规则），M_tact=0 条**——agent 判定其学到的经验多为跨文档可复用，故全部沉淀为战略记忆；战术分区为空。这说明模型在本任务上倾向于抽象出通用规则，而非文档专属技巧。

### 6.4 实验 C · 记忆可观测（二）：episodic 的情节记忆（真机读取 `episodicMem`）
episodic 模式下，AgentCore 的 EPISODIC 策略从每次运行的轨迹**自动提炼出"情节记录"**（`/episodes/memory-loop` 分区，共 15 条，`retrieve_memory_records` 读出）。

**记录结构与召回方式（实测）**：每条记录的 `content.text` 是**一整段 JSON，含 `situation / intent / assessment / justification / reflection` 全部字段**（非分字段存储）。`retrieve_memory_records` 的语义检索**对整条记录（全部字段拼成的整段文本）做向量匹配**，不是只匹配某一个字段——证据：用只出现在 `reflection` 里的词"幂等消息 重复推送"检索，排第一的正是该 reflection 所在记录，说明 reflection 也参与了匹配。此外 `metadata` 带结构化标签（如 `x-amz-agentcore-memory-episode-assessment: SUCCESS`），可用 `metadataFilters` 按"成功/失败"等**精确过滤**，与语义检索互补。（单关键词查询区分度不高、score 多在 0.35~0.39，因整段向量会稀释单个短语，也印证"整条匹配"。）

以下摘录 5 条（原文；完整 15 条见附件 `docs/memory-dump.md`）：

- **记录1**（assessment: Yes）：`situation:"…初始两轮助手输出存在格式不合规问题（字段为空或输出格式不符合要求），用户随后明确指出问题并要求修正。" intent:"提取五字段合规 JSON 数组并附 __META__ 修订次数" justification:"经过三轮交互，最终输出纯 JSON 数组，所有条目五字段非空，附 __META__ {revision_count:2}"`
- **记录2**（Yes）：`"…最终在第三轮成功输出约 80 条记录的合规 JSON…五字段均非空"`
- **记录3**（Yes）：`"…最终输出约 100 条 JSON 对象…覆盖整机指标、管口接口、材料、焊缝 NDE、运输封存、交付状态、安装底座、安装环境及配套清单等全部类别，五字段均非空"`
- **记录4**（Partially）：`"…前两轮存在 Markdown 包裹和格式不合规；第三轮输出纯净 JSON 并附 __META__，但整机级指标（介质、几何容积等）设备部件字段仍存在空字符串问题"`
- **记录5**（No）：`reflection:"…应确保：1）用户完整提交原始文件后再处理；2）分步骤——先确认提取维度再输出 JSON；3）避免指令不完整即开始"`

**这解释了 episodic 为何"越跑越好"**：它记住的是**过往抽取的经验教训**（哪里格式不合规、哪类字段易空、要覆盖哪些类别、约 80~100 条的规模），下次抽取自动注入这些情节，于是抽取条数收敛到 GT 的 123 条、格式合规、覆盖率上升。与 custom 的"显式规则列表"是两种互补的记忆形态：**episodic=经验情节（隐式、自动）** vs **custom M_strat=提炼规则（显式、可控）**。

---

## 7. 与博客的对比

> 说明：博客与本项目**场景/数据/模型/评测口径不同**，数字不可直接比较；下表对比"复现了什么、哪里一致、哪里不同"。

| 维度 | 原始博客 | 本项目（实测） | 是否复现 |
|---|---|---|---|
| 承载与编排 | AgentCore Runtime 容器 + Strands **多 agent**（Orchestrator+CSV/MD/Validator）| **单 Harness + Skill 驱动单 agent 自反思** | 换了实现，机制等价 |
| 两种记忆 | **战略记忆 + 战术记忆**（SCOPE） | 双 namespace 实现 M_strat + M_tact；实测 M_strat 3 条(→15规则)、M_tact 0 | ✅ 复现两级记忆结构 |
| 提示进化/自学习 | SCOPE：从轨迹学习、进化提示 | custom：M_strat **规则自增补 7→12→15 条**；episodic：自动提炼 5 条情节反思 | ✅ 明确复现"经验随运行积累/进化" |
| 记忆效果的度量 | **反思/校验轮数递减**（图9：同文档 4→2→1 轮） | 本工业场景**轮数不稳定**（episodic 恒 1 轮、custom 多为 None）；效果体现在**覆盖率↑(0.82→0.87) 与抽取完整度↑(→123=GT)** | ⚠️ 效果存在但**载体不同**（覆盖率而非轮数） |
| 跨文档迁移 | 图10：有/无先验经验对比 | Phase B（新文档）三模式对比；但 GT 仅 6 条、区分度不足 | ⚠️ 部分复现，样本偏小 |
| 抽取质量目标 | 核心字段准确率 **≥95%**、校验错误识别率 ≥98% | episodic 准确率 ~0.88、覆盖率 ~0.87（工业长文档、GT 123、不同 judge） | ❌ 未达其目标数值（场景更难，如实） |
| SCOPE 基准增益 | 论文引用 HLE 成功率 14.23%→38.64% | 未跑 HLE；在本抽取任务上以覆盖率/规则进化佐证记忆增益 | 不适用（不同基准） |
| 成本 | 未强调 | 发现 custom 客户端工具回路 **token 昂贵（单次达 96 万）**，episodic 成本低(~28k) | 本项目新增观察 |

**一句话**：核心思想（**两级记忆 + 从执行轨迹自学习/进化**）复现成功，并有真机记忆内容佐证（M_strat 规则 7→15 条、episodic 5 条情节反思）；但"记忆效果"在本工业抽取场景主要体现在**覆盖率与抽取完整度**（而非博客的反思轮数递减），且准确率未达博客对其文旅场景宣称的 ≥95% 目标——属场景/数据/模型差异，如实呈现。

## 8. 工程陷阱与修复（过程留痕）

| 现象 | 根因 | 修复 | 佐证 |
|---|---|---|---|
| 覆盖率大面积假 0.0 | 抽取 JSON 值内**未转义英文引号**（原文里的 "液封"）→ 整个数组非法→解析空 | `_extract_json_array` 加 `json_repair` 兜底 + 提示模型值内用中文「」 | 对一份畸形输出**救回 100 条** |
| judge 时而返回全 null | ~90×123 一次性对齐输出过大→截断/摆烂 | GT 每 20 条分块 + `temperature=0` + `maxTokens=8192` | 重打分稳定 cov 0.74/acc 0.88 |
| judge 直连 Bedrock 报 API Key 错 | 会话角色无 Bedrock 直连权限 | LLM-judge 复用 harness 承载 | judge 返回纯 JSON |
| 记忆刚写读不到 / namespace 不符 | SEMANTIC 异步抽取、namespace 语义不一致 | 改 `create_event`+`list_events` 精确即时；补 `eventTimestamp` | list_events 立即返回 |
| InvokeHarness 无 memoryId | 记忆绑定在资源侧 | episodic 用单独 harness `extractor_ep` | — |
| 装的 agentcore 是旧 starter-toolkit | 与 `@aws/agentcore` 同名冲突 | 用 `@aws/agentcore` CLI；harness 无 `deploy --local`，本地=`agentcore dev`/boto3 | — |

---

## 9. 结论与局限

**结论**：在工业技术文档抽取场景，**Episodic（AgentCore 原生记忆）给出最清晰的记忆自学习增益**（覆盖率↑、抽取完整度↑、准确率高、成本低）；**自定义 SCOPE 的价值在于可观测、可复用的自进化规则库**（战略记忆 7→15 条），但客户端工具回路成本高、本轮未转化为覆盖率提升。与博客"反思轮数递减"不同，本场景效果体现在覆盖率/完整度与成本。

**局限 / Phase 2**：
- custom 工具回路 token 昂贵（单次达 96 万），可优化（压缩反思、限制迭代、或把记忆读写下沉为原生策略）。
- Episodic 记忆无法经客户端逐条清除（harness 托管），跨实验重置需删/重建 memory 资源。
- Phase B 的 GT 过小（6 条），迁移实验区分度不足，宜换更大的新文档。
- 未做：WebUI Cognito 认证 + CloudFront 部署、ALP portal 包、θ_base 的 Optimization 慢环。

**复现**：见 [README](../README.md) §5；数据在 `runs.db`（未随仓库上传），截图见 `docs/e2e_expA_coverage.png`、`e2e_expB_modes.png`。
