<template>
  <div class="prompt-test-create-page">
    <el-breadcrumb separator="/" class="page-breadcrumb">
      <el-breadcrumb-item>
        <span class="breadcrumb-link" @click="goTestManagement">{{ t('menu.testJob') }}</span>
      </el-breadcrumb-item>
      <el-breadcrumb-item>{{ t('promptTestCreate.breadcrumb.current') }}</el-breadcrumb-item>
    </el-breadcrumb>

    <section class="page-header">
      <div class="page-header__text">
        <h2>{{ t('promptTestCreate.headerTitle') }}</h2>
        <p class="page-desc">{{ t('promptTestCreate.headerDescription') }}</p>
      </div>
    </section>

    <el-card class="form-card" v-loading="retryPrefillLoading">
      <template #header>
        <div class="card-header">
          <div>
            <h3>{{ t('promptTestCreate.card.title') }}</h3>
            <p class="card-subtitle">{{ t('promptTestCreate.card.subtitle') }}</p>
          </div>
          <div class="card-header__action">
            <el-switch
              v-model="taskForm.autoExecute"
              :active-text="t('promptTestCreate.form.autoExecute')"
            />
          </div>
        </div>
      </template>

      <el-form label-width="140px" class="task-form">
        <section class="form-section">
          <h4 class="section-title">{{ t('promptTestCreate.form.sections.task') }}</h4>
          <el-form-item :label="t('promptTestCreate.form.fields.taskName')" required>
            <el-input
              v-model="taskForm.name"
              :placeholder="t('promptTestCreate.form.placeholders.taskName')"
              maxlength="80"
              show-word-limit
            />
          </el-form-item>
          <el-form-item :label="t('promptTestCreate.form.fields.taskDescription')">
            <el-input
              v-model="taskForm.description"
              type="textarea"
              :rows="3"
              :placeholder="t('promptTestCreate.form.placeholders.taskDescription')"
            />
          </el-form-item>
          <el-form-item :label="t('promptTestCreate.form.fields.prompt')" required>
            <el-select
              v-model="taskForm.promptId"
              filterable
              :loading="promptLoading"
              :placeholder="t('promptTestCreate.form.placeholders.prompt')"
            >
              <el-option
                v-for="prompt in promptOptions"
                :key="prompt.id"
                :label="prompt.name"
                :value="prompt.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item :label="t('promptTestCreate.form.fields.promptVersions')" required>
            <el-select
              v-model="taskForm.promptVersionIds"
              multiple
              collapse-tags
              :disabled="!versionOptions.length"
              :placeholder="t('promptTestCreate.form.placeholders.promptVersions')"
            >
              <el-option
                v-for="option in versionOptions"
                :key="option.id"
                :label="option.label"
                :value="option.id"
              />
            </el-select>
            <p v-if="!versionOptions.length && taskForm.promptId" class="form-tip">
              {{ t('promptTestCreate.form.tips.noVersions') }}
            </p>
          </el-form-item>
        </section>

        <el-divider />

        <section class="form-section">
          <h4 class="section-title">{{ t('promptTestCreate.form.sections.unit') }}</h4>
          <el-form-item :label="t('promptTestCreate.form.fields.baseUnitName')">
            <el-input
              v-model="unitForm.baseName"
              :placeholder="t('promptTestCreate.form.placeholders.baseUnitName')"
            />
            <p class="form-tip">
              {{ t('promptTestCreate.form.tips.baseUnitName') }}
            </p>
          </el-form-item>
          <el-form-item :label="t('promptTestCreate.form.fields.models')" required>
            <el-select
              v-model="unitForm.selectedModels"
              multiple
              filterable
              collapse-tags
              :loading="providerLoading"
              :placeholder="t('promptTestCreate.form.placeholders.models')"
            >
              <el-option-group
                v-for="group in modelOptionGroups"
                :key="group.providerId"
                :label="group.label"
              >
                <el-option
                  v-for="option in group.options"
                  :key="option.value"
                  :label="option.label"
                  :value="option.value"
                />
              </el-option-group>
            </el-select>
            <p v-if="!providerLoading && !modelOptionGroups.length" class="form-tip">
              {{ t('promptTestCreate.form.tips.noModels') }}
            </p>
          </el-form-item>
          <el-form-item :label="t('promptTestCreate.form.fields.rounds')" required>
            <el-input-number
              v-model="unitForm.rounds"
              :min="1"
              :max="200"
              :step="1"
            />
            <p class="form-tip">
              {{ t('promptTestCreate.form.tips.rounds') }}
            </p>
          </el-form-item>
          <p v-if="combinationCount > 0" class="combination-summary">
            {{ t('promptTestCreate.form.tips.combinationCount', { count: combinationCount }) }}
          </p>
        </section>

        <el-divider />

        <section class="form-section">
          <h4 class="section-title">{{ t('promptTestCreate.form.sections.parameterSets') }}</h4>
          <div class="parameter-set-list">
            <el-card
              v-for="(set, index) in parameterSets"
              :key="set.id"
              class="parameter-set-card"
            >
              <div class="parameter-set-card__header">
                <span class="parameter-set-card__title">
                  {{ set.label.trim() || defaultParameterSetLabel(index) }}
                </span>
                <el-button
                  v-if="parameterSets.length > 1"
                  type="danger"
                  text
                  size="small"
                  @click="removeParameterSet(set.id)"
                >
                  {{ t('promptTestCreate.form.actions.removeParameterSet') }}
                </el-button>
              </div>
              <div class="parameter-set-grid">
                <el-form-item label-position="top" :label="t('promptTestCreate.form.fields.parameterSetName')">
                  <el-input
                    v-model="set.label"
                    :placeholder="t('promptTestCreate.form.placeholders.parameterSetName', { index: index + 1 })"
                  />
                </el-form-item>
                <el-form-item label-position="top" :label="t('promptTestCreate.form.fields.temperature')">
                  <div class="inline-control">
                    <el-slider
                      v-model="set.temperature"
                      :min="0"
                      :max="2"
                      :step="0.01"
                    />
                    <el-input-number
                      v-model="set.temperature"
                      :min="0"
                      :max="2"
                      :step="0.1"
                      :precision="2"
                    />
                  </div>
                </el-form-item>
                <el-form-item label-position="top" :label="t('promptTestCreate.form.fields.topP')">
                  <el-input-number
                    v-model="set.topP"
                    :min="0"
                    :max="1"
                    :step="0.05"
                    :precision="2"
                    :value-on-clear="null"
                  />
                </el-form-item>
                <el-form-item label-position="top" :label="t('promptTestCreate.form.fields.extraParameters')">
                  <el-input
                    v-model="set.parametersJson"
                    type="textarea"
                    :rows="4"
                    :placeholder="t('promptTestCreate.form.placeholders.extraParameters')"
                  />
                </el-form-item>
              </div>
            </el-card>
          </div>
          <el-button class="add-parameter-set" type="primary" link @click="addParameterSet">
            {{ t('promptTestCreate.form.actions.addParameterSet') }}
          </el-button>
        </section>

        <el-divider />

        <section class="form-section">
          <h4 class="section-title">{{ t('promptTestCreate.form.sections.analysis') }}</h4>
          <el-form-item :label="t('promptTestCreate.form.fields.analysisModules')">
            <el-select
              v-model="taskForm.analysisModules"
              multiple
              filterable
              collapse-tags
              :loading="analysisModuleLoading"
              :placeholder="t('promptTestCreate.form.placeholders.analysisModules')"
            >
              <el-option
                v-for="module in analysisModuleOptions"
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
            <p class="form-tip">
              {{ t('promptTestCreate.form.tips.analysisModules') }}
            </p>
          </el-form-item>
        </section>

        <el-divider />

        <section class="form-section">
          <div class="section-title-row">
            <h4 class="section-title">{{ t('promptTestCreate.form.sections.dataset') }}</h4>
            <el-tooltip :content="datasetTooltip" placement="top">
              <el-button
                class="section-help-button"
                :icon="QuestionFilled"
                circle
                size="small"
                text
                :aria-label="datasetTooltip"
              />
            </el-tooltip>
          </div>
          <div class="variables-mode">
            <el-radio-group v-model="unitForm.variableInputMode" size="small">
              <el-radio-button label="textarea">
                {{ t('promptTestCreate.form.actions.inputManual') }}
              </el-radio-button>
              <el-radio-button label="csv">
                {{ t('promptTestCreate.form.actions.inputCsv') }}
              </el-radio-button>
            </el-radio-group>
            <span v-if="unitForm.csvFileName" class="csv-file-name">
              {{ unitForm.csvFileName }}
            </span>
          </div>
          <div v-if="unitForm.variableInputMode === 'textarea'" class="variables-editor">
            <el-input
              v-model="unitForm.variablesText"
              type="textarea"
              :rows="6"
              :placeholder="t('promptTestCreate.form.placeholders.inputSamples')"
            />
            <div class="variables-toolbar">
              <el-button size="small" type="primary" @click="handleParseVariablesText">
                {{ t('promptTestCreate.form.actions.parseVariables') }}
              </el-button>
              <el-button size="small" @click="clearVariables">
                {{ t('promptTestCreate.form.actions.clearVariables') }}
              </el-button>
            </div>
          </div>
          <div v-else class="variables-editor">
            <el-button size="small" type="primary" @click="triggerCsvUpload">
              {{ t('promptTestCreate.form.actions.uploadCsv') }}
            </el-button>
            <input
              ref="csvInputRef"
              type="file"
              accept=".csv,.txt"
              class="hidden-file-input"
              @change="handleCsvFileChange"
            />
            <p class="form-tip">
              {{ t('promptTestCreate.form.tips.csvFormat') }}
            </p>
          </div>
          <div class="variables-preview-wrapper">
            <el-table
              v-if="unitForm.variablesPreview.length"
              :data="unitForm.variablesPreview"
              size="small"
              class="variables-preview"
              max-height="240"
              border
            >
              <el-table-column
                v-for="header in previewHeaders"
                :key="header"
                :prop="header"
                :label="header"
                show-overflow-tooltip
              />
            </el-table>
            <p v-else class="form-tip">
              {{ t('promptTestCreate.form.tips.noSamples') }}
            </p>
            <p v-if="variablesCount" class="form-tip">
              {{ t('promptTestCreate.form.tips.variableCount', { count: variablesCount }) }}
            </p>
          </div>
        </section>

        <el-divider />

        <el-form-item>
          <el-button type="primary" :loading="submitting || retryPrefillLoading" @click="handleSubmit">
            {{ t('promptTestCreate.form.submit') }}
          </el-button>
          <el-button @click="goTestManagement">
            {{ t('promptTestCreate.form.cancel') }}
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { QuestionFilled } from '@element-plus/icons-vue'
import { listPrompts, getPrompt } from '../api/prompt'
import { listLLMProviders } from '../api/llmProvider'
import { listAnalysisModules } from '../api/analysis'
import { createPromptTestTask, getPromptTestTask, listPromptTestUnits } from '../api/promptTest'
import type { Prompt } from '../types/prompt'
import type { AnalysisModuleDefinition } from '../types/analysis'
import type { LLMProvider } from '../types/llm'
import type { PromptTestTask, PromptTestUnit } from '../types/promptTest'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()

interface ModelOption {
  value: string
  label: string
  providerId: number
  providerName: string
  modelId: number
  modelName: string
}

interface ModelOptionGroup {
  providerId: number
  label: string
  options: ModelOption[]
}

interface VersionOption {
  id: number
  promptId: number
  promptName: string
  version: string
  label: string
  updatedAt: string
}

interface ParameterSet {
  id: number
  label: string
  temperature: number
  topP: number | null
  parametersJson: string
}

interface ModelInfo {
  providerId: number
  providerName: string
  modelId: number
  modelName: string
}

interface UnitDraft {
  name: string
  description: string | null
  model_name: string
  llm_provider_id: number
  temperature: number
  top_p: number | null
  rounds: number
  prompt_version_id: number
  prompt_template: string | null
  variables: Record<string, unknown> | null
  parameters: Record<string, unknown> | null
  expectations: Record<string, unknown> | null
  tags: string[] | null
  extra: Record<string, unknown> | null
}

interface ParameterSetSource {
  label: string
  temperature: number
  top_p: number | null
  parameters: Record<string, unknown> | null
}

const taskForm = reactive({
  name: '',
  description: '',
  promptId: null as number | null,
  promptVersionIds: [] as number[],
  autoExecute: true,
  analysisModules: [] as string[]
})

const unitForm = reactive({
  baseName: '',
  selectedModels: [] as string[],
  rounds: 3,
  variableInputMode: 'textarea' as 'textarea' | 'csv',
  variablesText: '',
  csvFileName: '',
  variableHeaders: [] as string[],
  variablesPreview: [] as Array<Record<string, string>>
})

const promptLoading = ref(false)
const providerLoading = ref(false)
const submitting = ref(false)

const promptOptions = ref<Prompt[]>([])
const selectedPrompt = ref<Prompt | null>(null)
const providers = ref<LLMProvider[]>([])
const csvInputRef = ref<HTMLInputElement | null>(null)
const routePromptId = ref<number | null>(null)
const routeVersionIds = ref<number[]>([])
const analysisModuleOptions = ref<AnalysisModuleDefinition[]>([])
const analysisModuleLoading = ref(false)
const retryPrefillLoading = ref(false)
let lastAppliedRetryTaskId: number | null = null
let pendingRetryTaskId: number | null = null
let suppressPromptWatcher = false

let parameterSetUid = 1
const parameterSets = ref<ParameterSet[]>([createParameterSet()])

const versionOptions = computed<VersionOption[]>(() => {
  const prompt = selectedPrompt.value
  if (!prompt) return []
  return prompt.versions
    .map((version) => ({
      id: version.id,
      promptId: prompt.id,
      promptName: prompt.name,
      version: version.version,
      label: `${prompt.name} · ${version.version}`,
      updatedAt: version.updated_at
    }))
    .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt))
})

const versionOptionMap = computed<Map<number, VersionOption>>(() => {
  const map = new Map<number, VersionOption>()
  versionOptions.value.forEach((option) => map.set(option.id, option))
  return map
})

const selectedPromptVersions = computed<VersionOption[]>(() =>
  taskForm.promptVersionIds
    .map((id) => versionOptionMap.value.get(id))
    .filter((option): option is VersionOption => Boolean(option))
)

const modelOptionGroups = computed<ModelOptionGroup[]>(() => {
  if (!providers.value.length) return []
  return providers.value
    .filter((provider) => !provider.is_archived)
    .map((provider) => ({
      providerId: provider.id,
      label: provider.provider_name,
      options: provider.models.map((model) => ({
        value: `${provider.id}:${model.id}`,
        label: model.name,
        providerId: provider.id,
        providerName: provider.provider_name,
        modelId: model.id,
        modelName: model.name
      }))
    }))
    .filter((group) => group.options.length > 0)
})

const modelOptionMap = computed<Map<string, ModelInfo>>(() => {
  const map = new Map<string, ModelInfo>()
  modelOptionGroups.value.forEach((group) => {
    group.options.forEach((option) => {
      map.set(option.value, {
        providerId: option.providerId,
        providerName: option.providerName,
        modelId: option.modelId,
        modelName: option.modelName
      })
    })
  })
  return map
})

const selectedModelInfos = computed<ModelInfo[]>(() =>
  unitForm.selectedModels
    .map((key) => modelOptionMap.value.get(key))
    .filter((info): info is ModelInfo => Boolean(info))
)
const baseNameCustomized = ref(false)
let syncingBaseName = false

function applyBaseNameFromTaskName(source: string) {
  const next = source ? source.trim() : ''
  syncingBaseName = true
  unitForm.baseName = next
  syncingBaseName = false
}

const previewHeaders = computed(() => unitForm.variableHeaders)
const variablesCount = computed(() => unitForm.variablesPreview.length)
const combinationCount = computed(
  () =>
    selectedPromptVersions.value.length *
    selectedModelInfos.value.length *
    parameterSets.value.length
)
const effectiveRounds = computed(() => {
  const value = Number(unitForm.rounds)
  if (Number.isFinite(value) && value > 0) {
    return Math.max(1, Math.floor(value))
  }
  return 1
})
const totalDatasetRuns = computed(() =>
  variablesCount.value > 0
    ? variablesCount.value * effectiveRounds.value
    : effectiveRounds.value
)
const datasetTooltip = computed(() =>
  t('promptTestCreate.form.tips.datasetTooltip', {
    rows: variablesCount.value,
    rounds: effectiveRounds.value,
    total: totalDatasetRuns.value
  })
)

watch(
  () => unitForm.baseName,
  (value) => {
    if (syncingBaseName) return
    const normalized = value.trim()
    const source = (taskForm.name ?? '').trim()
    baseNameCustomized.value = normalized.length > 0 && normalized !== source
    if (!normalized.length) {
      baseNameCustomized.value = false
    }
  }
)

watch(
  () => taskForm.name,
  (value) => {
    if (baseNameCustomized.value) {
      return
    }
    applyBaseNameFromTaskName(value ?? '')
  }
)

async function loadPromptDetail(promptId: number | null) {
  selectedPrompt.value = null
  taskForm.promptVersionIds = []
  if (!promptId) {
    return
  }
  try {
    const detail = await getPrompt(promptId)
    selectedPrompt.value = detail
    const defaultVersionId =
      detail.current_version?.id ?? detail.versions[0]?.id ?? null
    const appliedFromRoute = applyRouteVersionDefaults()
    if (!appliedFromRoute && defaultVersionId !== null) {
      taskForm.promptVersionIds = [defaultVersionId]
    }
  } catch (error) {
    console.error('加载 Prompt 详情失败', error)
    ElMessage.error(t('promptTestCreate.messages.loadPromptFailed'))
    taskForm.promptId = null
  }
}

watch(
  () => taskForm.promptId,
  async (newId, oldId) => {
    if (newId === oldId) return
    if (suppressPromptWatcher) return
    await loadPromptDetail(newId ?? null)
  }
)

watch(
  versionOptions,
  (options) => {
    const validIds = new Set(options.map((option) => option.id))
    if (taskForm.promptVersionIds.some((id) => !validIds.has(id))) {
      taskForm.promptVersionIds = taskForm.promptVersionIds.filter((id) =>
        validIds.has(id)
      )
    }
  },
  { deep: true }
)

watch(
  analysisModuleOptions,
  (modules) => {
    const validIds = new Set(modules.map((module) => module.module_id))
    if (taskForm.analysisModules.some((id) => !validIds.has(id))) {
      taskForm.analysisModules = taskForm.analysisModules.filter((id) =>
        validIds.has(id)
      )
    }
  },
  { deep: true }
)

watch(
  providers,
  () => {
    const validKeys = new Set(modelOptionGroups.value.flatMap((group) =>
      group.options.map((option) => option.value)
    ))
    if (unitForm.selectedModels.some((key) => !validKeys.has(key))) {
      unitForm.selectedModels = unitForm.selectedModels.filter((key) =>
        validKeys.has(key)
      )
    }
  },
  { deep: true }
)

function normalizeRouteNumber(value: unknown): number | null {
  const raw = Array.isArray(value) ? value[0] : value
  if (raw === null || raw === undefined) {
    return null
  }
  if (typeof raw === 'number') {
    if (!Number.isFinite(raw)) {
      return null
    }
    const intValue = Math.trunc(raw)
    return intValue > 0 ? intValue : null
  }
  const text = String(raw).trim()
  if (!text) {
    return null
  }
  const numeric = Number(text)
  if (!Number.isFinite(numeric)) {
    return null
  }
  const intValue = Math.trunc(numeric)
  return intValue > 0 ? intValue : null
}

function normalizeRouteNumberList(value: unknown): number[] {
  const values: unknown[] =
    Array.isArray(value)
      ? value
      : typeof value === 'string'
      ? value.split(',').map((item) => item.trim())
      : value === null || value === undefined
      ? []
      : [value]
  const result: number[] = []
  values.forEach((item) => {
    const parsed = normalizeRouteNumber(item)
    if (parsed !== null) {
      result.push(parsed)
    }
  })
  return Array.from(new Set(result))
}

function toPositiveInteger(value: unknown): number | null {
  if (typeof value === 'number') {
    if (Number.isInteger(value) && value > 0) {
      return value
    }
    return null
  }
  if (typeof value === 'string') {
    const parsed = Number(value)
    return Number.isInteger(parsed) && parsed > 0 ? parsed : null
  }
  return null
}

function isPlainRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

function toRecord(value: unknown): Record<string, unknown> | null {
  return isPlainRecord(value) ? (value as Record<string, unknown>) : null
}

function extractStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return []
  return value
    .map((item) => (typeof item === 'string' ? item.trim() : null))
    .filter((item): item is string => Boolean(item && item.length))
}

function extractNumberArray(value: unknown): number[] {
  if (!Array.isArray(value)) return []
  return Array.from(
    new Set(
      value
        .map((item) => toPositiveInteger(item))
        .filter((item): item is number => item !== null)
    )
  )
}

function formatParametersJson(data: Record<string, unknown> | null | undefined): string {
  if (!data || Object.keys(data).length === 0) {
    return ''
  }
  try {
    return JSON.stringify(data, null, 2)
  } catch (error) {
    void error
    return ''
  }
}

function formatDisplayValue(value: unknown): string {
  if (value === null || value === undefined) return ''
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value)
  }
  try {
    return JSON.stringify(value)
  } catch (error) {
    void error
    return String(value)
  }
}

function applyRouteVersionDefaults(): boolean {
  const prompt = selectedPrompt.value
  if (!prompt) {
    return false
  }
  if (routePromptId.value === null || routePromptId.value !== prompt.id) {
    return false
  }
  if (!routeVersionIds.value.length) {
    return false
  }
  const validIds = routeVersionIds.value.filter((id) =>
    prompt.versions.some((version) => version.id === id)
  )
  if (!validIds.length) {
    return false
  }
  taskForm.promptVersionIds = validIds
  return true
}

function syncRoutePromptId() {
  const parsed = normalizeRouteNumber(route.query.promptId)
  routePromptId.value = parsed
  if (parsed !== null && parsed !== taskForm.promptId) {
    taskForm.promptId = parsed
  }
}

routeVersionIds.value = normalizeRouteNumberList(route.query.promptVersionIds)

watch(
  () => route.query.promptId,
  () => {
    syncRoutePromptId()
    if (routePromptId.value === taskForm.promptId) {
      applyRouteVersionDefaults()
    }
  }
)

watch(
  () => route.query.promptVersionIds,
  () => {
    routeVersionIds.value = normalizeRouteNumberList(route.query.promptVersionIds)
    if (routePromptId.value === taskForm.promptId) {
      applyRouteVersionDefaults()
    }
  }
)

syncRoutePromptId()

function syncRetryTaskIdFromRoute() {
  const parsed = normalizeRouteNumber(route.query.retryTaskId)
  if (parsed !== null) {
    void applyRetryTaskConfig(parsed)
  }
}

watch(
  () => route.query.retryTaskId,
  () => {
    syncRetryTaskIdFromRoute()
  }
)

syncRetryTaskIdFromRoute()

function createParameterSet(): ParameterSet {
  return {
    id: parameterSetUid++,
    label: '',
    temperature: 0.7,
    topP: 1.0,
    parametersJson: ''
  }
}

function defaultParameterSetLabel(index: number): string {
  return t('promptTestCreate.form.defaults.parameterSet', { index: index + 1 })
}

async function applyRetryTaskConfig(taskId: number) {
  if (taskId === lastAppliedRetryTaskId) return
  if (retryPrefillLoading.value && pendingRetryTaskId === taskId) return
  retryPrefillLoading.value = true
  pendingRetryTaskId = taskId
  try {
    const [taskData, unitList] = await Promise.all([
      getPromptTestTask(taskId),
      listPromptTestUnits(taskId)
    ])
    await hydrateFormFromTask(taskData, unitList)
    lastAppliedRetryTaskId = taskId
  } catch (error) {
    console.error('复制测试任务配置失败', error)
    ElMessage.error(t('promptTestCreate.messages.retryPrefillFailed'))
  } finally {
    retryPrefillLoading.value = false
    pendingRetryTaskId = null
  }
}

async function hydrateFormFromTask(taskData: PromptTestTask, unitList: PromptTestUnit[]) {
  const configRecord = toRecord(taskData.config) ?? {}
  const promptId = extractPromptIdFromConfig(configRecord)
  const versionIds = extractVersionIdsFromConfig(configRecord, unitList)
  routePromptId.value = promptId
  routeVersionIds.value = versionIds
  const normalizedTaskName = taskData.name.trim()
  taskForm.name = `${normalizedTaskName}-retry`
  taskForm.description = taskData.description ?? ''
  const autoExecuteConfig = configRecord['auto_execute']
  taskForm.autoExecute =
    typeof autoExecuteConfig === 'boolean' ? autoExecuteConfig : true
  const analysisModules = extractStringArray(configRecord['analysis_modules'])
  taskForm.analysisModules = [...analysisModules]

  suppressPromptWatcher = true
  taskForm.promptId = promptId
  suppressPromptWatcher = false

  await loadPromptDetail(promptId)
  if (promptId !== null) {
    applyPromptVersionsFromRetry(versionIds)
  } else {
    taskForm.promptVersionIds = []
  }

  unitForm.selectedModels = [...extractModelKeys(configRecord, unitList)]
  applyParameterSetSources(extractParameterSetSources(configRecord, unitList))
  unitForm.rounds = inferRoundsFromUnits(unitList)
  unitForm.baseName = inferBaseNameFromUnits(unitList, normalizedTaskName)
  applyVariablesFromUnits(configRecord, unitList)
}

function applyPromptVersionsFromRetry(versionIds: number[]) {
  const validIds = new Set(versionOptions.value.map((option) => option.id))
  const resolved = versionIds.filter((id) => validIds.has(id))
  if (resolved.length) {
    taskForm.promptVersionIds = resolved
    return
  }
  if (versionOptions.value.length) {
    taskForm.promptVersionIds = [versionOptions.value[0].id]
  } else {
    taskForm.promptVersionIds = []
  }
}

function extractPromptIdFromConfig(config: Record<string, unknown>): number | null {
  const direct = toPositiveInteger(config['prompt_id'])
  if (direct !== null) return direct
  const list = extractNumberArray(config['prompt_ids'])
  return list[0] ?? null
}

function extractVersionIdsFromConfig(
  config: Record<string, unknown>,
  units: PromptTestUnit[]
): number[] {
  const ids = extractNumberArray(config['prompt_version_ids'])
  if (ids.length) {
    return ids
  }
  const unitVersionIds = Array.from(
    new Set(
      units
        .map((unit) => toPositiveInteger(unit.prompt_version_id))
        .filter((id): id is number => id !== null)
    )
  )
  return unitVersionIds
}

function extractModelKeys(
  config: Record<string, unknown>,
  units: PromptTestUnit[]
): string[] {
  const keys = extractStringArray(config['model_keys'])
  if (keys.length) {
    return keys
  }
  const derived = new Set<string>()
  units.forEach((unit) => {
    const providerId = toPositiveInteger(unit.llm_provider_id)
    const extra = toRecord(unit.extra)
    const modelId = extra ? toPositiveInteger(extra.llm_model_id) : null
    if (providerId && modelId) {
      derived.add(`${providerId}:${modelId}`)
    }
  })
  return Array.from(derived)
}

function extractParameterSetSources(
  config: Record<string, unknown>,
  units: PromptTestUnit[]
): ParameterSetSource[] {
  const rawSets = Array.isArray(config['parameter_sets']) ? config['parameter_sets'] : []
  const normalized = rawSets
    .map((item) => {
      const record = toRecord(item)
      if (!record) return null
      const temperature =
        typeof record.temperature === 'number'
          ? record.temperature
          : Number(record.temperature)
      const topSource = record.top_p ?? record.topP
      const topValue =
        topSource === null || topSource === undefined ? null : Number(topSource)
      return {
        label: typeof record.label === 'string' ? record.label : '',
        temperature: Number.isFinite(temperature) ? Number(temperature) : 0.7,
        top_p: Number.isFinite(topValue) ? Number(topValue) : null,
        parameters: toRecord(record.parameters)
      } as ParameterSetSource
    })
    .filter((item): item is ParameterSetSource => Boolean(item))
  if (normalized.length) {
    return normalized
  }
  return deriveParameterSetsFromUnits(units)
}

function deriveParameterSetsFromUnits(units: PromptTestUnit[]): ParameterSetSource[] {
  const map = new Map<string, ParameterSetSource>()
  units.forEach((unit, index) => {
    const extra = toRecord(unit.extra)
    const rawLabel =
      typeof extra?.parameter_label === 'string'
        ? extra.parameter_label.trim()
        : ''
    const fallbackIndex =
      typeof extra?.parameter_index === 'number' ? extra.parameter_index : index + 1
    const label =
      rawLabel.length > 0
        ? rawLabel
        : t('promptTestCreate.form.defaults.parameterSet', { index: fallbackIndex })
    if (map.has(label)) {
      return
    }
    map.set(label, {
      label,
      temperature:
        typeof unit.temperature === 'number' && Number.isFinite(unit.temperature)
          ? unit.temperature
          : 0.7,
      top_p:
        typeof unit.top_p === 'number' && Number.isFinite(unit.top_p)
          ? unit.top_p
          : null,
      parameters: toRecord(unit.parameters)
    })
  })
  return Array.from(map.values())
}

function applyParameterSetSources(sources: ParameterSetSource[]) {
  if (!sources.length) {
    parameterSetUid = 1
    parameterSets.value = [createParameterSet()]
    return
  }
  let nextId = 1
  parameterSets.value = sources.map((source) => ({
    id: nextId++,
    label: source.label ?? '',
    temperature: Number.isFinite(source.temperature) ? source.temperature : 0.7,
    topP:
      typeof source.top_p === 'number' && Number.isFinite(source.top_p)
        ? source.top_p
        : null,
    parametersJson: formatParametersJson(source.parameters ?? null)
  }))
  parameterSetUid = nextId
}

function inferRoundsFromUnits(units: PromptTestUnit[]): number {
  const target = units.find(
    (unit) => typeof unit.rounds === 'number' && Number.isFinite(unit.rounds) && unit.rounds > 0
  )
  if (!target) {
    return Math.max(1, Math.floor(unitForm.rounds))
  }
  return Math.max(1, Math.floor(target.rounds))
}

function inferBaseNameFromUnits(units: PromptTestUnit[], fallback: string): string {
  const first = units[0]
  if (!first || typeof first.name !== 'string') {
    return fallback
  }
  const extra = toRecord(first.extra)
  const promptName =
    typeof extra?.prompt_name === 'string' ? extra.prompt_name.trim() : ''
  const promptVersion =
    typeof extra?.prompt_version === 'string' ? extra.prompt_version.trim() : ''
  const promptLabel = [promptName, promptVersion].filter(Boolean).join(' ').trim()
  const parameterLabel =
    typeof extra?.parameter_label === 'string' ? extra.parameter_label.trim() : ''
  const suffixParts = [promptLabel, first.model_name, parameterLabel].filter(
    (part) => typeof part === 'string' && part.length
  )
  if (!suffixParts.length) {
    return fallback
  }
  const suffix = suffixParts.join(' / ')
  if (first.name.endsWith(suffix)) {
    const base = first.name.slice(0, first.name.length - suffix.length).replace(/\s*\/\s*$/, '')
    const trimmed = base.trim()
    return trimmed || fallback
  }
  return fallback
}

function applyVariablesFromUnits(
  config: Record<string, unknown>,
  units: PromptTestUnit[]
) {
  const rows = extractVariableRows(units)
  if (!rows.length) {
    unitForm.variableHeaders = []
    unitForm.variablesPreview = []
    unitForm.variablesText = ''
    unitForm.variableInputMode = 'textarea'
    unitForm.csvFileName = ''
    return
  }
  const headers = extractStringArray(config['variable_headers'])
  const headerSet = new Set(headers)
  rows.forEach((row) => {
    Object.keys(row).forEach((key) => {
      if (!headerSet.has(key)) {
        headerSet.add(key)
        headers.push(key)
      }
    })
  })
  if (!headers.length) {
    const fallbackHeaders = Array.from(
      new Set(rows.flatMap((row) => Object.keys(row)))
    )
    headers.push(...fallbackHeaders)
  }
  unitForm.variableHeaders = [...headers]
  unitForm.variablesPreview = rows.map((row) => ({ ...row }))
  unitForm.variablesText = buildVariablesText(headers, rows)
  unitForm.variableInputMode =
    typeof config['variable_source'] === 'string' && config['variable_source'] === 'csv'
      ? 'csv'
      : 'textarea'
  unitForm.csvFileName = ''
}

function extractVariableRows(units: PromptTestUnit[]): Array<Record<string, string>> {
  for (const unit of units) {
    const variables = toRecord(unit.variables)
    if (!variables) continue
    const cases = variables.cases
    if (!Array.isArray(cases) || !cases.length) {
      continue
    }
    return cases
      .map((item) => toRecord(item))
      .filter((row): row is Record<string, unknown> => Boolean(row))
      .map((row) => {
        const normalized: Record<string, string> = {}
        Object.entries(row).forEach(([key, value]) => {
          normalized[key] = formatDisplayValue(value)
        })
        return normalized
      })
  }
  return []
}

function buildVariablesText(
  headers: string[],
  rows: Array<Record<string, string>>
): string {
  if (!headers.length || !rows.length) {
    return ''
  }
  const escapeCell = (value: string): string => {
    if (value.includes('"') || value.includes(',') || /\r|\n/.test(value)) {
      return `"${value.replace(/"/g, '""')}"`
    }
    return value
  }
  const lines = [
    headers.map((header) => escapeCell(header)).join(','),
    ...rows.map((row) => headers.map((header) => escapeCell(row[header] ?? '')).join(','))
  ]
  return lines.join('\n')
}

function addParameterSet() {
  parameterSets.value = [...parameterSets.value, createParameterSet()]
}

function removeParameterSet(id: number) {
  if (parameterSets.value.length <= 1) {
    ElMessage.warning(t('promptTestCreate.messages.parameterSetRemoveLimit'))
    return
  }
  parameterSets.value = parameterSets.value.filter((set) => set.id !== id)
}

async function fetchPrompts() {
  promptLoading.value = true
  try {
    promptOptions.value = await listPrompts({ limit: 200 })
  } catch (error) {
    console.error('加载 Prompt 列表失败', error)
    ElMessage.error(t('promptTestCreate.messages.loadPromptFailed'))
  } finally {
    promptLoading.value = false
  }
}

async function fetchProviders() {
  providerLoading.value = true
  try {
    providers.value = await listLLMProviders()
  } catch (error) {
    console.error('加载模型列表失败', error)
    ElMessage.error(t('promptTestCreate.messages.loadProviderFailed'))
  } finally {
    providerLoading.value = false
  }
}

async function fetchAnalysisModules() {
  analysisModuleLoading.value = true
  try {
    analysisModuleOptions.value = await listAnalysisModules()
  } catch (error) {
    console.error('加载分析模块失败', error)
    ElMessage.error(t('promptTestCreate.messages.loadAnalysisModuleFailed'))
  } finally {
    analysisModuleLoading.value = false
  }
}

function goTestManagement() {
  router.push({ name: 'test-job-management' })
}

function parseDelimitedContent(content: string): {
  headers: string[]
  rows: Array<Record<string, string>>
} {
  const trimmed = content.trim()
  if (!trimmed) {
    return { headers: [], rows: [] }
  }
  const lines = trimmed.split(/\r\n|\n|\r/)
  if (lines.length === 0) {
    return { headers: [], rows: [] }
  }
  const delimiter = detectDelimiter(lines[0])
  const headers = parseCsvLine(lines[0], delimiter).map((header) => header.trim())
  if (!headers.length || headers.every((header) => !header)) {
    throw new Error(t('promptTestCreate.messages.variablesFormatInvalid'))
  }
  const rows: Array<Record<string, string>> = []
  for (let i = 1; i < lines.length; i += 1) {
    const values = parseCsvLine(lines[i], delimiter).map((value) => value.trim())
    if (values.every((value) => !value)) continue
    const row: Record<string, string> = {}
    headers.forEach((header, index) => {
      row[header] = values[index] ?? ''
    })
    rows.push(row)
  }
  return { headers, rows }
}

function detectDelimiter(line: string): string {
  if (line.includes('\t')) return '\t'
  if (line.includes(';')) return ';'
  return ','
}

function parseCsvLine(line: string, delimiter: string): string[] {
  const result: string[] = []
  let current = ''
  let inQuotes = false
  for (let i = 0; i < line.length; i += 1) {
    const char = line[i]
    if (char === '"') {
      if (inQuotes && line[i + 1] === '"') {
        current += '"'
        i += 1
      } else {
        inQuotes = !inQuotes
      }
    } else if (char === delimiter && !inQuotes) {
      result.push(current)
      current = ''
    } else {
      current += char
    }
  }
  result.push(current)
  return result
}

function handleParseVariablesText() {
  if (!unitForm.variablesText.trim()) {
    unitForm.variableHeaders = []
    unitForm.variablesPreview = []
    ElMessage.info(t('promptTestCreate.messages.variablesCleared'))
    return
  }
  try {
    const parsed = parseDelimitedContent(unitForm.variablesText)
    unitForm.variableHeaders = [...parsed.headers]
    unitForm.variablesPreview = parsed.rows.map((row) => ({ ...row }))
    unitForm.csvFileName = ''
    ElMessage.success(
      t('promptTestCreate.messages.variablesParsed', { count: parsed.rows.length })
    )
  } catch (error: any) {
    ElMessage.error(
      error?.message ?? t('promptTestCreate.messages.variablesFormatInvalid')
    )
  }
}

function clearVariables() {
  unitForm.variablesText = ''
  unitForm.csvFileName = ''
  unitForm.variableHeaders = []
  unitForm.variablesPreview = []
  ElMessage.info(t('promptTestCreate.messages.variablesCleared'))
}

function triggerCsvUpload() {
  csvInputRef.value?.click()
}

function handleCsvFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  const reader = new FileReader()
  reader.onload = () => {
    const text = typeof reader.result === 'string' ? reader.result : ''
    try {
      const parsed = parseDelimitedContent(text)
      unitForm.variableHeaders = [...parsed.headers]
      unitForm.variablesPreview = parsed.rows.map((row) => ({ ...row }))
      unitForm.variablesText = ''
      unitForm.csvFileName = file.name
      ElMessage.success(
        t('promptTestCreate.messages.csvParsed', { count: parsed.rows.length })
      )
    } catch (error: any) {
      unitForm.csvFileName = ''
      ElMessage.error(error?.message ?? t('promptTestCreate.messages.csvParseFailed'))
    } finally {
      if (csvInputRef.value) {
        csvInputRef.value.value = ''
      }
    }
  }
  reader.onerror = () => {
    unitForm.csvFileName = ''
    ElMessage.error(t('promptTestCreate.messages.csvReadFailed'))
    if (csvInputRef.value) {
      csvInputRef.value.value = ''
    }
  }
  reader.readAsText(file, 'utf-8')
}

function getVariablesPayload(): Record<string, unknown> | undefined {
  const cases = unitForm.variablesPreview.map((row) => ({ ...row }))
  if (!cases.length) {
    return undefined
  }
  return { cases }
}

function parseParameterJson(raw: string, label: string): Record<string, unknown> | undefined {
  const text = raw.trim()
  if (!text) return undefined
  try {
    const parsed = JSON.parse(text)
    if (parsed === null || Array.isArray(parsed) || typeof parsed !== 'object') {
      throw new Error('invalid')
    }
    return parsed as Record<string, unknown>
  } catch (error) {
    throw new Error(
      t('promptTestCreate.messages.parameterSetJsonInvalid', { name: label })
    )
  }
}

function cloneData<T>(data: T): T {
  return JSON.parse(JSON.stringify(data))
}

async function handleSubmit() {
  if (!taskForm.name.trim()) {
    ElMessage.warning(t('promptTestCreate.messages.taskNameRequired'))
    return
  }
  if (!taskForm.promptId) {
    ElMessage.warning(t('promptTestCreate.messages.promptRequired'))
    return
  }
  if (!selectedPromptVersions.value.length) {
    ElMessage.warning(t('promptTestCreate.messages.promptRequired'))
    return
  }
  if (!selectedModelInfos.value.length) {
    ElMessage.warning(t('promptTestCreate.messages.modelRequired'))
    return
  }
  if (!parameterSets.value.length) {
    ElMessage.warning(t('promptTestCreate.messages.parameterSetRequired'))
    return
  }
  if (!Number.isInteger(unitForm.rounds) || unitForm.rounds < 1) {
    ElMessage.warning(t('promptTestCreate.messages.roundsInvalid'))
    return
  }

  let preparedParameterSets: Array<{
    id: number
    label: string
    temperature: number
    topP: number | null
    parameters: Record<string, unknown> | undefined
  }>
  try {
    preparedParameterSets = parameterSets.value.map((set, index) => {
      const label = set.label.trim() || defaultParameterSetLabel(index)
      const parameters = parseParameterJson(set.parametersJson, label)
      const temperature = Number.isFinite(set.temperature)
        ? Number(set.temperature)
        : 0.7
      const topP =
        set.topP === null || Number.isNaN(Number(set.topP))
          ? null
          : Number(set.topP)
      return {
        id: set.id,
        label,
        temperature,
        topP,
        parameters
      }
    })
  } catch (error: any) {
    ElMessage.error(
      error?.message ??
        t('promptTestCreate.messages.parameterSetJsonInvalid', {
          name: defaultParameterSetLabel(0)
        })
    )
    return
  }

  const variablesPayload = getVariablesPayload()
  const rounds = Math.max(1, Math.floor(unitForm.rounds))

  const unitsPayload: UnitDraft[] = []

  for (const version of selectedPromptVersions.value) {
    for (const model of selectedModelInfos.value) {
      preparedParameterSets.forEach((set, index) => {
        const nameParts = [
          unitForm.baseName.trim() || taskForm.name.trim() || version.promptName,
          `${version.promptName} ${version.version}`,
          model.modelName,
          set.label
        ].filter(Boolean)

        const unitName = nameParts.length ? nameParts.join(' / ') : `Unit ${index + 1}`

        const unitVariables =
          variablesPayload !== undefined ? cloneData(variablesPayload) : null
        const parametersForUnit =
          set.parameters !== undefined ? cloneData(set.parameters) : null

        unitsPayload.push({
          name: unitName,
          description: null,
          model_name: model.modelName,
          llm_provider_id: model.providerId,
          temperature: set.temperature,
          top_p: set.topP,
          rounds,
          prompt_version_id: version.id,
          prompt_template: null,
          variables: unitVariables,
          parameters: parametersForUnit,
          expectations: null,
          tags: null,
          extra: {
            llm_model_id: model.modelId,
            llm_provider_name: model.providerName,
            prompt_name: version.promptName,
            prompt_version: version.version,
            parameter_label: set.label,
            parameter_index: index + 1
          }
        })
      })
    }
  }

  if (!unitsPayload.length) {
    ElMessage.warning(t('promptTestCreate.messages.noUnits'))
    return
  }

  submitting.value = true
  try {
    const payload = {
      name: taskForm.name.trim(),
      description: taskForm.description?.trim() || null,
      prompt_version_id: selectedPromptVersions.value[0]?.id ?? null,
      config: {
        prompt_id: taskForm.promptId,
        prompt_ids: taskForm.promptId ? [taskForm.promptId] : [],
        prompt_version_ids: taskForm.promptVersionIds,
        model_keys: unitForm.selectedModels,
        parameter_sets: preparedParameterSets.map((set, index) => ({
          id: set.id,
          label: set.label,
          temperature: set.temperature,
          top_p: set.topP,
          parameters: set.parameters ?? {}
        })),
        variable_headers: unitForm.variableHeaders,
        variable_source: unitForm.variableInputMode,
        analysis_modules: taskForm.analysisModules
      },
      auto_execute: taskForm.autoExecute,
      units: unitsPayload.map((unit) => ({
        name: unit.name,
        description: unit.description,
        model_name: unit.model_name,
        llm_provider_id: unit.llm_provider_id,
        temperature: unit.temperature,
        top_p: unit.top_p,
        rounds: unit.rounds,
        prompt_version_id: unit.prompt_version_id,
        prompt_template: unit.prompt_template,
        variables: unit.variables,
        parameters: unit.parameters,
        expectations: unit.expectations,
        tags: unit.tags,
        extra: unit.extra
      }))
    }

    await createPromptTestTask(payload)
    ElMessage.success(
      t('promptTestCreate.messages.createSuccess', { count: unitsPayload.length })
    )
    goTestManagement()
  } catch (error) {
    console.error('创建测试任务失败', error)
    ElMessage.error(t('promptTestCreate.messages.createFailed'))
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  void Promise.all([fetchPrompts(), fetchProviders(), fetchAnalysisModules()])
})
</script>

<style scoped>
.prompt-test-create-page {
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
  flex-direction: column;
  gap: 8px;
}

.page-header__text h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
}

.page-desc {
  margin: 0;
  font-size: 14px;
  color: var(--text-weak-color);
}

.form-card {
  margin-bottom: 32px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.card-header h3 {
  margin: 0;
  font-size: 18px;
}

.card-subtitle {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--text-weak-color);
}

.card-header__action {
  display: flex;
  align-items: center;
}

.task-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.form-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.section-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.section-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.section-help-button {
  padding: 0;
  width: 24px;
  height: 24px;
  min-height: 24px;
}

.form-tip {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--text-weak-color);
}

.inline-control {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
}

.inline-control .el-slider {
  flex: 1;
}

.parameter-set-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.parameter-set-card__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.parameter-set-card__title {
  font-weight: 600;
}

.parameter-set-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
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

.add-parameter-set {
  align-self: flex-start;
}

.variables-mode {
  display: flex;
  align-items: center;
  gap: 12px;
}

.variables-editor {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.variables-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
}

.hidden-file-input {
  display: none;
}

.variables-preview-wrapper {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.variables-preview {
  border-radius: 4px;
}

.csv-file-name {
  font-size: 12px;
  color: var(--text-weak-color);
}

.combination-summary {
  margin: 0;
  font-size: 12px;
  color: var(--text-weak-color);
}

@media (max-width: 768px) {
  .card-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .task-form {
    label-width: 100%;
  }
}
</style>
