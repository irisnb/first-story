// 前端结构契约测试（从旧 frontend/structure-contract.test.mjs 保留）
//
// 这是新前端的【验收标准】，不是旧实现的描述。旧前端已删除重做。
// 文档对应：docs/api-contract.md 附录 D。
//
// ⚠️ 使用前必须做一件事：把下面 NEW_FRONTEND_ROOT 改成重做后新前端的实际目录，
//    并确认入口文件名（App.tsx / App.css 或等价文件）。改完即可 `node --test` 验收。
//
// 旧路径为 ./src/App.tsx、./src/App.css（相对本测试文件原所在的 frontend/）。

import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

// 新前端根目录（相对本文件）
const NEW_FRONTEND_ROOT = './frontend/'
// TODO(重做后确认): 入口组件与样式文件名（相对 NEW_FRONTEND_ROOT）
const APP_SOURCE_PATH = 'src/App.tsx'
const APP_STYLES_PATH = 'src/App.css'

const appSource = readFileSync(new URL(NEW_FRONTEND_ROOT + APP_SOURCE_PATH, import.meta.url), 'utf8')
const appStyles = readFileSync(new URL(NEW_FRONTEND_ROOT + APP_STYLES_PATH, import.meta.url), 'utf8')

test('App shell exposes left navigation and required secondary pages', () => {
  const requiredMarkup = [
    'className="side-nav"',
    '主界面',
    '项目设置',
    '五兄弟',
    '正文',
    '直达正文',
  ]

  for (const marker of requiredMarkup) {
    assert.match(appSource, new RegExp(marker.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')), `${marker} should exist in App.tsx`)
  }
})

test('Story modules expose world, character, plot, theme, and structure detail entries', () => {
  for (const label of ['世界观', '角色', '剧情', '主题', '结构']) {
    assert.match(appSource, new RegExp(label), `${label} should be reachable from the five-module page`)
  }
})

test('Glassmorphism shell styles exist for navigation, secondary pages, and evidence surfaces', () => {
  for (const selector of ['.side-nav', '.view-shell', '.story-module-grid', '.evidence-panel']) {
    assert.match(appStyles, new RegExp(selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')), `${selector} should be styled`)
  }

  assert.match(appStyles, /backdrop-filter:\s*blur/, 'glass panels should use backdrop-filter blur')
})
