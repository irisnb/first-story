## Why

当前项目已经决定以 append-only event log 作为事实源、`story_state.json` 作为可重建投影，但还没有 OpenSpec 规格承接这个决定。没有最小故事状态模型与事件日志规则，提取 Agent、矛盾监控、用户偏好降权和后续 UI 都没有稳定地基。

这个变更把 P0-0 的真相源裁决和 P0-0b 的最小数据模型缺口收束成第一个可验收的 OpenSpec change，只覆盖 MVP 闭环所需的状态基础。

## What Changes

- 定义 append-only event log 的最小行为边界：只追加、不擦旧、支持幂等去重、支持批次边界、支持从日志重放恢复已接受投影。
- 定义 `story_state.json` 的角色：当前状态投影，而非单一真相源。
- 定义 MVP 所需的最小故事状态对象：`Character`、`PlotEvent`、`Fact`、`ContinuityEvent`、`project_preferences`，并补充账本层 `SystemEvent`。
- 明确双真相源边界：剧本文档是用户正文真相源，event log 是 AI 结构化状态与判断偏好的真相源。
- 定义故事时间字段的责任边界：数据模型必须能表达绝对/相对/未知时间，提取 Agent 负责从自然语言解析到该结构。
- 定义矛盾证据引用规则：`ContinuityEvent.evidence_fact_ids` 指向 `Fact`，`Fact` 可追溯到来源 `SystemEvent` 与原文锚点。
- 明确本变更不实现 UI、不接真实 LLM、不接 LightRAG、不选择完整技术栈、不实现完整多 Agent 编排。

## Capabilities

### New Capabilities
- `event-log`: append-only 系统事件日志、幂等键、批次边界、版本锚点、投影重放与恢复规则。
- `minimal-story-state`: MVP 故事状态投影对象、事实引用、故事时间表达、矛盾证据、项目偏好降权与显式确认的最小结构。

### Modified Capabilities

- None.

## Impact

- 影响 OpenSpec 规格层：新增 `event-log` 与 `minimal-story-state` 两个能力规格。
- 影响后续实现顺序：提取 Agent、矛盾监控、ChatUI 提醒、用户偏好降权都必须以本状态基础为前置。
- 影响现有设计文档口径：与 `AGENTS.md`、`架构总览.md`、`docs/问题清单-待解决.md` 中已记录的 event log 真相源决策保持一致。
- 暂不引入应用代码、运行时依赖、数据库选型或外部服务。
