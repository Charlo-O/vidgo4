<!-- 视频信息组件 -->
<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { markdownToHtml } from '@/composables/ConvertMarkdown'
import { getCSRFToken } from '@/composables/GetCSRFToken'
import NotesPanel from './NotesPanel.vue'
import MindmapEditor from './MindmapEditor.vue'
import { useI18n } from 'vue-i18n'

const router = useRouter()

// i18n functionality
const { t } = useI18n()

const props = withDefaults(
  defineProps<{
    filename: string
    title: string
    description: string
    id: number
  }>(),
  {
    description: '',
  },
)

// Tab management
const activeTab = ref('notes')

// Mindmap content management
const mindmapContent = ref<any>(null)
import { BACKEND } from '@/composables/ConfigAPI'
// Load mindmap content on component mount
const loadMindmapContent = async () => {
  // Don't load if we don't have a valid video ID
  if (!props.id || props.id <= 0) {
    console.log('Skipping mindmap load - invalid video ID:', props.id)
    return
  }

  try {
    console.log('Loading mindmap for video ID:', props.id)
    const res = await fetch(`${BACKEND}/api/mindmap/get/${props.id}`)

    if (res.ok) {
      const data = await res.json()
      console.log('Mindmap API response:', data)
      if (data.success) {
        mindmapContent.value = data.mindmap_content || null
        console.log('Set mindmapContent.value to:', mindmapContent.value)
      } else {
        console.log('API returned success: false')
        mindmapContent.value = null
      }
    } else {
      console.log('API request failed with status:', res.status)
      mindmapContent.value = null
    }
  } catch (err) {
    console.error('Error loading mindmap:', err)
    mindmapContent.value = null
  }
}

// 处理思维导图内容变化（实时更新，不保存）
const handleMindmapContentChange = (content: any) => {
  // Only update if the content has actually changed to avoid infinite loops
  if (JSON.stringify(mindmapContent.value) !== JSON.stringify(content)) {
    console.log('VideoInfo: Mindmap content changed, updating')
    mindmapContent.value = content
  }
}

// 处理思维导图保存（用户点击保存按钮时）
const handleMindmapSave = async (content: any) => {
  mindmapContent.value = content

  try {
    const csrf = await getCSRFToken()
    const res = await fetch(`${BACKEND}/api/mindmap/update/${props.id}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrf,
      },
      body: JSON.stringify({ mindmap_content: content }),
    })

    if (!res.ok) {
      const data = await res.json()
      console.warn('Failed to save mindmap content:', data.error || 'Unknown error')
      // 可以添加用户提示
      alert('保存失败: ' + (data.error || 'Unknown error'))
    } else {
      const data = await res.json()
      console.log('Mindmap saved successfully:', data.message)
      // 可以添加成功提示
      alert(t('mindmapSaved'))
    }
  } catch (err) {
    console.error('Error saving mindmap:', err)
    alert('保存时发生错误，请重试')
  }
}

const emit = defineEmits<{
  (e: 'update:description', value: string): void
}>()

// tool function for communication with backend
async function updateDescription(videoId: number, description: string) {
  try {
    const csrf = await getCSRFToken()
    const res = await fetch(`${BACKEND}/video/rename_description/${props.id}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrf,
      },
      body: JSON.stringify({ video_id: videoId, description: description }),
    })

    if (!res.ok) {
      throw new Error((await res.text()) || 'Request failed')
    }
    return await res.json()
  } catch (err) {
    console.error(err)
  }
}

// Status interaction for frontend
const isEditing = ref(false)
const draftDesc = ref(props.description)
function startEdit() {
  draftDesc.value = props.description
  isEditing.value = true
}

async function save() {
  const newDesc = draftDesc.value.trim() // trimming  extra space

  isEditing.value = false
  if (!newDesc || newDesc === props.description) return

  try {
    await updateDescription(props.id, newDesc)
    emit('update:description', newDesc) // ← now recognised
  } catch (err) {
    console.error(err)
    draftDesc.value = props.description // rollback on failure
  }
}

const renderedDescription = computed(() =>
  markdownToHtml(isEditing.value ? draftDesc.value : props.description),
)

// Load mindmap content when component mounts
onMounted(() => {
  loadMindmapContent()
})

// Watch for video ID changes and load mindmap when we get a valid ID
watch(
  () => props.id,
  (newId: number, oldId: number) => {
    console.log('VideoInfo: Video ID changed from', oldId, 'to', newId)
    if (newId && newId > 0 && newId !== oldId) {
      loadMindmapContent()
    }
  },
)
</script>

<template>
  <div class="bg-white/50 rounded-2xl border border-slate-200">
    <!-- Tab Header -->
    <div class="border-b border-slate-200 p-2">
      <nav class="flex space-x-2 px-2">
        <button
          @click="activeTab = 'notes'"
          :class="[
            'flex-1 px-6 py-3 text-sm font-medium rounded-xl transition-all duration-300',
            activeTab === 'notes'
              ? 'text-white bg-blue-500 shadow-lg'
              : 'text-slate-600 hover:text-blue-600 hover:bg-slate-100',
          ]"
        >
          {{ t('notes') }}
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
          {{ t('mindmap') }}
        </button>
        <!-- AI笔记编辑器入口 -->
        <button
          @click="router.push(`/notes/${props.filename}`)"
          class="px-4 py-3 text-sm font-medium text-white bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 rounded-xl transition-all duration-300 shadow-lg hover:shadow-xl flex items-center space-x-1"
        >
          <span>🤖</span>
          <span>AI笔记</span>
        </button>
      </nav>
    </div>

    <!-- Tab Content -->
    <div class="p-0">
      <!-- Notes Tab - Use NotesPanel Component -->
      <div v-show="activeTab === 'notes'">
        <NotesPanel :videoId="props.id" />
      </div>

      <!-- Mindmap Tab -->
      <div v-show="activeTab === 'mindmap'" class="p-6">
        <MindmapEditor
          :initialContent="mindmapContent"
          @contentChange="handleMindmapContentChange"
          @save="handleMindmapSave"
        />
      </div>
    </div>
  </div>
</template>
