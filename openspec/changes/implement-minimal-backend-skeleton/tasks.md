## 1. 项目初始化

- [x] 1.1 创建 backend 目录结构（app/models, app/services, app/api, tests）
- [x] 1.2 创建 pyproject.toml 配置文件（FastAPI, Pydantic, pytest 等依赖）
- [x] 1.3 创建 requirements.txt 供 pip 使用
- [x] 1.4 创建 backend/app/__init__.py 和子目录 __init__.py

## 2. 数据模型

- [x] 2.1 创建 backend/app/models/__init__.py 导出所有模型
- [x] 2.2 创建 backend/app/models/common.py 定义通用类型（StoryTime, SourceSpan 等）
- [x] 2.3 创建 backend/app/models/events.py 定义 SystemEvent 和事件类型枚举
- [x] 2.4 创建 backend/app/models/characters.py 定义 Character 模型
- [x] 2.5 创建 backend/app/models/plot_events.py 定义 PlotEvent 模型
- [x] 2.6 创建 backend/app/models/facts.py 定义 Fact 模型
- [x] 2.7 创建 backend/app/models/continuity.py 定义 ContinuityEvent 和 Delivery 模型
- [x] 2.8 创建 backend/app/models/preferences.py 定义 ProjectPreference 模型
- [x] 2.9 创建 backend/app/models/state.py 定义 StoryState 和 Story 投影模型
- [x] 2.10 创建 backend/app/models/project.py 定义 Project 元数据模型
- [x] 2.11 创建 backend/app/models/api.py 定义 API 请求/响应模型

## 3. Event Log 服务

- [x] 3.1 创建 backend/app/services/__init__.py 导出所有服务
- [x] 3.2 创建 backend/app/services/event_log.py 实现 EventLogService 类
- [x] 3.3 实现 append_event 方法：追加事件到 JSONL 文件
- [x] 3.4 实现 _assign_seq 方法：分配单调递增序号
- [x] 3.5 实现 _check_idempotency 方法：幂等去重检查
- [x] 3.6 实现 _build_idempotency_index 方法：启动时构建索引
- [x] 3.7 实现 read_events 方法：按 seq 顺序读取事件
- [x] 3.8 实现 get_events_by_batch 方法：按 batch_id 获取事件

## 4. Projector 服务

- [x] 4.1 创建 backend/app/services/projector.py 实现 ProjectorService 类
- [x] 4.2 实现 rebuild 方法：从 event log 重建投影
- [x] 4.3 实现 _process_character_created 方法
- [x] 4.4 实现 _process_character_status_updated 方法
- [x] 4.5 实现 _process_plot_event_created 方法
- [x] 4.6 实现 _process_fact_created 方法
- [x] 4.7 实现 _process_continuity_event_created 方法
- [x] 4.8 实现 _process_continuity_event_ignored 方法
- [x] 4.9 实现 _process_continuity_event_resolved 方法
- [x] 4.10 实现 _process_project_preference_events 方法
- [x] 4.11 实现 _save_projection 方法：持久化投影到 JSON 文件

## 5. Project 服务

- [x] 5.1 创建 backend/app/services/project.py 实现 ProjectService 类
- [x] 5.2 实现 create_project 方法：创建项目目录和文件
- [x] 5.3 实现 _generate_project_id 方法：生成唯一项目 ID
- [x] 5.4 实现 _init_project_files 方法：初始化项目文件结构
- [x] 5.5 实现 list_projects 方法：列出所有项目
- [x] 5.6 实现 get_project 方法：打开现有项目
- [x] 5.7 实现 _update_project_timestamp 方法：更新项目时间戳

## 6. API 路由

- [x] 6.1 创建 backend/app/api/__init__.py 导出所有路由
- [x] 6.2 创建 backend/app/api/projects.py 实现 /projects 端点
- [x] 6.3 创建 backend/app/api/events.py 实现 /projects/{id}/events 端点
- [x] 6.4 创建 backend/app/api/state.py 实现 /projects/{id}/state 端点

## 7. 应用入口

- [x] 7.1 创建 backend/app/config.py 配置管理
- [x] 7.2 创建 backend/app/main.py FastAPI 应用入口
- [x] 7.3 配置 CORS 中间件
- [x] 7.4 配置异常处理器
- [x] 7.5 配置依赖注入（服务实例）

## 8. 单元测试

- [x] 8.1 创建 tests/conftest.py 测试 fixtures
- [x] 8.2 创建 tests/test_models.py 测试数据模型
- [x] 8.3 创建 tests/test_event_log.py 测试 EventLogService
- [x] 8.4 创建 tests/test_projector.py 测试 ProjectorService
- [x] 8.5 创建 tests/test_project.py 测试 ProjectService
- [x] 8.6 创建 tests/test_api.py 测试 API 端点

## 9. 文档与收尾

- [x] 9.1 创建 backend/README.md 说明如何运行
- [x] 9.2 验证 OpenAPI 文档可访问（/docs）
- [x] 9.3 运行完整测试套件确保通过
- [ ] 9.4 提交代码到 git
