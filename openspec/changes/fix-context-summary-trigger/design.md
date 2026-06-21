## Context

### 当前状态

分层摘要的数据层已完整实现：
- `ContextSummary` 数据模型（`models/state.py`）
- `context_summary.updated` 事件类型（`models/events.py`）
- `ContextSummaryService` 服务（`services/context_summary.py`）
- 投影器处理 `context_summary.updated`（`services/projector.py`）
- `dialogue._build_prompt()` 已注入 `context_summary`

但触发逻辑缺失：
- `dialogue.py` 定义了常量但未使用
- `turn_count` 始终为 0
- 摘要永远不会自动更新

### 约束

- 摘要更新必须是后台任务，不阻塞对话响应
- 摘要生成失败不影响对话，继续使用旧摘要
- 必须使用现有的事件日志机制，保持 append-only

## Goals / Non-Goals

**Goals:**
- 实现对话轮数自动计数
- 每 10 轮触发小摘要更新（仅 `recent_focus`）
- 每 30 轮触发大摘要更新（全部字段）
- 摘要更新作为后台任务执行，不阻塞对话
- 更新结果通过事件日志持久化

**Non-Goals:**
- 不修改前端代码
- 不修改现有数据模型结构
- 不实现手动触发摘要更新（可作为后续扩展）

## Decisions

### D1: 轮数存储位置

**决定**：轮数存储在 `context_summary.turn_count`，通过 `context_summary.updated` 事件更新。

**理由**：
- 与现有数据模型一致
- 轮数变化也是状态变化，应该走事件日志
- 避免引入新的状态存储机制

**替代方案**：
- 每次对话时实时计算轮数（遍历事件日志）→ 性能差
- 单独文件存储 → 增加复杂度

### D2: 触发时机

**决定**：在 `DialogueAgent.respond()` 成功返回后，在 API 层检查并调度后台任务。

**理由**：
- `respond()` 方法只负责对话，不应包含后台调度逻辑
- API 层已有 `BackgroundTasks` 的使用模式（candidate extraction）
- 保持 `DialogueAgent` 单一职责

**数据流**：
```
chat.py:
  1. 调用 agent.respond()
  2. 检查 result.turn_count % 10 == 0 或 % 30 == 0
  3. 如果触发，添加 background_tasks.add_task()
```

### D3: 摘要更新函数签名

**决定**：新增 `_run_context_summary_update(project_service, project_id, summary_type)` 函数。

**理由**：
- 与现有 `_run_candidate_extraction` 模式一致
- 接收 `project_service` 以获取所有必要服务
- `summary_type` 区分小摘要和大摘要

### D4: ContextSummaryService 扩展

**决定**：添加 `update_and_persist()` 方法，整合生成 + 写事件 + 重建投影。

**理由**：
- 服务层封装完整操作
- 避免在 API 层直接操作事件日志
- 保持投影重建的一致性

**方法签名**：
```python
def update_and_persist(
    self,
    summary_type: str,  # "minor" | "major"
    current_turn_count: int,
) -> None:
    # 1. 获取最近对话
    # 2. 调用 generate_minor/generate_major
    # 3. 写 context_summary.updated 事件
    # 4. 调用 projector.rebuild()
```

## Risks / Trade-offs

### R1: LLM 调用失败

**风险**：摘要生成时 LLM 调用可能失败，导致摘要不更新。

**缓解**：
- `ContextSummaryService` 已有失败隔离逻辑，返回空摘要
- 不影响对话，继续使用旧摘要
- 日志记录失败原因

### R2: 后台任务堆积

**风险**：用户快速发送消息，可能导致多个摘要更新任务堆积。

**缓解**：
- 摘要更新是幂等的（只更新最新状态）
- 30 轮才触发一次大摘要，频率可控
- 可考虑添加任务去重（V1 不实现）

### R3: Token 成本增加

**风险**：摘要生成增加 LLM 调用成本。

**缓解**：
- 每 10 轮才触发一次小摘要
- 小摘要输入仅 10 轮对话，成本较低
- 大摘要 30 轮一次，性价比合理

### R4: 轮数计数准确性

**风险**：如果用户消息被标记为 `ignore`，是否应该计入轮数？

**决定**：只计用户消息数，不区分 intent。理由：
- 用户发了消息就是一轮交互
- `ignore` 只是表示"不提取"，不影响计数
- 简化实现逻辑
