## ADDED Requirements

### Requirement: Hub 是后台能力的唯一入口
薄 Hub SHALL 作为对话 Agent 访问一切后台能力（提取、矛盾检测、alias 归一）的唯一入口。对话 Agent MUST NOT 直接 import 或调用任何专职服务，只能通过 `Hub.dispatch` 请求。

#### Scenario: 对话 Agent 经 Hub 请求提取
- **WHEN** 对话 Agent 需要把聊天文本送去提取
- **THEN** 它调用 `Hub.dispatch` 并传入结构化事件，由 Hub 路由到提取链路
- **AND** 对话 Agent 的代码中不出现对提取/矛盾/alias 服务的直接 import

#### Scenario: 架构测试守门
- **WHEN** 运行架构防漂测试
- **THEN** 测试断言 `dialogue.py` 不 import 提取/矛盾/alias 服务模块
- **AND** 测试断言 `Hub.dispatch` 返回值不含面向用户的自然语言字段
- **AND** 测试断言除 `event_log.py` 与 Hub append gateway 外无业务代码直接调用 `append_event()`

### Requirement: Hub 只处理结构化字段
Hub SHALL 只接收和返回结构化数据（dataclass/dict）。Hub MUST NOT 生成任何用户可见的自然语言话术，MUST NOT 对创作内容做价值裁决。

#### Scenario: Hub 路由事件
- **WHEN** Hub 收到一个结构化事件
- **THEN** 它按事件 type 路由到对应能力并返回结构化结果
- **AND** 返回值中不包含面向用户的自然语言文案

#### Scenario: Hub 拒绝越权裁决
- **WHEN** 后台能力返回矛盾证据
- **THEN** Hub 原样转发结构化证据，不附加"对错"结论或修复建议

### Requirement: Hub 路由失败不阻断用户创作
当 Hub 路由的后台能力抛错时，Hub SHALL 隔离失败、记录日志，MUST NOT 让异常传播回阻断用户的请求路径。

#### Scenario: 提取能力抛错
- **WHEN** Hub 路由的提取链路抛出异常
- **THEN** Hub 捕获并记录该异常
- **AND** 用户的对话回复仍正常返回，不受影响

### Requirement: Hub 串行化事件日志写入（per-project 写锁覆盖所有写路径）
Hub SHALL 持有 per-project 写锁，**所有**对事件日志的写入 MUST 经此锁串行化，确保 seq 单调递增、投影不回退。覆盖面 MUST 包含全部现有写路径，不限于新增的 `/chat`：文档保存（`DocumentService`）、通用 events API、alias 归一、矛盾检测、evidence_card、风格备忘、后台提取产出。锁的临界区 MUST 覆盖"创建 `EventLogService` 实例 → 扫文件算 seq（read）→ append（write）"的完整 read-modify-write，因为现状 `ProjectService.get_services()` 每次新建 `EventLogService` 实例、各自用实例内 seq 计算，仅锁 append 仍可能两实例先各自扫描再排队写出重复 seq。

#### Scenario: 并发写入同一项目
- **WHEN** `/chat`、`/documents`、后台提取近乎同时尝试向同一项目的事件日志追加事件
- **THEN** Hub 写锁串行化这些写入
- **AND** 不产生重复 seq、不产生投影回退

#### Scenario: 现有写路径也走同一把锁
- **WHEN** 文档保存或通用 events API 触发事件日志写入
- **THEN** 该写入同样经 Hub 的 per-project 写锁串行化
- **AND** 与 `/chat` 写入共享同一把锁，不存在绕过锁的写路径

#### Scenario: 不同项目并发写入
- **WHEN** 两个不同项目的写入同时发生
- **THEN** 各自的 per-project 锁互不阻塞
- **AND** 两个项目的写入均正常完成

### Requirement: 禁止绕过 Hub 直接写事件日志
除 `event_log.py` 自身与 Hub 的 append gateway 外，业务代码 MUST NOT 直接调用 `append_event()`。所有写入 SHALL 经 Hub，否则 per-project 写锁形同虚设。此约束 SHALL 由架构测试钉死。

#### Scenario: 架构测试断言无旁路写入
- **WHEN** 运行架构防漂测试
- **THEN** 测试断言除 `event_log.py` 与 Hub append gateway 外，没有业务模块直接调用 `append_event()`
- **AND** 任何新增的旁路直写都会让该测试失败

### Requirement: 事件类型扩展先于写入
在写入任何新事件之前，`EventType` 枚举 SHALL 先包含 `chat.message`、`creative_intent.added`、`creative_intent.archived`、`manuscript.adopted`。`read_events()` 重放 MUST NOT 因遇到这些类型而报错崩溃。

#### Scenario: 重放含新类型的事件日志
- **WHEN** 事件日志中包含 `chat.message`、`creative_intent.*`、`manuscript.adopted` 事件
- **THEN** `read_events()` 正常重放全部事件
- **AND** 不抛未知事件类型异常
