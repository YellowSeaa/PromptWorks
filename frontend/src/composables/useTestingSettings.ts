import { ref } from 'vue'

import {
  getTestingTimeouts,
  updateTestingTimeouts,
  type TestingTimeoutsResponse,
} from '../api/settings'

export const DEFAULT_TIMEOUT_SECONDS = 30

const quickTestTimeout = ref<number | null>(null)
const testTaskTimeout = ref<number | null>(null)
const timeoutUpdatedAt = ref<string | null>(null)

let pendingPromise: Promise<void> | null = null

function applyTimeoutResponse(payload: TestingTimeoutsResponse) {
  quickTestTimeout.value = payload.quick_test_timeout
  testTaskTimeout.value = payload.test_task_timeout
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
  }): Promise<TestingTimeoutsResponse> {
    const updated = await updateTestingTimeouts({
      quick_test_timeout: payload.quickTestTimeout,
      test_task_timeout: payload.testTaskTimeout,
    })
    applyTimeoutResponse(updated)
    return updated
  }

  return {
    quickTestTimeout,
    testTaskTimeout,
    timeoutUpdatedAt,
    fetchTimeouts,
    saveTimeouts,
  }
}
