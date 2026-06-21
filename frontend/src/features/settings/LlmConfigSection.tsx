import { useState, useEffect } from 'react'
import { api, ApiError } from '@/shared/api/api'
import { LlmConfigCard } from './LlmConfigCard'
import type { LlmConfigResponse, LlmConfigSlot } from '@/shared/api/api-types'

interface LlmConfigSectionProps {
  projectId: string
}

const SLOTS: LlmConfigSlot[] = ['chat', 'utility']

function createEmptyConfig(slot: LlmConfigSlot): LlmConfigResponse {
  return {
    slot,
    provider: 'deepseek',
    model: '',
    api_endpoint: 'https://api.deepseek.com',
    api_key_preview: '',
    proxy: '',
    timeout_seconds: 60,
    is_configured: false,
  }
}

export function LlmConfigSection({ projectId }: LlmConfigSectionProps) {
  const [configsBySlot, setConfigsBySlot] = useState<Record<LlmConfigSlot, LlmConfigResponse>>(() => ({
    chat: createEmptyConfig('chat'),
    utility: createEmptyConfig('utility'),
  }))
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true

    async function loadConfigs() {
      setLoading(true)
      setLoadError(null)
      try {
        const response = await api.getProjectLlmConfigs(projectId)
        if (!mounted) return

        // Build a map from the response, filling in any missing slots
        const map: Record<LlmConfigSlot, LlmConfigResponse> = {
          chat: createEmptyConfig('chat'),
          utility: createEmptyConfig('utility'),
        }
        for (const config of response.configs) {
          map[config.slot] = config
        }
        setConfigsBySlot(map)
      } catch (e) {
        if (!mounted) return
        if (e instanceof ApiError) {
          setLoadError(`加载配置失败: ${e.message}`)
        } else {
          setLoadError('加载配置失败，请检查网络连接')
        }
      } finally {
        if (mounted) setLoading(false)
      }
    }

    loadConfigs()
    return () => {
      mounted = false
    }
  }, [projectId])

  const handleConfigChange = (slot: LlmConfigSlot, config: LlmConfigResponse) => {
    setConfigsBySlot((prev) => ({
      ...prev,
      [slot]: config,
    }))
  }

  if (loading) {
    return (
      <div className="text-sm text-muted-foreground py-4">
        正在加载配置...
      </div>
    )
  }

  if (loadError) {
    return (
      <div className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded">
        {loadError}
      </div>
    )
  }

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {SLOTS.map((slot) => (
        <LlmConfigCard
          key={slot}
          projectId={projectId}
          slot={slot}
          config={configsBySlot[slot]}
          onConfigChange={(config) => handleConfigChange(slot, config)}
        />
      ))}
    </div>
  )
}

