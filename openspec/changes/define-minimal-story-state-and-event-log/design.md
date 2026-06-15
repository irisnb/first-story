## Context

项目当前处于设计阶段,尚无实现代码。核心文档已经统一口径:用户原始正文以剧本文档为真相源；AI 结构化故事状态、矛盾发现和影响判断的项目偏好以 append-only event log 为真相源；`story_state.json` 是由事件日志重建的当前状态投影。问题清单将 P0-0 标记为已完成,并把 P0-0b 锁定为下一步:定义 MVP 所需的最小故事状态字段。

本变更是第一个真正的 OpenSpec change,目标不是实现 UI 或 Agent,而是把“状态如何可靠存在”写成可验收规格。它承接 MVP 最小闭环:用户写作 → 系统提取角色/事件/事实 → 写入 event log → 重建投影 → 检测硬矛盾 → 用户忽略/解决/显式确认偏好 → 保留证据与退路。

## Goals / Non-Goals

**Goals:**

- 定义账本层 `SystemEvent` 与 append-only event log 的最小行为。
- 定义投影层 `story_state` 的最小对象: `Character`、`PlotEvent`、`Fact`、`ContinuityEvent`、`project_preferences`。
- 明确 `story_state.json` 是可重建投影,不是事实源；剧本文档是用户正文真相源,event log 是结构化状态真相源。
- 明确事件去重、批次边界、状态重放、证据引用、时间表达、项目偏好降权与显式确认的最小规则。
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

**Decision:** 账本层只记录 `SystemEvent`;投影层承载 `Character`、`PlotEvent`、`Fact`、`ContinuityEvent`、`project_preferences`。

**Rationale:** “event”这个词有歧义:系统账本事件、故事情节事件、矛盾发现事件不是同一种东西。两层模型能避免把 `PlotEvent` 误当作真相源事件。

**Alternatives considered:**

- 只维护 `story_state.json`:实现直观,但会造成并发覆盖、崩溃恢复困难、版本分叉和忽略记录不可追溯。
- 把所有对象都叫 event 并放在同一数组:目录/字段少,但语义混乱,后续 Agent 无法稳定判断谁在修改状态、谁只是故事内容。

**Trade-off:** 两层模型增加了一个 `SystemEvent` 概念;换来恢复、重放、幂等和版本演化的地基。

### 2. `story_state.json` 只作为当前投影,不得成为写入争用点

**Decision:** 投影由 event log 重放得到,可缓存为 `story_state.json`,但任何结构化状态恢复都以 event log 为准。用户正文恢复以剧本文档为准；尚未提取的正文需要补提取,不能声称仅靠 event log 完整恢复。

**Rationale:** 本产品天然需要生长、分叉、撤销、忽略、降权和恢复。append-only 日志能保留历史,投影负责快速读取。

**Alternatives considered:**

- 让 Agent 直接改 `story_state.json`:简单,但多个 Agent 写入时会互相覆盖,且无法知道一个字段为何变成现在这样。
- 每次都让 LLM 从全文重新提取状态:避免维护日志,但成本高、结果不稳定,也无法保证崩溃后复现。

**Trade-off:** 需要定义重放规则、幂等键和批次边界;换来可恢复、可审计、可解释。

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

### 6. 项目偏好降权而非删除，忽略不等于确认

**Decision:** `project_preferences` 记录项目级降权规则和用户明确确认的项目假设;偏好影响检测或提醒时必须由 event log 入账。单次“忽略”只改变对应 `ContinuityEvent` 的状态,不得自动写成确认设定。

**Rationale:** 这与“老规则沉底不删”和“判断权在用户手里”一致。用户坚持的设定应被尊重,但系统只能在用户明确表达后记录确认,不能从忽略动作推断创作设定。

**Alternatives considered:**

- 忽略后直接删除提醒:界面干净,但历史不可恢复。
- 忽略后自动确认设定:短期显得聪明,但会让系统替用户下结论,违反“留余地”。

**Trade-off:** 状态会多保存一些历史和偏好事件;换来可逆、可解释、不越权。

## Risks / Trade-offs

- **Risk: 第一个 change 继续膨胀成全系统设计** → Mitigation: proposal 明确排除 UI、LLM、LightRAG、技术栈和完整 Agent 编排。
- **Risk: `SystemEvent` 与 `PlotEvent` 命名仍让人混淆** → Mitigation: specs 中明确账本层/投影层边界,并固定 `SystemEvent` 只属于 event log。
- **Risk: 双真相源表述被误读为两个结构化事实源** → Mitigation: 明确剧本文档只管用户原文,event log 只管 AI 结构化状态和判断偏好。
- **Risk: 时间结构看似完整但缺少解析实现** → Mitigation: 本 change 只验收表达能力;解析算法进入后续提取 Agent change。
- **Risk: 枚举状态限制先锋设定** → Mitigation: 保留 `status_note` 作为人读说明,且后续可扩展枚举;机器判断只处理明确状态。
- **Risk: 批次和锚点让第一版 schema 变重** → Mitigation: 只要求最小 `idempotency_key`、`batch_id`、原文 revision/span/hash,避免后端实现时返工。
- **Risk: 只做状态基础,短期看不到 UI 成果** → Mitigation: 这是后续 Agent/UI 的共同前置,避免返工。

## Open Questions

> 以下问题在 walkthrough 中已部分解决，剩余部分留待后续 change 处理。

### 已解决

- ✅ `SystemEvent.type` 的命名规范：采用领域命名格式（如 `character.created`, `fact.created`），在 walkthrough 中已验证。
- ✅ `Character.status` 的 MVP 枚举：初始包含 `alive/dead/unknown`，后续可扩展。
- ✅ `project_preferences` 的定位：项目级偏好由 event log 入账；单条提醒处理记录在 `ContinuityEvent.status` 中；跨项目用户记忆不在本 change 内设计。
- ✅ `Fact` 的来源边界：已补原文 document/revision/span/hash 与生命周期状态。
- ✅ 置信度语义：已拆分为 `extraction_confidence`、`contradiction_confidence`、谨慎的意图假设。

### 留待后续 change

- ⏳ `story_time.relative.anchor` 的锚定策略：walkthrough 中使用 `story_start` 和 `story_now` 作为临时锚点，具体锚定规则需在提取 Agent change 中细化。
- ⏳ Story Clock 的推断逻辑：walkthrough 中只定义了结构，推断规则需在后续 change 中设计。
- ⏳ 置信度动态变化的算法：walkthrough 中展示了字段边界，变化规则需在矛盾监控 Agent change 中细化。
- ⏳ 项目偏好与用户记忆的交互：本 change 只定义单项目偏好，用户记忆（跨项目）需单独设计。
