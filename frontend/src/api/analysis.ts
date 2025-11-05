import { request } from './http'
import type {
  AnalysisModuleDefinition,
  AnalysisModuleExecutionRequest,
  AnalysisResultPayload
} from '../types/analysis'

const BASE_PATH = '/analysis'

export function listAnalysisModules(): Promise<AnalysisModuleDefinition[]> {
  return request<AnalysisModuleDefinition[]>(`${BASE_PATH}/modules`)
}

export function executeAnalysisModule(
  payload: AnalysisModuleExecutionRequest
): Promise<AnalysisResultPayload> {
  return request<AnalysisResultPayload>(`${BASE_PATH}/modules/execute`, {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}
