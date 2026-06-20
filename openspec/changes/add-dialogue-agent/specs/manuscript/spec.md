## ADDED Requirements

### Requirement: 正文页只读、一整篇展示
系统 SHALL 提供正文页，只读展示项目已采纳的正文内容，作为一整篇连续文本呈现。V1 正文页 MUST NOT 提供编辑能力（可编辑留作未来版本）。

#### Scenario: 查看正文
- **WHEN** 用户打开正文页
- **THEN** 页面以一整篇连续文本展示全部已采纳内容
- **AND** 页面不提供编辑输入框或保存按钮

### Requirement: 采纳进正文是聊天内容进正文的唯一入口
"采纳进正文"SHALL 是把聊天内容写进故事正文（进而产生 committed facts）的唯一显式入口。committed facts 有两个合法来源：编辑器保存正文、聊天内容经采纳追加正文。后端 SHALL 提供采纳 endpoint，前端 SHALL 提供成对的"放入正文"按钮。采纳的内容 SHALL 追加到正文末尾，并触发 `committed` 提取。聊天本身 MUST NOT 自动把内容写进正文。

#### Scenario: 从 ChatUI 采纳内容
- **WHEN** 用户在 ChatUI 选定一段内容并点"放入正文"
- **THEN** 后端把该内容追加到正文末尾
- **AND** 对追加后的片段以 `committed` 模式走共享提取管道
- **AND** 正文页随后展示新追加的内容

#### Scenario: 采纳按钮与后端成对
- **WHEN** 后端提供采纳 endpoint
- **THEN** 前端必有对应的"放入正文"按钮可触发它
- **AND** 不存在有后端能力但前端无入口的情况

#### Scenario: 聊天不自动写正文
- **WHEN** 用户在聊天里描述设定但未点采纳
- **THEN** 该内容不进入正文页
- **AND** 正文只通过显式采纳或编辑器保存改变

### Requirement: 采纳=追加+重新提取，绝不原地改 candidate
采纳 MUST NOT 把旧 candidate fact 的 `acceptance_status` 原地改写为 `committed`（违背 append-only 真相源不可变）。采纳链路 SHALL 为：① 把选定文本追加到正文末尾；② 对追加后的正文片段以 `committed` 模式走共享提取管道，产出**新的** committed facts；③ 写 `manuscript.adopted` 事件，携带 `adopted_from_message_id`（来源聊天消息）与落位信息，使新 committed facts 可链回来源聊天；④ 旧 candidate facts SHALL 保留不动（记录"用户曾经这样想过"的历史，不删不改）。

#### Scenario: 采纳产生新 committed 而非改旧 candidate
- **WHEN** 用户采纳一段曾被记为 candidate 的内容
- **THEN** 系统追加正文并重新以 committed 模式提取，产出新的 committed facts
- **AND** 原 candidate facts 保留不变
- **AND** 写入 `manuscript.adopted` 事件，新 committed facts 可经 `adopted_from_message_id` 链回来源聊天

### Requirement: 采纳 endpoint 并发安全与幂等
采纳 endpoint 的"读当前正文 → 追加 → 写"read-modify-write SHALL 在 Hub per-project 写锁内执行。endpoint SHALL 接受幂等键（如客户端生成的 `adopt_request_id`），对重复提交 MUST NOT 重复追加正文，以防用户双击造成内容重复。

#### Scenario: 双击采纳不重复追加
- **WHEN** 用户因双击对同一内容带同一幂等键提交两次采纳
- **THEN** 正文只追加一次
- **AND** 第二次请求被识别为重复，不产生第二段追加
