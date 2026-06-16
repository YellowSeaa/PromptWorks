import { request } from './http'
import type {
  KnownLLMProvider,
  LLMModel,
  LLMModelCreatePayload,
  LLMModelUpdatePayload,
  LLMProvider,
  LLMProviderCreatePayload,
  LLMProviderUpdatePayload,
  LLMInvokePayload
} from '../types/llm'

const BASE_PATH = '/llm-providers/'
const DEFAULT_INVOKE_TIMEOUT_MS = 15_000

export class RequestTimeoutError extends Error {
  constructor(message = '请求超时') {
    super(message)
    this.name = 'RequestTimeoutError'
  }
}

export function listCommonLLMProviders(): Promise<KnownLLMProvider[]> {
  return request<KnownLLMProvider[]>(`${BASE_PATH}common`, {
    method: 'GET'
  })
}

export function listLLMProviders(): Promise<LLMProvider[]> {
  return request<LLMProvider[]>(BASE_PATH, {
    method: 'GET'
  })
}

export function createLLMProvider(payload: LLMProviderCreatePayload): Promise<LLMProvider> {
  return request<LLMProvider>(BASE_PATH, {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}

export function updateLLMProvider(
  providerId: number,
  payload: LLMProviderUpdatePayload
): Promise<LLMProvider> {
  return request<LLMProvider>(`${BASE_PATH}${providerId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  })
}

export function createLLMModel(
  providerId: number,
  payload: LLMModelCreatePayload
): Promise<LLMModel> {
  return request<LLMModel>(`${BASE_PATH}${providerId}/models`, {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}

export function updateLLMModel(
  providerId: number,
  modelId: number,
  payload: LLMModelUpdatePayload
): Promise<LLMModel> {
  return request<LLMModel>(`${BASE_PATH}${providerId}/models/${modelId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  })
}

export function deleteLLMModel(providerId: number, modelId: number): Promise<void> {
  return request<void>(`${BASE_PATH}${providerId}/models/${modelId}`, {
    method: 'DELETE'
  })
}

export function deleteLLMProvider(providerId: number): Promise<void> {
  return request<void>(`${BASE_PATH}${providerId}`, {
    method: 'DELETE'
  })
}

export async function invokeLLMProvider(
  providerId: number,
  payload: LLMInvokePayload,
  timeoutMs = DEFAULT_INVOKE_TIMEOUT_MS
): Promise<unknown> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)

  try {
    return await request(`${BASE_PATH}${providerId}/invoke`, {
      method: 'POST',
      body: JSON.stringify(payload),
      signal: controller.signal
    })
  } catch (error: any) {
    if (error?.name === 'AbortError') {
      throw new RequestTimeoutError()
    }
    throw error
  } finally {
    clearTimeout(timer)
  }
}
