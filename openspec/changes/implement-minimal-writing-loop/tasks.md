## 1. LLM 接口层（llm-provider）

- [x] 1.1 新增 `backend/app/config` LLM 配置项：API key（仅环境变量）、模型名、代理 URL、token 预算占位
- [x] 1.2 实现 `backend/app/services/llm_provider.py` 统一接口（抽象基类 + DeepSeek 默认实现），调用走代理 `http://127.0.0.1:7890`
- [x] 1.3 实现 token 用量记录（每次调用记输入/输出 token 数）
- [x] 1.4 实现 key 不入库/不回显/不写日志的护栏 + 未配置时明确报错
- [x] 1.5 写测试：provider 抽象可切换、key 不泄露到日志/响应（mock LLM，不真调）

## 2. 文档版本链路（document-revision）

- [x] 2.1 新增 `backend/app/models/documents.py`：document revision 模型（正文/source hash/source span）
- [x] 2.2 定义 `document.revised` 事件类型，接入现有 event log
- [x] 2.3 扩展 projector：从事件重建当前正文投影到 story_state
- [x] 2.4 实现 `backend/app/api/documents.py`：保存正文、列出历史版本、回到旧版本（回退也是追加新事件）
- [x] 2.5 写测试：保存生成版本、不覆盖旧版本、回退靠重放、source span 可定位

## 3. Fountain 解析 + LLM 提取（llm-extraction）

- [x] 3.1 选用成熟的 pip Fountain 解析库（现成库优先，无合适再补核心子集：场景标题/角色/对白/动作）
- [x] 3.2 实现结构解析：确定角色集合、对白归属（不猜人名）
- [x] 3.3 实现两段式提取服务 `backend/app/services/extraction.py`：结构解析喂 LLM → 输出结构化 Fact（事件/状态变化/source span）
- [x] 3.4 接入攒批触发：保存后排后台任务，逐字键入不触发
- [x] 3.5 失败隔离：LLM 失败/超时不阻断写作，下次触发补提取
- [x] 3.6 写测试：动作行普通名词不被当角色、确定结构不调 LLM（mock）、提取失败不阻断

## 4. 矛盾监控（contradiction-detection）

- [x] 4.1 实现 `backend/app/services/contradiction.py`：基于 Fact 检测硬矛盾（角色状态冲突、时间线冲突）
- [x] 4.2 产出 `ContinuityEvent`：只存 evidence + source span，不存结论/建议（落实灵魂清单 #3）
- [x] 4.3 接入攒批触发 + 失败不阻断
- [x] 4.4 写测试：状态冲突被检出、无冲突不产噪声、事件不含修改建议

## 5. 证据卡与偏好（evidence-card-handling）

- [x] 5.1 实现 `backend/app/api/preferences.py`：忽略/接受证据卡、写 project_preferences 降权规则
- [x] 5.2 实现降权逻辑：忽略某类 → 降权呈现而非关闭检测（落实灵魂清单 #4）
- [x] 5.3 写测试：忽略写降权规则、降权可恢复、检测仍在后台运行

## 6. 导入导出（screenplay-import-export）

- [x] 6.1 实现粘贴导入：文本载入正文 + 记 `document.revised` 事件 + 可被提取
- [x] 6.2 实现导出 Fountain（保留结构）与纯文本（去标记）
- [x] 6.3 写测试：导入后走相同提取流程、两种导出格式正确

## 7. 前端编辑器（screenplay-editor）

- [x] 7.1 搭建 React + Vite 前端骨架，对接后端 API
- [x] 7.2 实现 Fountain 文本输入区（不拦截/不改写输入）
- [x] 7.3 实现 Fountain 语法高亮（场景标题/角色名/对白/动作），非标准行降级为动作行
- [x] 7.4 实现自动存盘 + 关闭重开内容保留
- [x] 7.5 实现侧边证据卡：非侵入呈现、温和退路措辞、忽略/接受按钮
- [x] 7.6 实现版本历史查看 + 回退、导入粘贴框、导出按钮

## 8. 端到端验证 + 信任评估 + 防漂自检

- [x] 8.1 用真实 LLM 跑通完整闭环：写几千字短剧本 → 存 → 关重开内容在 → 触发提取 → 证据卡 → 忽略降权 → 导出
- [ ] 8.2 建 20-30 个固定剧本片段评估集，测提取/矛盾误报率，记录基线 —— 未做：按 design.md Open Questions 放本 change 收尾的信任验证节点，不阻塞主链路；标杆案例已用真实 LLM 验到 8/9（见 D9 快照）
- [x] 8.3 灵魂清单自检：逐条核对 5 项（不审判/留余地/递证据/降权/生长不覆盖）在实现中确实落实
- [x] 8.4 长大路标核对：确认延后能力都在 design.md D8 列明、未被悄悄砍掉
- [ ] 8.5 全量测试通过（含原 54 个不回归）+ lsp 诊断干净 + 清理临时文件 —— 测试 112 passed + ruff 干净已确认；lsp(basedpyright) 环境未安装无法跑；临时 diag 脚本待收尾清理
