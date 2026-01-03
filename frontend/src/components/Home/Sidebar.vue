<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { defineProps, defineEmits, ref, onMounted, watch } from 'vue'

// i18n functionality
const { t } = useI18n()
import {
  LibraryBig,
  Search as LucideSearch,
  History,
  Home,
  Video,
  Settings,
  Plus,
  FolderOpen,
  RefreshCw,
  MoreHorizontal,
  User,
  UserPlus,
  LogOut,
  ChevronUp,
} from 'lucide-vue-next'
import { ElMessage, ElMessageBox, ElTooltip } from 'element-plus'
import type { Category } from '@/types/media'
import { getCSRFToken } from '@/composables/GetCSRFToken'
import UsersDialog from '@/components/dialogs/UsersDialog.vue'
/*
说明：Home.vue中的侧边栏页面 (Sidebar)
◇ 布局结构
- 1.上方实现MenuItem，点击时切换Main page的内容（向父组件Home.vue发送切换的信号）
- 2.中间实现Folder的CRUD命令（增删改查）
- 3.下方展示Logo，名称(VidGo)，版本号，以及右侧切换Sidebar展开/收起状态的Icon，以FlexBox形式排版。
- 4.当Sidebar收起时，只展示 展开Sidebar的Icon，Home Icon，搜索Icon
*/

/** 工具函数：统一 POST, 自动解析 / 提示，返回 data 或 null */
async function request_post<T>(
  url: string,
  payload: unknown,
  successMsg = '操作成功',
): Promise<T | null> {
  try {
    // Get CSRF token
    const csrfToken = await getCSRFToken()

    const resp = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken,
      },
      credentials: 'include',
      body: JSON.stringify(payload),
    })
    const data = await resp.json()

    if (!resp.ok || data?.success === false) throw new Error(data?.error || resp.statusText)

    ElMessage.success(data?.message || t(successMsg) || successMsg)
    return data as T
  } catch (e: any) {
    console.error(e)
    ElMessage.error(e.message || t('networkError'))
    return null
  }
}

// 1.更新MenuItem
const menuList = [
  { key: 'home', icon: Home, action: () => emit('updateMenuIndex', 0) },
  { key: 'library', icon: Video, action: () => emit('updateMenuIndex', 1) },
  { key: 'history', icon: History, action: () => emit('updateMenuIndex', 2) },
  { key: 'settings', icon: Settings, action: openSettings },
  { key: 'search', icon: LucideSearch, action: openSearch, tooltip: 'Ctrl+K' },
]

const selectedCategoryId = ref(-1)

function openSearch() {
  emit('open-search')
}

function openSettings() {
  emit('open-settings')
}
import { BACKEND } from '@/composables/ConfigAPI'

/* 2.创建分类 */
async function createCategory() {
  const { value } = await ElMessageBox.prompt('请输入新建分类名称', '新建分类', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    inputPattern: /\S+/,
    inputErrorMessage: '文件夹名称不能为空',
  }).catch(() => ({ value: '' }) as any)

  if (!value) return

  const res = await request_post(
    `${BACKEND}/api/category/add/0`,
    { categoryName: value },
    '文件夹创建成功',
  )

  if (res) emit('refresh') // ✅ 通知父组件重新 fetch
}

// 3.创建合集
async function createCollection() {
  // First get the currently selected category
  const categoryId = selectedCategoryId.value === -1 ? 0 : selectedCategoryId.value

  const { value } = await ElMessageBox.prompt('请输入新建合集名称', '新建合集', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    inputPattern: /\S+/,
    inputErrorMessage: '合集名称不能为空',
  }).catch(() => ({ value: '' }) as any)

  if (!value) return

  const res = await request_post(
    `${BACKEND}/api/collection/create/0`,
    { name: value, category_id: categoryId },
    '合集创建成功',
  )

  if (res) emit('refresh') // ✅ 通知父组件重新 fetch
}

//选中分类
function selectCategory(id: number) {
  selectedCategoryId.value = id
  emit('select-category', id)
}

// 重命名分类
const editingCategoryId = ref<number | null>(null)
const originalName = ref('')
const draftName = ref('')
function startEdit(category: Category) {
  editingCategoryId.value = category.id
  originalName.value = category.name
  draftName.value = category.name
}

async function finishEdit(category: Category) {
  const name = draftName.value.trim()
  if (!name || name === category.name) {
    editingCategoryId.value = null
    return
  }

  const ok = await request_post(
    `${BACKEND}/api/category/rename/0`,
    { oldName: category.name, newName: name },
    '重命名成功',
  )

  editingCategoryId.value = null
  ok && emit('refresh')
}

// 删除文件夹
async function handleCategoryCommand(cmd: string, category: Category) {
  if (cmd === 'rename') return startEdit(category)
  /* delete */ else if (cmd === 'delete') {
    const ok = await ElMessageBox.confirm(
      `其中的视频将归入“无分类”，确定删除 "${category.name}" 吗？`,
      '警告',
    ).catch(() => false)
    if (!ok) return

    const res = await request_post(
      `${BACKEND}/api/category/delete/0`,
      { categoryName: category.name },
      '删除成功',
    )
    res && emit('refresh')
  }
  // 添加合集
  else if (cmd === 'create-collection') {
    // Set the selected category to this category before creating collection
    selectCategory(category.id)
    createCollection()
  }
}

// 折叠侧边栏
const collapsed = ref(false)
const toggleCollapse = () => (collapsed.value = !collapsed.value)

// User management
interface User {
  id: number
  username: string
  email: string
  is_root: boolean
  premium_authority: boolean
  is_active: boolean
}

const currentUser = ref<User | null>(null)
const showUserDropdown = ref(false)
const showUsersDialog = ref(false)

// Check if user is logged in on mount
const checkUserStatus = async () => {
  try {
    const response = await fetch(`${BACKEND}/api/auth/profile/`, {
      credentials: 'include',
    })

    if (response.ok) {
      const data = await response.json()
      if (data.success) {
        console.log('User data received:', data.user) // Debug log
        currentUser.value = data.user
      }
    }
  } catch (error) {
    console.error('Error checking user status:', error)
  }
}

// Logout function
const handleLogout = async () => {
  try {
    const response = await fetch(`${BACKEND}/api/auth/logout/`, {
      method: 'POST',
      credentials: 'include',
    })

    if (response.ok) {
      currentUser.value = null
      showUserDropdown.value = false
      ElMessage.success('已退出登录')
    }
  } catch (error) {
    console.error('Logout error:', error)
    ElMessage.error('退出登录失败')
  }
}

// Handle user area click
const handleUserAreaClick = async () => {
  if (currentUser.value) {
    showUserDropdown.value = !showUserDropdown.value
  } else {
    // Emit event to parent (Home.vue) to handle login dialog
    emit('show-login')
  }
}

// Handle user management click
const handleUserManagementClick = () => {
  showUsersDialog.value = true
  showUserDropdown.value = false
}

// Initialize user status check
onMounted(() => {
  checkUserStatus()
})

// Watch for authentication changes and emit refresh
watch(currentUser, (newUser, oldUser) => {
  // If user logs in (from null to user), emit refresh
  if (!oldUser && newUser) {
    emit('refresh')
  }
  // If user logs out (from user to null), emit refresh
  else if (oldUser && !newUser) {
    emit('refresh')
  }
})

// 从上级继承属性
const props = defineProps<{
  currentMenuIdx: number
  categories: Category[]
  isAuthenticated: boolean
}>()

// 向上级发送信号
const emit = defineEmits<{
  (e: 'update-menuIndex', idx: number): void
  (e: 'updateMenuIndex', idx: number): void
  (e: 'open-search'): void
  (e: 'open-settings'): void
  (e: 'select-category', id: number): void
  (e: 'refresh'): void
  (e: 'show-login'): void
}>()
</script>

<template>
  <div
    class="sidebar backdrop-blur-xl border-r flex flex-col h-full transition-all duration-300"
    :class="[
      collapsed ? 'sidebar-collapsed' : 'sidebar-expanded',
      'bg-gradient-to-b from-[#f8f9ff] via-white to-[#f1f5f9] border-slate-200/60'
    ]"
  >
    <!--缩起版 侧边栏-->
    <div v-if="collapsed" class="flex flex-col items-center py-6 space-y-6 flex-none px-2">
      <el-tooltip :content="t('displaySidebar')" placement="right">
        <button
          @click="toggleCollapse"
          class="text-slate-500 hover:text-indigo-600 p-2 rounded-xl hover:bg-indigo-50 transition-all duration-200"
        >
          <LibraryBig :size="20" />
        </button>
      </el-tooltip>
      <el-tooltip :content="t('home')" placement="right">
        <button
          @click="emit('updateMenuIndex', 0)"
          class="text-slate-500 hover:text-indigo-600 p-2 rounded-xl hover:bg-indigo-50 transition-all duration-200"
        >
          <Home :size="20" />
        </button>
      </el-tooltip>
      <el-tooltip content="Search (Ctrl+K)" placement="right">
        <button
          @click="openSearch"
          class="text-slate-500 hover:text-indigo-600 p-2 rounded-xl hover:bg-indigo-50 transition-all duration-200"
        >
          <LucideSearch :size="20" />
        </button>
      </el-tooltip>
    </div>

    <!-- 展开版 侧边栏 -->
    <template v-if="!collapsed">
      <!-- 加个空行美化排版 -->
      <div class="py-3"></div>
      <nav class="flex-1 overflow-y-auto px-3 scrollbar-premium">
        <!-- Menu items -->
        <div class="space-y-1.5 mb-6">
          <div
            v-for="(item, i) in menuList"
            :key="i"
            class="flex items-center p-3 rounded-2xl cursor-pointer border transition-all duration-200"
            :class="
              props.currentMenuIdx === i
                ? 'bg-gradient-to-r from-indigo-500 to-violet-500 text-white border-transparent shadow-lg shadow-indigo-200'
                : 'hover:bg-indigo-50 text-slate-600 hover:text-indigo-600 border-transparent hover:border-indigo-100'
            "
            @click="item.action()"
          >
            <template v-if="item.tooltip">
              <el-tooltip :content="item.tooltip" placement="right">
                <div class="flex items-center">
                  <component :is="item.icon" :size="18" />
                  <span class="ml-3 font-medium">{{ t(item.key) }}</span>
                </div>
              </el-tooltip>
            </template>
            <template v-else>
              <div class="flex items-center">
                <component :is="item.icon" :size="18" />
                <span class="ml-3 font-medium">{{ t(item.key) }}</span>
              </div>
            </template>
          </div>
        </div>

        <!-- 分类 - 只在用户登录时显示 -->
        <template v-if="currentUser">
          <h6
            class="mb-4 flex items-center justify-between text-xs font-semibold text-slate-400 tracking-wider uppercase"
          >
            <div>{{ t('categories') }} ({{ props.categories.length }})</div>
            <div class="flex items-center space-x-1">
              <el-tooltip :content="t('refreshVideoData')" placement="top">
                <button
                  @click="emit('refresh')"
                  class="text-slate-400 hover:text-indigo-600 p-1.5 rounded-lg hover:bg-indigo-50 transition-all duration-200"
                >
                  <RefreshCw :size="14" />
                </button>
              </el-tooltip>
              <el-tooltip :content="t('addCategory')" placement="top">
                <button
                  @click="createCategory"
                  class="text-slate-400 hover:text-indigo-600 p-1.5 rounded-lg hover:bg-indigo-50 transition-all duration-200"
                >
                  <Plus :size="14" />
                </button>
              </el-tooltip>
            </div>
          </h6>
          <div class="flex-1 overflow-y-auto space-y-1">
            <div
              v-for="category in props.categories"
              :key="category.id"
              class="group p-3 mb-1 rounded-2xl flex items-center cursor-pointer relative border transition-all duration-200"
              :class="
                category.id === selectedCategoryId
                  ? 'bg-indigo-50 text-indigo-700 border-indigo-200 shadow-sm'
                  : 'hover:bg-slate-50 text-slate-600 border-transparent hover:border-slate-200'
              "
              @click="selectCategory(category.id)"
            >
              <div class="w-full flex items-center justify-between">
                <div class="flex items-center flex-1">
                  <template v-if="category.id === selectedCategoryId">
                    <FolderOpen :size="16" class="mr-3" />
                  </template>
                  <template v-else>
                    <div class="w-2 h-2 rounded-full bg-gradient-to-r from-indigo-400 to-violet-400 mr-3"></div>
                  </template>
                  <template v-if="editingCategoryId !== category.id">
                    <span class="font-medium">{{ category.name }}</span>
                  </template>
                  <template v-else>
                    <input
                      v-model="draftName"
                      @keyup.enter="finishEdit(category)"
                      @blur="editingCategoryId = null"
                      @click.stop
                      class="ml-2 px-2 py-1 border border-indigo-200 rounded-lg focus:outline-none focus:border-indigo-400 bg-white text-slate-700 placeholder-slate-400"
                    />
                  </template>
                </div>

                <!-- More icon - shows on hover using CSS -->
                <el-dropdown
                  v-if="editingCategoryId !== category.id"
                  trigger="hover"
                  @command="(cmd: string) => handleCategoryCommand(cmd, category)"
                  @click.stop
                  class="more-dropdown"
                >
                  <button
                    class="text-slate-400 hover:text-indigo-600 p-1 opacity-0 group-hover:opacity-100 transition-all duration-200 rounded-lg hover:bg-indigo-50"
                  >
                    <MoreHorizontal :size="14" />
                  </button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item command="rename">{{ t('rename') }}</el-dropdown-item>
                      <el-dropdown-item command="create-collection">{{
                        t('addCollection')
                      }}</el-dropdown-item>
                      <el-dropdown-item command="delete" divided>{{
                        t('delete')
                      }}</el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </div>
            </div>
          </div>
        </template>

        <!-- 未登录状态提示 -->
        <template v-else>
          <div class="flex-1 flex items-center justify-center">
            <div class="text-center text-slate-400 p-6">
              <div class="w-16 h-16 mx-auto mb-4 rounded-2xl bg-slate-100 flex items-center justify-center">
                <User :size="32" class="text-slate-400" />
              </div>
              <p class="text-sm">{{ t('loginToViewCategories') }}</p>
            </div>
          </div>
        </template>
      </nav>

      <!-- User Status Area -->
      <div class="px-3 py-2 border-t border-slate-200/60">
        <div
          @click="handleUserAreaClick"
          @touchstart="handleUserAreaClick"
          @touchend.prevent
          class="flex items-center p-3 rounded-2xl cursor-pointer border border-transparent hover:bg-indigo-50 hover:border-indigo-100 active:bg-indigo-100 transition-all duration-200 relative"
        >
          <div
            class="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 via-violet-500 to-pink-500 flex items-center justify-center shadow-lg shadow-indigo-200"
          >
            <User :size="16" class="text-white" />
          </div>
          <div class="ml-3 flex-1">
            <div v-if="currentUser" class="text-sm font-semibold text-slate-700">
              {{ currentUser.username }}
            </div>
            <div v-else class="text-sm font-semibold text-slate-700">{{ t('notLoggedIn') }}</div>
            <div class="text-xs text-slate-400">
              {{
                currentUser
                  ? currentUser.is_root
                    ? t('administrator')
                    : t('user')
                  : t('clickToLogin')
              }}
            </div>
          </div>
          <ChevronUp
            v-if="currentUser"
            :size="16"
            class="text-slate-400 transition-transform duration-200"
            :class="{ 'rotate-180': showUserDropdown }"
          />
        </div>

        <!-- User Dropdown -->
        <div
          v-if="currentUser && showUserDropdown"
          class="mt-2 bg-white rounded-2xl border border-slate-200 shadow-glass overflow-hidden"
        >
          <div
            v-if="currentUser.is_root"
            @click="handleUserManagementClick"
            class="flex items-center px-4 py-3 hover:bg-indigo-50 cursor-pointer transition-colors"
          >
            <UserPlus :size="14" class="text-indigo-500 mr-3" />
            <span class="text-sm text-slate-700 font-medium">{{ t('userManagement') }}</span>
          </div>
          <div v-else-if="currentUser" class="flex items-center px-4 py-3 text-slate-400 text-sm">
            <span>调试: is_root = {{ currentUser.is_root }}</span>
          </div>
          <div
            @click="handleLogout"
            class="flex items-center px-4 py-3 hover:bg-red-50 cursor-pointer transition-colors border-t border-slate-100"
          >
            <LogOut :size="14" class="text-red-500 mr-3" />
            <span class="text-sm text-red-600 font-medium">{{ t('logout') }}</span>
          </div>
        </div>
      </div>

      <!-- Bottom Logo -->
      <div class="px-3 py-3 flex items-center border-t border-slate-200/60">
        <div class="h-9 w-9 rounded-xl bg-gradient-to-br from-indigo-500 via-violet-500 to-pink-500 flex items-center justify-center shadow-lg shadow-indigo-200">
          <LibraryBig :size="20" class="text-white" />
        </div>
        <div class="ml-2.5 flex flex-col">
          <span class="text-sm font-bold bg-gradient-to-r from-indigo-600 via-violet-600 to-pink-600 bg-clip-text text-transparent">VidGo</span>
          <span class="text-xs text-slate-400">v1.0</span>
        </div>
        <el-tooltip :content="t('hideSidebar')" placement="bottom">
          <button
            @click="toggleCollapse"
            class="ml-auto text-slate-400 hover:text-indigo-600 p-2 rounded-xl hover:bg-indigo-50 transition-all duration-200"
          >
            <LibraryBig :size="18" />
          </button>
        </el-tooltip>
      </div>
    </template>
  </div>

  <!-- Users Dialog Placeholder -->
  <UsersDialog
    v-if="showUsersDialog"
    v-model:visible="showUsersDialog"
    @users-updated="checkUserStatus"
  />
</template>

<style lang="postcss" scoped>
@reference "../../assets/tailwind.css";
@tailwind utilities;
.sidebar nav {
  /* Firefox */
  scrollbar-width: thin;
  scrollbar-color: #e5e7eb transparent; /* gray-200 on thumb, transparent track */
}

/* WebKit browsers */
.sidebar nav::-webkit-scrollbar {
  width: 6px;
}
.sidebar nav::-webkit-scrollbar-thumb {
  background-color: #e5e7eb; /* gray-200 */
  border-radius: 3px;
}
.sidebar nav::-webkit-scrollbar-track {
  background: transparent;
}
@layer utilities {
  .menu-item-active {
    @apply bg-primary/10 text-primary;
  }
}

/* Responsive sidebar width */
.sidebar-expanded {
  width: 28%;
}

.sidebar-collapsed {
  width: 8%;
}

/* Large screens and up (1024px+) */
@media (min-width: 1024px) {
  .sidebar-expanded {
    width: 14%;
  }

  .sidebar-collapsed {
    width: 4%;
  }
}

/* Glassy folder button effects */
.group {
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  background: rgba(255, 255, 255, 0.1);
}

.group:hover {
  transform: translateY(-1px);
  background: rgba(255, 255, 255, 0.25);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}
</style>
