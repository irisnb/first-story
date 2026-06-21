import './App.css'
import { Suspense, lazy, useEffect } from 'react'
import { BrowserRouter, Routes, Route, useNavigate, useLocation, NavLink } from 'react-router-dom'
import { useUiStore, type ViewKey } from '@/shared/store/ui-store'
import { ProjectPicker } from '@/components/ProjectPicker'
import { NAV_ITEMS, STORY_MODULE_LABELS } from '@/features/shell/navigation'

// Lazy load views for code splitting
const HomeView = lazy(() => import('@/features/home').then(m => ({ default: m.HomeView })))
const ModulesView = lazy(() => import('@/features/modules').then(m => ({ default: m.ModulesView })))
const IdeaWarehouseView = lazy(() => import('@/features/ideas').then(m => ({ default: m.IdeaWarehouseView })))
const ScreenplayView = lazy(() => import('@/features/screenplay').then(m => ({ default: m.ScreenplayView })))
const SettingsView = lazy(() => import('@/features/settings').then(m => ({ default: m.SettingsView })))

function ViewFallback() {
  return <div className="view-shell text-sm text-muted-foreground p-4">加载中...</div>
}

// Route path mapping
const VIEW_PATHS: Record<ViewKey, string> = {
  home: '/',
  modules: '/modules',
  ideas: '/ideas',
  screenplay: '/screenplay',
  settings: '/settings',
}

const PATH_VIEWS: Record<string, ViewKey> = {
  '/': 'home',
  '/modules': 'modules',
  '/ideas': 'ideas',
  '/screenplay': 'screenplay',
  '/settings': 'settings',
}

// Component that syncs URL with store
function RouteSync() {
  const location = useLocation()
  const setView = useUiStore((s) => s.setView)

  // Sync URL to store on mount and location change
  useEffect(() => {
    const viewKey = PATH_VIEWS[location.pathname] || 'home'
    setView(viewKey)
  }, [location.pathname, setView])

  return null
}

// Side navigation with React Router
function SideNav() {
  const navigate = useNavigate()

  return (
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
            <NavLink
              to={VIEW_PATHS[item.key]}
              className={({ isActive }) =>
                `side-nav__item${isActive ? ' is-active' : ''}`
              }
            >
              <span className="side-nav__item-label">{item.label}</span>
              <span className="side-nav__item-desc">{item.desc}</span>
            </NavLink>
          </li>
        ))}
      </ul>

      <button
        type="button"
        className="side-nav__jump"
        onClick={() => navigate('/screenplay')}
      >
        直达剧本
      </button>

      <div className="side-nav__modules" aria-label="五大模块">
        {STORY_MODULE_LABELS.map((label) => (
          <button
            key={label}
            type="button"
            className="side-nav__module-chip"
            onClick={() => navigate('/modules')}
          >
            {label}
          </button>
        ))}
      </div>

      <p className="side-nav__hint">
        你比我懂你的故事。我只在你需要时递上证据，从不替你下定论。
      </p>
    </nav>
  )
}

function AppRoutes() {
  return (
    <div className="app-root">
      <SideNav />
      <main className="app-main">
        <Suspense fallback={<ViewFallback />}>
          <Routes>
            <Route path="/" element={<HomeView />} />
            <Route path="/modules" element={<ModulesView />} />
            <Route path="/ideas" element={<IdeaWarehouseView />} />
            <Route path="/screenplay" element={<ScreenplayView />} />
            <Route path="/settings" element={<SettingsView />} />
          </Routes>
        </Suspense>
      </main>
      <RouteSync />
    </div>
  )
}

function App() {
  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  )
}

export default App
