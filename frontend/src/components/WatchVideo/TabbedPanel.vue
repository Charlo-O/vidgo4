<script setup lang="ts">
import { ref } from 'vue'
import SubtitlePanel from './SubtitlePanel.vue'
import VideoChapters from './VideoChapters.vue'
import { useI18n } from 'vue-i18n'

// i18n functionality
const { t } = useI18n()

const props = defineProps<{
  currentTime: number
  id: number
  rawLang?: string
  videoName?: string
}>()

const emit = defineEmits<{
  (e: 'seek', time: number): void
  (e: 'update-bloburls', blobUrls: Array<string | undefined>): void
}>()

const activeTab = ref<'subtitles' | 'chapters'>('subtitles')
// 保持字幕翻译开关状态，避免切换标签页时丢失
const showTranslation = ref(false)
</script>

<template>
  <div class="bg-white/50 rounded-2xl border border-slate-200">
    <!-- Tab Navigation -->
    <div class="flex border-b border-slate-200 p-2">
      <button
        @click="activeTab = 'subtitles'"
        class="flex-1 px-6 py-3 text-sm font-medium rounded-xl transition-all duration-300 mx-1"
        :class="
          activeTab === 'subtitles'
            ? 'text-white bg-blue-500 shadow-lg'
            : 'text-slate-600 hover:text-blue-600 hover:bg-slate-100'
        "
      >
        {{ t('subtitles') }}
      </button>
      <button
        @click="activeTab = 'chapters'"
        class="flex-1 px-6 py-3 text-sm font-medium rounded-xl transition-all duration-300 mx-1"
        :class="
          activeTab === 'chapters'
            ? 'text-white bg-blue-500 shadow-lg'
            : 'text-slate-600 hover:text-blue-600 hover:bg-slate-100'
        "
      >
        {{ t('videoChapters') }}
      </button>
    </div>

    <!-- Tab Content -->
    <div class="tab-content">
      <!-- Subtitles Tab -->
      <div v-show="activeTab === 'subtitles'" class="p-0">
        <SubtitlePanel
          :current-time="currentTime"
          :id="id"
          :rawLang="rawLang"
          :videoName="videoName"
          v-model:show-translation="showTranslation"
          @seek="emit('seek', $event)"
          @update-bloburls="emit('update-bloburls', $event)"
        />
      </div>

      <!-- Video Chapters Tab -->
      <div v-show="activeTab === 'chapters'" class="p-0">
        <VideoChapters :current-time="currentTime" :id="id" @seek="emit('seek', $event)" />
      </div>

    </div>
  </div>
</template>

<style scoped>
.tab-content {
  min-height: 400px;
}
</style>
