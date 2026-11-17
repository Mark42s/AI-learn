## Purpose

把网络设备日志文件解析成结构化条目，并把非法行转成可机读的错误记录，供调用方跳过或回填给模型修正。

## ADDED Requirements

### Requirement: 日志行格式切分
系统 SHALL 按固定前缀 `<ISO时间> <级别> <主机> <模块> <事件>` 识别每一行；前缀之后的 `port=` / `retry=` 键值对 SHALL 被提取为独立字段，其余文本 SHALL 作为 `message`。

#### Scenario: 合法行被切分
- **WHEN** 输入 `2026-01-01T00:00:00Z INFO r1 STP LINK port=Gi0/1 link up`
- **THEN** 系统给出 `port=Gi0/1`，`message=link up`，其余字段按位置填充

#### Scenario: 前缀不符合约定
- **WHEN** 输入行不匹配固定前缀（例如缺少级别或模块）
- **THEN** 系统返回 `kind=FORMAT` 的 `ParseIssue`，并保留原始行文本

#### Scenario: 缺少 message 文本
- **WHEN** 前缀与键值对解析完成后剩余文本为空
- **THEN** 系统返回 `kind=FORMAT` 的 `ParseIssue`

### Requirement: 字段取值校验
系统 SHALL 在解析后校验字段取值：`severity` MUST 属于 `INFO` / `WARN` / `ERROR`；`event` MUST 属于 `LINK` / `NEIGHBOR` / `STATE`；`retry` MUST 在 0 到 10 之间；`host`、`facility`、`message` MUST 非空白。

#### Scenario: 重试次数越界
- **WHEN** 输入行包含 `retry=99`
- **THEN** 系统返回 `kind=VALIDATION` 的 `ParseIssue`，`field=retry`

#### Scenario: 级别不在允许集合内
- **WHEN** 输入行的级别为 `DEBUG`
- **THEN** 系统无法切分出合法前缀，返回 `kind=FORMAT` 的 `ParseIssue`

#### Scenario: 必填字段为空白
- **WHEN** `host`、`facility` 或 `message` 只有空白字符
- **THEN** 系统返回 `kind=VALIDATION` 的 `ParseIssue`，并指明对应字段路径

#### Scenario: 可选端口缺省
- **WHEN** 输入行不含 `port=`
- **THEN** 该条目的 `port` 为 `null`，且不计为错误

### Requirement: 结构化错误输出
系统 SHALL 把每一处数据错误表示为可序列化的错误记录，包含行号、错误类别、字段路径、错误说明与原始行文本；错误类别 MUST 为 `FORMAT` 或 `VALIDATION` 之一。系统 MUST NOT 因单行数据错误而中断整个文件的解析。

#### Scenario: 坏行不影响后续行
- **WHEN** 文件中第 5 行不合法、第 6 行合法
- **THEN** 解析继续进行，第 6 行正常产出结构化条目

#### Scenario: 错误可机读
- **WHEN** 调用方取出一条错误记录
- **THEN** 可直接序列化为 JSON，且包含行号、类别、字段、说明与原文

### Requirement: 文件解析结果与统计
系统 SHALL 返回一次解析的完整结果，包含结构化条目列表、解析统计与错误列表；统计 MUST 给出总行数、成功数与跳过数，空行 MUST NOT 计入总行数。

#### Scenario: 统计计数与条目一致
- **WHEN** 解析示例文件中的 8 条非空行，其中 2 条非法
- **THEN** 统计为总行数 8、成功 6、跳过 2，且条目列表长度为 6、错误列表长度为 2

#### Scenario: 空行被忽略
- **WHEN** 文件中包含纯空白行
- **THEN** 该行不出现在条目、错误或统计总行数中

### Requirement: 命令行入口与退出码
系统 SHALL 提供命令行入口，接收一个日志文件路径并输出包含统计、条目与错误的 JSON；未提供路径时 SHALL 使用项目根目录下的 `sample.log`。路径错误时系统 MUST 向标准错误输出可读说明并以退出码 2 结束。

#### Scenario: 正常解析
- **WHEN** 执行 `python -m log_analyzer sample.log`
- **THEN** 标准输出为可解析的 JSON，包含 `stats`、`entries`、`issues`

#### Scenario: 文件不存在
- **WHEN** 执行命令行并传入不存在的路径
- **THEN** 标准错误输出参数错误说明，进程退出码为 2

### Requirement: 调用方错误与数据错误分流
系统 SHALL 区分调用方错误与数据错误：行号小于 1、行文本不是字符串、路径不存在或不是文件这类调用方错误 MUST 直接抛出异常；只有数据本身不合法时才转成结构化错误记录。

#### Scenario: 非法行号立即失败
- **WHEN** 以行号 0 调用单行解析
- **THEN** 系统抛出异常，而不是返回结构化错误记录

#### Scenario: 路径不是文件
- **WHEN** 传入一个目录路径
- **THEN** 系统在开始解析前即抛出异常
