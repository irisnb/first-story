## ADDED Requirements

### Requirement: 粘贴导入已有剧本
系统 SHALL 允许用户粘贴已有剧本文本导入到当前项目。

#### Scenario: 导入已有剧本
- **WHEN** 用户粘贴一段已有剧本文本并确认导入
- **THEN** 系统将其作为正文载入编辑器，并记录为一条 `document.revised` 事件

#### Scenario: 导入后可被提取
- **WHEN** 用户导入剧本后触发提取
- **THEN** 系统对导入正文执行与手写正文相同的 Fountain 解析与 LLM 提取流程

### Requirement: 导出 Fountain 与纯文本
系统 SHALL 允许用户将当前正文导出为 Fountain 或纯文本格式。

#### Scenario: 导出 Fountain
- **WHEN** 用户选择导出为 Fountain
- **THEN** 系统输出保留 Fountain 语法结构的文本文件

#### Scenario: 导出纯文本
- **WHEN** 用户选择导出为纯文本
- **THEN** 系统输出去除标记的可读纯文本文件
