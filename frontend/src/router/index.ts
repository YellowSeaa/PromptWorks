import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'prompt-management',
      component: () => import('../views/PromptManagementView.vue'),
      meta: { menu: 'prompt', title: 'Prompt 管理' }
    },
    {
      path: '/prompts/:id',
      name: 'prompt-detail',
      component: () => import('../views/PromptDetailView.vue'),
      meta: { menu: 'prompt', title: 'Prompt 详情' }
    },
    {
      path: '/prompts/:id/versions/compare',
      name: 'prompt-version-compare',
      component: () => import('../views/PromptVersionCompareView.vue'),
      meta: { menu: 'prompt', title: '版本对比' }
    },
    {
      path: '/prompts/:id/versions/new',
      name: 'prompt-version-create',
      component: () => import('../views/PromptVersionCreateView.vue'),
      meta: { menu: 'prompt', title: '新增版本' }
    },
    {
      path: '/prompts/:id/tests/new',
      name: 'prompt-test-create',
      component: () => import('../views/TestJobCreateView.vue'),
      meta: { menu: 'prompt', title: '新增测试' }
    },
    {
      path: '/tests/quick',
      name: 'quick-test',
      component: () => import('../views/QuickTestView.vue'),
      meta: { menu: 'quick-test', title: '快速测试' }
    },
    {
      path: '/tests/jobs',
      name: 'test-job-management',
      component: () => import('../views/TestJobManagementView.vue'),
      meta: { menu: 'test-job', title: '测试任务' }
    },
    {
      path: '/tests/jobs/new',
      name: 'test-job-create',
      component: () => import('../views/TestJobCreateView.vue'),
      meta: { menu: 'test-job', title: '新建测试任务' }
    },
    {
      path: '/tests/tasks/new',
      name: 'prompt-test-task-create',
      component: () => import('../views/PromptTestTaskCreateView.vue'),
      meta: { menu: 'test-job', title: '新建测试任务' }
    },
    {
      path: '/tests/tasks/:taskId/result',
      name: 'prompt-test-task-result',
      component: () => import('../views/PromptTestTaskResultView.vue'),
      meta: { menu: 'test-job', title: '测试任务结果（新）' }
    },
    {
      path: '/tests/tasks/:taskId/optimization',
      name: 'prompt-test-optimization',
      component: () => import('../views/PromptTestOptimizationView.vue'),
      meta: { menu: 'test-job', title: 'AI 优化' }
    },
    {
      path: '/tests/tasks/:taskId/units/:unitId',
      name: 'prompt-test-unit-result',
      component: () => import('../views/PromptTestUnitResultView.vue'),
      meta: { menu: 'test-job', title: '最小单元详情（新）' }
    },
    {
      path: '/tests/jobs/:id',
      name: 'test-job-result',
      component: () => import('../views/TestJobResultView.vue'),
      meta: { menu: 'test-job', title: '测试结果' }
    },
    {
      path: '/classes',
      name: 'class-management',
      component: () => import('../views/PromptClassManagementView.vue'),
      meta: { menu: 'class', title: '分类管理' }
    },
    {
      path: '/tags',
      name: 'tag-management',
      component: () => import('../views/PromptTagManagementView.vue'),
      meta: { menu: 'tag', title: '标签管理' }
    },
    {
      path: '/llms',
      name: 'llm-management',
      component: () => import('../views/LLMManagementView.vue'),
      meta: { menu: 'llm', title: 'LLMs 管理' }
    },
    {
      path: '/usage',
      name: 'usage-management',
      component: () => import('../views/UsageManagementView.vue'),
      meta: { menu: 'usage', title: '用量管理' }
    },
    { path: '/:pathMatch(.*)*', redirect: '/' }
  ]
})

export default router
