<template>
  <div class="page">
    <section class="page-header">
      <div class="page-header__text">
        <h2>{{ t('llmManagement.headerTitle') }}</h2>
        <p class="page-desc">{{ t('llmManagement.headerDescription') }}</p>
      </div>
      <el-button type="primary" :icon="Plus" @click="openDialog">
        {{ t('llmManagement.addProvider') }}
      </el-button>
    </section>

    <template v-if="providerCards.length">
      <el-row :gutter="0" class="provider-grid" v-loading="loadingProviders">
        <el-col
          v-for="card in providerCards"
          :key="card.id"
          :span="24"
        >
          <el-card
            shadow="hover"
            class="provider-card"
            :class="{ 'provider-card--collapsed': card.collapsed }"
          >
            <div class="provider-card__header">
              <div class="provider-card__identity">
                <el-avatar
                  :size="48"
                  class="provider-card__avatar"
                  :src="card.logoUrl || undefined"
                >
                  {{ card.logoEmoji ?? '✨' }}
                </el-avatar>
                <div class="provider-card__text">
                  <h3>{{ card.providerName }}</h3>
                </div>
              </div>
              <div class="provider-card__actions">
                <el-tooltip
                  :content="card.collapsed ? t('llmManagement.card.expand') : t('llmManagement.card.collapse')"
                  placement="top"
                >
                  <el-button
                    class="collapse-button"
                    text
                    size="small"
                    :icon="card.collapsed ? Expand : Fold"
                    @click="toggleCollapse(card.id)"
                  />
                </el-tooltip>
                <el-tooltip :content="t('llmManagement.card.updateApiKey')" placement="top">
                  <el-button
                    class="collapse-button"
                    text
                    size="small"
                    :icon="Edit"
                    @click="handleUpdateApiKey(card)"
                  />
                </el-tooltip>
                <el-tooltip :content="t('llmManagement.card.deleteProvider')" placement="top">
                  <el-button
                    class="collapse-button"
                    text
                    type="danger"
                    size="small"
                    :icon="Delete"
                    @click="handleDeleteProvider(card)"
                  />
                </el-tooltip>
              </div>
            </div>

            <transition name="fade">
              <div v-show="!card.collapsed" class="provider-card__body">
                <el-form label-position="top" class="provider-card__form">
                  <el-form-item :label="t('llmManagement.card.apiKeyLabel')">
                    <el-input
                      class="provider-card__input"
                      :type="card.revealApiKey ? 'text' : 'password'"
                      :model-value="card.maskedApiKey"
                      readonly
                    >
                      <template #suffix>
                        <el-icon class="icon-button" @click.stop="toggleApiVisible(card.id)">
                          <component :is="card.revealApiKey ? Hide : View" />
                        </el-icon>
                      </template>
                    </el-input>
                  </el-form-item>
                  <el-form-item :label="t('llmManagement.card.baseUrlLabel')">
                    <el-input
                      class="provider-card__input"
                      v-model="card.baseUrl"
                      :readonly="!card.isCustom"
                      :placeholder="
                        card.isCustom
                          ? t('llmManagement.card.baseUrlPlaceholderCustom')
                          : t('llmManagement.card.baseUrlPlaceholderDefault')
                      "
                      @change="(value) => handleBaseUrlChange(card, value)"
                    />
                  </el-form-item>
                </el-form>

                <div class="provider-card__models">
                  <div class="provider-card__models-header">
                    <span>{{ t('llmManagement.card.modelsTitle') }}</span>
                    <el-button
                      type="primary"
                      text
                      size="small"
                      :icon="Plus"
                      @click="handleAddModel(card.id)"
                    >{{ t('llmManagement.card.addModel') }}</el-button>
                  </div>
                  <el-table
                    :data="card.models"
                    size="small"
                    border
                    :empty-text="t('llmManagement.card.table.empty')"
                  >
                    <el-table-column
                      prop="name"
                      :label="t('llmManagement.card.table.columns.name')"
                      min-width="140"
                    />
                    <el-table-column
                      prop="capability"
                      :label="t('llmManagement.card.table.columns.capability')"
                      min-width="120"
                    />
                    <el-table-column
                      prop="quota"
                      :label="t('llmManagement.card.table.columns.quota')"
                      min-width="140"
                    />
                    <el-table-column
                      prop="concurrencyLimit"
                      :label="t('llmManagement.card.table.columns.concurrency')"
                      width="140"
                    >
                      <template #default="{ row }">
                        <el-tag size="small" type="info">{{ row.concurrencyLimit }}</el-tag>
                      </template>
                    </el-table-column>
                    <el-table-column
                      prop="contextLength"
                      :label="t('llmManagement.card.table.columns.contextLength')"
                      width="160"
                    >
                      <template #default="{ row }">
                        <el-tag size="small" type="info">
                          {{ formatContextLength(row.contextLength) }}
                        </el-tag>
                      </template>
                    </el-table-column>
                    <el-table-column :label="t('llmManagement.card.table.columns.actions')" width="220" align="center">
                      <template #default="{ row }">
                        <div class="provider-card__model-actions">
                          <el-button
                            type="primary"
                            text
                            size="small"
                            :icon="Edit"
                            @click="handleEditModel(card.id, row)"
                          >{{ t('llmManagement.card.table.edit') }}</el-button>
                          <el-button
                            type="primary"
                            text
                            size="small"
                            :icon="CircleCheck"
                            :loading="checkingModelId === row.id"
                            :disabled="checkingModelId !== null && checkingModelId !== row.id"
                            @click="checkModel(card.id, row)">
                            {{ t('llmManagement.card.table.check') }}
                          </el-button>
                          <el-button
                            type="danger"
                            text
                            size="small"
                            :icon="Delete"
                            @click="removeModel(card.id, row.id)"
                          >{{ t('llmManagement.card.table.remove') }}</el-button>
                        </div>
                      </template>
                    </el-table-column>
                  </el-table>
                </div>
              </div>
            </transition>
          </el-card>
        </el-col>
      </el-row>
    </template>
    <el-empty v-else :description="t('llmManagement.empty')" />

    <el-dialog v-model="dialogVisible" :title="t('llmManagement.providerDialog.title')" width="620px">
      <el-form :model="llmForm" label-width="120px" class="dialog-form">
        <el-form-item :label="t('llmManagement.providerDialog.providerLabel')">
          <el-select
            v-model="llmForm.provider_key"
            :placeholder="t('llmManagement.providerDialog.providerPlaceholder')"
            @change="handleProviderChange"
          >
            <el-option
              v-for="item in providerOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('llmManagement.providerDialog.displayNameLabel')">
          <el-input
            v-model="llmForm.provider_name"
            :placeholder="t('llmManagement.providerDialog.displayNamePlaceholder')"
          />
        </el-form-item>
        <el-form-item v-if="isCustomProvider" :label="t('llmManagement.providerDialog.baseUrlLabel')">
          <el-input
            v-model="llmForm.base_url"
            :placeholder="t('llmManagement.providerDialog.baseUrlPlaceholder')"
          />
        </el-form-item>
        <el-form-item v-if="isCustomProvider" :label="t('llmManagement.providerDialog.emojiLabel')">
          <el-popover placement="bottom-start" width="260" trigger="click" v-model:visible="emojiPopoverVisible">
            <div class="emoji-grid">
              <span
                v-for="emoji in emojiOptions"
                :key="emoji"
                class="emoji-option"
                @click="selectEmoji(emoji)"
              >
                {{ emoji }}
              </span>
            </div>
            <template #reference>
              <el-input
                v-model="llmForm.logo_emoji"
                :placeholder="t('llmManagement.providerDialog.emojiPlaceholder')"
              />
            </template>
          </el-popover>
        </el-form-item>
        <el-form-item :label="t('llmManagement.providerDialog.apiKeyLabel')">
          <el-input
            v-model="llmForm.api_key"
            :placeholder="t('llmManagement.providerDialog.apiKeyPlaceholder')"
            type="password"
            show-password
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="createLoading" @click="handleCreate">
          {{ t('common.submit') }}
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="modelDialogVisible"
      :title="isEditingModel ? t('llmManagement.modelDialog.editTitle') : t('llmManagement.modelDialog.title')"
      width="560px"
    >
      <el-form :model="modelForm" label-width="120px" class="dialog-form">
        <el-form-item :label="t('llmManagement.modelDialog.nameLabel')">
          <el-input
            v-model="modelForm.name"
            :placeholder="t('llmManagement.modelDialog.namePlaceholder')"
            :disabled="isEditingModel"
          />
        </el-form-item>
        <el-form-item :label="t('llmManagement.modelDialog.capabilityLabel')">
          <el-input
            v-model="modelForm.capability"
            :placeholder="t('llmManagement.modelDialog.capabilityPlaceholder')"
          />
        </el-form-item>
        <el-form-item :label="t('llmManagement.modelDialog.quotaLabel')">
          <el-input
            v-model="modelForm.quota"
            :placeholder="t('llmManagement.modelDialog.quotaPlaceholder')"
          />
        </el-form-item>
        <el-form-item :label="t('llmManagement.modelDialog.concurrencyLabel')">
          <el-input-number
            v-model="modelForm.concurrency"
            :min="1"
            :max="50"
            :step="1"
            controls-position="right"
            :placeholder="t('llmManagement.modelDialog.concurrencyPlaceholder')"
          />
        </el-form-item>
        <el-form-item :label="t('llmManagement.modelDialog.contextLengthLabel')">
          <el-input-number
            v-model="modelForm.contextLength"
            :min="1"
            :max="2000000"
            :step="1024"
            controls-position="right"
            :placeholder="t('llmManagement.modelDialog.contextLengthPlaceholder')"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="modelDialogVisible = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="modelSubmitLoading" @click="submitModel">
          {{ t('common.submit') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { CircleCheck, Delete, Edit, Expand, Fold, Hide, Plus, View } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import {
  createLLMModel,
  createLLMProvider,
  deleteLLMModel,
  deleteLLMProvider,
  listCommonLLMProviders,
  listLLMProviders,
  updateLLMModel,
  updateLLMProvider,
  invokeLLMProvider,
  RequestTimeoutError
} from '../api/llmProvider'
import type { KnownLLMProvider, LLMProvider } from '../types/llm'
import { useI18n } from 'vue-i18n'

interface ProviderOption {
  label: string
  value: string
}

interface ProviderCardModel {
  id: number
  name: string
  capability: string | null
  quota: string | null
  concurrencyLimit: number
  contextLength: number | null
}

interface ProviderCard {
  id: number
  providerKey?: string | null
  providerName: string
  logoEmoji: string | null
  logoUrl: string | null
  maskedApiKey: string
  baseUrl: string
  isCustom: boolean
  models: ProviderCardModel[]
  collapsed: boolean
  revealApiKey: boolean
}

const { t } = useI18n()

const loadingProviders = ref(false)
const providerCards = ref<ProviderCard[]>([])
const checkingModelId = ref<number | null>(null)

const commonProviders = ref<KnownLLMProvider[]>([])
const commonProviderMap = computed(() => {
  const map = new Map<string, KnownLLMProvider>()
  for (const item of commonProviders.value) {
    map.set(item.key, item)
  }
  return map
})

const providerOptions = computed<ProviderOption[]>(() => {
  const options = commonProviders.value.map((item) => ({
    label: item.name,
    value: item.key
  }))
  options.push({ label: t('llmManagement.options.customProvider'), value: 'custom' })
  return options
})

const emojiOptions = ['🚀', '🧠', '✨', '🔥', '🤖', '📦', '🛰️', '🏢', '🦾', '🧩']

const dialogVisible = ref(false)
const createLoading = ref(false)
const emojiPopoverVisible = ref(false)
const llmForm = reactive({
  provider_key: '',
  provider_name: '',
  base_url: '',
  api_key: '',
  logo_emoji: '',
  is_custom: false
})

const isCustomProvider = computed(() => llmForm.provider_key === 'custom')

function resetForm() {
  const firstOption = providerOptions.value[0]
  if (firstOption && firstOption.value !== 'custom') {
    applyCommonProvider(firstOption.value)
  } else {
    llmForm.provider_key = 'custom'
    llmForm.provider_name = ''
    llmForm.base_url = ''
    llmForm.logo_emoji = ''
    llmForm.is_custom = true
  }
  llmForm.api_key = ''
  emojiPopoverVisible.value = false
}

function applyCommonProvider(key: string) {
  const provider = commonProviderMap.value.get(key)
  llmForm.provider_key = key
  llmForm.is_custom = false
  if (provider) {
    llmForm.provider_name = provider.name
    llmForm.base_url = provider.base_url ?? ''
    llmForm.logo_emoji = provider.logo_emoji ?? ''
  } else {
    llmForm.provider_name = key
    llmForm.base_url = ''
    llmForm.logo_emoji = ''
  }
}

function openDialog() {
  resetForm()
  dialogVisible.value = true
}

function handleProviderChange(value: string) {
  if (value === 'custom') {
    llmForm.provider_key = 'custom'
    llmForm.provider_name = ''
    llmForm.base_url = ''
    llmForm.logo_emoji = ''
    llmForm.is_custom = true
    emojiPopoverVisible.value = false
    return
  }
  applyCommonProvider(value)
  emojiPopoverVisible.value = false
}

function selectEmoji(emoji: string) {
  llmForm.logo_emoji = emoji
  emojiPopoverVisible.value = false
}

function toggleCollapse(id: number) {
  const target = providerCards.value.find((item) => item.id === id)
  if (target) {
    target.collapsed = !target.collapsed
  }
}

function toggleApiVisible(id: number) {
  const target = providerCards.value.find((item) => item.id === id)
  if (target) {
    target.revealApiKey = !target.revealApiKey
  }
}

async function fetchProviders() {
  loadingProviders.value = true
  try {
    const existingCollapsed = new Map(providerCards.value.map((card) => [card.id, card.collapsed]))
    const existingReveal = new Map(providerCards.value.map((card) => [card.id, card.revealApiKey]))

    const providers = await listLLMProviders()
    providerCards.value = providers.map((provider) => mapProviderToCard(provider, existingCollapsed, existingReveal))
  } catch (error) {
    console.error(error)
    ElMessage.error(t('llmManagement.messages.loadProvidersFailed'))
  } finally {
    loadingProviders.value = false
  }
}

function extractErrorMessage(error: unknown): string {
  if (error instanceof RequestTimeoutError) {
    return t('llmManagement.messages.checkTimeout')
  }
  if (!error) {
    return t('llmManagement.messages.checkFailed')
  }
  const maybeError = error as any
  const detail = maybeError?.payload?.detail ?? maybeError?.detail
  if (typeof detail === 'string' && detail.trim()) {
    return detail
  }
  if (detail && typeof detail === 'object') {
    try {
      return JSON.stringify(detail)
    } catch (jsonError) {
      console.error('Failed to stringify error detail', jsonError)
    }
  }
  if (typeof maybeError?.message === 'string' && maybeError.message.trim()) {
    return maybeError.message
  }
  return t('llmManagement.messages.checkFailed')
}

function mapProviderToCard(
  provider: LLMProvider,
  collapsedState: Map<number, boolean>,
  revealState: Map<number, boolean>
): ProviderCard {
  const logoUrl = provider.logo_url ?? null
  const logoEmoji =
    provider.logo_emoji ?? (logoUrl ? null : '✨')
  return {
    id: provider.id,
    providerKey: provider.provider_key,
    providerName: provider.provider_name,
    logoEmoji,
    logoUrl,
    maskedApiKey: provider.masked_api_key,
    baseUrl: provider.base_url ?? '',
    isCustom: provider.is_custom,
    models: provider.models.map((model) => ({
      id: model.id,
      name: model.name,
      capability: model.capability,
      quota: model.quota,
      concurrencyLimit: model.concurrency_limit,
      contextLength: model.context_length
    })),
    collapsed: collapsedState.get(provider.id) ?? false,
    revealApiKey: revealState.get(provider.id) ?? false
  }
}

async function fetchCommonOptions() {
  try {
    commonProviders.value = await listCommonLLMProviders()
  } catch (error) {
    console.error(error)
    ElMessage.warning(t('llmManagement.messages.loadCommonProvidersFailed'))
    commonProviders.value = []
  }
}

async function initialize() {
  await fetchCommonOptions()
  await fetchProviders()
}

onMounted(() => {
  initialize()
})

async function handleCreate() {
  if (!llmForm.provider_name.trim()) {
    ElMessage.warning(t('llmManagement.messages.providerNameRequired'))
    return
  }
  if (!llmForm.api_key.trim()) {
    ElMessage.warning(t('llmManagement.messages.apiKeyRequired'))
    return
  }
  if (isCustomProvider.value) {
    if (!llmForm.base_url.trim()) {
      ElMessage.warning(t('llmManagement.messages.customBaseUrlRequired'))
      return
    }
  }

  createLoading.value = true
  try {
    const payload = {
      provider_name: llmForm.provider_name.trim(),
      api_key: llmForm.api_key.trim(),
      base_url: llmForm.base_url.trim() || undefined,
      logo_emoji: llmForm.logo_emoji.trim() || undefined,
      is_custom: isCustomProvider.value ? true : undefined,
      provider_key: !isCustomProvider.value ? llmForm.provider_key : undefined
    }
    await createLLMProvider(payload)
    ElMessage.success(t('llmManagement.messages.createProviderSuccess'))
    dialogVisible.value = false
    await fetchProviders()
  } catch (error: any) {
    console.error(error)
    const message = error?.payload?.detail ?? t('llmManagement.messages.createProviderFailed')
    ElMessage.error(message)
  } finally {
    createLoading.value = false
  }
}

async function removeModel(providerId: number, modelId: number) {
  try {
    await ElMessageBox.confirm(
      t('llmManagement.confirmations.removeModel.message'),
      t('llmManagement.confirmations.removeModel.title'),
      {
        confirmButtonText: t('common.delete'),
        cancelButtonText: t('common.cancel'),
        type: 'warning'
      }
    )
  } catch (error) {
    return
  }

  try {
    await deleteLLMModel(providerId, modelId)
    ElMessage.success(t('llmManagement.messages.modelRemoved'))
    await fetchProviders()
  } catch (error: any) {
    console.error(error)
    const message = error?.payload?.detail ?? t('llmManagement.messages.removeModelFailed')
    ElMessage.error(message)
  }
}

const modelDialogVisible = ref(false)
const modelSubmitLoading = ref(false)
const activeProviderId = ref<number | null>(null)
const modelForm = reactive({
  name: '',
  capability: '',
  quota: '',
  concurrency: 5,
  contextLength: null as number | null
})
const isEditingModel = ref(false)
const editingModelId = ref<number | null>(null)

function handleAddModel(providerId: number) {
  activeProviderId.value = providerId
  isEditingModel.value = false
  editingModelId.value = null
  modelForm.name = ''
  modelForm.capability = ''
  modelForm.quota = ''
  modelForm.concurrency = 5
  modelForm.contextLength = null
  modelDialogVisible.value = true
}

async function submitModel() {
  const providerId = activeProviderId.value
  if (!providerId) {
    ElMessage.error(t('llmManagement.messages.providerNotFound'))
    return
  }

  if (!isEditingModel.value && !modelForm.name.trim()) {
    ElMessage.warning(t('llmManagement.messages.modelNameRequired'))
    return
  }

  const concurrencyValue = Math.trunc(modelForm.concurrency)
  if (!Number.isFinite(concurrencyValue) || concurrencyValue < 1) {
    ElMessage.warning(t('llmManagement.messages.concurrencyRequired'))
    return
  }
  const contextLengthValue =
    modelForm.contextLength === null || modelForm.contextLength === undefined
      ? null
      : Math.trunc(modelForm.contextLength)
  if (
    contextLengthValue !== null &&
    (!Number.isFinite(contextLengthValue) || contextLengthValue < 1)
  ) {
    ElMessage.warning(t('llmManagement.messages.contextLengthRequired'))
    return
  }

  const capabilityValue = modelForm.capability.trim()
  const quotaValue = modelForm.quota.trim()

  modelSubmitLoading.value = true
  try {
    if (isEditingModel.value) {
      const modelId = editingModelId.value
      if (!modelId) {
        throw new Error('missing model id')
      }
      await updateLLMModel(providerId, modelId, {
        capability: capabilityValue ? capabilityValue : null,
        quota: quotaValue ? quotaValue : null,
        concurrency_limit: concurrencyValue,
        context_length: contextLengthValue
      })
      ElMessage.success(t('llmManagement.messages.updateModelSuccess'))
    } else {
      await createLLMModel(providerId, {
        name: modelForm.name.trim(),
        capability: capabilityValue || undefined,
        quota: quotaValue || undefined,
        concurrency_limit: concurrencyValue,
        context_length: contextLengthValue
      })
      ElMessage.success(t('llmManagement.messages.createModelSuccess'))
    }
    modelDialogVisible.value = false
    await fetchProviders()
  } catch (error: any) {
    console.error(error)
    const message =
      error?.payload?.detail ??
      (isEditingModel.value
        ? t('llmManagement.messages.updateModelFailed')
        : t('llmManagement.messages.createModelFailed'))
    ElMessage.error(message)
  } finally {
    modelSubmitLoading.value = false
  }
}

function handleEditModel(providerId: number, model: ProviderCardModel) {
  activeProviderId.value = providerId
  isEditingModel.value = true
  editingModelId.value = model.id
  modelForm.name = model.name
  modelForm.capability = model.capability ?? ''
  modelForm.quota = model.quota ?? ''
  modelForm.concurrency = model.concurrencyLimit
  modelForm.contextLength = model.contextLength
  modelDialogVisible.value = true
}

function formatContextLength(value: number | null) {
  if (!value) {
    return t('llmManagement.card.table.unlimitedContext')
  }
  return value.toLocaleString()
}

async function handleBaseUrlChange(card: ProviderCard, value: string) {
  if (!card.isCustom) {
    return
  }
  const trimmed = (value ?? '').trim()
  if (!trimmed) {
    ElMessage.warning(t('llmManagement.messages.customBaseUrlRequired'))
    await fetchProviders()
    return
  }
  try {
    await updateLLMProvider(card.id, { base_url: trimmed })
    ElMessage.success(t('llmManagement.messages.baseUrlUpdated'))
    card.baseUrl = trimmed
  } catch (error: any) {
    console.error(error)
    const message = error?.payload?.detail ?? t('llmManagement.messages.baseUrlUpdateFailed')
    ElMessage.error(message)
    await fetchProviders()
  }
}

async function handleDeleteProvider(card: ProviderCard) {
  const modelCount = card.models.length
  const message = t('llmManagement.confirmations.removeProvider.message', {
    name: card.providerName,
    count: modelCount
  })
  try {
    await ElMessageBox.confirm(message, t('llmManagement.confirmations.removeProvider.title'), {
      confirmButtonText: t('common.delete'),
      cancelButtonText: t('common.cancel'),
      type: 'warning'
    })
  } catch (error) {
    return
  }

  try {
    await deleteLLMProvider(card.id)
    ElMessage.success(t('llmManagement.messages.providerDeleted'))
    await fetchProviders()
  } catch (error: any) {
    console.error(error)
    const detail = error?.payload?.detail ?? t('llmManagement.messages.providerDeleteFailed')
    ElMessage.error(detail)
  }
}

async function handleUpdateApiKey(card: ProviderCard) {
  try {
    const { value } = await ElMessageBox.prompt(
      t('llmManagement.confirmations.updateApiKey.message'),
      t('llmManagement.confirmations.updateApiKey.title'),
      {
        confirmButtonText: t('common.confirm'),
        cancelButtonText: t('common.cancel'),
        inputType: 'password',
        inputPlaceholder: t('llmManagement.confirmations.updateApiKey.placeholder')
      }
    )

    const newKey = value.trim()
    if (!newKey) {
      ElMessage.warning(t('llmManagement.messages.invalidApiKey'))
      return
    }

    await updateLLMProvider(card.id, { api_key: newKey })
    ElMessage.success(t('llmManagement.messages.apiKeyUpdated'))
    await fetchProviders()
  } catch (error: any) {
    if (error === 'cancel' || error === 'close') {
      return
    }
    console.error(error)
    const detail = error?.payload?.detail ?? t('llmManagement.messages.apiKeyUpdateFailed')
    ElMessage.error(detail)
  }
}

async function checkModel(providerId: number, model: ProviderCardModel) {
  if (checkingModelId.value !== null) {
    return
  }
  checkingModelId.value = model.id
  const startedAt = performance.now()
  try {
    await invokeLLMProvider(providerId, {
      messages: [
        {
          role: 'user',
          content: 'hello'
        }
      ],
      model_id: model.id,
      parameters: {}
    })
    const elapsed = Math.round(performance.now() - startedAt)
    ElMessage.success(t('llmManagement.messages.checkSuccess', { ms: elapsed }))
  } catch (error) {
    console.error('Model check failed', error)
    const message = extractErrorMessage(error)
    ElMessage.error(message)
  } finally {
    checkingModelId.value = null
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

.provider-grid {
  margin-top: 8px;
  /* row-gap: 24px; */
}

.provider-grid .el-col {
  flex: 1 0 100%;
  margin-bottom: 24px;
}

.provider-grid .el-col:last-child {
  margin-bottom: 0;
}

.provider-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 180px;
}

.provider-card--collapsed {
  min-height: 120px;
}

.provider-card__header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.provider-card__identity {
  display: flex;
  gap: 12px;
  align-items: center;
}

.provider-card__avatar {
  font-size: 24px;
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
}

.provider-card__text h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.provider-card__text p {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--text-weak-color);
}

.provider-card__actions {
  display: flex;
  align-items: flex-start;
}

.collapse-button {
  padding: 0 8px;
}

.provider-card__body {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.provider-card__form {
  display: flex;
  flex-direction: column;
  /* gap: 12px; */
  width: 100%;
  max-width: 360px;
  margin-top: 15px;
}

.provider-card__form .el-form-item {
  width: 100%;
}
.provider-card__input {
  max-width: 360px;
  width: 100%;
}


.icon-button {
  cursor: pointer;
}

.provider-card__models {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.provider-card__models-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.provider-card__model-actions {
  display: flex;
  justify-content: center;
  gap: 6px;
}

.dialog-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.emoji-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(32px, 1fr));
  gap: 8px;
}

.emoji-option {
  cursor: pointer;
  font-size: 20px;
  text-align: center;
  line-height: 32px;
  border-radius: 8px;
  transition: background-color 0.2s ease;
}

.emoji-option:hover {
  background: rgba(64, 158, 255, 0.2);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
