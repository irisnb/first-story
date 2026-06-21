import type { ViewKey } from '@/shared/store/ui-store'

const NAV_ITEMS: { key: ViewKey; label: string; desc: string }[] = [
  { key: 'home', label: '主界面', desc: '聊天创作' },
  { key: 'modules', label: '五兄弟', desc: '五大模块' },
  { key: 'ideas', label: '创意仓库', desc: '想法卡片' },
  { key: 'screenplay', label: '剧本', desc: 'Fountain 手稿' },
  { key: 'settings', label: '项目设置', desc: '频率与叠甲' },
]

export const STORY_MODULE_LABELS = ['世界观', '角色', '剧情', '主题', '结构'] as const

export { NAV_ITEMS }
