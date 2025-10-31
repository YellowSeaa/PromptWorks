<template>
  <div class="prompt-test-result-page">
    <el-breadcrumb separator="/" class="page-breadcrumb">
      <el-breadcrumb-item>
        <span class="breadcrumb-link" @click="goBack">{{ t('menu.testJob') }}</span>
      </el-breadcrumb-item>
      <el-breadcrumb-item>{{ displayTaskName }}</el-breadcrumb-item>
    </el-breadcrumb>

    <section class="page-header">
      <div class="page-header__text">
        <h2>{{ displayTaskName }}</h2>
        <p class="page-desc">
          {{ headerDescription }}
        </p>
      </div>
      <div v-if="taskStatusTag" class="page-header__meta">
        <el-tag size="small" :type="taskStatusTag.type">
          {{ taskStatusTag.label }}
        </el-tag>
      </div>
    </section>

    <el-card v-loading="loading">
      <template #header>
        <div class="card-header">
          <el-radio-group v-model="activeTab" size="small">
            <el-radio-button label="units">{{ t('promptTestResult.tabs.units') }}</el-radio-button>
            <el-radio-button label="results">{{ t('promptTestResult.tabs.results') }}</el-radio-button>
            <el-radio-button label="analysis">{{ t('promptTestResult.tabs.analysis') }}</el-radio-button>
          </el-radio-group>
        </div>
      </template>

      <el-alert
        v-if="errorMessage"
        :title="errorMessage"
        type="error"
        show-icon
        class="result-alert"
      />

      <div v-if="activeTab === 'results'" class="result-panel">
        <div class="result-toolbar">
          <div class="toolbar-markdown">
            <span class="toolbar-markdown__label" :title="t('promptTestResult.markdown.tooltip')">
              {{ t('promptTestResult.markdown.label') }}
            </span>
            <el-switch
              v-model="resultMarkdownEnabled"
              size="small"
              :active-text="t('promptTestResult.markdown.on')"
              :inactive-text="t('promptTestResult.markdown.off')"
              inline-prompt
            />
          </div>
          <div class="columns-control">
            <el-button
              size="small"
              type="primary"
              :disabled="columnConfigs.length >= 5"
              @click="addColumn"
            >
              {{ t('promptTestResult.actions.addColumn') }}
            </el-button>
            <el-button
              size="small"
              type="default"
              :disabled="columnConfigs.length <= 1"
              @click="removeLastColumn"
            >
              {{ t('promptTestResult.actions.removeColumn') }}
            </el-button>
            <span class="column-count">{{ t('promptTestResult.actions.columnCount', { count: columnConfigs.length }) }}</span>
          </div>
        </div>

        <div class="result-grid">
          <div class="result-grid-scroll" :style="{ width: gridWidth, minWidth: '100%' }">
            <div
              class="grid-header"
              :style="{ gridTemplateColumns: gridTemplateColumnsValue, width: gridWidth, minWidth: '100%' }"
            >
              <div
                v-for="(config, idx) in columnConfigs"
                :key="config.columnId"
                class="grid-cell"
              >
                <div class="header-select">
                  <el-select v-model="config.unitId" size="small" class="column-selector">
                    <el-option
                      v-for="unit in units"
                      :key="unit.id"
                      :label="formatUnitOption(unit)"
                      :value="unit.id"
                    />
                  </el-select>
                  <el-button
                    v-if="columnConfigs.length > 1"
                    size="small"
                    type="text"
                    @click="removeColumn(config.columnId)"
                  >
                    {{ t('promptTestResult.actions.removeSingleColumn') }}
                  </el-button>
                </div>
                <div class="header-details">
                  <div>
                    <strong>{{ selectedUnits[idx]?.name ?? t('promptTestResult.empty.noSelection') }}</strong>
                  </div>
                  <div class="header-meta">
                    <span>{{ t('promptTestResult.fields.version') }}: {{ selectedUnits[idx]?.promptVersion ?? '-' }}</span>
                    <span>{{ t('promptTestResult.fields.model') }}: {{ selectedUnits[idx]?.modelName ?? '-' }}</span>
                    <span>{{ t('promptTestResult.fields.parameters') }}: {{ selectedUnits[idx]?.parameterSet ?? '-' }}</span>
                  </div>
                </div>
              </div>
            </div>

            <div v-if="alignedRows.length" class="grid-body">
              <div
                v-for="row in alignedRows"
                :key="row.index"
                class="grid-row"
                :style="{ gridTemplateColumns: gridTemplateColumnsValue, width: gridWidth, minWidth: '100%' }"
              >
                <div
                  v-for="(cell, cellIndex) in row.cells"
                  :key="cellIndex"
                  class="grid-cell"
                >
                  <div class="output-badge">#{{ row.index }}</div>
                  <template v-if="cell">
                    <div v-if="shouldShowWarning(cell)" class="output-warning">
                      <el-alert
                        type="warning"
                        show-icon
                        :closable="false"
                        :title="t('promptTestResult.warnings.missingOutputTitle')"
                      >
                        <template #default>
                          <span>{{ t('promptTestResult.warnings.missingOutputDescription') }}</span>
                          <el-link
                            type="primary"
                            :underline="false"
                            class="raw-response-link"
                            @click="openRawResponseDialog(selectedUnits[cellIndex]?.name, row.index, cell?.rawResponse ?? null)"
                          >
                            {{ t('promptTestResult.warnings.viewRawResponse') }}
                          </el-link>
                        </template>
                      </el-alert>
                    </div>
                    <template v-else>
                      <div
                        v-if="!resultMarkdownEnabled"
                        class="output-content output-content--plain"
                      >
                        {{ resolveCellContent(cell) || placeholderText }}
                      </div>
                      <div
                        v-else
                        class="output-content output-content--markdown"
                        v-html="renderMarkdown(resolveCellContent(cell) || placeholderText)"
                      />
                    </template>
                    <div class="output-meta">{{ cell?.meta ?? '' }}</div>
                    <div v-if="cell?.variables && Object.keys(cell.variables).length" class="output-variables">
                      <div
                        v-for="(value, key) in cell.variables"
                        :key="key"
                        class="variable-item"
                      >
                        <span class="variable-key">{{ key }}:</span>
                        <span class="variable-value">{{ value }}</span>
                      </div>
                    </div>
                  </template>
                  <template v-else>
                    <div
                      v-if="getMissingOutputInfo(row.index, cellIndex)"
                      class="output-warning"
                    >
                      <el-alert
                        :type="getMissingOutputInfo(row.index, cellIndex)?.type ?? 'info'"
                        show-icon
                        :closable="false"
                        :title="getMissingOutputInfo(row.index, cellIndex)?.title ?? ''"
                      >
                        <template v-if="getMissingOutputInfo(row.index, cellIndex)?.description" #default>
                          <span>{{ getMissingOutputInfo(row.index, cellIndex)?.description }}</span>
                        </template>
                      </el-alert>
                    </div>
                    <div
                      v-else-if="!resultMarkdownEnabled"
                      class="output-content output-content--plain"
                    >
                      {{ placeholderText }}
                    </div>
                    <div
                      v-else
                      class="output-content output-content--markdown"
                      v-html="renderMarkdown(placeholderText)"
                    />
                    <div class="output-meta"></div>
                  </template>
                </div>
              </div>
            </div>
            <el-empty v-else :description="t('promptTestResult.empty.noOutputs')" />
          </div>
        </div>
      </div>

      <div v-else-if="activeTab === 'units'" class="units-panel">
        <div class="units-toolbar">
          <div class="units-filters">
            <el-input
              v-model="filterForm.keyword"
              class="units-filter__keyword"
              size="small"
              clearable
              :placeholder="t('promptTestResult.filters.keywordPlaceholder')"
            />
            <el-select
              v-model="filterForm.promptVersion"
              size="small"
              class="units-filter__select"
              :placeholder="t('promptTestResult.filters.promptVersion')"
              clearable
            >
              <el-option
                v-for="version in filterOptions.promptVersions"
                :key="version"
                :label="version"
                :value="version"
              />
            </el-select>
            <el-select
              v-model="filterForm.modelName"
              size="small"
              class="units-filter__select"
              :placeholder="t('promptTestResult.filters.modelName')"
              clearable
            >
              <el-option
                v-for="model in filterOptions.modelNames"
                :key="model"
                :label="model"
                :value="model"
              />
            </el-select>
            <el-select
              v-model="filterForm.parameterSet"
              size="small"
              class="units-filter__select"
              :placeholder="t('promptTestResult.filters.parameterSet')"
              clearable
            >
              <el-option
                v-for="parameter in filterOptions.parameterSets"
                :key="parameter"
                :label="parameter"
                :value="parameter"
              />
            </el-select>
          </div>
          <el-button type="primary" size="small" @click="exportUnitsCsv">
            {{ t('promptTestResult.actions.exportCsv') }}
          </el-button>
        </div>
        <div v-if="filteredUnits.length" class="unit-card-grid">
          <el-card
            v-for="unit in filteredUnits"
            :key="unit.id"
            class="unit-card"
            shadow="hover"
            @click="openUnitDetail(unit.id)"
          >
            <div class="unit-card__header">
              <h4>{{ unit.name }}</h4>
              <el-tag size="small">{{ unit.outputs.length }} {{ t('promptTestResult.labels.outputs') }}</el-tag>
            </div>
            <div class="unit-card__meta">
              <div>{{ t('promptTestResult.fields.version') }}: {{ unit.promptVersion }}</div>
              <div>{{ t('promptTestResult.fields.model') }}: {{ unit.modelName }}</div>
              <div>{{ t('promptTestResult.fields.parameters') }}: {{ unit.parameterSet }}</div>
            </div>
            <div class="unit-card__preview">
              <p v-if="unit.outputs[0]">
                <strong>#1</strong> {{ unit.outputs[0].content.slice(0, 60) }}<span v-if="unit.outputs[0].content.length > 60">...</span>
              </p>
              <p v-else>{{ t('promptTestResult.empty.noOutputs') }}</p>
            </div>
          </el-card>
        </div>
        <el-empty v-else :description="t('promptTestResult.empty.noUnitsFiltered')" />
      </div>
      <div v-else class="analysis-panel">
        <el-empty :description="t('promptTestResult.empty.analysis')" />
      </div>
    </el-card>
    <el-dialog
      v-model="rawResponseDialog.visible"
      :title="rawResponseDialog.title"
      width="640px"
    >
      <div class="raw-response-dialog__content">
        <pre>{{ rawResponseDialog.content || t('promptTestResult.dialog.rawResponsePlaceholder') }}</pre>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { getPromptTestTask, listPromptTestUnits, listPromptTestExperiments } from '../api/promptTest'
import type { PromptTestTask } from '../types/promptTest'
import type { PromptTestResultUnit } from '../utils/promptTestResult'
import { buildPromptTestResultUnit, detectMissingOutput } from '../utils/promptTestResult'
import MarkdownIt from 'markdown-it'

type UnitOutput = PromptTestResultUnit['outputs'][number]

interface UnitColumnConfig {
  columnId: number
  unitId: number | null
}

interface AlignedRow {
  index: number
  cells: Array<UnitOutput | null>
}

interface MissingOutputInfo {
  type: 'info' | 'warning' | 'error'
  title: string
  description?: string
}

const router = useRouter()
const route = useRoute()
const { t, locale } = useI18n()

const task = ref<PromptTestTask | null>(null)
const units = ref<PromptTestResultUnit[]>([])
const loading = ref(false)
const errorMessage = ref<string | null>(null)
const resultMarkdownEnabled = ref(false)
const rawResponseDialog = reactive({
  visible: false,
  title: '',
  content: ''
})

const tabList = ['units', 'results', 'analysis'] as const
type TabKey = (typeof tabList)[number]
const DEFAULT_TAB: TabKey = 'results'

function isTabKey(value: unknown): value is TabKey {
  return typeof value === 'string' && tabList.includes(value as TabKey)
}

function resolveTabFromQuery(value: unknown): TabKey | null {
  if (Array.isArray(value)) {
    const candidate = value.find((item) => isTabKey(item))
    return candidate ?? null
  }
  return isTabKey(value) ? value : null
}

const queryTab = resolveTabFromQuery(route.query.tab)
const activeTab = ref<TabKey>(queryTab ?? DEFAULT_TAB)

const columnConfigs = ref<UnitColumnConfig[]>([])
let columnUid = 0
const markdownRenderer = new MarkdownIt({
  breaks: true,
  linkify: true,
  html: false
})

const routeTaskIdParam = computed(() => (route.params.taskId as string | undefined) ?? '')

const statusLabelMap: Record<string, string> = {
  draft: '草稿',
  ready: '待执行',
  running: '执行中',
  completed: '已完成',
  failed: '执行失败'
}

const statusTagType: Record<string, 'info' | 'success' | 'warning' | 'danger'> = {
  draft: 'info',
  ready: 'info',
  running: 'warning',
  completed: 'success',
  failed: 'danger'
}

const taskStatusLabel = computed(() =>
  task.value ? statusLabelMap[task.value.status] ?? task.value.status : null
)

const taskStatusTag = computed(() => {
  if (!task.value) return null
  return {
    label: taskStatusLabel.value ?? task.value.status,
    type: statusTagType[task.value.status] ?? 'info'
  }
})

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

function formatDateTime(value: string | null | undefined) {
  if (!value) return '--'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return String(value)
  }
  return dateTimeFormatter.value.format(date)
}

const displayTaskName = computed(() => {
  if (task.value?.name) {
    return task.value.name
  }
  const fallbackId = routeTaskIdParam.value || (task.value ? String(task.value.id) : '')
  return t('promptTestResult.fallback.taskTitle', { id: fallbackId || '--' })
})

const headerDescription = computed(() => {
  if (!task.value) {
    return t('promptTestResult.headerDescriptionPending')
  }
  const createdAt = formatDateTime(task.value.created_at)
  const unitCount = units.value.length
  const status = taskStatusLabel.value ?? task.value.status ?? '--'
  return t('promptTestResult.headerDescription', { createdAt, unitCount, status })
})

const placeholderText = computed(() => t('promptTestResult.empty.placeholder'))
function renderMarkdown(content: string | null | undefined) {
  const source = content ?? ''
  return markdownRenderer.render(source || '')
}

function resolveCellContent(cell: UnitOutput | null | undefined) {
  const content = cell?.content ?? ''
  return typeof content === 'string' && content.trim().length > 0 ? content : ''
}

function shouldShowWarning(cell: UnitOutput | null | undefined): cell is UnitOutput {
  if (!cell) return false
  const hasContent = typeof cell.content === 'string' && cell.content.trim().length > 0
  const hasRawResponse =
    typeof cell.rawResponse === 'string' && cell.rawResponse.trim().length > 0
  return !hasContent && hasRawResponse
}

function openRawResponseDialog(
  unitName: string | undefined | null,
  runIndex: number,
  rawResponse: string | null
) {
  if (!rawResponse) return
  const name = unitName?.trim()
  rawResponseDialog.title = t('promptTestResult.dialog.rawResponseTitle', {
    unit: name && name.length ? name : t('promptTestResult.empty.noSelection'),
    index: runIndex
  })
  rawResponseDialog.content = rawResponse
  rawResponseDialog.visible = true
}

const filterForm = reactive({
  keyword: '',
  promptVersion: '' as string | undefined,
  modelName: '' as string | undefined,
  parameterSet: '' as string | undefined
})

const filterOptions = computed(() => {
  const promptVersions = Array.from(
    new Set(units.value.map((unit) => unit.promptVersion))
  ).filter((value) => typeof value === 'string' && value.trim().length > 0)
  const modelNames = Array.from(new Set(units.value.map((unit) => unit.modelName))).filter(
    (value) => typeof value === 'string' && value.trim().length > 0
  )
  const parameterSets = Array.from(
    new Set(units.value.map((unit) => unit.parameterSet))
  ).filter((value) => typeof value === 'string' && value.trim().length > 0)
  return {
    promptVersions,
    modelNames,
    parameterSets
  }
})

const filteredUnits = computed(() =>
  units.value.filter((unit) => {
    const keyword = filterForm.keyword.trim().toLowerCase()
    const keywordMatched =
      !keyword ||
      [unit.name, unit.modelName, unit.promptVersion]
        .map((field) => String(field || '').toLowerCase())
        .some((field) => field.includes(keyword))
    const versionMatched =
      !filterForm.promptVersion || unit.promptVersion === filterForm.promptVersion
    const modelMatched = !filterForm.modelName || unit.modelName === filterForm.modelName
    const parameterMatched =
      !filterForm.parameterSet || unit.parameterSet === filterForm.parameterSet
    return keywordMatched && versionMatched && modelMatched && parameterMatched
  })
)

const selectedUnits = computed(() =>
  columnConfigs.value.map(
    (config) => units.value.find((unit) => unit.id === config.unitId) ?? null
  )
)

function resolveMissingOutputInfo(
  unit: PromptTestResultUnit | null,
  rowIndex: number
): MissingOutputInfo | null {
  const context = detectMissingOutput(unit, rowIndex)
  if (!context) {
    return null
  }
  const produced = context.produced
  const errorMessage = context.error?.trim() ?? ''
  switch (context.reason) {
    case 'partial':
      if (context.status === 'failed') {
        return {
          type: 'error',
          title: t('promptTestResult.empty.reasons.failedTitle'),
          description: errorMessage || t('promptTestResult.empty.reasons.failedDescription')
        }
      }
      return {
        type: 'info',
        title: t('promptTestResult.empty.reasons.partialTitle', {
          count: produced
        })
      }
    case 'failed':
      return {
        type: 'error',
        title: t('promptTestResult.empty.reasons.failedTitle'),
        description: errorMessage || t('promptTestResult.empty.reasons.failedDescription')
      }
    case 'cancelled':
      return {
        type: 'info',
        title: t('promptTestResult.empty.reasons.cancelledTitle')
      }
    case 'running':
      return {
        type: 'info',
        title: t('promptTestResult.empty.reasons.runningTitle')
      }
    case 'pending':
      return {
        type: 'info',
        title: t('promptTestResult.empty.reasons.pendingTitle')
      }
    case 'completed':
      return {
        type: errorMessage ? 'warning' : 'info',
        title: errorMessage
          ? t('promptTestResult.empty.reasons.completedWithReasonTitle')
          : t('promptTestResult.empty.reasons.completedTitle'),
        description:
          errorMessage || t('promptTestResult.empty.reasons.completedDescription')
      }
    default:
      return {
        type: errorMessage ? 'warning' : 'info',
        title: t('promptTestResult.empty.reasons.unknownTitle'),
        description:
          errorMessage || t('promptTestResult.empty.reasons.unknownDescription')
      }
  }
}

function getMissingOutputInfo(rowIndex: number, columnIndex: number): MissingOutputInfo | null {
  const unit = selectedUnits.value[columnIndex] ?? null
  return resolveMissingOutputInfo(unit, rowIndex)
}

const columnCount = computed(() => Math.max(columnConfigs.value.length, 1))
const gridTemplateColumnsValue = computed(
  () => `repeat(${columnCount.value}, minmax(240px, 1fr))`
)
const gridWidth = computed(() => {
  const minWidth = 260
  return columnCount.value > 1 ? `${columnCount.value * minWidth}px` : '100%'
})

const alignedRows = computed<AlignedRow[]>(() => {
  const maxLength = Math.max(
    ...selectedUnits.value.map((unit) => unit?.outputs.length ?? 0),
    0
  )
  return Array.from({ length: maxLength }, (_, idx) => ({
    index: idx + 1,
    cells: selectedUnits.value.map((unit) => unit?.outputs[idx] ?? null)
  }))
})

watch(
  () => route.query.tab,
  (tab) => {
    const nextTab = resolveTabFromQuery(tab) ?? DEFAULT_TAB
    if (activeTab.value !== nextTab) {
      activeTab.value = nextTab
    }
  }
)

watch(
  activeTab,
  (tab) => {
    const currentTab = resolveTabFromQuery(route.query.tab)
    if (currentTab === tab) return
    router.replace({ query: { ...route.query, tab } })
  }
)

watch(
  units,
  (list) => {
    if (!list.length) {
      columnConfigs.value = []
      columnUid = 0
      return
    }
    const availableIds = new Set(list.map((unit) => unit.id))
    let preserved = columnConfigs.value.filter(
      (config) => config.unitId !== null && availableIds.has(config.unitId)
    )
    if (!preserved.length) {
      columnUid = 0
      preserved = list.slice(0, Math.min(2, list.length)).map((unit) => ({
        columnId: ++columnUid,
        unitId: unit.id
      }))
    } else {
      columnUid = Math.max(...preserved.map((config) => config.columnId))
    }
    columnConfigs.value = preserved
  },
  { immediate: true }
)

function formatUnitOption(unit: PromptTestResultUnit) {
  const displayParts: string[] = []
  const seenSegments = new Set<string>()

  const normalize = (segment: string) => segment.replace(/\s+/g, '').toLowerCase()
  const splitSegments = (value: string) =>
    value
      .split('/')
      .map((item) => item.trim())
      .filter((item) => item.length > 0)

  const addValue = (raw: unknown, force = false) => {
    if (typeof raw !== 'string') return
    const text = raw.trim()
    if (!text) return
    const segments = splitSegments(text)
    const normalizedSegments = segments
      .map((segment) => normalize(segment))
      .filter((segment) => segment.length > 0)
    const seenList = Array.from(seenSegments)
    const hasNewSegment = normalizedSegments.some((segment) => {
      if (seenSegments.has(segment)) {
        return false
      }
      const redundant =
        segment.length <= 4 && seenList.some((existing) => existing.includes(segment))
      return !redundant
    })
    if (!force && !hasNewSegment) {
      normalizedSegments.forEach((segment) => seenSegments.add(segment))
      return
    }
    displayParts.push(text)
    normalizedSegments.forEach((segment) => seenSegments.add(segment))
  }

  addValue(unit.name, true)
  addValue(unit.promptVersion)
  addValue(unit.modelName)
  addValue(unit.parameterSet)

  if (!displayParts.length) {
    return String(unit.id)
  }
  return displayParts.join(' | ')
}

function addColumn() {
  if (columnConfigs.value.length >= 5 || !units.value.length) return
  const availableUnit = units.value.find(
    (unit) => !columnConfigs.value.some((config) => config.unitId === unit.id)
  )
  const fallbackUnitId = availableUnit?.id ?? units.value[0]?.id ?? null
  columnConfigs.value = [
    ...columnConfigs.value,
    {
      columnId: ++columnUid,
      unitId: fallbackUnitId
    }
  ]
}

function removeColumn(columnId: number) {
  if (columnConfigs.value.length <= 1) return
  columnConfigs.value = columnConfigs.value.filter((config) => config.columnId !== columnId)
}

function removeLastColumn() {
  if (columnConfigs.value.length <= 1) return
  const lastId = columnConfigs.value[columnConfigs.value.length - 1].columnId
  removeColumn(lastId)
}

function goBack() {
  router.push({ name: 'test-job-management' })
}

function exportUnitsCsv() {
  const headers = [
    'unit_id',
    'unit_name',
    'prompt_version',
    'model_name',
    'parameter_set',
    'run_index',
    'content',
    'meta',
    'variables'
  ]

  const rows = units.value.flatMap((unit) =>
    unit.outputs.map((output) => {
      const variables =
        Object.keys(output.variables).length > 0 ? JSON.stringify(output.variables) : ''
      const safeContent = output.content.replace(/"/g, '""').replace(/\r?\n/g, ' ')
      return [
        unit.id,
        unit.name,
        unit.promptVersion,
        unit.modelName,
        unit.parameterSet,
        output.runIndex,
        `"${safeContent}"`,
        output.meta ?? '',
        variables
      ]
    })
  )

  const csv = [headers.join(','), ...rows.map((row) => row.join(','))].join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  const identifier = routeTaskIdParam.value || (task.value ? String(task.value.id) : 'task')
  link.download = `prompt-test-units-${identifier}.csv`
  link.click()
  URL.revokeObjectURL(url)
}

function openUnitDetail(unitId: number) {
  const id = routeTaskIdParam.value || (task.value ? String(task.value.id) : '')
  if (!id) return
  router.push({ name: 'prompt-test-unit-result', params: { taskId: id, unitId } })
}

function extractTaskId(value: unknown): number | null {
  if (typeof value === 'string' && value.trim()) {
    const parsed = Number(value)
    if (Number.isInteger(parsed) && parsed > 0) {
      return parsed
    }
  }
  if (typeof value === 'number' && Number.isInteger(value) && value > 0) {
    return value
  }
  return null
}

async function loadTaskResult(taskId: number) {
  loading.value = true
  errorMessage.value = null
  try {
    const [taskData, unitList] = await Promise.all([
      getPromptTestTask(taskId),
      listPromptTestUnits(taskId)
    ])
    task.value = taskData
    const experimentResults = await Promise.allSettled(
      unitList.map((unit) => listPromptTestExperiments(unit.id))
    )
    let hasExperimentError = false
    const resultUnits = unitList.map((unit, index) => {
      const experiment = experimentResults[index]
      if (experiment.status === 'fulfilled') {
        return buildPromptTestResultUnit(unit, experiment.value)
      }
      hasExperimentError = true
      console.error(`加载测试单元 ${unit.id} 的实验数据失败`, experiment.reason)
      return buildPromptTestResultUnit(unit, [])
    })
    units.value = resultUnits
    if (hasExperimentError) {
      const message = t('promptTestResult.messages.partialFailed')
      errorMessage.value = message
      ElMessage.warning(message)
    }
  } catch (error) {
    console.error('加载测试任务结果失败', error)
    task.value = null
    units.value = []
    columnConfigs.value = []
    columnUid = 0
    const message = t('promptTestResult.messages.loadFailed')
    errorMessage.value = message
    ElMessage.error(message)
  } finally {
    loading.value = false
  }
}

async function refreshTask() {
  const id = extractTaskId(route.params.taskId)
  if (id === null) {
    loading.value = false
    task.value = null
    units.value = []
    columnConfigs.value = []
    columnUid = 0
    errorMessage.value = t('promptTestResult.messages.invalidTask')
    return
  }
  await loadTaskResult(id)
}

onMounted(() => {
  void refreshTask()
})

watch(
  () => route.params.taskId,
  () => {
    void refreshTask()
  }
)
</script>

<style scoped>
.prompt-test-result-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-breadcrumb {
  margin: 0;
}

.breadcrumb-link {
  cursor: pointer;
  color: var(--el-color-primary);
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.page-header__meta {
  display: flex;
  align-items: center;
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
  display: flex;
  justify-content: flex-start;
  align-items: center;
}

.result-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.result-alert {
  margin-bottom: 16px;
}

.result-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.toolbar-markdown {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--text-weak-color);
}

.toolbar-markdown__label {
  white-space: nowrap;
}

.columns-control {
  display: flex;
  align-items: center;
  gap: 8px;
}

.column-count {
  font-size: 12px;
  color: var(--text-weak-color);
}

.result-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 8px;
}

.result-grid-scroll {
  display: inline-block;
  min-width: 100%;
}

.grid-header {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 12px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.grid-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.grid-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 12px;
}

.grid-cell {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px;
  border: 1px solid var(--el-color-info-light-8);
  border-radius: 6px;
  background-color: var(--el-color-info-light-9);
}

.header-select {
  display: flex;
  align-items: center;
  gap: 8px;
}

.column-selector {
  flex: 1;
}

.header-details {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 6px;
}

.header-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 12px;
  color: var(--text-weak-color);
}

.output-badge {
  font-size: 12px;
  color: var(--el-color-primary);
  font-weight: 600;
}

.output-content {
  font-size: 14px;
  color: var(--el-text-color-primary);
}

.output-content--plain {
  white-space: pre-wrap;
}

.output-content--markdown {
  line-height: 1.6;
}

.output-content--markdown :deep(p) {
  margin: 0 0 8px;
}

.output-content--markdown :deep(p:last-child) {
  margin-bottom: 0;
}

.output-content--markdown :deep(pre) {
  margin: 0 0 12px;
  padding: 8px 12px;
  background-color: var(--el-color-info-light-9);
  border-radius: 4px;
  overflow-x: auto;
}

.output-content--markdown :deep(code) {
  font-family: var(--el-font-family-monospace, 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, Courier, monospace);
  background-color: var(--el-color-info-light-9);
  padding: 0 4px;
  border-radius: 4px;
}

.output-warning {
  margin: 4px 0 8px;
}

.raw-response-link {
  margin-left: 8px;
  font-size: 13px;
}

.raw-response-dialog__content {
  max-height: 60vh;
  overflow: auto;
  background-color: #1f1f1f;
  border-radius: 6px;
  padding: 16px;
  color: #f5f5f5;
}

.raw-response-dialog__content pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: var(--el-font-family-monospace, 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, Courier, monospace);
  font-size: 13px;
}

.output-meta {
  font-size: 12px;
  color: var(--text-weak-color);
}

.output-variables {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.variable-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
}

.variable-key {
  font-weight: 600;
  color: var(--el-color-primary);
}

.variable-value {
  color: var(--el-text-color-regular);
}

.analysis-panel {
  padding: 40px 0;
}

.units-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.units-toolbar {
  display: flex;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
}

.units-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.units-filter__keyword {
  width: 200px;
}

.units-filter__select {
  width: 160px;
}

.unit-card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
}

.unit-card {
  cursor: pointer;
}

.unit-card__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.unit-card__meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  color: var(--text-weak-color);
}

.unit-card__preview {
  margin-top: 12px;
  font-size: 13px;
  color: var(--el-text-color-regular);
}

@media (max-width: 768px) {
  .grid-header,
  .grid-row {
    grid-template-columns: 1fr;
  }
}
</style>
