import { ref } from 'vue'

import {
  getTestingTimeouts,
  updateTestingTimeouts,
  type TestingTimeoutsResponse,
} from '../api/settings'

export const DEFAULT_TIMEOUT_SECONDS = 30
export const DEFAULT_AI_OPTIMIZATION_TIMEOUT_SECONDS = 180

const quickTestTimeout = ref<number | null>(null)
const testTaskTimeout = ref<number | null>(null)
const aiOptimizationTimeout = ref<number | null>(null)
const timeoutUpdatedAt = ref<string | null>(null)

let pendingPromise: Promise<void> | null = null

function applyTimeoutResponse(payload: TestingTimeoutsResponse) {
  quickTestTimeout.value = payload.quick_test_timeout
  testTaskTimeout.value = payload.test_task_timeout
  aiOptimizationTimeout.value = payload.ai_optimization_timeout
  timeoutUpdatedAt.value = payload.updated_at
}

export function useTestingSettings() {
  async function fetchTimeouts(force = false): Promise<void> {
    if (pendingPromise && !force) {
      return pendingPromise
    }
    pendingPromise = getTestingTimeouts()
      .then((data) => {
        applyTimeoutResponse(data)
      })
      .finally(() => {
        pendingPromise = null
      })
    return pendingPromise
  }

  async function saveTimeouts(payload: {
    quickTestTimeout: number
    testTaskTimeout: number
    aiOptimizationTimeout: number
  }): Promise<TestingTimeoutsResponse> {
    const updated = await updateTestingTimeouts({
      quick_test_timeout: payload.quickTestTimeout,
      test_task_timeout: payload.testTaskTimeout,
      ai_optimization_timeout: payload.aiOptimizationTimeout,
    })
    applyTimeoutResponse(updated)
    return updated
  }

  return {
    quickTestTimeout,
    testTaskTimeout,
    aiOptimizationTimeout,
    timeoutUpdatedAt,
    fetchTimeouts,
    saveTimeouts,
  }
}
