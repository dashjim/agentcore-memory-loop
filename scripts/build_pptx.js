// 《记忆能让 Agent 越跑越好吗》PPTX —— AWS 深色风格，12 页实现导向结构（对齐 HTML 版）。
const pptxgen = require("pptxgenjs");
const p = new pptxgen();
p.defineLayout({ name: "W", width: 13.333, height: 7.5 });
p.layout = "W";
p.theme = { headFontFace: "Amazon Ember Display", bodyFontFace: "Microsoft YaHei" };

const C = {
  bg: "161E2D", bg2: "0B1220", card: "1C2740", line: "2E3B57",
  white: "FFFFFF", body: "CFD9E4", muted: "8496A8", lblue: "A8C7E8",
  blue: "0073E5", bblue: "42B4FF", orange: "FF6A3D", green: "00E500",
  goodtint: "12331F", badtint: "35181C", memtint: "2A2418",
};
const FH = "Amazon Ember Display", FB = "Microsoft YaHei", FM = "Amazon Ember Mono";
const BAR = "assets/leftbar.png";
const LEFT = 0.62, MW = 12.1;

function base(s, kicker) {
  s.background = { color: C.bg };
  s.addImage({ path: BAR, x: 0, y: 0, w: 0.16, h: 7.5 });
  if (kicker) s.addText(kicker, { x: 6.3, y: 0.42, w: 6.4, h: 0.35, fontFace: FH, fontSize: 13, bold: true, color: C.bblue, charSpacing: 3, align: "right", margin: 0 });
}
function title(s, t, lead) {
  s.addText(t, { x: LEFT, y: 0.4, w: 11.4, h: 0.7, fontFace: FH, fontSize: 27, bold: true, color: C.white, margin: 0 });
  if (lead) s.addText(lead, { x: LEFT, y: 1.14, w: MW, h: 0.62, fontFace: FB, fontSize: 14, color: C.body, margin: 0, lineSpacingMultiple: 1.15 });
}
function footer(s, note, n) {
  if (note) s.addText(note, { x: LEFT, y: 6.72, w: 10.6, h: 0.5, fontFace: FB, fontSize: 10.5, color: C.muted, margin: 0, lineSpacingMultiple: 1.1, valign: "top" });
  s.addText("亚马逊云科技", { x: LEFT, y: 7.08, w: 3, h: 0.3, fontFace: FH, fontSize: 11, bold: true, color: C.lblue, margin: 0 });
  s.addText(String(n), { x: 12.5, y: 7.05, w: 0.5, h: 0.3, fontFace: FH, fontSize: 11, color: C.muted, align: "right", margin: 0 });
}
function rect(s, x, y, w, h, fill) { s.addShape(p.ShapeType.roundRect, { x, y, w, h, rectRadius: 0.09, fill: { color: fill || C.card }, line: { color: C.line, width: 0.75 } }); }
function box(s, x, y, w, h, label, head, body, o = {}) {
  rect(s, x, y, w, h, o.fill || C.card);
  let yy = y + 0.16;
  if (label) { s.addText(label, { x: x + 0.22, y: yy, w: w - 0.4, h: 0.3, fontFace: FH, fontSize: 12, bold: true, color: o.labelColor || C.bblue, margin: 0 }); yy += 0.34; }
  if (head) { s.addText(head, { x: x + 0.22, y: yy, w: w - 0.4, h: 0.36, fontFace: FB, fontSize: 16.5, bold: true, color: C.white, margin: 0 }); yy += 0.44; }
  if (body) s.addText(body, { x: x + 0.22, y: yy, w: w - 0.44, h: y + h - yy - 0.12, fontFace: FB, fontSize: 13, color: C.body, margin: 0, lineSpacingMultiple: 1.15, valign: "top" });
}
function rowCard(s, x, y, w, h, num, head, desc, accent) {
  rect(s, x, y, w, h, C.card);
  s.addText(String(num), { x: x + 0.22, y: y + h / 2 - 0.26, w: 0.52, h: 0.52, shape: p.ShapeType.ellipse, fill: { color: accent || C.blue }, color: C.white, align: "center", valign: "middle", fontFace: FH, fontSize: 17, bold: true, margin: 0 });
  const tx = x + 0.95;
  s.addText(head, { x: tx, y: y + 0.16, w: w - 1.1, h: 0.34, fontFace: FB, fontSize: 16, bold: true, color: accent === C.orange ? C.orange : C.white, margin: 0 });
  s.addText(desc, { x: tx, y: y + 0.52, w: w - 1.1, h: h - 0.62, fontFace: FB, fontSize: 13, color: C.body, margin: 0, lineSpacingMultiple: 1.12 });
}
function darkbar(s, x, y, w, h, runs) { rect(s, x, y, w, h, C.bg2); s.addText(runs, { x: x + 0.05, y, w: w - 0.4, h, fontFace: FB, valign: "middle", align: "left", margin: [8, 16, 8, 16], lineSpacingMultiple: 1.18 }); }
function codebox(s, x, y, w, h, label, labelColor, txt) {
  rect(s, x, y, w, h, C.card);
  s.addText(label, { x: x + 0.22, y: y + 0.14, w: w - 0.4, h: 0.3, fontFace: FH, fontSize: 12, bold: true, color: labelColor, margin: 0 });
  rect(s, x + 0.22, y + 0.5, w - 0.44, h - 0.66, C.bg2);
  s.addText(txt, { x: x + 0.34, y: y + 0.5, w: w - 0.66, h: h - 0.66, fontFace: FM, fontSize: 11.5, color: C.body, align: "left", valign: "top", margin: [8, 8, 8, 8], lineSpacingMultiple: 1.18 });
}
function R(text, o = {}) { return { text, options: { fontFace: FB, breakLine: true, ...o } }; }
function tcell(text, o = {}) { return { text, options: { fontFace: FB, fontSize: o.fs || 12.5, bold: !!o.b, color: o.color || C.body, fill: { color: o.fill || C.card }, align: o.align || "left", valign: "middle" } }; }
let s;
function nd(x, y, w, txt, o = {}) { s.addText(txt, { x, y, w, h: 0.78, shape: p.ShapeType.roundRect, rectRadius: 0.06, fill: { color: o.bg || C.card }, line: { color: o.bd || C.line, width: 1 }, align: "center", valign: "middle", fontFace: FB, fontSize: 12.5, bold: true, color: o.color || C.white, margin: 2 }); }
function ar(x, y) { s.addText("→", { x, y, w: 0.34, h: 0.78, align: "center", valign: "middle", fontFace: FH, fontSize: 18, bold: true, color: C.bblue }); }

// ===== 1 TITLE =====
s = p.addSlide(); s.background = { color: C.bg };
s.addImage({ path: BAR, x: 0, y: 0, w: 0.16, h: 7.5 });
s.addText("AGENTCORE MEMORY · 一条有效的记忆回路", { x: 0.75, y: 1.35, w: 11, h: 0.4, fontFace: FH, fontSize: 14, bold: true, color: C.bblue, charSpacing: 3, margin: 0 });
s.addText("记忆能让 AI Agent\n越跑越好吗？", { x: 0.72, y: 1.8, w: 11.8, h: 1.75, fontFace: FH, fontSize: 46, bold: true, color: C.white, margin: 0, lineSpacingMultiple: 1.05 });
s.addText("答案是能——本文用一条真实跑通的实现，讲清「怎样的记忆才有效」，并附上每一步的真实提示词。", { x: 0.75, y: 3.7, w: 11.3, h: 0.5, fontFace: FB, fontSize: 17, color: C.body, margin: 0 });
rect(s, 0.75, 4.4, 11.1, 1.25, C.card);
s.addText([
  R("关键前提：回路里要有一个判定源（判定对错 / 该抽什么的外部权威）。", { fontSize: 16, color: C.body }),
  R("记忆是好的载体，不是好的老师。", { fontSize: 16, bold: true, color: C.bblue }),
], { x: 1.0, y: 4.4, w: 10.6, h: 1.25, fontFace: FB, valign: "middle", margin: 0, lineSpacingMultiple: 1.25 });
s.addText("复现自 AWS 博客《Self-learning evolvable agents … with AgentCore》 · us-west-2 · 场景：低温液氮储罐技术要求抽取", { x: 0.75, y: 6.0, w: 11.5, h: 0.4, fontFace: FB, fontSize: 12, color: C.muted, margin: 0 });
s.addText("亚马逊云科技", { x: 0.75, y: 7.02, w: 4, h: 0.3, fontFace: FH, fontSize: 12, bold: true, color: C.lblue, margin: 0 });

// ===== 2 THE ANSWER =====
s = p.addSlide(); base(s, "THE ANSWER");
title(s, "能，但记忆是「载体」，不是「老师」", "记忆机制本身没问题——它把反馈搬到下一次运行。真正决定成败的，是记忆里存的内容质量，而那取决于回路里有没有判定源。");
box(s, LEFT, 2.0, 3.85, 2.05, "有效 ✓", "存 judgment 反馈", "大模型/人类对比目标产出的反馈写进记忆 → 下次注入 → 覆盖率 0.642 → 0.813，关键探针 1/7 → 7/7。", { fill: C.goodtint, labelColor: C.green });
box(s, LEFT + 4.0, 2.0, 3.85, 2.05, "无效 ✗", "存自省规则", "让模型对自己产出空想、蒸馏规则（无判定源）→ 关键探针纹丝不动 1/7，甚至因过度拆分帮倒忙。", { fill: C.badtint, labelColor: C.orange });
box(s, LEFT + 8.0, 2.0, 4.1, 2.05, "机制相同", "差别只在内容", "两者注入路径完全一样（都是记忆）。唯一变量是记忆里存什么——所以说记忆是载体不是老师。");
darkbar(s, LEFT, 4.35, MW, 1.6, [R("本文主要讲清那条有效的回路：抽取 → 大模型对比标准答案产出反馈 → 写进记忆 → 注入重抽。每一步都附真实提示词与真实产物。", { fontSize: 15, color: C.body }), R("失败的自省法作为对照，一页带过。", { fontSize: 14.5, color: C.muted })]);
footer(s, "", 2);

// ===== 3 THE RECIPE =====
s = p.addSlide(); base(s, "THE RECIPE");
title(s, "让记忆真正生效的四步回路", "任务：从中文工业文档抽 设备主体·部件·指标名称·指标特征·原文，对比人工标注的标准答案（123 条）打分。下面这条回路把覆盖率从 0.642 拉到 0.813。");
let fx = LEFT, fy = 2.35; const fw = 2.06;
nd(fx, fy, fw, "① 基线抽取"); ar(fx + fw, fy);
nd(fx + fw + 0.34, fy, fw, "② 大模型检查器\n对比标准答案产反馈", { bd: C.bblue, color: C.bblue }); ar(fx + 2 * fw + 0.34, fy);
nd(fx + 2 * fw + 0.68, fy, fw, "③ 写进记忆", { bg: C.memtint, bd: C.orange, color: C.orange }); ar(fx + 3 * fw + 0.68, fy);
nd(fx + 3 * fw + 1.02, fy, fw, "④ 注入重抽"); ar(fx + 4 * fw + 1.02, fy);
nd(fx + 4 * fw + 1.36, fy, fw, "0.642 → 0.813", { bg: C.goodtint, bd: C.green, color: C.green });
const s3y = 3.6, s3h = 1.85, s3w = 2.9;
box(s, LEFT, s3y, s3w, s3h, "步骤①", null, "先跑一遍基线抽取，看它漏了什么。");
box(s, LEFT + 3.02, s3y, s3w, s3h, "步骤②", null, "判定源在这里进入：大模型对比标准答案，产出可迁移反馈。", { labelColor: C.bblue, fill: "16233A" });
box(s, LEFT + 6.04, s3y, s3w, s3h, "步骤③", null, "反馈作为记忆写入（事件存储），可复用。", { labelColor: C.orange });
box(s, LEFT + 9.06, s3y, 3.04, s3h, "步骤④", null, "下一次抽取注入这条记忆，直接受益。");
darkbar(s, LEFT, 5.6, MW, 0.75, [R("※ 标准答案只进步骤②的检查器，绝不进抽取器。后面 5–8 页逐步拆解，含真实提示词。", { fontSize: 13.5, color: C.body })]);
footer(s, "这就是真实 agent 回路：反馈（人类/大模型）→ 记忆捕获 → 下次更好。", 3);

// ===== 4 KEY CONCEPT =====
s = p.addSlide(); base(s, "KEY CONCEPT");
title(s, "判定源：整条回路的前提", "判定源 = 能告诉 agent「对不对 / 该抽什么」的外部权威。核心：它提供的信息，从输入本身推不出来，必须外部给。");
s.addTable([
  [tcell("判定源形式", { b: 1, fill: C.blue, color: C.white }), tcell("告诉 agent 什么", { b: 1, fill: C.blue, color: C.white })],
  [tcell("标准答案"), tcell("这篇「应该」抽出哪些")],
  [tcell("人类反馈", { b: 1, color: C.white }), tcell("「这类也要抽」/「这条错了」")],
  [tcell("大模型对比标准答案 / 规范检查", { b: 1, color: C.white }), tcell("按规范判对错、漏了哪类")],
  [tcell("下游验证"), tcell("参数拿去用报错 → 抽错了")],
], { x: LEFT, y: 2.15, w: 6.5, h: 2.35, border: { pt: 0.75, color: C.line }, valign: "middle", fontSize: 13 });
box(s, LEFT + 6.7, 2.15, 5.4, 1.12, "为什么非它不可", null, "模型看着「外观颜色须与甲方确认」，光凭\"原文+自己的输出\"推不出\"这句该成为一条记录\"——这个信号藏在判定源里，不在输入里。", { labelColor: C.orange });
box(s, LEFT + 6.7, 3.38, 5.4, 1.12, "一句话", null, "记忆不产生新知识，它只搬运。搬运什么，取决于回路里的判定源。");
darkbar(s, LEFT, 4.75, MW, 0.95, [R("这也解释了 AWS 博客那套 self-learning 为什么有效——它吃的是人类/下游反馈这个判定源，不是模型的自我空想。", { fontSize: 14.5, color: C.body })]);
footer(s, "标准答案只是其中一种；后三种在真实系统里很常见。", 4);

// ===== 5 STEP ① =====
s = p.addSlide(); base(s, "STEP ①");
title(s, "① 基线抽取：先看它漏了什么", "用只含 schema + 红线的基线提示词跑一遍，暴露问题——这决定了步骤②要产出什么反馈。");
codebox(s, LEFT, 1.95, 5.9, 2.35, "基线抽取 system prompt（节选）", C.bblue,
  "你是工业技术文档信息抽取助手。\n针对每条技术要求抽一条记录，字段：\n 设备主体/设备部件/指标名称/指标特征/原文\n红线：① 忠实抽取，绝不臆造；② 输出严格 JSON；\n ③ 不补单位；④ 不因格式跳过。\n（内联自审；你看不到标准答案）");
box(s, LEFT + 6.2, 1.95, 5.9, 2.35, "跑完发现：整类漏抽（约 3/4 是\"真召回失败\"）", null,
  "· 外观颜色及喷涂 LOGO 须与甲方确认\n· 真空度测量报告 / 真空度测量要求\n· 外部油漆等工序\n· 承制单位细化设计…提供全套地脚螺栓\n\n都不是「指标+数值」，而是离散文字/流程/待确认类——schema 面向定量，模型以为不该抽。", { fill: C.badtint, labelColor: C.orange });
s.addTable([
  [tcell("基线实测（标准答案 123 条）", { b: 1, fill: C.blue, color: C.white }), tcell("覆盖率", { b: 1, fill: C.blue, color: C.white }), tcell("抽取条数", { b: 1, fill: C.blue, color: C.white }), tcell("真召回失败", { b: 1, fill: C.blue, color: C.white }), tcell("离散文字探针", { b: 1, fill: C.blue, color: C.white })],
  [tcell("纯 schema+红线 提示词"), tcell("0.642"), tcell("83"), tcell("27", { color: C.orange, b: 1 }), tcell("1 / 7", { color: C.orange, b: 1 })],
], { x: LEFT, y: 4.5, w: MW, h: 0.85, colW: [4.3, 1.95, 1.95, 1.95, 1.95], border: { pt: 0.75, color: C.line }, valign: "middle", fontSize: 13 });
footer(s, "离散文字探针 = 从漏项挑 7 个代表词（真空度测量/外观颜色/…），看抽出几个。基线只 1/7 → 步骤②的反馈就要专治这个。", 5);

// ===== 6 STEP ② =====
s = p.addSlide(); base(s, "STEP ②");
title(s, "② 大模型对比标准答案，产出反馈", "让一个检查器读「抽取结果 + 标准答案」，产出可迁移的规则性反馈（不照抄答案）。标准答案只进这一步。");
codebox(s, LEFT, 1.95, 5.9, 2.6, "检查器 system prompt（真实原文）", C.bblue,
  "你是抽取质检专家。给你【抽取结果】\n和【标准答案】。对比两者，产出可迁移、\n指导未来抽取的改进反馈（≤10 条）：\n ① 系统性漏抽的类别/类型；\n ② 粒度问题（过度拆分/该合并）；\n ③ 规则性、可复用的纠正指引。\n不要逐条罗列答案——要给出下次能照做的规则。");
codebox(s, LEFT + 6.2, 1.95, 5.9, 2.6, "它真实产出的反馈（节选·已脱敏）", C.green,
  "1. 无损检测(RT/PT/UT)整类缺失 → 须作为\n   独立条目抽取，勿因\"过程要求\"忽略\n2. 制造/见证要求(合拢/压力试验须联系\n   甲方见证)漏抽\n3. 计算/设计文件交付要求漏抽\n4. 外观/标识/土建配合(外观颜色须与甲方\n   确认…)漏抽\n9. 非定量/程序性要求也须抽");
darkbar(s, LEFT, 4.75, MW, 1.1, [R("关键：检查器看得到标准答案，所以能指出\"整类漏了什么\"——这正是判定源的信号。同样让 LLM 产出记忆，给不给标准答案就是有效与无效的分界（对照见第 9 页）。", { fontSize: 14, color: C.body })]);
footer(s, "交互式与固定提示词的自动检查器两种实例，结论一致。", 6);

// ===== 7 STEP ③ =====
s = p.addSlide(); base(s, "STEP ③");
title(s, "③ 把反馈写进 AgentCore Memory", "这条反馈作为记忆写入、可跨运行复用。用什么记忆、存成什么样，直接决定下一步的效果。");
box(s, LEFT, 1.95, 5.9, 2.55, "Memory 类型（怎么存）", null,
  "用 AgentCore 自定义记忆当「事件存储」：create_event 写、list_events 精确即时读（不走 SEMANTIC/EPISODIC 异步策略——要可控、即时、可复现）。\n\n存在固定分区 canon-{actorId}，每次更新追加一版、读取取最新版；注入时逐字拼进 system prompt 的\"已积累经验\"段。");
codebox(s, LEFT + 6.2, 1.95, 5.9, 2.55, "记忆里存的内容（真实）", C.green,
  "【质检反馈·务必逐条应用】\n1. 非定量要求也要抽：定性/流程/报告/\n   待确认类 → 映射进 指标名称/特征\n2. 覆盖易漏类别：真空度测量/无损检测/\n   环境/受压/阀门/管口/材料\n3. 粒度对齐：默认一原文一记录");
darkbar(s, LEFT, 4.7, MW, 1.15, [R("对照坏例子：如果让模型自省自己的输出（无判定源），存进去的是\"复合指标要拆分\"这类通用文风规则——指不出漏了哪类，还诱发过度拆分。好记忆 = 指名道姓的、来自判定源的反馈。", { fontSize: 14, color: C.body })]);
footer(s, "记忆负责\"捕获并复用\"，不负责\"产生\"——产生要靠判定源。", 7);

// ===== 8 STEP ④ =====
s = p.addSlide(); base(s, "STEP ④");
title(s, "④ 注入记忆重抽 —— 效果兑现", "用基线提示词、注入这条记忆，重新抽一遍。之前\"整类视而不见\"的离散文字要求现在都抓到了。");
codebox(s, LEFT, 1.95, 5.9, 1.5, "注入前（基线漏掉）", C.orange,
  "（无此条目——整类未抽）\n「外观颜色及喷涂 LOGO 须与甲方确认」");
codebox(s, LEFT + 6.2, 1.95, 5.9, 1.5, "注入后（真实抽出）", C.green,
  "{\"设备主体\":\"150m³液氮储罐\",\n \"设备部件\":\"储罐整体\",\n \"指标名称\":\"外观颜色与喷涂确认\",\n \"指标特征\":\"须与甲方确认\", …}");
s.addTable([
  [tcell("　", { fill: C.bg2 }), tcell("覆盖率", { b: 1, fill: C.blue, color: C.white }), tcell("精确率", { b: 1, fill: C.blue, color: C.white }), tcell("F1", { b: 1, fill: C.blue, color: C.white }), tcell("真召回失败", { b: 1, fill: C.blue, color: C.white }), tcell("离散文字探针", { b: 1, fill: C.blue, color: C.white })],
  [tcell("基线"), tcell("0.642"), tcell("–"), tcell("–"), tcell("27"), tcell("1 / 7")],
  [tcell("注入判定源反馈记忆", { b: 1, fill: C.goodtint }), tcell("0.813", { color: C.green, b: 1, fill: C.goodtint }), tcell("0.813", { fill: C.goodtint }), tcell("0.813", { color: C.green, b: 1, fill: C.goodtint }), tcell("2", { fill: C.goodtint }), tcell("7 / 7", { color: C.green, b: 1, fill: C.goodtint })],
], { x: LEFT, y: 3.65, w: MW, h: 0.95, border: { pt: 0.75, color: C.line }, valign: "middle", fontSize: 12.5 });
darkbar(s, LEFT, 4.85, MW, 1.05, [R("两种实例一致：交互式 F1 0.813；固定提示词的自动检查器脚本 cov 0.789 / F1 0.833 / 探针 6/7——证明这条回路可 hands-off 自动跑。", { fontSize: 14, color: C.body })]);
footer(s, "+0.07 覆盖率其实低估了进步：真召回失败 27→2，残余多是粒度对齐问题，不再是召回失败。", 8);

// ===== 9 CONTROL =====
s = p.addSlide(); base(s, "CONTROL");
title(s, "对照：只让记忆「自省」，学不到", "把步骤②③换成\"让模型反思自己的输出、蒸馏成规则\"（全程无标准答案），其余不变——这是最初的记忆设计。");
box(s, LEFT, 2.35, 5.9, 2.2, "无判定源 · 自省", "关键探针纹丝不动 1/7", "模型只看自己的产出，没有信号告诉它「离散文字类也算数」。产出通用文风规则，碰不到真问题，还因过度拆分帮倒忙。", { fill: C.badtint, labelColor: C.orange });
rect(s, LEFT + 6.2, 2.35, 5.9, 2.2, C.card);
s.addText("决定性对照 · 同机制只变内容", { x: LEFT + 6.42, y: 2.5, w: 5.4, h: 0.3, fontFace: FH, fontSize: 12, bold: true, color: C.bblue, margin: 0 });
s.addText([
  R("自省规则（无判定源）　→　探针 1 / 7", { fontSize: 15, bold: true, color: C.orange }),
  R("大模型反馈（有判定源）　→　探针 7 / 7", { fontSize: 15, bold: true, color: C.green }),
  R("注入路径完全相同（都是记忆），唯一差别是内容有没有判定源。", { fontSize: 13, color: C.body }),
], { x: LEFT + 6.42, y: 2.95, w: 5.45, h: 1.5, fontFace: FB, margin: 0, valign: "top", lineSpacingMultiple: 1.3 });
darkbar(s, LEFT, 4.7, MW, 1.15, [R("这就是全文的因果锚点：记忆机制一直是好的；能不能越跑越好，取决于记忆里存的是\"判定源反馈\"还是\"无源自省\"。（我们还修过一个评分 bug——V1 曾误以为记忆有效，详见 blog。）", { fontSize: 14, color: C.body })]);
footer(s, "无判定源也非全无用：靠对照原文的自我批评能救回 4–10 条源覆盖类漏项，但学不到\"该抽什么\"。", 9);

// ===== 10 BEST PRACTICE =====
s = p.addSlide(); base(s, "BEST PRACTICE");
title(s, "怎么用记忆，才能真的越跑越好", "记忆负责「捕获并复用」反馈，反馈本身必须由判定源提供。落到工程上四条。");
const by = 2.15, bh = 1.9, bw = 5.9;
rowCard(s, LEFT, by, bw, bh, 1, "先确保回路里有判定源", "没有\"对错/目标\"的外部信号，记忆再多也原地打转。判定源不必是完整标准答案——一次人类纠正、少量标注、带 rubric 的裁判都行。", C.blue);
rowCard(s, LEFT + 6.2, by, bw, bh, 2, "存「具体批评」，别存「抽象规则」", "\"你漏了真空度测量这一段\"有用；\"复合指标要拆分\"空洞，还诱发过度拆分反噬。记忆要对照答案/原文，指名道姓。", C.blue);
rowCard(s, LEFT, by + bh + 0.2, bw, bh, 3, "判定源可以只用一次", "用少量标准答案做一次检查、把结论沉淀成可复用记忆，之后无标注地跑。用少量监督撬动长期收益，最划算。", C.blue);
rowCard(s, LEFT + 6.2, by + bh + 0.2, bw, bh, 4, "分清想学哪类教训", "任务规格类必须判定源；源覆盖 / 一致性类对照原文即可，无判定源也能学一点（天花板低）。", C.orange);
footer(s, "记忆是好的载体，不是好的老师。", 10);

// ===== 11 DATA =====
s = p.addSlide(); base(s, "DATA");
title(s, "四种回路放同一把尺", "看离散文字探针这一列就够——它是\"任务规格类教训\"的探针：只有引入判定源，才从 1/7 跳到 7/7。");
const hd = { b: 1, fill: C.blue, color: C.white, fs: 12 };
s.addTable([
  [tcell("回路", hd), tcell("教训来源", hd), tcell("教训放哪", hd), tcell("覆盖率", hd), tcell("F1", hd), tcell("真召回失败", hd), tcell("离散文字探针", hd)],
  [tcell("基线（无记忆）"), tcell("—"), tcell("—"), tcell("0.642"), tcell("–"), tcell("27"), tcell("1/7")],
  [tcell("自省记忆", { fill: C.badtint }), tcell("自省·无判定源", { fill: C.badtint }), tcell("记忆", { fill: C.badtint }), tcell("0.561", { fill: C.badtint }), tcell("–", { fill: C.badtint }), tcell("18*", { fill: C.badtint }), tcell("1/7", { fill: C.badtint, color: C.orange, b: 1 })],
  [tcell("提示词优化"), tcell("对比标准答案"), tcell("提示词"), tcell("0.715"), tcell("0.707"), tcell("1"), tcell("7/7")],
  [tcell("判定源反馈记忆·交互式", { fill: C.goodtint, b: 1, color: C.white }), tcell("对比标准答案", { fill: C.goodtint }), tcell("记忆", { fill: C.goodtint, b: 1 }), tcell("0.813", { fill: C.goodtint, color: C.green, b: 1 }), tcell("0.813", { fill: C.goodtint, color: C.green, b: 1 }), tcell("2", { fill: C.goodtint }), tcell("7/7", { fill: C.goodtint, color: C.green, b: 1 })],
  [tcell("判定源反馈记忆·自动脚本", { fill: C.goodtint, b: 1, color: C.white }), tcell("对比标准答案", { fill: C.goodtint }), tcell("记忆", { fill: C.goodtint, b: 1 }), tcell("0.789", { fill: C.goodtint, color: C.green, b: 1 }), tcell("0.833", { fill: C.goodtint, color: C.green, b: 1 }), tcell("2", { fill: C.goodtint }), tcell("6/7", { fill: C.goodtint, color: C.green, b: 1 })],
], { x: LEFT, y: 1.95, w: MW, h: 2.5, colW: [2.9, 2.3, 1.3, 1.3, 1.1, 1.6, 1.6], rowH: [0.4, 0.36, 0.36, 0.36, 0.36, 0.36], border: { pt: 0.75, color: C.line }, valign: "middle", fontSize: 12 });
box(s, LEFT, 4.62, 5.9, 1.35, "读法", null, "*自省记忆真召回失败=18 低于基线 27 是过度拆分噪声；探针 1/7 才是真相——真正该学的一条没学会。");
box(s, LEFT + 6.2, 4.62, 5.9, 1.35, "一句话", null, "同一记忆机制，把内容从「无判定源自省」换成「有判定源反馈」，探针 1/7 → 7/7。", { labelColor: C.green });
footer(s, "数据 / 脚本见仓库 dashjim/agentcore-memory-loop（db 已 gitignore）。", 11);

// ===== 12 LIMITS =====
s = p.addSlide(); base(s, "LIMITS & TAKEAWAY");
title(s, "能说什么，不能说什么", "结论方向可信，但边界要讲清——这也是「诚实实验」的一部分。");
box(s, LEFT, 2.1, 5.9, 2.3, "能说", null, "· 记忆注入机制有效（这条回路证明）\n· 瓶颈是记忆内容质量，取决于判定源\n· 标准答案 / 人类 / 大模型反馈都能兑现增益\n· 提示词 / schema 是漏抽的真因，改得动", { fill: C.goodtint, labelColor: C.green });
box(s, LEFT + 6.2, 2.1, 5.9, 2.3, "不能说 / 局限", null, "· 单文档、小样本、高方差（覆盖率 0.55–0.81 跳）→ 幅度不强断\n· 泛化未测（未做留出文档评估）\n· 裁判未经人工校准；有测量口径背离\n· V1 曾因评分 bug 误判，已修正", { labelColor: C.orange });
rect(s, LEFT, 4.65, MW, 1.3, C.card);
s.addText([
  R("记忆能让 agent 越跑越好——但前提是回路里有判定源把「对错 / 该抽什么」喂进来。", { fontSize: 16, color: C.body, align: "center" }),
  R("记忆负责捕获并复用反馈；它是好的载体，不是好的老师。", { fontSize: 16, bold: true, color: C.bblue, align: "center" }),
], { x: LEFT + 0.3, y: 4.65, w: MW - 0.6, h: 1.3, fontFace: FB, valign: "middle", margin: 0, lineSpacingMultiple: 1.25 });
footer(s, "复现自 AWS 博客 · 对应 LangChain Level-4 爬山循环（需判定源指明上坡方向）。", 12);

p.writeFile({ fileName: "docs/记忆能让Agent越跑越好吗.pptx" }).then(f => console.log("WROTE", f));
