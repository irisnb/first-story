## 1. 数据模型

- [ ] 1.1 创建 `LLMConfigSlot` 类型（`chat` | `utility`）
- [ ] 1.2 创建 `LLMConfig` 数据模型
- [ ] 1.3 创建 `ProjectLLMConfig` 数据模型（项目级配置容器）
- [ ] 1.4 创建 `LLMConfigResponse` API 响应模型（带 masked key）

## 2. 加密服务

- [ ] 2.1 添加 `cryptography` 依赖
- [ ] 2.2 创建 `EncryptionService` 加密/解密服务
- [ ] 2.3 从环境变量读取加密密钥

## 3. 配置存储服务

- [ ] 3.1 创建 `LLMConfigService` 服务
- [ ] 3.2 实现 `load_config()` 从文件加载配置
- [ ] 3.3 实现 `save_config()` 保存配置（加密 API key）
- [ ] 3.4 实现 `get_config(slot)` 获取特定槽位配置
- [ ] 3.5 实现回退逻辑：项目配置 → 环境变量

## 4. API 端点

- [ ] 4.1 实现 `GET /api/v1/projects/{id}/llm-config` 列出所有配置
- [ ] 4.2 实现 `GET /api/v1/projects/{id}/llm-config/{slot}` 获取特定配置
- [ ] 4.3 实现 `PUT /api/v1/projects/{id}/llm-config/{slot}` 更新配置
- [ ] 4.4 更新 `ProjectService` 添加 `get_llm_config_service()` 方法

## 5. LLMProvider 更新

- [ ] 5.1 修改 `LLMProvider` 支持动态配置
- [ ] 5.2 修改 `DialogueAgent` 使用 `chat` 槽位配置
- [ ] 5.3 修改 `ClassifyService` 使用 `utility` 槽位配置
- [ ] 5.4 修改 `ContextSummaryService` 使用 `utility` 槽位配置

## 6. 项目初始化

- [ ] 6.1 修改 `_init_project_files()` 创建空配置文件
- [ ] 6.2 添加 `llm_config.json` 到 `.gitignore`

## 7. 测试与验证

- [ ] 7.1 单元测试：加密/解密服务
- [ ] 7.2 单元测试：配置存储服务
- [ ] 7.3 单元测试：API 端点
- [ ] 7.4 集成测试：配置回退逻辑
- [ ] 7.5 全量测试通过
