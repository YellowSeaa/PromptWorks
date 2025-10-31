import { request } from './http'

export interface TestingTimeoutsResponse {
  quick_test_timeout: number
  test_task_timeout: number
  updated_at: string | null
}

export interface TestingTimeoutsPayload {
  quick_test_timeout: number
  test_task_timeout: number
}

export function getTestingTimeouts(): Promise<TestingTimeoutsResponse> {
  return request<TestingTimeoutsResponse>('/settings/testing', {
    method: 'GET'
  })
}

export function updateTestingTimeouts(
  payload: TestingTimeoutsPayload
): Promise<TestingTimeoutsResponse> {
  return request<TestingTimeoutsResponse>('/settings/testing', {
    method: 'PUT',
    body: JSON.stringify(payload)
  })
}
