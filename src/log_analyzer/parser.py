"""日志文本 → 结构化 dict。"""
from __future__ import annotations

import re
from pathlib import Path

from pydantic import ValidationError

from .models import LogEntry, ParseStats, RawLine

# 固定前缀：<ISO时间> <级别> <主机> <模块> <事件类型>，其后是 key=value 与自由文本
# event 这里只做切分（\S+ 抓一个词），取值合不合法交给 models.Event 的 Literal 由 pydantic 拦
_HEAD = re.compile(
    r"^(?P<ts>\S+)\s+(?P<severity>INFO|WARN|ERROR)\s+"
    r"(?P<host>\S+)\s+(?P<facility>\S+)\s+(?P<event>\S+)\s+(?P<rest>.*)$"
)
_KV = re.compile(r"(?P<key>port|retry)=(?P<value>\S+)")


def _split(line: str) -> dict[str, str]:
    """纯文本 → 字段字典。这里只做切分，校验交给 pydantic。"""
    m = _HEAD.match(line.strip())
    if m is None:
        raise ValueError("前缀不符：应为 '<ISO时间> <级别> <主机> <模块> ...'")

    fields = m.groupdict()
    rest: str = fields.pop("rest")

    kv: dict[str, str] = {}

    def _take(mo: re.Match[str]) -> str:
        kv[mo.group("key")] = mo.group("value")
        return ""

    message = _KV.sub(_take, rest).strip()
    if not message:
        raise ValueError("缺少 message 文本")
    return {**fields, **kv, "message": message}


def parse_line(raw: RawLine) -> LogEntry | None:
    """一行 → LogEntry；格式错或校验不过返回 None。

    v0 先跳过坏行（D3 再谈参数校验与错误处理）。
    """
    try:
        return LogEntry.model_validate(_split(raw.text))
    except ValidationError as e:
        # 校验没过：e.errors() 指出哪个字段、违反哪条规则
        print(f"第 {raw.lineno} 行校验失败:", e.errors())
        return None
    except ValueError as e:
        # 正则切分没过：连前缀格式都不对
        print(f"第 {raw.lineno} 行格式不符:", e)
        return None


def parse_file(path: str | Path) -> tuple[list[dict[str, object]], ParseStats]:
    """读日志文件 → (结构化 dict 列表, 统计)。这是 D2 的验收产出。"""
    stats = ParseStats()
    entries: list[dict[str, object]] = []

    for lineno, text in enumerate(
        Path(path).read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not text.strip():
            continue
        stats.total += 1
        entry = parse_line(RawLine(lineno=lineno, text=text))
        if entry is None:
            stats.skipped += 1
            continue
        stats.ok += 1
        # mode="json" 把 datetime 转成 ISO 字符串，得到可直接 json.dumps 的 dict
        entries.append(entry.model_dump(mode="json"))

    return entries, stats
