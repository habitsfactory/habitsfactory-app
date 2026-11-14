import { createRouter, createWebHistory } from 'vue-router'
import LoginView from '@/views/LoginView.vue'
import DashboardView from '@/views/DashboardView.vue'
import authService from '@/services/auth'

// Secondary pages are loaded on demand to keep the initial bundle small
const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  scrollBehavior(to, from) {
    // Don't jump to the top when only the query changes (dashboard tabs)
    if (to.path === from.path) return false
    return { top: 0 }
  },
  routes: [
    {
      path: '/login',
      name: 'login',
      component: LoginView,
      meta: { requiresAuth: false }
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('@/views/RegisterView.vue'),
      meta: { requiresAuth: false }
    },
    {
      path: '/register-admin',
      name: 'register-admin',
      component: () => import('@/views/RegisterAdminView.vue'),
      meta: { requiresAuth: false }
    },
    {
      path: '/dashboard',
      name: 'dashboard',
      component: DashboardView,
      meta: { requiresAuth: true }
    },
    {
      path: '/admin-settings',
      name: 'admin-settings',
      component: () => import('@/views/AdminSettings.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/profile',
      name: 'profile',
      component: () => import('@/views/ProfileView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/export',
      name: 'export',
      component: () => import('@/views/ExportView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/import',
      name: 'import',
      component: () => import('@/views/ImportView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/',
      redirect: '/dashboard'
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/dashboard'
    }
  ]
})

// Navigation guard
router.beforeEach((to, from, next) => {
  const isAuthenticated = authService.isAuthenticated()

  if (to.meta.requiresAuth && !isAuthenticated) {
    next('/login')
  } else if (!to.meta.requiresAuth && isAuthenticated && (to.path === '/login' || to.path === '/register')) {
    next('/dashboard')
  } else {
    next()
  }
})

export default router
