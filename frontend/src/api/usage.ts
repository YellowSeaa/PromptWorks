import { request } from './http'

export interface UsageOverviewResponse {
  total_tokens: number
  input_tokens: number
  output_tokens: number
  call_count: number
  total_cost: number
  cost_currency: string
}

export interface UsageModelSummaryResponse {
  model_key: string
  model_name: string
  provider: string
  total_tokens: number
  input_tokens: number
  output_tokens: number
  call_count: number
  total_cost: number
  cost_currency: string
}

export interface UsageTimeseriesPointResponse {
  date: string
  input_tokens: number
  output_tokens: number
  call_count: number
  total_cost: number
  cost_currency: string
}

export interface UsageQueryParams {
  start_date?: string
  end_date?: string
}

function buildQuery(params: UsageQueryParams = {}): string {
  const searchParams = new URLSearchParams()
  if (params.start_date) searchParams.set('start_date', params.start_date)
  if (params.end_date) searchParams.set('end_date', params.end_date)
  const query = searchParams.toString()
  return query ? `?${query}` : ''
}

export async function getUsageOverview(params: UsageQueryParams = {}) {
  const query = buildQuery(params)
  return request<UsageOverviewResponse | null>(`/usage/overview${query}`)
}

export async function listModelUsage(params: UsageQueryParams = {}) {
  const query = buildQuery(params)
  return request<UsageModelSummaryResponse[]>(`/usage/models${query}`)
}

export async function getModelTimeseries(
  modelKey: string,
  params: UsageQueryParams = {}
) {
  const query = buildQuery(params)
  return request<UsageTimeseriesPointResponse[]>(
    `/usage/models/${encodeURIComponent(modelKey)}/timeseries${query}`
  )
}
