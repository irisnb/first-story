## MODIFIED Requirements

### Requirement: DialogueAgent 是唯一用户出口
DialogueAgent SHALL 是唯一产生用户可见文本的组件。它负责聊天、意图分类、温和表达，MUST NOT 直接调用提取/矛盾/别名服务。

#### Scenario: 对话经过 Hub
- **WHEN** 用户发送消息
- **THEN** DialogueAgent 通过 Hub 请求后台能力
- **AND** 不直接导入或调用提取/矛盾服务

#### Scenario: 意图分类并入回复
- **WHEN** LLM 生成回复
- **THEN** 意图分类结果包含在同一响应中
- **AND** 意图只能是 `ignore` 或 `candidate`

## ADDED Requirements

### Requirement: DialogueAgent 更新轮数
DialogueAgent.respond() SHALL 在写入用户消息后更新 `turn_count`。轮数更新 SHALL 通过写入带 `turn_count` 字段的 `context_summary.updated` 事件完成。

#### Scenario: 写入用户消息后更新轮数
- **WHEN** DialogueAgent 写入用户消息事件
- **THEN** 同时写入 `context_summary.updated` 事件
- **AND** payload 包含 `turn_count` 字段（递增后的值）

#### Scenario: 返回结果包含轮数
- **WHEN** respond() 返回 DialogueResult
- **THEN** result 包含当前 `turn_count` 值
- **AND** API 层可根据 turn_count 判断是否触发摘要更新
