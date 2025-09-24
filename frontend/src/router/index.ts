import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'prompt-management',
      component: () => import('../views/PromptManagementView.vue'),
      meta: { menu: 'prompt', title: 'Prompt ����' }
    },
    {
      path: '/prompts/:id',
      name: 'prompt-detail',
      component: () => import('../views/PromptDetailView.vue'),
      meta: { menu: 'prompt', title: 'Prompt ����' }
    },
    {
      path: '/llms',
      name: 'llm-management',
      component: () => import('../views/LLMManagementView.vue'),
      meta: { menu: 'llm', title: 'LLMs ����' }
    },
    { path: '/:pathMatch(.*)*', redirect: '/' }
  ]
})

export default router
