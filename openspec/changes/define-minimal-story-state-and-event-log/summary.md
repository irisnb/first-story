# 变更总结：define-minimal-story-state-and-event-log

> 本文档记录 walkthrough 与 review cleanup 完成后的主要成果、边界和后续问题。

---

## 完成状态

✅ **原 tasks 与 review cleanup 均已完成**

- Walkthrough 已按“姐姐十年前死亡却昨天打电话”跑通。
- Spec 已根据 walkthrough 和 `review-findings.md` 修正。
- 忽略、项目偏好、幂等、批次、Fact 锚点、置信度和投递边界已对齐。
- `openspec validate define-minimal-story-state-and-event-log` 已通过；下一步可以考虑 `/opsx:archive`。

---

## 主要成果

### 1. 明确两类真相源

| 内容 | 真相源 | 说明 |
|------|--------|------|
| 用户原始正文 | `script/current.md` | 用户写了什么，以剧本文档为准。 |
| AI 结构化状态 | `events/*.jsonl` | 角色、事实、矛盾、项目偏好等结构化状态以 event log 为准。 |
| 快速读取状态 | `story_state.json` | 从 event log 重放得到的投影。 |
| 项目偏好缓存 | `project_preferences.json` | 可选派生投影，不得绕过 event log。 |

关键修正：如果正文已写入但 AI 尚未提取，下次打开时是“补提取”，不能声称“完全从 event log 恢复”。

### 2. 统一内部路径和字段风格

内部稳定路径使用 ASCII：

```text
project_folder/
├── project.json
├── story_state.json
├── project_preferences.json
├── events/00001.jsonl
└── script/current.md
```

JSON 字段统一使用 `snake_case`，例如：

- `event_id`
- `idempotency_key`
- `schema_version`
- `base_state_version`
- `plot_events`
- `continuity_events`
- `evidence_fact_ids`

### 3. 修正事件日志契约

`SystemEvent` 现在区分：

| 字段 | 用途 |
|------|------|
| `event_id` | 事件身份。 |
| `idempotency_key` | LLM/后台重试去重。 |
| `batch_id` | 一次慢挡提取的批次边界。 |
| `batch.committed` | 标记批次完整可重放。 |

这样可以避免同一段文本重试提取时重复写入事实，也能识别慢挡提取写到一半崩溃的情况。

### 4. 修正 Fact 证据锚点

`Fact` 不再只追溯到 `SystemEvent`，还要能追溯到原文：

- `source_document_id`
- `source_revision`
- `source_span`
- `source_text_hash`
- `lifecycle_status`

这样用户删改正文后，旧事实可以被 `retracted` 或 `superseded`，不会继续拿旧事实误报矛盾。

### 5. 修正矛盾发现边界

`ContinuityEvent` 只保存证据和发现本身：

- `contradiction_confidence` 表示事实之间是否冲突。
- `evidence_fact_ids` 引用证据事实。
- `delivery` 保存投递策略或指向投递队列。
- 后台 Agent 不保存 `possible_reasons`。

“灵异故事 / 假死 / 梦境”等解释只能由 Dialogue Gateway 在用户可见表达时临场生成，并且必须是可忽略的可能性。

### 6. 修正忽略与确认的边界

用户点击“忽略”只表示：这条提醒现在不要处理。

它不会自动生成：

```text
project_type = 灵异故事
assumption = 姐姐是鬼魂
```

只有用户明确说“姐姐就是鬼魂，这是核心设定”，系统才能通过 event log 写入 `project_preference.assumption_confirmed`。

重复忽略同类提醒时，系统可以请求用户确认是否降权；用户确认后才能写入 `project_preference.deweighting_set`。

---

## 待后续 change 处理

| 问题 | 留给哪个 change |
|------|----------------|
| Story Clock 推断逻辑 | 提取 Agent |
| `story_time.relative.anchor` 稳定锚定策略 | 提取 Agent |
| 置信度动态变化算法 | 矛盾监控 Agent |
| 用户记忆（跨项目）与项目偏好（单项目）的交互 | 用户记忆系统 |
| 剧本文档格式（Markdown/Fountain） | 剧本编辑器 |

---

## 归档判断

Review cleanup 后，本 change 已经满足“最小后端骨架施工图”的前置口径：

1. 用户正文与 AI 结构化状态的真相源边界已分开。
2. 项目偏好不再绕开 event log。
3. 忽略不再自动变成确认设定。
4. 字段命名、幂等、批次、Fact 原文锚点已落入 spec。
5. P1 风险已在本 change 内形成最小契约，算法细节留给后续 change。

`openspec validate define-minimal-story-state-and-event-log` 已通过，可以考虑 archive。
