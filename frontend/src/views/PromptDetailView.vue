<template>
  <div class="detail-page">
    <el-breadcrumb separator="/" class="detail-breadcrumb">
      <el-breadcrumb-item>
        <span class="breadcrumb-link" @click="goHome">{{ t('menu.prompt') }}</span>
      </el-breadcrumb-item>
      <el-breadcrumb-item>{{ detail?.name ?? t('promptDetail.breadcrumb.fallback') }}</el-breadcrumb-item>
    </el-breadcrumb>

    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      show-icon
    />

    <el-skeleton v-else-if="isLoading" animated :rows="6" />

    <el-empty v-else-if="!detail" :description="t('promptDetail.empty')" />

    <template v-else>
      <el-card class="info-card">
      <template #header>
        <div class="info-header">
          <div class="info-title-group">
            <p class="info-class">{{ t('promptDetail.info.classLabel', { name: detail.prompt_class.name }) }}</p>
            <h2 class="info-title">{{ detail.name }}</h2>
            <p class="info-desc">{{ detail.description ?? t('promptDetail.info.descriptionFallback') }}</p>
          </div>
          <div class="info-meta">
            <el-tag type="success" effect="light">
              {{
                detail.current_version?.version
                  ? t('promptDetail.info.currentVersion', { version: detail.current_version.version })
                  : t('promptDetail.info.currentVersionFallback')
              }}
            </el-tag>
            <span>{{ t('promptDetail.info.updatedAt', { time: formatDateTime(detail.updated_at) }) }}</span>
          </div>
        </div>
      </template>
      <el-descriptions :column="3" border size="small" class="info-descriptions">
        <el-descriptions-item :label="t('promptDetail.info.fields.author')">
          {{ detail.author ?? t('common.notSet') }}
        </el-descriptions-item>
        <el-descriptions-item :label="t('promptDetail.info.fields.createdAt')">
          {{ formatDateTime(detail.created_at) }}
        </el-descriptions-item>
        <el-descriptions-item :label="t('promptDetail.info.fields.updatedAt')">
          {{ formatDateTime(detail.updated_at) }}
        </el-descriptions-item>
        <el-descriptions-item :label="t('promptDetail.info.fields.classDescription')" :span="3">
          {{ detail.prompt_class.description ?? t('promptDetail.info.fields.classDescriptionFallback') }}
        </el-descriptions-item>
      </el-descriptions>
      <div class="info-tags">
        <div class="info-tags__list">
          <el-tag
            v-for="tag in detail.tags"
            :key="tag.id"
            size="small"
            effect="dark"
            :style="{ backgroundColor: tag.color, borderColor: tag.color }"
          >
            {{ tag.name }}
          </el-tag>
        </div>
        <el-button type="primary" link size="small" @click="openMetaDialog">
          {{ t('promptDetail.info.editButton') }}
        </el-button>
      </div>
      <el-dialog v-model="metaDialogVisible" :title="t('promptDetail.info.dialogTitle')" width="520px">
        <el-alert
          v-if="metaError"
          :title="metaError"
          type="warning"
          show-icon
          class="meta-alert"
        />
        <el-form label-width="80px" class="meta-form">
          <el-form-item :label="t('promptDetail.info.dialog.classLabel')">
            <el-select
              v-model="selectedClassId"
              :placeholder="t('promptDetail.info.dialog.classPlaceholder')"
              :loading="isMetaLoading"
              :disabled="isMetaLoading || !classOptions.length"
            >
              <el-option
                v-for="option in classOptions"
                :key="option.id"
                :label="option.name"
                :value="option.id"
              />
            </el-select>
            <span v-if="!classOptions.length && !isMetaLoading" class="meta-empty-tip">
              {{ t('promptDetail.info.dialog.noClassTip') }}
            </span>
          </el-form-item>
          <el-form-item :label="t('promptDetail.info.dialog.tagsLabel')">
            <el-select
              v-model="selectedTagIds"
              multiple
              collapse-tags
              collapse-tags-tooltip
              :placeholder="t('promptDetail.info.dialog.tagsPlaceholder')"
              :loading="isMetaLoading"
            >
              <el-option
                v-for="tag in tagOptions"
                :key="tag.id"
                :label="tag.name"
                :value="tag.id"
              >
                <span class="tag-option">
                  <span class="tag-dot" :style="{ backgroundColor: tag.color }" />
                  {{ tag.name }}
                </span>
              </el-option>
            </el-select>
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="closeMetaDialog" :disabled="isMetaSaving">{{ t('common.cancel') }}</el-button>
          <el-button type="primary" :loading="isMetaSaving" :disabled="!canSaveMeta" @click="handleSaveMeta">
            {{ t('common.save') }}
          </el-button>
        </template>
      </el-dialog>
      </el-card>

      <el-card class="content-card">
      <template #header>
        <div class="content-header">
          <div>
            <h3 class="content-title">{{ t('promptDetail.content.title') }}</h3>
            <span class="content-subtitle">{{ t('promptDetail.content.subtitle') }}</span>
          </div>
          <div class="content-actions">
            <el-button size="small" @click="handleCreateVersion">{{ t('promptDetail.content.newVersion') }}</el-button>
            <el-button size="small" type="primary" @click="handleViewVersionCompare">{{ t('promptDetail.content.compare') }}</el-button>
          </div>
        </div>
      </template>
      <div class="content-body">
        <section class="content-main">
          <header class="content-main__meta">
            <div>
              <span class="content-main__label">{{ t('promptDetail.content.versionLabel') }}</span>
              <strong class="content-main__value">
                {{ selectedVersion?.version ?? t('promptDetail.content.versionFallback') }}
              </strong>
            </div>
            <div class="content-main__time">
              <span class="content-main__label">{{ t('promptDetail.content.updatedLabel') }}</span>
              <strong class="content-main__value">{{ formatDateTime(selectedVersion?.updated_at ?? selectedVersion?.created_at) }}</strong>
              <el-tooltip :content="t('promptDetail.content.copyTooltip')" placement="top">
                <el-button
                  class="content-copy-button"
                  :icon="DocumentCopy"
                  circle
                  size="small"
                  type="primary"
                  text
                  :disabled="!selectedVersion?.content"
                  @click.stop="handleCopyPrompt"
                />
              </el-tooltip>
            </div>
          </header>
          <div class="content-scroll">
            <template v-if="selectedVersion">
              <pre class="content-text">{{ selectedVersion.content }}</pre>
            </template>
            <el-empty v-else :description="t('promptDetail.content.empty')" />
          </div>
        </section>
        <aside class="content-history">
          <h4 class="history-title">{{ t('promptDetail.content.historyTitle') }}</h4>
          <div class="history-scroll">
            <div
              v-for="version in detail.versions"
              :key="version.id"
              :class="['history-item', { 'is-active': version.id === selectedVersionId }]"
              @click="handleSelectVersion(version.id)"
            >
              <div class="history-item__meta">
                <span class="history-version">{{ version.version }}</span>
                <span class="history-date">{{ formatDateTime(version.updated_at) }}</span>
              </div>
              <p class="history-preview">{{ summarizeContent(version.content) }}</p>
            </div>
          </div>
        </aside>
      </div>
      </el-card>

      <el-card class="test-card">
      <template #header>
        <div class="test-header">
          <div>
            <h3 class="test-title">{{ t('promptDetail.test.title') }}</h3>
            <span class="test-subtitle">{{ t('promptDetail.test.subtitle') }}</span>
          </div>
          <el-button type="primary" size="small" @click="handleCreateTest">{{ t('promptDetail.test.newTest') }}</el-button>
        </div>
      </template>
      <el-alert
        v-if="testRunError"
        :title="testRunError"
        type="error"
        show-icon
        class="test-alert"
      />
      <el-skeleton v-else-if="testRunLoading && !testRecords.length" animated :rows="3" />
      <el-table
        v-else-if="testRecords.length"
        :data="testRecords"
        size="small"
        border
        v-loading="testRunLoading"
      >
        <el-table-column :label="t('promptDetail.test.columns.version')" min-width="180">
          <template #default="{ row }">
            <div class="test-record-name">
              <span>{{ row.versionLabel }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column :label="t('promptDetail.test.columns.model')" min-width="140">
          <template #default="{ row }">{{ row.modelLabel }}</template>
        </el-table-column>
        <el-table-column :label="t('promptDetail.test.columns.temperature')" width="100">
          <template #default="{ row }">{{ formatTemperature(row.temperature) }}</template>
        </el-table-column>
        <el-table-column :label="t('promptDetail.test.columns.repetitions')" width="120">
          <template #default="{ row }">{{ row.repetitions }}</template>
        </el-table-column>
        <el-table-column :label="t('promptDetail.test.columns.status')" width="120">
          <template #default="{ row }">
            <el-tag :type="statusTagType[row.statusKey] ?? 'info'" size="small">
              {{ row.statusDisplay }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="t('promptDetail.test.columns.createdAt')" min-width="160">
          <template #default="{ row }">
            {{ row.createdAtDisplay }}
          </template>
        </el-table-column>
        <el-table-column :label="t('promptDetail.test.columns.actions')" width="120">
          <template #default="{ row }">
            <template v-if="row.canNavigate">
              <el-button type="primary" link size="small" @click="handleViewTestRecord(row)">
                {{ t('promptDetail.test.viewResult') }}
              </el-button>
            </template>
            <span v-else class="test-record-empty-action">--</span>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-else :description="t('promptDetail.test.empty')" />
      </el-card>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { DocumentCopy } from '@element-plus/icons-vue'
import { usePromptDetail } from '../composables/usePromptDetail'
import { listPromptClasses, type PromptClassStats } from '../api/promptClass'
import { listPromptTags, type PromptTagStats } from '../api/promptTag'
import { updatePrompt } from '../api/prompt'
import { listTestRuns } from '../api/testRun'
import { listPromptTestTasks } from '../api/promptTest'
import type { TestRun } from '../types/testRun'
import type { PromptTestTask } from '../types/promptTest'
import { ElMessage } from 'element-plus'
import { useI18n } from 'vue-i18n'

const router = useRouter()
const route = useRoute()
const { t, locale } = useI18n()
const currentId = computed(() => {
  const raw = Number(route.params.id)
  return Number.isFinite(raw) && raw > 0 ? raw : null
})

const {
  prompt: detail,
  loading: isLoading,
  error: errorMessage,
  refresh: refreshDetail
} = usePromptDetail(currentId)

const selectedVersionId = ref<number | null>(null)
const promptClasses = ref<PromptClassStats[]>([])
const promptTags = ref<PromptTagStats[]>([])
const metaError = ref<string | null>(null)
const isMetaLoading = ref(false)
const isMetaSaving = ref(false)
const selectedClassId = ref<number | null>(null)
const selectedTagIds = ref<number[]>([])
const metaDialogVisible = ref(false)

const classOptions = computed(() =>
  promptClasses.value
    .map((item) => ({ id: item.id, name: item.name }))
    .sort((a, b) => a.name.localeCompare(b.name, locale.value))
)

const tagOptions = computed(() =>
  promptTags.value
    .map((tag) => ({ id: tag.id, name: tag.name, color: tag.color }))
    .sort((a, b) => a.name.localeCompare(b.name, locale.value))
)

watch(
  () => detail.value,
  (value) => {
    if (!value) {
      selectedVersionId.value = null
      selectedClassId.value = null
      selectedTagIds.value = []
      return
    }
    selectedVersionId.value = value.current_version?.id ?? value.versions[0]?.id ?? null
    selectedClassId.value = value.prompt_class.id
    selectedTagIds.value = value.tags.map((tag) => tag.id)
  },
  { immediate: true }
)

const selectedVersion = computed(() => {
  const prompt = detail.value
  if (!prompt) {
    return null
  }
  const match = prompt.versions.find((item) => item.id === selectedVersionId.value)
  return match ?? prompt.current_version ?? null
})

type TestRecordType = 'legacy' | 'task'
type TestRecordStatus = 'completed' | 'failed' | 'running' | 'pending'

interface TestRecordRow {
  key: string
  type: TestRecordType
  versionLabel: string
  modelLabel: string
  temperature: number | null
  repetitions: number
  statusKey: TestRecordStatus
  statusDisplay: string
  createdAtDisplay: string
  createdAtSortValue: number
  canNavigate: boolean
  runId?: number
  taskId?: number
  disabledReason?: string | null
}

const testRuns = ref<TestRun[]>([])
const promptTestTasks = ref<PromptTestTask[]>([])
const testRunLoading = ref(false)
const testRunError = ref<string | null>(null)

const testRecords = computed<TestRecordRow[]>(() => {
  const promptId = currentId.value
  if (!promptId) return []

  const records: TestRecordRow[] = []
  const promptDetail = detail.value
  const versionLabelMap = new Map<number, string>()

  if (promptDetail) {
    promptDetail.versions.forEach((version) => {
      versionLabelMap.set(version.id, version.version)
    })
  }

  const versionIdSet = new Set<number>()
  versionLabelMap.forEach((_, id) => {
    versionIdSet.add(id)
  })

  testRuns.value.forEach((run) => {
    if (!isRunRelatedToPrompt(run, promptId, versionIdSet)) {
      return
    }
    records.push(buildLegacyTestRecord(run, versionLabelMap))
  })

  promptTestTasks.value.forEach((task) => {
    if (!isTaskRelatedToPrompt(task, promptId, versionIdSet)) {
      return
    }
    records.push(buildPromptTestTaskRecord(task, versionLabelMap))
  })

  return records.sort((a, b) => b.createdAtSortValue - a.createdAtSortValue)
})

watch(
  currentId,
  () => {
    void fetchTestRecords()
  },
  { immediate: true }
)

watch(classOptions, (options) => {
  if (!options.length) {
    selectedClassId.value = null
    return
  }
  if (selectedClassId.value === null) {
    selectedClassId.value = options[0].id
    return
  }
  const exists = options.some((item) => item.id === selectedClassId.value)
  if (!exists) {
    selectedClassId.value = options[0].id
  }
})

watch(tagOptions, (options) => {
  if (!options.length) {
    selectedTagIds.value = []
    return
  }
  const available = new Set(options.map((item) => item.id))
  selectedTagIds.value = selectedTagIds.value.filter((id) => available.has(id))
})

onMounted(() => {
  void fetchMeta()
})

const statusTagType = {
  completed: 'success',
  failed: 'danger',
  running: 'warning',
  pending: 'info'
} as const

const statusLabel = computed<Record<string, string>>(() => ({
  completed: t('promptDetail.status.completed'),
  failed: t('promptDetail.status.failed'),
  running: t('promptDetail.status.running'),
  pending: t('promptDetail.status.pending')
}))

function mapPromptTestTaskStatus(status: string): 'pending' | 'running' | 'completed' | 'failed' {
  const normalized = typeof status === 'string' ? status.toLowerCase() : ''
  if (normalized === 'running') return 'running'
  if (normalized === 'completed') return 'completed'
  if (normalized === 'failed') return 'failed'
  return 'pending'
}

function normalizeLegacyStatus(status: string | null | undefined): TestRecordStatus {
  const normalized = typeof status === 'string' ? status.toLowerCase() : ''
  if (normalized === 'completed') return 'completed'
  if (normalized === 'failed') return 'failed'
  if (normalized === 'running') return 'running'
  return 'pending'
}

function safeDateValue(value: string): number {
  const time = new Date(value).getTime()
  if (Number.isNaN(time)) {
    return 0
  }
  return time
}

const canSaveMeta = computed(() => {
  const prompt = detail.value
  if (!prompt) {
    return false
  }
  if (selectedClassId.value === null) {
    return false
  }
  const originalClassId = prompt.prompt_class.id
  const originalTags = prompt.tags.map((tag) => tag.id).sort((a, b) => a - b)
  const currentTags = [...selectedTagIds.value].sort((a, b) => a - b)
  const tagsChanged =
    originalTags.length !== currentTags.length ||
    originalTags.some((value, index) => value !== currentTags[index])
  return selectedClassId.value !== originalClassId || tagsChanged
})

function extractMetaError(error: unknown): string {
  if (error && typeof error === 'object' && 'payload' in error) {
    const httpError = error as { status?: number; payload?: unknown }
    const payload = httpError.payload
    if (payload && typeof payload === 'object' && 'detail' in payload) {
      const detail = (payload as Record<string, unknown>).detail
      if (typeof detail === 'string' && detail.trim()) {
        return detail
      }
    }
    if (httpError.status === 404) {
      return t('promptDetail.messages.metaNotFound')
    }
  }
  if (error instanceof Error && error.message) {
    return error.message
  }
  return t('promptDetail.messages.metaLoadFailed')
}

async function fetchMeta() {
  isMetaLoading.value = true
  metaError.value = null
  try {
    const [classes, tagResponse] = await Promise.all([
      listPromptClasses(),
      listPromptTags()
    ])
    promptClasses.value = classes
    promptTags.value = tagResponse.items
  } catch (error) {
    metaError.value = extractMetaError(error)
  } finally {
    isMetaLoading.value = false
  }
}

async function fetchTestRecords() {
  if (!currentId.value) {
    testRuns.value = []
    promptTestTasks.value = []
    testRunError.value = null
    return
  }
  testRunLoading.value = true
  testRunError.value = null
  try {
    const [runs, tasks] = await Promise.all([
      listTestRuns({ limit: 200 }),
      listPromptTestTasks()
    ])
    testRuns.value = runs
    promptTestTasks.value = tasks
  } catch (error) {
    testRunError.value = extractTestRunError(error)
    testRuns.value = []
    promptTestTasks.value = []
  } finally {
    testRunLoading.value = false
  }
}

function isRunRelatedToPrompt(
  run: TestRun,
  promptId: number,
  versionIdSet: Set<number>
): boolean {
  if (run.prompt?.id === promptId) {
    return true
  }
  if (run.prompt_version?.prompt_id === promptId) {
    return true
  }
  if (typeof run.prompt_version_id === 'number' && versionIdSet.has(run.prompt_version_id)) {
    return true
  }
  return false
}

function buildLegacyTestRecord(
  run: TestRun,
  versionLabelMap: Map<number, string>
): TestRecordRow {
  const versionLabel =
    run.prompt_version?.version ??
    (typeof run.prompt_version_id === 'number'
      ? versionLabelMap.get(run.prompt_version_id) ??
        t('promptDetail.table.versionFallback', { id: run.prompt_version_id })
      : t('promptDetail.content.versionFallback'))

  const modelLabel = run.model_name?.trim() || '--'
  const temperature =
    typeof run.temperature === 'number' && !Number.isNaN(run.temperature)
      ? run.temperature
      : null
  const repetitions =
    typeof run.repetitions === 'number' && !Number.isNaN(run.repetitions)
      ? run.repetitions
      : 1
  const statusKey = normalizeLegacyStatus(run.status)
  const createdAtSource = run.created_at ?? run.updated_at ?? ''
  const createdAtSortValue = createdAtSource ? safeDateValue(createdAtSource) : 0
  const createdAtDisplay = createdAtSource ? formatDateTime(createdAtSource) : '--'

  return {
    key: `legacy-${run.id}`,
    type: 'legacy',
    versionLabel,
    modelLabel,
    temperature,
    repetitions,
    statusKey,
    statusDisplay: statusLabel.value[statusKey] ?? statusKey,
    createdAtDisplay,
    createdAtSortValue,
    canNavigate: typeof run.id === 'number' && run.id > 0,
    runId: run.id
  }
}

function extractRecord(value: unknown): Record<string, unknown> {
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    return value as Record<string, unknown>
  }
  return {}
}

function extractString(value: unknown): string | null {
  if (typeof value === 'string') {
    const trimmed = value.trim()
    return trimmed ? trimmed : null
  }
  return null
}

function extractPromptIdsFromConfig(
  config: Record<string, unknown> | null | undefined
): number[] {
  if (!config) {
    return []
  }
  const record = extractRecord(config)
  const result: number[] = []
  const single = record['prompt_id']
  if (typeof single === 'number' && Number.isFinite(single)) {
    result.push(single)
  } else if (typeof single === 'string') {
    const parsed = Number(single)
    if (Number.isFinite(parsed)) {
      result.push(parsed)
    }
  }
  const multiple = record['prompt_ids']
  if (Array.isArray(multiple)) {
    multiple.forEach((item) => {
      const parsed =
        typeof item === 'number'
          ? item
          : typeof item === 'string'
          ? Number(item)
          : Number.NaN
      if (Number.isFinite(parsed)) {
        result.push(parsed)
      }
    })
  }
  return Array.from(new Set(result))
}

function isTaskRelatedToPrompt(
  task: PromptTestTask,
  promptId: number,
  versionIdSet: Set<number>
): boolean {
  const configIds = extractPromptIdsFromConfig(task.config)
  if (configIds.includes(promptId)) {
    return true
  }
  const units = Array.isArray(task.units) ? task.units : []
  if (!units.length) {
    return false
  }
  if (versionIdSet.size > 0) {
    const match = units.some(
      (unit) =>
        typeof unit.prompt_version_id === 'number' && versionIdSet.has(unit.prompt_version_id)
    )
    if (match) {
      return true
    }
  }
  if (typeof task.prompt_version_id === 'number' && versionIdSet.has(task.prompt_version_id)) {
    return true
  }
  return false
}

function buildPromptTestTaskRecord(
  task: PromptTestTask,
  versionLabelMap: Map<number, string>
): TestRecordRow {
  const units = Array.isArray(task.units) ? task.units : []
  const versionLabels = new Set<string>()
  const modelNames = new Set<string>()
  const temperatureValues: number[] = []
  const roundsValues: number[] = []

  units.forEach((unit) => {
    if (typeof unit.model_name === 'string' && unit.model_name.trim()) {
      modelNames.add(unit.model_name.trim())
    }
    if (typeof unit.temperature === 'number' && !Number.isNaN(unit.temperature)) {
      temperatureValues.push(unit.temperature)
    }
    if (typeof unit.rounds === 'number' && !Number.isNaN(unit.rounds)) {
      roundsValues.push(unit.rounds)
    }
    const extra = extractRecord(unit.extra)
    const extraLabel = extractString(extra['prompt_version'])
    if (extraLabel) {
      versionLabels.add(extraLabel)
    } else if (typeof unit.prompt_version_id === 'number') {
      const mapped = versionLabelMap.get(unit.prompt_version_id)
      versionLabels.add(
        mapped ?? t('promptDetail.table.versionFallback', { id: unit.prompt_version_id })
      )
    }
  })

  if (!versionLabels.size && typeof task.prompt_version_id === 'number') {
    const mapped = versionLabelMap.get(task.prompt_version_id)
    versionLabels.add(
      mapped ?? t('promptDetail.table.versionFallback', { id: task.prompt_version_id })
    )
  }

  const versionLabel = versionLabels.size
    ? Array.from(versionLabels).join(' / ')
    : t('promptDetail.content.versionFallback')

  const modelLabel = modelNames.size ? Array.from(modelNames).join(' / ') : '--'
  const temperature = temperatureValues.length ? temperatureValues[0] : null
  const repetitions = roundsValues.length ? Math.max(...roundsValues) : 1
  const statusKey = mapPromptTestTaskStatus(task.status)
  const createdAtSource = task.created_at ?? task.updated_at ?? ''
  const createdAtSortValue = createdAtSource ? safeDateValue(createdAtSource) : 0
  const createdAtDisplay = createdAtSource ? formatDateTime(createdAtSource) : '--'

  return {
    key: `task-${task.id}`,
    type: 'task',
    versionLabel,
    modelLabel,
    temperature,
    repetitions,
    statusKey,
    statusDisplay: statusLabel.value[statusKey] ?? statusKey,
    createdAtDisplay,
    createdAtSortValue,
    canNavigate: typeof task.id === 'number' && task.id > 0,
    taskId: task.id
  }
}

function resetMetaSelections() {
  const prompt = detail.value
  if (!prompt) {
    selectedClassId.value = null
    selectedTagIds.value = []
    return
  }
  selectedClassId.value = prompt.prompt_class.id
  selectedTagIds.value = prompt.tags.map((tag) => tag.id)
}

function extractTestRunError(error: unknown): string {
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
  return t('promptDetail.messages.testLoadFailed')
}

async function handleSaveMeta() {
  const prompt = detail.value
  if (!prompt) {
    return
  }
  if (selectedClassId.value === null) {
    ElMessage.warning(t('promptDetail.messages.classRequired'))
    return
  }
  if (!canSaveMeta.value) {
    ElMessage.info(t('promptDetail.messages.noChange'))
    return
  }
  isMetaSaving.value = true
  try {
    await updatePrompt(prompt.id, {
      class_id: selectedClassId.value,
      tag_ids: selectedTagIds.value
    })
    ElMessage.success(t('promptDetail.messages.updateSuccess'))
    await refreshDetail()
    await fetchMeta()
  } catch (error) {
    ElMessage.error(extractMetaError(error))
  } finally {
    isMetaSaving.value = false
  }
}

function openMetaDialog() {
  metaDialogVisible.value = true
  resetMetaSelections()
}

function closeMetaDialog() {
  metaDialogVisible.value = false
}

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

function formatTemperature(value: number | null | undefined) {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return '--'
  }
  return value.toFixed(2)
}

function formatDateTime(value: string | null | undefined) {
  if (!value) {
    return '--'
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }
  return dateTimeFormatter.value.format(date)
}

function summarizeContent(content: string) {
  const normalized = content.replace(/\s+/g, ' ').trim()
  if (!normalized) {
    return t('promptDetail.messages.contentEmpty')
  }
  return normalized.length > 80 ? `${normalized.slice(0, 80)}…` : normalized
}

async function handleCopyPrompt() {
  const content = selectedVersion.value?.content
  if (!content) {
    ElMessage.warning(t('promptDetail.content.copyEmpty'))
    return
  }
  try {
    if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
      await navigator.clipboard.writeText(content)
    } else {
      legacyCopyToClipboard(content)
    }
    ElMessage.success(t('promptDetail.content.copySuccess'))
  } catch (error) {
    ElMessage.error(t('promptDetail.content.copyFailed'))
  }
}

function legacyCopyToClipboard(text: string) {
  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.style.position = 'fixed'
  textarea.style.top = '0'
  textarea.style.left = '0'
  textarea.style.opacity = '0'
  document.body.appendChild(textarea)
  textarea.focus()
  textarea.select()
  const succeeded = document.execCommand('copy')
  document.body.removeChild(textarea)
  if (!succeeded) {
    throw new Error('Copy command failed')
  }
}

function handleSelectVersion(id: number) {
  selectedVersionId.value = id
}

function handleViewVersionCompare() {
  if (!currentId.value) return
  router.push({ name: 'prompt-version-compare', params: { id: currentId.value } })
}

function handleCreateVersion() {
  if (!currentId.value) return
  router.push({ name: 'prompt-version-create', params: { id: currentId.value } })
}

function handleCreateTest() {
  if (!currentId.value) return
  const query: Record<string, string> = { promptId: String(currentId.value) }
  if (selectedVersionId.value) {
    query.promptVersionIds = String(selectedVersionId.value)
  }
  router.push({ name: 'prompt-test-task-create', query })
}

function handleViewTestRecord(record: TestRecordRow) {
  if (!record.canNavigate) {
    ElMessage.warning(t('promptDetail.messages.testUnavailable'))
    return
  }
  if (record.type === 'task' && record.taskId) {
    void router
      .push({ name: 'prompt-test-task-result', params: { taskId: String(record.taskId) } })
      .catch(() => {})
    return
  }
  if (record.runId) {
    void router
      .push({ name: 'test-job-result', params: { id: record.runId } })
      .catch(() => {})
    return
  }
  ElMessage.warning(t('promptDetail.messages.testUnavailable'))
}

function goHome() {
  router.push({ name: 'prompt-management' })
}
</script>

<style scoped>
.detail-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.detail-breadcrumb {
  font-size: 13px;
}

.breadcrumb-link {
  cursor: pointer;
  color: inherit;
}

.info-card {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.info-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
}

.info-title-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.info-class {
  margin: 0;
  font-size: 13px;
  color: var(--text-weak-color);
}

.info-title {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
}

.info-desc {
  margin: 0;
  color: var(--text-weak-color);
  line-height: 1.6;
}

.info-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 8px;
  font-size: 13px;
  color: var(--text-weak-color);
}

.info-descriptions :deep(.el-descriptions__body) {
  font-size: 13px;
}

.info-tags {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 10px;
}

.info-tags__list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.info-tags :deep(.el-button.is-link) {
  padding: 0;
}

.meta-form {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.meta-alert {
  margin-bottom: 12px;
}

.meta-empty-tip {
  margin-left: 12px;
  font-size: 12px;
  color: var(--text-weak-color);
}

.meta-actions {
  display: flex;
  gap: 8px;
}

.tag-option {
  display: flex;
  align-items: center;
  gap: 8px;
}

.tag-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #909399;
}

.content-card {
  display: flex;
  flex-direction: column;
}

.content-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.content-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.content-subtitle {
  font-size: 13px;
  color: var(--text-weak-color);
}

.content-actions {
  display: flex;
  gap: 8px;
}

.content-body {
  flex: 1;
  display: flex;
  gap: 20px;
  align-items: stretch;
  min-height: 320px;
}

.content-main {
  flex: 2;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.content-main__meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  color: var(--text-weak-color);
}

.content-main__time {
  display: flex;
  align-items: center;
  gap: 8px;
}

.content-copy-button {
  padding: 0;
}

.content-main__label {
  margin-right: 8px;
}

.content-main__value {
  font-size: 14px;
  color: var(--header-text-color);
}

.content-scroll {
  flex: 1;
  border: 1px solid var(--side-border-color);
  border-radius: 8px;
  background: var(--content-bg-color);
  padding: 16px;
  overflow-y: auto;
  max-height: 460px;
}

.content-text {
  margin: 0;
  white-space: pre-wrap;
  font-family: 'JetBrains Mono', 'Fira Mono', Consolas, monospace;
  font-size: 13px;
  line-height: 1.6;
}

.content-history {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.history-title {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
}

.history-scroll {
  flex: 1;
  border: 1px solid var(--side-border-color);
  border-radius: 8px;
  background: var(--content-bg-color);
  padding: 12px;
  overflow-y: auto;
  max-height: 460px;
}

.history-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 10px;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.history-item + .history-item {
  margin-top: 8px;
}

.history-item.is-active,
.history-item:hover {
  background: rgba(64, 158, 255, 0.12);
}

.history-item__meta {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  color: var(--text-weak-color);
}

.history-version {
  font-weight: 600;
  color: var(--header-text-color);
}

.history-preview {
  margin: 0;
  font-size: 13px;
  color: var(--header-text-color);
  line-height: 1.5;
}

.history-date {
  font-size: 12px;
}

.test-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.test-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.test-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.test-subtitle {
  font-size: 13px;
  color: var(--text-weak-color);
}

.test-card :deep(.el-table__cell) {
  font-size: 13px;
}

.test-record-name {
  display: flex;
  align-items: center;
  gap: 8px;
}

.test-record-empty-action {
  color: var(--text-weak-color);
}

.test-alert {
  margin-bottom: 12px;
}
</style>
