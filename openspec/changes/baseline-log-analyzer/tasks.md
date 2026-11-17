## 1. 校验基线规格

- [ ] 1.1 运行 `openspec validate baseline-log-analyzer --strict`，确认两份 delta spec 均通过校验（每个 Requirement 至少有一个 `#### Scenario`，结构合法）
- [ ] 1.2 逐条对照 `src/log_analyzer/parser.py`、`models.py`、`errors.py` 与 `log-parsing` 规格，确认每条 Requirement 描述的都是当前真实行为，而不是期望行为
- [ ] 1.3 逐条对照 `src/log_analyzer/async_probe.py` 与 `async-probe` 规格，确认并发上限、失败兜底、报告字段与实现一致
- [ ] 1.4 运行 `uv run pytest -q`，确认规格里描述的可观察行为都有测试覆盖；对没有覆盖的行为记录为后续补测项

## 2. 同步到主规格

- [ ] 2.1 运行 `/opsx:sync`，把两份 delta spec 合并进 `openspec/specs/`
- [ ] 2.2 确认 `openspec/specs/log-parsing/spec.md` 与 `openspec/specs/async-probe/spec.md` 已生成，且 `openspec validate --specs --strict` 通过

## 3. 归档

- [ ] 3.1 确认主规格已同步且无遗漏后，运行 `/opsx:archive` 归档本次基线变更
