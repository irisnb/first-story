## 1. 基础设施 - 数据模型

- [x] 1.1 创建 `ModuleDocument` 数据模型（name, sections, revision, checksum）
- [x] 1.2 创建 `ModuleLock` 数据模型（module, user_id, timestamp, ttl）
- [x] 1.3 创建 `ClassificationResult` 数据模型（module, section, content, confidence）
- [x] 1.4 修改 `StoryState` 添加 `modules` 字段

## 2. 基础设施 - MD 解析器

- [x] 2.1 添加 `markdown-it-py` 依赖
- [x] 2.2 创建 `ModuleParser` 服务，解析 MD 文档提取 sections
- [x] 2.3 创建 `ModuleRenderer` 服务，将结构化内容渲染回 MD
- [x] 2.4 实现 `append_to_section()` 方法，追加列表项到指定 section

## 3. 基础设施 - 模块文档存储

- [x] 3.1 创建默认模块模板（world.md, characters.md, plot.md, theme.md, structure.md）
- [x] 3.2 在项目创建时初始化五个模块文档
- [x] 3.3 创建 `ModuleDocumentService` 管理文档读写

## 4. 分类 API

- [x] 4.1 设计分类 prompt 模板
- [x] 4.2 实现 `POST /api/v1/projects/{project_id}/classify` 端点
- [x] 4.3 实现分类逻辑：调用 LLM 判断内容归属
- [x] 4.4 实现上下文注入：传入当前模块摘要
- [ ] 4.5 添加分类结果测试用例

## 5. 模块文档 API

- [x] 5.1 实现 `GET /api/v1/projects/{project_id}/modules/{module}` 端点
- [x] 5.2 实现 `PUT /api/v1/projects/{project_id}/modules/{module}` 端点
- [x] 5.3 更新 `ProjectService` 支持模块文档管理

## 6. 乐观锁机制

- [x] 6.1 实现 `POST /api/v1/projects/{project_id}/modules/{module}/lock` 端点
- [x] 6.2 实现 `DELETE /api/v1/projects/{project_id}/modules/{module}/lock` 端点
- [x] 6.3 实现锁存储（内存 + 可选持久化）
- [x] 6.4 实现锁过期检查和强制获取
- [x] 6.5 实现系统添加队列

## 7. 对话流程集成

- [ ] 7.1 修改 `DialogueAgent`，candidate 消息后触发分类
- [ ] 7.2 分类结果写入对应模块文档
- [ ] 7.3 MD 变更触发解析 → 生成事件日志
- [ ] 7.4 添加 `module_document.updated` 事件类型

## 8. 投影器更新

- [ ] 8.1 修改 `ProjectorService` 处理 `module_document.updated` 事件
- [ ] 8.2 实现从 MD 文档重建 modules 状态
- [ ] 8.3 更新 `story_state.json` 结构

## 9. 前端 - 模块画布 UI

- [ ] 9.1 创建 `ModulesView` 组件
- [ ] 9.2 实现五模块卡片展示
- [ ] 9.3 实现模块文档编辑器（Markdown 编辑）
- [ ] 9.4 实现编辑锁获取/释放逻辑
- [ ] 9.5 实现系统添加队列指示器

## 10. 数据迁移

- [ ] 10.1 创建迁移脚本：扁平列表 → MD 文档
- [ ] 10.2 测试迁移脚本
- [ ] 10.3 验证迁移后数据完整性

## 11. 测试与验证

- [ ] 11.1 单元测试：MD 解析器和渲染器
- [ ] 11.2 单元测试：分类 API
- [ ] 11.3 单元测试：乐观锁机制
- [ ] 11.4 集成测试：对话流程 → 分类 → 写入 MD
- [ ] 11.5 端到端测试：前端编辑 → 锁 → 保存 → 队列处理
- [ ] 11.6 全量测试通过
