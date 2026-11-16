"""D2：三种「结构体」写法，对照 C 来看。

    RawLine / ParseStats  ≈ struct（只存数据，dataclass 省掉样板代码）
    LogEntry              ≈ struct + parse_log_line()（pydantic 把校验变成声明式）
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

# Literal ≈ C 的 enum：取值集合在类型层面写死，pydantic 运行时会拦非法值
Severity = Literal["INFO", "WARN", "ERROR"]
Event = Literal["LINK", "NEIGHBOR", "STATE"]


@dataclass(frozen=True, slots=True)
class RawLine:
    """一行原始日志。frozen≈const struct；slots≈固定布局，拼错字段当场报错。"""

    lineno: int
    text: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)  # 只照抄字段，不做任何校验


@dataclass(slots=True)
class ParseStats:
    """解析计数，需要累加所以不 frozen。"""

    total: int = 0
    ok: int = 0
    skipped: int = 0

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


class LogEntry(BaseModel):
    """边界模型：外部字符串进来 → 强类型对象出去。

    ts: datetime     字符串自动转 datetime
    retry: int       "3" 自动转 3，且被 Field 约束在 [0, 10]
    不合法抛 ValidationError，e.errors() 会指出具体字段。
    """

    ts: datetime
    host: str
    severity: Severity
    facility: str
    message: str
    port: str | None = None
    retry: int = Field(default=0, ge=0, le=10)
    event: Event


    @field_validator("host", "facility", "message")
    @classmethod
    def not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("字段不能为空白")
        return v
