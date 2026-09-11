// Agent Memory Best Practices: structured data extraction.
// First-time-reader deck, aligned with the existing dark AWS visual system.
const pptxgen = require("pptxgenjs");
const p = new pptxgen();
p.defineLayout({ name: "W", width: 13.333, height: 7.5 });
p.layout = "W";
p.author = "Amazon Web Services";
p.company = "亚马逊云科技";
p.subject = "Agent memory best practices for structured data extraction";
p.title = "Agent 记忆最佳实践";
p.lang = "zh-CN";
p.theme = { headFontFace: "Amazon Ember Display", bodyFontFace: "Microsoft YaHei" };

const C = {
  bg: "161E2D", bg2: "0B1220", card: "1C2740", line: "2E3B57",
  white: "FFFFFF", body: "CFD9E4", muted: "8496A8", lblue: "A8C7E8",
  blue: "0073E5", bblue: "42B4FF", orange: "FF6A3D", green: "00E500",
  good: "12331F", warm: "2A2418", cyan: "0C3440", bad: "35181C",
};
const FH = "Amazon Ember Display", FB = "Microsoft YaHei", FM = "Amazon Ember Mono";
const BAR = "assets/leftbar.png";
const LEFT = 0.62, MW = 12.1;

function rect(s, x, y, w, h, fill = C.card, line = C.line) {
  s.addShape(p.ShapeType.roundRect, {
    x, y, w, h, rectRadius: 0.08,
    fill: { color: fill }, line: { color: line, width: 0.8 },
  });
}
function base(s, kicker, n) {
  s.background = { color: C.bg };
  s.addImage({ path: BAR, x: 0, y: 0, w: 0.16, h: 7.5 });
  s.addText(kicker, {
    x: 7.0, y: 0.4, w: 5.7, h: 0.3, fontFace: FH, fontSize: 12,
    bold: true, color: C.bblue, charSpacing: 3, align: "right", margin: 0,
  });
  s.addText("亚马逊云科技", {
    x: LEFT, y: 7.08, w: 3, h: 0.25, fontFace: FH, fontSize: 11,
    bold: true, color: C.lblue, margin: 0,
  });
  s.addText(String(n), {
    x: 12.5, y: 7.05, w: 0.45, h: 0.25, fontFace: FH, fontSize: 10.5,
    color: C.muted, align: "right", margin: 0,
  });
}
function title(s, text, lead) {
  s.addText(text, {
    x: LEFT, y: 0.38, w: 11.5, h: 0.62, fontFace: FH, fontSize: 27,
    bold: true, color: C.white, margin: 0,
  });
  if (lead) s.addText(lead, {
    x: LEFT, y: 1.1, w: MW, h: 0.58, fontFace: FB, fontSize: 14,
    color: C.body, margin: 0,
  });
}
function box(s, x, y, w, h, label, head, body, opts = {}) {
  rect(s, x, y, w, h, opts.fill || C.card, opts.line || C.line);
  let yy = y + 0.15;
  if (label) {
    s.addText(label, {
      x: x + 0.22, y: yy, w: w - 0.44, h: 0.28, fontFace: FH,
      fontSize: 11.5, bold: true, color: opts.labelColor || C.bblue, margin: 0,
    });
    yy += 0.38;
  }
  if (head) {
    s.addText(head, {
      x: x + 0.22, y: yy, w: w - 0.44, h: 0.42, fontFace: FB,
      fontSize: opts.headSize || 17, bold: true, color: C.white, margin: 0,
    });
    yy += 0.5;
  }
  if (body) s.addText(body, {
    x: x + 0.22, y: yy, w: w - 0.44, h: y + h - yy - 0.14,
    fontFace: FB, fontSize: opts.fontSize || 13, color: C.body,
    margin: 0, valign: "top",
  });
}
function codebox(s, x, y, w, h, label, text, color = C.bblue, fs = 11) {
  rect(s, x, y, w, h, C.card);
  s.addText(label, {
    x: x + 0.2, y: y + 0.14, w: w - 0.4, h: 0.28, fontFace: FH,
    fontSize: 11.5, bold: true, color, margin: 0,
  });
  rect(s, x + 0.2, y + 0.5, w - 0.4, h - 0.67, C.bg2);
  s.addText(text, {
    x: x + 0.32, y: y + 0.58, w: w - 0.64, h: h - 0.82,
    fontFace: FM, fontSize: fs, color: C.body, margin: 0, valign: "top",
  });
}
function arrow(s, x, y, color = C.bblue) {
  s.addText("→", {
    x, y, w: 0.42, h: 0.6, fontFace: FH, fontSize: 20, bold: true,
    color, align: "center", valign: "middle", margin: 0,
  });
}
function stat(s, x, y, w, value, label, color) {
  rect(s, x, y, w, 1.35, C.bg2, color);
  s.addText(value, {
    x: x + 0.1, y: y + 0.16, w: w - 0.2, h: 0.64, fontFace: FH,
    fontSize: 38, bold: true, color, align: "center", margin: 0,
  });
  s.addText(label, {
    x: x + 0.1, y: y + 0.88, w: w - 0.2, h: 0.28, fontFace: FB,
    fontSize: 12.5, color: C.body, align: "center", margin: 0,
  });
}
function callout(s, text, y, color = C.bblue) {
  rect(s, LEFT, y, MW, 0.85, C.bg2, color);
  s.addText(text, {
    x: LEFT + 0.28, y, w: MW - 0.56, h: 0.85, fontFace: FH,
    fontSize: 16.5, bold: true, color, align: "center", valign: "middle", margin: 0,
  });
}

let s;

// 1. Cover
s = p.addSlide();
s.background = { color: C.bg };
s.addImage({ path: BAR, x: 0, y: 0, w: 0.16, h: 7.5 });
s.addText("AGENTCORE MEMORY · STRUCTURED EXTRACTION", {
  x: 0.75, y: 1.2, w: 11, h: 0.38, fontFace: FH, fontSize: 14,
  bold: true, color: C.bblue, charSpacing: 3, margin: 0,
});
s.addText("Agent 记忆最佳实践", {
  x: 0.72, y: 1.75, w: 11.7, h: 0.85, fontFace: FH, fontSize: 46,
  bold: true, color: C.white, margin: 0,
});
s.addText("结构化数据抽取场景", {
  x: 0.75, y: 2.72, w: 11.4, h: 0.62, fontFace: FH, fontSize: 28,
  bold: true, color: C.bblue, margin: 0,
});
s.addText("怎样让 Agent 从一次抽取中学习，并在下一份文档中抽得更完整？", {
  x: 0.75, y: 3.75, w: 11.3, h: 0.5, fontFace: FB, fontSize: 18,
  color: C.body, margin: 0,
});
rect(s, 0.75, 4.52, 11.1, 1.15, C.card);
s.addText("核心：把 Review 中发现的遗漏模式与处理策略，转化为可复用的 Memory。", {
  x: 1.0, y: 4.52, w: 10.6, h: 1.15, fontFace: FH, fontSize: 20,
  bold: true, color: C.white, align: "center", valign: "middle", margin: 0,
});
s.addText("基于真实工业文档抽取实验 · AgentCore Harness + EPISODIC Memory", {
  x: 0.75, y: 6.08, w: 11.4, h: 0.35, fontFace: FB, fontSize: 12,
  color: C.muted, margin: 0,
});
s.addText("亚马逊云科技", {
  x: 0.75, y: 7.02, w: 3, h: 0.28, fontFace: FH, fontSize: 12,
  bold: true, color: C.lblue, margin: 0,
});

// 2. Challenge
s = p.addSlide(); base(s, "THE CHALLENGE", 2);
title(s, "结构化抽取真正难在哪里", "难点不是生成合法 JSON，而是完整识别散落在不同载体中的“应该抽取的信息”。");
codebox(s, LEFT, 1.9, 5.85, 3.65, "真实输入：正文 + 表格", [
  "技术要求:",
  "1. 所有尺寸单位为毫米",
  "2. 未注公差按 GB/T 1804-m 级",
  "3. 装配后转子应能灵活转动",
  "",
  "| 序号 | 名称 | 数量 |",
  "| 1 | 机座 | 1 |",
  "| 2 | 前端盖 | 1 |",
].join("\n"), C.bblue, 11.5);
box(s, LEFT + 6.15, 1.9, 5.95, 3.65, "常见漏项", "模型通常先抓住数值参数",
  "· 正文参数容易被识别\n· 整张 BOM 可能被当成背景\n· 附注与备注容易跳过\n· 定性、流程、待确认要求不一定被视为指标\n· 图片/OCR 内容存在不完整与冲突", { fill: C.bad, labelColor: C.orange, fontSize: 14 });
callout(s, "真正的问题：Agent 如何知道自己漏了什么？", 5.82, C.orange);

// 3. Memory role
s = p.addSlide(); base(s, "MEMORY ROLE", 3);
title(s, "Memory 应该在抽取回路中做什么", "不是保存上一次答案，而是保存下一次任务可复用的抽取策略。");
const y3 = 2.25, w3 = 2.05;
box(s, LEFT, y3, w3, 1.25, "①", "抽取草稿", "当前文档", { fill: C.card });
arrow(s, LEFT + 2.08, y3 + 0.32);
box(s, LEFT + 2.5, y3, w3, 1.25, "②", "Review", "漏了什么？", { fill: C.cyan });
arrow(s, LEFT + 4.58, y3 + 0.32);
box(s, LEFT + 5.0, y3, w3, 1.25, "③", "可复用经验", "形成策略", { fill: C.warm, labelColor: C.orange });
arrow(s, LEFT + 7.08, y3 + 0.32);
box(s, LEFT + 7.5, y3, w3, 1.25, "④", "Memory", "跨 session", { fill: C.good, labelColor: C.green });
arrow(s, LEFT + 9.58, y3 + 0.32);
box(s, LEFT + 10.0, y3, 2.1, 1.25, "⑤", "下一份文档", "复用经验", { fill: C.card });
box(s, LEFT, 4.1, 3.75, 1.55, "容易漏什么", "", "表格、附注、流程要求、图片限制", { labelColor: C.orange });
box(s, LEFT + 4.17, 4.1, 3.75, 1.55, "应该检查什么", "", "覆盖、遗漏、格式、粒度、冲突", { labelColor: C.bblue });
box(s, LEFT + 8.34, 4.1, 3.76, 1.55, "下次怎么做", "", "先扫章节与表格，再按 next_actions 修订", { labelColor: C.green });
callout(s, "Memory 的价值：复用 Review 得到的方法，而不是复读历史结果。", 5.98);

// 4. Learning signals
s = p.addSlide(); base(s, "LEARNING SIGNALS", 4);
title(s, "三种 Memory 学习信号", "同样叫“反思”，输入信息不同，能学到的东西完全不同。");
box(s, LEFT, 1.95, 3.75, 3.7, "方式 1", "抽象自省", "Review 输入：只有模型输出\n\n能学到：\n· 格式规则\n· 通用拆分方式\n· 字段完整性\n\n盲点：不知道整段或整表被漏掉", { fill: C.bad, labelColor: C.orange, fontSize: 13.5 });
box(s, LEFT + 4.17, 1.95, 3.75, 3.7, "方式 2", "结构化 Self-review", "Review 输入：原文 + 内部草稿\n\n能学到：\n· 漏段、漏表\n· 重复与冲突\n· 格式和粒度\n· 图片/OCR 限制", { fill: C.cyan, labelColor: C.bblue, fontSize: 13.5 });
box(s, LEFT + 8.34, 1.95, 3.76, 3.7, "方式 3", "任务目标 Review", "Review 输入：原文 + 输出 + 规范/Reviewer\n\n能学到：\n· 什么属于抽取目标\n· 什么粒度算一条\n· 业务口径与错误标准", { fill: C.good, labelColor: C.green, fontSize: 13.5 });
callout(s, "Memory 是否有效，取决于 Review 的信息来源和结构。", 5.95);

// 5. Abstract reflection prompt
s = p.addSlide(); base(s, "FIRST ATTEMPT", 5);
title(s, "尝试一：只看输出的抽象自省", "最初的做法，是让模型从已经生成的抽取结果中总结通用规则。");
codebox(s, LEFT, 1.9, 5.9, 3.55, "真实反思 Prompt", [
  "你是「抽取经验提炼器」。",
  "给你一次抽取结果，总结可复用于",
  "同类文档的抽取规则：",
  "",
  "· 每条必须可操作",
  "· 只讲规则，不讲具体数值",
  "· 不超过 10 条",
].join("\n"), C.bblue, 12);
codebox(s, LEFT + 6.2, 1.9, 5.9, 3.55, "真实 Consolidation Prompt", [
  "把「现有规则集 + 本轮新规则」",
  "合并成一份规范规则集：",
  "",
  "· 去重",
  "· 不超过 15 条",
  "· 每条必须可操作",
  "· 只输出最终规则集",
].join("\n"), C.orange, 12);
callout(s, "问题埋在输入里：模型只能总结“已经抽出来的内容”。", 5.78, C.orange);

// 6. Abstract memory
s = p.addSlide(); base(s, "WHAT IT LEARNED", 6);
title(s, "抽象自省实际记住了什么", "4 轮运行后，consolidation 形成一份包含 15 条规则的 canonical Memory。");
box(s, LEFT, 1.72, 3.86, 4.08, "规则 1–5", "", [
  "1. 设备主体识别：标题/首段的“容量+介质+设备类型”作为主体，全文统一。",
  "2. 整体性能归属：介质、容积、压力、温度、绝热等归“储罐整体”。",
  "3. 运输/交货独立：封存压力、气体、露点、封堵状态独立成条。",
  "4. 子系统/附件独立：增压器、安全装置、仪表、阀门、管口单独成部件。",
  "5. 多部件拆分：同句多个部件按部件拆分，保留完整原文。",
].join("\n\n"), { fill: C.card, labelColor: C.bblue, fontSize: 10.5 });
box(s, LEFT + 4.12, 1.72, 3.86, 4.08, "规则 6–10", "", [
  "6. 复合指标拆分：通径、压力、规格、数量、备注按指标分别成条。",
  "7. 指标名称规范：同义属性统一；检测拆成标准、比例、技术等级、合格级别。",
  "8. 管口/接口规格：保留原格式、不换算；DN 与压力等级分别抽取。",
  "9. 阀门/仪表清单：规格与数量分条，附加说明另生成备注。",
  "10. 材料分层：内罐、外罐、管道、阀门材料分别成条。",
].join("\n\n"), { fill: C.warm, labelColor: C.orange, fontSize: 10.5 });
box(s, LEFT + 8.24, 1.72, 3.86, 4.08, "规则 11–15", "", [
  "11. 检测标准完整：标准编号、比例、技术等级、合格级别齐全；RT/PT 分条。",
  "12. 工艺/结构要求：防涡、液封、双阀、清洁度、焊接结构独立抽取。",
  "13. 限值符号保留：≤、≥、不少于等原样保留，范围上下限完整。",
  "14. 功能/描述要求：无数值文本完整保留，不替换为空值或泛化词。",
  "15. 原文溯源：保留编号和标点；OCR 错误可修特征，但原文不改。",
].join("\n\n"), { fill: C.good, labelColor: C.green, fontSize: 10.5 });
rect(s, LEFT, 6.02, MW, 0.72, C.bg2, C.orange);
s.addText("4 轮抽取：90 → 93 → 95 → 102 条　|　15 条规则　|　53 个唯一原文　|　1.92 条/原文", {
  x: LEFT + 0.25, y: 6.02, w: MW - 0.5, h: 0.72, fontFace: FH,
  fontSize: 15.5, bold: true, color: C.orange, align: "center",
  valign: "middle", margin: 0,
});

// 7. Error taxonomy
s = p.addSlide(); base(s, "ROOT CAUSE", 7);
title(s, "抽取错误其实有两类", "先区分错误类型，才能判断应该由 Self-review 解决，还是需要规范/Reviewer。");
box(s, LEFT, 1.95, 5.85, 3.8, "类型 A", "源覆盖问题", "定义：原文中出现了 X，但输出中没有 X。\n\n例子：\n· 整张 BOM 没抽\n· 漏掉某个章节或附注\n· 重复记录\n· 字段为空或格式错误\n\n可通过：原文 + 草稿的结构化自审发现", { fill: C.cyan, labelColor: C.bblue, fontSize: 14 });
box(s, LEFT + 6.25, 1.95, 5.85, 3.8, "类型 B", "任务边界问题", "定义：模型不知道 X 也属于抽取目标。\n\n例子：\n· 流程与见证要求\n· 报告与交付文件\n· 待确认事项\n· 什么粒度算一条\n\n需要：任务规范、Reviewer 或人工反馈", { fill: C.warm, labelColor: C.orange, fontSize: 14 });
callout(s, "Self-review 能发现“漏了什么”；规范/Reviewer 决定“什么应该抽”。", 6.02);

// 8. Structured self review prompts
s = p.addSlide(); base(s, "NEW DESIGN", 8);
title(s, "Harness Agent：两阶段结构化 Self-review", "两个阶段均由 Harness Agent 执行；产物写入同一 runtime session，等待 Memory System 后台提炼。");
codebox(s, LEFT, 1.82, 5.95, 4.15, "HARNESS AGENT · 阶段一 Prompt", [
  "先在内部形成完整抽取草稿，再审查草稿；",
  "不要输出草稿。",
  "",
  "{",
  '  "self_review": {',
  '    "coverage": {...},',
  '    "omissions": {...},',
  '    "format": {...},',
  '    "granularity": {...},',
  '    "next_actions": [...]',
  "  }",
  "}",
].join("\n"), C.bblue, 10.8);
codebox(s, LEFT + 6.2, 1.82, 5.9, 4.15, "HARNESS AGENT · 阶段二 Prompt", [
  "读取原始文档和 self_review。",
  "",
  "根据 next_actions 重新完成抽取，",
  "并逐项复核：",
  "· coverage",
  "· omissions",
  "· format",
  "· granularity",
  "",
  "只输出最终五字段 JSON。",
].join("\n"), C.green, 11.2);
callout(s, "执行主体：Harness Agent　|　产物：self_review + 最终 JSON　|　载体：同一 session events", 6.18, C.green);

// 9. AgentCore pipeline
s = p.addSlide(); base(s, "MANAGED MEMORY", 9);
title(s, "Memory System：EPISODIC 提炼轨迹", "AgentCore Memory 资源使用内置 EPISODIC strategy；后台异步处理 Harness Agent 产生的完整 session events。");
const y9 = 2.0;
box(s, LEFT, y9, 2.5, 1.35, "HARNESS AGENT", "Session Events", "原文 + self_review + 最终 JSON", { fill: C.card, fontSize: 12.5 });
arrow(s, LEFT + 2.55, y9 + 0.38);
box(s, LEFT + 3.0, y9, 2.5, 1.35, "MEMORY · EPISODIC", "Episode Extraction", "逐 turn 分析行为与结果", { fill: C.cyan, fontSize: 12.5 });
arrow(s, LEFT + 5.55, y9 + 0.38);
box(s, LEFT + 6.0, y9, 2.5, 1.35, "MEMORY · EPISODIC", "Consolidation", "形成 session-level episode", { fill: C.warm, labelColor: C.orange, fontSize: 12.5 });
arrow(s, LEFT + 8.55, y9 + 0.38);
box(s, LEFT + 9.0, y9, 3.1, 1.35, "MEMORY · EPISODIC", "Reflection", "形成 actor-level 可复用策略", { fill: C.good, labelColor: C.green, fontSize: 12.5 });
stat(s, LEFT + 1.1, 4.15, 3.4, "1", "session-level episode", C.orange);
stat(s, LEFT + 4.85, 4.15, 3.4, "2", "actor-level reflections", C.bblue);
stat(s, LEFT + 8.6, 4.15, 3.4, "新 session", "Harness 自动检索并注入", C.green);
callout(s, "Episode namespace: /episodes/{actorId}/{sessionId}　|　Reflection namespace: /episodes/{actorId}", 5.95);

// 10. Actual memory
s = p.addSlide(); base(s, "REAL MEMORY", 10);
title(s, "AgentCore Memory System 实际生成的 Records", "以下内容均由内置 EPISODIC strategy 异步生成，不是 Harness Agent 手工写入的规则。");
box(s, LEFT, 1.82, 4.0, 4.3, "MEMORY SYSTEM · EPISODE RECORD", "两阶段流程设计有效",
  "先输出 self_review 再执行修订，避免一次性处理复杂文档时遗漏问题。\n\n对于 OCR 错误、章节跳号、重复表格和图片内容，分阶段结构化抽取是推荐模式。\n\n不可完整提取的内容应显式说明限制。", { fill: C.cyan, labelColor: C.bblue, fontSize: 13 });
box(s, LEFT + 4.25, 1.82, 3.85, 4.3, "MEMORY SYSTEM · ACTOR REFLECTION 1", "Two-Phase Structured Extraction",
  "Phase 1:\ncoverage / omissions / format / granularity\n\nPhase 2:\nexecute next_actions systematically\n\n保留原文用于追溯。", { fill: C.warm, labelColor: C.orange, fontSize: 12.8, headSize: 15 });
box(s, LEFT + 8.35, 1.82, 3.75, 4.3, "MEMORY SYSTEM · ACTOR REFLECTION 2", "Inline Annotation",
  "遇到 OCR 错误或表格冲突时：\n\n· 不静默丢弃\n· 保留原文\n· 标记冲突值\n· 文档级限制写入 __META__", { fill: C.good, labelColor: C.green, fontSize: 13, headSize: 15 });

// 11. Controlled target experiment
s = p.addSlide(); base(s, "CONTROLLED TEST", 11);
title(s, "Harness Agent 留出实验：目标端只改变 Memory 开关", "目标抽取由 Harness Agent 完成；Memory System 只在 enabled 组负责自动检索并注入 records。");
codebox(s, LEFT, 1.78, 5.95, 3.9, "HARNESS AGENT · 目标抽取 Prompt", [
  "根据用户文档抽取所有可识别的技术要求/参数。",
  "",
  "每条输出：",
  "设备主体 / 设备部件 / 指标名称 /",
  "指标特征 / 原文。",
  "",
  "先在内部自审覆盖、遗漏、格式和粒度，",
  "再只输出最终合法 JSON。",
].join("\n"), C.bblue, 11.3);
box(s, LEFT + 6.2, 1.78, 5.9, 3.9, "控制变量", "Harness Agent 配置相同",
  "· 同一测试文档与 system prompt\n· claude-sonnet-4-6\n· temperature=0 · maxTokens=32768\n· skills=[] · tools=[]\n· 两组均使用全新 session\n\nMemory 组：EPISODIC retrieval enabled\nNo Memory 组：Memory disabled", { fill: C.card, labelColor: C.green, fontSize: 13.3 });
callout(s, "执行主体：Harness Agent　|　实验变量：Memory System 是否检索并注入 source actor records", 5.95, C.green);

// 12. Actual outputs
s = p.addSlide(); base(s, "REAL OUTPUT", 12);
title(s, "Harness Agent 输出：Memory 注入后关注点发生变化", "两组输出都由 Harness Agent 生成；差别是左侧调用前接收了 Memory System 注入的 records。");
codebox(s, LEFT, 1.82, 5.95, 3.9, "HARNESS AGENT + MEMORY SYSTEM · BOM", JSON.stringify([
  {
    "设备部件": "机座",
    "指标名称": "零件明细（表1-序号1）",
    "指标特征": "数量：1；其他字段原文为「-」"
  },
  {
    "设备部件": "壳体组件",
    "指标名称": "组件明细（表2-序号1）",
    "指标特征": "数量：1；其他字段原文为「-」"
  }
], null, 2), C.green, 10.5);
codebox(s, LEFT + 6.2, 1.82, 5.9, 3.9, "HARNESS AGENT · MEMORY DISABLED", JSON.stringify([
  {
    "设备部件": "整机",
    "指标名称": "未注公差等级",
    "指标特征": "GB/T 1804-m级"
  },
  {
    "设备部件": "轴承",
    "指标名称": "装配数量",
    "指标特征": "2件"
  }
], null, 2), C.bblue, 10.5);
stat(s, LEFT + 1.0, 5.62, 4.5, "31 条", "Memory 首次运行", C.green);
stat(s, LEFT + 6.6, 5.62, 4.5, "11 条", "No Memory 首次运行", C.bblue);

// 13. Reconcile
s = p.addSlide(); base(s, "SYNTHESIS", 13);
title(s, "Harness Agent 的两种 Review，为何产生不同 Memory", "不是 Self-reflection 有用或没用，而是 Harness Agent 的 Review 是否有可靠检查对象。");
const head = (text) => ({ text, options: { bold: true, color: C.white, fill: C.blue, fontFace: FB, fontSize: 12.5 } });
const cell = (text, fill = C.card, color = C.body, bold = false) => ({ text, options: { color, fill, bold, fontFace: FB, fontSize: 12.2, valign: "middle" } });
s.addTable([
  [head("比较项"), head("抽象自省"), head("结构化 Self-review")],
  [cell("Review 输入", C.bg2, C.white, true), cell("只有模型输出", C.bad), cell("原文 + 内部草稿", C.good)],
  [cell("Review 结构", C.bg2, C.white, true), cell("自由总结规则", C.bad), cell("固定检查维度", C.good)],
  [cell("Memory 形成主体", C.bg2, C.white, true), cell("应用调用 LLM 合并规则", C.bad), cell("Memory System · EPISODIC", C.good)],
  [cell("主要 Memory", C.bg2, C.white, true), cell("拆分与格式规则", C.bad), cell("覆盖、遗漏、表格、冲突", C.good)],
  [cell("观察结果", C.bg2, C.white, true), cell("作用有限，可能过度拆分", C.bad, C.orange, true), cell("明显扩大 BOM 覆盖", C.good, C.green, true)],
  [cell("适合解决", C.bg2, C.white, true), cell("部分格式与粒度问题", C.bad), cell("源覆盖与一致性问题", C.good)],
  [cell("仍需外部信号", C.bg2, C.white, true), cell("任务边界", C.warm), cell("任务边界", C.warm)],
], {
  x: LEFT, y: 1.82, w: MW, h: 3.8, colW: [2.6, 4.7, 4.8],
  rowH: [0.42, 0.42, 0.42, 0.48, 0.48, 0.52, 0.42, 0.42],
  border: { pt: 0.75, color: C.line }, fontFace: FB, fontSize: 12.2,
});
callout(s, "统一结论：源文本自审能改善覆盖；任务边界仍需要规范、Reviewer 或人工反馈。", 5.95);

// 14. Best practices
s = p.addSlide(); base(s, "BEST PRACTICES", 14);
title(s, "结构化数据抽取的 Memory 最佳实践", "把 Memory 设计成可验证的学习回路，而不是无限累积的历史上下文。");
const items = [
  ["1", "Harness Agent · Review 看原文", "不要只对输出做抽象总结。"],
  ["2", "Harness Agent · 输出 Artifact", "固定 coverage / omissions / format / granularity。"],
  ["3", "Harness Agent · 产出动作", "生成明确、可执行的 next_actions。"],
  ["4", "任务设计 · 区分问题", "源覆盖可自审；任务边界需要规范或 Reviewer。"],
  ["5", "Memory 内容 · 保存方法", "描述何时适用、检查什么、避免什么，不保存答案。"],
  ["6", "Memory System · 区分 Records", "Episode 记录一次任务；Reflection 沉淀跨任务方法。"],
  ["7", "Harness 配置 · 控制召回", "限制 topK、清理噪声、避免长 episode 撑爆上下文。"],
  ["8", "Evaluation · 人工校准", "分别检查忠实性、完整性、粒度与过度抽取。"],
];
items.forEach((it, i) => {
  const col = i % 2, row = Math.floor(i / 2);
  const x = LEFT + col * 6.2, y = 1.75 + row * 1.13;
  rect(s, x, y, 5.9, 0.95, C.card);
  s.addText(it[0], {
    x: x + 0.18, y: y + 0.19, w: 0.48, h: 0.48, shape: p.ShapeType.ellipse,
    fill: { color: i === 3 || i === 6 ? C.orange : C.blue }, color: C.white,
    fontFace: FH, fontSize: 15, bold: true, align: "center", valign: "middle", margin: 0,
  });
  s.addText(it[1], {
    x: x + 0.82, y: y + 0.13, w: 2.2, h: 0.3, fontFace: FB,
    fontSize: 14.5, bold: true, color: C.white, margin: 0,
  });
  s.addText(it[2], {
    x: x + 0.82, y: y + 0.48, w: 4.8, h: 0.28, fontFace: FB,
    fontSize: 11.7, color: C.body, margin: 0,
  });
});
rect(s, LEFT + 1.2, 6.18, MW - 2.4, 0.55, C.bg2, C.bblue);
s.addText("Memory 的价值不是记住历史答案，而是复用经过 Review 得到的抽取策略。", {
  x: LEFT + 1.48, y: 6.18, w: MW - 2.96, h: 0.55,
  fontFace: FH, fontSize: 15.5, bold: true, color: C.bblue,
  align: "center", valign: "middle", margin: 0,
});

p.writeFile({ fileName: "docs/记忆能让Agent越跑越好吗-V3.pptx" })
  .then((file) => console.log("WROTE", file));
