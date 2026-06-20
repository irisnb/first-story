import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { useUiStore } from '@/lib/store'
import { Button } from '@/components/ui/button'

export function ProjectPicker() {
  const currentProjectId = useUiStore((s) => s.currentProjectId)
  const setProject = useUiStore((s) => s.setProject)
  const queryClient = useQueryClient()
  const [creating, setCreating] = useState(false)
  const [name, setName] = useState('')

  const { data } = useQuery({ queryKey: ['projects'], queryFn: api.listProjects })

  // 默认选中第一个项目
  useEffect(() => {
    if (!currentProjectId && data && data.projects.length > 0) {
      setProject(data.projects[0].id)
    }
  }, [currentProjectId, data, setProject])

  const createMutation = useMutation({
    mutationFn: () => api.createProject({ name: name.trim() }),
    onSuccess: (project) => {
      setProject(project.id)
      setName('')
      setCreating(false)
      queryClient.invalidateQueries({ queryKey: ['projects'] })
    },
  })

  return (
    <div className="flex flex-col gap-2">
      <label className="text-xs font-medium text-muted-foreground" htmlFor="project-select">
        项目
      </label>
      <select
        id="project-select"
        className="rounded-md border border-border bg-card/70 px-2 py-1.5 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
        value={currentProjectId ?? ''}
        onChange={(e) => setProject(e.target.value || null)}
      >
        <option value="" disabled>
          选择项目…
        </option>
        {data?.projects.map((p) => (
          <option key={p.id} value={p.id}>
            {p.name}
          </option>
        ))}
      </select>

      {creating ? (
        <div className="flex flex-col gap-2">
          <input
            className="rounded-md border border-border bg-card/70 px-2 py-1.5 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
            placeholder="新项目名称"
            value={name}
            autoFocus
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && name.trim()) createMutation.mutate()
              if (e.key === 'Escape') setCreating(false)
            }}
          />
          <div className="flex gap-2">
            <Button
              size="sm"
              onClick={() => createMutation.mutate()}
              disabled={!name.trim() || createMutation.isPending}
            >
              创建
            </Button>
            <Button variant="ghost" size="sm" onClick={() => setCreating(false)}>
              取消
            </Button>
          </div>
        </div>
      ) : (
        <Button variant="ghost" size="sm" className="justify-start" onClick={() => setCreating(true)}>
          + 新建项目
        </Button>
      )}
    </div>
  )
}
