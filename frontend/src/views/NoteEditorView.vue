<!-- 笔记编辑器页面 - 左侧视频，右侧AI生成笔记 -->
<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { BACKEND } from '@/composables/ConfigAPI'
import { getVideoInfo } from '@/composables/GetVideoInfo'
import { hhmmssToSeconds, secondsToHHMMSS } from '@/composables/TimeFunc'
import { getCSRFToken } from '@/composables/GetCSRFToken'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useI18n } from 'vue-i18n'
import VideoPlayer from '@/components/WatchVideo/VideoPlayer.vue'
import MindmapEditor from '@/components/WatchVideo/MindmapEditor.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

// 路由参数
const routeParams = route.params
const basenameRaw = (routeParams.basename || routeParams['basename.']) as string
const ext = routeParams.ext as string
const basename = basenameRaw?.replace(/\.$/, '') || ''
const fileName = ref(`${basename}.${ext?.toLowerCase() || ''}`)

// 视频信息
interface VideoInfoData {
  id: number
  name: string
  url: string
  description: string
  thumbnailUrl: string
  videoLength: string
  lastModified: string
  rawLang?: string
}

const defaultVideoInfo: VideoInfoData = {
  id: -1,
  name: '未命名视频',
  url: '',
  description: '',
  thumbnailUrl: '',
  videoLength: '00:00',
  lastModified: '',
}

const videoData = ref<VideoInfoData>(defaultVideoInfo)
const videoSrc = computed(() => `${BACKEND}/media/video/${fileName.value}`)
const playerRef = ref<InstanceType<typeof VideoPlayer> | null>(null)
const currentTime = ref(0)
const duration = ref(0)

// Tab管理
const activeTab = ref<'notes' | 'mindmap'>('notes')

// 笔记生成状态
const isGenerating = ref(false)
const generationProgress = ref('')
const notes = ref<Array<{
  id: string
  timestamp: string
  seconds: number
  title: string
  content: string
  imagePath: string | null
  isEdited: boolean
  renderedContent?: string
}>>([])

// 简单的Markdown转HTML（同步版本，用于模板显示）
function simpleMarkdownToHtml(md: string): string {
  if (!md) return ''
  return md
    .replace(/^### (.*)$/gm, '<h3>$1</h3>')
    .replace(/^## (.*)$/gm, '<h2>$1</h2>')
    .replace(/^# (.*)$/gm, '<h1>$1</h1>')
    .replace(/\*\*(.*)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*)\*/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/!\[([^\]]*)\]\(([^)]+)\)/g, '<img src="$2" alt="$1" class="rounded-lg max-w-full my-2" />')
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" class="text-blue-500 hover:underline">$1</a>')
    .replace(/\n\n/g, '</p><p>')
    .replace(/\n/g, '<br />')
    .replace(/^(.+)$/gm, '<p>$1</p>')
    .replace(/<p><\/p>/g, '')
}

// 编辑模式
const editingNoteId = ref<string | null>(null)
const editingContent = ref('')
const editingTitle = ref('')

// 笔记生成风格配置
const noteStyle = ref('professional')

// 从 localStorage 加载上次选择的风格
onMounted(() => {
  const savedStyle = localStorage.getItem('vidgo_note_style')
  if (savedStyle) {
    noteStyle.value = savedStyle
  }
})

// 处理时间更新
function handleTimeUpdate(t: number) {
  currentTime.value = t
}

// 跳转到指定时间
function seekTo(seconds: number) {
  currentTime.value = seconds
  playerRef.value?.seek(seconds)
}

// 加载视频数据
async function loadVideoData(filename: string) {
  try {
    const data = await getVideoInfo(filename)
    videoData.value = {
      ...data,
      description: data.description || '',
    }
    duration.value = hhmmssToSeconds(videoData.value.videoLength)
    document.title = `${videoData.value.name || filename} - 笔记编辑器`
  } catch (error) {
    console.error('Failed to load video info:', error)
    videoData.value = { ...defaultVideoInfo }
  }
}

// 生成AI笔记
async function generateNotes() {
  if (videoData.value.id <= 0) {
    ElMessage.error('请等待视频信息加载完成')
    return
  }

  // 保存风格选择
  localStorage.setItem('vidgo_note_style', noteStyle.value)

  isGenerating.value = true
  generationProgress.value = '正在分析字幕内容...'

  try {
    const csrf = await getCSRFToken()
    const response = await fetch(`${BACKEND}/api/notes/generate/${videoData.value.id}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrf,
      },
      body: JSON.stringify({
        style: noteStyle.value,
      }),
    })

    const result = await response.json()

    if (result.success) {
      notes.value = result.data
      ElMessage.success(result.message || '笔记生成成功')
    } else {
      ElMessage.error(result.error || '笔记生成失败')
    }
  } catch (error: any) {
    console.error('Note generation error:', error)
    ElMessage.error(error.message || '笔记生成失败')
  } finally {
    isGenerating.value = false
    generationProgress.value = ''
  }
}

// 开始编辑笔记
function startEditNote(note: typeof notes.value[0]) {
  editingNoteId.value = note.id
  editingTitle.value = note.title
  editingContent.value = note.content
}

// 保存笔记编辑
function saveEditNote() {
  if (!editingNoteId.value) return

  const noteIndex = notes.value.findIndex(n => n.id === editingNoteId.value)
  if (noteIndex !== -1) {
    const note = notes.value[noteIndex]
    if (note) {
      note.title = editingTitle.value
      note.content = editingContent.value
      note.isEdited = true
    }
  }

  editingNoteId.value = null
  editingTitle.value = ''
  editingContent.value = ''
  ElMessage.success('已保存修改')
}

// 取消编辑
function cancelEditNote() {
  editingNoteId.value = null
  editingTitle.value = ''
  editingContent.value = ''
}

// 删除笔记
function deleteNote(noteId: string) {
  ElMessageBox.confirm('确定要删除这条笔记吗？', '确认删除', {
    confirmButtonText: '删除',
    cancelButtonText: '取消',
    type: 'warning',
  }).then(() => {
    notes.value = notes.value.filter(n => n.id !== noteId)
    ElMessage.success('已删除')
  }).catch(() => {})
}

// 导出笔记为Markdown
function exportMarkdown() {
  if (notes.value.length === 0) {
    ElMessage.warning('没有可导出的笔记')
    return
  }

  let markdown = `# ${videoData.value.name || fileName.value}\n\n`
  markdown += `> 生成时间：${new Date().toLocaleString()}\n\n---\n\n`

  for (const note of notes.value) {
    markdown += `## ${note.title}\n\n`
    markdown += `*时间点：${note.timestamp}*\n\n`
    
    if (note.imagePath) {
      markdown += `![${note.timestamp}](${BACKEND}${note.imagePath})\n\n`
    }
    
    markdown += `${note.content}\n\n---\n\n`
  }

  // 下载文件
  const blob = new Blob([markdown], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${videoData.value.name || fileName.value}_notes.md`
  a.click()
  URL.revokeObjectURL(url)
  
  ElMessage.success('笔记已导出')
}

// 思维导图内容
const mindmapContent = ref<any>(null)

// 加载思维导图
async function loadMindmap() {
  if (videoData.value.id <= 0) return

  try {
    const res = await fetch(`${BACKEND}/api/mindmap/get/${videoData.value.id}`)
    if (res.ok) {
      const data = await res.json()
      if (data.success) {
        mindmapContent.value = data.mindmap_content || null
      }
    }
  } catch (err) {
    console.error('Error loading mindmap:', err)
  }
}

// 保存思维导图
async function handleMindmapSave(content: any) {
  mindmapContent.value = content

  try {
    const csrf = await getCSRFToken()
    const res = await fetch(`${BACKEND}/api/mindmap/update/${videoData.value.id}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrf,
      },
      body: JSON.stringify({ mindmap_content: content }),
    })

    if (res.ok) {
      ElMessage.success('思维导图已保存')
    } else {
      const data = await res.json()
      ElMessage.error('保存失败: ' + (data.error || 'Unknown error'))
    }
  } catch (err) {
    console.error('Error saving mindmap:', err)
    ElMessage.error('保存时发生错误')
  }
}

// 处理思维导图内容变化
function handleMindmapContentChange(content: any) {
  if (JSON.stringify(mindmapContent.value) !== JSON.stringify(content)) {
    mindmapContent.value = content
  }
}

// 返回首页
function goBack() {
  router.push('/')
}

// 返回视频页面
function goToWatch() {
  router.push(`/watch/${fileName.value}`)
}

onMounted(async () => {
  await loadVideoData(fileName.value)
  await loadMindmap()
})

// 监听路由变化
watch(
  () => route.params,
  async (newParams, oldParams) => {
    const getFileName = (params: any) => {
      if (!params) return ''
      const basename = ((params.basename || params['basename.']) as string)?.replace(/\.$/, '') || ''
      const ext = (params.ext as string)?.toLowerCase() || ''
      return `${basename}.${ext}`
    }

    const newFileName = getFileName(newParams)
    const oldFileName = getFileName(oldParams)

    if (newFileName !== oldFileName && newFileName !== '.') {
      fileName.value = newFileName
      notes.value = []
      await loadVideoData(newFileName)
      await loadMindmap()
    }
  },
  { immediate: false }
)
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
    <!-- 顶部导航栏 -->
    <header class="bg-white/80 backdrop-blur-lg border-b border-slate-200 sticky top-0 z-50">
      <div class="flex items-center justify-between px-6 py-3">
        <!-- 左侧：返回按钮和标题 -->
        <div class="flex items-center space-x-4">
          <button
            @click="goBack"
            class="p-2 rounded-xl hover:bg-slate-100 transition-colors"
          >
            <svg class="w-5 h-5 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
          </button>
          <div>
            <h1 class="text-lg font-bold text-slate-800">{{ videoData.name || fileName }}</h1>
            <p class="text-sm text-slate-500">笔记编辑器</p>
          </div>
        </div>

        <!-- 右侧：操作按钮 -->
        <div class="flex items-center space-x-3">
          <button
            @click="goToWatch"
            class="px-4 py-2 text-sm font-medium text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-xl transition-colors"
          >
            返回视频
          </button>
          <button
            @click="exportMarkdown"
            :disabled="notes.length === 0"
            class="px-4 py-2 text-sm font-medium text-white bg-emerald-500 hover:bg-emerald-600 disabled:opacity-50 disabled:cursor-not-allowed rounded-xl transition-colors"
          >
            📤 导出笔记
          </button>
        </div>
      </div>
    </header>

    <!-- 主内容区域 -->
    <div class="flex h-[calc(100vh-65px)]">
      <!-- 左侧：视频播放器 (40%) -->
      <div class="w-2/5 p-4 border-r border-slate-200 flex flex-col">
        <div class="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden flex-shrink-0">
          <div class="aspect-video">
            <VideoPlayer
              ref="playerRef"
              :src="videoSrc"
              :blobUrls="[]"
              :videoId="videoData.id"
              @time-update="handleTimeUpdate"
              class="w-full h-full"
            />
          </div>
        </div>

        <!-- 视频信息 -->
        <div class="mt-4 bg-white rounded-2xl shadow-sm border border-slate-200 p-4 flex-shrink-0">
          <div class="flex items-center justify-between mb-2">
            <span class="text-sm text-slate-500">当前时间</span>
            <span class="text-sm font-mono text-blue-600">{{ secondsToHHMMSS(currentTime) }}</span>
          </div>
          <div class="flex items-center justify-between">
            <span class="text-sm text-slate-500">视频时长</span>
            <span class="text-sm font-mono text-slate-700">{{ videoData.videoLength }}</span>
          </div>
        </div>

        <!-- 风格选择 -->
        <div class="mt-4 bg-white rounded-2xl shadow-sm border border-slate-200 p-4 flex-shrink-0">
          <label class="block text-sm font-medium text-slate-700 mb-2">📝 笔记生成风格</label>
          <select
            v-model="noteStyle"
            class="w-full px-4 py-3 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 bg-slate-50 text-slate-700"
          >
            <option value="professional">📋 专业文档 - 严谨精炼</option>
            <option value="blog">✍️ 博客风格 - 轻松易读</option>
            <option value="tutorial">📚 教程风格 - 循序渐进</option>
          </select>
        </div>

        <!-- 生成按钮 -->
        <div class="mt-4 flex-shrink-0">
          <button
            @click="generateNotes"
            :disabled="isGenerating || videoData.id <= 0"
            class="w-full py-4 text-lg font-medium text-white bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600 disabled:opacity-50 disabled:cursor-not-allowed rounded-2xl transition-all duration-300 shadow-lg hover:shadow-xl flex items-center justify-center space-x-2"
          >
            <span v-if="isGenerating" class="flex items-center">
              <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              {{ generationProgress || '生成中...' }}
            </span>
            <span v-else>🤖 AI生成笔记</span>
          </button>
        </div>

        <!-- 快速操作提示 -->
        <div class="mt-4 bg-gradient-to-r from-blue-50 to-purple-50 rounded-2xl p-4 border border-blue-100">
          <h4 class="text-sm font-medium text-blue-800 mb-2">💡 使用提示</h4>
          <ul class="text-xs text-blue-600 space-y-1">
            <li>• 点击笔记中的时间戳可跳转视频</li>
            <li>• 支持编辑生成的笔记内容</li>
            <li>• 可导出为Markdown格式</li>
          </ul>
        </div>
      </div>

      <!-- 右侧：笔记编辑区域 (60%) -->
      <div class="w-3/5 flex flex-col">
        <!-- Tab切换 -->
        <div class="bg-white border-b border-slate-200 px-4 py-2 flex-shrink-0">
          <nav class="flex space-x-2">
            <button
              @click="activeTab = 'notes'"
              :class="[
                'flex-1 px-6 py-3 text-sm font-medium rounded-xl transition-all duration-300',
                activeTab === 'notes'
                  ? 'text-white bg-blue-500 shadow-lg'
                  : 'text-slate-600 hover:text-blue-600 hover:bg-slate-100',
              ]"
            >
              📝 笔记
            </button>
            <button
              @click="activeTab = 'mindmap'"
              :class="[
                'flex-1 px-6 py-3 text-sm font-medium rounded-xl transition-all duration-300',
                activeTab === 'mindmap'
                  ? 'text-white bg-blue-500 shadow-lg'
                  : 'text-slate-600 hover:text-blue-600 hover:bg-slate-100',
              ]"
            >
              🧠 思维导图
            </button>
          </nav>
        </div>

        <!-- 内容区域 -->
        <div class="flex-1 overflow-y-auto p-4">
          <!-- 笔记Tab -->
          <div v-show="activeTab === 'notes'">
            <!-- 空状态 -->
            <div v-if="notes.length === 0 && !isGenerating" class="flex flex-col items-center justify-center h-full text-center py-16">
              <div class="w-24 h-24 bg-gradient-to-br from-blue-100 to-purple-100 rounded-full flex items-center justify-center mb-6">
                <span class="text-4xl">📝</span>
              </div>
              <h3 class="text-xl font-bold text-slate-800 mb-2">还没有笔记</h3>
              <p class="text-slate-500 mb-6">点击左侧"AI生成笔记"按钮开始</p>
              <button
                @click="generateNotes"
                :disabled="videoData.id <= 0"
                class="px-8 py-3 text-white bg-gradient-to-r from-blue-500 to-purple-500 rounded-xl font-medium hover:shadow-lg transition-all"
              >
                🤖 开始生成
              </button>
            </div>

            <!-- 笔记列表 -->
            <div v-else class="space-y-4">
              <div
                v-for="note in notes"
                :key="note.id"
                class="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden hover:shadow-md transition-shadow"
              >
                <!-- 笔记头部 -->
                <div class="flex items-center justify-between p-4 bg-gradient-to-r from-slate-50 to-blue-50 border-b border-slate-100">
                  <div class="flex items-center space-x-3">
                    <button
                      @click="seekTo(note.seconds)"
                      class="px-3 py-1 text-sm font-mono text-blue-600 bg-blue-100 hover:bg-blue-200 rounded-lg transition-colors"
                    >
                      {{ note.timestamp }}
                    </button>
                    <h3 v-if="editingNoteId !== note.id" class="font-semibold text-slate-800">
                      {{ note.title }}
                    </h3>
                    <input
                      v-else
                      v-model="editingTitle"
                      class="flex-1 px-3 py-1 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="章节标题"
                    />
                  </div>
                  
                  <div class="flex items-center space-x-2">
                    <span v-if="note.isEdited" class="text-xs text-amber-500 bg-amber-50 px-2 py-1 rounded-lg">
                      已编辑
                    </span>
                    <button
                      v-if="editingNoteId !== note.id"
                      @click="startEditNote(note)"
                      class="p-2 text-slate-400 hover:text-blue-500 hover:bg-blue-50 rounded-lg transition-colors"
                    >
                      ✏️
                    </button>
                    <template v-else>
                      <button
                        @click="saveEditNote"
                        class="px-3 py-1 text-sm text-white bg-blue-500 hover:bg-blue-600 rounded-lg transition-colors"
                      >
                        保存
                      </button>
                      <button
                        @click="cancelEditNote"
                        class="px-3 py-1 text-sm text-slate-500 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
                      >
                        取消
                      </button>
                    </template>
                    <button
                      @click="deleteNote(note.id)"
                      class="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                    >
                      🗑️
                    </button>
                  </div>
                </div>

                <!-- 笔记内容 -->
                <div class="p-4">
                  <!-- 截图 -->
                  <div v-if="note.imagePath" class="mb-4">
                    <img
                      :src="`${BACKEND}${note.imagePath}`"
                      :alt="note.timestamp"
                      class="w-full max-h-64 object-contain rounded-xl border border-slate-200 cursor-pointer hover:shadow-lg transition-shadow"
                      @click="seekTo(note.seconds)"
                    />
                  </div>

                  <!-- 内容文本 -->
                  <div v-if="editingNoteId !== note.id" class="prose prose-sm max-w-none text-slate-700">
                    <div v-html="simpleMarkdownToHtml(note.content)"></div>
                  </div>
                  <textarea
                    v-else
                    v-model="editingContent"
                    rows="8"
                    class="w-full p-3 border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y"
                    placeholder="笔记内容（支持Markdown）"
                  ></textarea>
                </div>
              </div>
            </div>
          </div>

          <!-- 思维导图Tab -->
          <div v-show="activeTab === 'mindmap'" class="bg-white rounded-2xl shadow-sm border border-slate-200 min-h-[500px]">
            <MindmapEditor
              :initialContent="mindmapContent"
              @contentChange="handleMindmapContentChange"
              @save="handleMindmapSave"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 滚动条样式 */
.overflow-y-auto::-webkit-scrollbar {
  width: 6px;
}

.overflow-y-auto::-webkit-scrollbar-track {
  background: transparent;
}

.overflow-y-auto::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
}

.overflow-y-auto::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}

/* Prose样式覆盖 */
.prose img {
  border-radius: 0.75rem;
  margin: 1rem 0;
}

.prose p {
  margin-bottom: 0.75rem;
}
</style>
