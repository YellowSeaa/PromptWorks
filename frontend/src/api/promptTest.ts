import { request } from './http'
import type {
  PromptTestTask,
  PromptTestTaskCreatePayload,
  PromptTestExperiment,
  PromptTestExperimentCreatePayload,
  PromptTestUnit,
  PromptTestAIScoringConfig,
  PromptTestAIScoreSummary,
  PromptTestOutputScore,
  PromptTestOptimizationRecommendation
} from '../types/promptTest'

const BASE_PATH = '/prompt-test'

export function createPromptTestTask(payload: PromptTestTaskCreatePayload): Promise<PromptTestTask> {
  return request<PromptTestTask>(`${BASE_PATH}/tasks`, {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}

export function listPromptTestTasks(): Promise<PromptTestTask[]> {
  return request<PromptTestTask[]>(`${BASE_PATH}/tasks`, {
    method: 'GET'
  })
}

export function getPromptTestTask(taskId: number): Promise<PromptTestTask> {
  return request<PromptTestTask>(`${BASE_PATH}/tasks/${taskId}`, {
    method: 'GET'
  })
}

export function deletePromptTestTask(taskId: number): Promise<void> {
  return request<void>(`${BASE_PATH}/tasks/${taskId}`, {
    method: 'DELETE'
  })
}

export function createPromptTestExperiment(
  unitId: number,
  payload: PromptTestExperimentCreatePayload
): Promise<PromptTestExperiment> {
  return request<PromptTestExperiment>(`${BASE_PATH}/units/${unitId}/experiments`, {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}

export function listPromptTestUnits(taskId: number): Promise<PromptTestUnit[]> {
  return request<PromptTestUnit[]>(`${BASE_PATH}/tasks/${taskId}/units`, {
    method: 'GET'
  })
}

export function getPromptTestUnit(unitId: number): Promise<PromptTestUnit> {
  return request<PromptTestUnit>(`${BASE_PATH}/units/${unitId}`, {
    method: 'GET'
  })
}

export function listPromptTestExperiments(unitId: number): Promise<PromptTestExperiment[]> {
  return request<PromptTestExperiment[]>(`${BASE_PATH}/units/${unitId}/experiments`, {
    method: 'GET'
  })
}

export function runPromptTestAIScoring(
  taskId: number,
  payload: PromptTestAIScoringConfig & { force?: boolean }
): Promise<PromptTestAIScoreSummary> {
  return request<PromptTestAIScoreSummary>(`${BASE_PATH}/tasks/${taskId}/ai-scoring`, {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}

export function getPromptTestAIScores(taskId: number): Promise<PromptTestAIScoreSummary> {
  return request<PromptTestAIScoreSummary>(`${BASE_PATH}/tasks/${taskId}/ai-scores`, {
    method: 'GET'
  })
}

export function retryPromptTestOutputScore(scoreId: number): Promise<PromptTestOutputScore> {
  return request<PromptTestOutputScore>(`${BASE_PATH}/output-scores/${scoreId}/retry`, {
    method: 'POST'
  })
}

export function createPromptTestOptimizationRecommendation(
  taskId: number,
  payload: Omit<PromptTestAIScoringConfig, 'enabled'>
): Promise<PromptTestOptimizationRecommendation> {
  return request<PromptTestOptimizationRecommendation>(
    `${BASE_PATH}/tasks/${taskId}/optimization-recommendations`,
    {
      method: 'POST',
      body: JSON.stringify(payload)
    }
  )
}

export function getLatestPromptTestOptimizationRecommendation(
  taskId: number
): Promise<PromptTestOptimizationRecommendation | null> {
  return request<PromptTestOptimizationRecommendation | null>(
    `${BASE_PATH}/tasks/${taskId}/optimization-recommendations/latest`,
    {
      method: 'GET'
    }
  )
}
