<template>
  <div class="version-create-page">
    <el-breadcrumb separator="/" class="version-breadcrumb">
      <el-breadcrumb-item>
        <span class="breadcrumb-link" @click="goPromptManagement">{{ t('menu.prompt') }}</span>
      </el-breadcrumb-item>
      <el-breadcrumb-item>
        <span class="breadcrumb-link" @click="goPromptDetail">
          {{ promptDetail?.name ?? t('promptVersionCreate.breadcrumb.fallback') }}
        </span>
      </el-breadcrumb-item>
      <el-breadcrumb-item>{{ t('promptVersionCreate.breadcrumb.current') }}</el-breadcrumb-item>
    </el-breadcrumb>

    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      show-icon
    />

    <el-skeleton v-else-if="isLoading" animated :rows="5" />

    <el-empty v-else-if="!promptDetail" :description="t('promptVersionCreate.empty')" />

    <el-card v-else>
      <template #header>
        <div class="card-header">
          <h3>{{ t('promptVersionCreate.card.title') }}</h3>
          <span class="card-subtitle">{{ t('promptVersionCreate.card.subtitle') }}</span>
        </div>
      </template>
      <el-form label-width="90px" class="version-form">
        <el-form-item :label="t('promptVersionCreate.form.versionLabel')">
          <el-input v-model="form.version" :placeholder="t('promptVersionCreate.form.versionPlaceholder')" />
        </el-form-item>
        <el-form-item :label="t('promptVersionCreate.form.summaryLabel')">
          <el-input v-model="form.summary" :placeholder="t('promptVersionCreate.form.summaryPlaceholder')" />
        </el-form-item>
        <el-form-item :label="t('promptVersionCreate.form.contentLabel')">
          <el-input
            v-model="form.content"
            type="textarea"
            :rows="12"
            :placeholder="t('promptVersionCreate.form.contentPlaceholder')"
          />
        </el-form-item>
        <el-form-item :label="t('promptVersionCreate.form.baseVersionLabel')">
          <el-select v-model="form.baseVersionId" clearable :placeholder="t('promptVersionCreate.form.baseVersionPlaceholder')">
            <el-option
              v-for="version in promptDetail.versions"
              :key="version.id"
              :label="version.version"
              :value="version.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-space>
            <el-button type="primary" :loading="isSubmitting" @click="handleSubmit">
              {{ t('promptVersionCreate.actions.submit') }}
            </el-button>
            <el-button @click="goPromptDetail">{{ t('promptVersionCreate.actions.cancel') }}</el-button>
          </el-space>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { usePromptDetail } from '../composables/usePromptDetail'
import { updatePrompt, type HttpError } from '../api/prompt'
import { useI18n } from 'vue-i18n'

const router = useRouter()
const route = useRoute()
const { t } = useI18n()

const currentId = computed(() => {
  const raw = Number(route.params.id)
  return Number.isFinite(raw) && raw > 0 ? raw : null
})

const {
  prompt: promptDetail,
  loading: isLoading,
  error: errorMessage
} = usePromptDetail(currentId)

const form = reactive({
  version: '',
  summary: '',
  content: '',
  baseVersionId: undefined as number | undefined
})

const isSubmitting = ref(false)

watch(
  () => promptDetail.value?.current_version?.id,
  (versionId) => {
    if (typeof versionId === 'number') {
      form.baseVersionId = versionId
    }
  },
  { immediate: true }
)

watch(
  () => form.baseVersionId,
  (versionId) => {
    if (typeof versionId !== 'number') {
      return
    }
    const baseVersion = promptDetail.value?.versions.find((version) => version.id === versionId)
    if (baseVersion) {
      form.content = baseVersion.content
    }
  }
)

function extractErrorMessage(error: unknown): string {
  if (error && typeof error === 'object' && 'payload' in error) {
    const httpError = error as HttpError
    const detail = (httpError.payload as Record<string, unknown> | null)?.detail
    if (typeof detail === 'string' && detail.trim()) {
      return detail
    }
    if (httpError.status === 404) {
      return t('promptVersionCreate.messages.promptNotFound')
    }
  }
  if (error instanceof Error && error.message) {
    return error.message
  }
  return t('promptVersionCreate.messages.submitFailed')
}

async function handleSubmit() {
  if (!currentId.value) {
    ElMessage.error(t('promptVersionCreate.messages.idMissing'))
    return
  }
  if (!form.version.trim() || !form.content.trim()) {
    ElMessage.warning(t('promptVersionCreate.messages.required'))
    return
  }

  isSubmitting.value = true
  try {
    await updatePrompt(currentId.value, {
      version: form.version.trim(),
      content: form.content
    })
    ElMessage.success(t('promptVersionCreate.messages.success'))
    router.push({ name: 'prompt-detail', params: { id: currentId.value } })
  } catch (error) {
    ElMessage.error(extractErrorMessage(error))
  } finally {
    isSubmitting.value = false
  }
}

function goPromptDetail() {
  if (!currentId.value) {
    router.push({ name: 'prompt-management' })
    return
  }
  router.push({ name: 'prompt-detail', params: { id: currentId.value } })
}

function goPromptManagement() {
  router.push({ name: 'prompt-management' })
}
</script>

<style scoped>
.version-create-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.version-breadcrumb {
  font-size: 13px;
}

.breadcrumb-link {
  cursor: pointer;
  color: inherit;
}

.card-header {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.card-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.card-subtitle {
  font-size: 13px;
  color: var(--text-weak-color);
}

.version-form {
  max-width: 720px;
}
</style>
