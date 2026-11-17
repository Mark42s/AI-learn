"""log_analyzer v0：读日志文件 → 输出结构化 dict。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from .parser import parse_file

DEFAULT_LOG = "sample.log"


def main() -> None:
    """CLI 入口：uv run python -m log_analyzer [日志文件路径]"""
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
    else:
        path = Path(__file__).resolve().parents[2] / DEFAULT_LOG

    try:
        result = parse_file(path)
    except (FileNotFoundError, ValueError, TypeError) as e:
        # 库层抛异常，CLI 层翻译成人话 + 非零退出码
        print(f"参数错误: {e}", file=sys.stderr)
        raise SystemExit(2) from e

    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))


__all__ = ["main"]
