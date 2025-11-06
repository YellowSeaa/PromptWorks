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

export interface AnalysisChartConfig {
  id: string
  title: string
  description?: string | null
  option: Record<string, unknown>
}

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
  extra?: { charts?: AnalysisChartConfig[] | null } & Record<string, unknown>
}

export interface AnalysisModuleExecutionRequest {
  module_id: string
  task_id: string
  target_type?: 'test_run' | 'prompt_test_task'
  parameters: Record<string, unknown>
}
