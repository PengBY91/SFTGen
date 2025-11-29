import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes: Array<RouteRecordRaw> = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { title: '登录', requiresAuth: false }
  },
  {
    path: '/',
    name: 'Layout',
    component: () => import('@/views/Layout.vue'),
    redirect: '/tasks',
    meta: { requiresAuth: true },
    children: [
      {
        path: '/tasks',
        name: 'Tasks',
        component: () => import('@/views/Tasks.vue'),
        meta: { title: '任务管理', requiresAuth: true }
      },
      {
        path: '/create',
        name: 'CreateTask',
        component: () => import('@/views/CreateTask.vue'),
        meta: { title: '新建任务', requiresAuth: true, requiresAdmin: true }
      },
      {
        path: '/config',
        name: 'Config',
        component: () => import('@/views/Config.vue'),
        meta: { title: '配置设置', requiresAuth: true, requiresAdmin: true }
      },
      {
        path: '/task/:id',
        name: 'TaskDetail',
        component: () => import('@/views/TaskDetail.vue'),
        meta: { title: '任务详情', requiresAuth: true }
      },
      {
        path: '/review/:id',
        name: 'Review',
        component: () => import('@/views/Review.vue'),
        meta: { title: '数据审核', requiresAuth: true }
      },
      {
        path: '/review/:id/detail/:itemId',
        name: 'ReviewDetail',
        component: () => import('@/views/ReviewDetail.vue'),
        meta: { title: '数据详情', requiresAuth: true }
      },
      {
        path: '/users',
        name: 'Users',
        component: () => import('@/views/Users.vue'),
        meta: { title: '用户管理', requiresAuth: true, requiresAdmin: true }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

router.beforeEach(async (to, from, next) => {
  try {
    const title = to.meta.title as string
    if (title) {
      document.title = `${title} - KGE-Gen`
    }
    
    const authStore = useAuthStore()
    const requiresAuth = to.matched.some(record => record.meta.requiresAuth)
    const requiresAdmin = to.matched.some(record => record.meta.requiresAdmin)
    
    // 如果需要认证
    if (requiresAuth) {
      // 如果没有 token，跳转到登录页
      if (!authStore.token) {
        next('/login')
        return
      }
      
      // 如果有 token 但没有用户信息，尝试获取
      if (!authStore.user) {
        try {
          await authStore.initUser()
          // 如果初始化后仍然没有用户信息，跳转到登录页
          if (!authStore.user) {
            next('/login')
            return
          }
        } catch (error) {
          // API 调用失败，如果仍然没有用户信息，跳转到登录页
          if (!authStore.user) {
            console.warn('Failed to initialize user:', error)
            next('/login')
            return
          }
          // 如果有用户信息（从 localStorage 恢复），继续导航
          console.warn('API call failed but using cached user info:', error)
        }
      }
      
      // 检查管理员权限
      if (requiresAdmin && !authStore.isAdmin) {
        next('/tasks')
        return
      }
    }
    
    // 如果已登录，访问登录页，跳转到任务页
    if (to.path === '/login' && authStore.isAuthenticated) {
      next('/tasks')
      return
    }
    
    next()
  } catch (error) {
    // 捕获所有未处理的错误，避免路由阻塞
    console.error('Router navigation error:', error)
    // 如果访问的是需要认证的页面，跳转到登录页
    const requiresAuth = to.matched.some(record => record.meta.requiresAuth)
    if (requiresAuth) {
      next('/login')
    } else {
      next()
    }
  }
})

export default router

