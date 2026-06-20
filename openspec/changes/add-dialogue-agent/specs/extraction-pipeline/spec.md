## ADDED Requirements

### Requirement: 共享提取管道
系统 SHALL 提供单一共享提取管道 `run_extraction_pipeline(project_id, source_type, source_id, content, acceptance_status)`，文档保存与聊天提取共用同一套 extract → alias 归一 → 矛盾检测 → 投影重建逻辑。文档链路与聊天链路 MUST NOT 各自维护分叉的提取实现。管道签名 MUST 显式携带 `project_id`（定位事件日志与投影）、`source_type`（`chat` | `document`）、`source_id`（来源消息或文档标识）、`content`（待提取文本）、`acceptance_status`（`candidate` | `committed`，决定下游隔离行为）。

#### Scenario: 文档保存触发提取
- **WHEN** 用户保存正文文档
- **THEN** 文档链路调用共享提取管道，`source_type=document`、`acceptance_status=committed`
- **AND** 提取行为与既有文档提取等价（回归测试守护）

#### Scenario: 聊天触发提取
- **WHEN** 一条 candidate 或 committed 聊天消息需要提取
- **THEN** 聊天链路调用同一个共享提取管道，`source_type=chat`
- **AND** 不存在独立于文档链路的第二套提取实现

### Requirement: 提取产物带来源与采纳状态（独立字段）
共享提取管道产出的 facts SHALL 带 `source_type`（`chat` | `document`）与独立字段 `acceptance_status`（`candidate` | `committed`）。`acceptance_status` MUST 是与既有 `lifecycle_status`（`active` | `retracted` | `superseded`）**正交并存**的独立字段，MUST NOT 复用或覆盖 `lifecycle_status`——因为一条 fact 可能同时是 `active` 且 `committed`，两个维度互不替代。

#### Scenario: 聊天 candidate 提取
- **WHEN** 一条 `candidate` 聊天消息被提取
- **THEN** 产出的 facts 标记 `source_type=chat`、`acceptance_status=candidate`、`lifecycle_status=active`

#### Scenario: 文档 committed 提取
- **WHEN** 正文文档被提取
- **THEN** 产出的 facts 标记 `source_type=document`、`acceptance_status=committed`、`lifecycle_status=active`

#### Scenario: 两个状态维度正交
- **WHEN** 一条 committed fact 被后续设定取代
- **THEN** 它的 `acceptance_status` 仍是 `committed`、`lifecycle_status` 变为 `superseded`
- **AND** 两个字段独立表达，互不覆盖

### Requirement: 历史 facts 缺字段默认 committed + active
读取既有 facts 时，缺失 `acceptance_status` 字段的旧 facts SHALL 默认为 `committed`（旧数据均来自编辑器正文，本就是正式设定）；缺失 `lifecycle_status` 的旧 facts SHALL 默认为 `active`。任何按这两个字段过滤的逻辑 MUST 应用此默认兜底，MUST NOT 因旧 facts 缺字段而将其排除。

#### Scenario: 旧项目 facts 仍进矛盾检测
- **WHEN** 矛盾检测过滤"只读 active committed facts"，遇到没有 `acceptance_status` 字段的旧 fact
- **THEN** 该旧 fact 按默认 `committed` + `active` 处理，正常进入矛盾比对
- **AND** 旧项目的 facts 不因缺字段凭空消失

### Requirement: candidate facts 跳过全局 alias 写入
共享提取管道以 `acceptance_status=candidate` 运行时 SHALL 跳过对全局 `alias_bound` 的写入。candidate 的 alias 解析 MUST 仅在本次提取内临时使用，MUST NOT 落入全局 alias map，以免污染 committed 世界的矛盾判断。

#### Scenario: candidate 不污染全局 alias
- **WHEN** 一条 candidate 消息提取时解析出别名绑定
- **THEN** 该绑定只在本次提取临时生效
- **AND** 全局 `alias_bound` 不被写入，committed 的矛盾检测不受影响

### Requirement: candidate 模式事件白名单
共享提取管道以 `acceptance_status=candidate` 运行时 SHALL 只允许写入"想法记录"类事件（带 `acceptance_status=candidate` 的 fact 记录事件）。candidate 模式 MUST NOT 写出与 committed 同形的"正文实体"结构事件（如 `character.created`、`batch.committed`），否则投影层无法区分想法与正文实体。

#### Scenario: candidate 不写正文实体事件
- **WHEN** 一条 candidate 消息提取产生角色相关 facts
- **THEN** 管道只写入标记 `acceptance_status=candidate` 的 fact 记录事件
- **AND** 不写出 `character.created` / `batch.committed` 等正文实体事件

### Requirement: 矛盾检测只读 active committed facts
矛盾检测 SHALL 只比对 `acceptance_status=committed` 且 `lifecycle_status=active` 的 facts（缺字段按上文默认兜底）。`candidate` facts MUST NOT 参与矛盾比对。

#### Scenario: candidate 假设不报矛盾
- **WHEN** 用户在聊天里提出一个与现有 committed 设定冲突的假设
- **THEN** 该假设被提取为 candidate fact
- **AND** 矛盾检测不把它与 committed facts 比对，不产生矛盾证据

#### Scenario: committed 设定才触发矛盾
- **WHEN** 一个 committed fact 与另一个 committed fact 冲突
- **THEN** 矛盾检测产生证据，回流证据栏
