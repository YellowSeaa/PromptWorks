<template>
  <div class="page">
    <section class="page-header">
      <div class="page-header__text">
        <h2>{{ t('quickTest.headerTitle') }}</h2>
        <p class="page-desc">{{ t('quickTest.headerDescription') }}</p>
      </div>
      <div class="page-header__actions">
        <el-select
          class="history-select"
          :model-value="activeSessionId"
          :placeholder="t('quickTest.historyPlaceholder')"
          filterable
          @change="handleSessionChange"
        >
          <el-option
            v-for="option in sessionOptions"
            :key="option.value"
            :label="option.label"
            :value="option.value"
          />
        </el-select>
        <el-button type="primary" @click="handleNewChat" :disabled="!canCreateNewChat">
          {{ t('quickTest.newChat') }}
        </el-button>
      </div>
    </section>

    <div class="test-layout">
      <el-card class="model-card">
        <template #header>
          <div class="card-header">
            <span>{{ t('quickTest.sections.model') }}</span>
          </div>
        </template>
        <el-form label-position="top" class="model-form">
          <el-form-item :label="t('quickTest.form.modelLabel')">
            <el-cascader
              v-model="selectedModelPath"
              :options="modelOptions"
              :props="cascaderProps"
              :show-all-levels="false"
              clearable
              filterable
              :placeholder="t('quickTest.form.modelPlaceholder')"
              :disabled="isModelLoading"
            />
          </el-form-item>
          <el-form-item :label="t('quickTest.form.temperatureLabel')">
            <div class="temperature-box">
              <el-slider
                v-model="temperature"
                :min="0"
                :max="2"
                :step="0.01"
              />
              <el-input-number
                v-model="temperature"
                :min="0"
                :max="2"
                :step="0.1"
                :precision="2"
              />
            </div>
          </el-form-item>
          <el-form-item :label="t('quickTest.form.extraParamsLabel')" :error="extraParamsError">
            <el-input
              v-model="extraParams"
              type="textarea"
              :autosize="{ minRows: 6, maxRows: 10 }"
              :placeholder="t('quickTest.form.extraParamsPlaceholder')"
            />
          </el-form-item>
        </el-form>
      </el-card>

      <el-card class="chat-card">
        <template #header>
          <div class="card-header">
            <span>{{ t('quickTest.sections.chat') }}</span>
            <div class="card-header__actions">
              <div class="card-header__toggle">
                <span class="card-header__toggle-label">{{ t('quickTest.markdown.label') }}</span>
                <el-tooltip
                  effect="dark"
                  :content="t('quickTest.markdown.tooltip')"
                  placement="top"
                >
                  <el-switch
                    v-model="isMarkdownEnabled"
                    class="chat-toggle-switch"
                    size="small"
                    inline-prompt
                    :active-text="t('quickTest.markdown.on')"
                    :inactive-text="t('quickTest.markdown.off')"
                  />
                </el-tooltip>
              </div>
              <div class="card-header__toggle">
                <span class="card-header__toggle-label">{{ t('quickTest.stream.label') }}</span>
                <el-tooltip
                  effect="dark"
                  :content="t('quickTest.stream.tooltip')"
                  placement="top"
                >
                  <el-switch
                    v-model="isStreamingEnabled"
                    class="chat-toggle-switch"
                    size="small"
                    inline-prompt
                    :active-text="t('quickTest.stream.on')"
                    :inactive-text="t('quickTest.stream.off')"
                    :disabled="isSending"
                  />
                </el-tooltip>
              </div>
            </div>
          </div>
        </template>
        <div class="chat-panel">
          <div class="chat-messages" ref="chatScrollRef">
            <template v-if="!messages.length">
              <el-empty :description="t('quickTest.chat.empty')" />
            </template>
            <template v-else>
              <div
                v-for="message in messages"
                :key="message.id"
                :class="['chat-message', `chat-message--${message.role}`]"
              >
                <el-bubble
                  :placement="message.role === 'user' ? 'end' : 'start'"
                  variant="filled"
                  shape="corner"
                  :loading="message.isStreaming && !message.content"
                  :typing="message.isStreaming && !!message.content"
                  :class="['chat-message__bubble', `chat-message__bubble--${message.role}`]"
                  :header-class="resolveBubbleHeaderClass(message)"
                  :content-class="resolveBubbleContentClass(message)"
                  :footer-class="message.tokens ? resolveBubbleFooterClass(message) : undefined"
                >
                  <template #avatar>
                    <el-avatar :size="36" class="chat-message__avatar">
                      <template v-if="message.role === 'assistant'">
                        <img
                          v-if="message.avatarUrl"
                          :src="message.avatarUrl"
                          :alt="message.avatarAlt"
                        />
                        <span v-else>{{ message.avatarEmoji ?? message.avatarFallback }}</span>
                      </template>
                      <template v-else>
                        <img
                          v-if="userAvatar"
                          :src="userAvatar"
                          :alt="t('quickTest.chat.avatar.user')"
                        />
                        <span v-else>{{ t('quickTest.chat.avatar.self') }}</span>
                      </template>
                    </el-avatar>
                  </template>
                  <template #header>
                    <p class="chat-message__name">{{ message.displayName }}</p>
                  </template>
                  <template #default>
                    <div
                      v-if="isMarkdownEnabled"
                      class="chat-message__content chat-message__content--markdown"
                      v-html="renderMessageMarkdown(message.content)"
                    />
                    <span
                      v-else
                      class="chat-message__content chat-message__content--text"
                    >
                      {{ message.content }}
                    </span>
                  </template>
                  <template v-if="message.tokens" #footer>
                    <div class="chat-message__meta">
                      <span>{{ t('quickTest.chat.tokens.input') }}：{{ formatTokenValue(message.tokens.input) }}</span>
                      <span>{{ t('quickTest.chat.tokens.output') }}：{{ formatTokenValue(message.tokens.output) }}</span>
                      <span>{{ t('quickTest.chat.tokens.total') }}：{{ formatTokenValue(message.tokens.total) }}</span>
                    </div>
                  </template>
                </el-bubble>
              </div>
            </template>
          </div>
          <div class="chat-input">
            <el-input
              v-model="chatInput"
              type="textarea"
              :autosize="{ minRows: 3, maxRows: 6 }"
              :placeholder="t('quickTest.chat.inputPlaceholder')"
              :disabled="isSending"
              @keydown.enter="handleEnterKey"
              @compositionstart="handleCompositionStart"
              @compositionend="handleCompositionEnd"
            />
            <div class="chat-input__footer">
              <el-cascader
                v-model="selectedPromptPath"
                :options="promptOptions"
                :props="promptCascaderProps"
                :show-all-levels="false"
                class="prompt-selector"
                clearable
                filterable
                :placeholder="t('quickTest.chat.promptPlaceholder')"
                :disabled="isPromptLoading"
              />
              <div class="chat-input__actions">
                <el-button plain @click="handleSaveAsPrompt">{{ t('quickTest.chat.save') }}</el-button>
                <el-button type="primary" @click="handleSend" :loading="isSending">
                  {{ t('quickTest.chat.send') }}
                </el-button>
              </div>
            </div>
          </div>
        </div>
      </el-card>
    </div>

    <el-dialog
      v-model="savePromptDialogVisible"
      :title="t('quickTest.dialog.title')"
      width="560px"
      :close-on-click-modal="false"
    >
      <el-form label-width="96px" class="save-prompt-form">
        <el-form-item :label="t('quickTest.dialog.modeLabel')">
          <el-radio-group v-model="savePromptMode">
            <el-radio-button label="new">{{ t('quickTest.dialog.modes.new') }}</el-radio-button>
            <el-radio-button label="existing">{{ t('quickTest.dialog.modes.existing') }}</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <template v-if="savePromptMode === 'new'">
          <el-form-item :label="t('quickTest.dialog.classLabel')">
            <div class="save-prompt-class">
              <el-select
                v-model="savePromptForm.promptClassId"
                class="save-prompt-select"
                clearable
                filterable
                :placeholder="t('quickTest.dialog.classPlaceholder')"
              >
                <el-option
                  v-for="option in promptClassOptions"
                  :key="option.value"
                  :label="option.label"
                  :value="option.value"
                />
              </el-select>
            </div>
          </el-form-item>
          <el-form-item :label="t('quickTest.dialog.nameLabel')">
            <el-input
              v-model="savePromptForm.promptName"
              :placeholder="t('quickTest.dialog.namePlaceholder')"
            />
          </el-form-item>
          <el-form-item :label="t('quickTest.dialog.tagsLabel')">
            <el-select
              v-model="savePromptForm.promptTagIds"
              class="save-prompt-select"
              multiple
              filterable
              clearable
              :placeholder="t('quickTest.dialog.tagsPlaceholder')"
            >
              <el-option
                v-for="option in promptTagOptions"
                :key="option.value"
                :label="option.label"
                :value="option.value"
              />
            </el-select>
          </el-form-item>
          <el-form-item :label="t('quickTest.dialog.versionLabel')">
            <el-input
              v-model="savePromptForm.promptVersion"
              :placeholder="t('quickTest.dialog.versionPlaceholderNew')"
            />
          </el-form-item>
          <el-form-item :label="t('quickTest.dialog.descriptionLabel')">
            <el-input
              v-model="savePromptForm.promptDescription"
              type="textarea"
              :autosize="{ minRows: 2, maxRows: 4 }"
              :placeholder="t('quickTest.dialog.descriptionPlaceholder')"
            />
          </el-form-item>
        </template>
        <template v-else>
          <el-form-item :label="t('quickTest.dialog.promptLabel')">
            <el-select
              v-model="savePromptForm.promptId"
              class="save-prompt-select"
              filterable
              :placeholder="t('quickTest.dialog.promptPlaceholder')"
            >
              <el-option
                v-for="option in existingPromptOptions"
                :key="option.value"
                :label="option.label"
                :value="option.value"
              />
            </el-select>
          </el-form-item>
          <el-form-item :label="t('quickTest.dialog.versionLabel')">
            <el-input
              v-model="savePromptForm.promptVersion"
              :placeholder="t('quickTest.dialog.versionPlaceholderExisting')"
            />
          </el-form-item>
        </template>

        <el-form-item :label="t('quickTest.dialog.contentLabel')">
          <el-input
            v-model="savePromptForm.promptContent"
            type="textarea"
            :autosize="{ minRows: 4, maxRows: 12 }"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="handleSavePromptCancel">{{ t('quickTest.dialog.actions.cancel') }}</el-button>
        <el-button type="primary" :loading="savePromptSubmitting" @click="handleSavePromptConfirm">
          {{ t('quickTest.dialog.actions.save') }}
        </el-button>
      </template>
    </el-dialog>

  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { ElBubble } from 'element-plus-x'
import 'element-plus-x/theme-chalk/el-bubble.css'
import MarkdownIt from 'markdown-it'
import { listLLMProviders, type LLMProvider } from '../api/llmProvider'
import {
  streamQuickTest,
  invokeQuickTest,
  fetchQuickTestHistory,
  type QuickTestHistoryItem
} from '../api/quickTest'
import {
  listPrompts,
  createPrompt,
  createPromptVersion
} from '../api/prompt'
import type { PromptCreatePayload } from '../api/prompt'
import type { ChatMessagePayload } from '../types/llm'
import type { Prompt } from '../types/prompt'
import { listPromptTags, type PromptTagStats } from '../api/promptTag'
import { useI18n } from 'vue-i18n'
import { useTestingSettings, DEFAULT_TIMEOUT_SECONDS } from '../composables/useTestingSettings'

interface CascaderOptionNode {
  value: number | string
  label: string
  children?: CascaderOptionNode[]
  disabled?: boolean
}

interface QuickTestMessage {
  id: number
  role: 'user' | 'assistant'
  content: string
  displayName: string
  avatarUrl?: string | null
  avatarEmoji?: string | null
  avatarFallback?: string
  avatarAlt?: string
  isStreaming?: boolean
  tokens?: {
    input: number | null
    output: number | null
    total: number | null
  }
}

interface ChatSession {
  id: number
  title: string
  messages: QuickTestMessage[]
  createdAt: number
  updatedAt: number
  autoTitle: boolean
  isPersisted: boolean
  hasInteraction: boolean
  providerId: number | null
  providerName: string | null
  providerLogoEmoji: string | null
  providerLogoUrl: string | null
  modelId: number | null
  modelName: string | null
  promptId: number | null
  promptVersionId: number | null
}

interface HistoryMatchCriteria {
  requestSignature?: string
  responseText?: string | null
  providerId?: number
  modelName?: string | null
  draftId?: number
}

const cascaderProps = reactive({
  expandTrigger: 'hover' as const,
  emitPath: true
})

const promptCascaderProps = reactive({
  expandTrigger: 'hover' as const,
  emitPath: true
})

const { t } = useI18n()

const PROMPT_FETCH_LIMIT = 200
const DEFAULT_QUICK_TEST_TIMEOUT_SECONDS = DEFAULT_TIMEOUT_SECONDS

const {
  quickTestTimeout: configuredQuickTestTimeout,
  fetchTimeouts: fetchTestingTimeouts
} = useTestingSettings()

const isModelLoading = ref(false)
const isPromptLoading = ref(false)
const isSending = ref(false)
const modelOptions = ref<CascaderOptionNode[]>([])
const promptOptions = ref<CascaderOptionNode[]>([])
const selectedModelPath = ref<(number | string)[]>([])
const selectedPromptPath = ref<(number | string)[]>([])
const temperature = ref(0.7)
const extraParams = ref('{}')
const extraParamsError = ref<string | null>(null)
const chatInput = ref('')
const chatSessions = ref<ChatSession[]>([])
const activeSessionId = ref<number | null>(null)
let sessionSeed = 0
const messages = ref<QuickTestMessage[]>([])
const userAvatar = ''
const isComposing = ref(false)
const isStreamingEnabled = ref(true)
const isMarkdownEnabled = ref(true)

const promptTags = ref<PromptTagStats[]>([])

const providerMap = ref(new Map<number, LLMProvider>())
const promptMap = ref(new Map<number, Prompt>())

let activeStreamingMessageId: number | null = null
let streamingScrollScheduled = false
const markdownRenderer = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true
})

const sessionOptions = computed(() =>
  [...chatSessions.value]
    .sort((a, b) => b.updatedAt - a.updatedAt)
    .map((session) => ({
      value: session.id,
      label: formatSessionOptionLabel(session)
    }))
)

const canCreateNewChat = computed(() =>
  !chatSessions.value.some(
    (session) => !session.isPersisted && !session.hasInteraction && session.messages.length === 0
  )
)

const savePromptDialogVisible = ref(false)
const savePromptMode = ref<'new' | 'existing'>('new')
const savePromptSubmitting = ref(false)
const savePromptForm = reactive({
  promptId: null as number | null,
  promptName: '',
  promptVersion: 'v1',
  promptClassId: null as number | null,
  promptDescription: '',
  promptContent: '',
  promptTagIds: [] as number[],
})

const existingPromptOptions = computed(() =>
  Array.from(promptMap.value.values()).map((prompt) => ({
    value: prompt.id,
    label: `${prompt.prompt_class.name} / ${prompt.name}`,
  }))
)

const promptClassOptions = computed(() => {
  const map = new Map<number, string>()
  promptMap.value.forEach((prompt) => {
    map.set(prompt.prompt_class.id, prompt.prompt_class.name)
  })
  return Array.from(map.entries()).map(([value, label]) => ({ value, label }))
})

const promptTagOptions = computed(() =>
  promptTags.value.map((tag) => ({ value: tag.id, label: tag.name }))
)

const chatScrollRef = ref<HTMLDivElement | null>(null)
let activeStreamController: AbortController | null = null
let messageId = 0

const HISTORY_LIMIT = 30

function scheduleStreamScroll() {
  if (streamingScrollScheduled) {
    return
  }
  if (typeof window === 'undefined') {
    void scrollToBottom()
    return
  }
  streamingScrollScheduled = true
  window.requestAnimationFrame(() => {
    streamingScrollScheduled = false
    void scrollToBottom()
  })
}

function enqueueStreamingContent(message: QuickTestMessage, text: string) {
  if (!text) {
    return
  }
  message.content = `${message.content}${text}`
  if (import.meta.env.DEV) {
    // eslint-disable-next-line no-console
    console.debug('[QuickTest][StreamAppend]', performance.now(), text, message.content)
  }
  scheduleStreamScroll()
}

function clearStreamingQueue(
  messageId: number,
  options: { flush?: boolean; target?: QuickTestMessage } = {}
) {
  if (options.flush && options.target) {
    // 兼容旧逻辑：已直接写入 message.content，无额外缓冲
    options.target.content = options.target.content
  }
}

function findMessageById(id: number) {
  return messages.value.find((item) => item.id === id)
}

function resolveBubbleHeaderClass(message: QuickTestMessage) {
  return `chat-message__header chat-message__header--${message.role}`
}

function resolveBubbleContentClass(message: QuickTestMessage) {
  return `chat-message__bubble-content chat-message__bubble-content--${message.role}`
}

function resolveBubbleFooterClass(message: QuickTestMessage) {
  return `chat-message__footer chat-message__footer--${message.role}`
}

function renderMessageMarkdown(content: string) {
  if (!content) {
    return ''
  }
  return markdownRenderer.render(content)
}

function nextMessageId(): number {
  messageId += 1
  return messageId
}

function normalizeMessageContent(content: unknown): string {
  if (typeof content === 'string') {
    return content
  }
  if (content == null) {
    return ''
  }
  try {
    return JSON.stringify(content)
  } catch (error) {
    void error
    return String(content)
  }
}

const selectedModel = computed(() => {
  if (selectedModelPath.value.length !== 2) return null
  const [providerIdRaw, modelNameRaw] = selectedModelPath.value
  const providerId = Number(providerIdRaw)
  if (Number.isNaN(providerId)) return null
  const provider = providerMap.value.get(providerId)
  if (!provider) return null
  const model = provider.models.find((item) => item.name === String(modelNameRaw))
  if (!model) return null
  return { provider, model }
})

watch(extraParams, (value) => {
  if (!value.trim()) {
    extraParamsError.value = t('quickTest.messages.extraInvalid')
    return
  }
  try {
    const parsed = JSON.parse(value)
    if (parsed === null || typeof parsed !== 'object') {
      extraParamsError.value = t('quickTest.messages.extraObjectRequired')
    } else {
      extraParamsError.value = null
    }
  } catch (error) {
    void error
    extraParamsError.value = t('quickTest.messages.extraParseFailed')
  }
}, { immediate: true })

watch(messages, () => {
  void scrollToBottom()
})

watch(selectedPromptPath, (path) => {
  if (path.length !== 3) {
    return
  }
  const [, promptIdRaw, versionIdRaw] = path
  const promptId = Number(promptIdRaw)
  const versionId = Number(versionIdRaw)
  if (Number.isNaN(promptId) || Number.isNaN(versionId)) {
    return
  }
  const prompt = promptMap.value.get(promptId)
  const version = prompt?.versions.find((item) => item.id === versionId)
  if (!version) {
    return
  }
  chatInput.value = version.content
})

watch(savePromptMode, (mode) => {
  if (mode === 'new') {
    savePromptForm.promptId = null
    savePromptForm.promptVersion = 'v1'
    savePromptForm.promptTagIds = []
  } else if (mode === 'existing') {
    const firstPrompt = existingPromptOptions.value[0]
    if (firstPrompt && savePromptForm.promptId === null) {
      savePromptForm.promptId = firstPrompt.value
    }
  }
})

watch(
  () => savePromptForm.promptId,
  (promptId) => {
    if (promptId === null) {
      return
    }
    const prompt = promptMap.value.get(promptId)
    if (!prompt) {
      return
    }
    savePromptForm.promptVersion = suggestNextVersion(prompt)
    savePromptForm.promptClassId = prompt.prompt_class.id
    savePromptForm.promptTagIds = prompt.tags.map((tag) => tag.id)
  }
)

onMounted(() => {
  if (configuredQuickTestTimeout.value == null) {
    void fetchTestingTimeouts()
  }
  void fetchLLMProviders()
  void fetchPromptOptions()
  void fetchPromptTags()
  void refreshHistory().then(() => {
    startNewDraftSession()
  })
})

onBeforeUnmount(() => {
  cancelActiveStream()
})

function cancelActiveStream() {
  if (activeStreamController) {
    activeStreamController.abort()
    activeStreamController = null
  }
  if (activeStreamingMessageId !== null) {
    const target = findMessageById(activeStreamingMessageId)
    if (target) {
      clearStreamingQueue(activeStreamingMessageId, { flush: true, target })
    } else {
      clearStreamingQueue(activeStreamingMessageId)
    }
    activeStreamingMessageId = null
  }
}

async function scrollToBottom() {
  await nextTick()
  const wrapper = chatScrollRef.value
  if (!wrapper) {
    return
  }
  wrapper.scrollTop = wrapper.scrollHeight
}

function handleSessionChange(value: number | null) {
  if (value === null || value === activeSessionId.value) {
    return
  }
  const session = chatSessions.value.find((item) => item.id === value)
  if (!session) {
    return
  }
  cancelActiveStream()
  isSending.value = false
  activeSessionId.value = session.id
  messages.value = session.messages
  chatInput.value = ''
  if (
    session.providerId != null &&
    session.modelName &&
    providerMap.value.has(session.providerId)
  ) {
    selectedModelPath.value = [session.providerId, session.modelName]
  }
  void scrollToBottom()
  syncActiveSessionSelection()
}

function handleNewChat() {
  if (!canCreateNewChat.value) {
    ElMessage.info(t('quickTest.messages.draftNotUsed'))
    return
  }
  cancelActiveStream()
  isSending.value = false
  chatInput.value = ''
  selectedPromptPath.value = []
  startNewDraftSession(true)
}

function getActiveSession(): ChatSession | undefined {
  if (activeSessionId.value === null) {
    return undefined
  }
  return chatSessions.value.find((session) => session.id === activeSessionId.value)
}

function ensureActiveSession(): ChatSession {
  const existing = getActiveSession()
  if (existing) {
    return existing
  }
  return createDraftSession()
}

function createDraftSession(title?: string): ChatSession {
  const now = Date.now()
  const sessionMessages = reactive<QuickTestMessage[]>([]) as QuickTestMessage[]
  sessionSeed -= 1
  const identifier = Math.abs(sessionSeed)
  const session: ChatSession = {
    id: sessionSeed,
    title: title && title.trim() ? title : t('quickTest.session.newTitle', { id: identifier }),
    messages: sessionMessages,
    createdAt: now,
    updatedAt: now,
    autoTitle: !(title && title.trim()),
    isPersisted: false,
    hasInteraction: false,
    providerId: null,
    providerName: null,
    providerLogoEmoji: null,
    providerLogoUrl: null,
    modelId: null,
    modelName: null,
    promptId: null,
    promptVersionId: null
  }
  chatSessions.value.push(session)
  activeSessionId.value = session.id
  messages.value = session.messages
  return session
}

function startNewDraftSession(force = false) {
  if (!force) {
    const hasEmptyDraft = chatSessions.value.some(
      (session) => !session.isPersisted && !session.hasInteraction && session.messages.length === 0
    )
    if (hasEmptyDraft) {
      return
    }
  }

  const session = createDraftSession()
  messages.value = session.messages
  selectedModelPath.value = []
  chatInput.value = ''
  void scrollToBottom()
}

function generateSessionTitle(content: string, fallback: string): string {
  const trimmed = content.trim()
  if (!trimmed) {
    return fallback
  }
  const snippet = trimmed.slice(0, 18)
  return trimmed.length > 18 ? `${snippet}…` : snippet
}

function updateActiveSessionTimestamp() {
  const session = getActiveSession()
  if (session) {
    session.updatedAt = Date.now()
  }
}

function formatSessionOptionLabel(session: ChatSession): string {
  const timestamp = formatSessionTime(session.updatedAt)
  const prefix = session.isPersisted ? '' : t('quickTest.session.draftPrefix')
  return t('quickTest.session.optionLabel', {
    prefix,
    title: session.title,
    timestamp
  })
}

function formatSessionTime(timestamp: number): string {
  const date = new Date(timestamp)
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hour = String(date.getHours()).padStart(2, '0')
  const minute = String(date.getMinutes()).padStart(2, '0')
  return `${month}-${day} ${hour}:${minute}`
}

function syncActiveSessionSelection() {
  const session = getActiveSession()
  if (
    session &&
    session.providerId != null &&
    session.modelName &&
    providerMap.value.has(session.providerId)
  ) {
    selectedModelPath.value = [session.providerId, session.modelName]
  }
}

function getDefaultPromptContent(): string {
  const draft = chatInput.value
  if (draft.trim()) {
    return draft
  }
  const lastUser = [...messages.value]
    .reverse()
    .find((item) => item.role === 'user' && item.content.trim())
  return lastUser ? lastUser.content : ''
}

function resetSavePromptForm(initialContent = '') {
  savePromptForm.promptId = null
  savePromptForm.promptName = ''
  savePromptForm.promptVersion = 'v1'
  savePromptForm.promptClassId = null
  savePromptForm.promptDescription = ''
  savePromptForm.promptContent = initialContent
  savePromptForm.promptTagIds = []
}

function getLatestPromptVersion(prompt: Prompt | undefined): string | null {
  if (!prompt) return null
  if (prompt.versions.length) {
    const sorted = [...prompt.versions].sort(
      (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
    )
    return sorted[sorted.length - 1]?.version ?? null
  }
  return prompt.current_version?.version ?? null
}

function suggestNextVersion(prompt: Prompt | undefined): string {
  const latest = getLatestPromptVersion(prompt)
  if (!latest) {
    return 'v1'
  }
  const match = latest.match(/^v(\d+)$/i)
  if (match) {
    const next = Number(match[1]) + 1
    return `v${next}`
  }
  const suffix = new Date().toISOString().slice(0, 10).replace(/-/g, '')
  return `${latest}-${suffix}`
}

function deriveHistoryTitle(log: QuickTestHistoryItem): string {
  if (Array.isArray(log.messages)) {
    const firstUser = log.messages.find((item) => item.role === 'user')
    if (firstUser) {
      const snippet = normalizeMessageContent(firstUser.content).trim()
      if (snippet) {
        return snippet.length > 18 ? `${snippet.slice(0, 18)}…` : snippet
      }
    }
  }
  if (log.provider_name) {
    return `${log.provider_name}-${log.model_name}`
  }
  return t('quickTest.session.historyTitle', { id: log.id })
}

function convertHistoryLogToSession(log: QuickTestHistoryItem): ChatSession {
  const sessionMessages = reactive<QuickTestMessage[]>([]) as QuickTestMessage[]
  const providerName = log.provider_name
  const providerEmoji = log.provider_logo_emoji
  const providerLogoUrl = log.provider_logo_url

  const historyMessages = Array.isArray(log.messages) ? log.messages : []
  const assistantLabel = t('quickTest.chat.avatar.assistant')
  const systemLabel = t('quickTest.chat.avatar.system')
  const selfLabel = t('quickTest.chat.avatar.self')

  for (const entry of historyMessages) {
    const role = typeof entry.role === 'string' ? entry.role : 'user'
    const normalizedRole = role === 'assistant' || role === 'system' ? 'assistant' : 'user'
    const displayName =
      role === 'assistant'
        ? providerName ?? assistantLabel
        : role === 'system'
          ? systemLabel
          : selfLabel
    sessionMessages.push({
      id: nextMessageId(),
      role: normalizedRole,
      content: normalizeMessageContent(entry.content),
      displayName,
      avatarUrl: normalizedRole === 'assistant' ? providerLogoUrl ?? undefined : userAvatar,
      avatarEmoji: normalizedRole === 'assistant' ? providerEmoji ?? undefined : undefined,
      avatarFallback:
        normalizedRole === 'assistant'
          ? (providerName ?? assistantLabel).slice(0, 1).toUpperCase()
          : undefined,
      avatarAlt: normalizedRole === 'assistant' ? providerName ?? assistantLabel : selfLabel,
      isStreaming: false,
      tokens: undefined,
    })
  }

  if (log.response_text) {
    const assistantMessage: QuickTestMessage = {
      id: nextMessageId(),
      role: 'assistant',
      content: normalizeMessageContent(log.response_text),
      displayName: providerName ?? assistantLabel,
      avatarUrl: providerLogoUrl ?? undefined,
      avatarEmoji: providerEmoji ?? undefined,
      avatarFallback: (providerName ?? assistantLabel).slice(0, 1).toUpperCase(),
      avatarAlt: providerName ?? assistantLabel,
      isStreaming: false,
      tokens: undefined,
    }
    applyUsageToMessage(assistantMessage, {
      prompt_tokens: log.prompt_tokens ?? undefined,
      completion_tokens: log.completion_tokens ?? undefined,
      total_tokens: log.total_tokens ?? undefined,
    })
    sessionMessages.push(assistantMessage)
  }

  const createdAt = Date.parse(log.created_at)
  const timestamp = Number.isNaN(createdAt) ? Date.now() : createdAt

  return {
    id: log.id,
    title: deriveHistoryTitle(log),
    messages: sessionMessages,
    createdAt: timestamp,
    updatedAt: timestamp,
    autoTitle: false,
    isPersisted: true,
    hasInteraction: true,
    providerId: log.provider_id,
    providerName,
    providerLogoEmoji: providerEmoji,
    providerLogoUrl,
    modelId: log.model_id,
    modelName: log.model_name,
    promptId: log.prompt_id,
    promptVersionId: log.prompt_version_id,
  }
}

async function refreshHistory(match?: HistoryMatchCriteria): Promise<void> {
  try {
    const logs = await fetchQuickTestHistory({ limit: HISTORY_LIMIT })
    const persistedSessions = logs.map(convertHistoryLogToSession)
    const drafts = chatSessions.value.filter((session) => !session.isPersisted)

    let remainingDrafts = drafts
    let matchedId: number | null = null

    if (match) {
      const matchedLog = logs.find((log) => {
        const providerOk =
          match.providerId === undefined || log.provider_id === match.providerId
        const modelOk =
          match.modelName === undefined || log.model_name === match.modelName
        const responseOk =
          match.responseText === undefined || log.response_text === match.responseText
        const requestOk =
          match.requestSignature === undefined
            ? true
            : JSON.stringify(log.messages ?? []) === match.requestSignature
        return providerOk && modelOk && responseOk && requestOk
      })
      if (matchedLog) {
        matchedId = matchedLog.id
        if (match.draftId !== undefined) {
          remainingDrafts = drafts.filter((session) => session.id !== match.draftId)
        }
      }
    }

    chatSessions.value = [...persistedSessions, ...remainingDrafts]

    if (matchedId !== null) {
      const matchedSession = chatSessions.value.find((session) => session.id === matchedId)
      if (matchedSession) {
        activeSessionId.value = matchedSession.id
        messages.value = matchedSession.messages
        if (
          matchedSession.providerId != null &&
          matchedSession.modelName &&
          providerMap.value.has(matchedSession.providerId)
        ) {
          selectedModelPath.value = [matchedSession.providerId, matchedSession.modelName]
        }
        chatInput.value = ''
        void scrollToBottom()
        syncActiveSessionSelection()
      }
      return
    }

    if (activeSessionId.value !== null) {
      const active = chatSessions.value.find((session) => session.id === activeSessionId.value)
      if (active) {
        messages.value = active.messages
        syncActiveSessionSelection()
        return
      }
    }

    if (chatSessions.value.length > 0) {
      const session = chatSessions.value[0]
      activeSessionId.value = session.id
      messages.value = session.messages
      if (
        session.providerId != null &&
        session.modelName &&
        providerMap.value.has(session.providerId)
      ) {
        selectedModelPath.value = [session.providerId, session.modelName]
      }
      chatInput.value = ''
      void scrollToBottom()
    }
    syncActiveSessionSelection()
  } catch (error) {
    void error
    ElMessage.warning(t('quickTest.messages.historyLoadFailed'))
  }
}
function handleEnterKey(event: KeyboardEvent) {
  if (event.shiftKey || event.isComposing || isComposing.value) {
    return
  }
  const keyCode = (event as KeyboardEvent & { keyCode?: number }).keyCode
  if (keyCode === 229) {
    return
  }
  event.preventDefault()
  if (isSending.value) {
    return
  }
  void handleSend()
}

function handleCompositionStart() {
  isComposing.value = true
}

function handleCompositionEnd() {
  setTimeout(() => {
    isComposing.value = false
  }, 0)
}

async function fetchLLMProviders() {
  isModelLoading.value = true
  try {
    const providers = await listLLMProviders()
    providerMap.value = new Map(providers.map((item) => [item.id, item]))
    modelOptions.value = providers.map((provider) => ({
      value: provider.id,
      label: provider.provider_name,
      children: provider.models.map((model) => ({
        value: model.name,
        label: model.name
      }))
    }))
    syncActiveSessionSelection()
  } catch (error) {
    ElMessage.error(t('quickTest.messages.modelsLoadFailed'))
  } finally {
    isModelLoading.value = false
  }
}

async function fetchPromptOptions() {
  isPromptLoading.value = true
  try {
    const prompts = await listPrompts({ limit: PROMPT_FETCH_LIMIT })
    promptMap.value = new Map(prompts.map((prompt) => [prompt.id, prompt]))
    const grouped = new Map<number, { label: string; prompts: Prompt[] }>()
    prompts.forEach((prompt) => {
      const classId = prompt.prompt_class.id
      if (!grouped.has(classId)) {
        grouped.set(classId, { label: prompt.prompt_class.name, prompts: [] })
      }
      grouped.get(classId)?.prompts.push(prompt)
    })
    promptOptions.value = Array.from(grouped.entries()).map(([classId, meta]) => ({
      value: classId,
      label: meta.label,
      children: meta.prompts.map((prompt) => ({
        value: prompt.id,
        label: prompt.name,
        children: prompt.versions.map((version) => ({
          value: version.id,
          label: version.version
        }))
      }))
    }))
  } catch (error) {
    ElMessage.error(t('quickTest.messages.promptsLoadFailed'))
  } finally {
    isPromptLoading.value = false
  }
}

async function fetchPromptTags() {
  try {
    const response = await listPromptTags()
    promptTags.value = response.items
  } catch (error) {
    ElMessage.warning(t('quickTest.messages.tagsLoadFailed'))
  }
}

function resolveSelectedPromptMeta() {
  if (selectedPromptPath.value.length !== 3) {
    return null
  }
  const [, promptIdRaw, versionIdRaw] = selectedPromptPath.value
  const promptId = Number(promptIdRaw)
  const versionId = Number(versionIdRaw)
  if (Number.isNaN(promptId) || Number.isNaN(versionId)) {
    return null
  }
  return { promptId, versionId }
}

function buildChatPayloadMessages(): ChatMessagePayload[] {
  return messages.value
    .filter((message) => !(message.role === 'assistant' && message.isStreaming))
    .map((message) => ({ role: message.role, content: message.content }))
}

function parseExtraParameters(): Record<string, unknown> {
  if (!extraParams.value.trim()) {
    return {}
  }
  try {
    const parsed = JSON.parse(extraParams.value)
    return parsed && typeof parsed === 'object' ? parsed : {}
  } catch (error) {
    void error
    return {}
  }
}

function applyUsageToMessage(
  message: QuickTestMessage,
  usage: { prompt_tokens?: number; completion_tokens?: number; total_tokens?: number }
) {
  if (!usage) return
  const input = usage.prompt_tokens ?? null
  const output = usage.completion_tokens ?? null
  const total = usage.total_tokens ?? (
    input !== null || output !== null
      ? (input ?? 0) + (output ?? 0)
      : null
  )
  message.tokens = { input, output, total }
}

function formatTokenValue(value: number | null | undefined) {
  if (value === null || value === undefined) {
    return '—'
  }
  return value
}

async function handleSend() {
  const model = selectedModel.value
  if (!model) {
    ElMessage.warning(t('quickTest.messages.modelRequired'))
    return
  }
  if (extraParamsError.value) {
    ElMessage.warning(t('quickTest.messages.extraFixRequired'))
    return
  }
  const content = chatInput.value.trim()
  if (!content) {
    ElMessage.info(t('quickTest.messages.inputRequired'))
    return
  }
  cancelActiveStream()
  const session = ensureActiveSession()
  const provider = model.provider
  const targetModel = model.model

  session.providerId = provider.id
  session.providerName = provider.provider_name
  session.providerLogoEmoji = provider.logo_emoji
  session.providerLogoUrl = provider.logo_url
  session.modelId = targetModel.id
  session.modelName = targetModel.name

  isSending.value = true
  chatInput.value = ''
  appendUserMessage(content)
  const assistantMessage = appendAssistantPlaceholder(provider)

  const messagesPayload = buildChatPayloadMessages()
  session.hasInteraction = true
  const extraParameters = parseExtraParameters()
  const promptMeta = resolveSelectedPromptMeta()
  session.promptId = promptMeta?.promptId ?? null
  session.promptVersionId = promptMeta?.versionId ?? null

  const controller = new AbortController()
  activeStreamController = controller

  const payload = {
    providerId: provider.id,
    modelId: targetModel.id,
    modelName: targetModel.name,
    messages: messagesPayload,
    temperature: temperature.value,
    parameters: extraParameters,
    promptId: promptMeta?.promptId ?? null,
    promptVersionId: promptMeta?.versionId ?? null,
    persistUsage: isStreamingEnabled.value ? undefined : true
  }

  const timeoutSeconds =
    configuredQuickTestTimeout.value ?? DEFAULT_QUICK_TEST_TIMEOUT_SECONDS
  let abortedByTimeout = false
  let abortTimer: ReturnType<typeof window.setTimeout> | null = null
  if (timeoutSeconds > 0 && Number.isFinite(timeoutSeconds)) {
    abortTimer = window.setTimeout(() => {
      abortedByTimeout = true
      controller.abort()
    }, timeoutSeconds * 1000)
  }

  let finalResponseText = ''
  let shouldScrollAfterStream = false
  let shouldRefreshHistory = false
  const matchCriteria: HistoryMatchCriteria = {
    requestSignature: JSON.stringify(messagesPayload),
    providerId: provider.id,
    modelName: targetModel.name,
    draftId: session.isPersisted ? undefined : session.id
  }
  try {
    if (isStreamingEnabled.value) {
      for await (const event of streamQuickTest(payload, { signal: controller.signal })) {
        const data = event.data
        if (data === '[DONE]') {
          break
        }
        let parsed: any
        try {
          parsed = JSON.parse(data)
        } catch (error) {
          void error
          continue
        }

        if (parsed?.usage) {
          applyUsageToMessage(assistantMessage, parsed.usage)
          updateActiveSessionTimestamp()
        }

        const choices = Array.isArray(parsed?.choices) ? parsed.choices : []
        for (const choice of choices) {
          const delta = choice?.delta
          if (delta && typeof delta.content === 'string') {
            finalResponseText += delta.content
            enqueueStreamingContent(assistantMessage, delta.content)
            shouldScrollAfterStream = true
            updateActiveSessionTimestamp()
            continue
          }
          const message = choice?.message
          if (message && typeof message.content === 'string') {
            finalResponseText += message.content
            enqueueStreamingContent(assistantMessage, message.content)
            shouldScrollAfterStream = true
            updateActiveSessionTimestamp()
            continue
          }
          const text = choice?.text
          if (typeof text === 'string') {
            finalResponseText += text
            enqueueStreamingContent(assistantMessage, text)
            shouldScrollAfterStream = true
            updateActiveSessionTimestamp()
          }
        }
      }
      shouldRefreshHistory = true
    } else {
      const response = await invokeQuickTest(payload, { signal: controller.signal })
      if (response?.usage) {
        applyUsageToMessage(assistantMessage, response.usage)
      }
      clearStreamingQueue(assistantMessage.id)
      const choices = Array.isArray(response?.choices) ? response.choices : []
      let combined = ''
      for (const choice of choices) {
        if (!choice || typeof choice !== 'object') {
          continue
        }
        const message = choice?.message
        if (message && typeof message.content === 'string') {
          combined += message.content
          continue
        }
        const text = choice?.text
        if (typeof text === 'string') {
          combined += text
        }
      }
      assistantMessage.content = combined || assistantMessage.content
      finalResponseText = combined || assistantMessage.content
      shouldScrollAfterStream = true
      shouldRefreshHistory = true
      updateActiveSessionTimestamp()
    }
  } catch (error: any) {
    if (error?.name === 'AbortError') {
      const message = abortedByTimeout
        ? t('quickTest.messages.requestTimeout', { seconds: timeoutSeconds })
        : t('quickTest.messages.requestCancelled')
      if (!assistantMessage.content) {
        assistantMessage.content = message
      }
      clearStreamingQueue(assistantMessage.id, { flush: true, target: assistantMessage })
      assistantMessage.tokens = undefined
      shouldScrollAfterStream = true
      updateActiveSessionTimestamp()
      if (abortedByTimeout) {
        ElMessage.warning(message)
      }
      return
    }
    let message = t('quickTest.messages.invokeFailed')
    const detail = error?.payload ?? error?.detail
    if (typeof detail === 'string') {
      message = detail
    } else if (detail && typeof detail === 'object') {
      message = detail.message ?? detail.detail ?? message
    } else if (error?.message) {
      message = error.message
    }
    clearStreamingQueue(assistantMessage.id)
    assistantMessage.content = message
    assistantMessage.tokens = undefined
    ElMessage.error(message)
    shouldScrollAfterStream = true
    updateActiveSessionTimestamp()
  } finally {
    if (abortTimer !== null) {
      clearTimeout(abortTimer)
    }
    assistantMessage.isStreaming = false
    isSending.value = false
    if (activeStreamController === controller) {
      activeStreamController = null
    }
    if (activeStreamingMessageId === assistantMessage.id) {
      activeStreamingMessageId = null
    }
    if (assistantMessage.content) {
      shouldScrollAfterStream = true
    }
    session.updatedAt = Date.now()
    if (shouldScrollAfterStream) {
      void scrollToBottom()
    }
    if (shouldRefreshHistory) {
      matchCriteria.responseText = finalResponseText || assistantMessage.content
      await refreshHistory(matchCriteria)
    }
  }
}

function handleSaveAsPrompt() {
  const content = getDefaultPromptContent()
  if (!content.trim()) {
    ElMessage.info(t('quickTest.messages.saveNoContent'))
    return
  }
  resetSavePromptForm(content)
  savePromptMode.value = 'new'
  savePromptDialogVisible.value = true
}

function handleSavePromptCancel() {
  savePromptDialogVisible.value = false
  resetSavePromptForm(chatInput.value)
}

async function handleSavePromptConfirm() {
  if (savePromptSubmitting.value) {
    return
  }
  const content = savePromptForm.promptContent.trim()
  if (!content) {
    ElMessage.warning(t('quickTest.messages.contentRequired'))
    return
  }

  savePromptSubmitting.value = true
  try {
    if (savePromptMode.value === 'new') {
      const name = savePromptForm.promptName.trim()
      if (!name) {
        ElMessage.warning(t('quickTest.messages.nameRequired'))
        savePromptSubmitting.value = false
        return
      }
      const version = savePromptForm.promptVersion.trim() || 'v1'
      const payload: PromptCreatePayload = {
        name,
        version,
        content: savePromptForm.promptContent,
      }
      if (savePromptForm.promptDescription.trim()) {
        payload.description = savePromptForm.promptDescription.trim()
      }
      if (savePromptForm.promptClassId) {
        payload.class_id = savePromptForm.promptClassId
      }
      if (savePromptForm.promptTagIds.length) {
        payload.tag_ids = [...savePromptForm.promptTagIds]
      }
      await createPrompt(payload)
      ElMessage.success(t('quickTest.messages.createPromptSuccess'))
    } else {
      const promptId = savePromptForm.promptId
      if (!promptId) {
        ElMessage.warning(t('quickTest.messages.selectPromptToUpdate'))
        savePromptSubmitting.value = false
        return
      }
      const version = savePromptForm.promptVersion.trim()
      if (!version) {
        ElMessage.warning(t('quickTest.messages.versionRequired'))
        savePromptSubmitting.value = false
        return
      }
      await createPromptVersion(promptId, version, savePromptForm.promptContent)
      ElMessage.success(t('quickTest.messages.createPromptVersionSuccess'))
    }

    savePromptDialogVisible.value = false
    resetSavePromptForm('')
    await fetchPromptOptions()
  } catch (error: any) {
    const message = error?.message ?? t('quickTest.messages.savePromptFailed')
    ElMessage.error(message)
  } finally {
    savePromptSubmitting.value = false
  }
}

function appendUserMessage(content: string) {
  messages.value.push({
    id: nextMessageId(),
    role: 'user',
    content,
    displayName: t('quickTest.chat.avatar.self')
  })
  const session = getActiveSession()
  if (session) {
    session.hasInteraction = true
    if (session.autoTitle) {
      session.title = generateSessionTitle(content, session.title)
      if (content.trim()) {
        session.autoTitle = false
      }
    }
    session.updatedAt = Date.now()
  }
  void scrollToBottom()
}

function appendAssistantPlaceholder(provider: LLMProvider) {
  const lastStreaming = [...messages.value].reverse().find((item) => item.role === 'assistant' && item.isStreaming)
  if (lastStreaming) {
    lastStreaming.isStreaming = false
    clearStreamingQueue(lastStreaming.id, { flush: true, target: lastStreaming })
  }
  const message = reactive<QuickTestMessage>({
    id: nextMessageId(),
    role: 'assistant',
    content: '',
    displayName: provider.provider_name,
    avatarUrl: provider.logo_url,
    avatarEmoji: provider.logo_emoji,
    avatarFallback: provider.provider_name.slice(0, 1).toUpperCase(),
    avatarAlt: provider.provider_name,
    isStreaming: true,
    tokens: undefined
  }) as QuickTestMessage
  messages.value.push(message)
  activeStreamingMessageId = message.id
  const session = getActiveSession()
  if (session) {
    session.providerId = provider.id
    session.providerName = provider.provider_name
    session.providerLogoEmoji = provider.logo_emoji
    session.providerLogoUrl = provider.logo_url
    session.updatedAt = Date.now()
  }
  void scrollToBottom()
  return message
}
</script>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: calc(100vh - 64px - 48px);
  min-height: 520px;
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

.page-header__actions {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 12px;
}

.history-select {
  width: 220px;
}

.save-prompt-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.save-prompt-select {
  width: 100%;
}

.save-prompt-class {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.save-prompt-class :deep(.el-select) {
  flex: 1 1 220px;
}

.save-prompt-class :deep(.el-input) {
  flex: 1 1 220px;
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

.test-layout {
  display: flex;
  gap: 16px;
  align-items: stretch;
  flex: 1;
  min-height: 0;
}

.model-card {
  flex: 0 0 25%;
  max-width: 25%;
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.model-card :deep(.el-card__body) {
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow: auto;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  font-size: 14px;
  font-weight: 600;
}

.card-header__actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.card-header__toggle {
  display: flex;
  align-items: center;
  gap: 8px;
}

.card-header__toggle-label {
  color: var(--text-weak-color);
  font-size: 12px;
}

.chat-toggle-switch {
  flex-shrink: 0;
  min-width: 66px;
}


.model-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.temperature-box {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.chat-card {
  flex: 0 0 75%;
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.chat-card :deep(.el-card__body) {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}

.chat-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  gap: 16px;
  flex: 1;
  min-height: 0;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding-right: 4px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 0;
}

.chat-message {
  display: flex;
}

.chat-message--assistant {
  justify-content: flex-start;
}

.chat-message--user {
  justify-content: flex-end;
}

.chat-message__bubble {
  max-width: 80%;
}

.chat-message__avatar {
  flex-shrink: 0;
}

.chat-message__header {
  margin: 0 0 4px;
  display: flex;
  font-size: 12px;
  color: var(--text-weak-color);
}

.chat-message__header--assistant {
  justify-content: flex-start;
}

.chat-message__header--user {
  justify-content: flex-end;
}

.chat-message__name {
  margin: 0;
}

.chat-message__bubble-content {
  word-break: break-word;
  font-size: 14px;
  line-height: 1.6;
  padding: 12px 14px;
}

.chat-message__bubble-content--assistant {
  background: var(--content-bg-color);
  border: 1px solid var(--side-border-color);
}

.chat-message__bubble-content--user {
  background: rgba(64, 158, 255, 0.12);
}

.chat-message__content--text {
  display: block;
  white-space: pre-wrap;
}

.chat-message__content--markdown {
  width: 100%;
}

.chat-message__content--markdown :deep(p) {
  margin: 0 0 8px;
}

.chat-message__content--markdown :deep(p:last-child) {
  margin-bottom: 0;
}

.chat-message__content--markdown :deep(code) {
  background-color: rgba(0, 0, 0, 0.05);
  padding: 2px 4px;
  border-radius: 4px;
  font-size: 90%;
}

.chat-message__content--markdown :deep(pre code) {
  display: block;
  padding: 12px;
  overflow-x: auto;
}

.chat-message__content--markdown :deep(ul),
.chat-message__content--markdown :deep(ol) {
  padding-left: 20px;
  margin: 0 0 8px;
}

.chat-message__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 16px;
  font-size: 12px;
  color: var(--text-weak-color);
  margin-top: 4px;
}

.chat-message__footer {
  display: flex;
  margin-top: 8px;
}

.chat-message__footer--assistant {
  justify-content: flex-start;
}

.chat-message__footer--user {
  justify-content: flex-end;
}

.chat-input {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: auto;
}

.chat-input__footer {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
}

.prompt-selector {
  flex: 1;
}

.chat-input__actions {
  display: flex;
  gap: 12px;
}

@media (max-width: 1200px) {
  .test-layout {
    flex-direction: column;
  }

  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .page-header__actions {
    margin-left: 0;
    width: 100%;
    flex-wrap: wrap;
    gap: 8px;
  }

  .history-select {
    flex: 1 1 auto;
    width: 100%;
  }

  .save-prompt-class {
    flex-direction: column;
  }

  .model-card,
  .chat-card {
    flex: 1 1 auto;
    max-width: 100%;
    height: auto;
  }

  .chat-message__bubble {
    max-width: 100%;
  }
}
</style>
