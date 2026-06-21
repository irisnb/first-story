## 1. 扩展 DialogueResult 和 ContextSummaryService

- [x] 1.1 在 `DialogueResult` dataclass 中添加 `turn_count: int` 字段
- [x] 1.2 在 `ContextSummaryService` 中添加 `update_and_persist()` 方法，整合生成摘要 + 写事件 + 重建投影
- [x] 1.3 在 `ContextSummaryService` 中添加 `_write_summary_event()` 私有方法，写入 `context_summary.updated` 事件

## 2. 修改 DialogueAgent

- [x] 2.1 修改 `respond()` 方法，在写入用户消息后同时写入带 `turn_count` 的 `context_summary.updated` 事件
- [x] 2.2 修改 `respond()` 方法，读取当前 `turn_count` 并递增
- [x] 2.3 修改 `DialogueResult` 返回值，包含当前 `turn_count`
- [x] 2.4 添加 `_get_current_turn_count()` 方法，从 story_state 读取当前轮数

## 3. 修改 ProjectService

- [x] 3.1 添加 `get_context_summary_service()` 方法，返回配置好的 `ContextSummaryService` 实例

## 4. 修改 Chat API

- [x] 4.1 添加 `_run_context_summary_update()` 后台任务函数
- [x] 4.2 在 `/chat` endpoint 中检查 `result.turn_count`，判断是否触发摘要更新
- [x] 4.3 触发时添加 `background_tasks.add_task()` 调度摘要更新

## 5. 测试与验证

- [x] 5.1 添加 `tests/test_context_summary_trigger.py`，测试轮数递增和摘要触发（7 个测试全部通过）
- [x] 5.2 手动测试：发送 10 条消息，确认小摘要触发
- [x] 5.3 手动测试：发送 30 条消息，确认大摘要触发
- [x] 5.4 验证：摘要生成失败时对话正常，旧摘要保留（后台任务不阻塞响应）
- [x] 5.5 运行全量测试 `pytest`，确认无回归（161 passed）
