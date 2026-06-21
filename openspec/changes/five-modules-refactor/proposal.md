## Why

当前系统将所有提取的内容存放在扁平的 `facts[]`、`plot_events[]`、`characters[]` 列表中，用户无法直接编辑、无法看到"不断完善的世界观文档"形式。用户期望每个模块（世界观/角色/情节/主题/结构）是一个可编辑的 MD 文档，系统自动整理和追加内容。

## What Changes

- **新增**：五模块 MD 文档作为用户可见的真相源（world.md, characters.md, plot.md, theme.md, structure.md）
- **新增**：独立的分类 API，判断用户内容应该追加到哪个模块的哪个 section
- **新增**：MD 文档解析器（remark AST），将 MD 变更同步到事件日志
- **新增**：乐观锁机制，支持用户编辑时锁定文档，系统添加排队等待
- **新增**：前端画布 UI 展示五模块文档
- **修改**：对话流程集成分类 API，分类结果写入对应 MD 文档
- **迁移**：现有扁平列表数据迁移到新的 MD 文档格式

## Capabilities

### New Capabilities

- `module-documents`: 五模块 MD 文档的存储、读取、解析、渲染能力
- `classify-api`: 独立的分类 API，判断内容归属哪个模块和 section
- `optimistic-lock`: 乐观锁机制，用户编辑时锁定文档，系统添加排队
- `module-canvas-ui`: 前端画布 UI 展示和编辑五模块文档

### Modified Capabilities

- `minimal-story-state`: 状态模型从扁平列表改为基于 MD 文档的结构化数据

## Impact

- **后端**：新增 modules API、分类 API、锁 API；修改提取流程
- **前端**：新增画布 UI、文档编辑器；修改状态面板
- **数据模型**：新增 ModuleDocument、ModuleLock；修改 StoryState 结构
- **成本**：每条消息增加 ~550 tokens（分类 API）
- **迁移**：需要数据迁移脚本
