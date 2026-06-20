// 轻量 API client —— Base 走 Vite 代理到 http://localhost:8000，前缀 /api/v1。
// 处理 service 层抛出的 404（OpenAPI 未声明）与 422 校验错误。

import type {
  AcceptRequest,
  AdoptRequest,
  AdoptResponse,
  CardActionResponse,
  ChatRequest,
  ChatResponse,
  CreateProjectRequest,
  DocumentRevision,
  IgnoreRequest,
  ProjectListResponse,
  ProjectResponse,
  RevisionListResponse,
  SaveRevisionRequest,
  StateResponse,
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
}
