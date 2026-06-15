const DEFAULT_BASE_URL = '/api/v1'

function normalizeBaseUrl(url: string | undefined): string {
  if (!url) return DEFAULT_BASE_URL
  return url.endsWith('/') ? url.slice(0, -1) : url
}

export const API_BASE_URL = normalizeBaseUrl(import.meta.env.VITE_API_BASE_URL)

type HttpMethod = 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE'

export interface HttpError extends Error {
  status?: number
  payload?: unknown
}

async function parseJsonSafely(response: Response): Promise<unknown> {
  const text = await response.text()
  if (!text) return null
  try {
    return JSON.parse(text)
  } catch (error) {
    console.warn('解析接口返回 JSON 失败', error)
    return text
  }
}

export async function request<T>(
  path: string,
  options: RequestInit & { method?: HttpMethod } = {}
): Promise<T> {
  const url = `${API_BASE_URL}${path.startsWith('/') ? path : `/${path}`}`
  const merged: RequestInit = {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers ?? {})
    }
  }

  const response = await fetch(url, merged)

  if (!response.ok) {
    const error: HttpError = new Error('请求接口失败')
    error.status = response.status
    error.payload = await parseJsonSafely(response)
    throw error
  }

  if (response.status === 204) {
    return undefined as T
  }

  return (await parseJsonSafely(response)) as T
}
