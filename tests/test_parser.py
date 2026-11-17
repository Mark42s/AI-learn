"""D3：10 个单测，覆盖正常路径、参数校验、错误分流与端到端结果。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from log_analyzer.errors import IssueKind, ParseIssue
from log_analyzer.models import LogEntry, RawLine
from log_analyzer.parser import parse_file, parse_line

VALID = (
    "2026-11-16T09:12:33 INFO sw-core-01 STP STATE "
    "port=ge-0/0/3 retry=3 link up"
)
BAD_RETRY = VALID.replace("retry=3", "retry=99")
BAD_EVENT = VALID.replace(" STATE ", " BOGUS ")
BAD_SEVERITY = VALID.replace(" INFO ", " DEBUG ")
NO_MESSAGE = "2026-11-16T09:12:33 INFO sw-core-01 STP STATE port=ge-0/0/3"


@pytest.fixture
def log_file(tmp_path: Path) -> Path:
    """≈ setup：每个用例独立临时文件，pytest 自动清理。"""
    path = tmp_path / "sample.log"
    path.write_text(
        "\n".join([VALID, BAD_RETRY, BAD_SEVERITY, "\n", BAD_EVENT]) + "\n",
        encoding="utf-8",
    )
    return path


def test_valid_line_returns_entry() -> None:
    entry = parse_line(RawLine(lineno=1, text=VALID))
    assert isinstance(entry, LogEntry)
    assert entry.host == "sw-core-01"
    assert entry.event == "STATE"
    assert entry.severity == "INFO"


def test_retry_and_timestamp_are_coerced() -> None:
    entry = parse_line(RawLine(lineno=1, text=VALID))
    assert isinstance(entry, LogEntry)
    assert entry.retry == 3 and isinstance(entry.retry, int)  # "3" → 3
    assert entry.ts.year == 2026 and entry.ts.month == 11  # str → datetime


@pytest.mark.parametrize(
    ("text", "lineno", "kind", "field"),
    [
        (BAD_RETRY, 7, "VALIDATION", "retry"),
        (BAD_EVENT, 8, "VALIDATION", "event"),
        (BAD_SEVERITY, 9, "FORMAT", None),
    ],
    ids=["retry", "event", "severity"],
)
def test_bad_line_reports_parse_issue(
    text: str, lineno: int, kind: IssueKind, field: str | None
) -> None:
    issue = parse_line(RawLine(lineno=lineno, text=text))
    assert isinstance(issue, ParseIssue)
    assert issue.kind == kind
    assert issue.field == field
    assert issue.lineno == lineno
    assert issue.suggestion is None  # B1 候选字段的默认值


def test_missing_message_reports_format_issue() -> None:
    issue = parse_line(RawLine(lineno=10, text=NO_MESSAGE))
    assert isinstance(issue, ParseIssue)
    assert issue.kind == "FORMAT"
    assert "message" in issue.message


def test_bad_lineno_raises_instead_of_being_swallowed() -> None:
    # 调用方错误：快速失败，不转成 ParseIssue
    with pytest.raises(ValueError, match="lineno"):
        parse_line(RawLine(lineno=0, text=VALID))


def test_missing_path_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        parse_file(tmp_path / "does-not-exist.log")


def test_directory_path_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="不是文件"):
        parse_file(tmp_path)


def test_parse_file_end_to_end(log_file: Path) -> None:
    result = parse_file(log_file)
    assert result.stats.total == 4  # 空行不计入
    assert result.stats.ok == 1
    assert result.stats.skipped == 3
    assert len(result.entries) == 1
    assert len(result.issues) == 3
    assert {i.kind for i in result.issues} == {"VALIDATION", "FORMAT"}
    # 结构化错误可序列化 = 可以回填给模型
    payload = json.dumps(result.to_dict(), ensure_ascii=False)
    assert '"field": "retry"' in payload
