import type { LlmProvider } from '../api/api-types'

export interface ProviderInfo {
  value: LlmProvider
  label: string
  defaultEndpoint: string
  modelPlaceholder: string
}

export const PROVIDERS: ProviderInfo[] = [
  {
    value: 'deepseek',
    label: 'DeepSeek',
    defaultEndpoint: 'https://api.deepseek.com',
    modelPlaceholder: 'deepseek-chat',
  },
  {
    value: 'openai',
    label: 'OpenAI',
    defaultEndpoint: 'https://api.openai.com/v1',
    modelPlaceholder: 'gpt-4o-mini',
  },
  {
    value: 'anthropic',
    label: 'Anthropic',
    defaultEndpoint: 'https://api.anthropic.com',
    modelPlaceholder: 'claude-sonnet-4-20250514',
  },
  {
    value: 'local',
    label: '本地 / OpenAI 兼容',
    defaultEndpoint: 'http://localhost:11434/v1',
    modelPlaceholder: '本地模型名称',
  },
]

export function getProviderInfo(provider: string): ProviderInfo | undefined {
  return PROVIDERS.find((p) => p.value === provider)
}

export function getDefaultEndpoint(provider: string): string {
  return getProviderInfo(provider)?.defaultEndpoint ?? ''
}

