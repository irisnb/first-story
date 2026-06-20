# Frist story — 前后端接口契约（API Contract）

> 真相源 = 后端 FastAPI 路由。本文档由 `app.openapi()` 导出的 OpenAPI 3.1.0 schema 整理而成（标题 `First Story Backend` v0.1.0）。
> **用途**：丢弃整个旧前端、全部重做时，唯一需要保留的前后端边界即本文档所列。文档核对无误后才执行删除 `frontend/`。

## 0. 全局约定

| 项 | 值 |
|---|---|
| Base URL | `http://localhost:8000` |
| API 前缀 | `/api/v1`（`settings.api_prefix`） |
| 顶层端点 | `GET /health`、`GET /`（无前缀） |
| 内容类型 | 请求/响应默认 `application/json`；导出端点为 `text/plain` |
| CORS | `allow_origin_regex = ^http://(localhost|127\.0\.0\.1)(:\d+)?$`；`allow_credentials=True`；methods=GET/POST/PUT/DELETE/OPTIONS；headers=`*` |
| 校验错误 | 任何带请求体/查询/路径参数的端点，参数不合法时返回 `422`，体为 `HTTPValidationError` |
| LLM key | 绝不出现在任何请求/响应字段；只走 git-ignored `.env` + 代理 |

**通用错误体**

```jsonc
// 422 HTTPValidationError
{ "detail": [ { "loc": ["body","name"], "msg": "...", "type": "..." } ] }
```

> 说明：路由层对「项目不存在」会抛 `404`（见各端点备注）；OpenAPI 仅声明了 `200/201/422`，`404` 来自 service 层抛出的 HTTPException，前端需自行处理。

---

## 1. 顶层端点（无 `/api/v1` 前缀）

### `GET /health`
- **响应 200** `HealthResponse`
  ```jsonc
  { "status": "ok", "version": "<string>" }   // status 默认 "ok"，version 必填
  ```

### `GET /`
- **响应 200** 自由对象（root，指向 docs）。后端实际返回：
  ```jsonc
  { "message": "First Story Backend API", "docs": "/docs", "demo": "/demo", "health": "/health" }
  ```

---

## 2. 项目 Projects（tag: projects）

### `GET /api/v1/projects` — 列出全部项目
- **响应 200** `ProjectListResponse`
  ```jsonc
  { "projects": [ProjectResponse], "total": <int> }
  ```

### `POST /api/v1/projects` — 新建项目
- **请求体** `CreateProjectRequest`
  ```jsonc
  { "name": "<string, 1..100>" }   // 必填
  ```
- **响应 201** `ProjectResponse`
- **错误** 422

### `GET /api/v1/projects/{project_id}` — 取单个项目
- **路径** `project_id: string`
- **响应 200** `ProjectResponse`
- **错误** 404（项目不存在）/ 422

**`ProjectResponse`**
```jsonc
{
  "id": "<string>",
  "name": "<string>",
  "created_at": "<date-time>",
  "updated_at": "<date-time>",
  "version": "<string>"          // 例 "1.0.0"
}
```

---

## 3. 事件 Events（tag: events）

> 真相源 = append-only event log。

### `GET /api/v1/projects/{project_id}/events` — 列事件
- **路径** `project_id: string`
- **查询** `from_seq: int | null`（可选）、`to_seq: int | null`（可选）
- **响应 200** `EventListResponse`
  ```jsonc
  { "events": [EventResponse], "total": <int>, "project_id": "<string>" }
  ```
- **错误** 404（项目不存在）/ 422

### `POST /api/v1/projects/{project_id}/events` — 追加事件
- **路径** `project_id: string`
- **请求体** `AppendEventRequest`
  ```jsonc
  {
    "event_id": "<string>",          // 必填，全局唯一
    "idempotency_key": "<string>",   // 必填，去重键
    "type": "<string>",              // 必填，须为合法 EventType（见附录 A）
    "payload": { },                  // 必填，任意对象
    "schema_version": "1.0",         // 默认 "1.0"
    "base_state_version": 0,         // 默认 0，>=0
    "actor": "user",                 // 默认 "user"（见附录 A）
    "batch_id": "<string> | null"    // 可选
  }
  ```
- **响应 201** `EventResponse`
- **错误** 404（项目不存在）/ 422

**`EventResponse`**（全部字段必填）
```jsonc
{
  "event_id": "<string>",
  "idempotency_key": "<string>",
  "seq": <int>,                     // 服务端分配的顺序号
  "timestamp": "<date-time>",
  "type": "<string>",
  "schema_version": "<string>",
  "payload": { },
  "base_state_version": <int>,
  "actor": "<string>",
  "batch_id": "<string> | null"
}
```

---

## 4. 文档/手稿 Documents（tag: documents）

### `POST /api/v1/projects/{project_id}/documents` — 保存修订
> append-only，永不覆盖。保存返回后才在后台排队抽取，不阻塞保存、不逐键触发。
- **路径** `project_id: string`
- **请求体** `SaveRevisionRequest`
  ```jsonc
  { "content": "<string>", "document_id": "main" }   // content 必填；document_id 默认 "main"
  ```
- **响应 201** `DocumentRevision`
- **错误** 404 / 422

### `GET /api/v1/projects/{project_id}/documents` — 列修订（最旧在前）
- **路径** `project_id: string`
- **查询** `document_id: string = "main"`
- **响应 200** `RevisionListResponse`
  ```jsonc
  { "revisions": [DocumentRevision], "total": <int>, "project_id": "<string>" }
  ```
- **错误** 404 / 422

### `GET /api/v1/projects/{project_id}/documents/export` — 导出
> `format='fountain'` 保留 Fountain 结构；`format='text'` 去除标记。
- **路径** `project_id: string`
- **查询** `document_id: string = "main"`、`format: string = "fountain"`
- **响应 200** `text/plain`（纯字符串正文）
- **错误** 404 / 422

### `POST /api/v1/projects/{project_id}/documents/{revision_id}/restore` — 恢复旧修订
> 通过把旧修订作为新修订追加来恢复（不擦写历史）。
- **路径** `project_id: string`、`revision_id: string`
- **查询** `document_id: string = "main"`
- **响应 200** `DocumentRevision`（`restored_from_revision_id` 会被置为来源修订）
- **错误** 404 / 422

**`DocumentRevision`**
```jsonc
{
  "revision_id": "<string>",                 // 必填
  "content": "<string>",                     // 必填，该修订完整正文
  "content_hash": "<string>",                // 必填，content 的 sha256 hex
  "source_span": { "start": <int>, "end": <int> },  // 必填，SourceSpan
  "revised_at": "<ISO 8601 string>",         // 必填
  "source_event_id": "<string>",             // 必填，引入此修订的 SystemEvent.event_id
  "document_id": "main",                     // 默认 "main"
  "restored_from_revision_id": "<string> | null"  // 恢复时才有值
}
```

**`SourceSpan`** `{ "start": <int>=0, "end": <int>=0 }`（end 为开区间上界）

---

## 5. 证据卡操作 Continuity Events（tag: preferences）

> 系统只递证据、不下结论；判断权在用户。`ignore` 的 `scope='category'` 只写降权规则，**不会关闭检测**。

### `POST /api/v1/projects/{project_id}/continuity-events/{continuity_event_id}/ignore`
- **路径** `project_id: string`、`continuity_event_id: string`
- **请求体** `IgnoreRequest`
  ```jsonc
  {
    "user_explanation": "<string> | null",   // 可选，用户忽略的理由
    "scope": "single_finding"                // 默认；或 "category"（写降权规则）
  }
  ```
- **响应 200** `CardActionResponse`
- **错误** 404 / 422

### `POST /api/v1/projects/{project_id}/continuity-events/{continuity_event_id}/accept`
> 接受 = 标记 confirmed/resolved，保留记录。
- **路径** `project_id: string`、`continuity_event_id: string`
- **请求体** `AcceptRequest`
  ```jsonc
  { "resolution_fact_id": "<string> | null" }   // 可选，解决冲突的 fact id
  ```
- **响应 200** `CardActionResponse`
- **错误** 404 / 422

**`CardActionResponse`**
```jsonc
{
  "continuity_event_id": "<string>",   // 必填
  "action": "<string>",                // 必填，如 "ignore" / "accept"
  "deweighting_written": false,        // 默认 false
  "category": "<string> | null"
}
```

---

## 6. 故事状态 State（tag: state）

### `GET /api/v1/projects/{project_id}/state` — 取当前投影
> 先 load_state，无则 rebuild。
- **路径** `project_id: string`
- **响应 200** `StateResponse`
- **错误** 404 / 422

### `POST /api/v1/projects/{project_id}/state/rebuild` — 强制重建
> 从 event log 重放重建投影。
- **路径** `project_id: string`
- **响应 200** `RebuildResponse`
  ```jsonc
  { "message": "<string>", "log_head_seq": <int>, "events_processed": <int> }
  ```
- **错误** 404 / 422

**`StateResponse`**（全部字段必填，可空字段标注）
```jsonc
{
  "projection_schema_version": "<string>",
  "log_head_seq": <int>,
  "head_event_id": "<string> | null",
  "source_document_revision": "<string> | null",
  "source_document_checksum": "<string> | null",
  "story": { },                         // 五大模块当前投影（自由对象，结构见附录 B）
  "updated_at": "<date-time> | null"
}
```

---

## 7. 对话 Chat / 采纳 / 风格备忘（tag: chat）

### `POST /api/v1/projects/{project_id}/chat` — 一轮对话
> 经唯一用户出口（对话 Agent）。落库该轮 → 分类 intent（仅 ignore | candidate）→ 返回回复。candidate 轮会在后台排队抽取，回复先于抽取返回。**响应不含证据、不含 LLM key。**
- **路径** `project_id: string`
- **请求体** `ChatRequest`
  ```jsonc
  { "message": "<string>" }   // 必填
  ```
- **响应 200** `ChatResponse`
  ```jsonc
  {
    "reply": "<string>",            // 必填
    "message_id": "<string>",       // 必填
    "intent": "<string>",           // 必填，枚举式字符串：ignore | candidate
    "extraction_status": "<string>" // 必填，枚举式字符串：queued | none | skipped_no_llm | llm_error
  }
  ```
  > **`intent`**（`str`，由对话解析器约束）：
  > - `ignore` — 该轮不入抽取（默认值；模型输出非法值时也回落到此）
  > - `candidate` — 该轮被判为候选，后台排队抽取
  > - 注：`committed` 是被显式禁止的值,绝不会出现在响应里。
  >
  > **`extraction_status`**（`str`，由对话流产生）：
  > - `queued` — intent=candidate 且 LLM 调用成功,已排队抽取
  > - `none` — LLM 调用成功但 intent=ignore,无抽取
  > - `skipped_no_llm` — 未配置 LLM（无 key），跳过抽取
  > - `llm_error` — LLM 调用异常
  >
  > 二者在响应模型中均为自由 `str`，非 Enum/Literal；上列取值为代码当前穷举集。
- **错误** 404 / 422

### `POST /api/v1/projects/{project_id}/manuscript/adopt` — 采纳进正文
> chat 内容追加到正文末尾并以 committed 模式重抽取。read-current → append → write 在 Hub 每项目写锁内执行，且按 `adopt_request_id` 幂等：相同 key 的二次点击绝不重复追加。旧 candidate facts 永不被改写，新 committed facts 由重抽取产生（append-only 真相源）。这是 chat 唯一进入正文的入口。
- **路径** `project_id: string`
- **请求体** `AdoptRequest`
  ```jsonc
  {
    "content": "<string>",                       // 必填，要追加的选中文本
    "adopt_request_id": "<string>",              // 必填，客户端生成的幂等键
    "adopted_from_message_id": "<string> | null",// 可选，来源 chat 消息 id，用于追溯
    "document_id": "main"                        // 默认 "main"
  }
  ```
- **响应 200** `AdoptResponse`
  ```jsonc
  { "revision_id": "<string>", "duplicate": false }   // duplicate 默认 false；识别为重复提交时 true
  ```
- **错误** 404 / 422

### `GET /api/v1/projects/{project_id}/style-memos` — 列风格备忘（含 active/archived）
- **路径** `project_id: string`
- **响应 200** `StyleMemoListResponse`
  ```jsonc
  { "memos": [StyleMemoResponse] }
  ```

### `POST /api/v1/projects/{project_id}/style-memos` — 加风格备忘
> kind 缺省回落到 `"未分类"`。
- **路径** `project_id: string`
- **请求体** `StyleMemoRequest`
  ```jsonc
  { "text": "<string>", "kind": "<string> | null" }   // text 必填
  ```
- **响应 201** `StyleMemoResponse`
- **错误** 404 / 422

### `POST /api/v1/projects/{project_id}/style-memos/{memo_id}/archive` — 归档风格备忘
> status → archived，永不删除。
- **路径** `project_id: string`、`memo_id: string`
- **响应 200** `StyleMemoResponse`
- **错误** 404 / 422

**`StyleMemoResponse`**
```jsonc
{
  "id": "<string>",
  "text": "<string>",
  "kind": "<string>",      // 例 "未分类"
  "status": "<string>"     // active | archived
}
```

---

## 附录 A — 事件类型与 Actor 取值

> 用于 `POST .../events` 的 `type` 与 `actor` 字段。来自后端 `EventType` / `Actor` 枚举。

**EventType**
`character.created`、`character.status_updated`、`character.alias_bound`、
`plot_event.created`、
`fact.created`、`fact.retracted`、
`document.revised`、
`continuity_event.created`、`continuity_event.ignored`、`continuity_event.resolved`、
`project_preference.deweighting_set`、`project_preference.assumption_confirmed`、
`batch.committed`、
`chat.message`（仅日志，永不投影）、
`creative_intent.added`、`creative_intent.archived`、
`manuscript.adopt*`（采纳相关）

**Actor**
`user`、`hub`、`extraction_agent`、`continuity_agent`、`dialogue_gateway`

---

## 附录 B — `story` 投影结构（`StateResponse.story` 内）

> `story` 在 OpenAPI 中声明为自由对象（`additionalProperties: true`）。其内部为五大模块的当前投影，由 `StoryState` 模型定义，前端按需读取：

- `characters` — `Character[]`：`id, name, status(alive|dead|unknown，默认 unknown), status_since_event_id, status_note, gender, relations[], known_fact_ids[], attributes{}`
- `facts` — `Fact[]`：`id, content, story_time(StoryTime|null), about_character_ids[], source_*` 系列、`extraction_confidence(0..1), lifecycle_status`
- `plot_events` — `PlotEvent[]`：`id, summary, story_time, participant_character_ids[], asserted_fact_ids[], source_event_id`
- `continuity` — 连续性证据卡集合（含 `Delivery{delivery_mode, interrupt_risk, armor_level, initiator, flow_blocked}`）
- `document` — 当前手稿投影
- `preferences` — 项目偏好（降权规则、已确认假设等）
- `StoryClock` — `{ current_time, reference_point="story_start", confidence(0..1, 默认 0.5) }`

> `StoryTime` 三态：`Absolute{value, confidence}` | `Relative{anchor, direction(before|after|same), distance, confidence}` | `Unknown`。

---

## 附录 C — 端点速查表

| Method | Path | 请求体 | 成功码 |
|---|---|---|---|
| GET | `/health` | — | 200 |
| GET | `/` | — | 200 |
| GET | `/api/v1/projects` | — | 200 |
| POST | `/api/v1/projects` | CreateProjectRequest | 201 |
| GET | `/api/v1/projects/{project_id}` | — | 200 |
| GET | `/api/v1/projects/{project_id}/events` | — (query from_seq/to_seq) | 200 |
| POST | `/api/v1/projects/{project_id}/events` | AppendEventRequest | 201 |
| POST | `/api/v1/projects/{project_id}/documents` | SaveRevisionRequest | 201 |
| GET | `/api/v1/projects/{project_id}/documents` | — (query document_id) | 200 |
| GET | `/api/v1/projects/{project_id}/documents/export` | — (query document_id, format) | 200 (text/plain) |
| POST | `/api/v1/projects/{project_id}/documents/{revision_id}/restore` | — (query document_id) | 200 |
| POST | `/api/v1/projects/{project_id}/continuity-events/{continuity_event_id}/ignore` | IgnoreRequest | 200 |
| POST | `/api/v1/projects/{project_id}/continuity-events/{continuity_event_id}/accept` | AcceptRequest | 200 |
| GET | `/api/v1/projects/{project_id}/state` | — | 200 |
| POST | `/api/v1/projects/{project_id}/state/rebuild` | — | 200 |
| POST | `/api/v1/projects/{project_id}/chat` | ChatRequest | 200 |
| POST | `/api/v1/projects/{project_id}/manuscript/adopt` | AdoptRequest | 200 |
| GET | `/api/v1/projects/{project_id}/style-memos` | — | 200 |
| POST | `/api/v1/projects/{project_id}/style-memos` | StyleMemoRequest | 201 |
| POST | `/api/v1/projects/{project_id}/style-memos/{memo_id}/archive` | — | 200 |

> 全部 19 个 API 端点 + 2 个顶层端点。所有带参数端点的校验失败均返回 422；项目/资源不存在返回 404。

---

## 附录 D — 前端结构契约（重做验收标准）

> 来源：旧前端 `frontend/structure-contract.test.mjs`（随旧前端删除，已提炼至此 + 保留测试文件副本于仓库根的 `frontend-structure-contract.test.mjs`）。
> **这不是旧实现的描述，而是新前端必须满足的 UI 硬性不变量。** 重做完成后跑保留的测试文件验收（需把测试内 `./src/App.tsx`、`./src/App.css` 的相对路径指向新前端实际位置）。

### D.1 App 外壳：左侧导航 + 必备二级页面
新前端 `App.tsx`（或等价入口）必须可达以下入口：
- 左侧导航容器，类名 `side-nav`
- 页面/入口文案（中文，原样）：`主界面`、`项目设置`、`五兄弟`、`正文`、`直达正文`

### D.2 五大模块详情入口
五模块页面必须可达全部五个模块文案：`世界观`、`角色`、`剧情`、`主题`、`结构`

### D.3 玻璃拟态外壳样式
样式表（旧为 `App.css`）必须定义以下选择器并使用毛玻璃模糊：
- 选择器：`.side-nav`、`.view-shell`、`.story-module-grid`、`.evidence-panel`
- `backdrop-filter: blur(...)`（玻璃面板）

> 注：`evidence-panel`（证据面）对应「系统只递证据、不下结论」—— 证据卡呈中性面板，非告警红。重做时此语义不变。
