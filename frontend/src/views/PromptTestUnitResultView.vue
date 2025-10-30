<template>
  <div class="unit-result-page">
    <el-breadcrumb separator="/" class="page-breadcrumb">
      <el-breadcrumb-item>
        <span class="breadcrumb-link" @click="goTaskResult">{{ t('promptTestResult.breadcrumb.task') }}</span>
      </el-breadcrumb-item>
      <el-breadcrumb-item>{{ unit?.name ?? t('promptTestResult.empty.noSelection') }}</el-breadcrumb-item>
    </el-breadcrumb>

    <section class="page-header">
      <div>
        <h2>{{ unit?.name ?? t('promptTestResult.empty.noSelection') }}</h2>
        <p class="page-desc">
          <span>{{ t('promptTestResult.fields.version') }}: {{ unit?.promptVersion ?? '-' }}</span>
          <span>{{ t('promptTestResult.fields.model') }}: {{ unit?.modelName ?? '-' }}</span>
          <span>{{ t('promptTestResult.fields.parameters') }}: {{ unit?.parameterSet ?? '-' }}</span>
        </p>
      </div>
      <div v-if="unitStatusTag" class="page-header__meta">
        <el-tag size="small" :type="unitStatusTag.type">{{ unitStatusTag.label }}</el-tag>
      </div>
    </section>

    <el-card v-loading="loading">
      <template #header>
        <div class="card-header">
          <span>{{ outputsTitle }}</span>
          <div class="card-markdown">
            <span class="card-markdown__label" :title="t('promptTestResult.markdown.tooltip')">
              {{ t('promptTestResult.markdown.label') }}
            </span>
            <el-switch
              v-model="unitMarkdownEnabled"
              size="small"
              :active-text="t('promptTestResult.markdown.on')"
              :inactive-text="t('promptTestResult.markdown.off')"
              inline-prompt
            />
          </div>
        </div>
      </template>

      <el-alert
        v-if="errorMessage"
        :title="errorMessage"
        type="error"
        show-icon
        class="unit-alert"
      />

      <div class="unit-parameters">
        <h4 class="unit-parameters__title">
          {{ t('promptTestResult.unitDetail.parametersTitle', { name: unit?.parameterSet ?? '-' }) }}
        </h4>
        <el-descriptions
          v-if="parameterEntries.length"
          :column="1"
          size="small"
          border
          class="unit-parameters__table"
        >
          <el-descriptions-item
            v-for="[paramKey, paramValue] in parameterEntries"
            :key="paramKey"
            :label="paramKey"
          >
            {{ paramValue }}
          </el-descriptions-item>
        </el-descriptions>
        <div v-else class="unit-parameters__empty">
          {{ t('promptTestResult.unitDetail.parametersEmpty') }}
        </div>
      </div>

      <div v-if="variableFilterVisible" class="variable-filter">
        <span class="variable-filter__label">
          {{ t('promptTestResult.unitDetail.variableFilterLabel') }}
        </span>
        <el-space wrap>
          <el-select
            v-model="variableFilter.key"
            clearable
            filterable
            size="small"
            :placeholder="t('promptTestResult.unitDetail.variableKeyPlaceholder')"
          >
            <el-option
              v-for="key in availableVariableKeys"
              :key="key"
              :label="key"
              :value="key"
            />
          </el-select>
          <el-input
            v-model="variableFilter.value"
            clearable
            size="small"
            :placeholder="t('promptTestResult.unitDetail.variableValuePlaceholder')"
          />
          <el-button
            v-if="isVariableFilterActive"
            size="small"
            type="primary"
            link
            @click="resetVariableFilter"
          >
            {{ t('promptTestResult.unitDetail.resetVariableFilter') }}
          </el-button>
        </el-space>
      </div>

      <el-empty
        v-if="!unit || !filteredOutputs.length"
        :description="t('promptTestResult.empty.noOutputs')"
      />
      <el-timeline v-else>
        <el-timeline-item
          v-for="output in filteredOutputs"
          :key="output.runIndex"
          :timestamp="`#${output.runIndex}`"
          placement="top"
        >
          <el-card shadow="hover">
            <div
              v-if="!unitMarkdownEnabled"
              class="output-content output-content--plain"
            >
              {{ output.content }}
            </div>
            <div
              v-else
              class="output-content output-content--markdown"
              v-html="renderMarkdown(output.content)"
            />
            <p class="output-meta">{{ output.meta ?? '' }}</p>
            <div v-if="output.variables && Object.keys(output.variables).length" class="output-variables">
              <div
                v-for="(value, key) in output.variables"
                :key="key"
                class="variable-item"
              >
                <span class="variable-key">{{ key }}:</span>
                <span class="variable-value">{{ value }}</span>
              </div>
            </div>
          </el-card>
        </el-timeline-item>
      </el-timeline>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { getPromptTestUnit, listPromptTestExperiments } from '../api/promptTest'
import type { PromptTestResultUnit } from '../utils/promptTestResult'
import { buildPromptTestResultUnit, buildParameterEntries } from '../utils/promptTestResult'
import MarkdownIt from 'markdown-it'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()

const unit = ref<PromptTestResultUnit | null>(null)
const loading = ref(false)
const errorMessage = ref<string | null>(null)
const unitMarkdownEnabled = ref(false)

const routeTaskId = computed(() => (route.params.taskId as string | undefined) ?? '')
const unitIdParam = computed(() => route.params.unitId)

const unitStatusLabelMap: Record<string, string> = {
  pending: '待执行',
  running: '执行中',
  completed: '已完成',
  failed: '执行失败',
  cancelled: '已取消'
}

const unitStatusTagType: Record<string, 'info' | 'success' | 'warning' | 'danger'> = {
  pending: 'info',
  running: 'warning',
  completed: 'success',
  failed: 'danger',
  cancelled: 'info'
}

const unitStatusTag = computed(() => {
  const status = unit.value?.status
  if (!status) return null
  return {
    label: unitStatusLabelMap[status] ?? status,
    type: unitStatusTagType[status] ?? 'info'
  }
})

const parameterEntries = computed(() =>
  unit.value ? buildParameterEntries(unit.value.parameters) : []
)

const unitOutputs = computed(() => unit.value?.outputs ?? [])
const variableFilter = reactive({
  key: '',
  value: ''
})
const availableVariableKeys = computed(() => {
  const keys = new Set<string>()
  unitOutputs.value.forEach((output) => {
    const variables = output.variables ?? {}
    Object.keys(variables).forEach((key) => {
      const trimmed = key.trim()
      if (trimmed) {
        keys.add(trimmed)
      }
    })
  })
  return Array.from(keys).sort((a, b) => a.localeCompare(b))
})
const isVariableFilterActive = computed(() => {
  return Boolean(variableFilter.key.trim()) || Boolean(variableFilter.value.trim())
})
const filteredOutputs = computed(() => {
  const outputs = unitOutputs.value
  if (!outputs.length) {
    return []
  }
  const key = variableFilter.key.trim()
  const search = variableFilter.value.trim().toLowerCase()
  return outputs.filter((output) => {
    const variables = output.variables ?? {}
    if (key) {
      if (!(key in variables)) {
        return false
      }
      if (!search) {
        return true
      }
      return String(variables[key] ?? '')
        .toLowerCase()
        .includes(search)
    }
    if (!search) {
      return true
    }
    return Object.values(variables).some((value) =>
      String(value ?? '')
        .toLowerCase()
        .includes(search)
    )
  })
})
const variableFilterVisible = computed(
  () => availableVariableKeys.value.length > 0 || isVariableFilterActive.value
)
const outputsTitle = computed(() => {
  const count = isVariableFilterActive.value
    ? filteredOutputs.value.length
    : unitOutputs.value.length
  const key = isVariableFilterActive.value ? 'filteredTitle' : 'outputsTitle'
  return t(`promptTestResult.unitDetail.${key}`, { count })
})
const markdownRenderer = new MarkdownIt({
  breaks: true,
  linkify: true,
  html: false
})

function renderMarkdown(content: string | null | undefined) {
  const source = content ?? ''
  return markdownRenderer.render(source || '')
}

function resetVariableFilter() {
  variableFilter.key = ''
  variableFilter.value = ''
}

function extractUnitId(value: unknown): number | null {
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

async function refreshUnit() {
  const id = extractUnitId(unitIdParam.value)
  if (id === null) {
    loading.value = false
    unit.value = null
    errorMessage.value = t('promptTestResult.messages.invalidUnit')
    return
  }

  loading.value = true
  errorMessage.value = null
  try {
    const unitData = await getPromptTestUnit(id)
    let experiments = []
    try {
      experiments = await listPromptTestExperiments(id)
    } catch (error) {
      console.error('加载测试单元实验数据失败', error)
      const message = t('promptTestResult.messages.partialFailed')
      errorMessage.value = message
      ElMessage.warning(message)
    }
    unit.value = buildPromptTestResultUnit(unitData, experiments)
  } catch (error) {
    console.error('加载测试单元失败', error)
    unit.value = null
    const message = t('promptTestResult.messages.unitLoadFailed')
    errorMessage.value = message
    ElMessage.error(message)
  } finally {
    loading.value = false
  }
}

function goTaskResult() {
  const taskId = routeTaskId.value
  if (!taskId) return
  router.push({ name: 'prompt-test-task-result', params: { taskId }, query: { tab: 'units' } })
}

onMounted(() => {
  void refreshUnit()
})

watch(
  () => route.params.unitId,
  () => {
    void refreshUnit()
  }
)

watch(
  () => unit.value?.id,
  () => {
    resetVariableFilter()
  }
)

watch(availableVariableKeys, (keys) => {
  if (variableFilter.key && !keys.includes(variableFilter.key)) {
    variableFilter.key = ''
  }
})
</script>

<style scoped>
.unit-result-page {
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

.page-header h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
}

.page-desc {
  margin: 4px 0 0;
  color: var(--text-weak-color);
  font-size: 13px;
  display: flex;
  gap: 12px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  font-weight: 600;
}

.card-markdown {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--text-weak-color);
}

.card-markdown__label {
  white-space: nowrap;
}

.unit-alert {
  margin-bottom: 16px;
}

.unit-parameters {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
}

.unit-parameters__title {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.unit-parameters__table {
  width: 100%;
}

.unit-parameters__empty {
  font-size: 12px;
  color: var(--text-weak-color);
}

.variable-filter {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 0 0 16px;
}

.variable-filter__label {
  font-size: 13px;
  color: var(--text-weak-color);
  white-space: nowrap;
}

.output-content {
  margin: 0 0 8px;
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

.output-meta {
  margin: 0 0 8px;
  color: var(--text-weak-color);
  font-size: 12px;
}

.output-variables {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
}

.variable-item {
  display: flex;
  gap: 6px;
}

.variable-key {
  font-weight: 600;
  color: var(--el-color-primary);
}
</style>
