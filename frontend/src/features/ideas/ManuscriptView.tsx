import { useCallback, useEffect, useRef, useState } from 'react'
import CodeMirror from '@uiw/react-codemirror'
import { EditorView } from '@codemirror/view'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Fountain } from 'fountain-js'
import { api, ApiError } from '@/shared/api/api'
import { useUiStore } from '@/shared/store/ui-store'
import { Button } from '@/shared/ui/button'

// 安静柔和的编辑器主题：无高对比、无花哨装饰，贴合 Fountain 纯文本本质。
const calmTheme = EditorView.theme({
  '&': { fontSize: '14px', backgroundColor: 'transparent' },
  '.cm-content': {
    fontFamily: "'Courier New', ui-monospace, monospace",
    padding: '16px 0',
    caretColor: 'hsl(var(--foreground))',
  },
  '.cm-gutters': { backgroundColor: 'transparent', border: 'none' },
  '.cm-activeLine': { backgroundColor: 'hsl(var(--muted) / 0.4)' },
  '.cm-activeLineGutter': { backgroundColor: 'transparent' },
  '&.cm-focused': { outline: 'none' },
})

const fountainParser = new Fountain()

export function ManuscriptView() {
  const projectId = useUiStore((s) => s.currentProjectId)
  const queryClient = useQueryClient()
  const [content, setContent] = useState('')
  const [dirty, setDirty] = useState(false)
  const [savedHint, setSavedHint] = useState<string | null>(null)
  const loadedFor = useRef<string | null>(null)

  // 拉取最近一版正文
  const { data: revisions } = useQuery({
    queryKey: ['revisions', projectId],
    queryFn: () => api.listRevisions(projectId!),
    enabled: Boolean(projectId),
  })

  useEffect(() => {
    if (!projectId) return
    if (loadedFor.current === projectId) return
    if (revisions && revisions.revisions.length > 0) {
      // revisions 按时间，取最新一条
      const latest = revisions.revisions[revisions.revisions.length - 1]
      setContent(latest.content)
      setDirty(false)
      loadedFor.current = projectId
    } else if (revisions) {
      setContent('')
      loadedFor.current = projectId
    }
  }, [projectId, revisions])

  const saveMutation = useMutation({
    mutationFn: () => api.saveRevision(projectId!, { content, document_id: 'main' }),
    onSuccess: (rev) => {
      setDirty(false)
      setSavedHint(`已保存 · ${new Date(rev.revised_at).toLocaleTimeString('zh-CN')}`)
      queryClient.invalidateQueries({ queryKey: ['revisions', projectId] })
      queryClient.invalidateQueries({ queryKey: ['state', projectId] })
    },
    onError: (err) => {
      setSavedHint(err instanceof ApiError ? `保存失败：${err.message}` : '保存失败')
    },
  })

  const onChange = useCallback((value: string) => {
    setContent(value)
    setDirty(true)
    setSavedHint(null)
  }, [])

  // Fountain 解析预览（标题/场景数）——只做轻量元信息，不做所见即所得
  let sceneCount = 0
  if (content.trim()) {
    try {
      const parsed = fountainParser.parse(content, true)
      sceneCount = (parsed.tokens ?? []).filter((t) => t.type === 'scene_heading').length
    } catch {
      sceneCount = 0
    }
  }

  if (!projectId) {
    return (
      <section className="view-shell" aria-labelledby="manuscript-heading">
        <h2 id="manuscript-heading" className="text-lg font-semibold">
          正文
        </h2>
        <p className="mt-2 text-sm text-muted-foreground">先选择或新建项目，再开始写正文。</p>
      </section>
    )
  }

  return (
    <section className="view-shell flex flex-col" aria-labelledby="manuscript-heading">
      <header className="mb-3 flex items-center justify-between">
        <div>
          <h2 id="manuscript-heading" className="text-lg font-semibold">
            正文
          </h2>
          <p className="text-xs text-muted-foreground">
            Fountain 格式 · {sceneCount} 个场景{dirty ? ' · 未保存' : ''}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {savedHint && <span className="text-xs text-muted-foreground">{savedHint}</span>}
          <Button
            size="sm"
            onClick={() => saveMutation.mutate()}
            disabled={!dirty || saveMutation.isPending}
          >
            {saveMutation.isPending ? '保存中…' : '保存'}
          </Button>
        </div>
      </header>

      <div className="flex-1 overflow-auto rounded-md border border-border bg-card/60 px-3">
        <CodeMirror
          value={content}
          onChange={onChange}
          theme={calmTheme}
          extensions={[EditorView.lineWrapping]}
          basicSetup={{
            lineNumbers: false,
            foldGutter: false,
            highlightActiveLineGutter: false,
          }}
          placeholder="标题页、场景标题（INT./EXT.）、动作、角色名、对白……尽管写，系统在后台静静观察。"
        />
      </div>
    </section>
  )
}

