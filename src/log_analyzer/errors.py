"""D3：把错误变成数据。

D2 里坏行只 print 一句就跳过；D3 改成返回结构化对象——
可序列化、可断言、可回填给模型让它自己改（摸底卷 B1 追问的标准做法）。
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal

from .models import ParseStats

IssueKind = Literal["FORMAT", "VALIDATION"]


@dataclass(frozen=True, slots=True)
class ParseIssue:
    """一条数据错误。field 精确到字段路径，raw 保留原文便于回填。

    suggestion 是可供模型参考的候选修正（B1「返回候选」），暂未填充时为 None。
    """

    lineno: int
    kind: IssueKind
    message: str
    field: str | None = None
    suggestion: str | None = None
    raw: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ParseResult:
    """一次文件解析的完整结果：成功项 + 统计 + 错误项。"""

    entries: list[dict[str, object]] = field(default_factory=list)
    stats: ParseStats = field(default_factory=ParseStats)
    issues: list[ParseIssue] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "stats": self.stats.to_dict(),
            "entries": self.entries,
            "issues": [issue.to_dict() for issue in self.issues],
        }
