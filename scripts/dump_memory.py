#!/usr/bin/env python3
"""导出 AgentCore Memory 全部内容为附件：docs/memory-dump.{md,json}。
custom(customMem)：list_events 读 strat 全局分区 + 各文档 tact 分区（原始事件=我们写入的规则）。
episodic(episodicMem)：retrieve_memory_records 读 /episodes/{actor} 的情节记录。
"""
import sys, json
from pathlib import Path
from datetime import datetime
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import boto3
from src import config, memory_tools as MT

REGION="us-west-2"; ACTOR="memory-loop"

# 脱敏：模型在情节反思里推断出的具体应用场景，公开前一般化处理（不改变技术内容）
_REDACT = {"卫星发射基地": "某工程项目", "卫星发射": "某工程"}
def _san(s):
    if not isinstance(s, str): return s
    for a, b in _REDACT.items(): s = s.replace(a, b)
    return s
dp=boto3.client("bedrock-agentcore", region_name=REGION)
dep=config.load_deployed(); CUS=dep["CUSTOM_MEMORY_ID"]; EPI=dep["EPISODIC_MEMORY_ID"]
DOCS=["150方液氮罐技术要求20240910(公开)(数量：2台)（令号：TP-2425、TP-2426）","2477080009简图-8.16"]

dump={"actor":ACTOR,"custom_memory_id":CUS,"episodic_memory_id":EPI,
      "custom":{"strat":[],"tact":{}}, "episodic":[]}

# custom: strat（全局）
s_sid=MT.strat_session(ACTOR)
dump["custom"]["strat"]=[{"sessionId":s_sid,"text":_san(t)} for t in MT._texts_from_events(MT._list_all_events(dp,CUS,ACTOR,s_sid))]
# custom: tact（按文档）
for d in DOCS:
    sid=MT.tact_session(ACTOR,d)
    txts=[_san(t) for t in MT._texts_from_events(MT._list_all_events(dp,CUS,ACTOR,sid))]
    dump["custom"]["tact"][d]={"sessionId":sid,"lessons":txts}
# episodic: 情节记录
r=dp.retrieve_memory_records(memoryId=EPI, namespace=f"/episodes/{ACTOR}",
    searchCriteria={"searchQuery":"液氮储罐 设备 部件 指标 抽取 经验 反思","topK":20})
recs=r.get("memoryRecordSummaries", r.get("memoryRecords", []))
for rec in recs:
    c=rec.get("content"); txt=c.get("text") if isinstance(c,dict) else (c if isinstance(c,str) else json.dumps(c,ensure_ascii=False,default=str))
    txt=_san(txt)
    dump["episodic"].append({"id":rec.get("memoryRecordId"),"namespaces":rec.get("namespaces"),
                             "score":rec.get("score"),"createdAt":str(rec.get("createdAt")),"content":txt})

Path("docs").mkdir(exist_ok=True)
json.dump(dump, open("docs/memory-dump.json","w"), ensure_ascii=False, indent=2, default=str)

# markdown
L=[]
L.append("# AgentCore Memory 内容导出（附件）\n")
L.append(f"> 真机导出自 us-west-2。actorId=`{ACTOR}`；customMem=`{CUS}`；episodicMem=`{EPI}`。\n")
L.append("## 一、自定义记忆 custom（我们自管的显式规则，list_events 读原始事件）\n")
L.append(f"### 战略记忆 M_strat（分区 sessionId=`{s_sid}`，共 {len(dump['custom']['strat'])} 条）\n")
for i,e in enumerate(dump["custom"]["strat"],1):
    L.append(f"**规则 {i}**：{e['text']}\n")
L.append("### 战术记忆 M_tact（按文档分区）\n")
for d,v in dump["custom"]["tact"].items():
    L.append(f"- 文档「{d[:30]}…」(sessionId=`{v['sessionId']}`)：{len(v['lessons'])} 条" + ("" if v["lessons"] else "（空）"))
    for t in v["lessons"]: L.append(f"  - {t}")
L.append("")
L.append(f"## 二、情节记忆 episodic（AgentCore EPISODIC 策略自动提炼，共 {len(dump['episodic'])} 条）\n")
for i,e in enumerate(dump["episodic"],1):
    L.append(f"### 情节 {i}（score={e['score']}）")
    try:
        obj=json.loads(e["content"])
        for k in ["situation","intent","assessment","justification","reflection"]:
            if k in obj: L.append(f"- **{k}**：{obj[k]}")
    except Exception:
        L.append(e["content"])
    L.append("")
Path("docs/memory-dump.md").write_text("\n".join(L), encoding="utf-8")
print("strat:",len(dump["custom"]["strat"]),"| tact docs:",{d[:12]:len(v["lessons"]) for d,v in dump["custom"]["tact"].items()},"| episodic:",len(dump["episodic"]))
print("写出 docs/memory-dump.md , docs/memory-dump.json")
