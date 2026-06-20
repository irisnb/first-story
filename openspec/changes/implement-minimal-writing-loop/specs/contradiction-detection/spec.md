## ADDED Requirements

### Requirement: 基于提取 Fact 检测硬矛盾
矛盾监控 SHALL 基于真实提取的 Fact 检测连续性硬矛盾（如角色状态冲突、时间线冲突）。

#### Scenario: 检测角色状态冲突
- **WHEN** 提取的 Fact 中存在互相冲突的角色状态（如"姐姐十年前死亡"与"姐姐昨天打电话"）
- **THEN** 系统生成一条 `ContinuityEvent` 标记该冲突

#### Scenario: 无冲突时不产出噪声
- **WHEN** 提取的 Fact 之间不存在硬矛盾
- **THEN** 系统不生成任何矛盾事件

### Requirement: 指代消解走独立身份归一层（身份与生死解耦）
矛盾监控 SHALL 在分组比对前，将同一角色的不同称呼归一到规范名（canonical），归一结果来自独立的 alias 归一 LLM pass。该 pass MUST 只做身份判断（谁和谁是同一人），MUST NOT 输出或考虑任何生死/状态信息。检测器 SHALL 仅查 alias 表做名字归一，MUST NOT 从关键词重新猜测身份或语义。

#### Scenario: 不同称呼归一后检出冲突
- **WHEN** 同一角色被以不同称呼提取（如"姐姐"标记 dead、"姐"标记 alive），且 alias pass 将二者归并为同一 canonical
- **THEN** 检测器在归一后识别出 alive+dead 冲突并生成一条 `ContinuityEvent`

#### Scenario: 身份歧义时保守不误并
- **WHEN** 两个称呼是否指同一人在上下文中不明确
- **THEN** alias pass 保守地不归并（各自独立），宁可漏报也不制造假矛盾——误并会凭空制造或抹掉矛盾，比漏报严重

#### Scenario（已知缺口 · 后续 spec 补全）: 状态化命名与 LLM 非确定性导致的漏报
- **WHEN** 提取 LLM 把同一角色拆成名字本身就写死生死的变体（如"已故姐姐"/"在世姐姐"），或偶发把本应 alive 的状态标为 unknown
- **THEN** 当前 V1 可能漏报该冲突（实测真实 LLM 命中率约 8/9）。这是 B' 架构为"避免误并"付出的内在代价 + LLM 非确定性，按用户 2026-06-20 拍板**记为后续 change 补全的已知缺口**，不在 V1 强行补满（详见 design.md D9 决策快照）

### Requirement: 矛盾事件只存证据不存结论
`ContinuityEvent` SHALL 只记录观察到的事实证据（evidence），MUST NOT 记录"应该怎么改"的结论或裁判。

#### Scenario: 事件含事实证据
- **WHEN** 系统生成一条矛盾事件
- **THEN** 该事件的 evidence 字段列出相互冲突的事实陈述，并标注其 source span，不包含修改建议或对错判定

### Requirement: 矛盾监控攒批触发且失败不阻断
矛盾监控 SHALL 在核心状态变更/保存后批量触发，且失败时 MUST NOT 阻断用户写作。

#### Scenario: 监控失败不阻断创作
- **WHEN** 矛盾监控处理失败
- **THEN** 系统允许用户继续写作，不弹错、不卡住编辑器
