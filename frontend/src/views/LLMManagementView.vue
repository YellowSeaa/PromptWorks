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
            <div
              class="provider-card__header"
              role="button"
              tabindex="0"
              :aria-label="card.collapsed ? t('llmManagement.card.expand') : t('llmManagement.card.collapse')"
              @click="toggleCollapse(card.id)"
              @keydown.enter.prevent="toggleCollapse(card.id)"
              @keydown.space.prevent="toggleCollapse(card.id)"
            >
              <div class="provider-card__identity">
                <el-avatar
                  :size="48"
                  shape="square"
                  class="provider-card__avatar"
                  :src="card.logoUrl || undefined"
                >
                  {{ card.logoEmoji ?? '✨' }}
                </el-avatar>
                <div class="provider-card__text">
                  <h3>{{ card.providerName }}</h3>
                  <p class="provider-card__url" :title="card.baseUrl || t('common.notSet')">
                    {{ card.baseUrl || t('common.notSet') }}
                  </p>
                </div>
              </div>
              <div class="provider-card__actions">
                <el-tag
                  v-if="card.collapsed"
                  class="provider-card__model-count"
                  type="info"
                  effect="plain"
                >
                  {{ t('llmManagement.card.modelCount', { count: card.models.length }) }}
                </el-tag>
                <el-tooltip
                  :content="card.collapsed ? t('llmManagement.card.expand') : t('llmManagement.card.collapse')"
                  placement="top"
                >
                  <el-button
                    class="collapse-button"
                    text
                    size="small"
                    :icon="card.collapsed ? Expand : Fold"
                    :aria-label="card.collapsed ? t('llmManagement.card.expand') : t('llmManagement.card.collapse')"
                    @click.stop="toggleCollapse(card.id)"
                  />
                </el-tooltip>
                <el-tooltip :content="t('llmManagement.card.editProvider')" placement="top">
                  <el-button
                    class="collapse-button"
                    text
                    size="small"
                    :icon="Edit"
                    :aria-label="t('llmManagement.card.editProvider')"
                    @click.stop="openProviderEditDialog(card)"
                  />
                </el-tooltip>
                <el-tooltip :content="t('llmManagement.card.deleteProvider')" placement="top">
                  <el-button
                    class="collapse-button"
                    text
                    type="danger"
                    size="small"
                    :icon="Delete"
                    :aria-label="t('llmManagement.card.deleteProvider')"
                    @click.stop="handleDeleteProvider(card)"
                  />
                </el-tooltip>
              </div>
            </div>

            <transition name="fade">
              <div v-show="!card.collapsed" class="provider-card__body">
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
                      :label="t('llmManagement.card.table.columns.modelType')"
                      min-width="120"
                    >
                      <template #default="{ row }">
                        <el-tag size="small" :type="getModelTypeTagType(row.modelType)">
                          {{ formatModelType(row.modelType) }}
                        </el-tag>
                      </template>
                    </el-table-column>
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
                    <el-table-column
                      :label="t('llmManagement.card.table.columns.cost')"
                      min-width="180"
                    >
                      <template #default="{ row }">
                        {{ formatModelCost(row) }}
                      </template>
                    </el-table-column>
                    <el-table-column
                      :label="t('llmManagement.card.table.columns.actions')"
                      width="300"
                      align="center"
                    >
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
      v-model="providerEditDialogVisible"
      :title="t('llmManagement.providerEditDialog.title')"
      width="560px"
    >
      <el-form :model="providerEditForm" label-width="120px" class="dialog-form">
        <el-form-item :label="t('llmManagement.providerEditDialog.providerLabel')">
          <el-input v-model="providerEditForm.providerName" disabled />
        </el-form-item>
        <el-form-item :label="t('llmManagement.providerEditDialog.baseUrlLabel')">
          <el-input
            v-model="providerEditForm.baseUrl"
            :placeholder="t('llmManagement.providerEditDialog.baseUrlPlaceholder')"
          />
        </el-form-item>
        <el-form-item :label="t('llmManagement.providerEditDialog.currentApiKeyLabel')">
          <el-input
            class="provider-card__input"
            :type="providerEditForm.revealApiKey ? 'text' : 'password'"
            :model-value="providerEditForm.maskedApiKey"
            readonly
          >
            <template #suffix>
              <el-icon class="icon-button" @click.stop="providerEditForm.revealApiKey = !providerEditForm.revealApiKey">
                <component :is="providerEditForm.revealApiKey ? Hide : View" />
              </el-icon>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item :label="t('llmManagement.providerEditDialog.newApiKeyLabel')">
          <el-input
            v-model="providerEditForm.apiKey"
            :placeholder="t('llmManagement.providerEditDialog.newApiKeyPlaceholder')"
            type="password"
            show-password
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="providerEditDialogVisible = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="providerEditLoading" @click="submitProviderEdit">
          {{ t('common.save') }}
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="modelDialogVisible"
      :title="isEditingModel ? t('llmManagement.modelDialog.editTitle') : t('llmManagement.modelDialog.title')"
      class="model-dialog"
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
        <el-form-item :label="t('llmManagement.modelDialog.modelTypeLabel')">
          <el-select v-model="modelForm.modelType" class="model-type-select">
            <el-option
              v-for="option in modelTypeOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('llmManagement.modelDialog.concurrencyLabel')">
          <el-input-number
            v-model="modelForm.concurrency"
            class="model-number-input"
            :min="1"
            :max="50"
            :step="1"
            controls-position="right"
            :placeholder="t('llmManagement.modelDialog.concurrencyPlaceholder')"
          />
        </el-form-item>
        <el-form-item v-if="modelForm.modelType === 'chat'">
          <template #label>
            <span class="form-label-with-help">
              {{ t('llmManagement.modelDialog.contextLengthLabel') }}
              <el-tooltip
                :content="t('llmManagement.modelDialog.contextLengthHelp')"
                placement="top"
                trigger="hover"
                :show-after="120"
              >
                <span class="form-help-trigger">
                  <el-icon class="form-help-icon">
                    <InfoFilled />
                  </el-icon>
                </span>
              </el-tooltip>
            </span>
          </template>
          <el-input-number
            v-model="modelForm.contextLength"
            class="model-number-input"
            :min="1"
            :max="2000000"
            :step="1024"
            controls-position="right"
            :placeholder="t('llmManagement.modelDialog.contextLengthPlaceholder')"
          />
        </el-form-item>
        <el-collapse class="model-more-settings-section">
          <el-collapse-item :title="t('llmManagement.modelDialog.moreSettingsTitle')" name="more-settings">
            <template v-if="modelForm.modelType === 'embedding'">
              <div class="cost-section-header">
                <div>
                  <h4>{{ t('llmManagement.modelDialog.embeddingSection') }}</h4>
                  <p>{{ t('llmManagement.modelDialog.embeddingDefaultNote') }}</p>
                </div>
              </div>
              <el-row :gutter="12">
                <el-col :xs="24" :sm="12">
                  <el-form-item :label="t('llmManagement.modelDialog.embeddingApiStyleLabel')">
                    <el-select v-model="modelForm.embeddingApiStyle" class="model-type-select">
                      <el-option
                        v-for="option in embeddingApiStyleOptions"
                        :key="option.value"
                        :label="option.label"
                        :value="option.value"
                      />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :xs="24" :sm="12">
                  <el-form-item :label="t('llmManagement.modelDialog.embeddingDimensionsLabel')">
                    <el-input-number
                      v-model="modelForm.embeddingDimensions"
                      class="model-number-input"
                      :min="1"
                      :step="128"
                      controls-position="right"
                      :placeholder="t('llmManagement.modelDialog.embeddingDimensionsPlaceholder')"
                    />
                  </el-form-item>
                </el-col>
              </el-row>
              <el-row :gutter="12">
                <el-col :xs="24" :sm="12">
                  <el-form-item :label="t('llmManagement.modelDialog.embeddingBatchSizeLabel')">
                    <el-input-number
                      v-model="modelForm.embeddingBatchSize"
                      class="model-number-input"
                      :min="1"
                      :max="128"
                      :step="1"
                      controls-position="right"
                      :placeholder="t('llmManagement.modelDialog.embeddingBatchSizePlaceholder')"
                    />
                  </el-form-item>
                </el-col>
                <el-col :xs="24" :sm="12">
                  <el-form-item :label="t('llmManagement.modelDialog.embeddingMaxInputTokensLabel')">
                    <el-input-number
                      v-model="modelForm.embeddingMaxInputTokens"
                      class="model-number-input"
                      :min="1"
                      :step="512"
                      controls-position="right"
                      :placeholder="t('llmManagement.modelDialog.embeddingMaxInputTokensPlaceholder')"
                    />
                  </el-form-item>
                </el-col>
              </el-row>
              <div class="cost-advanced-divider" />
            </template>
            <div class="cost-section-header">
              <div>
                <h4>{{ t('llmManagement.modelDialog.costSection') }}</h4>
                <p>{{ t('llmManagement.modelDialog.costDefaultNote') }}</p>
              </div>
            </div>
            <div class="cost-pricing-section">
              <div class="cost-section-header">
                <div>
                  <h4>{{ t('llmManagement.modelDialog.costPricingSectionTitle') }}</h4>
                  <p>{{ t('llmManagement.modelDialog.costPricingSectionHint') }}</p>
                </div>
              </div>
              <el-row :gutter="12">
                <el-col :xs="24" :sm="12">
                  <el-form-item :label="t('llmManagement.modelDialog.costPricingUnitLabel')">
                    <el-input-number
                      v-model="modelForm.costPricingUnit"
                      class="model-number-input"
                      :min="1"
                      :step="1000"
                      controls-position="right"
                    />
                  </el-form-item>
                </el-col>
                <el-col :xs="24" :sm="12">
                  <el-form-item :label="t('llmManagement.modelDialog.costInputLabel')">
                    <el-input-number
                      v-model="modelForm.costInputPerUnit"
                      class="model-number-input"
                      :min="0"
                      :step="0.01"
                      :precision="1"
                      controls-position="right"
                    />
                  </el-form-item>
                </el-col>
              </el-row>
              <el-row :gutter="12">
                <el-col :xs="24" :sm="12">
                  <el-form-item :label="t('llmManagement.modelDialog.costOutputLabel')">
                    <el-input-number
                      v-model="modelForm.costOutputPerUnit"
                      class="model-number-input"
                      :min="0"
                      :step="0.01"
                      :precision="1"
                      controls-position="right"
                    />
                  </el-form-item>
                </el-col>
              </el-row>
            </div>
            <div class="cost-advanced-divider" />
            <div class="cost-section-header">
              <div>
                <h4>{{ t('llmManagement.modelDialog.costCurrencySectionTitle') }}</h4>
                <p>{{ t('llmManagement.modelDialog.costCurrencySectionHint') }}</p>
              </div>
              <el-tag :type="modelForm.useCustomCurrency ? 'warning' : 'info'" effect="plain">
                {{
                  modelForm.useCustomCurrency
                    ? t('llmManagement.modelDialog.costCurrencyEnabled')
                    : t('llmManagement.modelDialog.costCurrencyDisabled')
                }}
              </el-tag>
            </div>
            <div class="cost-currency-toggle">
              <div>
                <strong>{{ t('llmManagement.modelDialog.costCurrencyToggleTitle') }}</strong>
                <span>{{ t('llmManagement.modelDialog.costCurrencyToggleHint') }}</span>
              </div>
              <el-switch
                v-model="modelForm.useCustomCurrency"
                @change="handleCustomCurrencyToggle"
              />
            </div>
            <div v-if="!modelForm.useCustomCurrency" class="cost-currency-summary">
              <span>{{ t('llmManagement.modelDialog.costCurrencyDefaultStatus') }}</span>
              <strong>CNY / 1</strong>
            </div>
            <el-row v-else :gutter="12">
              <el-col :xs="24" :sm="12">
                <el-form-item :label="t('llmManagement.modelDialog.costCurrencyLabel')">
                  <el-input v-model="modelForm.costCurrency" />
                </el-form-item>
              </el-col>
              <el-col :xs="24" :sm="12">
                <el-form-item :label="t('llmManagement.modelDialog.costExchangeRateLabel')">
                  <el-input-number
                    v-model="modelForm.costExchangeRate"
                    class="model-number-input"
                    :min="0.000001"
                    :step="0.1"
                    controls-position="right"
                  />
                </el-form-item>
              </el-col>
            </el-row>
            <div v-if="modelForm.useCustomCurrency" class="cost-default-note">
              {{ t('llmManagement.modelDialog.costCurrencyDefaultNote') }}
            </div>
            <div class="cost-advanced-divider" />
            <div class="cost-section-header">
              <div>
                <h4>{{ t('llmManagement.modelDialog.costTierTitle') }}</h4>
                <p>{{ t('llmManagement.modelDialog.costTierHint') }}</p>
              </div>
            </div>
            <div class="cost-tier-list">
              <div class="cost-tier-row cost-tier-row--head" aria-hidden="true">
                <span>{{ t('llmManagement.modelDialog.costTierContextLabel') }}</span>
                <span>{{ t('llmManagement.modelDialog.costInputLabel') }}</span>
                <span>{{ t('llmManagement.modelDialog.costOutputLabel') }}</span>
                <span>{{ t('llmManagement.modelDialog.costTierActionLabel') }}</span>
              </div>
              <div
                v-for="(tier, index) in modelForm.costTiers"
                :key="index"
                class="cost-tier-row"
              >
                <el-input-number
                  v-model="tier.upToContextTokens"
                  class="cost-tier-row__input"
                  :min="1"
                  :step="1024"
                  controls-position="right"
                  :placeholder="t('llmManagement.modelDialog.costTierContextPlaceholder')"
                />
                <el-input-number
                  v-model="tier.inputPerUnit"
                  class="cost-tier-row__input"
                  :min="0"
                  :step="0.01"
                  :precision="1"
                  controls-position="right"
                  :placeholder="t('llmManagement.modelDialog.costInputLabel')"
                />
                <el-input-number
                  v-model="tier.outputPerUnit"
                  class="cost-tier-row__input"
                  :min="0"
                  :step="0.01"
                  :precision="1"
                  controls-position="right"
                  :placeholder="t('llmManagement.modelDialog.costOutputLabel')"
                />
                <el-button text type="danger" :icon="Delete" @click="removeCostTier(index)" />
              </div>
              <el-button text type="primary" :icon="Plus" @click="addCostTier">
                {{ t('llmManagement.modelDialog.addCostTier') }}
              </el-button>
            </div>
          </el-collapse-item>
        </el-collapse>
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
import { CircleCheck, Delete, Edit, Expand, Fold, Hide, InfoFilled, Plus, View } from '@element-plus/icons-vue'
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
import type { EmbeddingApiStyle, KnownLLMProvider, LLMModelType, LLMProvider } from '../types/llm'
import { useI18n } from 'vue-i18n'

interface ProviderOption {
  label: string
  value: string
}

interface ProviderCardModel {
  id: number
  name: string
  modelType: LLMModelType
  embeddingApiStyle: EmbeddingApiStyle | null
  embeddingDimensions: number | null
  embeddingBatchSize: number | null
  embeddingMaxInputTokens: number | null
  concurrencyLimit: number
  contextLength: number | null
  costCurrency: string
  costDisplayCurrency: string
  costExchangeRate: number
  costPricingUnit: number
  costInputPerUnit: number | null
  costOutputPerUnit: number | null
  costTiers: CostTierForm[]
}

interface CostTierForm {
  upToContextTokens: number | null
  inputPerUnit: number | null
  outputPerUnit: number | null
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

const modelTypeOptions = computed(() => [
  { label: t('llmManagement.modelDialog.modelTypes.chat'), value: 'chat' as LLMModelType },
  { label: t('llmManagement.modelDialog.modelTypes.embedding'), value: 'embedding' as LLMModelType }
])

const embeddingApiStyleOptions = computed(() => [
  {
    label: t('llmManagement.modelDialog.embeddingApiStyles.openaiCompatible'),
    value: 'openai_compatible' as EmbeddingApiStyle
  }
])

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

async function fetchProviders() {
  loadingProviders.value = true
  try {
    const existingCollapsed = new Map(providerCards.value.map((card) => [card.id, card.collapsed]))

    const providers = await listLLMProviders()
    providerCards.value = providers.map((provider) => mapProviderToCard(provider, existingCollapsed))
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
  collapsedState: Map<number, boolean>
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
      modelType: model.model_type ?? 'chat',
      embeddingApiStyle: model.embedding_api_style ?? null,
      embeddingDimensions: model.embedding_dimensions ?? null,
      embeddingBatchSize: model.embedding_batch_size ?? null,
      embeddingMaxInputTokens: model.embedding_max_input_tokens ?? null,
      concurrencyLimit: model.concurrency_limit,
      contextLength: model.context_length,
      costCurrency: model.cost_currency,
      costDisplayCurrency: model.cost_display_currency,
      costExchangeRate: model.cost_exchange_rate,
      costPricingUnit: model.cost_pricing_unit,
      costInputPerUnit: model.cost_input_per_unit,
      costOutputPerUnit: model.cost_output_per_unit,
      costTiers: (model.cost_tiers ?? []).map((tier) => ({
        upToContextTokens: tier.up_to_context_tokens,
        inputPerUnit: tier.input_per_unit ?? null,
        outputPerUnit: tier.output_per_unit ?? null
      }))
    })),
    collapsed: collapsedState.get(provider.id) ?? true
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
  modelType: 'chat' as LLMModelType,
  embeddingApiStyle: 'openai_compatible' as EmbeddingApiStyle,
  embeddingDimensions: null as number | null,
  embeddingBatchSize: 16 as number | null,
  embeddingMaxInputTokens: null as number | null,
  concurrency: 5,
  contextLength: null as number | null,
  useCustomCurrency: false,
  costCurrency: 'CNY',
  costDisplayCurrency: 'CNY',
  costExchangeRate: 1,
  costPricingUnit: 1000000,
  costInputPerUnit: 0.0 as number | null,
  costOutputPerUnit: 0.0 as number | null,
  costTiers: [] as CostTierForm[]
})
const isEditingModel = ref(false)
const editingModelId = ref<number | null>(null)

function handleAddModel(providerId: number) {
  activeProviderId.value = providerId
  isEditingModel.value = false
  editingModelId.value = null
  modelForm.name = ''
  resetModelUsageForm()
  modelForm.concurrency = 5
  modelForm.contextLength = null
  resetModelCostForm()
  modelDialogVisible.value = true
}

function resetModelUsageForm() {
  modelForm.modelType = 'chat'
  modelForm.embeddingApiStyle = 'openai_compatible'
  modelForm.embeddingDimensions = null
  modelForm.embeddingBatchSize = 16
  modelForm.embeddingMaxInputTokens = null
}

function resetModelCostForm() {
  modelForm.useCustomCurrency = false
  modelForm.costCurrency = 'CNY'
  modelForm.costDisplayCurrency = 'CNY'
  modelForm.costExchangeRate = 1
  modelForm.costPricingUnit = 1000000
  modelForm.costInputPerUnit = 0.0
  modelForm.costOutputPerUnit = 0.0
  modelForm.costTiers = []
}

function isCustomCurrency(currency: string, exchangeRate: number) {
  const normalizedCurrency = currency.trim().toUpperCase()
  return normalizedCurrency !== 'CNY' || Number(exchangeRate) !== 1
}

function handleCustomCurrencyToggle(value: string | number | boolean) {
  if (!value) {
    modelForm.costCurrency = 'CNY'
    modelForm.costDisplayCurrency = 'CNY'
    modelForm.costExchangeRate = 1
  }
}

function buildCostPayload() {
  const tiers = modelForm.costTiers
    .filter((tier) => tier.upToContextTokens && tier.upToContextTokens > 0)
    .map((tier) => ({
      up_to_context_tokens: Math.trunc(Number(tier.upToContextTokens)),
      input_per_unit: tier.inputPerUnit ?? null,
      output_per_unit: tier.outputPerUnit ?? null
    }))
  return {
    cost_currency: modelForm.useCustomCurrency
      ? modelForm.costCurrency.trim().toUpperCase() || 'CNY'
      : 'CNY',
    cost_display_currency: modelForm.costDisplayCurrency.trim().toUpperCase() || 'CNY',
    cost_exchange_rate: modelForm.useCustomCurrency ? Number(modelForm.costExchangeRate) || 1 : 1,
    cost_pricing_unit: Math.trunc(Number(modelForm.costPricingUnit) || 1000000),
    cost_input_per_unit: modelForm.costInputPerUnit,
    cost_output_per_unit: modelForm.costOutputPerUnit,
    cost_tiers: tiers.length ? tiers : null
  }
}

function buildEmbeddingPayload() {
  if (modelForm.modelType !== 'embedding') {
    return {
      embedding_api_style: null,
      embedding_dimensions: null,
      embedding_batch_size: null,
      embedding_max_input_tokens: null
    }
  }
  return {
    embedding_api_style: modelForm.embeddingApiStyle,
    embedding_dimensions: normalizeOptionalPositiveInteger(modelForm.embeddingDimensions),
    embedding_batch_size: normalizeOptionalPositiveInteger(modelForm.embeddingBatchSize),
    embedding_max_input_tokens: normalizeOptionalPositiveInteger(modelForm.embeddingMaxInputTokens)
  }
}

function normalizeOptionalPositiveInteger(value: number | null | undefined) {
  if (value === null || value === undefined) {
    return null
  }
  const normalized = Math.trunc(Number(value))
  return Number.isFinite(normalized) && normalized > 0 ? normalized : null
}

function addCostTier() {
  modelForm.costTiers.push({
    upToContextTokens: modelForm.contextLength ?? null,
    inputPerUnit: modelForm.costInputPerUnit,
    outputPerUnit: modelForm.costOutputPerUnit
  })
}

function removeCostTier(index: number) {
  modelForm.costTiers.splice(index, 1)
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

  modelSubmitLoading.value = true
  try {
    if (isEditingModel.value) {
      const modelId = editingModelId.value
      if (!modelId) {
        throw new Error('missing model id')
      }
      await updateLLMModel(providerId, modelId, {
        model_type: modelForm.modelType,
        ...buildEmbeddingPayload(),
        concurrency_limit: concurrencyValue,
        context_length: contextLengthValue,
        ...buildCostPayload()
      })
      ElMessage.success(t('llmManagement.messages.updateModelSuccess'))
    } else {
      await createLLMModel(providerId, {
        name: modelForm.name.trim(),
        model_type: modelForm.modelType,
        ...buildEmbeddingPayload(),
        concurrency_limit: concurrencyValue,
        context_length: contextLengthValue,
        ...buildCostPayload()
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
  modelForm.modelType = model.modelType
  modelForm.embeddingApiStyle = model.embeddingApiStyle ?? 'openai_compatible'
  modelForm.embeddingDimensions = model.embeddingDimensions
  modelForm.embeddingBatchSize = model.embeddingBatchSize ?? 16
  modelForm.embeddingMaxInputTokens = model.embeddingMaxInputTokens
  modelForm.concurrency = model.concurrencyLimit
  modelForm.contextLength = model.contextLength
  modelForm.useCustomCurrency = isCustomCurrency(model.costCurrency, model.costExchangeRate)
  modelForm.costCurrency = model.costCurrency
  modelForm.costDisplayCurrency = model.costDisplayCurrency
  modelForm.costExchangeRate = model.costExchangeRate
  modelForm.costPricingUnit = model.costPricingUnit
  modelForm.costInputPerUnit = model.costInputPerUnit ?? 0.0
  modelForm.costOutputPerUnit = model.costOutputPerUnit ?? 0.0
  modelForm.costTiers = model.costTiers.map((tier) => ({ ...tier }))
  modelDialogVisible.value = true
}

function formatContextLength(value: number | null) {
  if (!value) {
    return t('llmManagement.card.table.unlimitedContext')
  }
  return value.toLocaleString()
}

function formatModelType(modelType: LLMModelType) {
  return t(`llmManagement.modelDialog.modelTypes.${modelType}`)
}

function getModelTypeTagType(modelType: LLMModelType) {
  if (modelType === 'embedding') {
    return 'success'
  }
  return 'info'
}

function formatModelCost(model: ProviderCardModel) {
  const input = formatDisplayCostRate(model.costInputPerUnit, model.costExchangeRate)
  const output = formatDisplayCostRate(model.costOutputPerUnit, model.costExchangeRate)
  const unit = model.costPricingUnit.toLocaleString()
  return `${model.costDisplayCurrency} ${input}/${output} / ${unit}`
}

function formatDisplayCostRate(value: number | null, exchangeRate: number) {
  const displayValue = (value ?? 0) * (Number(exchangeRate) || 1)
  return Number.isInteger(displayValue) ? `${displayValue}` : `${Number(displayValue.toFixed(6))}`
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

const providerEditDialogVisible = ref(false)
const providerEditLoading = ref(false)
const providerEditForm = reactive({
  providerId: null as number | null,
  providerName: '',
  baseUrl: '',
  originalBaseUrl: '',
  maskedApiKey: '',
  apiKey: '',
  revealApiKey: false
})

function openProviderEditDialog(card: ProviderCard) {
  providerEditForm.providerId = card.id
  providerEditForm.providerName = card.providerName
  providerEditForm.baseUrl = card.baseUrl
  providerEditForm.originalBaseUrl = card.baseUrl
  providerEditForm.maskedApiKey = card.maskedApiKey
  providerEditForm.apiKey = ''
  providerEditForm.revealApiKey = false
  providerEditDialogVisible.value = true
}

async function submitProviderEdit() {
  const providerId = providerEditForm.providerId
  if (!providerId) {
    ElMessage.error(t('llmManagement.messages.providerNotFound'))
    return
  }

  const trimmedBaseUrl = providerEditForm.baseUrl.trim()
  const trimmedApiKey = providerEditForm.apiKey.trim()
  if (!trimmedBaseUrl) {
    ElMessage.warning(t('llmManagement.messages.customBaseUrlRequired'))
    return
  }

  const payload: {
    base_url?: string
    api_key?: string
  } = {}
  if (trimmedBaseUrl !== providerEditForm.originalBaseUrl) {
    payload.base_url = trimmedBaseUrl
  }
  if (trimmedApiKey) {
    payload.api_key = trimmedApiKey
  }
  if (!Object.keys(payload).length) {
    providerEditDialogVisible.value = false
    return
  }

  providerEditLoading.value = true
  try {
    await updateLLMProvider(providerId, payload)
    ElMessage.success(t('llmManagement.messages.providerUpdated'))
    providerEditDialogVisible.value = false
    await fetchProviders()
  } catch (error: any) {
    console.error(error)
    const detail = error?.payload?.detail ?? t('llmManagement.messages.providerUpdateFailed')
    ElMessage.error(detail)
  } finally {
    providerEditLoading.value = false
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
}

.provider-card--collapsed {
  min-height: 0;
}

.provider-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  cursor: pointer;
  outline: none;
}

.provider-card__header:focus-visible {
  border-radius: 8px;
  box-shadow: 0 0 0 2px var(--el-color-primary-light-5);
}

.provider-card__identity {
  display: flex;
  flex: 1 1 auto;
  gap: 12px;
  align-items: center;
  min-width: 0;
}

.provider-card__avatar {
  flex: 0 0 auto;
  font-size: 24px;
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
  border-radius: 12px;
}

.provider-card__avatar :deep(img) {
  border-radius: 12px;
  object-fit: cover;
}

.provider-card__text {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.provider-card__text h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  line-height: 1.3;
}

.provider-card__url {
  max-width: min(640px, 58vw);
  margin: 0;
  overflow: hidden;
  color: var(--text-weak-color);
  font-size: 13px;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.provider-card__actions {
  display: flex;
  gap: 2px;
  align-items: center;
  flex: 0 0 auto;
}

.provider-card__model-count {
  display: inline-flex;
  align-items: center;
  margin-right: 6px;
  min-height: 34px;
  padding: 0 14px;
  white-space: nowrap;
  font-size: 14px;
  font-weight: 500;
}

.collapse-button {
  width: 36px;
  height: 36px;
  padding: 0;
  font-size: 18px;
}

.collapse-button :deep(.el-icon) {
  font-size: 18px;
}

.provider-card__body {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-top: 18px;
}

.provider-card__input {
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
  width: 100%;
  white-space: nowrap;
}

.provider-card__model-actions :deep(.el-button + .el-button) {
  margin-left: 0;
}

.dialog-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.model-dialog :deep(.el-dialog__body) {
  padding-right: 32px;
  padding-left: 32px;
}

.cost-default-note {
  margin-bottom: 12px;
  padding: 12px 14px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 12px;
  background: var(--el-fill-color-lighter);
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 1.6;
}

.cost-pricing-section,
.model-more-settings-section {
  margin-bottom: 12px;
}

.model-more-settings-section :deep(.el-collapse-item__content) {
  padding-bottom: 6px;
}

.cost-section-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.cost-section-header h4 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
}

.cost-section-header p {
  margin: 4px 0 0;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 1.5;
}

.cost-currency-toggle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
  padding: 12px 14px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 12px;
  background: var(--el-fill-color-lighter);
}

.cost-currency-toggle strong,
.cost-currency-toggle span {
  display: block;
}

.cost-currency-toggle strong {
  font-size: 13px;
}

.cost-currency-toggle span {
  margin-top: 4px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 1.5;
}

.cost-currency-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 12px;
  color: var(--el-text-color-secondary);
  background: var(--el-fill-color-blank);
  font-size: 12px;
}

.cost-currency-summary strong {
  color: var(--el-text-color-primary);
  font-size: 13px;
}

.cost-advanced-divider {
  height: 1px;
  margin: 18px 0 14px;
  background: var(--el-border-color-lighter);
}

.form-label-with-help {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.form-help-icon {
  color: var(--text-weak-color);
  cursor: help;
  font-size: 15px;
}

.form-help-trigger {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
}

.model-number-input {
  width: 100%;
}

.model-number-input :deep(.el-input) {
  width: 100%;
}

.model-type-select {
  width: 100%;
}

.cost-tier-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.cost-tier-row {
  display: grid;
  grid-template-columns: minmax(160px, 1fr) minmax(120px, 1fr) minmax(120px, 1fr) auto;
  gap: 8px;
  align-items: center;
}

.cost-tier-row--head {
  padding: 0 4px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.cost-tier-row--head span:last-child {
  text-align: center;
}

.cost-tier-row__input {
  width: 100%;
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

@media (max-width: 480px) {
  .page-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .provider-card__header {
    flex-direction: column;
  }

  .provider-card__identity {
    width: 100%;
  }

  .provider-card__text {
    flex: 1 1 auto;
  }

  .provider-card__url {
    max-width: 100%;
  }

  .provider-card__actions {
    align-self: flex-end;
    flex-wrap: wrap;
    justify-content: flex-end;
  }

  .cost-tier-row {
    grid-template-columns: 1fr;
  }

  .cost-tier-row--head {
    display: none;
  }

  .cost-section-header,
  .cost-currency-toggle,
  .cost-currency-summary {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
