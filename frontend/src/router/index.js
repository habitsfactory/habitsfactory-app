import { createRouter, createWebHistory } from 'vue-router'
import LoginView from '@/views/LoginView.vue'
import RegisterView from '@/views/RegisterView.vue'
import RegisterAdminView from '@/views/RegisterAdminView.vue'
import DashboardView from '@/views/DashboardView.vue'
import AdminSettings from '@/views/AdminSettings.vue'
import ProfileView from '@/views/ProfileView.vue'
import ExportView from '@/views/ExportView.vue'
import authService from '@/services/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  scrollBehavior() {
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
      component: RegisterView,
      meta: { requiresAuth: false }
    },
    {
      path: '/register-admin',
      name: 'register-admin',
      component: RegisterAdminView,
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
      component: AdminSettings,
      meta: { requiresAuth: true }
    },
    {
      path: '/profile',
      name: 'profile',
      component: ProfileView,
      meta: { requiresAuth: true }
    },
    {
      path: '/export',
      name: 'export',
      component: ExportView,
      meta: { requiresAuth: true }
    },
    {
      path: '/',
      redirect: '/dashboard'
    }
  ]
})

// Navigation guard
router.beforeEach((to, from, next) => {
  const isAuthenticated = !!authService.getAccessToken()

  if (to.meta.requiresAuth && !isAuthenticated) {
    next('/login')
  } else if (!to.meta.requiresAuth && isAuthenticated && (to.path === '/login' || to.path === '/register')) {
    next('/dashboard')
  } else {
    next()
  }
})

export default router