# Review Findings: define-minimal-story-state-and-event-log

> 2026-06-14 高强度审查记录。  
> 结论：先不要 archive；先修正本文件列出的契约和原则问题。

> 2026-06-15 修复状态：本文件以下内容保留为审查记录。P0/P1 的契约问题已在 `specs/`、`walkthrough.md`、`summary.md` 和全局路线图/问题清单中完成 cleanup；修复后可重新考虑 archive。

---

## 总体判断

当前 change 已通过 OpenSpec 语法校验，但还没有达到“可以作为最小后端骨架施工图”的成熟度。

主要问题不是方向错，而是：

```text
1. 用户正文的真相源边界还没讲清楚。
2. AI 结构化状态的真相源边界还没讲清楚。
3. 项目偏好到底走不走 event log 还没统一。
4. 系统发现问题时，哪些是证据、哪些是解释、哪些是用户确认，还混在一起。
```

---

## P0 - 明天优先修

### 1. “忽略”不能自动变成“确认设定”

**问题：**

walkthrough 里，用户只是选择“忽略”矛盾，但后面自动写成：

```text
projectType: 灵异故事
setting: 姐姐是鬼魂
```

这等于系统替用户拍板：你这个项目是鬼片，姐姐是鬼。

**为什么严重：**

这违反核心原则：系统永远留余地，不下定论。用户点“忽略”只代表“现在别管”，不代表“我确认这是设定”。

**应改方向：**

- 只记录：用户忽略了这条提醒。
- 可以记录候选解释：可能是灵异设定，待用户确认。
- 不能写成 confirmed setting。

---

### 2. `项目偏好.json` 不能绕开 event log

**问题：**

walkthrough 里单独写了 `项目偏好.json`，而这个文件会影响后续矛盾检测。

如果它会影响系统判断，它就不能绕开 event log。

**为什么严重：**

否则会出现两个真相源：

```text
event log 说一套
项目偏好.json 说另一套
```

崩溃恢复、迁移、同步、重放时都不知道该听谁的。

**应改方向：**

- 影响检测的项目偏好必须通过 `SystemEvent` 入账。
- `项目偏好.json` 最多是从 event log 重建出来的投影，或纯 UI 配置。
- 如果某个项目偏好只影响界面、不影响判断，可以不进结构化故事状态，但也要说明边界。

---

### 3. 快挡不入账，不能再声称“恢复不重跑 LLM”

**问题：**

walkthrough 说：

```text
快挡只记录，不写 event log。
用户关闭时 event log 为空。
后台之后再慢挡提取。
```

如果用户彻底关掉程序，后台慢挡可能根本没跑。

**为什么严重：**

这时系统只能下次打开后重新读剧本文档，再让 AI 重新提取。  
这和“恢复靠重放 event log，不重跑 LLM”的说法冲突。

**应改方向：**

把真相源边界讲清楚：

```text
剧本文档 = 用户正文的真相源
event log = AI 结构化状态的真相源
```

如果 AI 还没提取完，下次打开补跑，这是“补提取”，不是“完全从 event log 恢复”。

---

### 4. 字段命名必须统一

**问题：**

spec 里用：

```text
event_id
schema_version
base_state_version
plot_events
continuity_events
```

walkthrough 里用：

```text
eventId
schemaVersion
baseStateVersion
plotEvents
continuityEvents
```

**为什么严重：**

人能猜，程序不能猜。后面写后端时会不知道该按哪份文档实现。

**应改方向：**

- 先决定 JSON 字段到底用 `snake_case` 还是 `camelCase`。
- spec、walkthrough、summary 必须完全一致。
- 最好后续补一份机器可验证 schema。

---

## P1 - 重大风险，修完 P0 后处理

### 5. 一次慢挡提取拆成多条事件，但没有批次边界

**问题：**

一次慢挡提取会写多条事件：

```text
创建角色
创建事实
创建情节事件
再创建事实
```

如果写到一半崩溃，日志合法，但状态是半截的。

**应改方向：**

- 增加 `batch_id` / `correlation_id` / `causation_id`。
- 或定义一次提取如何原子提交。

---

### 6. `event_id` 不足以做 LLM 提取幂等

**问题：**

如果同一段剧本文本被 AI 重试提取，生成了新的 UUID，就会重复写入同一事实。

**应改方向：**

- 拆分 `event_id` 和 `idempotency_key`。
- `idempotency_key` 应该来自：源文档版本 + 文本范围 + 提取器版本 + mutation 类型。

---

### 7. Fact 缺少原文锚点

**问题：**

Fact 现在能说“姐姐十年前死亡”，但没有明确记录：

```text
来自哪份剧本文档？
哪一版？
第几段？
原文是哪一句？
后来是否被删改？
```

**为什么严重：**

用户改掉原文后，旧 Fact 可能仍然残留，系统继续用旧事实报矛盾。

**应改方向：**

Fact 需要补：

```text
source_document_id
source_revision
source_span
source_text_hash
```

并设计：

```text
fact.retracted
fact.superseded
```

---

### 8. `confidence` 混了三种意思

**问题：**

现在 `confidence` 同时像是在表示：

```text
AI 是否看对原文
这是不是矛盾
用户是不是故意这么写
```

这三件事不是一回事。

**应改方向：**

拆成：

```text
extraction_confidence
contradiction_confidence
intent_hypothesis_confidence
```

其中“用户是不是故意的”必须最谨慎，不能直接驱动确认设定。

---

### 9. `ContinuityEvent` 缺投递层

**问题：**

现在 `ContinuityEvent` 只记录发现本身，缺少：

```text
delivery_mode
interrupt_risk
armor_level
initiator
flow_blocked
```

**为什么重要：**

系统发现问题，不等于可以提醒用户。Timing Policy 必须决定什么时候说、怎么说、说多厚。

**应改方向：**

补投递层，或明确由单独 delivery queue 管。

---

### 10. `possible_reasons` 不该由后台 Agent 写死

**问题：**

“灵异故事 / 假死 / 笔误 / 梦境”这些是解释，不是证据。

后台矛盾监控 Agent 应该只提交证据。

**应改方向：**

- 后台只存 evidence 和 finding。
- possible reasons 由 Dialogue Gateway 在用户可见表达时临场生成。

---

### 11. 用文件修改时间判断是否处理完成不可靠

**问题：**

walkthrough 用“event log 最后事件时间”和“剧本文档修改时间”对比，判断是否处理完成。

文件修改时间会被同步、复制、时区、文件系统精度影响。

**应改方向：**

`story_state.json` 需要记录：

```text
log_head_seq
head_event_id
projection_schema_version
source_document_revision
checksum
```

---

## P2 - 文档清理

### 12. `UserPreference` / `Settings` / 项目偏好口径未统一

**问题：**

proposal、design、spec、summary 里仍混用：

```text
UserPreference
settings
项目偏好
用户偏好
用户记忆
```

**应改方向：**

统一三层：

```text
用户记忆 = 跨项目，关于这个人
项目偏好 = 单项目，关于这个项目
ContinuityEvent 状态 = 单个问题当前怎么处理
```

---

### 13. 路线图和问题清单状态过期

**问题：**

路线图和问题清单仍说 walkthrough 还没做，但 summary 已经说完成。

**应改方向：**

修完本问题单后，统一更新：

```text
docs/路线图.md
docs/问题清单-待解决.md
```

---

### 14. 中文文件名和 `snake_case` 规范冲突

**问题：**

summary 说文件名统一 `snake_case`，但 walkthrough 写：

```text
项目偏好.json
剧本/当前剧本.md
```

**应改方向：**

内部稳定路径建议用 ASCII：

```text
project_preferences.json
script/current.md
```

界面上仍然可以显示中文：

```text
项目偏好
当前剧本
```

---

## 明天建议处理顺序

1. 先修“忽略不等于确认设定”。
2. 再修“项目偏好必须入账或明确只是投影”。
3. 统一字段命名。
4. 明确剧本文档与 event log 的双真相源边界。
5. 再处理 batch、idempotency、source anchor、confidence 拆分。
6. 最后更新路线图和问题清单。

---

## 当前归档建议

**暂不归档。**

等 P0 修完、P1 至少形成明确后续任务后，再考虑 archive。
