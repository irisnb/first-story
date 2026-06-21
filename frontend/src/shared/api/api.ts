// 轻量 API client —— Base 走 Vite 代理到 http://localhost:8000，前缀 /api/v1。
// 处理 service 层抛出的 404（OpenAPI 未声明）与 422 校验错误。

import type {
  AcceptRequest,
  AdoptRequest,
  AdoptResponse,
  CardActionResponse,
  ChatMessageListResponse,
  ChatRequest,
  ChatResponse,
  ClassifyRequest,
  ClassifyResponse,
  CreateProjectRequest,
  DocumentRevision,
  IgnoreRequest,
  LlmConfigListResponse,
  LlmConfigResponse,
  LlmConfigUpdateRequest,
  LockResponse,
  ModuleResponse,
  ProjectListResponse,
  ProjectResponse,
  RevisionListResponse,
  SaveRevisionRequest,
  StateResponse,
  UpdateModuleRequest,
  UpdateModuleResponse,
} from './api-types'

const API_PREFIX = '/api/v1'

export class ApiError extends Error {
  status: number
  body: unknown
  constructor(status: number, message: string, body: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.body = body
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  parseAs: 'json' | 'text' = 'json',
): Promise<T> {
  const res = await fetch(path, {
    headers:
      options.body && !(options.headers as Record<string, string>)?.['Content-Type']
        ? { 'Content-Type': 'application/json', ...(options.headers ?? {}) }
        : options.headers,
    ...options,
  })

  if (!res.ok) {
    let body: unknown = null
    try {
      body = await res.json()
    } catch {
      body = await res.text().catch(() => null)
    }
    const detail =
      typeof body === 'object' && body && 'detail' in body
        ? JSON.stringify((body as { detail: unknown }).detail)
        : res.statusText
    throw new ApiError(res.status, `${res.status} ${detail}`, body)
  }

  if (parseAs === 'text') return (await res.text()) as unknown as T
  if (res.status === 204) return undefined as unknown as T
  return (await res.json()) as T
}

export const api = {
  // ---- Projects ----
  listProjects: () => request<ProjectListResponse>(`${API_PREFIX}/projects`),

  createProject: (body: CreateProjectRequest) =>
    request<ProjectResponse>(`${API_PREFIX}/projects`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  getProject: (projectId: string) =>
    request<ProjectResponse>(`${API_PREFIX}/projects/${projectId}`),

  // ---- Chat ----
  chat: (projectId: string, body: ChatRequest) =>
    request<ChatResponse>(`${API_PREFIX}/projects/${projectId}/chat`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  getChatMessages: (projectId: string, before?: string, limit = 50) =>
    request<ChatMessageListResponse>(
      `${API_PREFIX}/projects/${projectId}/chat/messages?limit=${limit}${before ? `&before=${encodeURIComponent(before)}` : ''}`,
    ),

  adopt: (projectId: string, body: AdoptRequest) =>
    request<AdoptResponse>(`${API_PREFIX}/projects/${projectId}/manuscript/adopt`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  // ---- Documents ----
  listRevisions: (projectId: string, documentId = 'main') =>
    request<RevisionListResponse>(
      `${API_PREFIX}/projects/${projectId}/documents?document_id=${encodeURIComponent(documentId)}`,
    ),

  saveRevision: (projectId: string, body: SaveRevisionRequest) =>
    request<DocumentRevision>(`${API_PREFIX}/projects/${projectId}/documents`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  exportDocument: (projectId: string, documentId = 'main', format = 'fountain') =>
    request<string>(
      `${API_PREFIX}/projects/${projectId}/documents/export?document_id=${encodeURIComponent(
        documentId,
      )}&format=${encodeURIComponent(format)}`,
      {},
      'text',
    ),

  // ---- State ----
  getState: (projectId: string) =>
    request<StateResponse>(`${API_PREFIX}/projects/${projectId}/state`),

  // ---- Continuity card actions ----
  ignoreContinuity: (projectId: string, eventId: string, body: IgnoreRequest) =>
    request<CardActionResponse>(
      `${API_PREFIX}/projects/${projectId}/continuity-events/${eventId}/ignore`,
      { method: 'POST', body: JSON.stringify(body) },
    ),

  acceptContinuity: (projectId: string, eventId: string, body: AcceptRequest) =>
    request<CardActionResponse>(
      `${API_PREFIX}/projects/${projectId}/continuity-events/${eventId}/accept`,
      { method: 'POST', body: JSON.stringify(body) },
    ),

  // ---- Modules ----
  getModule: (projectId: string, moduleName: string) =>
    request<ModuleResponse>(`${API_PREFIX}/projects/${projectId}/modules/${moduleName}`),

  updateModule: (projectId: string, moduleName: string, body: UpdateModuleRequest) =>
    request<UpdateModuleResponse>(
      `${API_PREFIX}/projects/${projectId}/modules/${moduleName}`,
      { method: 'PUT', body: JSON.stringify(body) },
    ),

  acquireLock: (projectId: string, moduleName: string) =>
    request<LockResponse>(
      `${API_PREFIX}/projects/${projectId}/modules/${moduleName}/lock`,
      { method: 'POST' },
    ),

  releaseLock: (projectId: string, moduleName: string) =>
    request<LockResponse>(
      `${API_PREFIX}/projects/${projectId}/modules/${moduleName}/lock`,
      { method: 'DELETE' },
    ),

  extendLock: (projectId: string, moduleName: string) =>
    request<LockResponse>(
      `${API_PREFIX}/projects/${projectId}/modules/${moduleName}/heartbeat`,
      { method: 'POST' },
    ),

  // ---- Classification ----
  classify: (projectId: string, body: ClassifyRequest) =>
    request<ClassifyResponse>(`${API_PREFIX}/projects/${projectId}/classify`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  // ---- LLM Configuration ----
  getProjectLlmConfigs: (projectId: string) =>
    request<LlmConfigListResponse>(`${API_PREFIX}/projects/${projectId}/llm-config`),

  getProjectLlmConfig: (projectId: string, slot: string) =>
    request<LlmConfigResponse>(`${API_PREFIX}/projects/${projectId}/llm-config/${slot}`),

  updateProjectLlmConfig: (projectId: string, slot: string, body: LlmConfigUpdateRequest) =>
    request<LlmConfigResponse>(`${API_PREFIX}/projects/${projectId}/llm-config/${slot}`, {
      method: 'PUT',
      body: JSON.stringify(body),
    }),

  deleteProjectLlmConfig: (projectId: string, slot: string) =>
    request<{ status: string; message: string }>(
      `${API_PREFIX}/projects/${projectId}/llm-config/${slot}`,
      { method: 'DELETE' },
    ),
}
