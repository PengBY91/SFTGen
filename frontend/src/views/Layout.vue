<template>
  <el-container class="layout-container">
    <el-header class="layout-header">
      <div class="logo">
        <h1>KGE-Gen SFT数据生成平台</h1>
      </div>
      <div class="header-right">
        <el-menu
          mode="horizontal"
          :default-active="activeMenu"
          class="header-menu"
          @select="handleMenuSelect"
        >
          <el-menu-item index="/tasks">
            <el-icon><List /></el-icon>
            <span>任务管理</span>
          </el-menu-item>
          <el-menu-item v-if="authStore.isAdmin" index="/create">
            <el-icon><Plus /></el-icon>
            <span>新建任务</span>
          </el-menu-item>
          <el-menu-item v-if="authStore.isAdmin" index="/config">
            <el-icon><Setting /></el-icon>
            <span>配置设置</span>
          </el-menu-item>
          <el-menu-item v-if="authStore.isAdmin" index="/users">
            <el-icon><User /></el-icon>
            <span>用户管理</span>
          </el-menu-item>
        </el-menu>
        
        <el-dropdown @command="handleCommand">
          <div class="user-info">
            <el-avatar :size="32">
              <el-icon><User /></el-icon>
            </el-avatar>
            <span class="username">{{ authStore.user?.username }}</span>
            <el-tag :type="authStore.isAdmin ? 'danger' : 'success'" size="small">
              {{ authStore.isAdmin ? '管理员' : '审核员' }}
            </el-tag>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="profile">
                <el-icon><User /></el-icon>
                个人信息
              </el-dropdown-item>
              <el-dropdown-item command="changePassword">
                <el-icon><Lock /></el-icon>
                修改密码
              </el-dropdown-item>
              <el-dropdown-item divided command="logout">
                <el-icon><SwitchButton /></el-icon>
                退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </el-header>

    <el-main class="layout-main">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </el-main>

    <el-footer class="layout-footer">
      <div class="footer-content">
        <span>KGE-Gen v2.0.0 © 2025</span>
        <div class="footer-links">
          <a href="https://github.com/open-sciencelab/GraphGen" target="_blank">GitHub</a>
          <a href="https://arxiv.org/abs/2505.20416" target="_blank">arXiv</a>
        </div>
      </div>
    </el-footer>
    
    <!-- 修改密码对话框 -->
    <el-dialog
      v-model="changePasswordDialogVisible"
      title="修改密码"
      width="400px"
    >
      <el-form :model="changePasswordForm" label-width="80px">
        <el-form-item label="旧密码">
          <el-input
            v-model="changePasswordForm.oldPassword"
            type="password"
            show-password
          />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input
            v-model="changePasswordForm.newPassword"
            type="password"
            show-password
          />
        </el-form-item>
        <el-form-item label="确认密码">
          <el-input
            v-model="changePasswordForm.confirmPassword"
            type="password"
            show-password
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="changePasswordDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleChangePassword">确定</el-button>
      </template>
    </el-dialog>
  </el-container>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { List, Plus, Setting, User, Lock, SwitchButton } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const activeMenu = computed(() => {
  return route.path
})

const handleMenuSelect = (index: string) => {
  router.push(index)
}

const handleCommand = async (command: string) => {
  switch (command) {
    case 'profile':
      ElMessage.info('个人信息功能开发中')
      break
    case 'changePassword':
      showChangePasswordDialog()
      break
    case 'logout':
      authStore.logout()
      break
  }
}

// 修改密码对话框
const changePasswordDialogVisible = ref(false)
const changePasswordForm = ref({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
})

const showChangePasswordDialog = () => {
  changePasswordForm.value = {
    oldPassword: '',
    newPassword: '',
    confirmPassword: ''
  }
  changePasswordDialogVisible.value = true
}

const handleChangePassword = async () => {
  if (!changePasswordForm.value.oldPassword) {
    ElMessage.warning('请输入旧密码')
    return
  }
  if (!changePasswordForm.value.newPassword) {
    ElMessage.warning('请输入新密码')
    return
  }
  if (changePasswordForm.value.newPassword !== changePasswordForm.value.confirmPassword) {
    ElMessage.warning('两次输入的密码不一致')
    return
  }
  
  try {
    await authStore.changePassword(
      changePasswordForm.value.oldPassword,
      changePasswordForm.value.newPassword
    )
    ElMessage.success('密码修改成功')
    changePasswordDialogVisible.value = false
  } catch (error: any) {
    ElMessage.error(error.message || '密码修改失败')
  }
}
</script>

<style scoped>
.layout-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.layout-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  padding: 0 20px;
  height: 60px !important;
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo h1 {
  font-size: 20px;
  font-weight: 600;
  color: #409eff;
  margin: 0;
}

.logo img {
  height: 40px;
  width: auto;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
}

.header-menu {
  border: none;
  background: transparent;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 16px;
  cursor: pointer;
  border-radius: 4px;
  transition: background-color 0.3s;
}

.user-info:hover {
  background-color: #f5f7fa;
}

.username {
  font-size: 14px;
  color: #606266;
}

.layout-main {
  flex: 1;
  padding: 20px;
  overflow: auto;
  background: #f5f7fa;
}

.layout-footer {
  height: 60px !important;
  background: #fff;
  border-top: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  padding: 0 20px;
}

.footer-content {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: #909399;
  font-size: 14px;
}

.footer-links {
  display: flex;
  gap: 20px;
}

.footer-links a {
  color: #409eff;
  text-decoration: none;
}

.footer-links a:hover {
  text-decoration: underline;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>

