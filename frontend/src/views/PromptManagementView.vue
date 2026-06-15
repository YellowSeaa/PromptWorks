<template>
  <div class="page">
    <section class="page-header">
      <div class="page-header__text">
        <h2>{{ t('promptManagement.headerTitle') }}</h2>
        <p class="page-desc">{{ t('promptManagement.headerDescription') }}</p>
      </div>
      <el-button type="primary" :icon="Plus" @click="openCreateDialog">
        {{ t('promptManagement.createPrompt') }}
      </el-button>
    </section>

    <div class="page-filters">
      <el-tabs v-model="activeClassKey" type="card" class="class-tabs">
        <el-tab-pane :label="t('promptManagement.allClasses')" name="all" />
        <el-tab-pane
          v-for="item in classOptions"
          :key="item.id"
          :label="item.name"
          :name="String(item.id)"
        />
      </el-tabs>

      <div class="filter-row">
        <el-input
          v-model="searchKeyword"
          :placeholder="t('promptManagement.searchPlaceholder')"
          clearable
          class="filter-item search-input"
          :prefix-icon="Search"
        />
        <el-select
          v-model="selectedTagIds"
          multiple
          collapse-tags
          collapse-tags-tooltip
          class="filter-item tag-select"
          :placeholder="t('promptManagement.tagPlaceholder')"
          clearable
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
        <el-select v-model="sortKey" class="filter-item sort-select" :placeholder="t('promptManagement.sortPlaceholder')">
          <el-option :label="t('promptManagement.sortDefault')" value="default" />
          <el-option :label="t('promptManagement.sortCreatedAt')" value="created_at" />
          <el-option :label="t('promptManagement.sortUpdatedAt')" value="updated_at" />
          <el-option :label="t('promptManagement.sortAuthor')" value="author" />
        </el-select>
      </div>
    </div>

    <el-alert
      v-if="loadError"
      :title="loadError"
      type="error"
      show-icon
      class="data-alert"
    />

    <el-skeleton v-else-if="isLoading" animated :rows="6" />

    <template v-else>
      <div v-if="filteredPrompts.length" class="card-grid">
        <div v-for="prompt in filteredPrompts" :key="prompt.id" class="card-grid__item">
          <el-card class="prompt-card" shadow="hover" @click="goDetail(prompt.id)">
            <div class="prompt-card__header">
              <div>
                <p class="prompt-class">{{ prompt.prompt_class.name }}</p>
                <h3 class="prompt-title">{{ prompt.name }}</h3>
              </div>
              <el-tag type="success" round size="small">
                {{ t('promptManagement.currentVersion') }}
                {{ prompt.current_version?.version ?? t('common.notEnabled') }}
              </el-tag>
            </div>
            <p class="prompt-desc">{{ prompt.description ?? t('common.descriptionNone') }}</p>
            <div class="prompt-meta">
              <div class="meta-item">
                <span class="meta-label">{{ t('promptManagement.author') }}</span>
                <span>{{ prompt.author ?? t('common.notSet') }}</span>
              </div>
              <div class="meta-item">
                <span class="meta-label">{{ t('promptManagement.createdAt') }}</span>
                <span>{{ formatDate(prompt.created_at) }}</span>
              </div>
              <div class="meta-item">
                <span class="meta-label">{{ t('promptManagement.updatedAt') }}</span>
                <span>{{ formatDate(prompt.updated_at) }}</span>
              </div>
            </div>
            <div class="prompt-tags">
              <div class="prompt-tags__list">
                <el-tag
                  v-for="tag in prompt.tags"
                  :key="tag.id"
                  size="small"
                  effect="dark"
                  :style="{ backgroundColor: tag.color, borderColor: tag.color }"
                >
                  {{ tag.name }}
                </el-tag>
              </div>
              <el-popconfirm
                :title="t('promptManagement.confirmDelete', { name: prompt.name })"
                :confirm-button-text="t('promptManagement.delete')"
                :cancel-button-text="t('promptManagement.cancel')"
                icon=""
                @confirm="() => handleDeletePrompt(prompt)"
              >
                <template #reference>
                  <el-button
                    type="danger"
                    text
                    size="small"
                    class="card-delete"
                    :loading="isDeleting(prompt.id)"
                    @click.stop
                  >
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </template>
              </el-popconfirm>
            </div>
          </el-card>
        </div>
      </div>
      <el-empty v-else :description="t('promptManagement.emptyDescription')" />
    </template>

    <el-dialog v-model="createDialogVisible" :title="t('promptManagement.dialogTitle')" width="720px">
      <el-alert
        v-if="!classOptions.length"
        :title="t('promptManagement.dialogAlert')"
        type="warning"
        show-icon
        class="dialog-alert"
      />
      <el-form
        ref="createFormRef"
        :model="promptForm"
        :rules="createRules"
        label-width="100px"
        class="dialog-form"
      >
        <el-form-item :label="t('promptManagement.form.title')" prop="name">
          <el-input v-model="promptForm.name" :placeholder="t('promptManagement.form.titlePlaceholder')" />
        </el-form-item>
        <el-form-item :label="t('promptManagement.form.author')">
          <el-input v-model="promptForm.author" :placeholder="t('promptManagement.form.authorPlaceholder')" />
        </el-form-item>
        <el-form-item :label="t('promptManagement.form.description')">
          <el-input
            v-model="promptForm.description"
            type="textarea"
            :autosize="{ minRows: 2, maxRows: 4 }"
            :placeholder="t('promptManagement.form.descriptionPlaceholder')"
          />
        </el-form-item>
        <el-form-item :label="t('promptManagement.form.class')" prop="classId">
          <el-select v-model="promptForm.classId" :placeholder="t('promptManagement.form.classPlaceholder')">
            <el-option
              v-for="item in classOptions"
              :key="item.id"
              :label="item.name"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('promptManagement.form.tags')">
          <el-select
            v-model="promptForm.tagIds"
            multiple
            collapse-tags
            collapse-tags-tooltip
            :placeholder="t('promptManagement.form.tagsPlaceholder')"
          >
            <el-option
              v-for="tag in tagOptions"
              :key="tag.id"
              :label="tag.name"
              :value="tag.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('promptManagement.form.version')" prop="version">
          <el-input v-model="promptForm.version" :placeholder="t('promptManagement.form.versionPlaceholder')" />
        </el-form-item>
        <el-form-item :label="t('promptManagement.form.content')" prop="content">
          <el-input
            v-model="promptForm.content"
            type="textarea"
            :autosize="{ minRows: 6, maxRows: 12 }"
            :placeholder="t('promptManagement.form.contentPlaceholder')"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">{{ t('promptManagement.footer.cancel') }}</el-button>
        <el-button type="primary" :loading="isSubmitting" @click="handleCreatePrompt">
          {{ t('promptManagement.footer.submit') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { Delete, Plus, Search } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { listPrompts, createPrompt, deletePrompt, type HttpError } from '../api/prompt'
import { listPromptClasses, type PromptClassStats } from '../api/promptClass'
import { listPromptTags, type PromptTagStats } from '../api/promptTag'
import type { Prompt } from '../types/prompt'
import { useI18n } from 'vue-i18n'

type SortKey = 'default' | 'created_at' | 'updated_at' | 'author'

interface PromptFormState {
  name: string
  description: string
  author: string
  classId: number | null
  tagIds: number[]
  version: string
  content: string
}

const router = useRouter()
const { t, locale } = useI18n()
const prompts = ref<Prompt[]>([])
const promptClasses = ref<PromptClassStats[]>([])
const promptTags = ref<PromptTagStats[]>([])
const isLoading = ref(false)
const promptError = ref<string | null>(null)
const collectionError = ref<string | null>(null)
const loadError = computed(() => promptError.value ?? collectionError.value)
const isSubmitting = ref(false)
const deletingIds = ref<number[]>([])

const activeClassKey = ref('all')
const searchKeyword = ref('')
const selectedTagIds = ref<number[]>([])
const sortKey = ref<SortKey>('default')

const classOptions = computed(() => {
  return promptClasses.value
    .map((item) => ({ id: item.id, name: item.name }))
    .sort((a, b) => a.name.localeCompare(b.name, locale.value))
})

const tagOptions = computed(() => {
  return promptTags.value
    .map((tag) => ({ id: tag.id, name: tag.name, color: tag.color }))
    .sort((a, b) => a.name.localeCompare(b.name, locale.value))
})

const dateFormatter = computed(
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

function formatDate(value: string | null | undefined) {
  if (!value) return '--'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : dateFormatter.value.format(date)
}

function matchKeyword(keyword: string, prompt: Prompt) {
  if (!keyword.trim()) return true
  const target = keyword.trim().toLowerCase()
  const fields: (string | null | undefined)[] = [
    prompt.name,
    prompt.author,
    prompt.description,
    prompt.current_version?.content,
    prompt.versions.map((item) => item.content).join('\n')
  ]
  return fields.some((field) => field?.toLowerCase().includes(target))
}

function sortPrompts(list: Prompt[]) {
  const sorted = [...list]
  switch (sortKey.value) {
    case 'created_at':
      sorted.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
      break
    case 'updated_at':
      sorted.sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
      break
    case 'author':
      sorted.sort((a, b) => {
        const authorA = a.author ?? ''
        const authorB = b.author ?? ''
        const cmp = authorA.localeCompare(authorB, locale.value)
        if (cmp !== 0) return cmp
        return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
      })
      break
    default:
      sorted.sort((a, b) => {
        const diff = new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
        if (diff !== 0) return diff
        return a.name.localeCompare(b.name, locale.value)
      })
  }
  return sorted
}

const filteredPrompts = computed(() => {
  const keyword = searchKeyword.value
  const activeClass = activeClassKey.value
  const tagIds = selectedTagIds.value

  const list = prompts.value.filter((prompt) => {
    if (activeClass !== 'all' && String(prompt.prompt_class.id) !== activeClass) {
      return false
    }
    if (!matchKeyword(keyword, prompt)) {
      return false
    }
    if (tagIds.length) {
      const tagSet = new Set(prompt.tags.map((tag) => tag.id))
      if (!tagIds.every((tagId) => tagSet.has(tagId))) {
        return false
      }
    }
    return true
  })

  return sortPrompts(list)
})

const createDialogVisible = ref(false)
const createFormRef = ref<FormInstance>()
const promptForm = reactive<PromptFormState>({
  name: '',
  description: '',
  author: '',
  classId: null,
  tagIds: [],
  version: '',
  content: ''
})

const createRules = computed<FormRules<PromptFormState>>(() => ({
  name: [
    {
      validator: (_rule, value: string, callback) => {
        if (value.trim()) {
          callback()
          return
        }
        callback(new Error(t('promptManagement.messages.missingRequired')))
      },
      trigger: 'blur'
    }
  ],
  classId: [
    {
      required: true,
      message: t('promptManagement.messages.selectClass'),
      trigger: 'change'
    }
  ],
  version: [
    {
      validator: (_rule, value: string, callback) => {
        if (value.trim()) {
          callback()
          return
        }
        callback(new Error(t('promptManagement.messages.missingRequired')))
      },
      trigger: 'blur'
    }
  ],
  content: [
    {
      validator: (_rule, value: string, callback) => {
        if (value.trim()) {
          callback()
          return
        }
        callback(new Error(t('promptManagement.messages.missingRequired')))
      },
      trigger: 'blur'
    }
  ]
}))

function resetPromptForm() {
  promptForm.name = ''
  promptForm.description = ''
  promptForm.author = ''
  promptForm.classId = classOptions.value[0]?.id ?? null
  promptForm.tagIds = []
  promptForm.version = ''
  promptForm.content = ''
}

function openCreateDialog() {
  resetPromptForm()
  createDialogVisible.value = true
  nextTick(() => {
    createFormRef.value?.clearValidate()
  })
}

function isDeleting(id: number) {
  return deletingIds.value.includes(id)
}

async function handleCreatePrompt() {
  if (isSubmitting.value) {
    return
  }

  const isValid = await createFormRef.value?.validate().catch(() => false)
  if (!isValid) {
    return
  }

  isSubmitting.value = true
  const payload = {
    name: promptForm.name.trim(),
    description: promptForm.description.trim() || null,
    author: promptForm.author.trim() || null,
    class_id: promptForm.classId,
    version: promptForm.version.trim(),
    content: promptForm.content,
    tag_ids: promptForm.tagIds.length ? promptForm.tagIds : []
  }

  createPrompt(payload)
    .then(async () => {
      ElMessage.success(t('promptManagement.messages.createSuccess'))
      createDialogVisible.value = false
      await Promise.all([fetchPrompts(), fetchCollections()])
    })
    .catch((error) => {
      ElMessage.error(extractErrorMessage(error, t('promptManagement.messages.createFailed')))
    })
    .finally(() => {
      isSubmitting.value = false
    })
}

function goDetail(id: number) {
  router.push({ name: 'prompt-detail', params: { id: String(id) } })
}

async function handleDeletePrompt(target: Prompt) {
  if (isDeleting(target.id)) {
    return
  }
  deletingIds.value = [...deletingIds.value, target.id]
  try {
    await deletePrompt(target.id)
    ElMessage.success(t('promptManagement.messages.deleteSuccess', { name: target.name }))
    await Promise.all([fetchPrompts(), fetchCollections()])
  } catch (error) {
    ElMessage.error(extractErrorMessage(error, t('promptManagement.messages.deleteFailed')))
  } finally {
    deletingIds.value = deletingIds.value.filter((item) => item !== target.id)
  }
}

function extractErrorMessage(error: unknown, fallback: string): string {
  if (error && typeof error === 'object' && 'status' in error) {
    const httpError = error as HttpError
    if (httpError.payload && typeof httpError.payload === 'object' && 'detail' in httpError.payload) {
      const detail = (httpError.payload as Record<string, unknown>).detail
      if (typeof detail === 'string' && detail.trim()) {
        return detail
      }
    }
    if (httpError.status === 404) {
      return t('promptManagement.messages.resourceNotFound')
    }
  }
  if (error instanceof Error && error.message) {
    return error.message
  }
  return fallback
}

async function fetchPrompts() {
  try {
    const data = await listPrompts({ limit: 200 })
    prompts.value = data
    promptError.value = null
  } catch (error) {
    const message = extractErrorMessage(error, t('promptManagement.messages.loadPromptFailed'))
    promptError.value = message
    ElMessage.error(message)
    prompts.value = []
  }
}

async function fetchCollections() {
  try {
    const [classes, tagResponse] = await Promise.all([
      listPromptClasses(),
      listPromptTags()
    ])
    promptClasses.value = classes
    promptTags.value = tagResponse.items
    collectionError.value = null
  } catch (error) {
    const message = extractErrorMessage(error, t('promptManagement.messages.loadCollectionFailed'))
    collectionError.value = message
    ElMessage.error(message)
    promptClasses.value = []
    promptTags.value = []
  }
}

async function bootstrap() {
  isLoading.value = true
  promptError.value = null
  collectionError.value = null
  await Promise.all([fetchPrompts(), fetchCollections()])
  isLoading.value = false
}

watch(classOptions, (options) => {
  if (activeClassKey.value !== 'all') {
    const exists = options.some((item) => String(item.id) === activeClassKey.value)
    if (!exists) {
      activeClassKey.value = 'all'
    }
  }
  if (!options.length) {
    promptForm.classId = null
    return
  }
  if (promptForm.classId === null || !options.some((item) => item.id === promptForm.classId)) {
    promptForm.classId = options[0].id
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
  void bootstrap()
})
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

.page-filters {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.class-tabs {
  --el-tabs-header-height: 40px;
}

.filter-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
}

.filter-item {
  flex: 1;
  min-width: 200px;
}

.search-input {
  max-width: 320px;
}

.tag-select {
  max-width: 320px;
}

.sort-select {
  width: 180px;
  flex: initial;
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

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 16px;
  align-items: stretch;
}

.data-alert {
  margin-bottom: 12px;
}

.card-grid__item {
  height: 100%;
}

.prompt-card {
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  border-radius: 12px;
  border: 1px solid transparent;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.prompt-card:hover {
  transform: translateY(-4px);
  border-color: #409eff33;
}

.prompt-card__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.prompt-class {
  margin: 0 0 4px;
  font-size: 13px;
  color: var(--text-weak-color);
}

.prompt-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.prompt-desc {
  margin: 16px 0;
  color: var(--header-text-color);
  font-size: 14px;
  line-height: 1.6;
  flex: 1;
}

.prompt-meta {
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 13px;
  color: var(--text-weak-color);
  margin-bottom: 12px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.meta-label {
  font-weight: 500;
  min-width: 64px;
}

.prompt-tags {
  margin-top: auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.prompt-tags__list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.card-delete {
  color: var(--el-color-danger);
  display: flex;
  align-items: center;
  padding: 4px;
}

.dialog-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.dialog-alert {
  margin-bottom: 12px;
}
</style>
