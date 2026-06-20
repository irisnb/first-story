## Why

最小后端骨架（节点 3）已完成：event log 能追加、能重放、能重建 story_state。但用户**还不能在上面写故事**——没有写作界面，没有能看懂剧本的 AI 能力。

上一次实现"最小写作闭环"（commit `10e3edd`）已被回退，因为效果非常差。根因不是参数没调好，而是方法论错误：提取 Agent 用纯规则（`[一-龥]{2,4}` 正则把任意 2-4 个连续中文字当人名，9 个词的黑名单过滤，状态靠"死了/活着"关键词硬匹配）。这在中文叙事文本上不可能 work——garbage in，矛盾监控再准也是 garbage out。项目文档第 291 行早就写过对策"死规矩先行 + 结果喂给 LLM"，但失败的 MVP 只做了"死规矩"、没接 LLM。

本次重做这条闭环，修掉根因（LLM 提取替代纯规则），并把范围锁定在**单人编剧用 Fountain 写完一个几千字短剧本全程顺手**。

## What Changes

- **写作主表面**：新增极简 Fountain 剧本编辑器（场景标题/角色名/对白高亮），替代上一版的"后台操作面板"
- **文档版本链路**：新增 document revision API（正文 + source hash + source span 读写），用户正文每轮立即落盘
- **LLM 提取**：用真实大模型提取事件/角色状态，替代被回退的纯规则提取。**BREAKING**（相对失败 MVP）：提取方法论从 rule-based 改为 Fountain 结构解析 + LLM 语义提取
- **角色识别走 Fountain 结构**：剧本角色名是结构化的（对白前居中大写行），系统直接读格式确定角色，不再"猜人名"——绕过上次失败的最大根因
- **矛盾监控接真实提取结果**：检测硬矛盾（如"姐姐十年前死亡却昨天打电话"），生成证据卡
- **信任机制**：证据卡支持忽略/接受，系统记住偏好（降权而非删除）；温和措辞极简版（不做完整五层叠甲）
- **导入导出**：粘贴已有剧本导入；导出 Fountain / 纯文本
- **LLM 接口层**：多模型支持 + API key 配置 + 基础 token 成本追踪
- **防漂锚**：在 design.md 固化两节——「灵魂清单」（AGENTS.md 不可动摇内核）+「长大路标」（延后的 Agent/机制排队清单），防止 MVP 偏离原始愿景或停在玩具版

明确**不做**（留到后续 change）：完整六大 UI、自动语义合并版本树、协作/多人、LightRAG 灵感检索、LangGraph 多 Agent、心流自动识别/涟漪/伏笔/渐进提问、生成 Agent（代笔）、Final Draft/Word 格式、完整五层叠甲系统、显式薄 Hub 调度层。

## Capabilities

### New Capabilities
- `screenplay-editor`: Fountain 剧本编辑器——文本输入、Fountain 语法高亮（场景标题/角色名/对白）、自动存盘、关闭重开内容保留
- `document-revision`: 正文版本链路——保存 revision、source hash、source span、历史版本列表、回到旧版本
- `llm-extraction`: LLM 提取能力——Fountain 结构解析确定角色，LLM 语义提取事件与角色状态变化，输出结构化 Fact
- `contradiction-detection`: 矛盾监控——基于真实提取的 Fact 检测硬矛盾，生成 ContinuityEvent 证据卡
- `evidence-card-handling`: 证据卡处理——用户忽略/接受，偏好落地为 project_preferences 降权规则；温和非裁判措辞
- `screenplay-import-export`: 剧本导入导出——粘贴导入已有剧本，导出 Fountain / 纯文本
- `llm-provider`: LLM 接口层——多模型支持、API key 配置、基础 token 成本追踪

### Modified Capabilities
<!-- 现有 event-log 与 minimal-story-state 规格的需求不变，仅在其上叠加新能力，无需 delta -->

## Impact

- **新增前端**：`frontend/`（技术栈待 design 决策，推荐 React+Vite，复用回退 MVP 的现成参考）
- **新增后端服务**：`backend/app/services/` 下新增 document / extraction（LLM 版）/ contradiction / llm_provider；`backend/app/api/` 下新增 documents / preferences / extraction 触发端点
- **新增模型**：`backend/app/models/` 下补 documents 模型（失败 MVP 残留的 `.pyc` 已清理，源码重写）
- **新增依赖**：LLM SDK（按选定 provider）、Fountain 解析库（或自实现最小解析器）
- **配置**：新增 LLM API key、模型选择、token 预算的环境变量配置
- **安全**：LLM API key 不入库、不回显；外部 LLM 调用需走代理（git config 已有 `http://127.0.0.1:7890`）
- **不影响**：现有 event log / projector / project 服务与 54 个通过的测试保持不变
