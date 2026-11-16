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

    ts: datetime = Field(description="日志时间戳，ISO 8601 格式")
    host: str = Field(description="产生该日志的主机名")
    severity: Severity = Field(description="严重级别，只能是 INFO/WARN/ERROR 之一")
    facility: str = Field(description="产生日志的模块/子系统，如 STP、OSPF、LACP")
    message: str = Field(description="日志正文，自由文本")
    port: str | None = Field(default=None, description="相关端口/接口名，没有则为 null")
    retry: int = Field(default=0, ge=0, le=10, description="重试次数，范围 0-10")
    event: Event = Field(description="事件类型，LINK/NEIGHBOR/STATE 之一")

    @field_validator("host", "facility", "message")
    @classmethod
    def not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("字段不能为空白")
        return v


def build_tool_schema() -> dict[str, object]:
    """D7 预告：把 LogEntry 的形状导出成一个 Claude API 工具 schema。

    - input_schema 是「形状」，由 pydantic 从 LogEntry 免费导出；
    - name / description 是「语义」，必须手写——尤其是 description 里的
      「何时不要用」，它划出负空间，防止模型在不该用时硬调工具。
    """
    return {
        "name": "submit_log_entry",
        "description": (
            "提交一条结构化的网络日志。"
            "当用户用自然语言描述了一条日志（时间、级别、主机、模块、事件等）、"
            "需要你把它整理成结构化字段时，调用本工具。"
            "如果用户给的是未解析的原始日志文本、日志已经是 JSON、"
            "或只是在问概念问题而没有给出日志内容，不要调用。"
        ),
        "input_schema": LogEntry.model_json_schema(),
    }
