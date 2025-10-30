export interface KnownLLMProvider {
  key: string
  name: string
  description: string | null
  base_url: string | null
  logo_emoji: string | null
  logo_url: string | null
}

export interface LLMModel {
  id: number
  name: string
  capability: string | null
  quota: string | null
  concurrency_limit: number
  created_at: string
  updated_at: string
}

export interface LLMProvider {
  id: number
  provider_key: string | null
  provider_name: string
  base_url: string | null
  logo_emoji: string | null
  logo_url: string | null
  is_custom: boolean
  is_archived: boolean
  default_model_name: string | null
  masked_api_key: string
  models: LLMModel[]
  created_at: string
  updated_at: string
}

export interface LLMProviderCreatePayload {
  provider_key?: string | null
  provider_name: string
  base_url?: string | null
  api_key: string
  logo_emoji?: string | null
  logo_url?: string | null
  is_custom?: boolean
}

export interface LLMProviderUpdatePayload {
  provider_name?: string | null
  base_url?: string | null
  api_key?: string | null
  logo_emoji?: string | null
  logo_url?: string | null
  is_custom?: boolean | null
  default_model_name?: string | null
}

export interface LLMModelCreatePayload {
  name: string
  capability?: string | null
  quota?: string | null
  concurrency_limit?: number
}

export interface LLMModelUpdatePayload {
  capability?: string | null
  quota?: string | null
  concurrency_limit?: number
}

export interface ChatMessagePayload {
  role: string
  content: unknown
}

export interface LLMInvokePayload {
  messages: ChatMessagePayload[]
  parameters?: Record<string, unknown>
  model?: string | null
  model_id?: number | null
  temperature?: number | null
  prompt_id?: number | null
  prompt_version_id?: number | null
  persist_usage?: boolean
}
