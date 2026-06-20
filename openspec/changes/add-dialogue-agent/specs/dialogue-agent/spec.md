## ADDED Requirements

### Requirement: 对话 Agent 是唯一用户出口
对话 Agent SHALL 是唯一生成用户可见话术的组件。它 SHALL 接收用户聊天消息、调用 LLM 生成温和、可忽略、非裁判式的回复。

#### Scenario: 用户发送聊天消息
- **WHEN** 用户在聊天框发送一条创作相关消息
- **THEN** 对话 Agent 调用 LLM 生成回复
- **AND** 回复语气温和、不评判用户创意好坏、不以"正确答案"姿态裁决

### Requirement: 对话 Agent 不承担专业判断
对话 Agent MUST NOT 自己做提取、矛盾检测、alias 归一等专业判断。这些 SHALL 经 Hub 请求专职能力完成。

#### Scenario: 聊天内容需要提取
- **WHEN** 用户在聊天里描述了角色或情节
- **THEN** 对话 Agent 经 Hub 把该文本送去提取链路
- **AND** 对话 Agent 自身不实现提取逻辑

### Requirement: 意图闸门三态分类
对话 Agent SHALL 把每条用户消息分类为三态之一：`ignore`（闲聊/提问，不提取）、`candidate`（脑暴/假设，提取但 `acceptance_status=candidate`、不进矛盾检测）、`committed`（正式设定）。意图分类 V1 SHALL 并入对话回复的同一次 LLM 调用（不单开调用）。该次 LLM 调用输出的意图值 MUST 只能是 `ignore` 或 `candidate` 两者之一，MUST NOT 输出 `committed`——`committed` 只能由编辑器保存或显式"采纳进正文"产生。LLM 输出解析失败或拿到意外值时，SHALL 保守降级为 `ignore`（不提取，最安全）。

#### Scenario: 闲聊或提问
- **WHEN** 用户发送"你觉得这个反派立得住吗？"这类闲聊/提问
- **THEN** 该消息被分类为 `ignore`
- **AND** 不触发提取

#### Scenario: 脑暴假设
- **WHEN** 用户发送"要不要给主角加个双胞胎妹妹？"这类假设
- **THEN** 该消息被分类为 `candidate`
- **AND** 经 Hub 送去提取，产出的 facts 标记 `acceptance_status=candidate`
- **AND** 这些 candidate facts 不进入矛盾检测

#### Scenario: 聊天永不自动 commit
- **WHEN** 用户在聊天里描述任何设定
- **THEN** 对话 Agent 绝不把该内容直接标记为 `committed`
- **AND** 内容只能经编辑器保存或显式采纳进正文才成为 `committed`

#### Scenario: 意图分类并入对话调用且不输出 committed
- **WHEN** 对话 Agent 调用 LLM 同时生成回复与意图
- **THEN** 意图输出只取 `ignore` 或 `candidate`
- **AND** 即便 LLM 试图输出 `committed`，对话 Agent 也不据此 commit

#### Scenario: 解析失败保守降级
- **WHEN** LLM 的意图输出无法解析或为意外值
- **THEN** 对话 Agent 降级为 `ignore`
- **AND** 不触发提取

#### Scenario: 分类不确定时保守降级
- **WHEN** 对话 Agent 无法确定一条消息是闲聊还是假设
- **THEN** 它倾向于降级处理（宁可判为 `candidate` 或 `ignore`，不误判为更高态）

### Requirement: 对话上下文受控，不塞完整 story_state 或正文
对话 Agent 构造 LLM prompt 时 SHALL 携带最近 N 轮对话、story_state 的受控摘要、以及当前生效的风格备忘。它 MUST NOT 把完整 story_state JSON 或整篇正文塞进 prompt，SHALL 对摘要与上下文长度设上限以控制 token 成本。

#### Scenario: 带受控上下文回复
- **WHEN** 对话已进行多轮且 story_state 中已有角色设定
- **THEN** 对话 Agent 的 prompt 包含最近 N 轮对话、角色/情节受控摘要、当前风格备忘
- **AND** 不包含完整 story_state JSON，也不包含整篇正文

#### Scenario: 故事增长时 token 不爆炸
- **WHEN** 故事内容随创作持续增长
- **THEN** prompt 携带的上下文受上限约束，不随故事体量无限增长

### Requirement: 对话 endpoint 响应契约
后端 SHALL 提供 `POST /api/v1/projects/{id}/chat`，请求体含用户消息文本，同步返回 `{reply, message_id, intent, extraction_status}`。响应体 MUST NOT 包含矛盾/连续性证据，MUST NOT 回显任何 LLM API key。证据 SHALL 仍只通过 `/state` 轮询渲染到证据栏。

#### Scenario: 发送聊天消息
- **WHEN** 前端向 `/chat` 提交一条用户消息
- **THEN** 响应包含 `reply`（回复文本）、`message_id`、`intent`（三态之一）、`extraction_status`
- **AND** 响应不含证据事件，也不回显 LLM key

#### Scenario: 提取不阻塞回复
- **WHEN** 一条 candidate 或 committed 消息触发提取
- **THEN** 提取经 Hub 走后台任务执行
- **AND** `/chat` 回复在提取完成前即返回

### Requirement: 对话历史持久化为事件
每轮 user 与 assistant 消息 SHALL 作为 `chat.message` 事件追加进事件日志（append-only），使崩溃后可通过重放恢复对话历史，而非重跑 LLM。`chat.message` 事件 SHALL 只存日志、不进 story_state 投影。写入顺序 SHALL 为：user 消息在调用 LLM **之前**写入（保证用户输入不因 LLM 失败丢失）；assistant 回复在 LLM **成功返回后**写入（失败则不写 assistant，避免半截脏数据）。两条写入 MUST 经 Hub 写锁。

#### Scenario: 一轮对话落盘
- **WHEN** 一轮对话完成
- **THEN** user 消息和 assistant 回复各作为一条 `chat.message` 事件追加进事件日志
- **AND** 重启后可从事件日志重建对话历史
- **AND** 这些事件不污染五大模块的 story_state 投影

#### Scenario: LLM 失败时不写半截
- **WHEN** user 消息已写入但 LLM 调用失败
- **THEN** user 消息事件保留（用户输入不丢）
- **AND** 不写入 assistant 消息事件
