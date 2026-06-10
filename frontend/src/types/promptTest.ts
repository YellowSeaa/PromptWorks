export interface PromptTestTaskCreatePayload {
  name: string
  description?: string | null
  prompt_version_id?: number | null
  owner_id?: number | null
  config?: Record<string, unknown> | null
  units?: PromptTestUnitCreatePayload[]
  auto_execute?: boolean
}

export interface PromptTestAIScoringConfig {
  enabled: boolean
  evaluator_provider_id: number
  evaluator_model_id: number
  evaluator_model_name: string
  language: string
}

export interface PromptTestUnitCreatePayload {
  task_id?: number
  prompt_version_id?: number | null
  name: string
  description?: string | null
  model_name: string
  llm_provider_id?: number | null
  temperature?: number
  top_p?: number | null
  rounds?: number
  prompt_template?: string | null
  variables?: Record<string, unknown> | unknown[] | null
  parameters?: Record<string, unknown> | null
  expectations?: Record<string, unknown> | null
  tags?: string[] | null
  extra?: Record<string, unknown> | null
}

export interface PromptTestExperimentCreatePayload {
  unit_id?: number
  batch_id?: string | null
  sequence?: number | null
  auto_execute?: boolean
}

export interface PromptTestTask {
  id: number
  name: string
  description: string | null
  prompt_version_id: number | null
  owner_id: number | null
  config: Record<string, unknown> | null
  status: string
  created_at: string
  updated_at: string
  units?: PromptTestUnit[]
}

export interface PromptTestUnit {
  id: number
  task_id: number
  prompt_version_id: number | null
  name: string
  description: string | null
  model_name: string
  llm_provider_id: number | null
  temperature: number
  top_p: number | null
  rounds: number
  prompt_template: string | null
  variables: Record<string, unknown> | unknown[] | null
  parameters: Record<string, unknown> | null
  expectations: Record<string, unknown> | null
  tags: string[] | null
  extra: Record<string, unknown> | null
  created_at: string
  updated_at: string
}

export interface PromptTestExperiment {
  id: number
  unit_id: number
  batch_id: string | null
  sequence: number
  status: string
  outputs: Record<string, unknown>[] | null
  metrics: Record<string, unknown> | null
  error: string | null
  started_at: string | null
  finished_at: string | null
  created_at: string
  updated_at: string
}

export interface PromptTestOutputScore {
  id: number
  task_id: number
  unit_id: number
  experiment_id: number
  run_index: number
  status: 'pending' | 'running' | 'completed' | 'failed'
  evaluator_provider_id: number | null
  evaluator_model_id: number | null
  evaluator_model_name: string | null
  language: string
  overall_score: number | null
  dimension_scores: Record<string, unknown> | null
  reason: string | null
  retry_count: number
  error: string | null
  started_at: string | null
  finished_at: string | null
  created_at: string
  updated_at: string
}

export interface PromptTestAIScoreSummary {
  status: Record<string, unknown>
  scores: PromptTestOutputScore[]
  unit_summaries: Record<string, unknown>
}

export interface PromptTestOptimizationRecommendation {
  id: number
  task_id: number
  status: 'running' | 'completed' | 'failed'
  evaluator_provider_id: number | null
  evaluator_model_id: number | null
  evaluator_model_name: string | null
  language: string
  content: Record<string, unknown> | null
  error: string | null
  started_at: string | null
  finished_at: string | null
  created_at: string
  updated_at: string
}
