import { useUiStore } from '@/lib/store'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export function SettingsView() {
  const projectId = useUiStore((s) => s.currentProjectId)

  return (
    <section className="view-shell" aria-labelledby="settings-heading">
      <header className="mb-4">
        <h2 id="settings-heading" className="text-lg font-semibold">
          项目设置
        </h2>
        <p className="text-sm text-muted-foreground">
          调整系统主动开口的频率和厚度 —— 你说了算。
        </p>
      </header>

      <div className="flex flex-col gap-4 lg:max-w-2xl">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">响应频率</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              控制后台 Agent 主动提醒你的频率。心流模式下，再严重的问题也只亮卡片、不插队。
            </p>
            <p className="mt-2 text-xs text-muted-foreground">（接入后端 preferences 后开放调节）</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">叠甲厚度</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              专业建议裹几层免责保护。越厚越温和，越薄越直接 —— 默认偏厚。
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">当前项目</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              {projectId ? `ID：${projectId}` : '尚未选择项目'}
            </p>
          </CardContent>
        </Card>
      </div>
    </section>
  )
}
