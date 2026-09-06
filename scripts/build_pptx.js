// 《记忆能让 Agent 越跑越好吗》PPTX —— AWS 深色风格（对齐参考 PPT）。
const pptxgen = require("pptxgenjs");
const p = new pptxgen();
p.defineLayout({ name: "W", width: 13.333, height: 7.5 });
p.layout = "W";
p.theme = { headFontFace: "Amazon Ember Display", bodyFontFace: "Microsoft YaHei" };

const C = {
  bg: "161E2D", bg2: "0B1220", card: "1C2740", card2: "222E45", line: "2E3B57",
  white: "FFFFFF", body: "CFD9E4", muted: "8496A8", lblue: "A8C7E8",
  blue: "0073E5", bblue: "42B4FF", orange: "FF6A3D", green: "00E500", purple: "B2A8FF",
  goodtint: "12331F", badtint: "35181C",
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
  if (lead) s.addText(lead, { x: LEFT, y: 1.12, w: MW, h: 0.62, fontFace: FB, fontSize: 14, color: C.body, margin: 0, lineSpacingMultiple: 1.15 });
}
function footer(s, note, n) {
  if (note) s.addText(note, { x: LEFT, y: 6.72, w: 10.6, h: 0.5, fontFace: FB, fontSize: 10.5, color: C.muted, margin: 0, lineSpacingMultiple: 1.1, valign: "top" });
  s.addText("亚马逊云科技", { x: LEFT, y: 7.08, w: 3, h: 0.3, fontFace: FH, fontSize: 11, bold: true, color: C.lblue, margin: 0 });
  s.addText(String(n), { x: 12.5, y: 7.05, w: 0.5, h: 0.3, fontFace: FH, fontSize: 11, color: C.muted, align: "right", margin: 0 });
}
function rect(s, x, y, w, h, fill) { s.addShape(p.ShapeType.roundRect, { x, y, w, h, rectRadius: 0.09, fill: { color: fill || C.card }, line: { color: C.line, width: 0.75 } }); }
function T(s, txt, o) { s.addText(txt, { fontFace: FB, margin: 0, valign: "top", ...o }); }
// 编号行卡片：左侧彩色数字圆 + 标题 + 描述
function rowCard(s, x, y, w, h, num, head, desc, accent) {
  rect(s, x, y, w, h, C.card);
  const cx = x + 0.22, cy = y + h / 2 - 0.26;
  s.addText(String(num), { x: cx, y: cy, w: 0.52, h: 0.52, shape: p.ShapeType.ellipse, fill: { color: accent || C.blue }, color: C.white, align: "center", valign: "middle", fontFace: FH, fontSize: 17, bold: true, margin: 0 });
  const tx = x + 0.95;
  s.addText(head, { x: tx, y: y + 0.16, w: w - 1.1, h: 0.34, fontFace: FB, fontSize: 16, bold: true, color: accent === C.orange ? C.orange : C.white, margin: 0 });
  s.addText(desc, { x: tx, y: y + 0.52, w: w - 1.1, h: h - 0.62, fontFace: FB, fontSize: 13, color: C.body, margin: 0, lineSpacingMultiple: 1.12 });
}
// 竖排卡片：小标签 + 标题 + 正文
function box(s, x, y, w, h, label, head, body, o = {}) {
  rect(s, x, y, w, h, o.fill || C.card);
  let yy = y + 0.16;
  if (label) { s.addText(label, { x: x + 0.22, y: yy, w: w - 0.4, h: 0.3, fontFace: FH, fontSize: 12, bold: true, color: o.labelColor || C.bblue, margin: 0 }); yy += 0.34; }
  if (head) { s.addText(head, { x: x + 0.22, y: yy, w: w - 0.4, h: 0.36, fontFace: FB, fontSize: 16.5, bold: true, color: C.white, margin: 0 }); yy += 0.44; }
  if (body) s.addText(body, { x: x + 0.22, y: yy, w: w - 0.44, h: y + h - yy - 0.12, fontFace: FB, fontSize: 13, color: C.body, margin: 0, lineSpacingMultiple: 1.15, valign: "top" });
}
function darkbar(s, x, y, w, h, runs) { rect(s, x, y, w, h, C.bg2); s.addText(runs, { x: x + 0.05, y, w: w - 0.4, h, fontFace: FB, valign: "middle", align: "left", margin: [8, 16, 8, 16], lineSpacingMultiple: 1.18 }); }
function code(s, x, y, w, h, txt) { rect(s, x, y, w, h, C.bg2); s.addText(txt, { x: x + 0.05, y, w: w - 0.2, h, fontFace: FM, fontSize: 11.5, color: C.body, align: "left", valign: "top", margin: [8, 12, 8, 12], lineSpacingMultiple: 1.15 }); }
function R(text, o = {}) { return { text, options: { fontFace: FB, breakLine: true, ...o } }; }
function tcell(text, o = {}) { return { text, options: { fontFace: FB, fontSize: o.fs || 12.5, bold: !!o.b, color: o.color || C.body, fill: { color: o.fill || C.card }, align: o.align || "left", valign: "middle" } }; }
function stat(s, x, y, big, lbl, cap) {
  s.addText(big, { x, y, w: 5.4, h: 0.62, fontFace: FH, fontSize: 34, bold: true, color: C.bblue, margin: 0 });
  s.addText(lbl, { x, y: y + 0.6, w: 5.4, h: 0.3, fontFace: FB, fontSize: 14, bold: true, color: C.white, margin: 0 });
  if (cap) s.addText(cap, { x, y: y + 0.9, w: 5.4, h: 0.3, fontFace: FB, fontSize: 11.5, color: C.muted, margin: 0 });
}

// ============ 1 TITLE ============
let s = p.addSlide(); s.background = { color: C.bg };
s.addImage({ path: BAR, x: 0, y: 0, w: 0.16, h: 7.5 });
s.addText("AGENTCORE MEMORY · 诚实实验", { x: 0.75, y: 1.35, w: 11, h: 0.4, fontFace: FH, fontSize: 14, bold: true, color: C.bblue, charSpacing: 4, margin: 0 });
s.addText("记忆能让 AI Agent\n越跑越好吗？", { x: 0.72, y: 1.8, w: 11.8, h: 1.75, fontFace: FH, fontSize: 46, bold: true, color: C.white, margin: 0, lineSpacingMultiple: 1.05 });
s.addText("在工业技术文档抽取任务上，用单变量实验验证「长期记忆是否带来自学习」——并给出记忆使用的最佳实践。", { x: 0.75, y: 3.65, w: 11, h: 0.5, fontFace: FB, fontSize: 17, color: C.body, margin: 0 });
rect(s, 0.75, 4.35, 11.1, 1.35, C.card);
s.addText([
  R("能。就算没人干预，记忆也能靠对照原文的自我批评学到一些；但真正的飞跃，需要回路里有一个判定源（判定对错 / 该抽什么的外部权威）。", { fontSize: 16, color: C.body }),
  R("记忆是好的载体，不是好的老师。", { fontSize: 16, bold: true, color: C.bblue }),
], { x: 1.0, y: 4.35, w: 10.6, h: 1.35, fontFace: FB, valign: "middle", margin: 0, lineSpacingMultiple: 1.25 });
s.addText("复现自 AWS 博客《Self-learning evolvable agents … with AgentCore》 · us-west-2 · 场景：低温液氮储罐技术要求抽取", { x: 0.75, y: 6.05, w: 11.5, h: 0.4, fontFace: FB, fontSize: 12, color: C.muted, margin: 0 });
s.addText("亚马逊云科技", { x: 0.75, y: 7.02, w: 4, h: 0.3, fontFace: FH, fontSize: 12, bold: true, color: C.lblue, margin: 0 });

// ============ 2 WHY ============
s = p.addSlide(); base(s, "WHY");
title(s, "一个所有做 Agent 的人都会问的问题", "给 agent 加长期记忆，它会不会「越用越聪明」？用可测量的方式回答，并给出最佳实践。");
box(s, LEFT, 2.0, 3.72, 2.0, "直觉", "记忆 = 自学习", "把过去经验记下、下次复用，agent 应该越跑越好。几乎所有人的默认假设。");
box(s, 4.5, 2.0, 3.72, 2.0, "现实", "没那么简单", "第一版「看起来」验证了直觉——但那是评分 bug 的假象。修正后增益消失。");
box(s, 8.38, 2.0, 3.72, 2.0, "真相", "关键在存什么", "记忆能变好多少，取决于往里存什么；而能存到「该抽什么」这类关键反馈，取决于有没有判定源。", { labelColor: C.orange });
darkbar(s, LEFT, 4.35, MW, 1.7, [
  R("主线：记忆机制是好的。没判定源时，靠对照原文的自我批评它也能救回一部分漏项（无标准答案也救回 4–10 条）；但只做抽象自省，够不着「该抽什么」这类关键问题。", { fontSize: 15, color: C.body }),
  R("一旦存进判定源质量的反馈，同一套机制立刻突飞猛进（探针 1/7 → 7/7）。", { fontSize: 15, bold: true, color: C.bblue }),
]);
footer(s, "", 2);

// ============ 3 SETUP ============
s = p.addSlide(); base(s, "SETUP");
title(s, "单变量实验：唯一变量 = 记忆开 / 关", "从 13 页中文工业文档抽 设备主体·部件·指标名称·指标特征·原文，对比人工标注的标准答案（123 条）。其余全一样，只切记忆。");
let fx = LEFT, fy = 2.1; const fw = 2.05;
function nd(x, y, w, txt, o = {}) { s.addText(txt, { x, y, w, h: 0.72, shape: p.ShapeType.roundRect, rectRadius: 0.06, fill: { color: o.bg || C.card }, line: { color: o.bd || C.line, width: 1 }, align: "center", valign: "middle", fontFace: FB, fontSize: 12, bold: true, color: o.color || C.white, margin: 2 }); }
function ar(x, y) { s.addText("→", { x, y, w: 0.38, h: 0.72, align: "center", valign: "middle", fontFace: FH, fontSize: 18, bold: true, color: C.bblue }); }
nd(fx, fy, fw, "工业文档\n(13页)"); ar(fx + fw, fy);
nd(fx + fw + 0.38, fy, fw, "Agent\n(AgentCore Harness)"); ar(fx + 2 * fw + 0.38, fy);
nd(fx + 2 * fw + 0.76, fy, fw, "结构化 JSON"); ar(fx + 3 * fw + 0.76, fy);
nd(fx + 3 * fw + 1.14, fy, fw, "LLM 裁判\n对比标准答案"); ar(fx + 4 * fw + 1.14, fy);
nd(fx + 4 * fw + 1.52, fy, fw, "覆盖率/精确率/F1");
nd(4.9, fy + 1.0, 3.6, "记忆　开 or 关　←　唯一变量", { bg: "2A2418", bd: C.orange, color: C.orange });
const my = 4.05, mh = 1.95, mw = 2.9;
box(s, LEFT, my, mw, mh, "指标①", "覆盖率(召回)", "抽出的覆盖了多少标准答案。");
box(s, LEFT + 3.02, my, mw, mh, "指标②", "精确率", "抽出的里多少对，惩罚乱抽 / 过度拆分。");
box(s, LEFT + 6.04, my, mw, mh, "指标③", "F1", "前两者调和平均，综合看。");
box(s, LEFT + 9.06, my, 3.04, mh, "诊断", "真召回失败", "某条标准答案与任何抽取项零重叠 = 根本没抽出来。全篇关键。", { labelColor: C.orange });
footer(s, "", 3);

// ============ 4 ROADMAP ============
s = p.addSlide(); base(s, "ROADMAP");
title(s, "我们分四步查下去", "有了「记忆开 / 关」这个单变量设置，下面每一步都由上一步的结果逼出来——先破后立：先弄清它为什么没用，再弄清怎么才有用。");
const ry = 2.5, rh = 2.1, rw = 2.9;
function rstep(x, n, h4, body, ptr, accent) {
  box(s, x, ry, x >= LEFT + 9 ? 3.04 : rw, rh, n, h4, body, accent ? { labelColor: C.orange } : {});
  s.addText(ptr, { x: x + 0.22, y: ry + rh - 0.42, w: (x >= LEFT + 9 ? 3.04 : rw) - 0.4, h: 0.32, fontFace: FB, fontSize: 12, color: C.muted, margin: 0 });
}
rstep(LEFT, "第 1 步", "先验尺子", "第一版\"看起来有效\"——但真的吗？先怀疑度量本身。", "→ 见「第一版骗了我们」");
rstep(LEFT + 3.02, "第 2 步", "诊断漏了什么", "打平之后不急着下结论，先看漏抽有没有规律。", "→ 见「为什么没用」");
rstep(LEFT + 6.04, "第 3 步", "三个实验", "A 改提示词 · C 反馈写进记忆 · B 对照。锁定因果。", "→ 本文的核心", true);
rstep(LEFT + 9.06, "第 4 步", "收束", "提炼「判定源」这个关键概念，给出记忆使用最佳实践。", "→ 见「最佳实践」");
darkbar(s, LEFT, 4.95, MW, 1.0, [R("全文只回答一个问题：记忆能不能让 agent 越跑越好？答案藏在\"记忆里到底存什么\"里。", { fontSize: 16, bold: true, color: C.bblue })]);
footer(s, "三个实验共用同一抽取器与评分，唯一变量是记忆内容——单变量可比。", 4);

// ============ 5 PITFALL ============
s = p.addSlide(); base(s, "PITFALL");
title(s, "覆盖率「越跑越高」——其实是假象", "第一轮带记忆的覆盖率 0.82→0.87，像自学习曲线。幸好多问了一句：这把尺子准吗？");
box(s, LEFT, 2.05, 5.9, 2.35, "问题一 · 评分 bug", "裁判会重复计分", "分块打分缺全局约束，同一抽取项被重复算去匹配多条标准答案，系统性高估覆盖率。\n\n铁证：某次只抽 91 条，却报匹配 94 条——94>91 一对一不可能。", { fill: C.badtint });
box(s, LEFT + 6.2, 2.05, 5.9, 2.35, "问题二 · 对比混淆", "比的不是同一个东西", "那个「好」的记忆模式偷偷用了更强的抽取器，还没冷启动。\n\n它冷启动（记忆还空着）就已领先——领先跟记忆无关。", { fill: C.badtint });
darkbar(s, LEFT, 4.75, MW, 1.15, [R("修好评分 + 拉平变量 + 冷启动重跑后：记忆增益消失。", { fontSize: 15.5, bold: true, color: C.white }), R("教训一：先怀疑自己的尺子——没校准的乐观结果，比没有结果更危险。", { fontSize: 15, color: C.body })]);
footer(s, "", 5);

// ============ 6 DIAGNOSIS ============
s = p.addSlide(); base(s, "DIAGNOSIS");
title(s, "不下「记忆无效」的结论，先做错误分析", "把漏抽的标准答案全捞出来分类：约 3/4 是「真召回失败」——根本没抽出来。这些漏项高度同质。");
box(s, LEFT, 2.05, 5.9, 2.5, "漏项长什么样", "都不是「指标+数值」", "· 外观颜色及喷涂 LOGO 须与甲方确认\n· 真空度测量报告 / 真空度测量要求\n· 外部油漆等工序\n· 承制单位细化设计…提供全套地脚螺栓\n\n全是离散文字式、流程式、待确认类要求。");
box(s, LEFT + 6.2, 2.05, 5.9, 2.5, "根因", "schema 让模型「以为不该抽」", "抽取 schema 天生面向定量指标。模型看到没有数值、只有要求的话，就默认「这不是一条指标」直接跳过。\n\n漏的不是模型能力，是它以为这些不该抽。", { labelColor: C.orange });
darkbar(s, LEFT, 4.9, MW, 1.05, [R("教训二：「没效果」往往不是终点，而是一个还没做的错误分析。不做归因，就会把「任务定义问题」误判成「方法无效」。", { fontSize: 15, color: C.body })]);
footer(s, "", 6);

// ============ 7 EXPERIMENT A ============
s = p.addSlide(); base(s, "EXPERIMENT · A");
title(s, "教训写进提示词 —— 有效，但用到了标准答案", "只显式加：非定量要求也要抽，「要求类型」放指标名称、「要求内容」放指标特征。");
s.addTable([
  [tcell("　", { fill: C.bg2 }), tcell("覆盖率", { b: 1, fill: C.blue, color: C.white }), tcell("真召回失败", { b: 1, fill: C.blue, color: C.white }), tcell("离散文字探针 (命中/共7)", { b: 1, fill: C.blue, color: C.white })],
  [tcell("基线（无此提示）"), tcell("0.642"), tcell("27", { color: C.orange, b: 1 }), tcell("1 / 7")],
  [tcell("加了提示词", { b: 1, fill: C.goodtint }), tcell("0.715", { fill: C.goodtint }), tcell("1", { color: C.green, b: 1, fill: C.goodtint }), tcell("7 / 7", { color: C.green, b: 1, fill: C.goodtint })],
], { x: LEFT, y: 1.95, w: MW, h: 1.0, colW: [3.7, 2.8, 2.8, 2.8], border: { pt: 0.75, color: C.line }, valign: "middle" });
box(s, LEFT, 3.15, MW, 1.35, "为什么真召回失败崩到 1、覆盖率只 +0.07？—— 两把尺量两件事", null,
  "真召回失败=松尺（有没有\"沾边\"抽到）→ 模型开始抽离散文字类，几乎每条都沾边，近乎归零；覆盖率=严尺（裁判一对一干净对齐）→ 受\"粒度对不齐 + 多抽拉低精确率(0.70)\"限制。即已从\"整类视而不见\"→\"基本抽到、只是粒度没对齐\"，+0.07 低估了真实进步。");
box(s, LEFT, 4.7, 5.9, 1.3, "结果", null, "证明是任务定义问题，改得动——不是方法无效。", { fill: C.goodtint, labelColor: C.green });
box(s, LEFT + 6.2, 4.7, 5.9, 1.3, "真正该问的", null, "现实里反馈不缺（人类纠正 / 大模型对比标准答案）。这种反馈被记忆捕获后，实际有效吗？", { labelColor: C.orange });
footer(s, "", 7);

// ============ 8 EXPERIMENT C ============
s = p.addSlide(); base(s, "EXPERIMENT · C");
title(s, "大模型对比标准答案产出反馈 → 写进记忆 —— 有效", "让大模型对比「抽取结果」与「标准答案」产出可迁移反馈（规则性指引，不照抄答案），写进记忆，基线提示词重抽。标准答案只进检查器，不进抽取器。");
fx = LEFT; fy = 2.4; const cw = 2.05;
nd(fx, fy, cw, "基线抽取"); ar(fx + cw, fy);
nd(fx + cw + 0.35, fy, cw, "大模型检查器\n对比标准答案产反馈", { bd: C.bblue, color: C.bblue }); ar(fx + 2 * cw + 0.35, fy);
nd(fx + 2 * cw + 0.7, fy, cw, "写进记忆", { bg: "2A2418", bd: C.orange, color: C.orange }); ar(fx + 3 * cw + 0.7, fy);
nd(fx + 3 * cw + 1.05, fy, cw, "注入 · 重抽"); ar(fx + 4 * cw + 1.05, fy);
nd(fx + 4 * cw + 1.4, fy, cw, "探针 7/7", { bg: C.goodtint, bd: C.green, color: C.green });
s.addTable([
  [tcell("　", { fill: C.bg2 }), tcell("覆盖率", { b: 1, fill: C.blue, color: C.white }), tcell("精确率", { b: 1, fill: C.blue, color: C.white }), tcell("F1", { b: 1, fill: C.blue, color: C.white }), tcell("真召回失败", { b: 1, fill: C.blue, color: C.white }), tcell("离散文字", { b: 1, fill: C.blue, color: C.white })],
  [tcell("基线"), tcell("0.642"), tcell("–"), tcell("–"), tcell("27"), tcell("1 / 7")],
  [tcell("大模型反馈写进记忆", { b: 1, fill: C.goodtint }), tcell("0.813", { color: C.green, b: 1, fill: C.goodtint }), tcell("0.813", { fill: C.goodtint }), tcell("0.813", { color: C.green, b: 1, fill: C.goodtint }), tcell("2", { fill: C.goodtint }), tcell("7 / 7", { color: C.green, b: 1, fill: C.goodtint })],
], { x: LEFT, y: 3.5, w: MW, h: 1.0, border: { pt: 0.75, color: C.line }, valign: "middle" });
darkbar(s, LEFT, 4.75, MW, 1.2, [R("这正是真实回路的缩影：大模型（或人类）对比目标给反馈 → 记忆捕获 → 下一次直接受益。目前最好的一次。", { fontSize: 14.5, color: C.body }), R("两种实例结论一致：交互式 F1 0.813、自动检查器脚本 cov 0.789 / F1 0.833 / 探针 6/7。", { fontSize: 14, color: C.muted })]);
footer(s, "", 8);

// ============ 9 EXPERIMENT B ============
s = p.addSlide(); base(s, "EXPERIMENT · B");
title(s, "换成「记忆自省」、没有反馈 —— 学不到", "为确认增益来自反馈内容、而非「塞了更多字」：让模型反思自己的输出、蒸馏成规则（全程无标准答案、无反馈）。这正是我们最初的记忆设计。");
box(s, LEFT, 2.4, 5.9, 2.2, "实验 B · 无判定源", "探针纹丝不动，钉死 1 / 7", "模型只看自己的产出，没有信号告诉它「离散文字类也算数」。蒸馏出的只是通用文风规则（\"复合指标要拆分\"），碰不到真问题，还因过度拆分帮倒忙。", { fill: C.badtint });
rect(s, LEFT + 6.2, 2.4, 5.9, 2.2, C.card);
s.addText("决定性对照 · 同机制只变内容", { x: LEFT + 6.42, y: 2.56, w: 5.4, h: 0.3, fontFace: FH, fontSize: 12, bold: true, color: C.bblue, margin: 0 });
s.addText([
  R("自省规则（无判定源）　→　探针 1 / 7", { fontSize: 15, bold: true, color: C.orange }),
  R("大模型反馈（有判定源）　→　探针 7 / 7", { fontSize: 15, bold: true, color: C.green }),
  R("注入路径完全相同（都是记忆），唯一差别是内容质量。", { fontSize: 13, color: C.body }),
], { x: LEFT + 6.42, y: 3.0, w: 5.45, h: 1.5, fontFace: FB, margin: 0, valign: "top", lineSpacingMultiple: 1.3 });
darkbar(s, LEFT, 4.75, MW, 1.2, [R("因果锁定：记忆的注入机制一直是好的。之前记忆在这条教训上没起作用，是因为「无判定源自省」够不着「该抽什么」——它产出的是通用文风规则；换成判定源质量的反馈，记忆一把兑现全部增益。", { fontSize: 14.5, color: C.body })]);
footer(s, "", 9);

// ============ 10 判定源 ============
s = p.addSlide(); base(s, "KEY CONCEPT");
title(s, "什么是判定源，为什么是它说了算", "判定源 = 能告诉 agent「对不对 / 该抽什么」的外部权威。核心：它提供的信息，从输入本身推不出来，必须外部给。");
s.addTable([
  [tcell("判定源形式", { b: 1, fill: C.blue, color: C.white }), tcell("告诉 agent 什么", { b: 1, fill: C.blue, color: C.white })],
  [tcell("标准答案"), tcell("这篇「应该」抽出哪些")],
  [tcell("人类反馈", { b: 1, color: C.white }), tcell("「这类也要抽」/「这条错了」")],
  [tcell("大模型对比标准答案 / 规范检查", { b: 1, color: C.white }), tcell("按规范判对错、漏了哪类")],
  [tcell("下游验证"), tcell("参数拿去用报错 → 抽错了")],
], { x: LEFT, y: 2.15, w: 6.5, h: 2.35, border: { pt: 0.75, color: C.line }, valign: "middle", fontSize: 13 });
box(s, LEFT + 6.7, 2.15, 5.4, 1.12, "任务规格类教训", null, "该抽什么 / 粒度 / 什么算一条——必须判定源。从「文档+自己输出」推不出。本实验决定成败的就是这类。", { labelColor: C.orange });
box(s, LEFT + 6.7, 3.38, 5.4, 1.12, "源覆盖 / 一致性类教训", null, "漏了原文里的 X / 重复 / 格式错——对照原文即可，无判定源也能学一点（天花板低）。");
darkbar(s, LEFT, 4.75, MW, 0.95, [R("记忆不产生新知识，它只搬运。搬运什么，取决于回路里的判定源。", { fontSize: 17, bold: true, color: C.bblue, align: "center" })]);
footer(s, "标准答案只是其中一种；后三种在真实系统里很常见。", 10);

// ============ 11 MEMORY ============
s = p.addSlide(); base(s, "MEMORY");
title(s, "坏记忆 vs 好记忆：内容差在哪", "同样是写进记忆的文本，一个学不到、一个全学会——差别一眼可见。");
rect(s, LEFT, 2.05, 5.9, 2.35, C.card);
s.addText("实验B · 自省产出（15 条节选）", { x: LEFT + 0.22, y: 2.18, w: 5.5, h: 0.3, fontFace: FH, fontSize: 12, bold: true, color: C.orange, margin: 0 });
code(s, LEFT + 0.22, 2.52, 5.45, 1.1, "5. 多部件拆分规则：按部件逐条拆分…\n6. 复合指标拆分规则：按指标逐条拆分…\n9. 阀门 / 仪表：规格与数量各一条…");
s.addText("全是通用文风 / 粒度规则，没一条说「该抽离散文字类」——它不知道自己漏了这类。", { x: LEFT + 0.22, y: 3.68, w: 5.45, h: 0.6, fontFace: FB, fontSize: 12.5, color: C.body, margin: 0, lineSpacingMultiple: 1.1 });
rect(s, LEFT + 6.2, 2.05, 5.9, 2.35, C.card);
s.addText("实验C · 对比标准答案的反馈", { x: LEFT + 6.42, y: 2.18, w: 5.5, h: 0.3, fontFace: FH, fontSize: 12, bold: true, color: C.green, margin: 0 });
code(s, LEFT + 6.42, 2.52, 5.45, 1.35, "【质检反馈·务必逐条应用】\n1. 非定量要求也要抽 → 映射进字段\n2. 覆盖易漏类别：真空度 / 无损检测 /\n   环境 / 受压 / 阀门 / 管口 / 材料\n3. 粒度对齐：默认一原文一记录");
s.addText("指名了漏抽的类别——这是标准答案才能给的信号。", { x: LEFT + 6.42, y: 3.95, w: 5.45, h: 0.4, fontFace: FB, fontSize: 12.5, color: C.body, margin: 0 });
darkbar(s, LEFT, 4.7, MW, 1.1, [R("Memory 类型：用 AgentCore 自定义记忆当事件存储（create_event 写 / list_events 精确即时读，不走异步策略），存在固定分区 canon-{actorId}，注入时逐字拼进 system prompt。", { fontSize: 13.5, color: C.body })]);
footer(s, "真实导出自 us-west-2。", 11);

// ============ 12 PROMPTS ============
s = p.addSlide(); base(s, "PROMPTS");
title(s, "「教训」和「检查器」的真实提示词", "抽象说了半天，直接看真东西：写进提示词的那条教训（含真实示例），以及产出它的检查器。");
rect(s, LEFT, 2.05, 5.9, 2.6, C.card);
s.addText("实验 A：写进提示词的「教训」（真实原文·节选）", { x: LEFT + 0.22, y: 2.18, w: 5.5, h: 0.3, fontFace: FH, fontSize: 12, bold: true, color: C.orange, margin: 0 });
code(s, LEFT + 0.22, 2.52, 5.45, 1.95, "非定量要求也要抽：定性 / 流程 / 待确认类，\n「要求类型」→指标名称、「要求内容」→指标特征。\n示例（真实漏项）：\n外观颜色须与甲方确认\n  → 名称=外观颜色确认；特征=须与甲方确认\n真空度测量报告\n  → 名称=真空度测量；特征=需测量并提供报告");
rect(s, LEFT + 6.2, 2.05, 5.9, 2.6, C.card);
s.addText("产出它的「检查器」提示词（实验C）", { x: LEFT + 6.42, y: 2.18, w: 5.5, h: 0.3, fontFace: FH, fontSize: 12, bold: true, color: C.green, margin: 0 });
code(s, LEFT + 6.42, 2.52, 5.45, 1.7, "你是抽取质检专家。给你【抽取结果】\n和【标准答案】。对比两者，产出\n可迁移改进反馈（≤10 条）：\n ① 系统性漏抽的类别；② 粒度问题；\n ③ 规则性纠正指引。不要照抄答案。");
darkbar(s, LEFT, 4.9, MW, 1.05, [R("输入里有标准答案 ← 它才能指出\"漏了哪类\"。这是与实验 B 自省（无标准答案）的唯一关键差别。完整全文见 blog 附录 D。", { fontSize: 14, color: C.body })]);
footer(s, "", 12);

// ============ 13 BEST PRACTICE ============
s = p.addSlide(); base(s, "BEST PRACTICE");
title(s, "怎么用记忆，才能真的越跑越好", "记忆负责「捕获并复用」反馈，反馈本身必须由判定源提供。落到工程上四条。");
const by = 2.15, bh = 1.9, bw = 5.9;
rowCard(s, LEFT, by, bw, bh, 1, "先确保回路里有判定源", "没有「对错/目标」的外部信号，记忆再多也原地打转。判定源不必是完整标准答案——一次人类纠正、少量标注、带 rubric 的裁判都行。", C.blue);
rowCard(s, LEFT + 6.2, by, bw, bh, 2, "存「具体批评」，别存「抽象规则」", "「你漏了真空度测量这一段」有用；「复合指标要拆分」空洞，还诱发过度拆分反噬。记忆要对照答案/原文，指名道姓。", C.blue);
rowCard(s, LEFT, by + bh + 0.2, bw, bh, 3, "判定源可以只用一次", "用少量标准答案做一次错误分析，把结论沉淀成可复用记忆，之后无标注地跑。用少量监督撬动长期收益，最划算。", C.blue);
rowCard(s, LEFT + 6.2, by + bh + 0.2, bw, bh, 4, "分清想学哪类教训", "任务规格类必须判定源；源覆盖 / 一致性类对照原文即可，无判定源也能学一点（天花板低）。", C.orange);
footer(s, "记忆是好的载体，不是好的老师。", 13);

// ============ 14 DATA ============
s = p.addSlide(); base(s, "DATA");
title(s, "四种回路放同一把尺", "看离散文字探针这一列就够——它是任务规格类教训的探针：只有引入判定源才从 1/7 跳到 7/7。");
const hd = { b: 1, fill: C.blue, color: C.white, fs: 12 };
s.addTable([
  [tcell("回路", hd), tcell("教训来源", hd), tcell("教训放哪", hd), tcell("覆盖率", hd), tcell("F1", hd), tcell("真召回失败", hd), tcell("离散文字探针", hd)],
  [tcell("基线（无记忆）"), tcell("—"), tcell("—"), tcell("0.642"), tcell("–"), tcell("27"), tcell("1/7")],
  [tcell("自省记忆", { fill: C.badtint }), tcell("自省·无判定源", { fill: C.badtint }), tcell("记忆", { fill: C.badtint }), tcell("0.561", { fill: C.badtint }), tcell("–", { fill: C.badtint }), tcell("18*", { fill: C.badtint }), tcell("1/7", { fill: C.badtint, color: C.orange, b: 1 })],
  [tcell("提示词优化"), tcell("对比标准答案"), tcell("提示词"), tcell("0.715"), tcell("0.707"), tcell("1"), tcell("7/7")],
  [tcell("大模型反馈记忆·交互式", { fill: C.goodtint, b: 1, color: C.white }), tcell("对比标准答案", { fill: C.goodtint }), tcell("记忆", { fill: C.goodtint, b: 1 }), tcell("0.813", { fill: C.goodtint, color: C.green, b: 1 }), tcell("0.813", { fill: C.goodtint, color: C.green, b: 1 }), tcell("2", { fill: C.goodtint }), tcell("7/7", { fill: C.goodtint, color: C.green, b: 1 })],
  [tcell("大模型反馈记忆·自动脚本", { fill: C.goodtint, b: 1, color: C.white }), tcell("对比标准答案", { fill: C.goodtint }), tcell("记忆", { fill: C.goodtint, b: 1 }), tcell("0.789", { fill: C.goodtint, color: C.green, b: 1 }), tcell("0.833", { fill: C.goodtint, color: C.green, b: 1 }), tcell("2", { fill: C.goodtint }), tcell("6/7", { fill: C.goodtint, color: C.green, b: 1 })],
], { x: LEFT, y: 1.95, w: MW, h: 2.5, colW: [2.9, 2.3, 1.3, 1.3, 1.1, 1.6, 1.6], rowH: [0.4, 0.36, 0.36, 0.36, 0.36, 0.36], border: { pt: 0.75, color: C.line }, valign: "middle", fontSize: 12 });
box(s, LEFT, 4.62, 5.9, 1.35, "读法", null, "*自省记忆真召回失败=18 低于基线 27 是过度拆分噪声；探针 1/7 才是真相——真正该学的一条没学会。");
box(s, LEFT + 6.2, 4.62, 5.9, 1.35, "一句话", null, "同一记忆机制，把内容从「无判定源自省」换成「有判定源反馈」，探针 1/7 → 7/7。", { labelColor: C.green });
footer(s, "数据 / 脚本见仓库 dashjim/agentcore-memory-loop（db 已 gitignore）。", 14);

// ============ 15 LIMITS ============
s = p.addSlide(); base(s, "LIMITS & TAKEAWAY");
title(s, "能说什么，不能说什么", "结论方向可信，但边界要讲清——这也是「诚实实验」的一部分。");
box(s, LEFT, 2.1, 5.9, 2.3, "能说", null, "· 记忆注入机制有效（实验 C 证明）\n· 瓶颈是记忆内容质量，取决于判定源\n· 用标准答案 / 人类 / 大模型反馈都能兑现增益\n· 提示词 / schema 是漏抽的真因，改得动", { fill: C.goodtint, labelColor: C.green });
box(s, LEFT + 6.2, 2.1, 5.9, 2.3, "不能说 / 局限", null, "· 单文档、小样本、高方差（覆盖率 0.55–0.81 跳）→ 幅度不强断\n· 泛化未测（未做留出文档评估）\n· 裁判未经人工校准；有测量口径背离\n· 需多文档盲测 + 多 seed + CI 严格验证", { labelColor: C.orange });
rect(s, LEFT, 4.65, MW, 1.3, C.card);
s.addText([
  R("记忆能让 agent 越跑越好——但前提是回路里有判定源把「对错 / 该抽什么」喂进来。", { fontSize: 16, color: C.body, align: "center" }),
  R("记忆负责捕获并复用反馈；它是好的载体，不是好的老师。", { fontSize: 16, bold: true, color: C.bblue, align: "center" }),
], { x: LEFT + 0.3, y: 4.65, w: MW - 0.6, h: 1.3, fontFace: FB, valign: "middle", margin: 0, lineSpacingMultiple: 1.25 });
footer(s, "复现自 AWS 博客 · 对应 LangChain Level-4 爬山循环（需判定源指明上坡方向）。", 15);

p.writeFile({ fileName: "docs/记忆能让Agent越跑越好吗.pptx" }).then(f => console.log("WROTE", f));
