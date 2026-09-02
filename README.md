# Memory-Loop：AgentCore 自学习信息抽取（复现博客核心 Memory 效果）

> **复现自 AWS 博客**：[Self-learning evolvable agents for cultural tourism info extraction with AgentCore](https://aws.amazon.com/cn/blogs/china/self-learning-evolvable-agents-for-cultural-tourism-info-extraction-with-agentcore/)
> 原文用 AgentCore Runtime + Strands 多 agent + SCOPE 提示进化做文旅信息抽取；本项目改用**单 AgentCore Harness + Memory** 承载、场景换成**工业技术文档抽取**，聚焦复现其"记忆自学习"效果。

在 **单个 AgentCore Harness + Memory** 上复现"agent 靠长期记忆越跑越好"，场景为**工业技术文档抽取**（低温液氮储罐技术要求 → `设备主体/设备部件/指标名称/指标特征/原文`）。三种记忆模式可对比：`无记忆(none) / Episodic(内置策略) / 自定义双策略(custom, SCOPE)`。区域 us-west-2。

> **完整技术报告（含记忆隔离设计、提示词/Skill 全文、评分方法、全部实验数据、记忆里记住的内容、与博客对比）**：[`docs/技术报告-memory-loop.md`](docs/技术报告-memory-loop.md)。
> 其他：结论摘要 `docs/e2e-test-report-memory-loop.md`、设计 `docs/design-memory-loop.md`。**本文件讲清代码在哪、每块逻辑、每个实验怎么做。**

---

## 1. 一图看懂数据流

```
UI/实验脚本
   │ run_extraction(doc, mode, warm)
   ▼
orchestrator.py（薄驱动，不做编排）
   │ 1) corpus.load_doc_text(doc)  载入 markdown_corrected/*.md + tables
   │ 2) invoke_harness(按 mode 选 harness/override)  ── 反思编排在 harness 内的 Skill 里
   │      custom: 流里出现 record/recall 的 toolUse → 本地执行 memory_tools → 回传 toolResult → 同 session 续调
   │ 3) _parse_final()  从冗长输出里健壮提取最终 JSON 数组（json_repair 兜底）
   │ 4) _passes_gate()  合规门禁（空/字段缺→补一次 invoke）
   │ 5) scorer.score(extracted, gt, judge_fn)  LLM-as-judge（judge 复用 harness）vs GT 算 覆盖率/准确率
   │ 6) runstore.insert_run()  落库（轮数/耗时/token/覆盖率/准确率…）
   ▼
runs.db (SQLite) ──► ui/server.py (FastAPI, 127.0.0.1:8600) ──► ui/static/index.html（A/B/C 面板）
                     AgentCore Memory ──► /api/memory（实时读沉淀的规则，实验C）
```

**核心理念**：编排（回忆→抽取→自审→修订→反思→记录）写在 **Harness Skill** 里，由 agent 在自己的 loop 内执行；Python 侧只负责调用、采指标、评分、存储、展示。

---

## 2. 代码地图（文件在哪 + 干什么）

```
memory-loop/
├── README.md                      # 本文件
├── requirements.txt               # boto3 / fastapi / uvicorn / pytest / json-repair
├── config.local.json              # 部署后真实资源 ARN/ID（HARNESS_ARN / EPISODIC_HARNESS_ARN / *_MEMORY_ID）
├── runs.db                        # SQLite 指标库（每次抽取一行）
│
├── input/
│   ├── extraction-item.txt        # 抽取字段定义（设备主体/部件/指标名称/指标特征）
│   └── corpus/output/<doc>/       # 语料：markdown_corrected/(输入) tables/ csv/(GT: flattened_data_restructured_*.csv)
│
├── memoryloop/                    # AgentCore CLI 工程（@aws/agentcore）
│   ├── agentcore/agentcore.json   # 工程配置：harnesses/memories 注册
│   └── app/
│       ├── extractor/             # 主 harness（none/custom 用）
│       │   ├── harness.json       #   model=claude-sonnet-4-6, tools=[recall_lessons,record_lesson], skill=scope-extract, memory=disabled
│       │   ├── system-prompt.md   #   抽取人设 + 红线（含"值内引号用中文「」"）
│       │   └── skills/scope-extract/SKILL.md      # SCOPE 反思流程（含 record/recall 工具步骤）
│       └── extractor_ep/          # episodic harness（绑定 episodicMem）
│           ├── harness.json       #   memory={mode:existing,name:episodicMem}, 无工具
│           ├── system-prompt.md   #   同抽取人设，靠原生记忆自动注入
│           └── skills/scope-extract-native/SKILL.md  # 反思流程（无显式工具，靠原生 episodic 记忆）
│
├── src/                           # Python 逻辑（18 单测：tests/）
│   ├── config.py        (100)     # 常量(REGION/ACTOR_ID/MODEL_ID) + load_deployed()（env>config.local.json>占位）
│   ├── corpus.py        (213)     # list_docs / load_doc_text(拼页+表格) / load_gt(解析 restructured CSV 单元格)
│   ├── memory_tools.py  (135)     # record_lesson(create_event) / recall_lessons(list_events 精确读) / clear_memory；session 分区 strat 全局·tact 按文档
│   ├── scorer.py        (200)     # LLM-as-judge：GT 分块对齐 + 逐字段判定 → coverage/accuracy
│   ├── orchestrator.py  (555)     # 薄驱动：invoke 工具回路 / 按模式选 harness / 流消费 / 解析 / 门禁 / judge 构建 / run_extraction
│   └── runstore.py      (105)     # SQLite：init/insert/list/get_run
│
├── ui/
│   ├── server.py        (182)     # FastAPI 127.0.0.1:8600：/api/docs /runs /run /memory /clear-memory /status
│   ├── mockdata.py      (202)     # 无 AWS 时的降级假数据（MEMORY_LOOP_UI_MOCK=1）
│   └── static/index.html          # 单页：控件 + 完成卡片 + 实验A/B/C 图表 + 历史表（内联 SVG）
│
├── scripts/run_experiments.py (83) # 一键跑 A/B/C 全部运行并落库（见 §4）
└── docs/                          # requirements / design / e2e-test-report + e2e_*.png 截图
```

### 关键函数逻辑（按调用顺序）
- **`orchestrator.run_extraction(doc, mode, warm)`** — 主入口。载文→invoke 回路→解析→门禁→评分→落库，返回 run dict。
- **`orchestrator._build_invoke_kwargs(deps, msgs, sid, mode)`** — 按模式拼 invoke 参数：
  - `none`：主 harness，override 自包含无工具提示（`_none_system_prompt`），`skills=[]`，不带 tools。
  - `custom`：主 harness，`skills=[scope-extract]` + `tools=[record/recall]`（走客户端工具回路）。
  - `episodic`：`extractor_ep`（绑 episodicMem），**不 override**，用其烤入的 native skill/提示 + 原生记忆。
- **`orchestrator._run_invoke_loop`** — 反复 `invoke_harness`（同一 `runtimeSessionId` 续调）：消费流→累积文本/toolUse.input 片段→若有 toolUse 则 `_execute_tool` 执行 record/recall 并回传 toolResult→continue，直到无 toolUse 得最终文本。累加 token、记轮数。
- **`orchestrator._parse_final` / `_extract_json_array`** — 从散文+草稿+围栏混杂的输出里取最终 JSON 数组；合法 JSON 走回溯匹配，非法（值内未转义引号）用 `json_repair` 兜底。
- **`memory_tools`** — `record_lesson`→`create_event`(带 eventTimestamp) 写；`recall_lessons`→`list_events` 精确即时读。分区：`strat-{actor}`（全局跨运行）、`tact-{actor}-{md5(doc)[:8]}`（按文档累积）。
- **`scorer.score`** — 把 GT 每 20 条一块，连同全部 extracted 交给 `judge_fn` 做一对一语义对齐 + 逐字段判(正确/部分/错误)，聚合：`coverage=匹配GT数/GT总数`、`accuracy=字段级正确率`。
- **`orchestrator._build_harness_judge`** — judge_fn 用 `invoke_harness`（override 评审系统提示、`skills=[]`、`temperature=0`、`maxTokens=8192`）承载 LLM 裁判（因会话角色无 Bedrock 直连权限）。

---

## 3. 三种记忆模式怎么工作

| 模式 | harness | 记忆 | 自学习机制 | 工具回路 |
|---|---|---|---|---|
| **none** | extractor | 无 | 无（每次从零，基线） | 否 |
| **episodic** | extractor_ep | episodicMem（EPISODIC 策略，harness 资源侧挂载） | AgentCore **原生**：自动把过往回合经验注入上下文 | 否（原生托管） |
| **custom** | extractor | customMem（写事件） | **SCOPE**：agent 调 `recall_lessons` 取经验→抽取→自审→`record_lesson` 沉淀（战略 M_strat / 战术 M_tact 双分区） | 是（客户端执行 record/recall） |

---

## 4. 三个实验具体怎么做（`scripts/run_experiments.py`）

脚本参数（文件头常量可调）：`TARGET_DOC_PREFIX="150方液氮罐"`（13 页、有 GT），`B_DOC_PREFIX="2477080009简图"`（小、有 GT），`N_NONE=2, N_EPISODIC=4, N_CUSTOM=4`。运行前 `clear_memory_for_mode("custom")` 清空自定义记忆。

### 实验 A · 记忆生效（越跑越好）
- **怎么做**：在**同一份 13 页文档**上，每种模式**串行重跑多次**（none×2、episodic×4、custom×4）。串行是关键——episodic/custom 每轮把经验写入记忆，下一轮受益。
- **测什么**：每次运行的**覆盖率**（vs GT，见下）、反思轮数、token。
- **预期信号**：Episodic 覆盖率随重跑上升；none 平（无记忆）；custom 视情况。
- **UI 面板**：实验 A = 三模式覆盖率随"第N次运行"的折线（`renderExpA`→`multiLineChart`）。实测 Episodic 82→84→87→85%。

### 实验 B · 战略记忆迁移
- **怎么做**：在一份**新文档**（B_DOC，A 里没跑过）上，各跑 none / episodic / custom 一次；custom 用 A 阶段已积累的 strat 经验（`warm=True`）。
- **测什么**：三模式的**首轮覆盖率/准确率**对比。
- **预期信号**：带记忆（尤其预热过的）应不差于无记忆。
- **UI 面板**：实验 B = 三模式覆盖率/准确率分组柱图（`renderExpB`→`groupedBar`）。

### 实验 C · 记忆可观测（自进化）
- **怎么做**：无需额外运行——custom 模式每轮 `record_lesson` 写入的规则，实时从 AgentCore Memory 读出展示。
- **测什么**：沉淀了哪些规则、是否逐步增补/进化。
- **预期信号**：M_strat 出现可读的抽取指南，并跨运行自我增补（实测："经验"→"增补"→"增补v2"）。
- **UI 面板**：实验 C = 两栏规则列表（`loadMemory`→`/api/memory?scope=strat|tact`）。

### "覆盖率/准确率"怎么算（评分口径）
GT = 各文档 `csv/flattened_data_restructured_*.csv`（**只用于评分，绝不喂给 agent**）。`scorer.py` 用 LLM 裁判把 agent 抽取与 GT **语义对齐**：`覆盖率 = 对齐上的 GT 条目 / GT 总数`；`准确率 = 匹配条目的字段级正确率`（正确=1/部分=0.5/错误=0）。

---

## 5. 复现 / 运行

```bash
# 依赖
pip install --break-system-packages -r requirements.txt      # 含 json-repair
npm i -g @aws/agentcore@preview                              # AgentCore CLI（bin 名 agentcore）

# 语料（若未解压）
mkdir -p input/corpus && unzip -o input/input-samples-output.zip -x "__MACOSX/*" -d input/corpus

# 部署 AgentCore 资源（需 AWS 凭据；us-west-2）——已部署则跳过
cd memoryloop && agentcore deploy --yes    # 建 extractor / extractor_ep / 2×Memory / IAM
# 把 CloudFormation 输出的 ARN 写入 ../config.local.json（见该文件字段）

# 跑全部实验（真实调用 Bedrock，约 40 分钟 / ~1.5M tokens）
cd .. && python3 scripts/run_experiments.py

# 起本地 UI（仅 localhost）
cd ui && python3 server.py          # http://127.0.0.1:8600
#   无 AWS 时用假数据预览： MEMORY_LOOP_UI_MOCK=1 python3 server.py

# 单测（不触 AWS）
python3 -m pytest tests/ -q         # 18 passed
```

已部署资源（us-west-2, stack `AgentCore-memoryloop-default`）：harness `memoryloop_extractor-*` / `memoryloop_extractor_ep-*`、memory `memoryloop_customMem-*`(SEMANTIC) / `memoryloop_episodicMem-*`(EPISODIC)。清理：`cd memoryloop && agentcore destroy`。

---

## 6. 已知坑（真机踩过，已修）
- 抽取 JSON 字符串值内**未转义英文引号**（如原文里的 "液封"）会破坏 JSON → `_extract_json_array` 用 `json_repair` 兜底 + 提示模型值内用中文「」。
- LLM 裁判对大文档一次性全量对齐会截断/摆烂 → `scorer` 按 20 条 GT 分块 + `temperature=0`。
- 会话角色（EC2 SSM Role）**无 Bedrock 直连权限** → 裁判复用 harness 承载。
- AgentCore Memory 刚写的事件用 SEMANTIC 检索读不到（异步）→ 用 `list_events` 精确即时读；`create_event` 必带 `eventTimestamp`、`list_events` 的 `sessionId` 必填。
- 装的 `agentcore` 可能是旧 `bedrock-agentcore-starter-toolkit`（同名冲突）；本项目用 `@aws/agentcore`。harness **无 `deploy --local`**，本地=`agentcore dev` 或直接 boto3 `invoke_harness`。
- custom 工具回路 token 成本高（单次可达 ~96 万），Episodic 成本更低效果更优（见 e2e 报告）。
