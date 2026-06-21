## Why

分层摘要功能的数据模型和服务已实现，但触发逻辑缺失。`dialogue.py` 定义了常量 `_MINOR_SUMMARY_TURNS = 10` 和 `_MAJOR_SUMMARY_TURNS = 30`，但 `respond()` 方法中没有调用 `ContextSummaryService`。导致 `context_summary.turn_count` 始终为 0，摘要永远不会自动更新，LLM 无法获得项目上下文摘要的帮助。

## What Changes

- **新增**：`DialogueAgent.respond()` 中的轮数计数和摘要触发检查逻辑
- **新增**：后台摘要更新任务 `_run_context_summary_update()`
- **新增**：`ProjectService.get_context_summary_service()` 方法
- **新增**：`ContextSummaryService.update_and_persist()` 方法（生成摘要 + 写事件 + 重建投影）
- **修改**：`chat.py` 的 `/chat` endpoint，在对话完成后检查并调度摘要更新

## Capabilities

### New Capabilities

- `context-summary-trigger`: 对话轮数计数和分层摘要自动触发机制

### Modified Capabilities

- `dialogue-agent`: 新增轮数更新和摘要触发检查的职责

## Impact

**后端修改**：
- `backend/app/services/dialogue.py` — 添加轮数更新逻辑
- `backend/app/api/chat.py` — 添加后台摘要更新任务调度
- `backend/app/services/project.py` — 添加 `get_context_summary_service()` 方法
- `backend/app/services/context_summary.py` — 添加 `update_and_persist()` 方法

**无前端改动**：摘要更新是后端后台任务，前端无需修改

**无数据库改动**：使用现有的事件日志和投影机制
