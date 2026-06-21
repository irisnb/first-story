## ADDED Requirements

### Requirement: 对话轮数自动计数
系统 SHALL 在每次用户发送消息时自动递增 `context_summary.turn_count`。轮数更新 SHALL 通过写入 `context_summary.updated` 事件持久化。

#### Scenario: 用户消息递增轮数
- **WHEN** 用户发送一条聊天消息
- **THEN** 系统 `turn_count` 递增 1
- **AND** 写入 `context_summary.updated` 事件，payload 包含新的 `turn_count`

#### Scenario: assistant 消息不计入轮数
- **WHEN** 系统生成 assistant 回复
- **THEN** `turn_count` 保持不变
- **AND** 只有用户消息触发轮数递增

### Requirement: 小摘要自动触发
系统 SHALL 在 `turn_count` 为 10 的倍数时（10, 20, 40, 50, 70, 80...）触发小摘要更新。小摘要 SHALL 只更新 `recent_focus` 字段。

#### Scenario: 第 10 轮触发小摘要
- **WHEN** 用户发送第 10 条消息
- **THEN** 系统在后台生成小摘要
- **AND** 更新 `recent_focus` 字段
- **AND** 更新 `last_minor_update` 时间戳
- **AND** 不阻塞对话响应

#### Scenario: 第 20 轮触发小摘要
- **WHEN** 用户发送第 20 条消息
- **THEN** 系统在后台生成小摘要
- **AND** 更新 `recent_focus` 字段

### Requirement: 大摘要自动触发
系统 SHALL 在 `turn_count` 为 30 的倍数时（30, 60, 90...）触发大摘要更新。大摘要 SHALL 更新所有字段：`world_brief`、`plot_brief`、`character_brief`、`recent_focus`。

#### Scenario: 第 30 轮触发大摘要
- **WHEN** 用户发送第 30 条消息
- **THEN** 系统在后台生成大摘要
- **AND** 更新 `world_brief`、`plot_brief`、`character_brief`、`recent_focus` 字段
- **AND** 更新 `last_major_update` 时间戳
- **AND** 不阻塞对话响应

#### Scenario: 第 60 轮触发大摘要
- **WHEN** 用户发送第 60 条消息
- **THEN** 系统在后台生成大摘要
- **AND** 更新所有摘要字段

### Requirement: 摘要更新不阻塞对话
摘要生成 SHALL 作为后台任务执行，不阻塞对话响应。摘要生成失败 SHALL 不影响对话功能，系统继续使用旧摘要。

#### Scenario: 摘要生成失败不影响对话
- **WHEN** 后台摘要生成失败（LLM 错误、超时等）
- **THEN** 对话功能正常工作
- **AND** 系统继续使用旧的摘要内容
- **AND** 错误被记录到日志

#### Scenario: 摘要更新后台执行
- **WHEN** 触发摘要更新
- **THEN** 对话 API 立即返回响应
- **AND** 摘要更新在后台执行
- **AND** 用户无需等待摘要生成完成

### Requirement: 摘要内容注入对话上下文
`DialogueAgent._build_prompt()` SHALL 在构建 prompt 时注入 `context_summary` 的内容。如果 `context_summary` 为空或字段缺失，SHALL 使用空字符串，不影响对话。

#### Scenario: 有摘要时注入上下文
- **WHEN** `context_summary` 有内容
- **THEN** prompt 包含项目摘要部分
- **AND** 包含世界观、情节、角色、最近焦点信息

#### Scenario: 无摘要时继续对话
- **WHEN** `context_summary` 为空或所有字段为空字符串
- **THEN** prompt 不包含项目摘要部分
- **AND** 对话正常进行
