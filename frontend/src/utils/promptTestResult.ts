import type {
  PromptTestAIScoreSummary,
  PromptTestExperiment,
  PromptTestOutputScore,
  PromptTestUnit
} from '../types/promptTest'

export interface PromptTestResultOutput {
  runIndex: number
  content: string
  meta: string
  variables: Record<string, string>
  rawResponse: string | null
  errorMessage: string | null
  score: PromptTestOutputScore | null
}

export interface PromptTestResultUnit {
  id: number
  name: string
  promptVersionId: number | null
  promptVersion: string
  modelName: string
  temperature: number | null
  temperatureMode: 'llm_default' | 'explicit'
  parameterSet: string
  parameters: Record<string, string>
  rounds: number
  status: PromptTestExperiment['status'] | null
  error: string | null
  metrics: PromptTestExperiment['metrics'] | null
  averageScore: number | null
  scoreCount: number
  scoreTotal: number
  outputs: PromptTestResultOutput[]
}

export function buildPromptTestResultUnit(
  unit: PromptTestUnit,
  experiments: PromptTestExperiment[]
): PromptTestResultUnit {
  const extra = extractRecord(unit.extra)
  const parameterLabel = resolveParameterLabel(extra)
  const promptVersionLabel = resolvePromptVersionLabel(extra, unit.prompt_version_id)
  const latestExperiment = extractLatestExperiment(experiments)
  return {
    id: unit.id,
    name: unit.name,
    promptVersionId: unit.prompt_version_id,
    promptVersion: promptVersionLabel,
    modelName: unit.model_name,
    temperature: unit.temperature,
    temperatureMode: resolveTemperatureMode(unit),
    parameterSet: parameterLabel,
    parameters: normalizeRecord({
      ...extractRecord(unit.parameters),
      temperature:
        typeof unit.temperature === 'number' && Number.isFinite(unit.temperature)
          ? unit.temperature
          : null,
      temperature_mode: resolveTemperatureMode(unit)
    }),
    rounds: unit.rounds,
    status: latestExperiment?.status ?? null,
    error: normalizeError(latestExperiment?.error),
    metrics: latestExperiment?.metrics ?? null,
    averageScore: null,
    scoreCount: 0,
    scoreTotal: 0,
    outputs: buildOutputs(latestExperiment)
  }
}

function resolveTemperatureMode(
  unit: PromptTestUnit
): 'llm_default' | 'explicit' {
  if (typeof unit.temperature === 'number' && Number.isFinite(unit.temperature)) {
    return 'explicit'
  }
  return 'llm_default'
}

export function attachScoresToResultUnits(
  sourceUnits: PromptTestResultUnit[],
  summary: PromptTestAIScoreSummary | null
): PromptTestResultUnit[] {
  const scoreMap = new Map<string, PromptTestOutputScore>()
  ;(summary?.scores ?? []).forEach((score) => {
    scoreMap.set(`${score.unit_id}:${score.run_index}`, score)
  })
  return sourceUnits.map((unit) => {
    const unitSummary = extractRecord(summary?.unit_summaries?.[String(unit.id)])
    return {
      ...unit,
      averageScore: safeNumber(unitSummary.avg_score),
      scoreCount: safeNumber(unitSummary.count) ?? 0,
      scoreTotal: countUnitScores(summary, unit.id),
      outputs: unit.outputs.map((output) => ({
        ...output,
        score: scoreMap.get(`${unit.id}:${output.runIndex}`) ?? null
      }))
    }
  })
}

export function formatScoreValue(value: unknown, locale: string): string {
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return '-'
  return numeric.toLocaleString(locale, {
    minimumFractionDigits: 0,
    maximumFractionDigits: 1
  })
}

export function dimensionEntries(
  score: PromptTestOutputScore | null | undefined,
  locale: string
): Array<[string, string]> {
  const dimensions = score?.dimension_scores
  if (!dimensions || typeof dimensions !== 'object') return []
  return Object.entries(dimensions).map(([key, value]) => [
    key,
    formatScoreValue(value, locale)
  ])
}

export function extractLatestExperiment(
  experiments: PromptTestExperiment[]
): PromptTestExperiment | null {
  if (!Array.isArray(experiments) || !experiments.length) {
    return null
  }
  return experiments.reduce<PromptTestExperiment | null>((latest, current) => {
    if (!latest) return current
    if (current.sequence > latest.sequence) return current
    if (current.sequence === latest.sequence) {
      const latestCreated = safeTime(latest.created_at)
      const currentCreated = safeTime(current.created_at)
      return currentCreated > latestCreated ? current : latest
    }
    return latest
  }, null)
}

export function normalizeRecord(value: unknown): Record<string, string> {
  const source = extractRecord(value)
  const entries: Array<[string, string]> = Object.entries(source).map(([key, val]) => [
    key,
    formatDisplayValue(val)
  ])
  return Object.fromEntries(entries)
}

export function buildParameterEntries(
  parameters: Record<string, string>
): Array<[string, string]> {
  return Object.entries(parameters)
}

export function formatDisplayValue(value: unknown): string {
  if (value === null || value === undefined) {
    return ''
  }
  if (typeof value === 'string') {
    return value
  }
  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value)
  }
  try {
    return JSON.stringify(value)
  } catch {
    return String(value)
  }
}

function buildOutputs(experiment: PromptTestExperiment | null): PromptTestResultOutput[] {
  if (!experiment) {
    return []
  }
  const outputs = Array.isArray(experiment.outputs) ? experiment.outputs : []
  return outputs.map((item, index) => {
    const record = extractRecord(item)
    const runIndex =
      typeof record.run_index === 'number'
        ? record.run_index
        : typeof record.sequence === 'number'
          ? record.sequence
          : index + 1
    const contentSource =
      typeof record.output_text === 'string'
        ? record.output_text
        : record.parsed_output ?? record.output ?? ''
    const content = formatDisplayValue(contentSource)
    const meta = formatOutputMeta(record)
    const parameterRecord = extractRecord(record.parameters)
    const directVariables = extractRecord(record.variables)
    const nestedParameterVariables =
      'variables' in parameterRecord ? extractRecord(parameterRecord.variables) : {}
    const contextVariables = extractRecord(record.context)
    const variablesSource =
      Object.keys(directVariables).length > 0
        ? directVariables
        : Object.keys(nestedParameterVariables).length > 0
          ? nestedParameterVariables
          : Object.keys(contextVariables).length > 0
            ? contextVariables
            : parameterRecord
    const variables = normalizeRecord(variablesSource)
    const rawResponseSource = record.raw_response ?? record.rawResponse ?? null
    let rawResponse: string | null = null
    if (typeof rawResponseSource === 'string' && rawResponseSource.trim()) {
      rawResponse = rawResponseSource
    } else if (rawResponseSource && typeof rawResponseSource === 'object') {
      try {
        rawResponse = JSON.stringify(rawResponseSource, null, 2)
      } catch {
        rawResponse = String(rawResponseSource)
      }
    }
    let errorMessage: string | null = null
    if (typeof record.error === 'string') {
      const trimmed = record.error.trim()
      if (trimmed.length) {
        errorMessage = trimmed
      }
    } else if (record.error !== undefined && record.error !== null) {
      const formatted = formatDisplayValue(record.error)
      if (formatted.trim().length) {
        errorMessage = formatted.trim()
      }
    }

    return {
      runIndex,
      content,
      meta,
      variables,
      rawResponse,
      errorMessage,
      score: null
    }
  })
}

function countUnitScores(summary: PromptTestAIScoreSummary | null, unitId: number): number {
  return (summary?.scores ?? []).filter((score) => score.unit_id === unitId).length
}

function formatOutputMeta(record: Record<string, unknown>): string {
  const parts: string[] = []
  const latency = safeNumber(record.latency_ms)
  if (latency !== null) {
    parts.push(`耗时 ${latency}ms`)
  }
  const totalTokens =
    safeNumber(record.total_tokens) ??
    (safeNumber(record.prompt_tokens) ?? 0) + (safeNumber(record.completion_tokens) ?? 0)
  if (!Number.isNaN(totalTokens) && totalTokens > 0) {
    parts.push(`总 Tokens ${totalTokens}`)
  }
  return parts.join(' · ')
}

function resolveParameterLabel(extra: Record<string, unknown>): string {
  const label = extra.parameter_label
  if (typeof label === 'string' && label.trim()) {
    return label.trim()
  }
  const index = safeNumber(extra.parameter_index)
  if (index !== null) {
    return `参数集 ${index}`
  }
  return '默认参数集'
}

function resolvePromptVersionLabel(
  extra: Record<string, unknown>,
  promptVersionId: number | null
): string {
  const label = extra.prompt_version
  if (typeof label === 'string' && label.trim()) {
    return label.trim()
  }
  if (typeof promptVersionId === 'number') {
    return `版本 #${promptVersionId}`
  }
  return '-'
}

function extractRecord(value: unknown): Record<string, unknown> {
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    return value as Record<string, unknown>
  }
  return {}
}

function safeTime(value: unknown): number {
  if (typeof value === 'string' || value instanceof Date) {
    const time = new Date(value).getTime()
    return Number.isNaN(time) ? 0 : time
  }
  return 0
}

function safeNumber(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value
  }
  if (typeof value === 'string' && value.trim()) {
    const parsed = Number(value)
    return Number.isFinite(parsed) ? parsed : null
  }
  return null
}

function normalizeError(value: unknown): string | null {
  if (typeof value === 'string') {
    const trimmed = value.trim()
    return trimmed.length ? trimmed : null
  }
  return null
}

export type MissingOutputReason =
  | 'partial'
  | 'failed'
  | 'cancelled'
  | 'running'
  | 'pending'
  | 'completed'
  | 'unknown'

export interface MissingOutputContext {
  reason: MissingOutputReason
  produced: number
  status: PromptTestExperiment['status'] | null
  error: string | null
}

export function detectMissingOutput(
  unit: PromptTestResultUnit | null,
  rowIndex: number
): MissingOutputContext | null {
  if (!unit) {
    return null
  }
  const produced = unit.outputs.length
  if (produced >= rowIndex) {
    return null
  }
  if (produced > 0) {
    return {
      reason: 'partial',
      produced,
      status: unit.status ?? null,
      error: unit.error ?? null
    }
  }
  const status = unit.status ?? null
  let reason: MissingOutputReason = 'unknown'
  if (status === 'failed') {
    reason = 'failed'
  } else if (status === 'cancelled') {
    reason = 'cancelled'
  } else if (status === 'running') {
    reason = 'running'
  } else if (status === 'pending') {
    reason = 'pending'
  } else if (status === 'completed') {
    reason = 'completed'
  }
  return {
    reason,
    produced,
    status,
    error: unit.error ?? null
  }
}
