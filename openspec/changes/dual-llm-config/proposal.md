## Why

当前系统只有一个全局 LLM 配置，但不同功能对 LLM 的需求不同：
- **主聊天窗口**：需要高质量、响应快的模型（如 GPT-4、Claude）
- **后台任务**（分类、摘要）：可以用更便宜的模型，不需要最高质量

用户希望独立配置这两个 API，实现成本优化和灵活性。

## What Changes

- **新增**：`LLMConfig` 数据模型，支持多个配置方案
- **新增**：`ProjectLLMConfig` 数据模型，关联项目和配置
- **新增**：`GET/PUT /api/v1/projects/{id}/llm-config` 端点
- **新增**：两个预定义配置槽位：`chat`（主聊天）、`utility`（后台任务）
- **修改**：`LLMProvider` 支持动态配置切换
- **新增**：API Key 安全存储（加密）

## Capabilities

### New Capabilities

- `llm-config`: LLM 配置管理，支持多配置方案和安全存储

### Modified Capabilities

- `minimal-story-state`: 无变更（配置独立存储）

## Impact

- **后端**：新增 LLM 配置模型、API 端点、加密存储
- **前端**：后续统一添加设置面板 UI
- **安全**：API Key 加密存储，前端只显示后 4 位
