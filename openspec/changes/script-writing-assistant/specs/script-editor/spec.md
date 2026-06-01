## ADDED Requirements

### Requirement: 双模式创作
系统 SHALL 提供辅助模式和生成模式两种创作方式，且两种模式产出的内容可互相转换。

#### Scenario: 辅助模式
- **WHEN** 用户选择辅助模式
- **THEN** 系统提供模块画布和编辑工具，用户主导创作过程，工具提供建议、参考和自检

#### Scenario: 生成模式
- **WHEN** 用户选择生成模式并提供创意描述
- **THEN** 系统基于知识库和用户描述生成剧本内容

#### Scenario: 模式互通
- **WHEN** 用户在生成模式产出的剧本中切换为辅助模式
- **THEN** 系统保留生成内容，用户可自由编辑、修改、迭代

### Requirement: Fountain 格式编辑与渲染
系统 SHALL 支持 Fountain 纯文本格式的编辑，并实时渲染为专业剧本样式。

#### Scenario: Fountain 语法渲染
- **WHEN** 用户输入符合 Fountain 语法的内容（场景标题、角色名、对白等）
- **THEN** 系统实时渲染为专业剧本排版样式

#### Scenario: 格式自动提示
- **WHEN** 用户输入疑似场景标题的内容（如以 INT./EXT. 开头）
- **THEN** 系统自动应用场景标题样式

### Requirement: 剧本导出
系统 SHALL 支持将剧本导出为 PDF（专业排版）和 Word（可编辑）格式。

#### Scenario: 导出为 PDF
- **WHEN** 用户选择"导出 PDF"
- **THEN** 系统生成符合行业排版规范的 PDF 文件

#### Scenario: 导出为 Word
- **WHEN** 用户选择"导出 Word"
- **THEN** 系统生成保留格式的 .docx 文件，用户可在 Word 中继续编辑

### Requirement: AI 功能需用户主动触发
系统 SHALL NOT 在未经用户主动激活的情况下调用 AI 生成内容，以控制成本和尊重创作者主导权。

#### Scenario: AI 功能未激活
- **WHEN** AI 辅助功能未被用户激活
- **THEN** 系统仅使用本地知识库检索，不调用外部 API 或生成内容

#### Scenario: 用户主动触发 AI
- **WHEN** 用户点击 AI 辅助按钮并输入需求
- **THEN** 系统调用 AI 并返回结果

### Requirement: 大白话交互
系统 SHALL 以日常用语与用户交互，不使用学术术语或剧作理论套话，即使底层对照了专业理论。

#### Scenario: 自检反馈用大白话
- **WHEN** 系统自检发现某处节奏问题
- **THEN** 输出如"这段的感觉有点拖，读者可能会走神。要不要试试把前面两段对话精简一下？"而非引用理论术语
