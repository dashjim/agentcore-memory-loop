import pathlib
import sys

# 确保 repo 根（含 src/ 包）在 import 路径上，无论 pytest 从何处启动。
_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
