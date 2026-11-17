## Why

`log_analyzer` 已经实现了日志解析、结构化校验、错误分流和异步并发探测，但 `openspec/specs/` 仍是空的——现有行为只存在于代码和 README 里。没有基线规格，后续每次改动都无法判断「哪些行为是有意为之、哪些是可以改的」，change 流程也无从对照。

本变更把**当前已实现的行为**反向固化成 OpenSpec 基线规格，之后所有行为改动都通过 change 流程相对这份基线来描述。

## What Changes

- 新增 `log-parsing` 能力规格，覆盖日志行切分、字段校验、结构化错误、文件解析统计与 CLI 入口。
- 新增 `async-probe` 能力规格，覆盖并发探测、限流、单项失败兜底与串行对照。
- 不修改任何实现代码：本变更只补齐规格基线。

## Capabilities

### New Capabilities
- `log-parsing`: 日志文件 → 结构化条目，包含字段校验规则、三类错误分流、解析统计与命令行入口。
- `async-probe`: 并发 HTTP 探测，包含并发上限、单项失败转结构化结果、串行基线对照。

### Modified Capabilities
<!-- 无：openspec/specs/ 当前为空，不存在需要修改的既有能力。 -->

## Impact

- 仅新增 `openspec/specs/log-parsing/spec.md` 与 `openspec/specs/async-probe/spec.md`（由 delta spec 同步生成）。
- 不涉及 `src/` 与 `tests/` 的任何改动，不影响运行时行为、依赖或 API。
