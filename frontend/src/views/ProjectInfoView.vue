<template>
  <div class="page project-info-page">
    <el-skeleton v-if="loading && !summary" animated :rows="8" />

    <template v-else-if="summary">
      <section class="hero-card">
        <div class="hero-card__main">
          <img class="project-logo" src="/logo.png" alt="PromptWorks" />
          <div class="project-copy">
            <div class="project-kicker">{{ t('projectInfo.kicker') }}</div>
            <h2>{{ summary.project.name }}</h2>
            <p>{{ t('projectInfo.description') }}</p>
            <div class="project-actions">
              <el-button type="primary" @click="openExternal(summary.project.github_url)">
                <svg class="button-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                  <path
                    fill="currentColor"
                    d="M12 .5C5.65.5.5 5.65.5 12c0 5.08 3.29 9.39 7.86 10.91.58.11.79-.25.79-.56v-2.17c-3.2.7-3.88-1.36-3.88-1.36-.52-1.33-1.28-1.69-1.28-1.69-1.05-.72.08-.7.08-.7 1.16.08 1.77 1.19 1.77 1.19 1.03 1.76 2.69 1.25 3.35.96.1-.75.4-1.25.73-1.54-2.55-.29-5.23-1.28-5.23-5.68 0-1.25.45-2.28 1.18-3.08-.12-.29-.51-1.46.11-3.04 0 0 .97-.31 3.16 1.18A10.9 10.9 0 0 1 12 6.03c.98 0 1.95.13 2.87.39 2.19-1.49 3.15-1.18 3.15-1.18.63 1.58.24 2.75.12 3.04.74.8 1.18 1.83 1.18 3.08 0 4.41-2.69 5.38-5.25 5.67.41.36.78 1.06.78 2.13v3.19c0 .31.21.67.8.56A11.51 11.51 0 0 0 23.5 12C23.5 5.65 18.35.5 12 .5Z"
                  />
                </svg>
                {{ t('projectInfo.repository') }}
              </el-button>
              <el-tooltip :content="t('projectInfo.tutorialComingSoon')" placement="top">
                <el-button :icon="Reading" disabled>
                  {{ t('projectInfo.tutorial') }}
                </el-button>
              </el-tooltip>
              <el-button :icon="Message" @click="contactDialogVisible = true">
                {{ t('projectInfo.contactAuthor') }}
              </el-button>
            </div>
          </div>
        </div>
        <div class="hero-card__version">
          <span class="version-label">{{ t('projectInfo.currentVersion') }}</span>
          <strong>{{ versionInfo.current }}</strong>
          <el-tag :type="versionTagType" effect="light" round>
            {{ versionStatusText }}
          </el-tag>
        </div>
      </section>

      <el-row :gutter="16" class="stat-grid">
        <el-col
          v-for="stat in statisticCards"
          :key="stat.key"
          :xs="24"
          :sm="12"
          :lg="6"
        >
          <el-card
            class="stat-card"
            :class="{ 'stat-card--clickable': stat.routeName }"
            shadow="hover"
            @click="navigateToStat(stat.routeName)"
          >
            <div class="stat-card__icon">
              <el-icon><component :is="stat.icon" /></el-icon>
            </div>
            <div>
              <div class="stat-card__value">{{ formatNumber(stat.value) }}</div>
              <div class="stat-card__label">{{ stat.label }}</div>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="16" class="detail-row">
        <el-col :xs="24">
          <el-card class="version-card" shadow="hover">
            <template #header>
              <div class="card-header">
                <div>
                  <span>{{ t('projectInfo.version.title') }}</span>
                  <p>{{ t('projectInfo.version.subtitle') }}</p>
                </div>
                <div class="version-actions">
                  <el-button
                    v-if="versionInfo.release_url"
                    :icon="Link"
                    @click="openExternal(versionInfo.release_url)"
                  >
                    {{ t('projectInfo.version.releaseNotes') }}
                  </el-button>
                  <el-button
                    type="primary"
                    :icon="Refresh"
                    :loading="checking"
                    @click="handleCheckVersion"
                  >
                    {{ t('projectInfo.version.check') }}
                  </el-button>
                </div>
              </div>
            </template>

            <div class="version-summary">
              <div class="version-item">
                <span>{{ t('projectInfo.version.current') }}</span>
                <strong>{{ versionInfo.current }}</strong>
              </div>
              <div class="version-item">
                <span>{{ t('projectInfo.version.latest') }}</span>
                <strong>{{ versionInfo.latest ?? t('projectInfo.version.remoteUnknown') }}</strong>
              </div>
              <div class="version-item">
                <span>{{ t('projectInfo.version.deployment') }}</span>
                <strong>{{ deploymentText }}</strong>
              </div>
            </div>

            <el-alert
              v-if="versionInfo.has_update"
              type="success"
              show-icon
              :closable="false"
              class="version-alert"
              :title="t('projectInfo.version.updateAvailable')"
            >
              <template #default>
                <div class="update-command-panel">
                  <div
                    v-for="command in updateCommands"
                    :key="command"
                    class="update-command-panel__line"
                  >
                    <code>{{ command }}</code>
                  </div>
                  <el-button
                    v-if="updateCommands.length"
                    class="copy-command-button"
                    size="small"
                    type="success"
                    plain
                    @click="copyUpdateCommands"
                  >
                    {{ t('projectInfo.version.copyCommands') }}
                  </el-button>
                </div>
              </template>
            </el-alert>
            <el-alert
              v-else
              type="info"
              show-icon
              :closable="false"
              class="version-alert"
              :title="versionInfo.latest ? t('projectInfo.version.upToDate') : t('projectInfo.version.remoteUnknownHint')"
            />
          </el-card>
        </el-col>

      </el-row>
    </template>

    <el-empty v-else :description="t('projectInfo.empty')" />

    <el-dialog v-model="contactDialogVisible" :title="t('projectInfo.contactDialog.title')" width="420px">
      <div class="contact-dialog">
        <p>{{ t('projectInfo.contactDialog.message') }}</p>
        <a :href="`mailto:${summary?.project.contact_email ?? ''}`">
          {{ summary?.project.contact_email }}
        </a>
      </div>
      <template #footer>
        <el-button @click="contactDialogVisible = false">
          {{ t('common.cancel') }}
        </el-button>
        <el-button type="primary" :icon="Message" @click="openEmail">
          {{ t('projectInfo.contactDialog.emailAction') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { useRouter, type RouteRecordName } from 'vue-router'
import {
  Collection,
  Cpu,
  Histogram,
  Link,
  Memo,
  Message,
  Reading,
  Refresh
} from '@element-plus/icons-vue'
import {
  checkProjectVersion,
  getProjectInfoSummary,
  type ProjectInfoSummaryResponse,
  type ProjectVersionInfoResponse
} from '../api/projectInfo'
import {
  PROJECT_VERSION_CHECK_EVENT,
  readCachedProjectVersionCheck,
  writeProjectVersionCheckCache
} from '../utils/projectVersionCheck'

const { t, locale } = useI18n()
const router = useRouter()

const summary = ref<ProjectInfoSummaryResponse | null>(null)
const loading = ref(false)
const checking = ref(false)
const contactDialogVisible = ref(false)

const versionInfo = computed<ProjectVersionInfoResponse>(() => {
  if (summary.value) {
    return summary.value.version
  }
  return {
    current: 'v0.0.0',
    latest: null,
      has_update: false,
      check_status: 'unknown',
      release_url: null,
    deployment_type: 'unknown',
    update_guidance: {
      deployment_type: 'unknown',
      title: '',
      steps: [],
      commands: []
    }
  }
})

const updateCommands = computed(() => versionInfo.value.update_guidance.commands)

const statisticCards = computed(() => {
  const stats = summary.value?.statistics
  return [
    {
      key: 'providers',
      label: t('projectInfo.stats.providers'),
      value: stats?.provider_count ?? 0,
      icon: Cpu,
      routeName: 'llm-management'
    },
    {
      key: 'models',
      label: t('projectInfo.stats.models'),
      value: stats?.model_count ?? 0,
      icon: Histogram,
      routeName: 'llm-management'
    },
    {
      key: 'prompts',
      label: t('projectInfo.stats.prompts'),
      value: stats?.prompt_count ?? 0,
      icon: Collection,
      routeName: 'prompt-management'
    },
    {
      key: 'tasks',
      label: t('projectInfo.stats.testTasks'),
      value: stats?.test_task_count ?? 0,
      icon: Memo,
      routeName: 'test-job-management'
    }
  ]
})

const numberLocale = computed(() => (locale.value === 'zh-CN' ? 'zh-CN' : 'en-US'))

const versionStatusText = computed(() => {
  if (versionInfo.value.check_status === 'failed') {
    return t('projectInfo.version.statusFailed')
  }
  if (versionInfo.value.check_status === 'update_available') {
    return t('projectInfo.version.statusUpdate')
  }
  if (versionInfo.value.check_status === 'up_to_date') {
    return t('projectInfo.version.statusLatest')
  }
  return t('projectInfo.version.statusRemoteUnknown')
})

const versionTagType = computed(() => {
  if (versionInfo.value.check_status === 'failed') return 'danger'
  if (versionInfo.value.check_status === 'update_available') return 'warning'
  if (versionInfo.value.check_status === 'up_to_date') return 'success'
  return 'info'
})

const deploymentText = computed(() => {
  const type = versionInfo.value.deployment_type
  if (type === 'docker') return t('projectInfo.deployment.docker')
  if (type === 'source') return t('projectInfo.deployment.source')
  return t('projectInfo.deployment.unknown')
})

function formatNumber(value: number): string {
  return new Intl.NumberFormat(numberLocale.value).format(value)
}

function openExternal(url: string | null) {
  if (!url) return
  window.open(url, '_blank', 'noopener,noreferrer')
}

function openEmail() {
  const email = summary.value?.project.contact_email
  if (!email) return
  window.location.href = `mailto:${email}`
}

function navigateToStat(routeName?: RouteRecordName) {
  if (!routeName) return
  router.push({ name: routeName })
}

async function copyUpdateCommands() {
  if (!updateCommands.value.length) return
  try {
    await navigator.clipboard.writeText(updateCommands.value.join('\n'))
    ElMessage.success(t('projectInfo.messages.copySuccess'))
  } catch (error) {
    console.error(error)
    ElMessage.error(t('projectInfo.messages.copyFailed'))
  }
}

async function loadSummary() {
  loading.value = true
  try {
    const loadedSummary = await getProjectInfoSummary()
    const cachedVersion = readCachedProjectVersionCheck()
    summary.value = cachedVersion
      ? { ...loadedSummary, version: cachedVersion }
      : loadedSummary
  } catch (error) {
    console.error(error)
    ElMessage.error(t('projectInfo.messages.loadFailed'))
  } finally {
    loading.value = false
  }
}

function handleCachedVersionCheck(event: Event) {
  const version = (event as CustomEvent<ProjectVersionInfoResponse>).detail
  if (!version || !summary.value) return
  summary.value = { ...summary.value, version }
}

async function handleCheckVersion() {
  checking.value = true
  try {
    const version = await checkProjectVersion()
    if (summary.value) {
      summary.value = { ...summary.value, version }
    }
    writeProjectVersionCheckCache(version)
    if (version.check_status === 'failed') {
      ElMessage.error(t('projectInfo.messages.checkFailed'))
    } else {
      ElMessage.success(t('projectInfo.messages.checkSuccess'))
    }
  } catch (error) {
    console.error(error)
    ElMessage.error(t('projectInfo.messages.checkFailed'))
  } finally {
    checking.value = false
  }
}

onMounted(() => {
  window.addEventListener(PROJECT_VERSION_CHECK_EVENT, handleCachedVersionCheck)
  loadSummary()
})

onUnmounted(() => {
  window.removeEventListener(PROJECT_VERSION_CHECK_EVENT, handleCachedVersionCheck)
})
</script>

<style scoped>
.project-info-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.hero-card {
  display: flex;
  align-items: stretch;
  justify-content: space-between;
  gap: 32px;
  padding: 40px 44px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
  background:
    linear-gradient(135deg, rgb(255 255 255 / 94%), rgb(245 248 252 / 96%)),
    radial-gradient(circle at top right, rgb(64 158 255 / 18%), transparent 34%);
  box-shadow: 0 12px 28px rgb(31 35 41 / 8%);
}

.dark .hero-card {
  background:
    linear-gradient(135deg, rgb(31 38 47 / 96%), rgb(28 32 38 / 96%)),
    radial-gradient(circle at top right, rgb(64 158 255 / 18%), transparent 34%);
}

.hero-card__main {
  display: flex;
  gap: 26px;
  min-width: 0;
}

.project-logo {
  flex: 0 0 82px;
  width: 82px;
  height: 82px;
  border-radius: 8px;
  object-fit: contain;
  background: #ffffff;
  box-shadow: 0 4px 14px rgb(31 35 41 / 10%);
}

.project-copy {
  min-width: 0;
}

.project-kicker {
  margin-bottom: 8px;
  color: var(--el-color-primary);
  font-size: 17px;
  font-weight: 700;
}

.project-copy h2 {
  margin: 0;
  color: var(--header-text-color);
  font-size: 36px;
  font-weight: 800;
  line-height: 1.15;
}

.project-copy p {
  max-width: 980px;
  margin: 14px 0 24px;
  color: var(--text-weak-color);
  font-size: 18px;
  line-height: 1.7;
}

.project-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.hero-card__version {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 12px;
  min-width: 250px;
}

.version-label {
  color: var(--text-weak-color);
  font-size: 16px;
  font-weight: 600;
}

.hero-card__version strong {
  color: var(--header-text-color);
  font-size: 28px;
  font-weight: 800;
  line-height: 1;
  white-space: nowrap;
}

.hero-card__version :deep(.el-tag) {
  height: 34px;
  padding: 0 16px;
  font-size: 15px;
  font-weight: 700;
}

.button-icon {
  width: 16px;
  height: 16px;
  margin-right: 6px;
}

.stat-grid {
  row-gap: 16px;
}

.stat-card :deep(.el-card__body) {
  display: flex;
  align-items: center;
  gap: 14px;
  min-height: 96px;
}

.stat-card--clickable {
  cursor: pointer;
  transition:
    border-color 0.2s ease,
    transform 0.2s ease;
}

.stat-card--clickable:hover {
  border-color: var(--el-color-primary-light-5);
  transform: translateY(-2px);
}

.stat-card__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border-radius: 8px;
  color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
  font-size: 20px;
}

.stat-card__value {
  color: var(--header-text-color);
  font-size: 24px;
  font-weight: 700;
  line-height: 1.1;
}

.stat-card__label {
  margin-top: 6px;
  color: var(--text-weak-color);
  font-size: 13px;
}

.detail-row {
  row-gap: 16px;
}

.version-card {
  height: 100%;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.card-header span {
  color: var(--header-text-color);
  font-weight: 600;
}

.card-header p {
  margin: 4px 0 0;
  color: var(--text-weak-color);
  font-size: 13px;
}

.version-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 10px;
}

.version-summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.version-item {
  padding: 14px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
  background: var(--el-fill-color-lighter);
}

.version-item span {
  display: block;
  color: var(--text-weak-color);
  font-size: 12px;
}

.version-item strong {
  display: block;
  margin-top: 8px;
  color: var(--header-text-color);
  font-size: 18px;
}

.version-alert {
  margin-top: 16px;
}

.update-command-panel {
  margin-top: 10px;
}

.update-command-panel__line {
  margin-top: 8px;
  padding: 8px 10px;
  border-radius: 6px;
  background: var(--el-fill-color-lighter);
  color: var(--header-text-color);
  font-size: 13px;
}

.copy-command-button {
  margin-top: 10px;
}

.contact-dialog p {
  margin: 0 0 12px;
  color: var(--text-weak-color);
  line-height: 1.7;
}

.contact-dialog a {
  color: var(--el-color-primary);
  font-weight: 600;
}

@media (max-width: 900px) {
  .hero-card {
    flex-direction: column;
  }

  .hero-card__version {
    align-items: flex-start;
  }

  .version-summary {
    grid-template-columns: 1fr;
  }

  .card-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .version-actions {
    justify-content: flex-start;
  }
}

@media (max-width: 640px) {
  .hero-card {
    padding: 20px;
  }

  .hero-card__main {
    flex-direction: column;
  }

  .project-copy h2 {
    font-size: 30px;
  }

  .project-kicker {
    font-size: 16px;
  }

  .project-copy p {
    font-size: 16px;
  }

  .hero-card__version strong {
    font-size: 24px;
  }
}
</style>
