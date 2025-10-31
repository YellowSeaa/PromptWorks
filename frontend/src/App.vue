<template>
  <el-config-provider :locale="elementLocale">
    <div class="app-shell">
      <el-container class="app-container">
        <el-header class="app-header" height="64px">
          <div class="header-left">
            <span class="app-title">{{ t('app.title') }}</span>
          </div>
          <div class="header-right">
            <el-button type="primary" :icon="Setting" text @click="handleOpenSettings">
              {{ t('app.settings') }}
            </el-button>
            <el-select v-model="language" size="small" class="language-select">
              <el-option :label="t('app.languageCn')" value="zh-CN" />
              <el-option :label="t('app.languageEn')" value="en-US" />
            </el-select>
            <el-switch
              v-model="isDark"
              inline-prompt
              :active-icon="Moon"
              :inactive-icon="Sunny"
              active-color="#303133"
              inactive-color="#409EFF"
            />
          </div>
        </el-header>
        <el-container>
          <el-aside width="220px" class="side-nav">
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
            <router-view />
          </el-main>
        </el-container>
      </el-container>
    </div>

    <el-dialog
      v-model="settingsDialogVisible"
      :title="t('app.settingsDialogTitle')"
      width="420px"
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
        <p class="settings-hint">
          {{ t('app.settingsTimeoutHint', { min: TIMEOUT_MIN, max: TIMEOUT_MAX }) }}
        </p>
        <p class="settings-updated">{{ settingsUpdatedText }}</p>
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
import { computed, nextTick, reactive, ref, watch } from 'vue'
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
  Sunny,
  Moon
} from '@element-plus/icons-vue'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import enUs from 'element-plus/es/locale/lang/en'
import { useI18n } from 'vue-i18n'
import { setLocale } from './i18n'
import type { SupportedLocale } from './i18n/messages'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { useTestingSettings, DEFAULT_TIMEOUT_SECONDS } from './composables/useTestingSettings'

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
const isDark = ref(false)

const {
  quickTestTimeout,
  testTaskTimeout,
  timeoutUpdatedAt,
  fetchTimeouts,
  saveTimeouts
} = useTestingSettings()

const settingsDialogVisible = ref(false)
const settingsLoading = ref(false)
const settingsSaving = ref(false)
const settingsFormRef = ref<FormInstance>()
const settingsForm = reactive({
  quickTestTimeout: DEFAULT_TIMEOUT_SECONDS,
  testTaskTimeout: DEFAULT_TIMEOUT_SECONDS
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
  ]
}

function formatSettingsTimestamp(value: string | null): string | null {
  if (!value) return null
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return null
  }
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hour = String(date.getHours()).padStart(2, '0')
  const minute = String(date.getMinutes()).padStart(2, '0')
  return `${year}-${month}-${day} ${hour}:${minute}`
}

const settingsUpdatedText = computed(() => {
  const formatted = formatSettingsTimestamp(timeoutUpdatedAt.value)
  if (!formatted) {
    return t('app.settingsNeverUpdated')
  }
  return t('app.settingsLastUpdated', { time: formatted })
})

function syncSettingsFormFromRefs() {
  settingsForm.quickTestTimeout =
    quickTestTimeout.value ?? DEFAULT_TIMEOUT_SECONDS
  settingsForm.testTaskTimeout =
    testTaskTimeout.value ?? DEFAULT_TIMEOUT_SECONDS
}

const menuItems = computed<MenuItem[]>(() => [
  { index: 'prompt', label: t('menu.prompt'), routeName: 'prompt-management', icon: Collection },
  { index: 'quick-test', label: t('menu.quickTest'), routeName: 'quick-test', icon: MagicStick },
  { index: 'test-job', label: t('menu.testJob'), routeName: 'test-job-management', icon: Memo },
  { index: 'class', label: t('menu.class'), routeName: 'class-management', icon: Files },
  { index: 'tag', label: t('menu.tag'), routeName: 'tag-management', icon: Tickets },
  { index: 'llm', label: t('menu.llm'), routeName: 'llm-management', icon: Cpu },
  { index: 'usage', label: t('menu.usage'), routeName: 'usage-management', icon: Histogram }
])

const activeMenu = computed(() => (route.meta.menu as string | undefined) ?? 'prompt')

watch(language, (value) => {
  setLocale(value)
})

watch(isDark, (value) => toggleTheme(value), { immediate: true })

watch(
  () => [quickTestTimeout.value, testTaskTimeout.value],
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
      testTaskTimeout: settingsForm.testTaskTimeout
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

function handleMenuSelect(index: string) {
  const target = menuItems.value.find((item) => item.index === index)
  if (target) {
    router.push({ name: target.routeName })
  }
}
</script>

<style scoped>
.app-shell {
  min-height: 100vh;
  background: var(--app-bg-color);
}

.app-container {
  min-height: 100vh;
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: var(--header-bg-color);
  color: var(--header-text-color);
  box-shadow: 0 1px 4px rgb(0 0 0 / 10%);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.app-title {
  font-size: 20px;
  font-weight: 600;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.language-select {
  width: 120px;
}

.side-nav {
  background: var(--side-bg-color);
  border-right: 1px solid var(--side-border-color);
}

.side-menu {
  border-right: none;
}

.main-view {
  padding: 24px;
  background: var(--content-bg-color);
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

.settings-updated {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>
