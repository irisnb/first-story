// 前后端边界类型 —— 唯一真相源 docs/api-contract.md。
// 仅声明 V1 闭环用到的部分，其余按需扩展。

export interface ProjectResponse {
  id: string
  name: string
  created_at: string
  updated_at: string
  version: string
}

export interface ProjectListResponse {
  projects: ProjectResponse[]
  total: number
}

export interface CreateProjectRequest {
  name: string
}

// ---- Chat ----
export interface ChatRequest {
  message: string
}

export type ChatIntent = 'ignore' | 'candidate'
export type ExtractionStatus = 'queued' | 'none' | 'skipped_no_llm' | 'llm_error'

export interface ChatResponse {
  reply: string
  message_id: string
  // 契约声明为自由 str；下列为代码当前穷举集
  intent: ChatIntent | string
  extraction_status: ExtractionStatus | string
}

// ---- Documents ----
export interface SourceSpan {
  start: number
  end: number
}

export interface DocumentRevision {
  revision_id: string
  content: string
  content_hash: string
  source_span: SourceSpan
  revised_at: string
  source_event_id: string
  document_id: string
  restored_from_revision_id: string | null
}

export interface RevisionListResponse {
  revisions: DocumentRevision[]
  total: number
  project_id: string
}

export interface SaveRevisionRequest {
  content: string
  document_id?: string
}

// ---- State (五大模块投影) ----
export interface CharacterRelation {
  [key: string]: unknown
}

export interface Character {
  id: string
  name: string
  status: 'alive' | 'dead' | 'unknown' | string
  status_since_event_id?: string | null
  status_note?: string | null
  gender?: string | null
  relations?: CharacterRelation[]
  known_fact_ids?: string[]
  attributes?: Record<string, unknown>
  acceptance_status?: 'candidate' | 'committed' | string
}

export interface Fact {
  id: string
  content: string
  story_time?: unknown
  about_character_ids?: string[]
  about_character_names?: string[]
  extraction_confidence?: number
  lifecycle_status?: string
  acceptance_status?: 'candidate' | 'committed' | string
  source_type?: 'chat' | 'document' | string
}

export interface PlotEvent {
  id: string
  summary: string
  story_time?: unknown
  participant_character_ids?: string[]
  participant_character_names?: string[]
  asserted_fact_ids?: string[]
  source_event_id?: string
  acceptance_status?: 'candidate' | 'committed' | string
}

export interface ContinuityDelivery {
  delivery_mode: string
  interrupt_risk: string
  armor_level: string
  initiator: string
  flow_blocked: boolean
}

export interface ContinuityEvent {
  id: string
  type?: string
  severity?: string
  confidence?: number
  evidence?: string[]
  affected_modules?: string[]
  delivery?: ContinuityDelivery
  status?: string
  [key: string]: unknown
}

export interface StoryProjection {
  characters?: Character[]
  facts?: Fact[]
  plot_events?: PlotEvent[]
  continuity?: ContinuityEvent[] | Record<string, unknown>
  document?: Record<string, unknown>
  preferences?: Record<string, unknown>
  StoryClock?: Record<string, unknown>
  [key: string]: unknown
}

export interface StateResponse {
  projection_schema_version: string
  log_head_seq: number
  head_event_id: string | null
  source_document_revision: string | null
  source_document_checksum: string | null
  story: StoryProjection
  updated_at: string | null
}

// ---- Continuity card actions ----
export interface IgnoreRequest {
  user_explanation?: string | null
  scope?: 'single_finding' | 'category'
}

export interface AcceptRequest {
  resolution_fact_id?: string | null
}

export interface CardActionResponse {
  continuity_event_id: string
  action: string
  deweighting_written: boolean
  category: string | null
}

// ---- Manuscript adopt ----
export interface AdoptRequest {
  content: string
  adopt_request_id: string
  adopted_from_message_id?: string | null
  document_id?: string
}

export interface AdoptResponse {
  revision_id: string
  duplicate: boolean
}

// ---- Chat History ----
export interface ChatMessage {
  message_id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
}

export interface ChatMessageListResponse {
  messages: ChatMessage[]
  total: number
  has_more: boolean
}
