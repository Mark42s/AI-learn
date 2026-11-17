# log_analyzer v0（D2 产出）

读日志文件 → 输出结构化 dict。用来落地三个知识点：类型注解、dataclass、pydantic v2 BaseModel。

## 跑起来

```powershell
uv run python -m log_analyzer sample.log
# 或等价的脚本入口
uv run log-analyzer sample.log
```

预期：`stats` 为 `total=8 / ok=6 / skipped=2`，`entries` 是 6 个结构化 dict，每条都带 `event`（LINK/NEIGHBOR/STATE）。`sample.log` 里第 5 行 `retry=99` 越过 `Field(le=10)`、第 6 行 `DEBUG` 不在 `Severity` 里，这两行被校验拦下并计入 `skipped`。

## 文件分工

| 文件 | 对应知识点 | 职责 |
|---|---|---|
| `models.py` | dataclass / pydantic | `RawLine`、`ParseStats` 管内部数据；`LogEntry` 守外部边界 |
| `parser.py` | 类型注解 | 正则切字段 → `model_validate` → `model_dump(mode="json")` |
| `sample.log` | — | 6 条合法 + 2 条故意非法，用来观察校验拦截 |

## 边界原则

外部数据（日志、模型输出、HTTP 请求）进来的那一下必须过 pydantic；内部中间结果用 dataclass 就够。`model_json_schema()` 是 D6 结构化输出和 D7 function calling 的骨架。

---

## D3：质量习惯（在当前版本上）

```powershell
uv run pytest -q                            # 10 passed
uv run python -m log_analyzer sample.log    # stats + entries + issues
uv run python -m log_analyzer nope.log      # 参数错误 → exit 2
```

改动：`errors.py` 新增 `ParseIssue` / `ParseResult`，坏行不再 `print`，而是返回**结构化错误**（`lineno / kind / field / message / raw`），可序列化、可断言、可回填给模型（摸底卷 B1 追问）。`parser.py` 加了 `_validate_path` 参数校验；CLI 把参数异常翻译成人话 + 退出码 2。

三层分流：**调用方错误 → raise 快速失败｜数据错误 → ParseIssue｜IO 错误 → CLI 翻译**。

`tests/test_parser.py` 的 10 个单测覆盖正常路径、类型转换、两类错误与端到端计数，用到了 `pytest.raises`、`@pytest.fixture` 和内置 `tmp_path`。讲义见 `F:\dev\outputs\D3-质量习惯与pytest.md`。
