// Memory-Loop V3 deck. Dark AWS style aligned with the existing project deck.
const pptxgen = require("pptxgenjs");
const p = new pptxgen();
p.defineLayout({ name: "W", width: 13.333, height: 7.5 });
p.layout = "W";
p.author = "Amazon Web Services";
p.subject = "AgentCore Memory V3 explicit self-review experiment";
p.title = "Memory-Loop V3";
p.company = "亚马逊云科技";
p.lang = "zh-CN";
p.theme = { headFontFace: "Amazon Ember Display", bodyFontFace: "Microsoft YaHei" };

const C = {
  bg: "161E2D", bg2: "0B1220", card: "1C2740", line: "2E3B57",
  white: "FFFFFF", body: "CFD9E4", muted: "8496A8", lblue: "A8C7E8",
  blue: "0073E5", bblue: "42B4FF", orange: "FF6A3D", green: "00E500",
  good: "12331F", warm: "2A2418", cyan: "0C3440",
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
    color: C.body, margin: 0, breakLine: false,
  });
}
function box(s, x, y, w, h, label, head, body, opts = {}) {
  rect(s, x, y, w, h, opts.fill || C.card, opts.line || C.line);
  if (label) s.addText(label, {
    x: x + 0.22, y: y + 0.15, w: w - 0.44, h: 0.28, fontFace: FH,
    fontSize: 11.5, bold: true, color: opts.labelColor || C.bblue, margin: 0,
  });
  if (head) s.addText(head, {
    x: x + 0.22, y: y + 0.52, w: w - 0.44, h: 0.42, fontFace: FB,
    fontSize: 17, bold: true, color: C.white, margin: 0,
  });
  if (body) s.addText(body, {
    x: x + 0.22, y: y + (head ? 1.0 : 0.52), w: w - 0.44,
    h: h - (head ? 1.12 : 0.65), fontFace: FB, fontSize: opts.fontSize || 13,
    color: C.body, margin: 0, breakLine: false, valign: "top",
  });
}
function codebox(s, x, y, w, h, label, text, color = C.bblue, fs = 11.5) {
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
function arrow(s, x, y) {
  s.addText("→", {
    x, y, w: 0.42, h: 0.6, fontFace: FH, fontSize: 20, bold: true,
    color: C.bblue, align: "center", valign: "middle", margin: 0,
  });
}
function stat(s, x, y, w, label, value, color) {
  rect(s, x, y, w, 1.35, C.bg2, color);
  s.addText(value, {
    x: x + 0.1, y: y + 0.16, w: w - 0.2, h: 0.65, fontFace: FH,
    fontSize: 38, bold: true, color, align: "center", margin: 0,
  });
  s.addText(label, {
    x: x + 0.1, y: y + 0.88, w: w - 0.2, h: 0.28, fontFace: FB,
    fontSize: 12.5, color: C.body, align: "center", margin: 0,
  });
}

let s;

// 1
s = p.addSlide();
s.background = { color: C.bg };
s.addImage({ path: BAR, x: 0, y: 0, w: 0.16, h: 7.5 });
s.addText("AGENTCORE MEMORY · V3", {
  x: 0.75, y: 1.25, w: 10, h: 0.35, fontFace: FH, fontSize: 14,
  bold: true, color: C.bblue, charSpacing: 3, margin: 0,
});
s.addText("显式自审形成的记忆\n能迁移到下一份文档吗？", {
  x: 0.72, y: 1.72, w: 11.8, h: 1.65, fontFace: FH, fontSize: 42,
  bold: true, color: C.white, margin: 0,
});
s.addText("V3 用一次真实的 EPISODIC Memory 生成与单页留出实验，直接观察 Memory 如何改变抽取行为。", {
  x: 0.75, y: 3.62, w: 11.3, h: 0.5, fontFace: FB, fontSize: 17,
  color: C.body, margin: 0,
});
rect(s, 0.75, 4.35, 11.05, 1.15, C.card);
s.addText("13 页源文档 → self_review → 1 episode + 2 reflections → 新 session 抽取电机图纸", {
  x: 1.0, y: 4.35, w: 10.55, h: 1.15, fontFace: FB, fontSize: 18,
  bold: true, color: C.bblue, align: "center", valign: "middle", margin: 0,
});
s.addText("Memory-Loop V3 · us-west-2 · 完整输出交由人工审阅", {
  x: 0.75, y: 6.0, w: 11.4, h: 0.35, fontFace: FB, fontSize: 12,
  color: C.muted, margin: 0,
});
s.addText("亚马逊云科技", {
  x: 0.75, y: 7.02, w: 3, h: 0.28, fontFace: FH, fontSize: 12,
  bold: true, color: C.lblue, margin: 0,
});

// 2
s = p.addSlide(); base(s, "THE QUESTION", 2);
title(s, "这次只问一个问题", "无人工反馈、无外部评分参与 Memory 形成：Agent 自审产生的托管记忆，会不会改变下一份文档的抽取？");
box(s, LEFT, 2.0, 3.7, 2.3, "SOURCE", "13 页液氮罐文档", "两阶段执行：先形成显式 self_review，再根据 next_actions 修订最终结果。", { fill: C.cyan });
box(s, LEFT + 4.05, 2.0, 3.7, 2.3, "MANAGED MEMORY", "AgentCore EPISODIC", "后台从完整 session 提炼 episode，并跨 episode 生成可复用 reflection。", { fill: C.warm, labelColor: C.orange });
box(s, LEFT + 8.1, 2.0, 4.0, 2.3, "TARGET", "一页电机图纸", "同一抽取 prompt，对比 Memory enabled 与 Memory disabled 的输出差异。", { fill: C.good, labelColor: C.green });
s.addText("不是“模型记住了答案”，而是“模型记住了处理复杂文档的方法”。", {
  x: LEFT, y: 4.65, w: MW, h: 0.72, fontFace: FH, fontSize: 22,
  bold: true, color: C.white, align: "center", margin: 0,
});
box(s, LEFT + 2.0, 5.45, 8.1, 0.82, "", "", "V3 不报告自动分数，完整结果由人工判断是否忠实、完整、存在臆造。", { fill: C.bg2, fontSize: 14 });

// 3
s = p.addSlide(); base(s, "THE FLOW", 3);
title(s, "从自审到跨任务复用", "Memory 形成与目标测试分成两个清晰阶段；目标测试使用新的 runtime session。");
const flowY = 2.25, flowW = 2.08;
box(s, LEFT, flowY, flowW, 1.25, "①", "内部草稿", "通读源文档", { fill: C.card });
arrow(s, LEFT + 2.11, flowY + 0.3);
box(s, LEFT + 2.55, flowY, flowW, 1.25, "②", "显式自审", "coverage / omissions\nformat / granularity", { fill: C.cyan });
arrow(s, LEFT + 4.66, flowY + 0.3);
box(s, LEFT + 5.1, flowY, flowW, 1.25, "③", "修订输出", "执行 next_actions", { fill: C.card });
arrow(s, LEFT + 7.21, flowY + 0.3);
box(s, LEFT + 7.65, flowY, flowW, 1.25, "④", "托管提炼", "episode + reflections", { fill: C.warm, labelColor: C.orange });
arrow(s, LEFT + 9.76, flowY + 0.3);
box(s, LEFT + 10.2, flowY, 1.9, 1.25, "⑤", "目标测试", "新 session", { fill: C.good, labelColor: C.green });
stat(s, LEFT, 4.15, 3.75, "session-level episode", "1", C.orange);
stat(s, LEFT + 4.18, 4.15, 3.75, "actor-level reflections", "2", C.bblue);
stat(s, LEFT + 8.36, 4.15, 3.75, "source actor", "1", C.green);
s.addText("actor: ep-review-1789102186", {
  x: LEFT + 8.36, y: 5.72, w: 3.75, h: 0.28, fontFace: FM,
  fontSize: 10.5, color: C.muted, align: "center", margin: 0,
});

// 4
s = p.addSlide(); base(s, "MEMORY CONTENT", 4);
title(s, "AgentCore 实际记住了什么", "不是字段值，而是处理复杂技术文档的工作模式与质量控制经验。");
box(s, LEFT, 1.9, 4.0, 3.95, "EPISODE REFLECTION", "两阶段流程设计有效",
  "先输出 self_review 再执行修订，降低一次性处理复杂文档时的遗漏风险。\n\n将质量问题与对应 JSON 记录关联，保留可追溯性。\n\n图片或 ASCII 图无法完整提取时，应显式说明限制。", { fill: C.cyan, labelColor: C.bblue, fontSize: 13 });
box(s, LEFT + 4.25, 1.9, 3.85, 3.95, "ACTOR REFLECTION 1", "Two-Phase Structured Extraction",
  "· 先检查覆盖、遗漏、格式和粒度\n· 再执行结构化抽取\n· 保留原文用于追溯\n· 对不可抽取内容明确说明", { fill: C.warm, labelColor: C.orange, fontSize: 13 });
box(s, LEFT + 8.35, 1.9, 3.75, 3.95, "ACTOR REFLECTION 2", "Inline Annotation",
  "· 遇到 OCR 错误或冲突信息时不静默丢弃\n· 将质量说明关联到对应记录\n· 保留冲突值与原文\n· 文档级限制放入 __META__", { fill: C.good, labelColor: C.green, fontSize: 13 });
s.addText("Memory 的抽象层级：任务执行方法 > 当前文档事实", {
  x: LEFT, y: 6.1, w: MW, h: 0.45, fontFace: FH, fontSize: 17,
  bold: true, color: C.white, align: "center", margin: 0,
});

// 5
s = p.addSlide(); base(s, "CONTROL", 5);
title(s, "目标端只改变 Memory 开关", "测试文档、模型、推理参数、prompt 和输出约束保持一致。");
const rows = [
  ["测试文档", "2477080009简图-8.16", "相同"],
  ["System prompt", "同一 invocation-level prompt", "相同"],
  ["模型", "claude-sonnet-4-6", "相同"],
  ["推理参数", "temperature=0 · maxTokens=32768", "相同"],
  ["工具与 Skill", "skills=[] · tools=[]", "相同"],
  ["Runtime session", "两组均使用全新 session", "相同"],
  ["Harness Memory", "enabled / disabled", "唯一变量"],
];
s.addTable(
  [
    [
      { text: "控制项", options: { bold: true, color: C.white, fill: C.blue } },
      { text: "设置", options: { bold: true, color: C.white, fill: C.blue } },
      { text: "状态", options: { bold: true, color: C.white, fill: C.blue } },
    ],
    ...rows.map((r, i) => r.map((v, j) => ({
      text: v,
      options: {
        color: j === 2 && i === rows.length - 1 ? C.green : C.body,
        bold: j === 2 || (j === 0 && i === rows.length - 1),
        fill: i === rows.length - 1 ? C.good : C.card,
        fontFace: FB, fontSize: 13, valign: "middle",
      },
    }))),
  ],
  {
    x: LEFT, y: 1.9, w: MW, h: 3.65, colW: [2.7, 6.8, 2.6],
    rowH: [0.45, 0.44, 0.44, 0.44, 0.44, 0.44, 0.44, 0.5],
    border: { pt: 0.75, color: C.line }, fontFace: FB, fontSize: 13,
  }
);
box(s, LEFT + 1.75, 5.82, 8.6, 0.65, "", "", "Memory 组复用 source actor；No Memory 组绑定 disabled Harness。", { fill: C.bg2, fontSize: 14 });

// 6
s = p.addSlide(); base(s, "RESULT", 6);
title(s, "Memory 改变了抽取覆盖范围", "两组都抽出了标题栏与技术要求；Memory 组进一步系统展开了两张 BOM 表。");
stat(s, LEFT, 1.95, 5.7, "Memory 首次运行", "31 条", C.green);
stat(s, LEFT + 6.4, 1.95, 5.7, "No Memory 首次运行", "11 条", C.bblue);
s.addShape(p.ShapeType.rect, { x: LEFT, y: 3.65, w: 11.4, h: 0.44, fill: { color: C.bg2 }, line: { color: C.bg2 } });
s.addShape(p.ShapeType.rect, { x: LEFT, y: 3.65, w: 11.4, h: 0.44, fill: { color: C.green }, line: { color: C.green } });
s.addShape(p.ShapeType.rect, { x: LEFT, y: 4.45, w: 4.05, h: 0.44, fill: { color: C.bblue }, line: { color: C.bblue } });
s.addText("Memory", { x: LEFT, y: 3.32, w: 1.2, h: 0.25, fontFace: FH, fontSize: 11, bold: true, color: C.green, margin: 0 });
s.addText("No Memory", { x: LEFT, y: 4.12, w: 1.4, h: 0.25, fontFace: FH, fontSize: 11, bold: true, color: C.bblue, margin: 0 });
box(s, LEFT, 5.15, 5.7, 1.0, "MEMORY 多出的主要内容", "", "机座、前后端盖、转子、定子、轴承，以及壳体/法兰盘/散热器等组件明细。", { fill: C.good, labelColor: C.green, fontSize: 13 });
box(s, LEFT + 6.4, 5.15, 5.7, 1.0, "人工初看", "", "新增条目基本都能在两张 BOM 表中找到原文依据，没有明显臆造。", { fill: C.cyan, labelColor: C.bblue, fontSize: 13 });

// 7
s = p.addSlide(); base(s, "EXAMPLES", 7);
title(s, "同一份图纸，输出关注点不同", "Memory 组把表格行当成需要完整保留的结构化信息；No Memory 组更聚焦技术要求。");
codebox(s, LEFT, 1.85, 5.9, 3.9, "MEMORY · BOM 条目", JSON.stringify([
  {
    "设备部件": "机座",
    "指标名称": "零件明细（表1-序号1）",
    "指标特征": "数量：1；其余字段原文为「-」"
  },
  {
    "设备部件": "壳体组件",
    "指标名称": "组件明细（表2-序号1）",
    "指标特征": "数量：1；其余字段原文为「-」"
  }
], null, 2), C.green, 10.5);
codebox(s, LEFT + 6.2, 1.85, 5.9, 3.9, "NO MEMORY · 技术要求", JSON.stringify([
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
s.addText("观察：Memory 没有简单复读源文档事实，而是改变了“什么值得结构化”的判断。", {
  x: LEFT + 0.4, y: 6.0, w: MW - 0.8, h: 0.42, fontFace: FH, fontSize: 17,
  bold: true, color: C.white, align: "center", margin: 0,
});

// 8
s = p.addSlide(); base(s, "TAKEAWAY", 8);
title(s, "V3 能说什么", "这是一次行为观察：结果值得人工检查，但还不是统计结论。");
box(s, LEFT, 1.95, 5.85, 2.5, "可以确认", "", "· 显式 self_review 能被托管 EPISODIC 提炼\n· actor-level reflection 能跨 session 复用\n· Memory 组明显扩大了 BOM 覆盖范围\n· 新增条目初看有原文依据", { fill: C.good, labelColor: C.green, fontSize: 14 });
box(s, LEFT + 6.25, 1.95, 5.85, 2.5, "仍需人工判断", "", "· BOM 是否都属于任务目标\n· 31 条是否存在过度抽取\n· 两次运行的随机方差\n· reflection 的适用边界与噪声", { fill: C.warm, labelColor: C.orange, fontSize: 14 });
rect(s, LEFT, 4.8, MW, 1.2, C.card);
s.addText("Memory 让 Agent 更主动地覆盖结构化表格；\n这种变化是改进还是过抽，最终要由任务口径决定。", {
  x: LEFT + 0.5, y: 4.8, w: MW - 1.0, h: 1.2, fontFace: FH, fontSize: 20,
  bold: true, color: C.bblue, align: "center", valign: "middle", margin: 0,
});

p.writeFile({ fileName: "docs/记忆能让Agent越跑越好吗-V3.pptx" })
  .then((file) => console.log("WROTE", file));
