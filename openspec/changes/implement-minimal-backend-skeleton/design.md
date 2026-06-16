## Context

项目已完成 OpenSpec 规格定义阶段：
- `event-log` 规格：定义了 append-only 事件日志的行为边界
- `minimal-story-state` 规格：定义了 MVP 故事状态投影的数据结构

当前状态：规格已验证通过，但没有实现代码。本变更是第一个实现变更，将规格转化为可运行的 Python 后端。

技术约束：
- 数据模型必须严格遵循 `event-log` 和 `minimal-story-state` 规格
- 存储方案使用纯文件（JSONL + JSON），方便调试和迁移
- 后续需要接真实 LLM，技术栈选择 Python + FastAPI

## Goals / Non-Goals

**Goals:**

- 实现 Event Log 服务的核心功能：追加事件、幂等去重、批次边界、JSONL 存储
- 实现 Projector 服务：从 event log 重放事件并重建 story_state 投影
- 实现 Project 服务：项目创建、打开、列出、文件夹结构管理
- 实现最小 REST API：事件追加、事件列表、状态查询、投影重建、项目管理
- 提供完整的 Pydantic 数据模型，与规格一一对应
- 单元测试覆盖核心逻辑
- FastAPI 自动文档生成

**Non-Goals:**

- 不实现 Agent 相关功能（提取、矛盾监控等）
- 不实现 LLM 调用
- 不实现 LightRAG 集成
- 不实现 UI
- 不实现用户认证和权限
- 不实现数据库（使用纯文件存储）

## Decisions

### 1. 技术栈：Python 3.11+ + FastAPI + Pydantic v2

**Decision:** 使用 Python 3.11+ 作为运行环境，FastAPI 作为 Web 框架，Pydantic v2 作为数据验证库。

**Rationale:** 
- Python AI/LLM 生态最成熟（OpenAI SDK、Anthropic SDK、LightRAG、LangGraph 都是 Python 优先）
- FastAPI 现代化：异步原生支持、自动 OpenAPI 文档、依赖注入系统
- Pydantic v2 性能优秀，类型注解与规格自然对应

**Alternatives considered:**
- Node.js + Express：AI 生态弱，类型安全需额外配置
- Go：AI 生态几乎为零
- Flask：异步支持弱，不够现代

### 2. 存储方案：纯文件（JSONL + JSON）

**Decision:** 使用 JSONL 文件存储 event log，JSON 文件存储 story_state 投影。

**Rationale:**
- 当前规格就是基于 JSONL 设计的
- 方便调试（直接看文件内容）
- 无需数据库依赖，降低部署复杂度
- 后续迁移到 SQLite/PostgreSQL 很简单（抽象层已设计）

**Alternatives considered:**
- SQLite 作为 event log 存储：查询更快，但增加抽象层复杂度，暂时不必要
- 内存数据库：无法持久化，不符合规格要求

### 3. 项目结构：分层架构

**Decision:** 采用分层架构：models → services → api。

```
backend/
├── app/
│   ├── models/      # Pydantic 数据模型
│   ├── services/    # 核心业务逻辑
│   ├── api/         # FastAPI 路由
│   └── main.py      # 应用入口
└── tests/           # 单元测试
```

**Rationale:**
- 清晰的关注点分离
- 数据模型与规格一一对应
- 服务层可独立测试
- API 层薄，便于后续扩展

### 4. 幂等去重：内存索引 + 文件扫描

**Decision:** 幂等去重使用两层机制：
1. 内存维护 `idempotency_key → seq` 索引
2. 启动时扫描 event log 文件重建索引

**Rationale:**
- 简单可靠，无额外依赖
- 对于 MVP 阶段的项目规模足够
- 后续可优化为持久化索引

### 5. 投影重建：事件重放

**Decision:** 投影重建通过按 `seq` 顺序重放所有事件实现。

**Rationale:**
- 完全符合规格要求
- 实现简单，逻辑清晰
- 易于调试和验证

### 6. API 设计：REST 风格

**Decision:** API 设计遵循 REST 风格，资源命名清晰。

| 端点 | 方法 | 功能 |
|------|------|------|
| `/projects` | GET, POST | 列出/创建项目 |
| `/projects/{id}` | GET | 获取项目详情 |
| `/projects/{id}/events` | GET, POST | 列出/追加事件 |
| `/projects/{id}/state` | GET | 获取当前投影 |
| `/projects/{id}/state/rebuild` | POST | 强制重建投影 |

**Rationale:**
- REST 风格符合业界惯例
- 资源嵌套反映数据关系
- FastAPI 自动生成 OpenAPI 文档

## Risks / Trade-offs

### Risk: 文件存储并发安全

**Risk:** 多进程同时写入 JSONL 文件可能导致数据损坏。

**Mitigation:** 
- MVP 阶段假设单进程运行
- 使用文件锁（`fcntl` 或 `msvcrt`）作为后续增强
- 后续可迁移到 SQLite 解决并发问题

### Risk: 内存索引丢失

**Risk:** 进程崩溃后内存索引丢失，需要重新扫描文件。

**Mitigation:** 
- 启动时自动重建索引
- 扫描性能对于 MVP 规模可接受（数千事件）
- 后续可持久化索引

### Risk: 投影重建性能

**Risk:** 事件数量增长后，投影重建可能变慢。

**Mitigation:**
- MVP 阶段事件数量有限，性能可接受
- 后续可实现快照机制（定期保存投影快照）

### Trade-off: 不实现认证授权

**Trade-off:** MVP 不实现用户认证和授权。

**Reason:** 当前阶段聚焦核心功能，认证授权在产品化阶段再添加。

## Open Questions

无。本变更范围明确，技术决策已确定。
