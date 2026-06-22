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
