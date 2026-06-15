import { request } from './http'

export interface PromptTagStats {
  id: number
  name: string
  color: string
  prompt_count: number
  created_at: string
  updated_at: string
}

export interface PromptTagListResponse {
  items: PromptTagStats[]
  tagged_prompt_total: number
}

export interface PromptTagCreatePayload {
  name: string
  color: string
}

export async function listPromptTags(): Promise<PromptTagListResponse> {
  return request<PromptTagListResponse>('/prompt-tags/')
}

export async function createPromptTag(payload: PromptTagCreatePayload) {
  return request<PromptTagStats>('/prompt-tags/', {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}

export async function deletePromptTag(tagId: number) {
  await request<void>(`/prompt-tags/${tagId}`, {
    method: 'DELETE'
  })
}
