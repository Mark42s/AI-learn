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

    entries, stats = parse_file(path)
    print(
        json.dumps(
            {"stats": stats.to_dict(), "entries": entries},
            ensure_ascii=False,
            indent=2,
        )
    )


__all__ = ["main"]
