export type AnalysisParameterType = 'text' | 'number' | 'select' | 'regex'

export interface AnalysisParameterSpec {
  key: string
  label: string
  type: AnalysisParameterType
  required: boolean
  default: unknown
  options?: unknown[] | null
  help_text?: string | null
  regex_pattern?: string | null
}

export interface AnalysisColumnMeta {
  name: string
  label: string
  description?: string | null
  visualizable: string[]
  extra?: Record<string, unknown> | null
}

export interface AnalysisChartMeta {
  unit_labels?: string[]
  unit_ids?: Array<number | string>
  unit_names?: string[]
}

export interface AnalysisChartConfig {
  id: string
  title: string
  description?: string | null
  option: Record<string, unknown>
  meta?: AnalysisChartMeta
}

export type SemanticAnalysisObjective = 'consistency' | 'diversity' | 'balanced' | string

export type SemanticAnalysisGroupStatus = 'ok' | 'insufficient_samples' | string

export interface SemanticAnalysisGroupSummary {
  unit_id?: number | string | null
  unit_name?: string | null
  variable_case_hash?: string | null
  semantic_objective?: SemanticAnalysisObjective | null
  sample_count?: number | null
  mean_pairwise_similarity?: number | null
  min_pairwise_similarity?: number | null
  centroid_similarity_mean?: number | null
  semantic_dispersion?: number | null
  outlier_count?: number | null
  outlier_output_ids?: string[] | null
  status?: SemanticAnalysisGroupStatus | null
  interpretation_level?: string | null
  interpretation?: string | null
}

export interface SemanticAnalysisSummary {
  group_count?: number | null
  group_summaries?: SemanticAnalysisGroupSummary[] | null
}

export interface AnalysisUnitLink {
  unit_id: number | string | null
  unit_name: string
  label: string
}

export interface AnalysisInsightUnitRef {
  unit_id: number | string | null
  unit_name: string
  label: string
  value: number | null
  unit: string
}

export type AnalysisInsightDetail =
  | {
      type: 'latency_comparison'
      fast: AnalysisInsightUnitRef
      slow: AnalysisInsightUnitRef
    }
  | {
      type: 'tokens_peak'
      unit: AnalysisInsightUnitRef
    }
  | {
      type: 'throughput_peak'
      unit: AnalysisInsightUnitRef
    }
  | Record<string, unknown>

export interface AnalysisModuleDefinition {
  module_id: string
  name: string
  description?: string | null
  parameters: AnalysisParameterSpec[]
  required_columns: string[]
  tags: string[]
  protocol_version: string
  allow_llm: boolean
}

export interface AnalysisResultPayload {
  module_id: string
  data: Array<Record<string, unknown>>
  columns_meta: AnalysisColumnMeta[]
  insights: string[]
  llm_usage?: Record<string, unknown> | null
  protocol_version: string
  extra?: {
    charts?: AnalysisChartConfig[] | null
    unit_links?: AnalysisUnitLink[] | null
    insight_details?: AnalysisInsightDetail[] | null
    semantic_summary?: SemanticAnalysisSummary | null
  } & Record<string, unknown>
}

export interface AnalysisModuleExecutionRequest {
  module_id: string
  task_id: string
  target_type?: 'test_run' | 'prompt_test_task'
  parameters: Record<string, unknown>
}
