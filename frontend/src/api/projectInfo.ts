import { request } from './http'

export interface ProjectMetadataResponse {
  name: string
  description: string
  github_url: string
  contact_email: string
  tutorial_available: boolean
}

export interface ProjectStatisticsResponse {
  provider_count: number
  model_count: number
  prompt_count: number
  prompt_version_count: number
  test_task_count: number
  test_unit_count: number
  test_experiment_count: number
}

export interface ProjectUpdateGuidanceResponse {
  deployment_type: string
  title: string
  steps: string[]
}

export interface ProjectVersionInfoResponse {
  current: string
  latest: string | null
  has_update: boolean
  release_url: string | null
  deployment_type: string
  update_guidance: ProjectUpdateGuidanceResponse
}

export interface ProjectInfoSummaryResponse {
  project: ProjectMetadataResponse
  version: ProjectVersionInfoResponse
  statistics: ProjectStatisticsResponse
}

export function getProjectInfoSummary(): Promise<ProjectInfoSummaryResponse> {
  return request<ProjectInfoSummaryResponse>('/project-info/summary')
}

export function checkProjectVersion(): Promise<ProjectVersionInfoResponse> {
  return request<ProjectVersionInfoResponse>('/project-info/version/check')
}
