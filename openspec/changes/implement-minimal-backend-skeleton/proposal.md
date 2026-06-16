## Why

项目已完成地基施工图（event-log 和 minimal-story-state 规格），但尚无可运行的后端代码。没有后端骨架，后续的 Agent 链路、UI 闭环都无法落地。本变更将已验证的规格转化为可运行的 Python + FastAPI 后端，为后续开发提供稳定的代码基础。

## What Changes

- 创建 Python 后端项目结构（FastAPI 框架）
- 实现 `SystemEvent` 的完整 Pydantic 数据模型
- 实现 `StoryState` 投影的完整 Pydantic 数据模型
- 实现 Event Log 服务：追加事件、幂等去重、批次边界、JSONL 存储
- 实现 Projector 服务：从 event log 重放事件并重建 story_state 投影
- 实现 Project 服务：项目创建、打开、列出、文件夹结构管理
- 实现最小 REST API：事件追加、事件列表、状态查询、投影重建、项目管理
- 实现单元测试覆盖核心逻辑
- 配置 FastAPI 自动文档生成

## Capabilities

### New Capabilities

- `backend-api`: REST API 服务，提供事件追加、状态查询、项目管理等接口
- `event-log-service`: Event Log 读写服务，实现幂等去重、批次边界、JSONL 存储
- `projector-service`: 投影重建服务，从 event log 重放事件并重建 story_state
- `project-service`: 项目管理服务，创建/打开/列出项目，管理文件夹结构

### Modified Capabilities

无。本变更是新增实现，不修改现有规格。

## Impact

- 新增 `backend/` 目录，包含完整 Python 后端代码
- 依赖现有规格 `event-log` 和 `minimal-story-state` 作为数据模型定义
- 后续 Agent 和 UI 将依赖本变更提供的 API
- 引入 Python 生态依赖：FastAPI、Pydantic、uvicorn 等
