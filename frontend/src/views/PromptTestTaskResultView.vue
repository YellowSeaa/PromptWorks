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
        <div class="analysis-toolbar">
          <el-select
            v-model="selectedAnalysisModules"
            multiple
            collapse-tags
            filterable
            size="small"
            class="analysis-toolbar__selector"
            :placeholder="t('promptTestResult.analysis.selectPlaceholder')"
            :loading="analysisModulesLoading"
            clearable
          >
            <el-option
              v-for="module in analysisModules"
              :key="module.module_id"
              :label="module.name"
              :value="module.module_id"
            >
              <div class="analysis-option">
                <span class="analysis-option__title">{{ module.name }}</span>
                <span v-if="module.description" class="analysis-option__desc">
                  {{ module.description }}
                </span>
              </div>
            </el-option>
          </el-select>
          <el-button
            type="primary"
            size="small"
            :disabled="!selectedAnalysisModules.length"
            :loading="runningSelected"
            @click="runSelectedModules"
          >
            {{ t('promptTestResult.analysis.actions.runSelected') }}
          </el-button>
        </div>
        <div v-if="!selectedAnalysisModules.length" class="analysis-empty">
          <el-empty :description="t('promptTestResult.analysis.selectHint')" />
        </div>
        <div v-else class="analysis-modules-grid">
          <el-card
            v-for="moduleId in selectedAnalysisModules"
            :key="moduleId"
            class="analysis-module-card"
            shadow="hover"
          >
            <template #header>
              <div class="analysis-module-card__header">
                <div class="analysis-module-card__title">
                  <h4>{{ moduleStates[moduleId]?.definition.name || moduleId }}</h4>
                  <p
                    v-if="moduleStates[moduleId]?.definition.description"
                    class="analysis-module-card__desc"
                  >
                    {{ moduleStates[moduleId]?.definition.description }}
                  </p>
                </div>
                <div class="analysis-module-card__actions" v-if="moduleStates[moduleId]">
                  <el-tag
                    size="small"
                    :type="moduleStates[moduleId].status === 'error' ? 'danger' : 'info'"
                  >
                    {{ t(`promptTestResult.analysis.status.${moduleStates[moduleId].status}`) }}
                  </el-tag>
                  <el-button
                    size="small"
                    text
                    :loading="moduleStates[moduleId].status === 'running'"
                    @click.stop="runAnalysisModule(moduleId)"
                  >
                    {{
                      moduleStates[moduleId].result
                        ? t('promptTestResult.analysis.actions.rerun')
                        : t('promptTestResult.analysis.actions.run')
                    }}
                  </el-button>
                </div>
              </div>
            </template>
            <div v-if="moduleStates[moduleId]" class="analysis-module-card__body">
              <div
                v-if="moduleStates[moduleId].definition.parameters.length"
                class="analysis-params"
              >
                <el-form label-position="top" size="small" class="analysis-params__form">
                  <el-form-item
                    v-for="param in moduleStates[moduleId].definition.parameters"
                    :key="param.key"
                    :label="param.label"
                    :required="param.required"
                    class="analysis-param-item"
                  >
                    <template v-if="param.type === 'select'">
                      <el-select
                        v-model="moduleStates[moduleId].form[param.key]"
                        size="small"
                        class="analysis-param-input"
                        clearable
                      >
                        <el-option
                          v-for="(option, optionIndex) in (param.options || [])"
                          :key="`${param.key}-${optionIndex}`"
                          :label="String(option)"
                          :value="option"
                        />
                      </el-select>
                    </template>
                    <template v-else-if="param.type === 'number'">
                      <el-input-number
                        v-model="moduleStates[moduleId].form[param.key]"
                        :controls="false"
                        class="analysis-param-input"
                        :placeholder="param.help_text || ''"
                      />
                    </template>
                    <template v-else>
                      <el-input
                        v-model="moduleStates[moduleId].form[param.key]"
                        size="small"
                        class="analysis-param-input"
                        :placeholder="param.help_text || ''"
                      />
                    </template>
                    <p v-if="param.help_text" class="analysis-param-tip">{{ param.help_text }}</p>
                  </el-form-item>
                </el-form>
              </div>
              <el-alert
                v-if="moduleStates[moduleId].errorMessage"
                type="error"
                :title="moduleStates[moduleId].errorMessage"
                show-icon
                class="analysis-alert"
              />
              <div v-if="moduleStates[moduleId].status === 'running'" class="analysis-loading">
                <el-skeleton animated :rows="3" />
              </div>
              <template v-else-if="moduleStates[moduleId].result">
                <el-alert
                  v-if="moduleStates[moduleId].result"
                  type="info"
                  show-icon
                  class="analysis-alert"
                >
                  <ul class="analysis-insight-list">
                    <template v-if="moduleStates[moduleId].insightDetails.length">
                      <li
                        v-for="(detail, insightIndex) in moduleStates[moduleId].insightDetails"
                        :key="`detail-${insightIndex}`"
                      >
                        <template v-if="detail.type === 'latency_comparison'">
                          {{ t('promptTestResult.analysis.text.latencyFastest') }}
                          <el-tooltip :content="detail.fast.unit_name">
                            <span
                              class="analysis-unit-chip"
                              @click="handleUnitChipClick(detail.fast.unit_id)"
                            >
                              {{ getUnitDisplayLabel(moduleId, detail.fast) }}
                            </span>
                          </el-tooltip>
                          ，{{ t('promptTestResult.analysis.text.approx') }}
                          {{ formatMetricValue(detail.fast.value) }}{{ detail.fast.unit }}；
                          {{ t('promptTestResult.analysis.text.latencySlowest') }}
                          <el-tooltip :content="detail.slow.unit_name">
                            <span
                              class="analysis-unit-chip"
                              @click="handleUnitChipClick(detail.slow.unit_id)"
                            >
                              {{ getUnitDisplayLabel(moduleId, detail.slow) }}
                            </span>
                          </el-tooltip>
                          ，{{ t('promptTestResult.analysis.text.approx') }}
                          {{ formatMetricValue(detail.slow.value) }}{{ detail.slow.unit }}。
                        </template>
                        <template v-else-if="detail.type === 'tokens_peak'">
                          {{ t('promptTestResult.analysis.text.tokensPeak') }}
                          <el-tooltip :content="detail.unit.unit_name">
                            <span
                              class="analysis-unit-chip"
                              @click="handleUnitChipClick(detail.unit.unit_id)"
                            >
                              {{ getUnitDisplayLabel(moduleId, detail.unit) }}
                            </span>
                          </el-tooltip>
                          ，{{ t('promptTestResult.analysis.text.approx') }}
                          {{ formatMetricValue(detail.unit.value) }}{{ detail.unit.unit }}。
                        </template>
                        <template v-else-if="detail.type === 'throughput_peak'">
                          {{ t('promptTestResult.analysis.text.throughputPeak') }}
                          <el-tooltip :content="detail.unit.unit_name">
                            <span
                              class="analysis-unit-chip"
                              @click="handleUnitChipClick(detail.unit.unit_id)"
                            >
                              {{ getUnitDisplayLabel(moduleId, detail.unit) }}
                            </span>
                          </el-tooltip>
                          ，{{ t('promptTestResult.analysis.text.approx') }}
                          {{ formatMetricValue(detail.unit.value) }}{{ detail.unit.unit }}。
                        </template>
                        <template v-else>
                          {{ moduleStates[moduleId].result?.insights[insightIndex] || '' }}
                        </template>
                      </li>
                    </template>
                    <template v-else>
                      <li
                        v-for="(insight, insightIndex) in moduleStates[moduleId].result?.insights || []"
                        :key="`plain-${insightIndex}`"
                      >
                        {{ insight }}
                      </li>
                    </template>
                  </ul>
                </el-alert>
                <el-table
                  :data="moduleStates[moduleId].result.data"
                  size="small"
                  border
                  stripe
                  :empty-text="t('promptTestResult.analysis.emptyData')"
                >
                  <el-table-column
                    v-for="meta in moduleStates[moduleId].result.columns_meta"
                    :key="meta.name"
                    :prop="meta.name"
                    :label="meta.label"
                  >
                    <template #default="{ row }">
                      {{ formatAnalysisCell(row[meta.name]) }}
                    </template>
                  </el-table-column>
                </el-table>
                <div v-if="getPrebuiltCharts(moduleId).length" class="analysis-prebuilt-charts">
                  <div
                    v-for="chart in getPrebuiltCharts(moduleId)"
                    :key="`${moduleId}-${chart.id}`"
                    class="analysis-prebuilt-chart"
                  >
                    <div class="analysis-prebuilt-chart__header">
                      <h5>{{ chart.title }}</h5>
                      <p v-if="chart.description" class="analysis-prebuilt-chart__desc">
                        {{ chart.description }}
                      </p>
                    </div>
                    <div
                      class="analysis-chart"
                      :ref="(el) => handlePrebuiltChartRef(moduleId, chart, el)"
                    ></div>
                  </div>
                </div>
                <template v-else-if="getChartableColumns(moduleId).length">
                  <div class="analysis-chart-block">
                    <div class="analysis-chart-toolbar">
                      <el-select
                        v-model="moduleStates[moduleId].chartColumn"
                        size="small"
                        class="analysis-chart-toolbar__select"
                        @change="handleChartConfigChange(moduleId)"
                      >
                        <el-option
                          v-for="meta in getChartableColumns(moduleId)"
                          :key="`${moduleId}-${meta.name}`"
                        :label="meta.label"
                        :value="meta.name"
                      />
                    </el-select>
                    <el-select
                      v-model="moduleStates[moduleId].chartType"
                      size="small"
                      class="analysis-chart-toolbar__select"
                      @change="handleChartConfigChange(moduleId)"
                    >
                      <el-option
                        v-for="type in getChartTypeOptions(moduleId)"
                        :key="`${moduleId}-${type}`"
                        :label="t(`promptTestResult.analysis.chartTypes.${type}`)"
                        :value="type"
                      />
                    </el-select>
                  </div>
                  <div class="analysis-chart" :ref="(el) => handleChartRef(moduleId, el)"></div>
                  </div>
                </template>
              </template>
              <el-empty
                v-else
                :description="t('promptTestResult.analysis.emptyCard')"
                class="analysis-empty-card"
              />
            </div>
            <el-empty v-else :description="t('promptTestResult.analysis.missingModule')" />
          </el-card>
        </div>
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
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { getPromptTestTask, listPromptTestUnits, listPromptTestExperiments } from '../api/promptTest'
import type { PromptTestTask } from '../types/promptTest'
import type { PromptTestResultUnit } from '../utils/promptTestResult'
import { buildPromptTestResultUnit, detectMissingOutput } from '../utils/promptTestResult'
import MarkdownIt from 'markdown-it'
import * as echarts from 'echarts'
import { listAnalysisModules, executeAnalysisModule } from '../api/analysis'
import type {
  AnalysisModuleDefinition,
  AnalysisResultPayload,
  AnalysisColumnMeta,
  AnalysisParameterSpec,
  AnalysisChartConfig,
  AnalysisUnitLink,
  AnalysisInsightDetail,
  AnalysisInsightUnitRef
} from '../types/analysis'

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

type AnalysisRunStatus = 'idle' | 'running' | 'success' | 'error'

interface AnalysisModuleState {
  definition: AnalysisModuleDefinition
  form: Record<string, unknown>
  status: AnalysisRunStatus
  result: AnalysisResultPayload | null
  errorMessage: string | null
  chartColumn: string | null
  chartType: string | null
  chartInstance: echarts.ECharts | null
  charts: AnalysisChartConfig[]
  unitLinks: AnalysisUnitLink[]
  unitLinkMapById: Map<string, AnalysisUnitLink>
  unitLinkMapByLabel: Map<string, AnalysisUnitLink>
  insightDetails: AnalysisInsightDetail[]
  autoTriggered: boolean
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

const analysisModules = ref<AnalysisModuleDefinition[]>([])
const analysisModulesLoading = ref(false)
const selectedAnalysisModules = ref<string[]>([])
const moduleStates = reactive<Record<string, AnalysisModuleState>>({})
const autoSelectedModuleIds = ref<string[]>([])
const chartRefs = new Map<string, HTMLElement | null>()
const prebuiltChartInstances = new Map<string, Map<string, echarts.ECharts>>()
let analysisSelectionInitialized = false

function buildDefaultAnalysisForm(definition: AnalysisModuleDefinition): Record<string, unknown> {
  const form: Record<string, unknown> = {}
  definition.parameters.forEach((param) => {
    if (param.default !== undefined && param.default !== null) {
      form[param.key] = param.default
    } else if (param.type === 'select' && Array.isArray(param.options) && param.options.length) {
      form[param.key] = param.options[0]
    } else if (param.type === 'number') {
      form[param.key] = null
    } else {
      form[param.key] = ''
    }
  })
  return form
}

function ensureModuleState(definition: AnalysisModuleDefinition) {
  const existing = moduleStates[definition.module_id]
  if (existing) {
    existing.definition = definition
    const defaults = buildDefaultAnalysisForm(definition)
    const validKeys = new Set(definition.parameters.map((param) => param.key))
    Object.keys(existing.form).forEach((key) => {
      if (!validKeys.has(key)) {
        delete existing.form[key]
      }
    })
    definition.parameters.forEach((param) => {
      if (!(param.key in existing.form)) {
        existing.form[param.key] = defaults[param.key]
      }
    })
    if (!Array.isArray(existing.charts)) {
      existing.charts = []
    }
    if (!Array.isArray(existing.unitLinks)) {
      existing.unitLinks = []
    }
    if (!(existing.unitLinkMapById instanceof Map)) {
      existing.unitLinkMapById = new Map()
    } else {
      existing.unitLinkMapById.clear()
    }
    if (!(existing.unitLinkMapByLabel instanceof Map)) {
      existing.unitLinkMapByLabel = new Map()
    } else {
      existing.unitLinkMapByLabel.clear()
    }
    if (!Array.isArray(existing.insightDetails)) {
      existing.insightDetails = []
    }
    return
  }
  moduleStates[definition.module_id] = {
    definition,
    form: buildDefaultAnalysisForm(definition),
    status: 'idle',
    result: null,
    errorMessage: null,
    chartColumn: null,
    chartType: null,
    chartInstance: null,
    charts: [],
    unitLinks: [],
    unitLinkMapById: new Map(),
    unitLinkMapByLabel: new Map(),
    insightDetails: [],
    autoTriggered: false
  }
}

function getModuleState(moduleId: string): AnalysisModuleState | null {
  return moduleStates[moduleId] ?? null
}

function extractConfiguredAnalysisModules(
  config: Record<string, unknown> | null | undefined
): string[] {
  if (!config || typeof config !== 'object') return []
  const modules = (config as Record<string, unknown>).analysis_modules
  if (!Array.isArray(modules)) return []
  return modules
    .map((item) => (typeof item === 'string' && item.trim() ? item.trim() : null))
    .filter((item): item is string => Boolean(item))
}

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

const configuredModuleIds = computed(() =>
  extractConfiguredAnalysisModules(task.value?.config as Record<string, unknown> | null)
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

watch(
  () => task.value?.id,
  () => {
    analysisSelectionInitialized = false
    selectedAnalysisModules.value = []
    Object.keys(moduleStates).forEach((moduleId) => {
      const state = moduleStates[moduleId]
      state.status = 'idle'
      state.result = null
      state.errorMessage = null
      state.chartColumn = null
      state.chartType = null
      state.charts = []
      state.unitLinks = []
      state.unitLinkMapById.clear()
      state.unitLinkMapByLabel.clear()
      state.insightDetails = []
      state.autoTriggered = false
      disposeModuleChart(moduleId)
    })
  }
)

watch(
  [analysisModules, configuredModuleIds],
  ([modules, configured]) => {
    const validIds = new Set<string>()
    modules.forEach((module) => {
      ensureModuleState(module)
      validIds.add(module.module_id)
    })
    autoSelectedModuleIds.value = configured.filter((id) => validIds.has(id))
    if (selectedAnalysisModules.value.some((id) => !validIds.has(id))) {
      selectedAnalysisModules.value = selectedAnalysisModules.value.filter((id) =>
        validIds.has(id)
      )
    }
    if (!analysisSelectionInitialized && modules.length) {
      const defaults = selectedAnalysisModules.value.length
        ? selectedAnalysisModules.value
        : autoSelectedModuleIds.value.length
        ? [...autoSelectedModuleIds.value]
        : [modules[0].module_id]
      selectedAnalysisModules.value = defaults
      analysisSelectionInitialized = true
    }
  },
  { immediate: true }
)

watch(
  selectedAnalysisModules,
  (ids, previous) => {
    ids.forEach((id) => {
      const state = getModuleState(id)
      if (!state) return
      if (
        autoSelectedModuleIds.value.includes(id) &&
        state.status === 'idle' &&
        !state.autoTriggered
      ) {
        state.autoTriggered = true
        void runAnalysisModule(id)
      }
    })
    previous.forEach((id) => {
      if (!ids.includes(id)) {
        disposeModuleChart(id)
      }
    })
  }
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

function getChartableColumns(moduleId: string): AnalysisColumnMeta[] {
  const state = getModuleState(moduleId)
  if (!state?.result) return []
  return state.result.columns_meta.filter(
    (meta) => Array.isArray(meta.visualizable) && meta.visualizable.length > 0
  )
}

function getPrebuiltCharts(moduleId: string): AnalysisChartConfig[] {
  const state = getModuleState(moduleId)
  if (!state || !Array.isArray(state.charts)) {
    return []
  }
  return state.charts
}

function disposeModuleChart(moduleId: string) {
  const state = getModuleState(moduleId)
  if (!state) return
  if (state.chartInstance) {
    state.chartInstance.dispose()
    state.chartInstance = null
  }
  const chartMap = prebuiltChartInstances.get(moduleId)
  if (chartMap) {
    chartMap.forEach((instance) => {
      instance.dispose()
    })
    prebuiltChartInstances.delete(moduleId)
  }
  chartRefs.delete(moduleId)
}

function resolveDimensionColumn(state: AnalysisModuleState): AnalysisColumnMeta | null {
  if (!state.result || !state.result.columns_meta.length) {
    return null
  }
  const primary = state.result.columns_meta[0]
  if (primary.name === state.chartColumn && state.result.columns_meta.length > 1) {
    return state.result.columns_meta[1]
  }
  return primary
}

function renderModuleChart(moduleId: string) {
  const state = getModuleState(moduleId)
  if (!state?.result) {
    disposeModuleChart(moduleId)
    return
  }
  if (state.charts.length) {
    return
  }
  const chartable = getChartableColumns(moduleId)
  if (!chartable.length) {
    disposeModuleChart(moduleId)
    return
  }

  if (!state.chartColumn || !chartable.some((meta) => meta.name === state.chartColumn)) {
    state.chartColumn = chartable[0].name
  }
  const currentColumn = state.chartColumn
  const columnMeta = chartable.find((meta) => meta.name === currentColumn)
  const chartTypes = columnMeta?.visualizable ?? []
  if (!state.chartType || !chartTypes.includes(state.chartType)) {
    state.chartType = chartTypes[0] ?? 'bar'
  }
  const chartType = state.chartType
  const container = chartRefs.get(moduleId)
  if (!container) {
    return
  }
  if (!state.chartInstance) {
    state.chartInstance = echarts.init(container)
  }

  const dimensionMeta = resolveDimensionColumn(state)
  const dimensionKey = dimensionMeta?.name ?? currentColumn

  const categories: string[] = []
  const values: number[] = []

  state.result.data.forEach((row) => {
    const rawCategory = row[dimensionKey]
    const rawValue = row[currentColumn]
    const category = rawCategory === null || rawCategory === undefined ? '' : String(rawCategory)
    const numeric = typeof rawValue === 'number' ? rawValue : Number(rawValue)
    if (!category || Number.isNaN(numeric) || !Number.isFinite(numeric)) {
      return
    }
    categories.push(category)
    values.push(numeric)
  })

  if (!categories.length) {
    state.chartInstance.clear()
    return
  }

  let option: echarts.EChartsOption
  if (chartType === 'pie') {
    option = {
      tooltip: { trigger: 'item' },
      legend: { orient: 'horizontal', top: 0 },
      series: [
        {
          type: 'pie',
          radius: '65%',
          center: ['50%', '60%'],
          data: categories.map((name, index) => ({ name, value: values[index] })),
          label: { formatter: '{b}: {c}' }
        }
      ]
    }
  } else {
    option = {
      tooltip: { trigger: 'axis' },
      xAxis: {
        type: 'category',
        data: categories,
        axisLabel: { interval: 0 }
      },
      yAxis: { type: 'value' },
      series: [
        {
          type: chartType === 'line' ? 'line' : 'bar',
          data: values,
          smooth: chartType === 'line',
          name: columnMeta?.label ?? currentColumn,
          areaStyle: chartType === 'line' ? {} : undefined
        }
      ]
    }
  }

  state.chartInstance.setOption(option)
  state.chartInstance.resize()
}

function getUnitDisplayLabel(moduleId: string, unit: AnalysisInsightUnitRef): string {
  const state = getModuleState(moduleId)
  if (!state) return unit.label || unit.unit_name
  return (
    state.unitLinkMapByLabel.get(unit.label)?.label ||
    (unit.unit_id != null ? state.unitLinkMapById.get(String(unit.unit_id))?.label : undefined) ||
    unit.label ||
    unit.unit_name
  )
}

function handleUnitChipClick(unitId: number | string | null) {
  if (unitId === null || unitId === undefined) return
  const numeric = Number(unitId)
  if (Number.isFinite(numeric) && numeric > 0) {
    openUnitDetail(numeric)
  }
}

function formatMetricValue(value: unknown): string {
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return '-'
  const absValue = Math.abs(numeric)
  const fractionDigits = absValue >= 100 ? 0 : absValue >= 10 ? 1 : 2
  return numeric.toLocaleString(locale.value, {
    minimumFractionDigits: 0,
    maximumFractionDigits: fractionDigits
  })
}

function handlePrebuiltChartRef(
  moduleId: string,
  chart: AnalysisChartConfig,
  el: HTMLElement | null
) {
  const chartId = chart.id
  if (!el) {
    const chartMap = prebuiltChartInstances.get(moduleId)
    if (chartMap) {
      const instance = chartMap.get(chartId)
      if (instance) {
        instance.dispose()
      }
      chartMap.delete(chartId)
      if (chartMap.size === 0) {
        prebuiltChartInstances.delete(moduleId)
      }
    }
    return
  }

  let chartMap = prebuiltChartInstances.get(moduleId)
  if (!chartMap) {
    chartMap = new Map<string, echarts.ECharts>()
    prebuiltChartInstances.set(moduleId, chartMap)
  }

  let instance = chartMap.get(chartId)
  if (!instance) {
    instance = echarts.init(el)
    chartMap.set(chartId, instance)
  }

  const finalOption = JSON.parse(JSON.stringify(chart.option ?? {}))
  const state = getModuleState(moduleId)
  if (state) {
    finalOption.tooltip = finalOption.tooltip || {}
    const originalFormatter = finalOption.tooltip.formatter
    finalOption.tooltip.axisPointer = finalOption.tooltip.axisPointer || { type: 'shadow' }
    finalOption.tooltip.formatter = (params: any) => {
      if (typeof originalFormatter === 'function') {
        const formatted = originalFormatter(params)
        if (formatted !== undefined) return formatted
      }
      const items = Array.isArray(params) ? params : [params]
      if (!items.length) return ''
      const axisLabel = String(items[0]?.axisValue ?? items[0]?.name ?? '')
      const link = state.unitLinkMapByLabel.get(axisLabel) || state.unitLinkMapById.get(axisLabel)
      const header = link ? `${link.label} · ${link.unit_name}` : axisLabel
      const lines = items.map((item: any) => {
        const seriesName = item.seriesName ? `${item.seriesName}: ` : ''
        const value = Array.isArray(item.value) ? item.value[0] : item.value
        return `${item.marker}${seriesName}${formatMetricValue(value)}`
      })
      return [header, ...lines].join('<br/>')
    }
  }

  instance.setOption(finalOption as echarts.EChartsOption, true)
  instance.resize()
}

function handleChartRef(moduleId: string, el: HTMLElement | null) {
  if (!el) {
    disposeModuleChart(moduleId)
    return
  }
  chartRefs.set(moduleId, el)
  void nextTick(() => renderModuleChart(moduleId))
}

function handleChartConfigChange(moduleId: string) {
  void nextTick(() => renderModuleChart(moduleId))
}

function getChartTypeOptions(moduleId: string): string[] {
  const state = getModuleState(moduleId)
  if (!state?.result || state.charts.length) return []
  const column = state.chartColumn
  if (column) {
    const meta = state.result.columns_meta.find((item) => item.name === column)
    if (meta && Array.isArray(meta.visualizable) && meta.visualizable.length) {
      return meta.visualizable
    }
  }
  const chartable = getChartableColumns(moduleId)
  if (!chartable.length) {
    return []
  }
  return chartable[0].visualizable ?? []
}

function mapParameterValue(spec: AnalysisParameterSpec, value: unknown): unknown {
  if (spec.type === 'number') {
    if (typeof value === 'number') {
      return value
    }
    const numeric = Number(value)
    if (!Number.isFinite(numeric)) {
      throw new Error(
        spec.label
          ? t('promptTestResult.analysis.messages.numberInvalid', { field: spec.label })
          : t('promptTestResult.analysis.messages.numberInvalidSimple')
      )
    }
    return numeric
  }
  if (spec.type === 'select' && Array.isArray(spec.options) && spec.options.length) {
    if (!spec.options.includes(value)) {
      throw new Error(
        spec.label
          ? t('promptTestResult.analysis.messages.selectInvalid', { field: spec.label })
          : t('promptTestResult.analysis.messages.selectInvalidSimple')
      )
    }
    return value
  }
  if (value === undefined || value === null) {
    return ''
  }
  return value
}

function prepareModuleParameters(moduleId: string): Record<string, unknown> | null {
  const state = getModuleState(moduleId)
  if (!state) return null
  const params: Record<string, unknown> = {}
  for (const spec of state.definition.parameters) {
    const rawValue = state.form[spec.key]
    if (rawValue === undefined || rawValue === null || rawValue === '') {
      if (spec.required) {
        ElMessage.warning(
          spec.label
            ? t('promptTestResult.analysis.messages.paramRequired', { field: spec.label })
            : t('promptTestResult.analysis.messages.paramRequiredSimple')
        )
        return null
      }
      continue
    }
    try {
      params[spec.key] = mapParameterValue(spec, rawValue)
    } catch (error: any) {
      ElMessage.warning(error?.message ?? t('promptTestResult.analysis.messages.paramInvalid'))
      return null
    }
  }
  return params
}

async function runAnalysisModule(moduleId: string) {
  const state = getModuleState(moduleId)
  if (!state || !task.value) return
  if (state.status === 'running') return
  const parameters = prepareModuleParameters(moduleId)
  if (parameters === null) {
    return
  }
  state.status = 'running'
  state.errorMessage = null
  try {
    disposeModuleChart(moduleId)
    const result = await executeAnalysisModule({
      module_id: moduleId,
      task_id: String(task.value.id),
      target_type: 'prompt_test_task',
      parameters
    })
    state.result = result
    state.status = 'success'
    state.autoTriggered = true
    state.errorMessage = null
    const chartsRaw = Array.isArray(result.extra?.charts)
      ? (result.extra?.charts as AnalysisChartConfig[])
      : []
    state.charts = chartsRaw.map((chart, index) => ({
      id: chart.id || `chart-${index}`,
      title: chart.title ?? '',
      description: chart.description ?? '',
      option: JSON.parse(JSON.stringify(chart.option ?? {})),
      meta: chart.meta ? JSON.parse(JSON.stringify(chart.meta)) : undefined
    })) as AnalysisChartConfig[]

    const unitLinksRaw = Array.isArray(result.extra?.unit_links)
      ? (result.extra?.unit_links as AnalysisUnitLink[])
      : []
    state.unitLinks = unitLinksRaw
    state.unitLinkMapById.clear()
    state.unitLinkMapByLabel.clear()
    unitLinksRaw.forEach((link) => {
      state.unitLinkMapByLabel.set(link.label, link)
      if (link.unit_id !== null && link.unit_id !== undefined) {
        state.unitLinkMapById.set(String(link.unit_id), link)
      }
    })

    state.insightDetails = Array.isArray(result.extra?.insight_details)
      ? (result.extra?.insight_details as AnalysisInsightDetail[])
      : []

    if (state.charts.length === 0) {
      state.chartColumn = null
      state.chartType = null
      const chartable = getChartableColumns(moduleId)
      if (chartable.length) {
        state.chartColumn = chartable[0].name
        state.chartType = chartable[0].visualizable[0] ?? 'bar'
      }
    }

    await nextTick()
    if (state.charts.length === 0) {
      renderModuleChart(moduleId)
    }
    ElMessage.success(t('promptTestResult.analysis.messages.runSuccess'))
  } catch (error: any) {
    state.status = 'error'
    state.errorMessage =
      error?.message ?? t('promptTestResult.analysis.messages.runFailed')
    state.result = null
    disposeModuleChart(moduleId)
    ElMessage.error(state.errorMessage)
  }
}

const runningSelected = ref(false)

async function runSelectedModules() {
  if (!selectedAnalysisModules.value.length) return
  runningSelected.value = true
  try {
    for (const moduleId of selectedAnalysisModules.value) {
      await runAnalysisModule(moduleId)
    }
  } finally {
    runningSelected.value = false
  }
}

function formatAnalysisCell(value: unknown): string {
  if (value === null || value === undefined) return '-'
  if (typeof value === 'number') {
    return Number.isFinite(value) ? value.toString() : '-'
  }
  if (typeof value === 'object') {
    try {
      return JSON.stringify(value)
    } catch (error) {
      return String(value)
    }
  }
  return String(value)
}

function handleWindowResize() {
  Object.values(moduleStates).forEach((state) => {
    state.chartInstance?.resize()
  })
  prebuiltChartInstances.forEach((chartMap) => {
    chartMap.forEach((instance) => instance.resize())
  })
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

async function fetchAnalysisModulesList() {
  analysisModulesLoading.value = true
  try {
    analysisModules.value = await listAnalysisModules()
  } catch (error) {
    console.error('加载分析模块失败', error)
    ElMessage.error(t('promptTestResult.analysis.messages.loadFailed'))
  } finally {
    analysisModulesLoading.value = false
  }
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
  window.addEventListener('resize', handleWindowResize)
  void Promise.all([refreshTask(), fetchAnalysisModulesList()])
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleWindowResize)
  Object.keys(moduleStates).forEach((moduleId) => disposeModuleChart(moduleId))
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
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 24px 0;
}

.analysis-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
}

.analysis-toolbar__selector {
  flex: 1;
  min-width: 260px;
}

.analysis-empty {
  padding: 40px 0;
}

.analysis-modules-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 16px;
}

.analysis-module-card {
  display: flex;
  flex-direction: column;
}

.analysis-module-card__header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.analysis-module-card__title {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.analysis-module-card__title h4 {
  margin: 0;
  font-size: 16px;
}

.analysis-module-card__desc {
  margin: 0;
  font-size: 13px;
  color: var(--text-weak-color);
}

.analysis-module-card__actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.analysis-module-card__body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.analysis-prebuilt-charts {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.analysis-prebuilt-chart__header {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.analysis-prebuilt-chart__header h5 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
}

.analysis-prebuilt-chart__desc {
  margin: 0;
  font-size: 12px;
  color: var(--text-weak-color);
}

.analysis-option {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.analysis-option__title {
  font-weight: 600;
}

.analysis-option__desc {
  font-size: 12px;
  color: var(--text-weak-color);
  white-space: normal;
}

.analysis-params__form {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
}

.analysis-param-item {
  margin-bottom: 0;
}

.analysis-param-input {
  width: 100%;
}

.analysis-param-tip {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--text-weak-color);
}

.analysis-alert {
  margin-bottom: 8px;
}

.analysis-insight-list {
  margin: 0;
  padding-left: 18px;
}

.analysis-insight-list li {
  margin-bottom: 4px;
}

.analysis-unit-chip {
  display: inline-flex;
  align-items: center;
  padding: 0 8px;
  height: 22px;
  border-radius: 12px;
  background-color: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
  font-weight: 600;
  font-size: 12px;
  cursor: pointer;
  border: 1px solid var(--el-color-primary-light-7);
  transition: background-color 0.2s ease, color 0.2s ease, border-color 0.2s ease;
  white-space: nowrap;
}

.analysis-unit-chip:hover {
  background-color: var(--el-color-primary-light-7);
  border-color: var(--el-color-primary-light-5);
  color: var(--el-color-primary-dark-2);
}

.analysis-loading {
  padding: 16px 0;
}

.analysis-empty-card {
  padding: 24px 0;
}

.analysis-chart-block {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.analysis-chart-toolbar {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.analysis-chart-toolbar__select {
  min-width: 180px;
}

.analysis-chart {
  width: 100%;
  height: 280px;
}

.analysis-empty-card :deep(.el-empty__description) {
  font-size: 13px;
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
