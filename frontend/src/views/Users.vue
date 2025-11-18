<template>
  <div class="users-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>用户管理</span>
          <el-button type="primary" @click="showAddUserDialog">
            <el-icon><Plus /></el-icon>
            添加用户
          </el-button>
        </div>
      </template>
      
      <el-table :data="users" style="width: 100%">
        <el-table-column prop="username" label="用户名" width="150" />
        <el-table-column prop="email" label="邮箱" width="200" />
        <el-table-column label="角色" width="100">
          <template #default="{ row }">
            <el-tag :type="row.role === 'admin' ? 'danger' : 'success'">
              {{ row.role === 'admin' ? '管理员' : '审核员' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'">
              {{ row.is_active ? '激活' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="last_login" label="最后登录" width="180">
          <template #default="{ row }">
            {{ formatDate(row.last_login) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" fixed="right" width="200">
          <template #default="{ row }">
            <el-button
              size="small"
              @click="handleEdit(row)"
            >
              编辑
            </el-button>
            <el-button
              size="small"
              type="danger"
              @click="handleDelete(row)"
              :disabled="row.username === authStore.user?.username"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    
    <!-- 添加/编辑用户对话框 -->
    <el-dialog
      v-model="userDialogVisible"
      :title="isEdit ? '编辑用户' : '添加用户'"
      width="500px"
    >
      <el-form :model="userForm" label-width="80px">
        <el-form-item label="用户名">
          <el-input
            v-model="userForm.username"
            :disabled="isEdit"
            placeholder="请输入用户名"
          />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input
            v-model="userForm.email"
            placeholder="请输入邮箱"
          />
        </el-form-item>
        <el-form-item v-if="!isEdit" label="密码">
          <el-input
            v-model="userForm.password"
            type="password"
            show-password
            placeholder="请输入密码"
          />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="userForm.role" placeholder="请选择角色">
            <el-option label="管理员" value="admin" />
            <el-option label="审核员" value="reviewer" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="isEdit" label="状态">
          <el-switch
            v-model="userForm.is_active"
            active-text="激活"
            inactive-text="禁用"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="userDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import api from '@/api'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

interface User {
  user_id: string
  username: string
  email?: string
  role: 'admin' | 'reviewer'
  is_active: boolean
  created_at?: string
  last_login?: string
}

const users = ref<User[]>([])
const userDialogVisible = ref(false)
const isEdit = ref(false)
const userForm = ref({
  username: '',
  email: '',
  password: '',
  role: 'reviewer' as 'admin' | 'reviewer',
  is_active: true
})

const loadUsers = async () => {
  try {
    const response = await api.auth.getUsers()
    if (response.success) {
      users.value = response.data
    }
  } catch (error) {
    ElMessage.error('加载用户列表失败')
  }
}

const showAddUserDialog = () => {
  isEdit.value = false
  userForm.value = {
    username: '',
    email: '',
    password: '',
    role: 'reviewer',
    is_active: true
  }
  userDialogVisible.value = true
}

const handleEdit = (user: User) => {
  isEdit.value = true
  userForm.value = {
    username: user.username,
    email: user.email || '',
    password: '',
    role: user.role,
    is_active: user.is_active
  }
  userDialogVisible.value = true
}

const handleSave = async () => {
  if (!userForm.value.username) {
    ElMessage.warning('请输入用户名')
    return
  }
  
  if (!isEdit.value && !userForm.value.password) {
    ElMessage.warning('请输入密码')
    return
  }
  
  try {
    if (isEdit.value) {
      // 更新用户
      const updateData: any = {
        email: userForm.value.email,
        role: userForm.value.role,
        is_active: userForm.value.is_active
      }
      const response = await api.auth.updateUser(userForm.value.username, updateData)
      if (response.success) {
        ElMessage.success('用户更新成功')
        userDialogVisible.value = false
        loadUsers()
      }
    } else {
      // 添加用户
      const response = await api.auth.register({
        username: userForm.value.username,
        password: userForm.value.password,
        email: userForm.value.email,
        role: userForm.value.role
      })
      if (response.success) {
        ElMessage.success('用户添加成功')
        userDialogVisible.value = false
        loadUsers()
      }
    }
  } catch (error: any) {
    ElMessage.error(error.message || '操作失败')
  }
}

const handleDelete = async (user: User) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除用户 "${user.username}" 吗？`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    const response = await api.auth.deleteUser(user.username)
    if (response.success) {
      ElMessage.success('用户删除成功')
      loadUsers()
    }
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '删除失败')
    }
  }
}

const formatDate = (dateStr?: string) => {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}

onMounted(() => {
  loadUsers()
})
</script>

<style scoped>
.users-container {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>

