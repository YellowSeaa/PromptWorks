<template>
  <div class="page project-info-page">
    <el-skeleton v-if="loading && !summary" animated :rows="8" />

    <template v-else-if="summary">
      <section class="hero-card">
        <div class="hero-card__main">
          <div class="project-mark">PW</div>
          <div class="project-copy">
            <div class="project-kicker">{{ t('projectInfo.kicker') }}</div>
            <h2>{{ summary.project.name }}</h2>
            <p>{{ summary.project.description }}</p>
            <div class="project-actions">
              <el-button :icon="Link" type="primary" @click="openExternal(summary.project.github_url)">
                GitHub
              </el-button>
              <el-button :icon="Message" @click="openEmail">
                {{ summary.project.contact_email }}
              </el-button>
              <el-tooltip :content="t('projectInfo.tutorialComingSoon')" placement="top">
                <el-button :icon="Reading" disabled>
                  {{ t('projectInfo.tutorial') }}
                </el-button>
              </el-tooltip>
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
          :xs="12"
          :sm="8"
          :lg="6"
        >
          <el-card class="stat-card" shadow="hover">
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
        <el-col :xs="24" :lg="14">
          <el-card class="version-card" shadow="hover">
            <template #header>
              <div class="card-header">
                <div>
                  <span>{{ t('projectInfo.version.title') }}</span>
                  <p>{{ t('projectInfo.version.subtitle') }}</p>
                </div>
                <el-button
                  type="primary"
                  :icon="Refresh"
                  :loading="checking"
                  @click="handleCheckVersion"
                >
                  {{ t('projectInfo.version.check') }}
                </el-button>
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
            />
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

        <el-col :xs="24" :lg="10">
          <el-card class="guidance-card" shadow="hover">
            <template #header>
              <div class="card-header card-header--plain">
                <span>{{ versionInfo.update_guidance.title }}</span>
              </div>
            </template>
            <ol class="guidance-list">
              <li v-for="step in versionInfo.update_guidance.steps" :key="step">
                {{ step }}
              </li>
            </ol>
            <el-button
              v-if="versionInfo.release_url"
              class="release-link"
              text
              type="primary"
              :icon="Link"
              @click="openExternal(versionInfo.release_url)"
            >
              {{ t('projectInfo.version.releaseNotes') }}
            </el-button>
          </el-card>
        </el-col>
      </el-row>
    </template>

    <el-empty v-else :description="t('projectInfo.empty')" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import {
  Collection,
  Cpu,
  Files,
  Histogram,
  Link,
  Memo,
  Message,
  Reading,
  Refresh,
  Tickets
} from '@element-plus/icons-vue'
import {
  checkProjectVersion,
  getProjectInfoSummary,
  type ProjectInfoSummaryResponse,
  type ProjectVersionInfoResponse
} from '../api/projectInfo'

const { t, locale } = useI18n()

const summary = ref<ProjectInfoSummaryResponse | null>(null)
const loading = ref(false)
const checking = ref(false)

const versionInfo = computed<ProjectVersionInfoResponse>(() => {
  if (summary.value) {
    return summary.value.version
  }
  return {
    current: 'v0.0.0',
    latest: null,
    has_update: false,
    release_url: null,
    deployment_type: 'unknown',
    update_guidance: {
      deployment_type: 'unknown',
      title: '',
      steps: []
    }
  }
})

const statisticCards = computed(() => {
  const stats = summary.value?.statistics
  return [
    {
      key: 'providers',
      label: t('projectInfo.stats.providers'),
      value: stats?.provider_count ?? 0,
      icon: Cpu
    },
    {
      key: 'models',
      label: t('projectInfo.stats.models'),
      value: stats?.model_count ?? 0,
      icon: Histogram
    },
    {
      key: 'prompts',
      label: t('projectInfo.stats.prompts'),
      value: stats?.prompt_count ?? 0,
      icon: Collection
    },
    {
      key: 'versions',
      label: t('projectInfo.stats.promptVersions'),
      value: stats?.prompt_version_count ?? 0,
      icon: Files
    },
    {
      key: 'tasks',
      label: t('projectInfo.stats.testTasks'),
      value: stats?.test_task_count ?? 0,
      icon: Memo
    },
    {
      key: 'units',
      label: t('projectInfo.stats.testUnits'),
      value: stats?.test_unit_count ?? 0,
      icon: Tickets
    }
  ]
})

const numberLocale = computed(() => (locale.value === 'zh-CN' ? 'zh-CN' : 'en-US'))

const versionStatusText = computed(() => {
  if (versionInfo.value.has_update) {
    return t('projectInfo.version.statusUpdate')
  }
  if (versionInfo.value.latest) {
    return t('projectInfo.version.statusLatest')
  }
  return t('projectInfo.version.statusRemoteUnknown')
})

const versionTagType = computed(() => (versionInfo.value.has_update ? 'success' : 'info'))

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

async function loadSummary() {
  loading.value = true
  try {
    summary.value = await getProjectInfoSummary()
  } catch (error) {
    console.error(error)
    ElMessage.error(t('projectInfo.messages.loadFailed'))
  } finally {
    loading.value = false
  }
}

async function handleCheckVersion() {
  checking.value = true
  try {
    const version = await checkProjectVersion()
    if (summary.value) {
      summary.value = { ...summary.value, version }
    }
    ElMessage.success(t('projectInfo.messages.checkSuccess'))
  } catch (error) {
    console.error(error)
    ElMessage.error(t('projectInfo.messages.checkFailed'))
  } finally {
    checking.value = false
  }
}

onMounted(() => {
  loadSummary()
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
  gap: 24px;
  padding: 28px;
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
  gap: 20px;
  min-width: 0;
}

.project-mark {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 64px;
  width: 64px;
  height: 64px;
  border-radius: 8px;
  color: #ffffff;
  background: #1f2d3d;
  font-size: 22px;
  font-weight: 700;
}

.project-copy {
  min-width: 0;
}

.project-kicker {
  margin-bottom: 6px;
  color: var(--el-color-primary);
  font-size: 13px;
  font-weight: 600;
}

.project-copy h2 {
  margin: 0;
  color: var(--header-text-color);
  font-size: 30px;
  line-height: 1.2;
}

.project-copy p {
  max-width: 760px;
  margin: 10px 0 18px;
  color: var(--text-weak-color);
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
  gap: 10px;
  min-width: 160px;
}

.version-label {
  color: var(--text-weak-color);
  font-size: 13px;
}

.hero-card__version strong {
  color: var(--header-text-color);
  font-size: 28px;
  line-height: 1;
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

.version-card,
.guidance-card {
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

.card-header--plain {
  justify-content: flex-start;
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

.guidance-list {
  margin: 0;
  padding-left: 20px;
  color: var(--header-text-color);
}

.guidance-list li + li {
  margin-top: 10px;
}

.release-link {
  margin-top: 16px;
  padding-left: 0;
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
}

@media (max-width: 640px) {
  .hero-card {
    padding: 20px;
  }

  .hero-card__main {
    flex-direction: column;
  }

  .project-copy h2 {
    font-size: 24px;
  }
}
</style>
