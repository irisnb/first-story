## Context

项目当前处于设计阶段,尚无实现代码。核心文档已经统一口径:事实源是 append-only event log,`story_state.json` 是由事件日志重建的当前状态投影。问题清单将 P0-0 标记为已完成,并把 P0-0b 锁定为下一步:定义 MVP 所需的最小故事状态字段。

本变更是第一个真正的 OpenSpec change,目标不是实现 UI 或 Agent,而是把“状态如何可靠存在”写成可验收规格。它承接 MVP 最小闭环:用户写作 → 系统提取角色/事件/事实 → 写入 event log → 重建投影 → 检测硬矛盾 → 用户忽略/接受/保留 → 记住偏好。

## Goals / Non-Goals

**Goals:**

- 定义账本层 `SystemEvent` 与 append-only event log 的最小行为。
- 定义投影层 `story_state` 的最小对象: `Character`、`PlotEvent`、`Fact`、`ContinuityEvent`、`UserPreference`。
- 明确 `story_state.json` 是可重建投影,不是事实源。
- 明确事件去重、状态重放、证据引用、时间表达、用户偏好降权的最小规则。
- 用“姐姐十年前死亡却昨天打电话”的纸面场景验证字段足够表达 MVP 矛盾。

**Non-Goals:**

- 不实现应用代码、数据库、UI、ChatUI 或 Agent 编排。
- 不接真实 LLM、不接 LightRAG、不接外部服务。
- 不冻结完整前后端技术栈。
- 不实现完整自然语言时间解析;本变更只定义时间结构应能表达什么。
- 不设计主题、结构、完整世界观模型;它们在 MVP 中保留为空壳或后续能力。
- 不做自动语义合并、完整版本分叉 UI 或跨分支合并。

## Decisions

### 1. 使用两层状态模型:SystemEvent 账本层 + story_state 投影层

**Decision:** 账本层只记录 `SystemEvent`;投影层承载 `Character`、`PlotEvent`、`Fact`、`ContinuityEvent`、`UserPreference`。

**Rationale:** “event”这个词有歧义:系统账本事件、故事情节事件、矛盾发现事件不是同一种东西。两层模型能避免把 `PlotEvent` 误当作真相源事件。

**Alternatives considered:**

- 只维护 `story_state.json`:实现直观,但会造成并发覆盖、崩溃恢复困难、版本分叉和忽略记录不可追溯。
- 把所有对象都叫 event 并放在同一数组:目录/字段少,但语义混乱,后续 Agent 无法稳定判断谁在修改状态、谁只是故事内容。

**Trade-off:** 两层模型增加了一个 `SystemEvent` 概念;换来恢复、重放、幂等和版本演化的地基。

### 2. `story_state.json` 只作为当前投影,不得成为写入争用点

**Decision:** 投影由 event log 重放得到,可缓存为 `story_state.json`,但任何恢复都以 event log 为准。

**Rationale:** 本产品天然需要生长、分叉、撤销、忽略、降权和恢复。append-only 日志能保留历史,投影负责快速读取。

**Alternatives considered:**

- 让 Agent 直接改 `story_state.json`:简单,但多个 Agent 写入时会互相覆盖,且无法知道一个字段为何变成现在这样。
- 每次都让 LLM 从全文重新提取状态:避免维护日志,但成本高、结果不稳定,也无法保证崩溃后复现。

**Trade-off:** 需要定义重放规则和幂等键;换来可恢复、可审计、可解释。

### 3. 时间字段结构完备,自然语言解析不属于数据模型职责

**Decision:** `PlotEvent.story_time` 必须能表达绝对时间、相对时间和未知时间,并携带置信度;提取 Agent 负责把“十年前”“昨天”等自然语言解析到该结构。

**Rationale:** 数据模型不能把时间问题推迟到 Later,也不能假装自己负责自然语言理解。它应负责“只要解析结果来了,我能存得下、比得了、标得出不确定”。

**Alternatives considered:**

- 只用提取顺序号:可快速实现,但逃避了时间线矛盾的核心表达问题。
- 现在就设计完整时间线 NLP:会把第一个 change 拖进实现细节和模型能力评估,超出状态基础范围。

**Trade-off:** 当前不会解决所有时间解析问题;但不会丢失时间表达空间。

### 4. 角色状态使用机器枚举 + 人读 note,但只有枚举参与确定性判断

**Decision:** `Character.status` 是机器可读状态;`Character.status_note` 是人读备注。确定性矛盾检测只看 `status`,不得解析 `status_note`。

**Rationale:** 这避免 `status=alive` 但备注写“其实是鬼魂”时两个字段互相打架。系统不猜用户意图,只处理明确结构。

**Alternatives considered:**

- 只用自由文本:创作空间大,但机器无法稳定检测。
- 让系统解析备注:看似聪明,但会越权猜测用户创意,违反“留余地、不下定论”。

**Trade-off:** 如果用户只在 note 写关键状态,系统不会自动拿它做确定性判断;换来边界清晰和低误报。

### 5. 矛盾证据指向 Fact,Fact 再追溯到 SystemEvent

**Decision:** `ContinuityEvent.evidence` 引用 `Fact.id`,而不是直接引用 `SystemEvent.event_id`。

**Rationale:** 用户需要看到的是故事事实之间的冲突,不是第几次编辑操作之间的冲突。Fact 可通过 `source_event_id` 追溯账本来源。

**Alternatives considered:**

- 直接引用 SystemEvent:追溯简单,但用户可见证据会变成编辑流水,不利于温和提醒。
- 存自然语言证据字符串:展示简单,但不可追溯、不可去重、不可复核。

**Trade-off:** 需要维护 Fact 层;换来证据语义清晰、可追溯。

### 6. 用户偏好降权而非删除

**Decision:** `UserPreference` 记录忽略规则和降权日志;偏好影响提醒权重,不得删除原始事实、原始矛盾或原始判断。

**Rationale:** 这与“老规则沉底不删”和“判断权在用户手里”一致。用户坚持的设定应被尊重,但系统仍保留可追溯记录。

**Alternatives considered:**

- 忽略后直接删除提醒:界面干净,但历史不可恢复。
- 忽略后完全沉默到 0:短期不打扰,但用户之后主动求助时系统失去上下文。

**Trade-off:** 状态会多保存一些历史;换来可逆和可解释。

## Risks / Trade-offs

- **Risk: 第一个 change 继续膨胀成全系统设计** → Mitigation: proposal 明确排除 UI、LLM、LightRAG、技术栈和完整 Agent 编排。
- **Risk: `SystemEvent` 与 `PlotEvent` 命名仍让人混淆** → Mitigation: specs 中明确账本层/投影层边界,并固定 `SystemEvent` 只属于 event log。
- **Risk: 时间结构看似完整但缺少解析实现** → Mitigation: 本 change 只验收表达能力;解析算法进入后续提取 Agent change。
- **Risk: 枚举状态限制先锋设定** → Mitigation: 保留 `status_note` 作为人读说明,且后续可扩展枚举;机器判断只处理明确状态。
- **Risk: 只做状态基础,短期看不到 UI 成果** → Mitigation: 这是后续 Agent/UI 的共同前置,避免返工。

## Open Questions

- `SystemEvent.type` 的完整枚举是否在本 change 内固定,还是只定义 MVP 所需类型?
- `Character.status` 的 MVP 枚举是否只包含 `alive/dead/unknown`,还是还需要 `missing/incapacitated/non-human`?
- `story_time.relative.anchor` 应优先锚定 `PlotEvent.id`、`Fact.id`,还是允许临时文本锚点?
- `UserPreference` 的降权幅度是否需要数值范围,还是先只记录规则与状态?