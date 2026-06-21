/**
 * 创意卡片数据结构
 * 
 * 基于 Oracle 建议的设计：
 * - 卡片有版本概念（revision_id）
 * - 编辑时生成新版本，不覆盖历史
 * - 支持软删除和状态管理
 */

/** 卡片状态：用户意图 */
export type IdeaCardStatus = 'active' | 'shelved' | 'archived'

/** 卡片来源 */
export interface IdeaCardSource {
  /** 来源消息 ID（可选） */
  message_id?: string
  /** 原文节选（独立保存，避免依赖聊天历史） */
  excerpt: string
}

/** 创意卡片 */
export interface IdeaCard {
  /** 唯一标识 */
  id: string
  /** 当前版本 ID */
  current_revision_id: string
  /** 用户状态 */
  status: IdeaCardStatus
  /** 创建时间 */
  created_at: string
  /** 更新时间 */
  updated_at: string
  /** 来源 */
  source?: IdeaCardSource
}

/** 卡片版本（内容存储在版本中） */
export interface IdeaCardRevision {
  /** 版本 ID */
  revision_id: string
  /** 所属卡片 ID */
  card_id: string
  /** 卡片内容 */
  content: string
  /** 创建时间 */
  created_at: string
}

/** 创建卡片请求 */
export interface CreateIdeaCardRequest {
  content: string
  source?: IdeaCardSource
}

/** 更新卡片请求 */
export interface UpdateIdeaCardRequest {
  content: string
}

/** 卡片列表响应 */
export interface IdeaCardListResponse {
  cards: IdeaCard[]
  revisions: IdeaCardRevision[]
}

/** 单张卡片响应（含内容） */
export interface IdeaCardResponse {
  card: IdeaCard
  revision: IdeaCardRevision
}
