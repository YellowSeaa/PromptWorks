import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const root = resolve(import.meta.dirname, '..')
const read = (path) => readFileSync(resolve(root, path), 'utf8')

const http = read('src/api/http.ts')
const dockerfile = read('Dockerfile')
const nginx = read('nginx.conf')
const promptApi = read('src/api/prompt.ts')
const promptClassApi = read('src/api/promptClass.ts')
const promptTagApi = read('src/api/promptTag.ts')
const llmApi = read('src/api/llmProvider.ts')
const testRunApi = read('src/api/testRun.ts')
const promptManagement = read('src/views/PromptManagementView.vue')
const promptDetail = read('src/views/PromptDetailView.vue')
const promptTestCreate = read('src/views/PromptTestTaskCreateView.vue')

const checks = [
  {
    name: 'API 默认基址使用相对路径',
    pass:
      http.includes("const DEFAULT_BASE_URL = '/api/v1'") &&
      !http.includes('http://localhost:8000/api/v1') &&
      dockerfile.includes('ARG VITE_API_BASE_URL="/api/v1"')
  },
  {
    name: 'Nginx 将 /api/v1 反向代理到后端服务',
    pass:
      nginx.includes('location /api/v1/') &&
      nginx.includes('proxy_pass http://backend:8000/api/v1/') &&
      nginx.includes('location = /api/v1')
  },
  {
    name: '集合根路由请求带尾斜杠避免 FastAPI 307',
    pass:
      promptApi.includes('const path = `/prompts/${query ? `?${query}` : \'\'}') &&
      promptClassApi.includes('const path = `/prompt-classes/${query ? `?${query}` : \'\'}') &&
      promptClassApi.includes("request<PromptClassStats>('/prompt-classes/'") &&
      promptTagApi.includes("request<PromptTagListResponse>('/prompt-tags/'") &&
      promptTagApi.includes("request<PromptTagStats>('/prompt-tags/'") &&
      llmApi.includes("const BASE_PATH = '/llm-providers/'") &&
      testRunApi.includes('`/test_prompt/${query}`')
  },
  {
    name: '新建 Prompt 表单使用字段级校验',
    pass:
      promptManagement.includes('ref="createFormRef"') &&
      promptManagement.includes(':rules="createRules"') &&
      promptManagement.includes('prop="name"') &&
      promptManagement.includes('prop="classId"') &&
      promptManagement.includes('prop="version"') &&
      promptManagement.includes('prop="content"') &&
      promptManagement.includes('await createFormRef.value?.validate()') &&
      !promptManagement.includes("ElMessage.warning(t('promptManagement.messages.missingRequired'))")
  },
  {
    name: 'Prompt 详情元信息保存成功后关闭弹窗',
    pass:
      promptDetail.includes('@mousedown.prevent.stop="handleSaveMeta"') &&
      promptDetail.includes('if (isMetaSaving.value)') &&
      promptDetail.includes('await fetchMeta()\n    metaDialogVisible.value = false') &&
      promptDetail.indexOf('await updatePrompt(prompt.id') <
        promptDetail.indexOf('await fetchMeta()\n    metaDialogVisible.value = false')
  },
  {
    name: '新建测试任务版本下拉支持悬停查看 Prompt 内容',
    pass:
      promptTestCreate.includes('<el-tooltip') &&
      promptTestCreate.includes('formatPromptVersionPreview(option.content)') &&
      promptTestCreate.includes('prompt-version-option__preview') &&
      promptTestCreate.includes('content: version.content')
  }
]

const failed = checks.filter((check) => !check.pass)

for (const check of checks) {
  console.log(`${check.pass ? 'PASS' : 'FAIL'} ${check.name}`)
}

if (failed.length) {
  process.exitCode = 1
}
