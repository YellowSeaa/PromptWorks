<template>
  <div class="page">
    <section class="page-header">
      <div class="page-header__text">
        <h2>{{ t('testJobManagement.headerTitle') }}</h2>
        <p class="page-desc">{{ t('testJobManagement.headerDescription') }}</p>
      </div>
      <div class="page-header__actions">
        <el-button type="primary" plain :icon="Memo" @click="handleCreateNewTask">
          {{ t('testJobManagement.createButtonNew') }}
        </el-button>
        <el-button
          v-if="showLegacyCreateButton"
          type="primary"
          :icon="Memo"
          @click="handleCreateTestJob"
        >
          {{ t('testJobManagement.createButton') }}
        </el-button>
      </div>
    </section>

    <el-card class="job-card">
      <template #header>
        <div class="card-header">
          <span>{{ t('testJobManagement.listTitle') }}</span>
        </div>
      </template>
      <div ref="tableWrapperRef" class="table-wrapper">
        <el-alert
          v-if="errorMessage"
          :title="errorMessage"
          type="error"
          show-icon
          class="table-alert"
        />
        <el-table
          class="job-table"
          :data="jobs"
          border
          stripe
          :height="tableHeight"
          :max-height="tableHeight"
          :empty-text="tableEmptyText"
          v-loading="isLoading"
        >
        <el-table-column :label="t('testJobManagement.table.columns.name')" min-width="260">
          <template #default="{ row }">
            <div class="table-name-cell">
              <span class="table-name__title">{{ row.jobName }}</span>
              <el-tag v-if="row.versionLabels.length > 1" size="small" type="info">
                {{ t('testJobManagement.versionCount', { count: row.versionLabels.length }) }}
              </el-tag>
            </div>
            <p class="table-subtitle">{{ t('testJobManagement.table.promptPrefix') }}{{ row.promptName }}</p>
            <p v-if="row.description" class="table-subtitle">
              {{ t('testJobManagement.table.notePrefix') }}{{ row.description }}
            </p>
            <p v-if="row.failureReason" class="table-failure">
              <el-icon class="table-failure__icon"><WarningFilled /></el-icon>
              <span class="table-failure__label">{{ t('testJobManagement.failureReasonPrefix') }}</span>
              <span class="table-failure__content">{{ row.failureReason }}</span>
            </p>
          </template>
        </el-table-column>
        <el-table-column :label="t('testJobManagement.table.columns.model')" min-width="180">
          <template #default="{ row }">
            <div class="table-model">
              <span>{{ row.modelName }}</span>
              <span v-if="row.providerName" class="table-subtext">{{ row.providerName }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column :label="t('testJobManagement.table.columns.versions')" min-width="220">
          <template #default="{ row }">
            <el-space wrap>
              <el-tag
                v-for="label in row.versionLabels"
                :key="label"
                size="small"
                type="info"
              >
                {{ label }}
              </el-tag>
            </el-space>
          </template>
        </el-table-column>
        <el-table-column :label="t('testJobManagement.table.columns.temperature')" width="100">
          <template #default="{ row }">{{ formatTemperature(row.temperature) }}</template>
        </el-table-column>
        <el-table-column :label="t('testJobManagement.table.columns.repetitions')" width="100">
          <template #default="{ row }">{{ row.repetitions }}</template>
        </el-table-column>
        <el-table-column :label="t('testJobManagement.table.columns.status')" width="180">
          <template #default="{ row }">
            <div class="status-cell">
              <el-tag :type="statusTagType[row.status] ?? 'info'" size="small">
                {{ statusLabel[row.status] ?? row.status }}
              </el-tag>
              <div
                v-if="(row.status === 'running' || row.status === 'pending') && row.progressPercent !== null"
                class="status-progress"
              >
                <el-progress
                  :show-text="false"
                  :stroke-width="6"
                  :percentage="row.progressPercent ?? 0"
                />
                <span class="status-progress__text">
                  {{ row.progressCurrent ?? '--' }} / {{ row.progressTotal ?? '--' }}
                </span>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column :label="t('testJobManagement.table.columns.createdAt')" min-width="160">
          <template #default="{ row }">{{ formatDateTime(row.createdAt) }}</template>
        </el-table-column>
        <el-table-column :label="t('testJobManagement.table.columns.updatedAt')" min-width="160">
          <template #default="{ row }">{{ formatDateTime(row.updatedAt) }}</template>
        </el-table-column>
        <el-table-column :label="t('testJobManagement.table.columns.actions')" width="210" fixed="right">
          <template #default="{ row }">
            <el-space :size="4">
              <el-button type="primary" link size="small" @click="handleViewJob(row)">
                {{ t('testJobManagement.table.viewDetails') }}
              </el-button>
              <el-button
                v-if="row.failedRunIds.length"
                type="danger"
                link
                size="small"
                :loading="isJobRetrying(row.id)"
                @click="handleRetry(row)"
              >
                {{ t('testJobManagement.table.retry') }}
              </el-button>
              <el-button
                type="danger"
                link
                size="small"
                :loading="isJobDeleting(row.id)"
                @click="handleDelete(row)"
              >
                {{ t('testJobManagement.table.delete') }}
              </el-button>
            </el-space>
          </template>
        </el-table-column>
      </el-table>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { Memo, WarningFilled } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { deleteTestRun, listTestRuns, retryTestRun } from '../api/testRun'
import {
  deletePromptTestTask,
  listPromptTestExperiments,
  listPromptTestTasks
} from '../api/promptTest'
import type { TestRun } from '../types/testRun'
import type { PromptTestTask, PromptTestUnit, PromptTestExperiment } from '../types/promptTest'
import { useI18n } from 'vue-i18n'

interface AggregatedJobRow {
  id: string
  batchId: string | null
  jobName: string
  promptName: string
  versionLabels: string[]
  modelName: string
  providerName: string | null
  temperature: number
  repetitions: number
  status: string
  createdAt: string
  updatedAt: string
  description: string | null
  failureReason: string | null
  runIds: number[]
  failedRunIds: number[]
  mode: string
  isNewResultPage: boolean
  newResultTaskId: number | null
  progressCurrent: number | null
  progressTotal: number | null
  progressPercent: number | null
}

interface ProgressMetrics {
  current: number | null
  total: number | null
  percent: number | null
}

const router = useRouter()
const { t, locale } = useI18n()
const retryingJobIds = ref<string[]>([])
const deletingJobIds = ref<string[]>([])
const showLegacyCreateButton = false

const testRuns = ref<TestRun[]>([])
const promptTestTasks = ref<PromptTestTask[]>([])
const isLoading = ref(false)
const errorMessage = ref<string | null>(null)
const pollingTimer = ref<number | null>(null)
const tableWrapperRef = ref<HTMLElement | null>(null)
const tableHeight = ref(520)

const TABLE_BOTTOM_PADDING = 24
const TABLE_MIN_HEIGHT = 240
const promptTaskProgress = ref<Record<number, ProgressMetrics>>({})

function clearPolling() {
  if (pollingTimer.value !== null) {
    window.clearTimeout(pollingTimer.value)
    pollingTimer.value = null
  }
}

function scheduleNextPoll() {
  clearPolling()
  const hasLegacyInProgress = testRuns.value.some(
    (run) => run.status === 'pending' || run.status === 'running'
  )
  const hasPromptTaskInProgress = promptTestTasks.value.some((task) => {
    const status = mapPromptTestTaskStatus(task.status)
    return status === 'pending' || status === 'running'
  })
  if (hasLegacyInProgress || hasPromptTaskInProgress) {
    pollingTimer.value = window.setTimeout(() => {
      void fetchAllJobs(false)
    }, 3000)
  }
}

const tableEmptyText = computed(() => errorMessage.value ?? t('testJobManagement.empty'))

function updateTableHeight() {
  const wrapper = tableWrapperRef.value
  if (!wrapper) {
    tableHeight.value = Math.max(TABLE_MIN_HEIGHT, tableHeight.value)
    return
  }
  const rect = wrapper.getBoundingClientRect()
  const available =
    window.innerHeight - rect.top - TABLE_BOTTOM_PADDING
  const usable = Number.isFinite(available) ? Math.floor(available) : TABLE_MIN_HEIGHT
  tableHeight.value = Math.max(TABLE_MIN_HEIGHT, usable)
}

function handleWindowResize() {
  updateTableHeight()
}

function safeNumber(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value
  }
  if (typeof value === 'string') {
    const trimmed = value.trim()
    if (!trimmed) {
      return null
    }
    const parsed = Number(trimmed)
    if (Number.isFinite(parsed)) {
      return parsed
    }
  }
  return null
}

function resolveVariableCaseCount(variables: unknown): number {
  if (Array.isArray(variables)) {
    return variables.length || 1
  }
  if (variables && typeof variables === 'object') {
    const record = variables as Record<string, unknown>
    const rows = record.rows
    if (Array.isArray(rows)) {
      return rows.length || 1
    }
    const lengthValue = safeNumber(record.length)
    if (lengthValue && lengthValue > 0) {
      return Math.floor(lengthValue)
    }
  }
  return 1
}

function estimatePromptTaskTotalRuns(units: PromptTestUnit[]): number | null {
  let total = 0
  for (const unit of units) {
    const baseRounds = safeNumber(unit.rounds) ?? 1
    const caseCount = resolveVariableCaseCount(unit.variables)
    total += Math.max(1, Math.floor(baseRounds)) * Math.max(1, caseCount)
  }
  return total > 0 ? total : null
}

function normalizeProgressMetrics(
  current: number | null | undefined,
  total: number | null | undefined
): ProgressMetrics {
  const totalValue =
    typeof total === 'number' && Number.isFinite(total) ? Math.floor(total) : null
  if (totalValue === null || totalValue <= 0) {
    return { current: null, total: null, percent: null }
  }

  const currentValue =
    typeof current === 'number' && Number.isFinite(current) ? Math.floor(current) : 0
  const clampedCurrent = Math.max(0, Math.min(totalValue, currentValue))
  const percent = Math.max(
    0,
    Math.min(100, Math.round((clampedCurrent / Math.max(totalValue, 1)) * 100))
  )

  return {
    current: clampedCurrent,
    total: totalValue,
    percent
  }
}

function extractProgressFromConfig(
  configRecord: Record<string, unknown>,
  fallbackTotal: number | null
): ProgressMetrics | null {
  const directProgress = configRecord.progress
  const directRecord =
    directProgress && typeof directProgress === 'object' && !Array.isArray(directProgress)
      ? (directProgress as Record<string, unknown>)
      : null

  const currentCandidates = [
    configRecord.progressCurrent,
    configRecord.progress_current,
    configRecord.completedUnits,
    configRecord.completed_units,
    configRecord.completedCount,
    configRecord.completed_count,
    directRecord?.current,
    directRecord?.completed,
    directRecord?.done
  ]

  const totalCandidates = [
    configRecord.progressTotal,
    configRecord.progress_total,
    configRecord.totalUnits,
    configRecord.total_units,
    configRecord.expectedCount,
    configRecord.expected_count,
    directRecord?.total,
    directRecord?.expected,
    fallbackTotal
  ]

  const currentValue = currentCandidates
    .map((value) => safeNumber(value))
    .find((value): value is number => typeof value === 'number')
  const totalValue = totalCandidates
    .map((value) => safeNumber(value))
    .find((value): value is number => typeof value === 'number')

  if (totalValue === undefined || totalValue === null || totalValue <= 0) {
    return null
  }

  return normalizeProgressMetrics(currentValue ?? 0, totalValue)
}

function pickProgressMetrics(
  primary: ProgressMetrics | null | undefined,
  secondary: ProgressMetrics | null | undefined
): ProgressMetrics | null {
  if (primary && primary.total !== null) {
    return primary
  }
  if (secondary && secondary.total !== null) {
    return secondary
  }
  return null
}

function calculateLegacyProgress(runs: TestRun[]): ProgressMetrics | null {
  let total = 0
  let completed = 0
  for (const run of runs) {
    const repetitions = safeNumber(run.repetitions) ?? 0
    const resultsCount = Array.isArray(run.results) ? run.results.length : 0
    total += repetitions
    completed += Math.min(resultsCount, repetitions || resultsCount)
  }
  if (total <= 0) {
    return null
  }
  return normalizeProgressMetrics(completed, total)
}

function resolveFailureReason(run: TestRun): string | null {
  const direct = typeof run.failure_reason === 'string' ? run.failure_reason.trim() : ''
  if (direct) {
    return direct
  }
  const schema = (run.schema ?? {}) as Record<string, unknown>
  const fallback = schema['last_error']
  if (typeof fallback === 'string') {
    const trimmed = fallback.trim()
    if (trimmed) {
      return trimmed
    }
  }
  return null
}

function isJobRetrying(id: string): boolean {
  return retryingJobIds.value.includes(id)
}

function markJobRetrying(id: string) {
  if (isJobRetrying(id)) return
  retryingJobIds.value = [...retryingJobIds.value, id]
}

function unmarkJobRetrying(id: string) {
  if (!isJobRetrying(id)) return
  retryingJobIds.value = retryingJobIds.value.filter((item) => item !== id)
}

function isJobDeleting(id: string): boolean {
  return deletingJobIds.value.includes(id)
}

function markJobDeleting(id: string) {
  if (isJobDeleting(id)) return
  deletingJobIds.value = [...deletingJobIds.value, id]
}

function unmarkJobDeleting(id: string) {
  if (!isJobDeleting(id)) return
  deletingJobIds.value = deletingJobIds.value.filter((item) => item !== id)
}

const jobs = computed<AggregatedJobRow[]>(() => {
  const legacyRows = buildLegacyJobRows(testRuns.value)
  const promptTaskRows = buildPromptTestTaskRows(promptTestTasks.value)
  const merged = [...legacyRows, ...promptTaskRows]
  return merged.sort((a, b) => b.createdAt.localeCompare(a.createdAt))
})

watch([jobs, isLoading], () => {
  nextTick(() => {
    updateTableHeight()
  })
}, { immediate: true })

function buildLegacyJobRows(runs: TestRun[]): AggregatedJobRow[] {
  const groups = new Map<string, TestRun[]>()
  for (const run of runs) {
    const key = run.batch_id ?? `run-${run.id}`
    const group = groups.get(key)
    if (group) {
      group.push(run)
    } else {
      groups.set(key, [run])
    }
  }

  const aggregateStatus = (items: TestRun[]): string => {
    if (items.some((item) => item.status === 'failed')) return 'failed'
    if (items.some((item) => item.status === 'running')) return 'running'
    if (items.some((item) => item.status === 'pending')) return 'pending'
    return 'completed'
  }

  return Array.from(groups.entries()).map(([key, items]) => {
    const ordered = [...items].sort((a, b) => a.created_at.localeCompare(b.created_at))
    const primary = ordered[0]
    const schema = (primary.schema ?? {}) as Record<string, unknown>
    const promptName = primary.prompt?.name ?? t('testJobManagement.unnamedPrompt')
    const jobNameCandidate = typeof schema.job_name === 'string' ? schema.job_name.trim() : ''
    const jobName = jobNameCandidate || primary.notes || promptName
    const versionLabels = ordered.map((run) => {
      const data = (run.schema ?? {}) as Record<string, unknown>
      const label = typeof data.version_label === 'string' ? data.version_label : null
      return (
        label ??
        run.prompt_version?.version ??
        t('testJobManagement.versionFallback', { id: run.prompt_version_id })
      )
    })
    const repetitions = Math.max(...ordered.map((run) => run.repetitions ?? 1))
    const createdAt = ordered.reduce(
      (acc, run) => (run.created_at < acc ? run.created_at : acc),
      ordered[0].created_at
    )
    const updatedAt = ordered.reduce(
      (acc, run) => (run.updated_at > acc ? run.updated_at : acc),
      ordered[0].updated_at
    )
    const mode =
      typeof schema.mode === 'string' ? String(schema.mode) : 'same-model-different-version'
    const failedRuns = ordered.filter((run) => run.status === 'failed')
    const failedRunIds = failedRuns.map((run) => run.id)
    const failureReasons = failedRuns
      .map((run) => resolveFailureReason(run))
      .filter((value): value is string => Boolean(value))
    const mergedReason = failureReasons.length
      ? Array.from(new Set(failureReasons)).join('；')
      : null
    let newResultTaskId: number | null = null
    const rawTaskId = schema.prompt_test_task_id
    if (typeof rawTaskId === 'number') {
      newResultTaskId = rawTaskId
    } else if (typeof rawTaskId === 'string' && rawTaskId.trim()) {
      const parsed = Number(rawTaskId)
      if (!Number.isNaN(parsed)) {
        newResultTaskId = parsed
      }
    }
    const isNewResultPage =
      typeof schema.new_result_page === 'boolean'
        ? schema.new_result_page
        : Boolean(newResultTaskId)

    const progress = calculateLegacyProgress(ordered)

    return {
      id: key,
      batchId: primary.batch_id ?? null,
      jobName,
      promptName,
      versionLabels,
      modelName: primary.model_name,
      providerName: primary.model_version ?? null,
      temperature: primary.temperature,
      repetitions,
      status: aggregateStatus(ordered),
      createdAt,
      updatedAt,
      description: primary.notes,
      failureReason: mergedReason,
      runIds: ordered.map((run) => run.id),
      failedRunIds,
      mode,
      isNewResultPage,
      newResultTaskId,
      progressCurrent: progress?.current ?? null,
      progressTotal: progress?.total ?? null,
      progressPercent: progress?.percent ?? null
    }
  })
}

function buildPromptTestTaskRows(tasks: PromptTestTask[]): AggregatedJobRow[] {
  return tasks.map((task) => {
    const units = Array.isArray(task.units) ? task.units : []
    const unitExtras = units.map((unit) => extractRecord(unit.extra))
    const configRecord = extractRecord(task.config)
    const jobName = task.name?.trim() || t('testJobManagement.unnamedPrompt')
    const promptNames = deduplicateStrings(
      unitExtras
        .map((extra) => extractString(extra.prompt_name))
        .filter((value): value is string => Boolean(value))
    )
    const configPromptName = extractString(configRecord.prompt_name)
    const promptName =
      promptNames[0] ?? configPromptName ?? t('testJobManagement.unnamedPrompt')

    const versionLabels = deduplicateStrings(
      units
        .map((unit, index) => formatVersionLabel(unit, unitExtras[index]))
        .filter((label): label is string => Boolean(label))
    )
    if (!versionLabels.length) {
      versionLabels.push(
        t('testJobManagement.versionFallback', {
          id: task.prompt_version_id ?? '-'
        })
      )
    }

    const modelNames = deduplicateStrings(
      units.map((unit) => unit.model_name)
    )
    const providerNames = deduplicateStrings(
      unitExtras
        .map((extra) => extractString(extra.llm_provider_name))
        .filter((value): value is string => Boolean(value))
    )

    const temperatureValues = units
      .map((unit) => unit.temperature)
      .filter((value): value is number => typeof value === 'number' && !Number.isNaN(value))
    const roundsValues = units
      .map((unit) => unit.rounds)
      .filter((value): value is number => typeof value === 'number' && !Number.isNaN(value))

    const failureDetail = extractString(configRecord.last_error)
    const status = mapPromptTestTaskStatus(task.status)
    const fallbackTotal = estimatePromptTaskTotalRuns(units)
    const configProgress = extractProgressFromConfig(configRecord, fallbackTotal)
    const runtimeProgress = promptTaskProgress.value[task.id] ?? null
    const progressCandidate = pickProgressMetrics(runtimeProgress, configProgress)
    const progress =
      progressCandidate ??
      (typeof fallbackTotal === 'number' ? normalizeProgressMetrics(0, fallbackTotal) : null)

    return {
      id: `task-${task.id}`,
      batchId: null,
      jobName,
      promptName,
      versionLabels,
      modelName: modelNames.length ? modelNames.join(' / ') : '--',
      providerName: providerNames.length ? providerNames.join(' / ') : null,
      temperature: temperatureValues.length ? temperatureValues[0] : Number.NaN,
      repetitions: roundsValues.length ? Math.max(...roundsValues) : 1,
      status,
      createdAt: task.created_at,
      updatedAt: task.updated_at,
      description: task.description ?? null,
      failureReason: status === 'failed' ? failureDetail : null,
      runIds: [],
      failedRunIds: [],
      mode: 'prompt-test-task',
      isNewResultPage: true,
      newResultTaskId: task.id,
      progressCurrent: progress?.current ?? null,
      progressTotal: progress?.total ?? null,
      progressPercent: progress?.percent ?? null
    }
  })
}

async function refreshPromptTaskProgress(tasks: PromptTestTask[]): Promise<void> {
  if (!tasks.length) {
    promptTaskProgress.value = {}
    await nextTick(() => updateTableHeight())
    return
  }

  try {
    const progressEntries = await Promise.all(
      tasks.map(async (task) => {
        const units = Array.isArray(task.units) ? task.units : []
        const fallbackTotal = estimatePromptTaskTotalRuns(units)
        const configRecord = extractRecord(task.config)
        const configProgress = extractProgressFromConfig(configRecord, fallbackTotal)

        if (!units.length) {
          const status = mapPromptTestTaskStatus(task.status)
          const metrics =
            status === 'completed'
              ? normalizeProgressMetrics(1, 1)
              : normalizeProgressMetrics(0, 1)
          return [task.id, metrics] as const
        }

        if (configProgress) {
          return [task.id, configProgress] as const
        }

        const computed = await computeProgressFromExperiments(units, fallbackTotal)
        const status = mapPromptTestTaskStatus(task.status)
        const totalBaseline = fallbackTotal ?? units.length
        const fallbackProgress =
          status === 'completed'
            ? normalizeProgressMetrics(totalBaseline ?? 1, totalBaseline ?? 1)
            : normalizeProgressMetrics(0, totalBaseline ?? 1)

        return [task.id, computed ?? fallbackProgress] as const
      })
    )

    const progressMap: Record<number, ProgressMetrics> = {}
    for (const entry of progressEntries) {
      if (!entry) continue
      const [taskId, metrics] = entry
      progressMap[taskId] = metrics
    }
    promptTaskProgress.value = progressMap
  } catch (error) {
    console.error('加载测试任务进度失败', error)
  } finally {
    await nextTick(() => updateTableHeight())
  }
}

async function computeProgressFromExperiments(
  units: PromptTestUnit[],
  fallbackTotal: number | null
): Promise<ProgressMetrics | null> {
  if (!units.length) {
    return null
  }

  const experimentsList = await Promise.all(
    units.map((unit) =>
      listPromptTestExperiments(unit.id).catch(() => [] as PromptTestExperiment[])
    )
  )

  let totalRuns = 0
  let completedRuns = 0

  units.forEach((unit, index) => {
    const expectedRuns =
      Math.max(1, Math.floor(safeNumber(unit.rounds) ?? 1)) *
      Math.max(1, resolveVariableCaseCount(unit.variables))
    totalRuns += expectedRuns
    const experiments = experimentsList[index]
    if (!experiments.length) {
      return
    }

    let remaining = expectedRuns
    const ordered = [...experiments].sort((a, b) => a.sequence - b.sequence)
    for (const experiment of ordered) {
      if (remaining <= 0) {
        break
      }
      if (experiment.status === 'completed') {
        const outputsLength = Array.isArray(experiment.outputs)
          ? experiment.outputs.length
          : expectedRuns
        const credited = Math.min(remaining, outputsLength || expectedRuns)
        completedRuns += credited
        remaining -= credited
      } else if (experiment.status === 'running') {
        const outputsLength = Array.isArray(experiment.outputs)
          ? experiment.outputs.length
          : 0
        const credited = Math.min(remaining, outputsLength)
        completedRuns += credited
        remaining -= credited
      } else if (
        experiment.status === 'failed' ||
        experiment.status === 'cancelled'
      ) {
        completedRuns += remaining
        remaining = 0
      }
    }
  })

  const total = totalRuns || fallbackTotal || units.length
  if (!total) {
    return null
  }
  return normalizeProgressMetrics(completedRuns, total)
}

function deduplicateStrings(values: Array<string | null | undefined>): string[] {
  return Array.from(
    new Set(
      values
        .map((value) => (typeof value === 'string' ? value.trim() : ''))
        .filter((value) => value.length > 0)
    )
  )
}

function extractString(value: unknown): string | null {
  if (typeof value === 'string') {
    const trimmed = value.trim()
    return trimmed || null
  }
  return null
}

function extractRecord(value: unknown): Record<string, unknown> {
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    return value as Record<string, unknown>
  }
  return {}
}

function mapPromptTestTaskStatus(status: string): 'pending' | 'running' | 'completed' | 'failed' {
  const normalized = typeof status === 'string' ? status.toLowerCase() : ''
  if (normalized === 'running') return 'running'
  if (normalized === 'completed') return 'completed'
  if (normalized === 'failed') return 'failed'
  return 'pending'
}

function formatVersionLabel(
  unit: PromptTestUnit,
  extraRecord?: Record<string, unknown>
): string | null {
  const extra = extraRecord ?? extractRecord(unit.extra)
  const label = extractString(extra.prompt_version)
  if (label) {
    return label
  }
  if (typeof unit.prompt_version_id === 'number') {
    return t('testJobManagement.versionFallback', { id: unit.prompt_version_id })
  }
  return null
}

const statusTagType = {
  completed: 'success',
  running: 'warning',
  failed: 'danger',
  pending: 'warning'
} as const

const statusLabel = computed<Record<string, string>>(() => ({
  completed: t('testJobManagement.status.completed'),
  running: t('testJobManagement.status.running'),
  failed: t('testJobManagement.status.failed'),
  pending: t('testJobManagement.status.pending')
}))

const dateTimeFormatter = computed(
  () =>
    new Intl.DateTimeFormat(locale.value === 'zh-CN' ? 'zh-CN' : 'en-US', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    })
)

function formatDateTime(value: string) {
  if (!value) return '--'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }
  return dateTimeFormatter.value.format(date)
}

function formatTemperature(value: number | null | undefined) {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return '--'
  }
  return value.toFixed(2)
}

function extractErrorMessage(error: unknown, fallback: string): string {
  if (error && typeof error === 'object' && 'payload' in error) {
    const payload = (error as { payload?: unknown }).payload
    if (payload && typeof payload === 'object' && 'detail' in payload) {
      const detail = (payload as Record<string, unknown>).detail
      if (typeof detail === 'string' && detail.trim()) {
        return detail
      }
    }
  }
  if (error instanceof Error && error.message) {
    return error.message
  }
  return fallback
}

async function fetchAllJobs(withLoading = true) {
  if (withLoading) {
    isLoading.value = true
  }
  errorMessage.value = null
  try {
    const [runs, tasks] = await Promise.all([
      listTestRuns({ limit: 200 }),
      listPromptTestTasks()
    ])
    testRuns.value = runs
    promptTestTasks.value = tasks
    void refreshPromptTaskProgress(tasks)
  } catch (error) {
    errorMessage.value = extractErrorMessage(error, t('testJobManagement.messages.loadFailed'))
    testRuns.value = []
    promptTestTasks.value = []
    promptTaskProgress.value = {}
  } finally {
    isLoading.value = false
    if (!errorMessage.value) {
      scheduleNextPoll()
    } else {
      clearPolling()
    }
  }
}

onMounted(() => {
  window.addEventListener('resize', handleWindowResize)
  nextTick(() => {
    updateTableHeight()
  })
  void fetchAllJobs()
})

onUnmounted(() => {
  clearPolling()
  window.removeEventListener('resize', handleWindowResize)
})

function handleCreateTestJob() {
  router.push({ name: 'test-job-create' })
}

function handleCreateNewTask() {
  router.push({ name: 'prompt-test-task-create' })
}

function handleViewJob(job: AggregatedJobRow) {
  if (job.isNewResultPage) {
    const targetId = job.newResultTaskId ?? job.id
    router.push({
      name: 'prompt-test-task-result',
      params: { taskId: targetId }
    })
    return
  }
  if (!job.runIds.length) {
    return
  }
  const [firstId, ...rest] = job.runIds
  const query: Record<string, string> = {}
  if (rest.length) {
    query.runIds = rest.join(',')
  }
  query.mode = job.mode
  router.push({ name: 'test-job-result', params: { id: firstId }, query })
}

async function handleRetry(job: AggregatedJobRow) {
  if (!job.failedRunIds.length) {
    ElMessage.info(t('testJobManagement.messages.noFailedRuns'))
    return
  }
  if (isJobRetrying(job.id)) {
    return
  }
  markJobRetrying(job.id)
  try {
    await Promise.all(job.failedRunIds.map((runId) => retryTestRun(runId)))
    ElMessage.success(t('testJobManagement.messages.retrySuccess'))
    await fetchAllJobs(false)
  } catch (error) {
    ElMessage.error(
      extractErrorMessage(error, t('testJobManagement.messages.retryFailed'))
    )
  } finally {
    unmarkJobRetrying(job.id)
  }
}

async function handleDelete(job: AggregatedJobRow) {
  try {
    await ElMessageBox.confirm(
      t('testJobManagement.messages.deleteConfirmMessage', { name: job.jobName }),
      t('testJobManagement.messages.deleteConfirmTitle'),
      {
        confirmButtonText: t('common.confirm'),
        cancelButtonText: t('common.cancel'),
        type: 'warning'
      }
    )
  } catch {
    return
  }

  if (isJobDeleting(job.id)) {
    return
  }

  markJobDeleting(job.id)
  try {
    if (job.mode === 'prompt-test-task' && job.newResultTaskId) {
      await deletePromptTestTask(job.newResultTaskId)
    } else if (job.runIds.length) {
      await Promise.all(job.runIds.map((runId) => deleteTestRun(runId)))
    } else {
      ElMessage.warning(t('testJobManagement.messages.deleteUnavailable'))
      return
    }
    ElMessage.success(t('testJobManagement.messages.deleteSuccess'))
    await fetchAllJobs(false)
  } catch (error) {
    ElMessage.error(
      extractErrorMessage(error, t('testJobManagement.messages.deleteFailed'))
    )
  } finally {
    unmarkJobDeleting(job.id)
  }
}
</script>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.page-header__text {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.page-header__actions {
  display: flex;
  gap: 8px;
}

.page-header__text h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
}

.page-desc {
  margin: 0;
  color: var(--text-weak-color);
  font-size: 14px;
}

.card-header {
  font-size: 14px;
  font-weight: 600;
}

.job-card {
  display: flex;
  flex-direction: column;
}

.job-card :deep(.el-card__body) {
  display: flex;
  flex-direction: column;
  flex: 1;
}

.table-wrapper {
  display: flex;
  flex-direction: column;
  gap: 12px;
  height: 100%;
}

.table-alert {
  margin-bottom: 0;
}

.job-table {
  flex: 1;
}

.table-name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.table-name__title {
  font-weight: 600;
}

.table-subtitle {
  margin: 2px 0 0;
  font-size: 12px;
  color: var(--text-weak-color);
}

.table-model {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.table-subtext {
  font-size: 12px;
  color: var(--text-weak-color);
}

.table-failure {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--el-color-danger);
  display: flex;
  align-items: flex-start;
  gap: 4px;
  line-height: 1.4;
  white-space: normal;
}

.table-failure__icon {
  margin-top: 2px;
}

.table-failure__label {
  font-weight: 600;
}

.table-failure__content {
  word-break: break-word;
  flex: 1;
}

.status-cell {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
}

.status-progress {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  max-width: 220px;
}

.status-progress :deep(.el-progress) {
  flex: 1;
}

.status-progress__text {
  font-size: 12px;
  color: var(--text-weak-color);
  white-space: nowrap;
}
</style>
