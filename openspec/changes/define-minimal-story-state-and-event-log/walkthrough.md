# Walkthrough: 姐姐十年前死亡却昨天打电话

> 本文档用纸面推演验证 `event-log` 和 `minimal-story-state` 两个 spec 是否足够支撑 MVP 闭环。重点不是证明系统“判断正确”，而是证明系统能保存证据、保留余地、恢复状态，并且不替用户确认设定。

---

## 场景概述

用户写了两句话：

```text
姐姐十年前就死了。
昨天，姐姐给我打电话了。
```

系统需要完成这条链路：

```text
用户正文落盘
  → 后台补提取
  → 追加 SystemEvent
  → 重建 story_state 投影
  → 创建 ContinuityEvent 证据链
  → 用户选择忽略
  → 只更新该条发现状态，不确认任何设定
```

---

## 真相源边界

本 walkthrough 使用两类真相源，不再混成一个：

| 内容 | 真相源 | 说明 |
|------|--------|------|
| 用户原始正文 | `script/current.md` | 用户写了什么，以剧本文档为准。 |
| AI 结构化状态 | `events/*.jsonl` | 角色、事实、矛盾、项目偏好等结构化结果，以 event log 为准。 |
| 快速读取状态 | `story_state.json` | 从 event log 重放得到的投影，可删可重建。 |
| 项目偏好缓存 | `project_preferences.json` | 可选派生投影，不得绕过 event log 影响判断。 |

如果用户正文已经写入，但 AI 还没提取，下一次打开时触发的是“补提取”，不是“完全从 event log 恢复”。

---

## 第一步：项目初始状态

### 项目文件夹结构

```text
project_folder/
├── project.json
├── story_state.json
├── project_preferences.json      # 可选派生投影，不是真相源
├── events/
│   └── 00001.jsonl
└── script/
    ├── current.md
    └── history/
```

界面上仍可显示“项目偏好”“当前剧本”等中文名；内部稳定路径使用 ASCII。

### project.json

```json
{
  "id": "proj_20260614_001",
  "name": "未命名项目",
  "created_at": "2026-06-14T10:00:00+08:00",
  "updated_at": "2026-06-14T10:00:00+08:00",
  "version": "1.0.0"
}
```

### story_state.json

```json
{
  "projection_schema_version": "1.0",
  "log_head_seq": 0,
  "head_event_id": null,
  "source_document_revision": null,
  "source_document_checksum": null,
  "story": {
    "story_clock": null,
    "characters": [],
    "plot_events": [],
    "facts": [],
    "continuity_events": [],
    "project_preferences": []
  }
}
```

### project_preferences.json

```json
{
  "derived_from_head_event_id": null,
  "preferences": []
}
```

> 这个文件只是缓存/投影。任何会影响检测、降权、提醒厚度的偏好，都必须先进入 event log。

---

## 第二步：用户写下正文

用户写入：

```markdown
姐姐十年前就死了。

昨天，姐姐给我打电话了。
```

系统立即保存原文：

```text
source_document_id: script_current
source_revision: script_rev_001
source_document_checksum: sha256:script_rev_001
```

快挡提取可以在内存里记录“可能有角色/事实/时间信息”，但不写入 event log。此时：

```text
script/current.md 有内容
events/00001.jsonl 仍为空
story_state.json 仍为空投影
```

如果程序在这里关闭，下次打开时系统只能根据 `script/current.md` 补跑提取；不能声称已经靠 event log 完整恢复结构化状态。

---

## 第三步：慢挡提取写入 event log

后台慢挡提取读取 `script_current@script_rev_001`，产生一个批次：

```text
batch_id: batch_extract_001
extractor_version: extraction_agent@0.1.0
```

事件写入使用 `snake_case` 字段，并拆分：

- `event_id`：事件身份。
- `idempotency_key`：重试去重键。
- `batch_id`：同一次慢挡提取的批次边界。

### events/00001.jsonl

```json
{"event_id":"evt_001","idempotency_key":"script_current:script_rev_001:0-8:character.created:char_001:extraction_agent@0.1.0","seq":1,"type":"character.created","timestamp":"2026-06-14T10:30:00+08:00","schema_version":"1.0","batch_id":"batch_extract_001","payload":{"character_id":"char_001","name":"姐姐","gender":"female","initial_status":"dead","initial_status_note":"十年前死亡","relations":[{"target_id":"protagonist","relation":"亲人"}]},"base_state_version":0,"actor":"extraction_agent"}
{"event_id":"evt_002","idempotency_key":"script_current:script_rev_001:0-8:fact.created:fact_001:extraction_agent@0.1.0","seq":2,"type":"fact.created","timestamp":"2026-06-14T10:30:01+08:00","schema_version":"1.0","batch_id":"batch_extract_001","payload":{"fact_id":"fact_001","content":"姐姐十年前死亡","story_time":{"type":"relative","anchor":"story_start","direction":"before","distance":"10年","confidence":0.8},"about_character_ids":["char_001"],"source_document_id":"script_current","source_revision":"script_rev_001","source_span":{"start":0,"end":8},"source_text_hash":"sha256:fact_001_source","source_plot_event_id":null,"extraction_confidence":0.8,"lifecycle_status":"active"},"base_state_version":1,"actor":"extraction_agent"}
{"event_id":"evt_003","idempotency_key":"script_current:script_rev_001:10-22:plot_event.created:plot_001:extraction_agent@0.1.0","seq":3,"type":"plot_event.created","timestamp":"2026-06-14T10:30:02+08:00","schema_version":"1.0","batch_id":"batch_extract_001","payload":{"plot_event_id":"plot_001","summary":"姐姐打电话","story_time":{"type":"relative","anchor":"story_now","direction":"before","distance":"1天","confidence":0.7},"participant_character_ids":["char_001","protagonist"],"asserted_fact_ids":[]},"base_state_version":2,"actor":"extraction_agent"}
{"event_id":"evt_004","idempotency_key":"script_current:script_rev_001:10-22:fact.created:fact_002:extraction_agent@0.1.0","seq":4,"type":"fact.created","timestamp":"2026-06-14T10:30:03+08:00","schema_version":"1.0","batch_id":"batch_extract_001","payload":{"fact_id":"fact_002","content":"姐姐昨天打电话","story_time":{"type":"relative","anchor":"story_now","direction":"before","distance":"1天","confidence":0.9},"about_character_ids":["char_001"],"source_document_id":"script_current","source_revision":"script_rev_001","source_span":{"start":10,"end":22},"source_text_hash":"sha256:fact_002_source","source_plot_event_id":"plot_001","extraction_confidence":0.9,"lifecycle_status":"active"},"base_state_version":3,"actor":"extraction_agent"}
{"event_id":"evt_005","idempotency_key":"batch_extract_001:batch.committed","seq":5,"type":"batch.committed","timestamp":"2026-06-14T10:30:04+08:00","schema_version":"1.0","batch_id":"batch_extract_001","payload":{"member_event_ids":["evt_001","evt_002","evt_003","evt_004"],"source_document_id":"script_current","source_revision":"script_rev_001"},"base_state_version":4,"actor":"hub"}
```

如果写到一半崩溃，重放时能看到缺少 `batch.committed`，不会把半截提取当作完整状态。

---

## 第四步：重建 story_state 投影

### story_state.json

```json
{
  "projection_schema_version": "1.0",
  "log_head_seq": 5,
  "head_event_id": "evt_005",
  "source_document_revision": "script_rev_001",
  "source_document_checksum": "sha256:script_rev_001",
  "story": {
    "story_clock": {
      "current_time": null,
      "reference_point": "story_start",
      "confidence": 0.5
    },
    "characters": [
      {
        "id": "char_001",
        "name": "姐姐",
        "status": "dead",
        "status_since_event_id": "evt_001",
        "status_note": "十年前死亡",
        "gender": "female",
        "relations": [{"target_id":"protagonist","relation":"亲人"}],
        "known_fact_ids": ["fact_001", "fact_002"],
        "attributes": {}
      }
    ],
    "plot_events": [
      {
        "id": "plot_001",
        "summary": "姐姐打电话",
        "story_time": {"type":"relative","anchor":"story_now","direction":"before","distance":"1天","confidence":0.7},
        "participant_character_ids": ["char_001", "protagonist"],
        "asserted_fact_ids": ["fact_002"],
        "source_event_id": "evt_003"
      }
    ],
    "facts": [
      {
        "id": "fact_001",
        "content": "姐姐十年前死亡",
        "story_time": {"type":"relative","anchor":"story_start","direction":"before","distance":"10年","confidence":0.8},
        "about_character_ids": ["char_001"],
        "source_event_id": "evt_002",
        "source_document_id": "script_current",
        "source_revision": "script_rev_001",
        "source_span": {"start":0,"end":8},
        "source_text_hash": "sha256:fact_001_source",
        "source_plot_event_id": null,
        "extraction_confidence": 0.8,
        "lifecycle_status": "active"
      },
      {
        "id": "fact_002",
        "content": "姐姐昨天打电话",
        "story_time": {"type":"relative","anchor":"story_now","direction":"before","distance":"1天","confidence":0.9},
        "about_character_ids": ["char_001"],
        "source_event_id": "evt_004",
        "source_document_id": "script_current",
        "source_revision": "script_rev_001",
        "source_span": {"start":10,"end":22},
        "source_text_hash": "sha256:fact_002_source",
        "source_plot_event_id": "plot_001",
        "extraction_confidence": 0.9,
        "lifecycle_status": "active"
      }
    ],
    "continuity_events": [],
    "project_preferences": []
  }
}
```

---

## 第五步：矛盾监控只提交证据

矛盾监控 Agent 发现：

- `char_001.status = dead`
- `fact_002` 表示同一角色昨天打电话
- 这两个结构化事实存在连续性冲突

后台 Agent 不写“灵异故事 / 假死 / 梦境”等解释。这些是用户可见表达时 Dialogue Gateway 可以临场给出的可能性，不是后台证据。

### events/00001.jsonl（追加）

```json
{"event_id":"evt_006","idempotency_key":"cont:character_status_conflict:fact_001+fact_002:v1","seq":6,"type":"continuity_event.created","timestamp":"2026-06-14T10:30:10+08:00","schema_version":"1.0","payload":{"continuity_event_id":"cont_001","type":"character_status_conflict","severity":"P2","contradiction_confidence":0.82,"evidence_fact_ids":["fact_001","fact_002"],"affected_modules":["character","plot"],"status":"queued","title":"姐姐的死亡状态与后续通话事实并存","involved_character_ids":["char_001"],"delivery":{"delivery_mode":"card_only","interrupt_risk":"medium","armor_level":"light","initiator":"system","flow_blocked":true}},"base_state_version":5,"actor":"continuity_agent"}
```

### 投影中的 ContinuityEvent

```json
{
  "id": "cont_001",
  "type": "character_status_conflict",
  "severity": "P2",
  "contradiction_confidence": 0.82,
  "evidence_fact_ids": ["fact_001", "fact_002"],
  "affected_modules": ["character", "plot"],
  "status": "queued",
  "title": "姐姐的死亡状态与后续通话事实并存",
  "involved_character_ids": ["char_001"],
  "source_event_id": "evt_006",
  "ignored_at": null,
  "ignored_days": 0,
  "delivery": {
    "delivery_mode": "card_only",
    "interrupt_risk": "medium",
    "armor_level": "light",
    "initiator": "system",
    "flow_blocked": true
  }
}
```

---

## 第六步：用户下次打开项目

系统不再用文件修改时间判断是否处理完成，而是比较：

```text
story_state.log_head_seq
story_state.head_event_id
story_state.source_document_revision
story_state.source_document_checksum
script/current.md 当前 revision/checksum
```

如果脚本 revision 与投影记录一致，直接加载投影。若脚本 revision 更新但 event log 没有对应提取批次，则标记为待补提取。

创意模式下，由于 Timing Policy 判断主动打断风险较高，系统只亮侧边卡片，不插队提醒。

---

## 第七步：用户选择“忽略”

用户看到卡片后选择“忽略”。这只表示：这条提醒现在不要处理。它不表示：用户确认这是灵异故事，也不表示姐姐是鬼魂。

### events/00001.jsonl（追加）

```json
{"event_id":"evt_007","idempotency_key":"cont_001:ignored:user:2026-06-14T11:00:00+08:00","seq":7,"type":"continuity_event.ignored","timestamp":"2026-06-14T11:00:00+08:00","schema_version":"1.0","payload":{"continuity_event_id":"cont_001","user_explanation":null,"scope":"single_finding"},"base_state_version":6,"actor":"user"}
```

### 更新后的投影片段

```json
{
  "continuity_events": [
    {
      "id": "cont_001",
      "status": "ignored",
      "evidence_fact_ids": ["fact_001", "fact_002"],
      "ignored_at": "2026-06-14T11:00:00+08:00",
      "ignored_days": 0
    }
  ],
  "project_preferences": []
}
```

此时 `project_preferences` 仍为空。系统可以记住“这条已忽略”，但不能自动写入：

```text
project_type = 灵异故事
assumption = 姐姐是鬼魂
```

---

## 第八步：后续两种合法发展

### 场景 A：用户多次忽略同类问题

如果类似问题多次出现，系统可以提出一个可拒绝的问题：

> 这类“死亡状态与后续行动并存”的提醒，要不要以后只放到卡片里，不主动提醒？

只有用户确认后，才写入项目偏好事件：

```json
{"event_id":"evt_008","idempotency_key":"project_preferences:deweight:character_status_conflict:v1","seq":8,"type":"project_preference.deweighting_set","timestamp":"2026-06-14T12:00:00+08:00","schema_version":"1.0","payload":{"category":"character_status_conflict","weight_delta":-0.4,"reason":"user_confirmed_deweighting","scope":"project"},"base_state_version":7,"actor":"user"}
```

这会影响未来投递优先级，但仍不确认任何故事设定。

### 场景 B：用户主动确认设定

如果用户明确说：

> “姐姐就是鬼魂，这是核心设定。”

系统才可以写入确认设定：

```json
{"event_id":"evt_009","idempotency_key":"project_preferences:assumption:姐姐是鬼魂:v1","seq":9,"type":"project_preference.assumption_confirmed","timestamp":"2026-06-14T12:05:00+08:00","schema_version":"1.0","payload":{"assumption":"姐姐是鬼魂","confirmed_by":"user","related_continuity_event_id":"cont_001","related_fact_ids":["fact_001","fact_002"]},"base_state_version":8,"actor":"user"}
```

这时投影可以包含：

```json
{
  "project_preferences": [
    {
      "assumption": "姐姐是鬼魂",
      "confirmed_at": "2026-06-14T12:05:00+08:00",
      "confirmed_by": "user",
      "source_event_id": "evt_009"
    }
  ]
}
```

确认设定必须来自用户明确表达，不能来自“忽略”。

---

## 第九步：用户解释为假死

用户主动写下：

```text
原来姐姐是假死，为了躲避仇家。
```

这是新的正文 revision：

```text
source_revision: script_rev_002
```

系统提取新 Fact，并更新角色状态：

```json
{"event_id":"evt_010","idempotency_key":"script_current:script_rev_002:fact.created:fact_004:extraction_agent@0.1.0","seq":10,"type":"fact.created","timestamp":"2026-06-14T13:00:00+08:00","schema_version":"1.0","batch_id":"batch_extract_002","payload":{"fact_id":"fact_004","content":"姐姐是假死，为了躲避仇家","story_time":{"type":"unknown"},"about_character_ids":["char_001"],"source_document_id":"script_current","source_revision":"script_rev_002","source_span":{"start":24,"end":41},"source_text_hash":"sha256:fact_004_source","source_plot_event_id":null,"extraction_confidence":0.9,"lifecycle_status":"active"},"base_state_version":9,"actor":"extraction_agent"}
{"event_id":"evt_011","idempotency_key":"char_001:status_updated:alive:fact_004:v1","seq":11,"type":"character.status_updated","timestamp":"2026-06-14T13:00:01+08:00","schema_version":"1.0","batch_id":"batch_extract_002","payload":{"character_id":"char_001","previous_status":"dead","new_status":"alive","reason_fact_id":"fact_004"},"base_state_version":10,"actor":"extraction_agent"}
{"event_id":"evt_012","idempotency_key":"cont_001:resolved:fact_004:v1","seq":12,"type":"continuity_event.resolved","timestamp":"2026-06-14T13:00:02+08:00","schema_version":"1.0","payload":{"continuity_event_id":"cont_001","resolution_fact_id":"fact_004"},"base_state_version":11,"actor":"continuity_agent"}
```

这不是系统猜出来的“可能是假死”，而是用户正文新增事实后，系统才更新结构化状态。

---

## 数据结构总结

### SystemEvent 字段

| 字段 | 说明 | 示例 |
|------|------|------|
| `event_id` | 事件身份 | `evt_001` |
| `idempotency_key` | 重试去重键 | `script_current:script_rev_001:...` |
| `seq` | 日志内顺序 | `1` |
| `type` | 事件类型 | `fact.created` |
| `timestamp` | 写入时间 | `2026-06-14T10:30:00+08:00` |
| `schema_version` | Schema 版本 | `1.0` |
| `batch_id` | 批次边界 | `batch_extract_001` |
| `payload` | 事件专属数据 | `{...}` |
| `base_state_version` | 乐观并发版本 | `0` |
| `actor` | 发起者 | `extraction_agent` |

### Fact 字段

| 字段 | 说明 | 示例 |
|------|------|------|
| `id` | 事实 ID | `fact_001` |
| `content` | 事实内容 | `姐姐十年前死亡` |
| `story_time` | 故事时间 | `{type, anchor, direction, distance, confidence}` |
| `about_character_ids` | 相关角色 | `["char_001"]` |
| `source_event_id` | 来源事件 | `evt_002` |
| `source_document_id` | 来源文档 | `script_current` |
| `source_revision` | 来源版本 | `script_rev_001` |
| `source_span` | 原文范围 | `{start, end}` |
| `source_text_hash` | 原文哈希 | `sha256:...` |
| `extraction_confidence` | 提取置信度 | `0.8` |
| `lifecycle_status` | 生命周期 | `active` |

### ContinuityEvent 字段

| 字段 | 说明 | 示例 |
|------|------|------|
| `id` | 发现 ID | `cont_001` |
| `type` | 发现类型 | `character_status_conflict` |
| `severity` | 优先级 | `P2` |
| `contradiction_confidence` | 矛盾置信度 | `0.82` |
| `evidence_fact_ids` | 证据事实 | `["fact_001", "fact_002"]` |
| `affected_modules` | 影响模块 | `["character", "plot"]` |
| `status` | 生命周期 | `queued` / `ignored` / `resolved` |
| `delivery` | 投递策略 | `{delivery_mode, armor_level, ...}` |
| `source_event_id` | 来源事件 | `evt_006` |
| `ignored_at` | 忽略时间 | `2026-06-14T11:00:00+08:00` |

---

## 验证结论

### 通过验证的点

1. ✅ `event_id` 与 `idempotency_key` 已拆开，LLM 重试不会天然重复写事实。
2. ✅ 一次慢挡提取有 `batch_id` 与提交边界，半截批次不会被当成完整投影。
3. ✅ `Fact` 能追溯到原文版本、范围和哈希，用户改文后可撤回或替换旧事实。
4. ✅ `ContinuityEvent` 只保存证据和发现，不保存后台写死的创意解释。
5. ✅ 用户选择“忽略”只更新该条发现状态，不自动确认项目类型或设定。
6. ✅ 项目偏好必须通过 event log 入账，派生文件不再是第二真相源。

### 留给后续 change 的问题

1. Story Clock 的具体推断规则。
2. `story_time.relative.anchor` 如何稳定锚定到 `PlotEvent.id` / `Fact.id`。
3. 置信度动态变化的算法。
4. 用户记忆（跨项目）与项目偏好（单项目）的同步策略。

---

## 下一步

本 walkthrough 已能支撑最小后端骨架的施工图。归档前仍需：

1. 反查 spec 是否包含本 walkthrough 使用的字段和边界。
2. 更新 `summary.md`、`docs/路线图.md`、`docs/问题清单-待解决.md`，避免继续声称 walkthrough 未完成。
3. 运行 `openspec validate define-minimal-story-state-and-event-log`。
