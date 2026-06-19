<script setup lang="ts">
/**
 * 自适应大屏容器
 * 以 1920×1080 为基准，transform: scale() 等比缩放居中
 */
import { ref, onMounted, onUnmounted } from 'vue'

defineProps<{ readonly?: boolean }>()

const BASE_W = 1920
const BASE_H = 1080
const containerRef = ref<HTMLElement>()
const scale = ref(1)
const isFullscreen = ref(false)

function updateScale() {
  const cw = window.innerWidth
  const ch = window.innerHeight
  scale.value = Math.min(cw / BASE_W, ch / BASE_H)
}

function toggleFullscreen() {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen().then(() => { isFullscreen.value = true })
  } else {
    document.exitFullscreen().then(() => { isFullscreen.value = false })
  }
}

function onFullscreenChange() {
  isFullscreen.value = !!document.fullscreenElement
}

onMounted(() => {
  updateScale()
  window.addEventListener('resize', updateScale)
  document.addEventListener('fullscreenchange', onFullscreenChange)
})

onUnmounted(() => {
  window.removeEventListener('resize', updateScale)
  document.removeEventListener('fullscreenchange', onFullscreenChange)
})

defineExpose({ toggleFullscreen, isFullscreen })
</script>

<template>
  <div class="screen-outer">
    <div
      ref="containerRef"
      class="screen-container"
      :style="{
        width: BASE_W + 'px',
        height: BASE_H + 'px',
        transform: `scale(${scale})`,
        transformOrigin: 'center center',
      }"
    >
      <slot />
    </div>
  </div>
</template>

<style scoped>
.screen-outer {
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  background: var(--surface-deep, #0B1220);
  display: flex;
  align-items: center;
  justify-content: center;
}
.screen-container {
  position: relative;
  flex-shrink: 0;
}
</style>
