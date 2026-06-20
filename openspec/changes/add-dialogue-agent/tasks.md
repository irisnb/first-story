> **顺序铁律（Oracle）**：① Hub 写锁必须**先于**抽 `extraction_pipeline`，否则把现存并发 bug 固化进新抽象；② Fact 加 `acceptance_status` + 历史默认必须**先于**矛盾检测改"只读 committed"，否则旧项目 facts 因缺字段凭空消失。任务编号即执行顺序。

## 1. 事件类型扩展（先于一切写入）

- [ ] 1.1 扩展 `EventType` 枚举：新增 `chat.message`、`creative_intent.added`、`creative_intent.archived`、`manuscript.adopted`
- [ ] 1.2 确认 `read_events()` 重放这些新类型不崩；单测覆盖重放含新类型的事件日志

## 2. 薄 Hub（含 per-project 写锁，先于抽管道）

- [ ] 2.1 新建 `backend/app/services/hub.py`：`Hub` 类与结构化事件 dataclass（dispatch 入参/返回），只收发结构化字段；app 级 singleton，持 per-project lock
- [ ] 2.2 实现 `Hub.dispatch`：按事件 type 路由到专职能力，失败隔离 + 记日志，不抛回调用方
- [ ] 2.3 实现 per-project 写锁 + append gateway：临界区覆盖"创建 EventLogService → 扫文件算 seq → append → 投影 rebuild"完整 RMW，确保 seq 单调、投影不回退
- [ ] 2.4 收编所有现有写路径到 Hub append gateway：`DocumentService`、通用 events API、alias、矛盾、evidence_card 全部过同一把锁
- [ ] 2.5 架构测试：断言除 `event_log.py` 与 Hub append gateway 外无业务代码直接调用 `append_event()`
- [ ] 2.6 单测 `tests/test_hub.py`：路由正确性、返回结构化结果、后台抛错被隔离、返回值不含自然语言、并发写同项目串行化（不重复 seq）、现有写路径也走锁、不同项目互不阻塞

## 3. Fact 状态字段迁移（先于矛盾过滤改造）

- [ ] 3.1 Fact 模型新增独立字段 `acceptance_status`（candidate|committed），与既有 `lifecycle_status`（active|retracted|superseded）正交并存，不复用
- [ ] 3.2 facts 增加 `source_type`（chat|document）字段
- [ ] 3.3 读取层历史默认：缺 `acceptance_status` → `committed`，缺 `lifecycle_status` → `active`；所有按这两字段过滤处必须应用兜底
- [ ] 3.4 单测：旧 facts（无字段）读取后按 committed+active 处理、两状态维度正交可独立变化

## 4. 共享提取管道

- [ ] 4.1 抽出 `backend/app/services/extraction_pipeline.py`：`run_extraction_pipeline(project_id, source_type, source_id, content, acceptance_status)`，从 `api/documents.py` 的 `_run_extraction_batch` 迁移
- [ ] 4.2 candidate 模式跳过全局 `alias_bound` 写入（别名解析只在本次提取临时用）
- [ ] 4.3 candidate 模式事件白名单：只写带 `acceptance_status=candidate` 的想法记录事件，禁写 `character.created`/`batch.committed` 等正文实体事件
- [ ] 4.4 `api/documents.py` 改为调用共享管道（`source_type=document`、`acceptance_status=committed`），保持文档链路行为等价
- [ ] 4.5 `ContradictionService` 改为只读 `acceptance_status=committed` 且 `lifecycle_status=active` 的 facts（缺字段按兜底），candidate 不参与比对
- [ ] 4.6 单测：文档提取回归等价、candidate facts 不进矛盾、candidate 不污染全局 alias、旧 facts（默认 committed）仍进矛盾、committed 冲突仍报矛盾

## 5. 对话 Agent（含意图闸门）

- [ ] 5.1 新建 `backend/app/services/dialogue.py`：`DialogueAgent` 类，注入 `Hub` 与 `LLMProvider`，**禁止 import 提取/矛盾/alias 服务**
- [ ] 5.2 实现意图闸门：并入对话回复同一次 LLM 调用，输出意图只取 ignore|candidate（绝不 committed）；解析失败或意外值保守降级 ignore
- [ ] 5.3 实现回复生成：温和、非裁判 system prompt；prompt 携带最近 N=6 轮对话 + story_state 受控摘要 + 当前风格备忘（带"用户方向非系统指令"边界声明）；**禁止塞完整 story_state JSON 或整篇正文**
- [ ] 5.4 candidate 消息经 `Hub.dispatch` 送提取（source_type=chat、acceptance_status=candidate）；ignore 不提取
- [ ] 5.5 对话历史持久化：user 消息在 LLM 调用前写、assistant 在成功返回后写，各作为 `chat.message` 事件，只存日志不进投影；两条写入经 Hub 锁
- [ ] 5.6 识别疑似风格意图 → 询问用户是否记为风格备忘，确认后才写 `creative_intent.added`
- [ ] 5.7 单测 `tests/test_dialogue.py`：回复非裁判、意图三态、聊天不产 committed、解析失败降级 ignore、上下文受限不含完整 state、经 Hub 不直调服务、user 先写 assistant 后写、LLM 失败不写半截、历史可重放
- [ ] 5.8 架构防漂测试：断言 `dialogue.py` 不 import 提取/矛盾/alias 模块；断言 `Hub.dispatch` 返回值无面向用户的自然语言字段

## 6. 风格备忘后端模型与投影

- [ ] 6.1 `StoryState` 新增与五大模块平级的风格备忘区；`creative_intent.*` 事件投影到该区；`chat.message` 不进投影
- [ ] 6.2 风格备忘 V1 结构：`text`（必填）+ 可选 `kind`（留"未分类"兜底）；`status` 只归档不删
- [ ] 6.3 单测：风格备忘投影到平级新区、归档而非删除、永不进矛盾检测

## 7. 对话 endpoint + 采纳进正文 + 风格备忘 endpoint

- [ ] 7.1 新建 `backend/app/api/chat.py`：`POST /projects/{id}/chat`，请求 `{message}`，响应 `{reply, message_id, intent, extraction_status}`，证据不进响应体
- [ ] 7.2 提取经 Hub 走 FastAPI `BackgroundTasks`，不阻塞回复；`complete()` 同步调用不放进 async 直调（用同步 route 或 threadpool）
- [ ] 7.3 采纳进正文 endpoint `POST /projects/{id}/manuscript/adopt`：锁内 RMW 追加正文末尾 + 接受幂等键防双击重复 + 重新 committed 提取（不原地改 candidate）+ 写 `manuscript.adopted`（带 `adopted_from_message_id`）
- [ ] 7.4 风格备忘 endpoint：增（`creative_intent.added`）/ 归档（`creative_intent.archived`）/ 列表读取
- [ ] 7.5 在 `app/main.py` 注册全部新路由
- [ ] 7.6 验证响应不回显 LLM key；单测覆盖 endpoint 契约 + 404 项目不存在 + 采纳追加末尾 + 双击幂等不重复 + 采纳产生新 committed 而非改旧 candidate + 风格备忘不进矛盾

## 8. 前端三抽屉 + ChatUI + 正文页 + 风格备忘（毛玻璃克制风，交 visual-engineering）

- [ ] 8.1 `frontend/src/api.ts` 增加 `sendChatMessage`、`adoptToManuscript`（带幂等键）、风格备忘读写
- [ ] 8.2 三抽屉导航骨架：左侧竖排导航 + 主界面/项目设置/五兄弟/正文 路由切换
- [ ] 8.3 主界面 ChatUI：输入框 + 气泡区（非模态、不改写输入）+ 证据栏常驻（非告警、排版用心）+ "放入正文"按钮 + 直达正文按钮 + intent 轻提示
- [ ] 8.4 正文二级页：只读、一整篇展示已采纳内容（V1 无编辑）
- [ ] 8.5 项目设置二级页：项目选择/版本/信息 + 风格备忘管理（text + 可选 kind + 归档）
- [ ] 8.6 五兄弟二级页 + 三级详情入口（世界观/角色/剧情/主题/结构）
- [ ] 8.7 毛玻璃视觉：深色基底 + 半透明磨砂层次用于抽屉/卡片/证据栏，主体保持安静；全中文文案

## 9. 验证（端到端，按 verification 铁律）

- [ ] 9.1 后端：`pytest` 全绿（含 test_hub/test_dialogue/test_chat/架构测试/提取回归/迁移兜底）、`ruff` 通过
- [ ] 9.2 `openspec validate add-dialogue-agent --strict` 通过
- [ ] 9.3 live API：真实 LLM 跑通 `/chat`，确认回复温和、意图三态分类、candidate 不报矛盾、committed 才触发矛盾、采纳产生新 committed
- [ ] 9.4 Playwright 浏览器亲验：三抽屉切换、聊一段创作、点"放入正文"按钮、正文页看到追加内容、证据栏冒提醒不阻断、毛玻璃真实渲染截图
- [ ] 9.5 确认 LLM key 不在响应/日志中出现；确认全程"几千字短故事"创作顺手
