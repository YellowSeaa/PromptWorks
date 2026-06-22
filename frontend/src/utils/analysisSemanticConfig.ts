import type { LLMProvider } from '../types/llm'

export const SEMANTIC_ANALYSIS_MODULE_ID = 'semantic_consistency_diversity'

export type SemanticObjectiveValue = 'consistency' | 'diversity' | 'balanced'

export interface EmbeddingModelOption {
  value: string
  label: string
  providerId: number
  providerName: string
  modelId: number
  modelName: string
}

export interface SemanticAnalysisParameters {
  embedding_provider_id?: number
  embedding_model_id?: number
  objective_override?: SemanticObjectiveValue
  max_samples_per_group?: number
}

export interface SemanticObjectiveLabels {
  consistency: string
  diversity: string
  balanced: string
}

export function buildEmbeddingModelOptions(providers: LLMProvider[]): EmbeddingModelOption[] {
  return providers.flatMap((provider) =>
    provider.models
      .filter((model) => model.model_type === 'embedding')
      .map((model) => ({
        value: `${provider.id}:${model.id}`,
        label: `${provider.provider_name} / ${model.name}`,
        providerId: provider.id,
        providerName: provider.provider_name,
        modelId: model.id,
        modelName: model.name
      }))
  )
}

export function hasCallableChatModel(provider: LLMProvider): boolean {
  return provider.models.some((model) => model.model_type === 'chat')
}

export function normalizeAnalysisModuleCollapsed(value: unknown): boolean {
  return value === true
}

export function toggleAnalysisModuleCollapsed(state: { collapsed?: boolean }): boolean {
  state.collapsed = !normalizeAnalysisModuleCollapsed(state.collapsed)
  return state.collapsed
}

export function buildSemanticAnalysisParameters(
  modelKey: string,
  objective: SemanticObjectiveValue | null,
  maxSamplesPerGroup: number | null
): SemanticAnalysisParameters {
  const params: SemanticAnalysisParameters = {}
  const [providerRaw, modelRaw] = modelKey.split(':')
  const providerId = Number(providerRaw)
  const modelId = Number(modelRaw)
  if (Number.isInteger(providerId) && providerId > 0) {
    params.embedding_provider_id = providerId
  }
  if (Number.isInteger(modelId) && modelId > 0) {
    params.embedding_model_id = modelId
  }
  if (objective) {
    params.objective_override = objective
  }
  if (
    typeof maxSamplesPerGroup === 'number' &&
    Number.isFinite(maxSamplesPerGroup) &&
    maxSamplesPerGroup > 0
  ) {
    params.max_samples_per_group = maxSamplesPerGroup
  }
  return params
}

export function semanticModelKeyFromParameters(
  params: Record<string, unknown> | null | undefined
): string {
  const providerId = toPositiveInteger(params?.embedding_provider_id)
  const modelId = toPositiveInteger(params?.embedding_model_id)
  return providerId && modelId ? `${providerId}:${modelId}` : ''
}

export function toPositiveInteger(value: unknown): number | null {
  if (typeof value === 'number' && Number.isInteger(value) && value > 0) {
    return value
  }
  if (typeof value === 'string' && value.trim()) {
    const parsed = Number(value)
    if (Number.isInteger(parsed) && parsed > 0) {
      return parsed
    }
  }
  return null
}

export function formatSemanticObjective(
  value: unknown,
  labels: SemanticObjectiveLabels
): string {
  if (value === 'consistency') return labels.consistency
  if (value === 'diversity') return labels.diversity
  if (value === 'balanced') return labels.balanced
  return typeof value === 'string' && value.trim() ? value : '-'
}

export function formatSemanticMetricValue(value: unknown, locale: string): string {
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return '-'
  return numeric.toLocaleString(locale, {
    minimumFractionDigits: 0,
    maximumFractionDigits: 3
  })
}

export function buildAnalysisChartOption(
  chart: {
    id?: string | null
    title?: string | null
    type?: unknown
    x?: unknown
    y?: unknown
    option?: Record<string, unknown> | null
  },
  rows: Array<Record<string, unknown>>,
  formatValue: (value: unknown) => string
): Record<string, unknown> {
  if (chart.option && Object.keys(chart.option).length > 0) {
    return chart.option
  }
  const xKey = typeof chart.x === 'string' ? chart.x : ''
  const yKey = typeof chart.y === 'string' ? chart.y : ''
  if (!xKey || !yKey) {
    return {}
  }
  const categories = rows.map((row, index) => {
    const raw = row[xKey]
    if (raw === null || raw === undefined || raw === '') {
      return `#${index + 1}`
    }
    return String(raw)
  })
  const values = rows.map((row) => {
    const numeric = Number(row[yKey])
    return Number.isFinite(numeric) ? numeric : null
  })
  const chartType = chart.type === 'line' ? 'line' : 'bar'
  return {
    grid: { left: 40, right: 20, top: 24, bottom: 64 },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: chartType === 'bar' ? 'shadow' : 'line' },
      formatter: (params: unknown) => {
        const items = Array.isArray(params) ? params : [params]
        const first = items[0] as Record<string, unknown> | undefined
        const header = String(first?.axisValue ?? first?.name ?? '')
        const lines = items.map((item) => {
          const record = item as Record<string, unknown>
          const marker = typeof record.marker === 'string' ? record.marker : ''
          const seriesName = record.seriesName ? `${String(record.seriesName)}: ` : ''
          const value = Array.isArray(record.value) ? record.value[1] : record.value
          return `${marker}${seriesName}${formatValue(value)}`
        })
        return [header, ...lines].filter(Boolean).join('<br/>')
      }
    },
    xAxis: {
      type: 'category',
      data: categories,
      axisLabel: {
        interval: 0,
        rotate: categories.length > 4 ? 30 : 0,
        overflow: 'truncate',
        width: 120
      }
    },
    yAxis: {
      type: 'value',
      axisLabel: {
        formatter: (value: unknown) => formatValue(value)
      }
    },
    series: [
      {
        name: chart.title || yKey,
        type: chartType,
        data: values
      }
    ]
  }
}

export function normalizeSemanticAnalysisChart(
  chart: {
    id?: string | null
    title?: string | null
    type?: unknown
    x?: unknown
    y?: unknown
    description?: string | null
    option?: Record<string, unknown> | null
    meta?: unknown
  },
  index: number
): {
  id: string
  title: string
  type: string | null
  x: string | null
  y: string | null
  description: string
  option: Record<string, unknown>
  meta?: unknown
} {
  const id = chart.id || `chart-${index}`
  const inferredY =
    id === 'mean_pairwise_similarity' || id === 'semantic_dispersion' ? id : null
  return {
    id,
    title: chart.title ?? '',
    type: typeof chart.type === 'string' ? chart.type : inferredY ? 'bar' : null,
    x: typeof chart.x === 'string' ? chart.x : inferredY ? 'variable_case_label' : null,
    y: typeof chart.y === 'string' ? chart.y : inferredY,
    description: chart.description ?? '',
    option: JSON.parse(JSON.stringify(chart.option ?? {})),
    meta: chart.meta && typeof chart.meta === 'object'
      ? JSON.parse(JSON.stringify(chart.meta))
      : undefined
  }
}
