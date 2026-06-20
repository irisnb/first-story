import './App.css'
import { useUiStore, type ViewKey } from '@/lib/store'
import { ProjectPicker } from '@/components/ProjectPicker'
import { HomeView } from '@/views/HomeView'
import { ModulesView } from '@/views/ModulesView'
import { ManuscriptView } from '@/views/ManuscriptView'
import { SettingsView } from '@/views/SettingsView'

// side-nav 导航项。文案原样（契约：主界面 / 五兄弟 / 正文 / 项目设置）。
const NAV_ITEMS: { key: ViewKey; label: string; desc: string }[] = [
  { key: 'home', label: '主界面', desc: '聊天创作' },
  { key: 'modules', label: '五兄弟', desc: '五大模块' },
  { key: 'manuscript', label: '正文', desc: 'Fountain 手稿' },
  { key: 'settings', label: '项目设置', desc: '频率与叠甲' },
]

// 五大模块标签（源头在此，向下传给五兄弟视图）：世界观/角色/剧情/主题/结构。
export const STORY_MODULE_LABELS = ['世界观', '角色', '剧情', '主题', '结构'] as const

function App() {
  const activeView = useUiStore((s) => s.activeView)
  const setView = useUiStore((s) => s.setView)
  const jumpToManuscript = useUiStore((s) => s.jumpToManuscript)

  return (
    <div className="app-root">
      <nav className="side-nav" aria-label="主导航">
        <div className="side-nav__brand">
          <span className="side-nav__title">Frist story</span>
          <span className="side-nav__subtitle">剧作老师 · 只递证据</span>
        </div>

        <div className="side-nav__project">
          <ProjectPicker />
        </div>

        <ul className="side-nav__list">
          {NAV_ITEMS.map((item) => (
            <li key={item.key}>
              <button
                type="button"
                className={`side-nav__item${activeView === item.key ? ' is-active' : ''}`}
                aria-current={activeView === item.key ? 'page' : undefined}
                onClick={() => setView(item.key)}
              >
                <span className="side-nav__item-label">{item.label}</span>
                <span className="side-nav__item-desc">{item.desc}</span>
              </button>
            </li>
          ))}
        </ul>

        {/* 直达正文：用户随时可一键跳到正文编辑器 */}
        <button
          type="button"
          className="side-nav__jump"
          onClick={jumpToManuscript}
        >
          直达正文
        </button>

        {/* 五兄弟速览：世界观 / 角色 / 剧情 / 主题 / 结构 */}
        <div className="side-nav__modules" aria-label="五大模块">
          {STORY_MODULE_LABELS.map((label) => (
            <button
              key={label}
              type="button"
              className="side-nav__module-chip"
              onClick={() => setView('modules')}
            >
              {label}
            </button>
          ))}
        </div>

        <p className="side-nav__hint">
          你比我懂你的故事。我只在你需要时递上证据，从不替你下定论。
        </p>
      </nav>

      <main className="app-main">
        {activeView === 'home' && <HomeView />}
        {activeView === 'modules' && <ModulesView />}
        {activeView === 'manuscript' && <ManuscriptView />}
        {activeView === 'settings' && <SettingsView />}
      </main>
    </div>
  )
}

export default App
