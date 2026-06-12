<template>
  <el-config-provider :locale="elementLocale">
    <div class="app-shell">
      <el-container class="app-container">
        <el-aside width="220px" class="side-nav">
          <div class="brand-row">
            <img src="/logo.png" alt="PromptWorks" class="brand-logo" />
            <span class="app-title">PromptWorks</span>
          </div>
          <div class="side-divider" />
          <el-menu class="side-menu" :default-active="activeMenu" @select="handleMenuSelect">
            <el-menu-item v-for="item in menuItems" :key="item.index" :index="item.index">
              <el-icon>
                <component :is="item.icon" />
              </el-icon>
              <span>{{ item.label }}</span>
            </el-menu-item>
          </el-menu>
        </el-aside>
        <el-main class="main-view">
          <div class="main-toolbar-space" aria-hidden="true" />
          <router-view />
        </el-main>
      </el-container>

      <div class="global-action-card" aria-label="全局操作">
        <el-dropdown trigger="click" @command="handleLanguageCommand">
          <el-tooltip :content="t('app.language')" placement="bottom">
            <el-button
              :icon="Reading"
              circle
              text
              class="global-action-button"
              :title="t('app.language')"
              :aria-label="t('app.language')"
            />
          </el-tooltip>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="zh-CN" :disabled="language === 'zh-CN'">
                {{ t('app.languageCn') }}
              </el-dropdown-item>
              <el-dropdown-item command="en-US" :disabled="language === 'en-US'">
                {{ t('app.languageEn') }}
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>

        <el-dropdown trigger="click" @command="handleThemeCommand">
          <el-tooltip :content="themeTooltip" placement="bottom">
            <el-button
              :icon="themeIcon"
              circle
              text
              class="global-action-button"
              :title="themeTooltip"
              :aria-label="themeTooltip"
            />
          </el-tooltip>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="system" :disabled="themeMode === 'system'">
                <el-icon><Monitor /></el-icon>
                <span>{{ t('app.themeSystem') }}</span>
              </el-dropdown-item>
              <el-dropdown-item command="light" :disabled="themeMode === 'light'">
                <el-icon><Sunny /></el-icon>
                <span>{{ t('app.themeLight') }}</span>
              </el-dropdown-item>
              <el-dropdown-item command="dark" :disabled="themeMode === 'dark'">
                <el-icon><Moon /></el-icon>
                <span>{{ t('app.themeDark') }}</span>
              </el-dropdown-item>
              <li class="theme-color-panel" role="presentation">
                <div class="theme-color-panel__title">{{ t('app.themeColor') }}</div>
                <div class="theme-color-options" role="group" :aria-label="t('app.themeColor')">
                  <button
                    v-for="item in themeColorOptions"
                    :key="item.value"
                    type="button"
                    class="theme-color-option"
                    :class="{ 'is-active': themeColor === item.value }"
                    :style="{ '--theme-option-color': item.primary }"
                    :aria-label="t(item.labelKey)"
                    :aria-pressed="themeColor === item.value"
                    :title="t(item.labelKey)"
                    @click.stop="handleThemeColorSelect(item.value)"
                  />
                </div>
              </li>
            </el-dropdown-menu>
          </template>
        </el-dropdown>

        <el-tooltip :content="t('app.settings')" placement="bottom">
          <el-button
            :icon="Setting"
            circle
            text
            class="global-action-button"
            :title="t('app.settings')"
            :aria-label="t('app.settings')"
            @click="handleOpenSettings"
          />
        </el-tooltip>
      </div>
    </div>

    <el-dialog
      v-model="settingsDialogVisible"
      :title="t('app.settingsDialogTitle')"
      width="460px"
      :close-on-click-modal="false"
      :destroy-on-close="true"
    >
      <el-skeleton v-if="settingsLoading" :rows="3" animated />
      <el-form
        v-else
        ref="settingsFormRef"
        :model="settingsForm"
        :rules="settingsRules"
        label-position="top"
        class="settings-form"
      >
        <el-form-item :label="t('app.settingsQuickTestTimeoutLabel')" prop="quickTestTimeout">
          <div class="settings-input-row">
            <el-input-number
              v-model="settingsForm.quickTestTimeout"
              :min="TIMEOUT_MIN"
              :max="TIMEOUT_MAX"
              :step="5"
              :precision="0"
              :disabled="settingsSaving"
              controls-position="right"
            />
            <span class="settings-input-unit">{{ t('app.settingsSecondsUnit') }}</span>
          </div>
        </el-form-item>
        <el-form-item :label="t('app.settingsTestTaskTimeoutLabel')" prop="testTaskTimeout">
          <div class="settings-input-row">
            <el-input-number
              v-model="settingsForm.testTaskTimeout"
              :min="TIMEOUT_MIN"
              :max="TIMEOUT_MAX"
              :step="5"
              :precision="0"
              :disabled="settingsSaving"
              controls-position="right"
            />
            <span class="settings-input-unit">{{ t('app.settingsSecondsUnit') }}</span>
          </div>
        </el-form-item>
        <el-form-item
          :label="t('app.settingsAiOptimizationTimeoutLabel')"
          prop="aiOptimizationTimeout"
        >
          <div class="settings-input-row">
            <el-input-number
              v-model="settingsForm.aiOptimizationTimeout"
              :min="TIMEOUT_MIN"
              :max="TIMEOUT_MAX"
              :step="30"
              :precision="0"
              :disabled="settingsSaving"
              controls-position="right"
            />
            <span class="settings-input-unit">{{ t('app.settingsSecondsUnit') }}</span>
          </div>
        </el-form-item>
        <p class="settings-hint">
          {{ t('app.settingsTimeoutHint', { min: TIMEOUT_MIN, max: TIMEOUT_MAX }) }}
        </p>
      </el-form>
      <template #footer>
        <el-button @click="handleSettingsCancel" :disabled="settingsSaving">
          {{ t('common.cancel') }}
        </el-button>
        <el-button type="primary" :loading="settingsSaving" @click="handleSettingsConfirm">
          {{ t('common.save') }}
        </el-button>
      </template>
    </el-dialog>
  </el-config-provider>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import type { Component } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Setting,
  Collection,
  MagicStick,
  Memo,
  Files,
  Tickets,
  Cpu,
  Histogram,
  InfoFilled,
  Sunny,
  Moon,
  Monitor,
  Reading
} from '@element-plus/icons-vue'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import enUs from 'element-plus/es/locale/lang/en'
import { useI18n } from 'vue-i18n'
import { setLocale } from './i18n'
import type { SupportedLocale } from './i18n/messages'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { version as APP_VERSION } from '@/version.json'
import {
  useTestingSettings,
  DEFAULT_AI_OPTIMIZATION_TIMEOUT_SECONDS,
  DEFAULT_TIMEOUT_SECONDS
} from './composables/useTestingSettings'
import {
  checkProjectVersionOncePerDay,
  writeProjectVersionCheckCache
} from './utils/projectVersionCheck'

interface MenuItem {
  index: string
  label: string
  routeName: string
  icon: Component
}

const router = useRouter()
const route = useRoute()

const { t, locale } = useI18n()
const language = ref<SupportedLocale>(locale.value as SupportedLocale)
const elementLocale = computed(() => (language.value === 'zh-CN' ? zhCn : enUs))
type ThemeMode = 'system' | 'light' | 'dark'
type ThemeColor = 'blue' | 'green' | 'violet' | 'orange' | 'rose'
interface ThemeColorOption {
  value: ThemeColor
  labelKey: string
  primary: string
  dark2: string
  light3: string
  light5: string
  light7: string
  light8: string
  light9: string
}

const THEME_MODE_STORAGE_KEY = 'promptworks-theme-mode'
const THEME_COLOR_STORAGE_KEY = 'promptworks-theme-color'
const themeColorOptions: ThemeColorOption[] = [
  {
    value: 'blue',
    labelKey: 'app.themeColorBlue',
    primary: '#409eff',
    dark2: '#337ecc',
    light3: '#79bbff',
    light5: '#a0cfff',
    light7: '#c6e2ff',
    light8: '#d9ecff',
    light9: '#ecf5ff'
  },
  {
    value: 'green',
    labelKey: 'app.themeColorGreen',
    primary: '#10b981',
    dark2: '#0f8f69',
    light3: '#5ed0aa',
    light5: '#88dcc2',
    light7: '#b7ead8',
    light8: '#d1f3e8',
    light9: '#ecfdf5'
  },
  {
    value: 'violet',
    labelKey: 'app.themeColorViolet',
    primary: '#7c3aed',
    dark2: '#6429c7',
    light3: '#a377f3',
    light5: '#bd9bf6',
    light7: '#d7c4fa',
    light8: '#e8ddfd',
    light9: '#f3efff'
  },
  {
    value: 'orange',
    labelKey: 'app.themeColorOrange',
    primary: '#f97316',
    dark2: '#c75b12',
    light3: '#fb9d5c',
    light5: '#fdbc8a',
    light7: '#fed8b8',
    light8: '#fee8d5',
    light9: '#fff4eb'
  },
  {
    value: 'rose',
    labelKey: 'app.themeColorRose',
    primary: '#e11d48',
    dark2: '#b91c3f',
    light3: '#ea6380',
    light5: '#f099a9',
    light7: '#f5c2cc',
    light8: '#fadce3',
    light9: '#fff1f4'
  }
]

function readStoredThemeMode(): ThemeMode {
  if (typeof window === 'undefined') {
    return 'system'
  }
  const stored = window.localStorage.getItem(THEME_MODE_STORAGE_KEY)
  return stored === 'light' || stored === 'dark' || stored === 'system'
    ? stored
    : 'system'
}

function readStoredThemeColor(): ThemeColor {
  if (typeof window === 'undefined') {
    return 'blue'
  }
  const stored = window.localStorage.getItem(THEME_COLOR_STORAGE_KEY)
  return themeColorOptions.some((item) => item.value === stored)
    ? (stored as ThemeColor)
    : 'blue'
}

const themeMode = ref<ThemeMode>(readStoredThemeMode())
const themeColor = ref<ThemeColor>(readStoredThemeColor())
const systemPrefersDark = ref(
  typeof window !== 'undefined'
    ? window.matchMedia('(prefers-color-scheme: dark)').matches
    : false
)
let colorSchemeQuery: MediaQueryList | null = null
function handleSystemThemeChange(event: MediaQueryListEvent) {
  systemPrefersDark.value = event.matches
}

const {
  quickTestTimeout,
  testTaskTimeout,
  aiOptimizationTimeout,
  fetchTimeouts,
  saveTimeouts
} = useTestingSettings()

const settingsDialogVisible = ref(false)
const settingsLoading = ref(false)
const settingsSaving = ref(false)
const settingsFormRef = ref<FormInstance>()
const settingsForm = reactive({
  quickTestTimeout: DEFAULT_TIMEOUT_SECONDS,
  testTaskTimeout: DEFAULT_TIMEOUT_SECONDS,
  aiOptimizationTimeout: DEFAULT_AI_OPTIMIZATION_TIMEOUT_SECONDS
})

const TIMEOUT_MIN = 1
const TIMEOUT_MAX = 600
function validateTimeout(
  _: unknown,
  value: number,
  callback: (error?: Error) => void
) {
  if (value == null || Number.isNaN(value)) {
    callback(new Error(t('app.settingsTimeoutRequired')))
    return
  }
  if (value < TIMEOUT_MIN || value > TIMEOUT_MAX) {
    callback(
      new Error(
        t('app.settingsTimeoutRange', { min: TIMEOUT_MIN, max: TIMEOUT_MAX })
      )
    )
    return
  }
  callback()
}

const settingsRules: FormRules = {
  quickTestTimeout: [
    {
      required: true,
      message: t('app.settingsTimeoutRequired'),
      trigger: 'blur'
    },
    {
      validator: validateTimeout,
      trigger: ['change', 'blur']
    }
  ],
  testTaskTimeout: [
    {
      required: true,
      message: t('app.settingsTimeoutRequired'),
      trigger: 'blur'
    },
    {
      validator: validateTimeout,
      trigger: ['change', 'blur']
    }
  ],
  aiOptimizationTimeout: [
    {
      required: true,
      message: t('app.settingsTimeoutRequired'),
      trigger: 'blur'
    },
    {
      validator: validateTimeout,
      trigger: ['change', 'blur']
    }
  ]
}

function syncSettingsFormFromRefs() {
  settingsForm.quickTestTimeout =
    quickTestTimeout.value ?? DEFAULT_TIMEOUT_SECONDS
  settingsForm.testTaskTimeout =
    testTaskTimeout.value ?? DEFAULT_TIMEOUT_SECONDS
  settingsForm.aiOptimizationTimeout =
    aiOptimizationTimeout.value ?? DEFAULT_AI_OPTIMIZATION_TIMEOUT_SECONDS
}

const menuItems = computed<MenuItem[]>(() => [
  { index: 'prompt', label: t('menu.prompt'), routeName: 'prompt-management', icon: Collection },
  { index: 'quick-test', label: t('menu.quickTest'), routeName: 'quick-test', icon: MagicStick },
  { index: 'test-job', label: t('menu.testJob'), routeName: 'test-job-management', icon: Memo },
  { index: 'class', label: t('menu.class'), routeName: 'class-management', icon: Files },
  { index: 'tag', label: t('menu.tag'), routeName: 'tag-management', icon: Tickets },
  { index: 'llm', label: t('menu.llm'), routeName: 'llm-management', icon: Cpu },
  { index: 'usage', label: t('menu.usage'), routeName: 'usage-management', icon: Histogram },
  { index: 'project-info', label: t('menu.projectInfo'), routeName: 'project-info', icon: InfoFilled }
])

const activeMenu = computed(() => (route.meta.menu as string | undefined) ?? 'prompt')
const isDarkTheme = computed(() =>
  themeMode.value === 'system'
    ? systemPrefersDark.value
    : themeMode.value === 'dark'
)
const themeIcon = computed(() => {
  if (themeMode.value === 'system') {
    return Monitor
  }
  return isDarkTheme.value ? Moon : Sunny
})
const themeTooltip = computed(() => {
  if (themeMode.value === 'system') {
    return t('app.themeSystem')
  }
  return isDarkTheme.value ? t('app.themeDark') : t('app.themeLight')
})

watch(language, (value) => {
  setLocale(value)
})

watch(isDarkTheme, (value) => toggleTheme(value), { immediate: true })
watch(themeMode, (value) => {
  window.localStorage.setItem(THEME_MODE_STORAGE_KEY, value)
})
watch(themeColor, (value) => {
  applyThemeColor(value)
  window.localStorage.setItem(THEME_COLOR_STORAGE_KEY, value)
}, { immediate: true })

watch(
  () => [
    quickTestTimeout.value,
    testTaskTimeout.value,
    aiOptimizationTimeout.value
  ],
  () => {
    if (!settingsDialogVisible.value || settingsLoading.value) {
      return
    }
    syncSettingsFormFromRefs()
  }
)

watch(settingsDialogVisible, (visible) => {
  if (!visible) {
    settingsFormRef.value?.clearValidate()
  }
})

async function handleOpenSettings() {
  settingsDialogVisible.value = true
  settingsLoading.value = true
  try {
    await fetchTimeouts(true)
    syncSettingsFormFromRefs()
    await nextTick()
    settingsFormRef.value?.clearValidate()
  } catch (error) {
    if (import.meta.env.DEV) {
      // eslint-disable-next-line no-console
      console.warn('[settings] load failed', error)
    }
    ElMessage.error(t('app.settingsLoadFailed'))
    syncSettingsFormFromRefs()
  } finally {
    settingsLoading.value = false
  }
}

function handleSettingsCancel() {
  settingsDialogVisible.value = false
}

function handleLanguageCommand(command: string | number | object) {
  if (command === 'zh-CN' || command === 'en-US') {
    language.value = command
  }
}

function handleThemeCommand(command: string | number | object) {
  if (command === 'system' || command === 'light' || command === 'dark') {
    themeMode.value = command
  }
}

function handleThemeColorSelect(value: ThemeColor) {
  themeColor.value = value
}

async function handleSettingsConfirm() {
  if (settingsSaving.value) {
    return
  }
  const form = settingsFormRef.value
  if (!form) {
    return
  }

  try {
    await form.validate()
  } catch (error) {
    void error
    return
  }

  settingsSaving.value = true
  try {
    await saveTimeouts({
      quickTestTimeout: settingsForm.quickTestTimeout,
      testTaskTimeout: settingsForm.testTaskTimeout,
      aiOptimizationTimeout: settingsForm.aiOptimizationTimeout
    })
    ElMessage.success(t('app.settingsSaveSuccess'))
    settingsDialogVisible.value = false
  } catch (error) {
    if (import.meta.env.DEV) {
      // eslint-disable-next-line no-console
      console.error('[settings] save failed', error)
    }
    ElMessage.error(t('app.settingsSaveFailed'))
  } finally {
    settingsSaving.value = false
  }
}

function toggleTheme(value: boolean) {
  const root = document.documentElement
  if (value) {
    root.classList.add('dark')
  } else {
    root.classList.remove('dark')
  }
}

function applyThemeColor(value: ThemeColor) {
  const option =
    themeColorOptions.find((item) => item.value === value) ?? themeColorOptions[0]
  const root = document.documentElement
  root.style.setProperty('--el-color-primary', option.primary)
  root.style.setProperty('--el-color-primary-dark-2', option.dark2)
  root.style.setProperty('--el-color-primary-light-3', option.light3)
  root.style.setProperty('--el-color-primary-light-5', option.light5)
  root.style.setProperty('--el-color-primary-light-7', option.light7)
  root.style.setProperty('--el-color-primary-light-8', option.light8)
  root.style.setProperty('--el-color-primary-light-9', option.light9)
}

function handleMenuSelect(index: string) {
  const target = menuItems.value.find((item) => item.index === index)
  if (target) {
    router.push({ name: target.routeName })
  }
}

onMounted(() => {
  colorSchemeQuery = window.matchMedia('(prefers-color-scheme: dark)')
  systemPrefersDark.value = colorSchemeQuery.matches
  colorSchemeQuery.addEventListener('change', handleSystemThemeChange)

  checkProjectVersionOncePerDay().catch((error) => {
    if (import.meta.env.DEV) {
      console.warn('[project-version] daily check failed', error)
    }
    writeProjectVersionCheckCache({
      current: APP_VERSION,
      latest: null,
      has_update: false,
      check_status: 'failed',
      release_url: null,
      deployment_type: 'unknown',
      update_guidance: {
        deployment_type: 'unknown',
        title: '',
        steps: [],
        commands: []
      }
    })
  })
})

onUnmounted(() => {
  colorSchemeQuery?.removeEventListener('change', handleSystemThemeChange)
})
</script>

<style scoped>
.app-shell {
  min-height: 100vh;
  background: var(--app-bg-color);
}

.app-container {
  min-height: 100vh;
  padding-left: 220px;
}

.brand-row {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 64px;
  padding: 0 20px;
}

.brand-logo {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  object-fit: cover;
}

.app-title {
  font-size: 20px;
  font-weight: 600;
  line-height: 1;
}

.side-divider {
  height: 1px;
  margin: 0 16px 12px;
  background: var(--side-border-color);
}

.side-nav {
  position: fixed;
  inset: 0 auto 0 0;
  z-index: 10;
  height: 100vh;
  background: var(--side-bg-color);
  border-right: 1px solid var(--side-border-color);
  overflow: hidden;
}

.side-menu {
  border-right: none;
  background: transparent;
}

.side-menu :deep(.el-menu-item) {
  height: 44px;
  margin: 4px 10px;
  border-radius: 8px;
}

.side-menu :deep(.el-menu-item.is-active) {
  background: var(--el-color-primary-light-9);
}

.main-view {
  min-height: 100vh;
  padding: 0 24px 24px;
  background: var(--content-bg-color);
}

.main-toolbar-space {
  height: 76px;
}

.global-action-card {
  position: fixed;
  top: 16px;
  right: 24px;
  z-index: 30;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 5px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
  background: var(--header-bg-color);
  box-shadow: var(--el-box-shadow-light);
}

.global-action-button {
  width: 34px;
  height: 34px;
}

.theme-color-panel {
  margin: 4px 0 0;
  padding: 8px 12px 10px;
  border-top: 1px solid var(--el-border-color-lighter);
  list-style: none;
}

.theme-color-panel__title {
  margin-bottom: 8px;
  font-size: 12px;
  line-height: 1;
  color: var(--el-text-color-secondary);
}

.theme-color-options {
  display: grid;
  grid-template-columns: repeat(5, 24px);
  gap: 8px;
}

.theme-color-option {
  width: 24px;
  height: 24px;
  padding: 0;
  border: 2px solid transparent;
  border-radius: 50%;
  background: var(--theme-option-color);
  box-shadow: inset 0 0 0 1px rgb(255 255 255 / 58%);
  cursor: pointer;
}

.theme-color-option:hover,
.theme-color-option:focus-visible {
  border-color: var(--el-color-primary-light-5);
  outline: none;
}

.theme-color-option.is-active {
  border-color: var(--el-color-primary);
  box-shadow:
    0 0 0 2px var(--el-color-primary-light-8),
    inset 0 0 0 1px rgb(255 255 255 / 70%);
}

.settings-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.settings-input-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.settings-input-unit {
  color: var(--el-text-color-secondary);
}

.settings-hint {
  margin: 0;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

@media (max-width: 768px) {
  .app-container {
    padding-left: 72px;
  }

  .side-nav {
    width: 72px !important;
  }

  .brand-row {
    justify-content: center;
    padding: 0;
  }

  .app-title,
  .side-menu :deep(.el-menu-item span) {
    display: none;
  }

  .side-menu :deep(.el-menu-item) {
    justify-content: center;
    margin: 4px 8px;
    padding: 0;
  }

  .main-view {
    padding: 0 16px 20px;
  }

  .main-toolbar-space {
    height: 72px;
  }

  .global-action-card {
    top: 14px;
    right: 16px;
  }
}
</style>
