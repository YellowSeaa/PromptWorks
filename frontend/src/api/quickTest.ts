import type { HttpError } from './http'
import { API_BASE_URL } from './http'
import type { ChatMessagePayload } from '../types/llm'

export interface QuickTestStreamPayload {
  providerId: number
  modelId?: number | null
  modelName?: string | null
  messages: ChatMessagePayload[]
  temperature: number
  parameters?: Record<string, unknown>
  promptId?: number | null
  promptVersionId?: number | null
  persistUsage?: boolean
}

export interface QuickTestHistoryMessage {
  role: string
  content: unknown
}

export interface QuickTestHistoryItem {
  id: number
  provider_id: number | null
  provider_name: string | null
  provider_logo_emoji: string | null
  provider_logo_url: string | null
  model_id: number | null
  model_name: string
  response_text: string | null
  messages: QuickTestHistoryMessage[]
  temperature: number | null
  latency_ms: number | null
  prompt_tokens: number | null
  completion_tokens: number | null
  total_tokens: number | null
  prompt_id: number | null
  prompt_version_id: number | null
  created_at: string
}

export interface SSEMessage {
  event?: string
  data: string
}

function parseSSEChunk(chunk: string): SSEMessage | null {
  if (!chunk.trim()) return null
  let eventName: string | undefined
  const dataLines: string[] = []
  const lines = chunk.split('\n')
  for (const raw of lines) {
    const line = raw.trimEnd()
    if (!line) continue
    if (line.startsWith('event:')) {
      eventName = line.slice(6).trim()
    } else if (line.startsWith('data:')) {
      dataLines.push(line.slice(5).trim())
    }
  }
  if (!dataLines.length) return null
  return { event: eventName, data: dataLines.join('\n') }
}

async function parseErrorPayload(response: Response): Promise<unknown> {
  const text = await response.text()
  if (!text) return null
  try {
    return JSON.parse(text)
  } catch (error) {
    void error
    return text
  }
}

export async function* streamQuickTest(
  payload: QuickTestStreamPayload,
  options: { signal?: AbortSignal } = {}
): AsyncGenerator<SSEMessage, void, undefined> {
  const url = `${API_BASE_URL}/llm-providers/${payload.providerId}/invoke/stream`
  const body: Record<string, unknown> = {
    messages: payload.messages,
    parameters: payload.parameters ?? {},
    temperature: payload.temperature
  }
  if (payload.modelId != null) {
    body.model_id = payload.modelId
  }
  if (payload.modelName) {
    body.model = payload.modelName
  }
  if (payload.promptId != null) {
    body.prompt_id = payload.promptId
  }
  if (payload.promptVersionId != null) {
    body.prompt_version_id = payload.promptVersionId
  }

  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal: options.signal
  })

  if (!response.ok) {
    const error: HttpError = new Error('请求接口失败')
    error.status = response.status
    error.payload = await parseErrorPayload(response)
    throw error
  }
  if (!response.body) {
    throw new Error('流式响应不可用')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      let separatorIndex = buffer.indexOf('\n\n')
      while (separatorIndex !== -1) {
        const chunk = buffer.slice(0, separatorIndex)
        buffer = buffer.slice(separatorIndex + 2)
        const parsed = parseSSEChunk(chunk)
        if (parsed) {
          yield parsed
        }
        separatorIndex = buffer.indexOf('\n\n')
      }
    }
    buffer += decoder.decode()
    const remaining = buffer.trim()
    if (remaining) {
      const parsed = parseSSEChunk(remaining)
      if (parsed) {
        yield parsed
      }
    }
  } finally {
    reader.releaseLock()
  }
}

export async function invokeQuickTest(
  payload: QuickTestStreamPayload,
  options: { signal?: AbortSignal } = {}
): Promise<unknown> {
  const url = `${API_BASE_URL}/llm-providers/${payload.providerId}/invoke`
  const body: Record<string, unknown> = {
    messages: payload.messages,
    parameters: payload.parameters ?? {}
  }
  if (payload.modelId != null) {
    body.model_id = payload.modelId
  }
  if (payload.modelName) {
    body.model = payload.modelName
  }
  if (payload.promptId != null) {
    body.prompt_id = payload.promptId
  }
  if (payload.promptVersionId != null) {
    body.prompt_version_id = payload.promptVersionId
  }
  if (typeof payload.temperature === 'number') {
    body.temperature = payload.temperature
  }
  if (payload.persistUsage === true) {
    body.persist_usage = true
  }

  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal: options.signal
  })

  if (!response.ok) {
    const error: HttpError = new Error('请求接口失败')
    error.status = response.status
    error.payload = await parseErrorPayload(response)
    throw error
  }
  return response.json()
}

export async function fetchQuickTestHistory(
  params: { limit?: number; offset?: number } = {}
): Promise<QuickTestHistoryItem[]> {
  const search = new URLSearchParams()
  if (params.limit !== undefined) {
    search.set('limit', String(params.limit))
  }
  if (params.offset !== undefined) {
    search.set('offset', String(params.offset))
  }
  const query = search.toString()
  const url = `${API_BASE_URL}/llm-providers/quick-test/history${query ? `?${query}` : ''}`
  const response = await fetch(url)
  if (!response.ok) {
    const error: HttpError = new Error('获取历史记录失败')
    error.status = response.status
    error.payload = await parseErrorPayload(response)
    throw error
  }
  const data = (await response.json()) as QuickTestHistoryItem[]
  return data
}
