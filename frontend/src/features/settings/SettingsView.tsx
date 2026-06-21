import { useUiStore } from '@/shared/store/ui-store'
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card'
import { LlmConfigSection } from './LlmConfigSection'

export function SettingsView() {
  const projectId = useUiStore((s) => s.currentProjectId)

  return (
    <section className="view-shell" aria-labelledby="settings-heading">
      <header className="mb-6">
        <h2 id="settings-heading" className="text-lg font-semibold">
          项目设置
        </h2>
        <p className="text-sm text-muted-foreground">
          配置模型、调整系统行为 —— 你说了算。
        </p>
      </header>

      {!projectId ? (
        <Card>
          <CardContent className="py-8">
            <p className="text-center text-muted-foreground">
              请先选择一个项目
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="flex flex-col gap-6">
          {/* Model Configuration Section */}
          <div>
            <h3 className="text-base font-medium mb-3">模型配置</h3>
            <p className="text-sm text-muted-foreground mb-4">
              配置对话和后台任务使用的模型。项目级配置优先于服务端默认配置。
            </p>
            <LlmConfigSection projectId={projectId} />
          </div>

          {/* Response Frequency Section */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">响应频率</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                控制后台 Agent 主动提醒你的频率。心流模式下，再严重的问题也只亮卡片、不插队。
              </p>
              <p className="mt-2 text-xs text-muted-foreground">
                （接入后端 preferences 后开放调节）
              </p>
            </CardContent>
          </Card>

          {/* Armor Thickness Section */}
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

          {/* Project Info Section */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">当前项目</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground font-mono">
                {projectId}
              </p>
            </CardContent>
          </Card>
        </div>
      )}
    </section>
  )
}

