## ADDED Requirements

### Requirement: 保存正文版本
系统 SHALL 将每次正文保存记录为 event log 上一条 `document.revised` 事件，包含正文内容、source hash 与 source span。

#### Scenario: 保存生成新版本
- **WHEN** 用户保存正文
- **THEN** 系统追加一条 `document.revised` 事件，记录正文内容与对应的 source hash

#### Scenario: 不覆盖旧版本
- **WHEN** 用户多次保存同一文档
- **THEN** 系统保留每一次保存的历史版本，旧版本事件永不被擦除或覆盖

### Requirement: 列出历史版本
系统 SHALL 提供接口列出某文档的所有历史版本及其元数据。

#### Scenario: 查看版本列表
- **WHEN** 用户请求某文档的版本历史
- **THEN** 系统返回按时间排序的版本列表，每项含版本标识与保存时间

### Requirement: 回到旧版本
系统 SHALL 允许用户将正文恢复到某个历史版本。

#### Scenario: 恢复到指定版本
- **WHEN** 用户选择某个历史版本并请求恢复
- **THEN** 系统通过重放事件重建该版本正文，并以追加新事件的方式（非删除）记录这次恢复

### Requirement: source span 可定位
系统 SHALL 记录提取结果对应的正文 source span，使后续证据可定位回原文位置。

#### Scenario: 提取结果带原文定位
- **WHEN** 提取能力从某版本正文中产出 Fact
- **THEN** 该 Fact 关联到正文中对应文本片段的 source span
