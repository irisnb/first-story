import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card'
import { Button } from '@/shared/ui/button'
import { api, ApiError } from '@/shared/api/api'
import { PROVIDERS, getDefaultEndpoint } from '@/shared/lib/llm-config-defaults'
import type { LlmConfigResponse, LlmConfigSlot, LlmConfigUpdateRequest } from '@/shared/api/api-types'

interface LlmConfigCardProps {
  projectId: string
  slot: LlmConfigSlot
  config: LlmConfigResponse | null
  onConfigChange: (config: LlmConfigResponse) => void
}

const SLOT_LABELS: Record<LlmConfigSlot, string> = {
  chat: '对话模型',
  utility: '后台工具模型',
}

const SLOT_DESCRIPTIONS: Record<LlmConfigSlot, string> = {
  chat: '用于与用户的对话交互，需要最高质量的回复',
  utility: '用于提取、分类、摘要、别名解析等后台任务',
}

export function LlmConfigCard({ projectId, slot, config, onConfigChange }: LlmConfigCardProps) {
  const [provider, setProvider] = useState(config?.provider ?? 'deepseek')
  const [model, setModel] = useState(config?.model ?? '')
  const [apiEndpoint, setApiEndpoint] = useState(config?.api_endpoint ?? '')
  const [apiKey, setApiKey] = useState('')
  const [proxy, setProxy] = useState(config?.proxy ?? '')
  const [timeoutSeconds, setTimeoutSeconds] = useState(config?.timeout_seconds ?? 60)

  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  // Auto-hide success message after 3 seconds
  useEffect(() => {
    if (success) {
      const timer = setTimeout(() => setSuccess(null), 3000)
      return () => clearTimeout(timer)
    }
  }, [success])

  // Sync form with config when it changes (e.g., after load)
  useEffect(() => {
    if (config) {
      setProvider(config.provider)
      setModel(config.model)
      setApiEndpoint(config.api_endpoint)
      setProxy(config.proxy)
      setTimeoutSeconds(config.timeout_seconds)
    }
  }, [config])

  // Auto-fill default endpoint when provider changes (only if empty or matches old default)
  const handleProviderChange = (newProvider: string) => {
    const oldDefault = getDefaultEndpoint(provider)
    const newDefault = getDefaultEndpoint(newProvider)
    
    setProvider(newProvider)
    
    // Only auto-fill if endpoint is empty or was the old provider's default
    if (!apiEndpoint || apiEndpoint === oldDefault) {
      setApiEndpoint(newDefault)
    }
  }

  const validateForm = (): string | null => {
    if (!model.trim()) return '请输入模型名称'
    if (!apiEndpoint.trim()) return '请输入 API 端点'
    try {
      new URL(apiEndpoint)
    } catch {
      return 'API 端点格式不正确'
    }
    if (timeoutSeconds <= 0) return '超时时间必须大于 0'
    if (proxy && proxy.trim()) {
      try {
        new URL(proxy)
      } catch {
        return '代理地址格式不正确'
      }
    }
    // local provider can have empty API key
    if (provider !== 'local' && !config?.is_configured && !apiKey.trim()) {
      return '请输入 API Key'
    }
    return null
  }

  const handleSave = async () => {
    setError(null)
    setSuccess(null)

    const validationError = validateForm()
    if (validationError) {
      setError(validationError)
      return
    }

    setSaving(true)
    try {
      const payload: LlmConfigUpdateRequest = {
        provider,
        model: model.trim(),
        api_endpoint: apiEndpoint.trim(),
        proxy: proxy.trim() || undefined,
        timeout_seconds: timeoutSeconds,
      }
      
      // Only include api_key if user entered a new one
      if (apiKey.trim()) {
        payload.api_key = apiKey.trim()
      }

      const response = await api.updateProjectLlmConfig(projectId, slot, payload)
      onConfigChange(response)
      setApiKey('') // Clear sensitive input after save
      setSuccess('配置已保存')
    } catch (e) {
      if (e instanceof ApiError) {
        setError(`保存失败: ${e.message}`)
      } else {
        setError('保存失败，请检查网络连接')
      }
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!confirm('确定要重置此配置吗？将恢复使用服务端默认配置。')) return

    setError(null)
    setSuccess(null)
    setDeleting(true)
    try {
      await api.deleteProjectLlmConfig(projectId, slot)
      // Reset form to defaults
      setProvider('deepseek')
      setModel('')
      setApiEndpoint(getDefaultEndpoint('deepseek'))
      setApiKey('')
      setProxy('')
      setTimeoutSeconds(60)
      setSuccess('配置已重置')
    } catch (e) {
      if (e instanceof ApiError) {
        setError(`重置失败: ${e.message}`)
      } else {
        setError('重置失败，请检查网络连接')
      }
    } finally {
      setDeleting(false)
    }
  }

  const providerInfo = PROVIDERS.find((p) => p.value === provider)

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">{SLOT_LABELS[slot]}</CardTitle>
          {config?.is_configured ? (
            <span className="text-xs bg-green-100 text-green-800 px-2 py-0.5 rounded">
              已配置
            </span>
          ) : (
            <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">
              未配置项目级模型
            </span>
          )}
        </div>
        <p className="text-xs text-muted-foreground">{SLOT_DESCRIPTIONS[slot]}</p>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Status indicator */}
        {config?.is_configured && config.api_key_preview && (
          <div className="text-xs text-muted-foreground">
            已保存密钥：<code className="bg-muted px-1 rounded">{config.api_key_preview}</code>
          </div>
        )}
        {!config?.is_configured && (
          <div className="text-xs text-muted-foreground">
            将尝试使用服务端默认配置，如果服务端未配置则相关能力不可用。
          </div>
        )}

        {/* Error/Success messages */}
        {error && (
          <div className="text-xs text-red-600 bg-red-50 px-2 py-1 rounded">{error}</div>
        )}
        {success && (
          <div className="text-xs text-green-600 bg-green-50 px-2 py-1 rounded">{success}</div>
        )}

        {/* Form fields */}
        <div className="grid gap-3">
          <div className="grid grid-cols-[100px_1fr] items-center gap-2">
            <label className="text-sm text-right">服务商</label>
            <select
              value={provider}
              onChange={(e) => handleProviderChange(e.target.value)}
              className="border rounded px-2 py-1 text-sm bg-background"
            >
              {PROVIDERS.map((p) => (
                <option key={p.value} value={p.value}>
                  {p.label}
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-[100px_1fr] items-center gap-2">
            <label className="text-sm text-right">模型</label>
            <input
              type="text"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              placeholder={providerInfo?.modelPlaceholder}
              className="border rounded px-2 py-1 text-sm bg-background w-full"
            />
          </div>

          <div className="grid grid-cols-[100px_1fr] items-center gap-2">
            <label className="text-sm text-right">API 端点</label>
            <input
              type="text"
              value={apiEndpoint}
              onChange={(e) => setApiEndpoint(e.target.value)}
              placeholder="https://api.example.com"
              className="border rounded px-2 py-1 text-sm bg-background w-full"
            />
          </div>

          <div className="grid grid-cols-[100px_1fr] items-center gap-2">
            <label className="text-sm text-right">API Key</label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder={config?.is_configured ? '留空保持不变' : '输入新的 API Key'}
              autoComplete="new-password"
              className="border rounded px-2 py-1 text-sm bg-background w-full"
            />
          </div>

          <div className="grid grid-cols-[100px_1fr] items-center gap-2">
            <label className="text-sm text-right">代理</label>
            <input
              type="text"
              value={proxy}
              onChange={(e) => setProxy(e.target.value)}
              placeholder="http://127.0.0.1:7890（可选）"
              className="border rounded px-2 py-1 text-sm bg-background w-full"
            />
          </div>

          <div className="grid grid-cols-[100px_1fr] items-center gap-2">
            <label className="text-sm text-right">超时(秒)</label>
            <input
              type="number"
              value={timeoutSeconds}
              onChange={(e) => setTimeoutSeconds(Number(e.target.value))}
              min={1}
              className="border rounded px-2 py-1 text-sm bg-background w-24"
            />
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-2 pt-2">
          <Button size="sm" onClick={handleSave} disabled={saving}>
            {saving ? '保存中...' : '保存配置'}
          </Button>
          {config?.is_configured && (
            <Button
              size="sm"
              variant="outline"
              onClick={handleDelete}
              disabled={deleting}
            >
              {deleting ? '重置中...' : '重置配置'}
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

