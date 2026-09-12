// Agent Memory Best Practices: structured data extraction.
// First-time-reader deck, aligned with the existing dark AWS visual system.
const fs = require("fs");
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
function title(s, text, lead, fontSize = 27) {
  s.addText(text, {
    x: LEFT, y: 0.38, w: 11.5, h: 0.62, fontFace: FH, fontSize,
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
function sectionSlide(n, experiment, titleText, question, bridge, color) {
  const slide = p.addSlide();
  base(slide, `EXPERIMENT ${experiment}`, n);
  const titleSize = titleText.length > 31 ? 27 : titleText.length > 24 ? 30 : 34;
  slide.addText(`0${experiment}`, {
    x: LEFT, y: 1.22, w: 2.25, h: 1.35, fontFace: FH, fontSize: 72,
    bold: true, color, margin: 0, valign: "middle",
  });
  slide.addText(titleText, {
    x: LEFT + 2.55, y: 1.3, w: 9.3, h: 0.82, fontFace: FH, fontSize: titleSize,
    bold: true, color: C.white, margin: 0,
  });
  slide.addText(question, {
    x: LEFT + 2.58, y: 2.25, w: 9.0, h: 0.72, fontFace: FB, fontSize: 18,
    color: C.body, margin: 0,
  });
  rect(slide, LEFT, 3.42, MW, 1.65, C.bg2, color);
  slide.addText(bridge, {
    x: LEFT + 0.45, y: 3.42, w: MW - 0.9, h: 1.65, fontFace: FB,
    fontSize: 20, bold: true, color, align: "center", valign: "middle", margin: 0,
  });
  return slide;
}
function loadSpeakerNotes(fileName) {
  const markdown = fs.readFileSync(fileName, "utf8");
  const headers = [...markdown.matchAll(/^## Slide (\d+)｜.*$/gm)];
  const notes = headers.map((header, index) => {
    const slideNumber = Number(header[1]);
    const start = header.index + header[0].length;
    const end = index + 1 < headers.length ? headers[index + 1].index : markdown.length;
    const text = markdown.slice(start, end)
      .replace(/\*\*(.*?)\*\*/g, "$1")
      .replace(/`([^`]+)`/g, "$1")
      .replace(/^>\s?/gm, "")
      .replace(/^-\s+/gm, "• ")
      .trim();
    return { slideNumber, text };
  });

  if (notes.length !== p._slides.length) {
    throw new Error(`Speaker Notes count ${notes.length} does not match slide count ${p._slides.length}.`);
  }

  notes.forEach((note, index) => {
    if (note.slideNumber !== index + 1) {
      throw new Error(`Expected Speaker Notes for slide ${index + 1}, found slide ${note.slideNumber}.`);
    }
    p._slides[index].addNotes(note.text);
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
s.addText("怎样让 Harness Agent 从一次抽取中学习，并在下一份文档中抽得更完整？", {
  x: 0.75, y: 3.75, w: 11.3, h: 0.5, fontFace: FB, fontSize: 18,
  color: C.body, margin: 0,
});
rect(s, 0.75, 4.52, 11.1, 1.15, C.card);
s.addText("核心：Harness Agent 产出 Review 轨迹；AgentCore Memory System 把轨迹提炼为可复用 Records。", {
  x: 1.0, y: 4.52, w: 10.6, h: 1.15, fontFace: FH, fontSize: 20,
  bold: true, color: C.white, align: "center", valign: "middle", margin: 0,
});
s.addText("基于真实工业文档实验 · Application 编排 + Harness Agent 抽取 + AgentCore Memory EPISODIC", {
  x: 0.75, y: 6.08, w: 11.4, h: 0.35, fontFace: FB, fontSize: 12,
  color: C.muted, margin: 0,
});
s.addText("亚马逊云科技", {
  x: 0.75, y: 7.02, w: 3, h: 0.28, fontFace: FH, fontSize: 12,
  bold: true, color: C.lblue, margin: 0,
});

// 2. Challenge
s = p.addSlide(); base(s, "THE CHALLENGE", 2);
title(s, "Harness Agent 的结构化抽取难点", "Harness Agent 生成合法 JSON 并不难；难点是完整识别散落在不同载体中的目标信息。");
codebox(s, LEFT, 1.9, 5.85, 3.65, "APPLICATION 提供的真实输入", [
  "技术要求:",
  "1. 所有尺寸单位为毫米",
  "2. 未注公差按 GB/T 1804-m 级",
  "3. 装配后转子应能灵活转动",
  "",
  "| 序号 | 名称 | 数量 |",
  "| 1 | 机座 | 1 |",
  "| 2 | 前端盖 | 1 |",
].join("\n"), C.bblue, 11.5);
box(s, LEFT + 6.15, 1.9, 5.95, 3.65, "HARNESS AGENT · 常见漏项", "Harness Agent 通常先抓住数值参数",
  "· 正文参数容易被识别\n· 整张 BOM 可能被当成背景\n· 附注与备注容易跳过\n· 定性、流程、待确认要求不一定被视为指标\n· 图片/OCR 内容存在不完整与冲突", { fill: C.bad, labelColor: C.orange, fontSize: 14 });
callout(s, "真正的问题：Harness Agent 如何发现自己的源覆盖遗漏？", 5.82, C.orange);

// 3. Memory role
s = p.addSlide(); base(s, "MEMORY ROLE", 3);
title(s, "端到端抽取回路：每一步由谁执行", "Application 负责调用与实验控制；Harness Agent 负责抽取与自审；Memory System 负责 EPISODIC 处理与跨 session 召回。");
const y3 = 1.92, w3 = 2.05, gap3 = 0.36;
const x31 = LEFT, x32 = x31 + w3 + gap3, x33 = x32 + w3 + gap3;
const x34 = x33 + w3 + gap3, x35 = x34 + w3 + gap3;
box(s, x31, y3, w3, 1.75, "① APPLICATION", "启动源任务", "向 Harness Agent 提交源文档与抽取 Prompt", { fill: C.card, fontSize: 11.2, headSize: 15 });
arrow(s, x31 + w3, y3 + 0.56);
box(s, x32, y3, w3, 1.75, "② HARNESS AGENT", "抽取 + Self-review", "产出 self_review、next_actions 与最终 JSON", { fill: C.cyan, fontSize: 11.2, headSize: 15 });
arrow(s, x32 + w3, y3 + 0.56);
box(s, x33, y3, w3, 1.75, "③ MEMORY SYSTEM", "EPISODIC 处理", "Event Storage → Extraction → Consolidation → Reflection", { fill: C.warm, labelColor: C.orange, fontSize: 10.8, headSize: 15 });
arrow(s, x33 + w3, y3 + 0.56);
box(s, x34, y3, w3, 1.75, "④ AGENTCORE HARNESS", "调用 Retrieval + 注入", "调用 Memory System 检索 actor records，并注入新 session", { fill: C.good, labelColor: C.green, fontSize: 10.8, headSize: 14.5 });
arrow(s, x34 + w3, y3 + 0.56);
box(s, x35, y3, w3, 1.75, "⑤ HARNESS AGENT", "执行目标抽取", "读取新文档与注入的 Records，输出最终 JSON", { fill: C.card, fontSize: 11.2, headSize: 15 });
box(s, LEFT, 4.15, 3.75, 1.42, "源任务产物 · HARNESS AGENT", "", "self_review + next_actions + 最终 JSON", { labelColor: C.bblue, fontSize: 13 });
box(s, LEFT + 4.17, 4.15, 3.75, 1.42, "托管记录 · MEMORY SYSTEM", "", "1 session-level episode + actor-level reflections", { labelColor: C.orange, fontSize: 13 });
box(s, LEFT + 8.34, 4.15, 3.76, 1.42, "目标任务产物 · HARNESS AGENT", "", "Memory enabled / disabled 两组最终 JSON", { labelColor: C.green, fontSize: 13 });
callout(s, "端到端链路：Application 调用 → Harness Agent 产轨迹 → Memory System 提炼/检索 → AgentCore Harness 注入", 5.88);

// 4. Experiment map
s = p.addSlide(); base(s, "EXPERIMENT MAP", 4);
title(s, "两项实验：先生成 Records，再验证跨 session 效果", "实验一构造高质量源任务轨迹并生成托管 EPISODIC Records；实验二只切换 Retrieval 链路验证目标任务差异。");
box(s, LEFT, 1.92, 5.85, 3.85, "实验一 · EPISODIC RECORDS 生成", "Harness Agent 产轨迹；Memory System 提炼",
  "Application：顺序调用两阶段\nHarness Agent：原文 → self_review → 最终 JSON\nMemory System：Event Storage → Extraction → Consolidation → Reflection\n\n产物：1 session-level episode + 2 actor-level reflections", { fill: C.cyan, labelColor: C.bblue, fontSize: 12.5, headSize: 17 });
box(s, LEFT + 6.25, 1.92, 5.85, 3.85, "实验二 · 留出文档开关对照", "Retrieval / Injection 是唯一变量",
  "Application：创建两组 fresh sessions\nMemory System：仅 enabled 组 Retrieval\nAgentCore Harness：仅 enabled 组注入 Records\nHarness Agent：两组使用相同 Prompt 抽取\nReviewer：人工核对\n\n结果：31 vs 11；新增内容主要来自两张 BOM", { fill: C.good, labelColor: C.green, fontSize: 12.3, headSize: 17 });
callout(s, "证据链：源任务 Review 轨迹 → 托管 EPISODIC Records → 留出文档 Retrieval 开关对照", 6.02);

// 5. Experiment 1 divider
sectionSlide(
  5,
  1,
  "Harness Agent 产出轨迹；Memory System 生成 Records",
  "Application 顺序调用 Harness Agent 两个阶段；Harness Agent 对照原文自审并修订。",
  "实验边界：AgentCore Memory System 使用内置 EPISODIC 处理源 session，生成 1 条 episode 和 2 条 actor reflections。",
  C.bblue,
);

// 6. Structured self review prompts
s = p.addSlide(); base(s, "EXPERIMENT 1 · HARNESS AGENT", 6);
title(s, "Harness Agent：两阶段 Self-review", "Application 连续调用同一 Harness Agent；Harness Agent 执行自审与修订；Memory System 保存同一 session 的 events。");
codebox(s, LEFT, 1.82, 5.95, 4.15, "APPLICATION 调用 → HARNESS AGENT 阶段一", [
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
codebox(s, LEFT + 6.2, 1.82, 5.9, 4.15, "APPLICATION 调用 → HARNESS AGENT 阶段二", [
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
callout(s, "Application：顺序调用　|　Harness Agent：self_review + 最终 JSON　|　Memory System：保存 session events", 6.18, C.green);

// 7. AgentCore pipeline
s = p.addSlide(); base(s, "EXPERIMENT 1 · MEMORY SYSTEM", 7);
title(s, "Memory System：EPISODIC 处理链", "Memory System 异步处理 Harness Agent 的 session events；新 session 中，AgentCore Harness 调用 Retrieval 并注入 Records。");
const y9 = 2.0;
box(s, LEFT, y9, 2.5, 1.55, "MEMORY · EVENT STORAGE", "保存 Session Events", "Harness Agent 产物：原文 + self_review + 最终 JSON", { fill: C.card, fontSize: 10.5, headSize: 14.0 });
arrow(s, LEFT + 2.55, y9 + 0.48);
box(s, LEFT + 3.0, y9, 2.5, 1.55, "MEMORY · EXTRACTION", "分析每个 Turn", "Memory System 识别行为、结果与任务信号", { fill: C.cyan, fontSize: 10.5, headSize: 14.0 });
arrow(s, LEFT + 5.55, y9 + 0.48);
box(s, LEFT + 6.0, y9, 2.5, 1.55, "MEMORY · CONSOLIDATION", "生成 Episode", "Memory System 形成 session-level episode", { fill: C.warm, labelColor: C.orange, fontSize: 10.5, headSize: 14.0 });
arrow(s, LEFT + 8.55, y9 + 0.48);
box(s, LEFT + 9.0, y9, 3.1, 1.55, "MEMORY · REFLECTION", "生成跨任务方法", "Memory System 形成 actor-level reflections", { fill: C.good, labelColor: C.green, fontSize: 10.5, headSize: 14.0 });
stat(s, LEFT + 1.1, 4.15, 3.4, "1", "Memory System · session-level episode", C.orange);
stat(s, LEFT + 4.85, 4.15, 3.4, "2", "Memory System · actor-level reflections", C.bblue);
stat(s, LEFT + 8.6, 4.15, 3.4, "新 session", "AgentCore Harness · Retrieval 调用 + 注入", C.green);
callout(s, "Memory System：检索 actor Records　|　AgentCore Harness：注入上下文　|　接收方：新 Harness Agent", 5.95);

// 8. Actual memory
s = p.addSlide(); base(s, "EXPERIMENT 1 · REAL MEMORY", 8);
title(s, "Memory System · EPISODIC 实际生成的 Records", "Memory System 在 Consolidation 阶段生成 session-level episode，在 Reflection 阶段生成 actor-level reflections。");
box(s, LEFT, 1.82, 4.0, 4.3, "MEMORY SYSTEM · EPISODE RECORD", "两阶段流程设计有效",
  "先输出 self_review 再执行修订，避免一次性处理复杂文档时遗漏问题。\n\n对于 OCR 错误、章节跳号、重复表格和图片内容，分阶段结构化抽取是推荐模式。\n\n不可完整提取的内容应显式说明限制。", { fill: C.cyan, labelColor: C.bblue, fontSize: 13 });
box(s, LEFT + 4.25, 1.82, 3.85, 4.3, "MEMORY SYSTEM · ACTOR REFLECTION 1", "Two-Phase Structured Extraction",
  "Phase 1:\ncoverage / omissions / format / granularity\n\nPhase 2:\nexecute next_actions systematically\n\n保留原文用于追溯。", { fill: C.warm, labelColor: C.orange, fontSize: 12.8, headSize: 15 });
box(s, LEFT + 8.35, 1.82, 3.75, 4.3, "MEMORY SYSTEM · ACTOR REFLECTION 2", "Inline Annotation",
  "遇到 OCR 错误或表格冲突时：\n\n· 不静默丢弃\n· 保留原文\n· 标记冲突值\n· 文档级限制写入 __META__", { fill: C.good, labelColor: C.green, fontSize: 13, headSize: 15 });

// 9. Experiment 2 divider
sectionSlide(
  9,
  2,
  "Application 启动留出实验：只改变 Retrieval 开关",
  "Application 为同一电机图纸创建两组 fresh sessions；Harness Agent 使用相同配置执行抽取。",
  "实验边界：enabled 组由 Memory System 执行 Retrieval、AgentCore Harness 注入 Records；disabled 组不接收 Records。",
  C.green,
);

// 10. Controlled target experiment
s = p.addSlide(); base(s, "EXPERIMENT 2 · CONTROL", 10);
title(s, "Application 控制变量；Harness Agent 执行目标抽取", "Application 固定两组配置；enabled 组由 Memory System 检索 Records、AgentCore Harness 注入上下文。", 25);
codebox(s, LEFT, 1.78, 5.95, 3.9, "APPLICATION 提供 → HARNESS AGENT 执行", [
  "根据用户文档抽取所有可识别的技术要求/参数。",
  "",
  "每条输出：",
  "设备主体 / 设备部件 / 指标名称 /",
  "指标特征 / 原文。",
  "",
  "先在内部自审覆盖、遗漏、格式和粒度，",
  "再只输出最终合法 JSON。",
].join("\n"), C.bblue, 11.3);
box(s, LEFT + 6.2, 1.78, 5.9, 3.9, "APPLICATION · 实验控制", "Application 固定 Harness Agent 配置",
  "· 同一测试文档与 system prompt\n· claude-sonnet-4-6\n· temperature=0 · maxTokens=32768\n· skills=[] · tools=[]\n· 两组均使用全新 session\n\nEnabled：Memory Retrieval + Harness Injection\nDisabled：不检索、不注入历史 Records", { fill: C.card, labelColor: C.green, fontSize: 13.0 });
callout(s, "Application 控制变量　|　Memory System 检索　|　AgentCore Harness 注入　|　Harness Agent 抽取", 5.95, C.green);

// 11. Key result
s = p.addSlide(); base(s, "EXPERIMENT 2 · KEY RESULT", 11);
title(s, "Harness Agent 结果：31 vs 11", "Enabled 组由 Memory System 检索 EPISODIC Records、AgentCore Harness 注入；两组 Harness Agent 使用相同 Prompt。");
stat(s, LEFT, 1.78, 4.85, "31 条", "Memory enabled", C.green);
s.addText("VS", {
  x: LEFT + 5.05, y: 2.08, w: 1.35, h: 0.58, fontFace: FH,
  fontSize: 24, bold: true, color: C.white, align: "center", margin: 0,
});
stat(s, LEFT + 6.58, 1.78, 4.85, "11 条", "Memory disabled", C.bblue);
rect(s, LEFT, 3.38, MW, 1.08, C.good, C.green);
s.addText("AgentCore Harness 注入 Memory Records 后，Harness Agent 多输出约 20 条；新增内容主要来自两张 BOM。", {
  x: LEFT + 0.35, y: 3.38, w: MW - 0.7, h: 1.08, fontFace: FH,
  fontSize: 19, bold: true, color: C.green, align: "center", valign: "middle", margin: 0,
});
box(s, LEFT, 4.72, 5.86, 1.35, "HARNESS AGENT · ENABLED 输出", "零部件表", "机座 · 前端盖 · 转子 · 轴承", { fill: C.card, labelColor: C.green, fontSize: 13.2, headSize: 15 });
box(s, LEFT + 6.24, 4.72, 5.86, 1.35, "HARNESS AGENT · ENABLED 输出", "组件表", "壳体组件 · 法兰盘组件 · 散热器组件", { fill: C.card, labelColor: C.green, fontSize: 13.2, headSize: 15 });
callout(s, "Reviewer 人工核对：新增条目基本有原文依据；该实验说明覆盖关注点扩大，不等于质量提升 3 倍。", 6.15, C.orange);

// 12. Reconcile
s = p.addSlide(); base(s, "EXPERIMENT SYNTHESIS", 12);
title(s, "两项实验构成一条完整证据链", "实验一证明托管 EPISODIC Records 能从高质量源任务轨迹中形成；实验二验证这些 Records 对新任务抽取行为的影响。");
const head = (text) => ({ text, options: { bold: true, color: C.white, fill: C.blue, fontFace: FB, fontSize: 12.2 } });
const cell = (text, fill = C.card, color = C.body, bold = false) => ({ text, options: { color, fill, bold, fontFace: FB, fontSize: 11.3, valign: "middle" } });
s.addTable([
  [head("对比项"), head("实验一 · EPISODIC Records 生成"), head("实验二 · 留出文档验证")],
  [cell("核心问题", C.bg2, C.white, true), cell("Memory System 能否从 Harness Agent 轨迹生成 Records？", C.cyan), cell("AgentCore Harness 注入后，Harness Agent 输出是否变化？", C.good)],
  [cell("执行主体", C.bg2, C.white, true), cell("Application + Harness Agent + Memory System", C.cyan), cell("Application + Memory System + AgentCore Harness + Harness Agent + Reviewer", C.good)],
  [cell("输入 / 变量", C.bg2, C.white, true), cell("13 页原文 + self_review + 最终 JSON", C.cyan), cell("同一目标配置；只切换 Retrieval + Injection", C.good)],
  [cell("实际产物", C.bg2, C.white, true), cell("Memory System：1 episode + 2 actor reflections", C.cyan), cell("Harness Agent：31 条 vs 11 条", C.good, C.green, true)],
  [cell("关键观察", C.bg2, C.white, true), cell("Records 包含 coverage / omissions / conflict 处理方法", C.cyan), cell("Enabled Harness Agent 系统展开两张 BOM", C.good, C.green, true)],
  [cell("结论边界", C.bg2, C.white, true), cell("证明 EPISODIC Records 能生成并跨 session 检索", C.cyan), cell("证明覆盖关注点变化；最终质量仍由 Reviewer 判断", C.good)],
], {
  x: LEFT, y: 1.82, w: MW, h: 3.75, colW: [2.2, 4.95, 4.95],
  rowH: [0.46, 0.5, 0.52, 0.5, 0.52, 0.55, 0.55],
  border: { pt: 0.75, color: C.line }, fontFace: FB, fontSize: 11.3,
});
callout(s, "证据链：Harness Agent 原文自审 → Memory System 生成/检索 Records → AgentCore Harness 注入 → 新 Harness Agent 扩大 BOM 覆盖", 5.92);

// 13. Best practices
s = p.addSlide(); base(s, "BEST PRACTICES", 13);
title(s, "各组件在 Memory 学习回路中的最佳实践", "每条实践都明确责任主体，避免把 Application 编排、Harness Agent 推理和 Memory System 托管能力混为一谈。");
const items = [
  ["1", "Harness Agent · Review 看原文", "对照原文检查覆盖、遗漏和冲突。"],
  ["2", "Harness Agent · 输出 Artifact", "固定 coverage / omissions / format / granularity。"],
  ["3", "Application · 编排两阶段", "顺序调用 Review 与 Revision，并保持同一 session。"],
  ["4", "Reviewer / Human · 定义边界", "Harness Agent 自审源覆盖；Reviewer 定义业务边界。"],
  ["5", "Memory 设计者 · 保存方法", "要求 Records 描述何时适用、检查什么、避免什么。"],
  ["6", "Memory System · 区分 Records", "EPISODIC：Episode 记一次任务；Reflection 沉淀跨任务方法。"],
  ["7", "AgentCore Harness · 控制注入", "调用 Retrieval、设置 topK，并记录向 Harness Agent 注入的 Records。"],
  ["8", "Reviewer / Human · 校准结果", "分别检查忠实性、完整性、粒度、过度抽取和业务边界。"],
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
    x: x + 0.82, y: y + 0.13, w: 4.85, h: 0.3, fontFace: FB,
    fontSize: 14.5, bold: true, color: C.white, margin: 0,
  });
  s.addText(it[2], {
    x: x + 0.82, y: y + 0.48, w: 4.8, h: 0.28, fontFace: FB,
    fontSize: 11.7, color: C.body, margin: 0,
  });
});
rect(s, LEFT + 1.2, 6.18, MW - 2.4, 0.55, C.bg2, C.bblue);
s.addText("Harness Agent 产 Review；Memory System 生成/检索；AgentCore Harness 注入；Reviewer / Human 判断质量。", {
  x: LEFT + 1.48, y: 6.18, w: MW - 2.96, h: 0.55,
  fontFace: FH, fontSize: 15.5, bold: true, color: C.bblue,
  align: "center", valign: "middle", margin: 0,
});

loadSpeakerNotes("docs/记忆能让Agent越跑越好吗-V3-notes.md");

p.writeFile({ fileName: "docs/记忆能让Agent越跑越好吗-V3.pptx" })
  .then((file) => console.log("WROTE", file));
