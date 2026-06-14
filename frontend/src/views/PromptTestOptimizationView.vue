<template>
  <div class="optimization-page">
    <el-breadcrumb separator="/" class="page-breadcrumb">
      <el-breadcrumb-item>
        <span class="breadcrumb-link" @click="goTaskManagement">{{ t('menu.testJob') }}</span>
      </el-breadcrumb-item>
      <el-breadcrumb-item>
        <span class="breadcrumb-link" @click="goTaskResult">
          {{ task?.name ?? t('promptTestOptimization.breadcrumb.task') }}
        </span>
      </el-breadcrumb-item>
      <el-breadcrumb-item>{{ t('promptTestOptimization.breadcrumb.current') }}</el-breadcrumb-item>
    </el-breadcrumb>

    <section class="page-header">
      <div class="page-header__text">
        <h2>{{ t('promptTestOptimization.title') }}</h2>
        <p class="page-desc">{{ t('promptTestOptimization.subtitle') }}</p>
      </div>
      <el-button @click="goTaskResult">{{ t('promptTestOptimization.actions.backResult') }}</el-button>
    </section>

    <el-alert
      v-if="errorMessage"
      class="page-alert"
      type="error"
      show-icon
      :title="errorMessage"
    />

    <el-skeleton v-if="loading" animated :rows="8" />

    <template v-else-if="task">
      <el-alert
        v-if="!targetPrompt"
        class="page-alert"
        type="warning"
        show-icon
        :closable="false"
        :title="t('promptTestOptimization.messages.promptScopeInvalid')"
      />

      <div class="optimization-layout">
        <aside class="context-column">
          <el-card class="context-card" shadow="never">
            <template #header>
              <div class="section-header">
                <div>
                  <h3>{{ t('promptTestOptimization.sections.summary') }}</h3>
                  <p>{{ summaryMetaText }}</p>
                </div>
                <el-tag size="small" type="info">{{ scoringStatusText }}</el-tag>
              </div>
            </template>

            <div class="score-overview">
              <div class="score-overview__main">
                <span>{{ t('promptTestOptimization.labels.averageScore') }}</span>
                <strong>{{ averageScoreText }}</strong>
              </div>
              <div class="score-overview__meta">
                {{ t('promptTestOptimization.labels.scoreProgress', { completed: completedScoreCount, total: totalScoreCount }) }}
              </div>
            </div>

            <div class="dimension-list">
              <div
                v-for="dimension in dimensionStats"
                :key="dimension.name"
                class="dimension-row"
              >
                <span>{{ dimension.name }}</span>
                <el-progress
                  :percentage="dimension.value"
                  :show-text="false"
                  :stroke-width="8"
                  :status="dimension.value < 70 ? 'exception' : dimension.value < 80 ? 'warning' : 'success'"
                />
                <strong>{{ formatScoreValue(dimension.value) }}</strong>
              </div>
              <el-empty
                v-if="!dimensionStats.length"
                :description="t('promptTestOptimization.empty.noDimensions')"
              />
            </div>
          </el-card>

          <el-card class="context-card" shadow="never">
            <template #header>
              <div class="section-header">
                <div>
                  <h3>{{ t('promptTestOptimization.sections.issue') }}</h3>
                  <p>{{ t('promptTestOptimization.sections.issueDesc') }}</p>
                </div>
              </div>
            </template>
            <ul v-if="issueReasons.length" class="issue-list">
              <li v-for="reason in issueReasons" :key="reason">{{ reason }}</li>
            </ul>
            <el-empty v-else :description="t('promptTestOptimization.empty.noIssues')" />
          </el-card>

          <el-card class="context-card context-card--prompt" shadow="never">
            <template #header>
              <div class="section-header">
                <div>
                  <h3>{{ t('promptTestOptimization.sections.currentPrompt') }}</h3>
                  <p>{{ currentPromptMeta }}</p>
                </div>
              </div>
            </template>
            <pre class="prompt-preview">{{ currentPromptContent || t('promptTestOptimization.empty.noPromptContent') }}</pre>
          </el-card>
        </aside>

        <main class="workbench-column">
          <el-card class="workbench-card" shadow="never">
            <template #header>
              <div class="workbench-header">
                <div>
                  <h3>{{ t('promptTestOptimization.sections.workbench') }}</h3>
                  <p>{{ recommendationMetaText }}</p>
                </div>
                <el-tag
                  v-if="recommendation"
                  size="small"
                  :type="recommendation.status === 'failed' ? 'danger' : recommendation.status === 'completed' ? 'success' : 'warning'"
                >
                  {{ recommendationStatusText }}
                </el-tag>
              </div>
            </template>

            <div class="generator-row">
              <el-button
                class="version-manage-button"
                :disabled="generating"
                @click="openHistoryDialog"
              >
                {{ t('promptTestOptimization.actions.versionHistory') }}
              </el-button>
              <el-tag class="current-version-tag" type="info">
                {{ selectedPromptVersionLabel }}
              </el-tag>
              <el-select
                v-model="optimizationModelKey"
                filterable
                clearable
                class="model-select"
                :placeholder="t('promptTestOptimization.placeholders.model')"
                :disabled="generating"
              >
                <el-option-group
                  v-for="group in modelOptionGroups"
                  :key="`opt-${group.providerId}`"
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
              <el-button
                type="primary"
                :icon="MagicStick"
                :loading="generating"
                :disabled="!selectedPromptVersionId"
                @click="handleGenerateRecommendation"
              >
                {{ recommendation ? t('promptTestOptimization.actions.regenerate') : t('promptTestOptimization.actions.generate') }}
              </el-button>
            </div>

            <el-alert
              v-if="recommendation?.status === 'failed'"
              class="recommendation-alert"
              type="error"
              show-icon
              :closable="false"
              :title="recommendation.error || t('promptTestOptimization.messages.generateFailed')"
            />

            <div class="advice-grid">
              <section
                v-for="field in adviceFields"
                :key="field"
                class="advice-item"
              >
                <h4>{{ t(`promptTestResult.recommendation.fields.${field}`) }}</h4>
                <pre>{{ recommendationText(field) || '-' }}</pre>
              </section>
            </div>

            <section class="revision-section">
              <div class="revision-header">
                <div>
                  <h4>{{ t('promptTestOptimization.sections.revision') }}</h4>
                  <p>{{ t('promptTestOptimization.sections.revisionDesc') }}</p>
                </div>
                <el-button
                  :icon="CopyDocument"
                  :disabled="!revisionDraft.trim()"
                  @click="copyRevision"
                >
                  {{ t('promptTestOptimization.actions.copy') }}
                </el-button>
              </div>
              <el-input
                v-model="revisionDraft"
                type="textarea"
                :rows="14"
                :placeholder="t('promptTestOptimization.placeholders.revision')"
              />
              <div class="revision-actions">
                <span v-if="!targetPrompt" class="revision-tip">
                  {{ t('promptTestOptimization.messages.versionDisabled') }}
                </span>
                <el-button
                  type="success"
                  :icon="DocumentAdd"
                  :disabled="!canCreateVersion"
                  @click="openVersionDialog"
                >
                  {{ t('promptTestOptimization.actions.createVersion') }}
                </el-button>
              </div>
            </section>
          </el-card>
        </main>
      </div>
    </template>

    <el-empty v-else :description="t('promptTestOptimization.empty.noTask')" />

    <el-dialog
      v-model="historyDialog.visible"
      :title="t('promptTestOptimization.historyDialog.title')"
      width="860px"
    >
      <div class="history-dialog">
        <section class="history-dialog__pane">
          <div class="history-dialog__header">
            <h4>{{ t('promptTestOptimization.historyDialog.versionTitle') }}</h4>
            <p>{{ t('promptTestOptimization.historyDialog.versionDesc') }}</p>
          </div>
          <div v-if="promptVersionOptions.length" class="version-option-list">
            <button
              v-for="option in promptVersionOptions"
              :key="option.id"
              type="button"
              class="version-option"
              :class="{ 'version-option--active': selectedPromptVersionId === option.id }"
              :disabled="generating"
              @click="handlePromptVersionChange(option.id)"
            >
              <span>{{ option.version }}</span>
              <small>{{ option.label }}</small>
            </button>
          </div>
          <el-empty v-else :description="t('promptTestOptimization.empty.promptUnknown')" />
        </section>

        <section class="history-dialog__pane">
          <div class="history-dialog__header history-dialog__header--inline">
            <div>
              <h4>{{ t('promptTestOptimization.sections.history') }}</h4>
              <p>{{ currentPromptMeta }}</p>
            </div>
            <el-switch
              v-model="showAllHistory"
              :active-text="t('promptTestOptimization.actions.showAllHistory')"
              @change="handleHistoryScopeChange"
            />
          </div>
          <div v-if="recommendationHistory.length" class="history-list">
            <button
              v-for="item in recommendationHistory"
              :key="item.id"
              type="button"
              class="history-item"
              :class="{ 'history-item--active': recommendation?.id === item.id }"
              @click="applyRecommendation(item)"
            >
              <span>{{ recommendationHistoryMeta(item) }}</span>
              <el-tag
                size="small"
                :type="item.status === 'failed' ? 'danger' : item.status === 'completed' ? 'success' : 'warning'"
              >
                {{ t(`promptTestOptimization.status.${item.status}`) }}
              </el-tag>
            </button>
          </div>
          <el-empty v-else :description="t('promptTestOptimization.empty.noHistory')" />
        </section>
      </div>
    </el-dialog>

    <el-dialog
      v-model="versionDialog.visible"
      :title="t('promptTestOptimization.versionDialog.title')"
      width="720px"
      :close-on-click-modal="false"
    >
      <el-form label-position="top">
        <el-form-item :label="t('promptTestOptimization.versionDialog.prompt')">
          <el-input :model-value="targetPrompt?.name ?? '-'" disabled />
        </el-form-item>
        <el-form-item :label="t('promptTestOptimization.versionDialog.version')">
          <el-input
            v-model="versionDialog.version"
            :placeholder="t('promptTestOptimization.versionDialog.versionPlaceholder')"
          />
        </el-form-item>
        <el-form-item :label="t('promptTestOptimization.versionDialog.content')">
          <el-input
            v-model="versionDialog.content"
            type="textarea"
            :rows="10"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button :disabled="creatingVersion" @click="versionDialog.visible = false">
          {{ t('common.cancel') }}
        </el-button>
        <el-button type="success" :loading="creatingVersion" @click="submitVersion">
          {{ t('promptTestOptimization.actions.createVersion') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { CopyDocument, DocumentAdd, MagicStick } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import {
  createPromptTestOptimizationRecommendation,
  getLatestPromptTestOptimizationRecommendation,
  getPromptTestAIScores,
  getPromptTestTask,
  listPromptTestOptimizationRecommendations,
  listPromptTestUnits
} from '../api/promptTest'
import { listLLMProviders } from '../api/llmProvider'
import { getPrompt, listPrompts, updatePrompt, type HttpError } from '../api/prompt'
import type {
  PromptTestAIScoreSummary,
  PromptTestOptimizationRecommendation,
  PromptTestTask,
  PromptTestUnit
} from '../types/promptTest'
import type { LLMProvider } from '../types/llm'
import type { Prompt, PromptVersion } from '../types/prompt'
import { formatScoreValue as formatAIScoreValue } from '../utils/promptTestResult'

interface ModelInfo {
  providerId: number
  providerName: string
  modelId: number
  modelName: string
}

interface DimensionStat {
  name: string
  value: number
}

const route = useRoute()
const router = useRouter()
const { t, locale } = useI18n()

const task = ref<PromptTestTask | null>(null)
const units = ref<PromptTestUnit[]>([])
const scoringSummary = ref<PromptTestAIScoreSummary | null>(null)
const recommendation = ref<PromptTestOptimizationRecommendation | null>(null)
const recommendationHistory = ref<PromptTestOptimizationRecommendation[]>([])
const providers = ref<LLMProvider[]>([])
const prompts = ref<Prompt[]>([])
const optimizationModelKey = ref('')
const selectedPromptVersionId = ref<number | null>(null)
const showAllHistory = ref(false)
const revisionDraft = ref('')
const loading = ref(false)
const generating = ref(false)
const creatingVersion = ref(false)
const errorMessage = ref<string | null>(null)

const adviceFields = ['overall_advice', 'parameter_advice', 'model_advice', 'validation_plan']

const historyDialog = reactive({
  visible: false
})

const versionDialog = reactive({
  visible: false,
  version: '',
  content: ''
})

const routeTaskId = computed(() => {
  const raw = Array.isArray(route.params.taskId) ? route.params.taskId[0] : route.params.taskId
  const parsed = Number(raw)
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null
})

const modelOptionGroups = computed(() =>
  providers.value
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
)

const modelMap = computed<Map<string, ModelInfo>>(() => {
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

const selectedModel = computed(() => {
  if (!optimizationModelKey.value) return null
  return modelMap.value.get(optimizationModelKey.value) ?? null
})

const taskConfig = computed(() => toRecord(task.value?.config))

const configuredPromptId = computed(() => {
  const value = Number(taskConfig.value?.prompt_id)
  return Number.isInteger(value) && value > 0 ? value : null
})

const referencedVersionIds = computed(() => {
  const ids = new Set<number>()
  if (typeof task.value?.prompt_version_id === 'number') {
    ids.add(task.value.prompt_version_id)
  }
  units.value.forEach((unit) => {
    if (typeof unit.prompt_version_id === 'number') {
      ids.add(unit.prompt_version_id)
    }
  })
  return ids
})

const promptVersionOptions = computed(() => {
  const prompt = targetPrompt.value
  if (!prompt) return []
  return prompt.versions
    .filter((version) => referencedVersionIds.value.has(version.id))
    .map((version) => ({
      id: version.id,
      label: `${prompt.name} · ${version.version}`,
      version: version.version
    }))
    .sort((left, right) => left.version.localeCompare(right.version))
})

const targetUnitIds = computed(() => {
  if (!selectedPromptVersionId.value) return new Set<number>()
  return new Set(
    units.value
      .filter((unit) => unit.prompt_version_id === selectedPromptVersionId.value)
      .map((unit) => unit.id)
  )
})

const targetPrompt = computed<Prompt | null>(() => {
  if (configuredPromptId.value) {
    return prompts.value.find((prompt) => prompt.id === configuredPromptId.value) ?? null
  }
  const matched = prompts.value.filter((prompt) =>
    prompt.versions.some((version) => referencedVersionIds.value.has(version.id))
  )
  return matched.length === 1 ? matched[0] : null
})

const currentPromptVersion = computed<PromptVersion | null>(() => {
  const prompt = targetPrompt.value
  if (!prompt) return null
  if (selectedPromptVersionId.value) {
    const matched = prompt.versions.find((version) => version.id === selectedPromptVersionId.value)
    if (matched) return matched
  }
  const taskVersionId = task.value?.prompt_version_id
  if (typeof taskVersionId === 'number') {
    const matched = prompt.versions.find((version) => version.id === taskVersionId)
    if (matched) return matched
  }
  for (const versionId of referencedVersionIds.value) {
    const matched = prompt.versions.find((version) => version.id === versionId)
    if (matched) return matched
  }
  return prompt.current_version ?? prompt.versions[0] ?? null
})

const currentPromptContent = computed(() => currentPromptVersion.value?.content ?? '')

const currentPromptMeta = computed(() => {
  const prompt = targetPrompt.value
  const version = currentPromptVersion.value
  if (!prompt || !version) {
    return t('promptTestOptimization.empty.promptUnknown')
  }
  return `${prompt.name} · ${version.version}`
})

const selectedPromptVersionLabel = computed(() => {
  if (!selectedPromptVersionId.value) {
    return t('promptTestOptimization.messages.promptVersionRequired')
  }
  const matched = promptVersionOptions.value.find(
    (option) => option.id === selectedPromptVersionId.value
  )
  return matched?.version ?? `#${selectedPromptVersionId.value}`
})

const summaryMetaText = computed(() =>
  t('promptTestOptimization.labels.summaryMeta', {
    task: task.value?.name ?? '-',
    version: selectedPromptVersionLabel.value
  })
)

const targetScores = computed(() => {
  const ids = targetUnitIds.value
  if (!ids.size) return scoringSummary.value?.scores ?? []
  return (scoringSummary.value?.scores ?? []).filter((score) => ids.has(score.unit_id))
})

const completedScores = computed(() =>
  targetScores.value.filter((score) => score.status === 'completed')
)

const totalScoreCount = computed(() => targetScores.value.length)
const completedScoreCount = computed(() => completedScores.value.length)

const averageScore = computed(() => {
  const values = completedScores.value
    .map((score) => Number(score.overall_score))
    .filter((value) => Number.isFinite(value))
  if (!values.length) return null
  return values.reduce((sum, value) => sum + value, 0) / values.length
})

const averageScoreText = computed(() => formatScoreValue(averageScore.value))

const scoringStatusText = computed(() => {
  const status = String(scoringSummary.value?.status?.status ?? 'idle')
  return t(`promptTestResult.aiScoring.status.${status}`)
})

const recommendationStatusText = computed(() => {
  if (!recommendation.value) {
    return t('promptTestOptimization.status.noRecommendation')
  }
  return t(`promptTestOptimization.status.${recommendation.value.status}`)
})

const recommendationMetaText = computed(() => {
  if (!recommendation.value) {
    return t('promptTestOptimization.status.noRecommendation')
  }
  const created = formatDateTime(recommendation.value.created_at)
  return t('promptTestOptimization.labels.recommendationMeta', {
    model: recommendation.value.evaluator_model_name ?? '-',
    time: created
  })
})

const dimensionStats = computed<DimensionStat[]>(() => {
  const bucket = new Map<string, number[]>()
  completedScores.value.forEach((score) => {
    const dimensions = score.dimension_scores
    if (!dimensions || typeof dimensions !== 'object') return
    Object.entries(dimensions).forEach(([name, rawValue]) => {
      const value = Number(rawValue)
      if (!Number.isFinite(value)) return
      const values = bucket.get(name) ?? []
      values.push(value)
      bucket.set(name, values)
    })
  })
  return Array.from(bucket.entries())
    .map(([name, values]) => ({
      name,
      value: Math.round(values.reduce((sum, value) => sum + value, 0) / values.length)
    }))
    .sort((left, right) => left.value - right.value)
})

const issueReasons = computed(() => {
  const reasons = completedScores.value
    .filter((score) => Number(score.overall_score ?? 0) < 80)
    .map((score) => score.reason?.trim())
    .filter((reason): reason is string => Boolean(reason))
  return Array.from(new Set(reasons)).slice(0, 4)
})

const canCreateVersion = computed(
  () => Boolean(targetPrompt.value) && revisionDraft.value.trim().length > 0 && !creatingVersion.value
)

function toRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null
}

function formatScoreValue(value: unknown): string {
  return formatAIScoreValue(value, locale.value)
}

function recommendationText(key: string): string {
  const content = recommendation.value?.content
  const value =
    key === 'parameter_advice'
      ? content?.parameter_advice ?? content?.temperature_advice
      : content?.[key]
  if (value === null || value === undefined) return ''
  if (typeof value === 'string') return value
  return formatAdviceValue(value)
}

function formatAdviceValue(value: unknown): string {
  if (value === null || value === undefined) return ''
  if (typeof value === 'string') return value.trim()
  if (Array.isArray(value)) {
    return value
      .map((item) => formatAdviceValue(item))
      .filter(Boolean)
      .join('\n')
  }
  if (typeof value === 'object') {
    return Object.entries(value as Record<string, unknown>)
      .map(([key, item]) => {
        const text = formatAdviceValue(item)
        return text ? `${key}：${text}` : ''
      })
      .filter(Boolean)
      .join('\n')
  }
  return String(value)
}

function promptVersionLabel(versionId: number | null | undefined): string {
  if (!versionId) return '-'
  return promptVersionOptions.value.find((option) => option.id === versionId)?.version ?? `#${versionId}`
}

function recommendationHistoryMeta(item: PromptTestOptimizationRecommendation): string {
  return t('promptTestOptimization.labels.historyMeta', {
    version: promptVersionLabel(item.prompt_version_id),
    model: item.evaluator_model_name ?? '-',
    time: formatDateTime(item.created_at)
  })
}

function applyRecommendation(item: PromptTestOptimizationRecommendation | null) {
  recommendation.value = item
  applyRecommendationDraft()
}

function extractErrorMessage(error: unknown, fallback: string): string {
  if (error && typeof error === 'object' && 'payload' in error) {
    const httpError = error as HttpError
    const detail = (httpError.payload as Record<string, unknown> | null)?.detail
    if (typeof detail === 'string' && detail.trim()) return detail
  }
  if (error instanceof Error && error.message) return error.message
  return fallback
}

function formatDateTime(value: string | null): string {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString(locale.value)
}

function initializeOptimizationModel() {
  const aiScoring = toRecord(taskConfig.value?.ai_scoring)
  const providerId = Number(aiScoring?.evaluator_provider_id)
  const modelId = Number(aiScoring?.evaluator_model_id)
  const key = `${providerId}:${modelId}`
  if (Number.isFinite(providerId) && Number.isFinite(modelId) && modelMap.value.has(key)) {
    optimizationModelKey.value = key
  }
}

function applyRecommendationDraft() {
  const promptRevision = recommendationText('prompt_revision')
  revisionDraft.value = promptRevision
}

async function loadPrompts() {
  const promptList = await listPrompts({ limit: 200 })
  const promptMap = new Map(promptList.map((prompt) => [prompt.id, prompt]))
  if (configuredPromptId.value && !promptMap.has(configuredPromptId.value)) {
    const detail = await getPrompt(configuredPromptId.value)
    promptMap.set(detail.id, detail)
  }
  prompts.value = Array.from(promptMap.values())
}

function resolveRoutePromptVersionId(): number | null {
  const raw = Array.isArray(route.query.promptVersionId)
    ? route.query.promptVersionId[0]
    : route.query.promptVersionId
  const parsed = Number(raw)
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null
}

async function refreshRecommendationHistory(taskId: number) {
  const versionId = selectedPromptVersionId.value
  const history = await listPromptTestOptimizationRecommendations(
    taskId,
    showAllHistory.value ? null : versionId
  )
  recommendationHistory.value = history
}

async function refreshRecommendationForTarget(taskId: number) {
  const versionId = selectedPromptVersionId.value
  recommendation.value = versionId
    ? await getLatestPromptTestOptimizationRecommendation(taskId, versionId).catch(() => null)
    : null
  await refreshRecommendationHistory(taskId)
  applyRecommendationDraft()
}

function initializeTargetPromptVersion() {
  const routeVersionId = resolveRoutePromptVersionId()
  const available = Array.from(referencedVersionIds.value)
  if (routeVersionId && available.includes(routeVersionId)) {
    selectedPromptVersionId.value = routeVersionId
    return
  }
  if (available.length === 1) {
    selectedPromptVersionId.value = available[0]
    void router.replace({
      name: 'prompt-test-optimization',
      params: route.params,
      query: { ...route.query, promptVersionId: String(available[0]) }
    })
    return
  }
  selectedPromptVersionId.value = null
}

async function loadPage() {
  const taskId = routeTaskId.value
  if (!taskId) {
    errorMessage.value = t('promptTestOptimization.messages.invalidTask')
    return
  }
  loading.value = true
  errorMessage.value = null
  try {
    const [taskData, unitList, scoreResult, providerList] =
      await Promise.all([
        getPromptTestTask(taskId),
        listPromptTestUnits(taskId),
        getPromptTestAIScores(taskId).catch(() => null),
        listLLMProviders()
      ])
    task.value = taskData
    units.value = unitList
    scoringSummary.value = scoreResult
    providers.value = providerList
    initializeTargetPromptVersion()
    initializeOptimizationModel()
    await loadPrompts()
    await refreshRecommendationForTarget(taskId)
  } catch (error) {
    console.error('加载 AI 优化页失败', error)
    errorMessage.value = extractErrorMessage(
      error,
      t('promptTestOptimization.messages.loadFailed')
    )
  } finally {
    loading.value = false
  }
}

async function handleGenerateRecommendation() {
  const currentTask = task.value
  if (!currentTask) return
  const promptVersionId = selectedPromptVersionId.value
  if (!promptVersionId) {
    ElMessage.warning(t('promptTestOptimization.messages.promptVersionRequired'))
    return
  }
  const model = selectedModel.value
  if (!model) {
    ElMessage.warning(t('promptTestOptimization.messages.modelRequired'))
    return
  }
  generating.value = true
  try {
    recommendation.value = await createPromptTestOptimizationRecommendation(currentTask.id, {
      prompt_version_id: promptVersionId,
      evaluator_provider_id: model.providerId,
      evaluator_model_id: model.modelId,
      evaluator_model_name: model.modelName,
      language: locale.value
    })
    await refreshRecommendationHistory(currentTask.id)
    applyRecommendationDraft()
    if (recommendation.value.status === 'failed') {
      ElMessage.error(
        recommendation.value.error || t('promptTestOptimization.messages.generateFailed')
      )
    } else {
      ElMessage.success(t('promptTestOptimization.messages.generateSuccess'))
    }
  } catch (error) {
    console.error('生成优化建议失败', error)
    ElMessage.error(
      extractErrorMessage(error, t('promptTestOptimization.messages.generateFailed'))
    )
  } finally {
    generating.value = false
  }
}

async function handlePromptVersionChange(value: string | number | boolean | null | undefined) {
  if (generating.value) return
  const taskId = routeTaskId.value
  const parsed = Number(value)
  const versionId = Number.isInteger(parsed) && parsed > 0 ? parsed : null
  selectedPromptVersionId.value = versionId
  revisionDraft.value = ''
  recommendation.value = null
  if (taskId && versionId) {
    await router.replace({
      name: 'prompt-test-optimization',
      params: route.params,
      query: { ...route.query, promptVersionId: String(versionId) }
    })
    await refreshRecommendationForTarget(taskId)
  }
}

function openHistoryDialog() {
  historyDialog.visible = true
}

async function handleHistoryScopeChange() {
  const taskId = routeTaskId.value
  if (taskId) {
    await refreshRecommendationHistory(taskId)
  }
}

async function copyRevision() {
  if (!revisionDraft.value.trim()) return
  try {
    await navigator.clipboard.writeText(revisionDraft.value)
    ElMessage.success(t('promptTestOptimization.messages.copySuccess'))
  } catch (error) {
    console.error('复制 Prompt 改写失败', error)
    ElMessage.error(t('promptTestOptimization.messages.copyFailed'))
  }
}

function buildNextVersionName(prompt: Prompt): string {
  const labels = prompt.versions.map((version) => version.version)
  const numeric = labels
    .map((label) => /^v(\d+)$/i.exec(label.trim()))
    .filter((match): match is RegExpExecArray => Boolean(match))
    .map((match) => Number(match[1]))
    .filter((value) => Number.isFinite(value))
  const candidate = numeric.length ? `v${Math.max(...numeric) + 1}` : `v${labels.length + 1}`
  if (!labels.includes(candidate)) return candidate
  const now = new Date()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  const hour = String(now.getHours()).padStart(2, '0')
  const minute = String(now.getMinutes()).padStart(2, '0')
  return `v${now.getFullYear()}${month}${day}-${hour}${minute}`
}

function openVersionDialog() {
  const prompt = targetPrompt.value
  if (!prompt || !revisionDraft.value.trim()) return
  versionDialog.version = buildNextVersionName(prompt)
  versionDialog.content = revisionDraft.value
  versionDialog.visible = true
}

async function submitVersion() {
  const prompt = targetPrompt.value
  if (!prompt) return
  const version = versionDialog.version.trim()
  const content = versionDialog.content.trim()
  if (!version || !content) {
    ElMessage.warning(t('promptTestOptimization.messages.versionRequired'))
    return
  }
  creatingVersion.value = true
  try {
    const updated = await updatePrompt(prompt.id, { version, content })
    prompts.value = prompts.value.map((item) => (item.id === updated.id ? updated : item))
    versionDialog.visible = false
    ElMessage.success(t('promptTestOptimization.messages.versionCreated'))
    router.push({ name: 'prompt-detail', params: { id: updated.id } })
  } catch (error) {
    console.error('新增 Prompt 版本失败', error)
    ElMessage.error(
      extractErrorMessage(error, t('promptTestOptimization.messages.versionCreateFailed'))
    )
  } finally {
    creatingVersion.value = false
  }
}

function goTaskManagement() {
  router.push({ name: 'test-job-management' })
}

function goTaskResult() {
  const taskId = routeTaskId.value
  if (!taskId) {
    goTaskManagement()
    return
  }
  router.push({ name: 'prompt-test-task-result', params: { taskId } })
}

onMounted(() => {
  void loadPage()
})
</script>

<style scoped>
.optimization-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-breadcrumb {
  font-size: 13px;
}

.breadcrumb-link {
  cursor: pointer;
  color: inherit;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.page-header__text h2 {
  margin: 0 0 6px;
  font-size: 22px;
}

.page-desc {
  margin: 0;
  color: var(--text-weak-color);
}

.page-alert {
  margin-bottom: 0;
}

.optimization-layout {
  display: grid;
  grid-template-columns: minmax(320px, 0.9fr) minmax(460px, 1.4fr);
  gap: 16px;
  align-items: start;
}

.context-column,
.workbench-column {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
}

.context-card,
.workbench-card {
  border-radius: 8px;
}

.context-card--prompt {
  min-height: 260px;
}

.section-header,
.workbench-header,
.revision-header,
.generator-row,
.revision-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.section-header h3,
.section-header p,
.workbench-header h3,
.workbench-header p,
.revision-header h4,
.revision-header p {
  margin: 0;
}

.section-header p,
.workbench-header p,
.revision-header p {
  margin-top: 4px;
  color: var(--text-weak-color);
  font-size: 13px;
}

.score-overview {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 14px;
  border-radius: 8px;
  background: var(--el-color-primary-light-9);
}

.score-overview__main {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.score-overview__main span,
.score-overview__meta {
  color: var(--text-weak-color);
  font-size: 13px;
}

.score-overview__main strong {
  font-size: 32px;
  line-height: 1;
}

.dimension-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 14px;
}

.dimension-row {
  display: grid;
  grid-template-columns: 72px 1fr 44px;
  gap: 10px;
  align-items: center;
  font-size: 13px;
}

.dimension-row strong {
  text-align: right;
}

.issue-list {
  margin: 0;
  padding-left: 18px;
  color: var(--el-text-color-primary);
  line-height: 1.7;
}

.prompt-preview,
.advice-item pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
  color: var(--el-text-color-primary);
}

.prompt-preview {
  max-height: 340px;
  overflow: auto;
  padding: 12px;
  border-radius: 8px;
  background: var(--el-fill-color-lighter);
  font-size: 13px;
}

.generator-row {
  justify-content: flex-start;
  margin-bottom: 16px;
}

.model-select {
  width: min(380px, 100%);
}

.version-manage-button {
  min-width: 128px;
}

.current-version-tag {
  max-width: min(240px, 100%);
  overflow: hidden;
}

.recommendation-alert {
  margin-bottom: 16px;
}

.advice-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.advice-item {
  min-width: 0;
  padding: 12px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  background: var(--el-fill-color-lighter);
}

.advice-item h4 {
  margin: 0 0 8px;
  font-size: 14px;
}

.advice-item pre {
  font-size: 13px;
  line-height: 1.6;
}

.revision-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 18px;
}

.revision-actions {
  justify-content: flex-end;
}

.revision-tip {
  color: var(--el-color-warning);
  font-size: 13px;
}

.history-dialog {
  display: grid;
  grid-template-columns: minmax(220px, 0.8fr) minmax(320px, 1.2fr);
  gap: 16px;
}

.history-dialog__pane {
  min-width: 0;
}

.history-dialog__header {
  margin-bottom: 12px;
}

.history-dialog__header--inline {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.history-dialog__header h4,
.history-dialog__header p {
  margin: 0;
}

.history-dialog__header p {
  margin-top: 4px;
  color: var(--text-weak-color);
  font-size: 13px;
}

.version-option-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.version-option {
  display: flex;
  flex-direction: column;
  gap: 4px;
  width: 100%;
  min-height: 58px;
  padding: 10px 12px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  background: var(--el-bg-color);
  color: var(--el-text-color-primary);
  text-align: left;
  cursor: pointer;
}

.version-option:disabled {
  cursor: not-allowed;
  opacity: 0.65;
}

.version-option--active {
  border-color: var(--el-color-primary);
  box-shadow: 0 0 0 2px var(--el-color-primary-light-8);
}

.version-option small {
  color: var(--text-weak-color);
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.history-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  background: var(--el-bg-color);
  color: var(--el-text-color-primary);
  text-align: left;
  cursor: pointer;
}

.history-item--active {
  border-color: var(--el-color-primary);
  box-shadow: 0 0 0 2px var(--el-color-primary-light-8);
}

@media (max-width: 1120px) {
  .optimization-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .page-header,
  .generator-row,
  .revision-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .advice-grid {
    grid-template-columns: 1fr;
  }

  .model-select {
    width: 100%;
  }

  .history-dialog {
    grid-template-columns: 1fr;
  }
}
</style>
