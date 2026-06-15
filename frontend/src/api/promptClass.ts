import { request } from './http'

export interface PromptClassStats {
  id: number
  name: string
  description: string | null
  created_at: string
  updated_at: string
  prompt_count: number
  latest_prompt_updated_at: string | null
}

export interface PromptClassCreatePayload {
  name: string
  description?: string | null
}

export interface PromptClassUpdatePayload {
  name?: string
  description?: string | null
}

export async function listPromptClasses(params: {
  q?: string
  limit?: number
  offset?: number
} = {}): Promise<PromptClassStats[]> {
  const searchParams = new URLSearchParams()
  if (params.q) searchParams.set('q', params.q)
  if (typeof params.limit === 'number') searchParams.set('limit', String(params.limit))
  if (typeof params.offset === 'number') searchParams.set('offset', String(params.offset))
  const query = searchParams.toString()
  const path = `/prompt-classes/${query ? `?${query}` : ''}`
  return request<PromptClassStats[]>(path)
}

export async function createPromptClass(payload: PromptClassCreatePayload) {
  return request<PromptClassStats>('/prompt-classes/', {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}

export async function updatePromptClass(
  classId: number,
  payload: PromptClassUpdatePayload
) {
  return request<PromptClassStats>(`/prompt-classes/${classId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  })
}

export async function deletePromptClass(classId: number) {
  await request<void>(`/prompt-classes/${classId}`, {
    method: 'DELETE'
  })
}
