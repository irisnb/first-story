## Why

当前用户只能在编辑器里写正文，后台静默做提取/矛盾检测、把证据回流到证据栏。这只是"观察循环"，缺了 AGENTS.md 定义的**主入口——ChatUI 与对话 Agent**。没有对话框，就无法真正模仿用户使用本产品（自由聊创作、被温和提醒、自己决定），测试覆盖不到产品灵魂，工具与普通编辑器无异。

本变更把产品翻转成"**ChatUI 为绝对主角**"的形态：用户主要在聊天框里自由聊创作，对话 Agent 用温和、可忽略、非裁判的语言回应。但聊天是 explore（脑暴、假设、问答），不是写正文——所以引入**意图闸门**区分"闲聊/候选想法/正式设定"，用**采纳进正文**作为把聊天内容写进故事的唯一显式入口。验收标准是"完整写完一个短故事（几千字）全程顺手"，不是玩具 demo。

## What Changes

- 新增**薄 Hub（Runtime）**：路由、权限、调度的最小实现（进程内同步路由器）。对话 Agent 经 Hub 中转访问后台能力，严禁直调、严禁变 god-object（守 AGENTS.md 防漂第 1、2 条）。Hub 额外承担事件日志的 **per-project 写锁**，消除聊天/文档/后台提取并发写导致的 seq 重复与投影回退。
- 新增**对话 Agent（Dialogue Gateway）**：唯一用户出口。负责聊天、把后台结构化事件翻译成温和表达。它**不自己做**提取/矛盾检测，只经 Hub 请求专职能力。
- 新增**意图闸门三态**：每条聊天消息被分类为 `ignore`（闲聊/提问，不提取）/ `candidate`（脑暴/假设，只入事件日志、不进矛盾检测）/ `committed`（正式设定，**只能由编辑器或显式"采纳"产生**）。意图分类并入对话回复同一次 LLM 调用，输出只取 ignore|candidate（绝不 committed），解析失败保守降级 ignore。聊天本身**永不自动 commit**。
- 新增**共享提取管道**：抽出 `run_extraction_pipeline(project_id, source_type, source_id, content, acceptance_status)`，文档与聊天共用同一套 extract→alias→矛盾→rebuild 逻辑。提取出的 facts 带 `source_type=chat|document` 与**独立字段** `acceptance_status`（candidate|committed，与既有 `lifecycle_status` 正交并存，不复用）；candidate 模式跳过全局 alias 写入、走想法事件白名单；**矛盾检测只读 active committed facts**（旧 facts 缺字段默认 committed+active 兜底），candidate 不参与矛盾比对。
- 新增**采纳进正文（聊天内容进正文的唯一入口）**：用户在 ChatUI 点"放入正文"按钮 → 后端 endpoint 锁内追加到正文页末尾（带幂等键防双击）→ 重新走 committed 提取产出**新** committed facts（不原地改旧 candidate）+ 写 `manuscript.adopted` 链回来源消息。后端 endpoint 与前端按钮成对交付（用户会亲测）。committed facts 合法来源有二：编辑器保存、聊天经采纳。
- 新增**正文页（只读）**：一整篇展示已采纳内容，V1 不可编辑（可编辑留作完整版未来方向）。ChatUI 有按钮直达。
- 新增**风格备忘**：全局创作方向（如"动画+collage 拼贴"）走事件日志、投影到 story_state 平级新区、**永不进矛盾检测**、生成时自动进 prompt、识别到时"问一下再存"。定位"给 AI 看的参照系"，住项目设置二级页。
- 新增前端 **三抽屉结构**：左侧竖排导航——① 主界面 ChatUI（主角）+ 证据栏常驻；② 项目设置二级页（项目/版本/信息/风格备忘）；③ 五兄弟二级页（世界观/角色/剧情/主题/结构入口→三级详情）；另有独立**正文二级页**。视觉采用**毛玻璃（glassmorphism）高级克制风**——简约、实用、不喧宾夺主。
- 复用现有 `llm_provider.py`、事件日志、提取/矛盾/alias 服务，不重复造。

## Capabilities

### New Capabilities

- `agent-hub`: 薄 Hub 运行时——结构化事件路由、权限边界（仅对话 Agent 可生成用户可见话术）、调度后台能力、事件日志 per-project 写锁（覆盖**所有**写路径，含文档/events/alias/矛盾/evidence_card）。只处理结构化字段，不写用户话术、不裁决创作。除 event_log 与 Hub gateway 外禁止直调 `append_event()`（架构测试钉死）。
- `dialogue-agent`: 对话 Agent——唯一用户出口；聊天、意图闸门分类（并入对话调用、只输出 ignore|candidate、失败降级 ignore）、温和表达；经 Hub 请求提取/矛盾能力，自身不承担专业判断；prompt 上下文受控（不塞完整 story_state/正文）；user 消息 LLM 前写、assistant 成功后写。
- `extraction-pipeline`: 共享提取管道——文档与聊天共用；facts 带 `source_type` + **独立字段** `acceptance_status`（与 `lifecycle_status` 正交）；candidate 跳过全局 alias、走想法事件白名单；矛盾检测只读 active committed facts（旧 facts 默认兜底）；candidate 只入日志不进矛盾。
- `manuscript`: 正文页——只读、一整篇展示已采纳内容；"采纳进正文"是聊天内容进正文（产生 committed）的唯一入口，锁内追加末尾 + 幂等 + 重新提取（不原地改 candidate）+ `manuscript.adopted` 链回来源。
- `creative-memory`: 风格备忘——全局创作方向走事件日志、投影到 story_state 平级新区、永不进矛盾检测、生成时进 prompt、识别到时问一下再存。
- `chat-ui`: 前端三抽屉界面——主界面 ChatUI + 证据栏 + 直达正文按钮、项目设置页、五兄弟页、独立正文页；毛玻璃克制视觉；气泡非模态、证据仍只走证据栏。

### Modified Capabilities

<!-- event-log / minimal-story-state 的行为契约不变，仅被复用与扩展（新增 chat.message / creative_intent 事件类型、per-project 写锁）。 -->

## Impact

- **后端新增**：`app/services/hub.py`（薄 Hub + 写锁 + append gateway）、`app/services/dialogue.py`（对话 Agent + 意图闸门）、`app/services/extraction_pipeline.py`（共享提取管道，从 `api/documents.py` 抽出）、`app/api/chat.py`（对话 endpoint）、采纳进正文 endpoint、风格备忘 endpoint，并在 `app/main.py` 注册路由。
- **后端改动**：`api/documents.py` 改为调用共享提取管道；`EventType` 枚举新增 `chat.message` / `creative_intent.added` / `creative_intent.archived` / `manuscript.adopted`，否则重放崩溃；Fact 新增独立字段 `acceptance_status`（+ `source_type`，历史缺字段默认 committed+active）；`ContradictionService` 改为只读 active committed facts；`StoryState` 新增风格备忘平级区；所有事件日志写路径收编进 Hub 写锁。
- **前端新增**：三抽屉导航 + 主界面 ChatUI + 正文页 + 风格备忘 UI + 证据栏（毛玻璃风）；`api.ts` 增加 `sendChatMessage`、采纳进正文、风格备忘读写。前端不提交 git（遵守约定）。
- **依赖**：无新外部依赖；LLM key 仍只走 git-ignored `.env`、走代理、不入库/不回显/不进日志。
- **成本**：每条聊天消息触发 1 次对话 LLM 调用，candidate/committed 才额外触发提取——沿用现有 TokenUsageTracker 观测；prompt 上下文受控防止 token 无限增长。
