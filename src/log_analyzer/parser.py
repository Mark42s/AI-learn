"""日志文本 → 结构化 dict。"""
from __future__ import annotations

import re
from pathlib import Path

from pydantic import ValidationError

from .errors import ParseIssue, ParseResult
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
        raise ValueError("前缀不符：应为 '<ISO时间> <级别> <主机> <模块> <事件> ...'")

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


def parse_line(raw: RawLine) -> LogEntry | ParseIssue:
    """一行 → LogEntry 或结构化错误。

    分流：调用方错误（lineno<1 / text 非 str）直接 raise；
          数据错误（格式、字段非法）返回 ParseIssue，交给调用方跳过或回填。
    """
    if raw.lineno < 1:
        raise ValueError("lineno 必须 >= 1（调用方错误，快速失败）")
    if not isinstance(raw.text, str):
        raise TypeError("text 必须是 str（调用方错误，快速失败）")

    try:
        return LogEntry.model_validate(_split(raw.text))
    except ValidationError as e:
        # e.errors() 指出哪个字段、违反哪条规则 → 压成一条可机读的错误
        first = e.errors()[0]
        loc = ".".join(str(part) for part in first["loc"])
        return ParseIssue(
            lineno=raw.lineno,
            kind="VALIDATION",
            field=loc,
            message=str(first["msg"]),
            raw=raw.text,
        )
    except ValueError as e:
        return ParseIssue(
            lineno=raw.lineno, kind="FORMAT", message=str(e), raw=raw.text
        )


def _validate_path(path: str | Path) -> Path:
    """函数入口的参数校验：这类是调用方 bug，不吞、不转成 issue。"""
    if not isinstance(path, (str, Path)):
        raise TypeError(f"path 必须是 str 或 Path，实际是 {type(path).__name__}")
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"日志文件不存在: {p}")
    if not p.is_file():
        raise ValueError(f"路径不是文件: {p}")
    return p


def parse_file(path: str | Path) -> ParseResult:
    """读日志文件 → ParseResult（entries + stats + issues）。"""
    p = _validate_path(path)
    stats = ParseStats()
    entries: list[dict[str, object]] = []
    issues: list[ParseIssue] = []

    for lineno, text in enumerate(p.read_text(encoding="utf-8").splitlines(), start=1):
        if not text.strip():
            continue
        stats.total += 1
        outcome = parse_line(RawLine(lineno=lineno, text=text))
        if isinstance(outcome, ParseIssue):
            stats.skipped += 1
            issues.append(outcome)
            continue
        stats.ok += 1
        # mode="json" 把 datetime 转成 ISO 字符串，得到可直接 json.dumps 的 dict
        entries.append(outcome.model_dump(mode="json"))

    return ParseResult(entries=entries, stats=stats, issues=issues)
