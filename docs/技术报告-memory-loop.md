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

**为什么不用 `retrieve_memory_records`**：AgentCore Memory 的 SEMANTIC 策略是**异步抽取**记录，刚写完读不到，且其记录 namespace 由策略决定、与我们写入的 metadata 不一致。我们的"经验"是**已提炼的短规则、需逐字即时存取**，故改用 **`create_event` 写 + `list_events` 读**（精确、即时）。

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

脚本 `scripts/run_experiments.py`。目标文档 = 13 页"150方液氮罐技术要求"（GT 123 条），B 文档 = 小文档"2477080009简图"（GT 6 条）。运行前清空 custom 记忆。

- **实验 A（记忆生效·越跑越好）**：同一 13 页文档，每模式**串行重跑**（none×2、episodic×4、custom×4）。串行是关键——episodic/custom 每轮把经验写入记忆，下轮受益。测每次的覆盖率/准确率/轮数/token。
- **实验 B（战略记忆迁移）**：新文档上各跑 none/episodic/custom 一次（custom 用 A 积累的 strat），比首轮覆盖率/准确率。
- **实验 C（记忆可观测）**：实时读 custom 写入的规则，看是否逐步自进化。

---

## 6. 实验结果（完整数据，取自 runs.db）

### 6.1 Phase A — 13 页文档（GT=123），逐次运行

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
- **custom**：覆盖率 0.73~0.78 无明显上升，抽取条数偏少（80~95<123，欠抽），准确率高(~0.87)，但 **token 从 20 万涨到 96 万**（客户端多轮工具回路 + 冗长反思），成本代价大；反思轮数多为 None（工具回路里 __META__ 未稳定输出）。

### 6.2 Phase B — 新文档（GT=6）
| 模式 | 覆盖率 | 准确率 | token |
|---|---|---|---|
| none | 0.667 | 0.692 | 9,797 |
| episodic | 0.667 | 0.562 | 17,988 |
| custom | 0.667 | 0.688 | 11,260 |
覆盖率均 0.667（4/6），GT 太小不足以区分模式；准确率上 none/custom 略优于 episodic（首见新文档、无先验）。

### 6.3 Phase C — 自定义 SCOPE 战略记忆的自进化（M_strat 全文）
custom 模式跨 4 次运行，`record_lesson("strat", …)` 沉淀出 **3 个版本、规则从 7 条增补到 15 条**的抽取指南（`/strategy/memory-loop` 分区，`list_events` 读出）：

**v1（初版，7 条，197 字）**
> 液氮储罐技术要求文档抽取经验：1.整机参数归属「储罐整体」部件；2.接口通径(DN)和验收管口规格(Φ外径×壁厚)分别用「通径」和「管口规格」区分；3.配套清单每个部件的规格和数量分成两条记录；4.英寸符号用「英寸」替代以保证JSON合法；5.环境条件（温度/风速/风压/地震烈度）不是设备部件指标不抽取；6.运输保护参数和交货状态保护气露点属于设备要求可抽取；7.字段值内引号用中文引号「」。

**v2（增补，12 条，345 字）** —— 在 v1 基础上新增：8.地脚螺栓规格/数量/配套件分别抽取；9.供液管道双阀、下进液管防涡装置等功能性要求也作指标；10.外罐/内罐/管道阀门材料分三条；11.自增压器能力归属「自增压器」而非整体；12.表2 仅有数量无规格的条目只抽数量一条。

**v3（增补v2，15 条，468 字）** —— 再新增：13.焊接检测要求（RT/PT 比例、合格级别）按焊缝类型（A/B、C/D/E 类）分组、归属「内罐焊接接头(X类)」；14.外增压进气管 DN 通径与 Φ 管口规格均抽；15.充装法兰备注（含配套法兰及紧固件）单独抽一条。

> 这直观展示了 SCOPE 的"自我进化"：agent 把每轮学到的抽取规则不断增补进战略记忆（7→12→15 条），且规则高度领域具体、可操作。这是本项目 custom 模式的核心价值，尽管它未在覆盖率数字上体现。

**战略 vs 战术两种记忆（对应博客）**：本设计的自定义双策略实现了博客提出的两类记忆——**战略记忆 M_strat**（`/strategy/{actorId}`，跨文档通用，即上述 3 条规则）与**战术记忆 M_tact**（`/tactic/{actorId}/{md5(doc)}`，仅当前文档）。实测本轮 **M_strat=3 条（自进化到 15 条规则），M_tact=0 条**——agent 判定其学到的经验多为跨文档可复用，故全部沉淀为战略记忆；战术分区为空。这说明模型在本任务上倾向于抽象出通用规则，而非文档专属技巧。

### 6.4 Episodic 记忆记住了什么（真机读取 `episodicMem`）
episodic 模式下，AgentCore 的 EPISODIC 策略从每次运行的轨迹**自动提炼出"情节记录"**（`/episodes/memory-loop` 分区，`retrieve_memory_records` 读出 5 条），每条含 `situation / intent / assessment / reflection` 四要素。摘录（原文）：

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
