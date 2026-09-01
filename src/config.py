"""集中式配置：固定常量 + 从环境变量/部署产物宽容读取资源标识。

- 区域固定 us-west-2。
- 资源 ID（HARNESS_ARN / EPISODIC_MEMORY_ID / CUSTOM_MEMORY_ID）在部署前不存在，
  因此本模块提供占位值并允许注入，便于单测与本地开发。
"""
import json
import os
from pathlib import Path

# ---- 固定常量 ----
REGION = "us-west-2"
ACTOR_ID = "memory-loop"
MODEL_ID = "global.anthropic.claude-sonnet-4-6"

# ---- 目录锚点：本文件位于 <BASE>/src/config.py ----
BASE_DIR = Path(__file__).resolve().parent.parent          # /home/ubuntu/g-repo/memory-loop
MEMORYLOOP_DIR = BASE_DIR / "memoryloop"

HARNESS_CONFIG_PATH = MEMORYLOOP_DIR / "app" / "extractor" / "harness.json"
SYSTEM_PROMPT_PATH = MEMORYLOOP_DIR / "app" / "extractor" / "system-prompt.md"
DEPLOYED_STATE_PATH = MEMORYLOOP_DIR / "agentcore" / ".cli" / "deployed-state.json"
# 部署后由脚本写出的解析结果（真实 ARN/ID），优先于 deployed-state.json。
CONFIG_LOCAL_PATH = BASE_DIR / "config.local.json"
SKILL_PATH = "./skills/scope-extract"                       # harness.json 里引用的技能路径
RUNS_DB_PATH = BASE_DIR / "runs.db"

# ---- 占位符：部署后由 load_deployed() 用真实值覆盖 ----
PLACEHOLDER_HARNESS_ARN = "arn:aws:bedrock-agentcore:us-west-2:000000000000:harness/PLACEHOLDER"
PLACEHOLDER_EPISODIC_MEMORY_ID = "mem-episodic-PLACEHOLDER"
PLACEHOLDER_CUSTOM_MEMORY_ID = "mem-custom-PLACEHOLDER"

# 部署产物中可能出现的 key 别名（统一 key -> 候选别名集合）
_KEY_ALIASES = {
    "HARNESS_ARN": ("HARNESS_ARN", "harnessArn", "harnessArn"),
    "EPISODIC_MEMORY_ID": ("EPISODIC_MEMORY_ID", "episodicMemoryId", "episodicMemoryArn"),
    "CUSTOM_MEMORY_ID": ("CUSTOM_MEMORY_ID", "customMemoryId", "customMemoryArn"),
}


def _walk_collect(obj, wanted, found):
    """递归遍历任意嵌套 dict/list，收集命中的字符串字段（首个命中优先）。"""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in wanted and isinstance(v, str) and v and k not in found:
                found[k] = v
            _walk_collect(v, wanted, found)
    elif isinstance(obj, list):
        for it in obj:
            _walk_collect(it, wanted, found)


def load_deployed(path=None) -> dict:
    """宽容读取部署产物，返回统一 key 的 dict：
    {HARNESS_ARN, EPISODIC_MEMORY_ID, CUSTOM_MEMORY_ID}。

    优先级：环境变量 > deployed-state.json 内解析 > 占位符。
    文件缺失/损坏或字段找不到时回退占位符（便于单测注入替换）。

    TODO(上线校对): 当前 deployed-state.json 为 {"targets": {}}（尚未 agentcore deploy）。
      真实结构未知——上线后按 deploy 实际写出的字段名/嵌套层级校对 _KEY_ALIASES 与解析路径。
    """
    path = Path(path) if path else DEPLOYED_STATE_PATH
    resolved = {
        "HARNESS_ARN": PLACEHOLDER_HARNESS_ARN,
        "EPISODIC_HARNESS_ARN": PLACEHOLDER_HARNESS_ARN,  # episodic 用的 extractor_ep harness
        "EPISODIC_MEMORY_ID": PLACEHOLDER_EPISODIC_MEMORY_ID,
        "CUSTOM_MEMORY_ID": PLACEHOLDER_CUSTOM_MEMORY_ID,
    }

    # 1) 从部署产物解析（宽容）
    wanted = {alias for aliases in _KEY_ALIASES.values() for alias in aliases}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        found = {}
        _walk_collect(data, wanted, found)
        for unified, aliases in _KEY_ALIASES.items():
            for alias in aliases:
                if found.get(alias):
                    resolved[unified] = found[alias]
                    break
    except (FileNotFoundError, json.JSONDecodeError, OSError, ValueError):
        pass  # 保留占位符

    # 2) config.local.json（部署后写出的真实值）覆盖占位/部署产物
    try:
        local = json.loads(CONFIG_LOCAL_PATH.read_text(encoding="utf-8"))
        for unified in resolved:
            if isinstance(local.get(unified), str) and local[unified]:
                resolved[unified] = local[unified]
    except (FileNotFoundError, json.JSONDecodeError, OSError, ValueError):
        pass

    # 3) 环境变量最高优先级
    for unified in resolved:
        env_val = os.environ.get(unified)
        if env_val:
            resolved[unified] = env_val

    return resolved
