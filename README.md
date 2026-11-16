# log_analyzer v0（D2 产出）

读日志文件 → 输出结构化 dict。用来落地三个知识点：类型注解、dataclass、pydantic v2 BaseModel。

## 跑起来

```powershell
uv run python -m log_analyzer sample.log
# 或等价的脚本入口
uv run log-analyzer sample.log
```

预期：`stats` 为 `total=6 / ok=4 / skipped=2`，`entries` 是 4 个结构化 dict。`sample.log` 里第 5 行 `retry=99` 越过 `Field(le=10)`、第 6 行 `DEBUG` 不在 `Severity` 里，这两行被校验拦下并计入 `skipped`。

## 文件分工

| 文件 | 对应知识点 | 职责 |
|---|---|---|
| `models.py` | dataclass / pydantic | `RawLine`、`ParseStats` 管内部数据；`LogEntry` 守外部边界 |
| `parser.py` | 类型注解 | 正则切字段 → `model_validate` → `model_dump(mode="json")` |
| `sample.log` | — | 4 条合法 + 2 条故意非法，用来观察校验拦截 |

## 边界原则

外部数据（日志、模型输出、HTTP 请求）进来的那一下必须过 pydantic；内部中间结果用 dataclass 就够。`model_json_schema()` 是 D6 结构化输出和 D7 function calling 的骨架，今天先把 `LogEntry` 写熟。
