import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const root = resolve(import.meta.dirname, '..')
const appVue = readFileSync(resolve(root, 'src/App.vue'), 'utf8')
const usageManagementVue = readFileSync(resolve(root, 'src/views/UsageManagementView.vue'), 'utf8')
const messages = readFileSync(resolve(root, 'src/i18n/messages.ts'), 'utf8')

const checks = [
  {
    name: '品牌区使用 logo 且不显示版本徽标',
    pass:
      appVue.includes('src="/logo.png"') &&
      !appVue.includes('app-version') &&
      !appVue.includes('APP_VERSION }}</span>')
  },
  {
    name: '左侧导航固定在视口内',
    pass:
      appVue.includes('.side-nav') &&
      appVue.includes('position: fixed') &&
      appVue.includes('height: 100vh')
  },
  {
    name: '右上角工具卡片按语言、主题、设置排序',
    pass:
      appVue.indexOf('global-action-card') !== -1 &&
      appVue.indexOf('handleLanguageCommand') < appVue.indexOf('handleThemeCommand') &&
      appVue.indexOf('handleThemeCommand') < appVue.indexOf('handleOpenSettings')
  },
  {
    name: '语言和主题下拉按钮不嵌套 Tooltip 触发器',
    pass:
      !appVue.includes('<el-dropdown trigger="click" @command="handleLanguageCommand">\n          <el-tooltip') &&
      !appVue.includes('<el-dropdown trigger="click" @command="handleThemeCommand">\n          <el-tooltip')
  },
  {
    name: '深色模式下左侧菜单 hover 仍保持可读',
    pass:
      appVue.includes('.dark .side-menu :deep(.el-menu-item:hover)') &&
      appVue.includes('--el-text-color-primary') &&
      appVue.includes('color: var(--el-text-color-primary);')
  },
  {
    name: '语言入口使用合适图标且英文模式中文选项仍显示中文',
    pass:
      appVue.includes(':icon="Reading"') &&
      !appVue.includes(':icon="Connection"') &&
      messages.includes("languageCn: '中文'")
  },
  {
    name: '设置弹窗不展示超时时间更新时间提示',
    pass:
      !appVue.includes('settings-updated') &&
      !appVue.includes('settingsUpdatedText') &&
      !messages.includes('settingsNeverUpdated') &&
      !messages.includes('settingsLastUpdated')
  },
  {
    name: '主题模式支持 system',
    pass:
      appVue.includes("type ThemeMode = 'system' | 'light' | 'dark'") &&
      appVue.includes('prefers-color-scheme: dark') &&
      messages.includes("themeSystem: '跟随系统'")
  },
  {
    name: '用量监控统计卡片在桌面端保持一行',
    pass:
      usageManagementVue.includes('<div class="overview-row">') &&
      usageManagementVue.includes('grid-template-columns: repeat(5, minmax(0, 1fr))') &&
      !usageManagementVue.includes(':sm="6" v-for="card in overviewCards"')
  },
  {
    name: '深色模式下模型表格当前行使用深色高亮',
    pass:
      usageManagementVue.includes('.dark .model-card :deep(.el-table__body tr.is-active > td)') &&
      usageManagementVue.includes('--el-table-tr-bg-color') &&
      usageManagementVue.includes('--el-fill-color-light')
  },
  {
    name: '中文菜单使用提示词管理和模型管理',
    pass:
      messages.includes("prompt: '提示词管理'") &&
      messages.includes("llm: '模型管理'")
  }
]

const failed = checks.filter((check) => !check.pass)

for (const check of checks) {
  console.log(`${check.pass ? 'PASS' : 'FAIL'} ${check.name}`)
}

if (failed.length) {
  process.exitCode = 1
}
