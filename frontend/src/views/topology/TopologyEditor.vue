<script setup lang="ts">
/**
 * 拓扑图编辑页
 * 基于 Claude Design 08-topology-editor.html 实现
 * 使用 drawio embed iframe (embed.diagrams.net)
 */
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  fetchCurrentTopology,
  fetchTopologyVersions,
  generateTopology,
  saveTopology,
  rollbackTopology,
} from '@/api/topology'
import type { TopologyDetail, TopologyVersion } from '@/types/topology'

const loading = ref(false)
const generating = ref(false)
const currentTopology = ref<TopologyDetail | null>(null)
const versions = ref<TopologyVersion[]>([])
const drawioXml = ref('')
const drawioReady = ref(false)
const iframeRef = ref<HTMLIFrameElement | null>(null)

// drawio embed URL
const DRAWIO_URL = 'https://embed.diagrams.net/?embed=1&ui=min&spin=1&proto=json&configure=1&lang=zh'

async function loadData() {
  loading.value = true
  try {
    const [topo, vers] = await Promise.all([
      fetchCurrentTopology(),
      fetchTopologyVersions(),
    ])
    currentTopology.value = topo
    versions.value = vers
    if (topo) {
      drawioXml.value = topo.drawio_xml
    }
  } finally {
    loading.value = false
  }
}

// drawio postMessage 协议处理
function handleDrawioMessage(evt: MessageEvent) {
  if (!evt.data) return
  let msg: any
  try {
    msg = JSON.parse(evt.data)
  } catch {
    return
  }

  if (msg.event === 'configure') {
    // 配置 drawio 编辑器
    sendToDrawio({
      action: 'configure',
      config: {
        defaultFonts: ['Inter', 'JetBrains Mono'],
      },
    })
  } else if (msg.event === 'init') {
    // drawio 就绪，加载 XML
    drawioReady.value = true
    if (drawioXml.value) {
      sendToDrawio({ action: 'load', xml: drawioXml.value })
    } else {
      sendToDrawio({ action: 'load', xml: '' })
    }
  } else if (msg.event === 'save') {
    // 用户在 drawio 中点了保存
    drawioXml.value = msg.xml
    ElMessage.success('拓扑图内容已更新（尚未保存到服务器）')
  } else if (msg.event === 'export') {
    // 导出完成
    drawioXml.value = msg.data || msg.xml
  } else if (msg.event === 'exit') {
    // 用户关闭编辑器（不做处理，保持 iframe）
  }
}

function sendToDrawio(msg: object) {
  if (iframeRef.value?.contentWindow) {
    iframeRef.value.contentWindow.postMessage(JSON.stringify(msg), '*')
  }
}

// 从 drawio 获取当前 XML
function requestExport() {
  sendToDrawio({ action: 'export', format: 'xml' })
}

async function handleGenerate() {
  await ElMessageBox.confirm(
    '将使用 LLM 基于当前在线资产生成拓扑图初稿，可能需要 30-60 秒。',
    '生成拓扑图',
    { confirmButtonText: '开始生成', cancelButtonText: '取消' }
  )
  generating.value = true
  try {
    const result = await generateTopology()
    drawioXml.value = result.drawio_xml
    // 加载到 drawio
    if (drawioReady.value) {
      sendToDrawio({ action: 'load', xml: drawioXml.value })
    }
    ElMessage.success(`拓扑图已生成（${result.asset_count} 个资产）`)
  } finally {
    generating.value = false
  }
}

async function handleSave() {
  // 先从 drawio 获取最新 XML
  if (drawioReady.value) {
    requestExport()
    // 等待一小段时间让 export 回调更新 drawioXml
    await new Promise(resolve => setTimeout(resolve, 500))
  }

  if (!drawioXml.value) {
    ElMessage.warning('没有可保存的拓扑图内容')
    return
  }
  await saveTopology({
    title: `拓扑图 ${new Date().toLocaleDateString()}`,
    drawio_xml: drawioXml.value,
  })
  ElMessage.success('拓扑图已保存为新版本')
  loadData()
}

async function handleRollback(id: number, versionNo: string) {
  await ElMessageBox.confirm(
    `确认回滚到版本 ${versionNo}？当前版本将不再是活跃版本。`,
    '回滚确认',
    { confirmButtonText: '确认回滚', cancelButtonText: '取消', type: 'warning' }
  )
  await rollbackTopology(id)
  ElMessage.success('已回滚')
  loadData()
}

onMounted(() => {
  window.addEventListener('message', handleDrawioMessage)
  loadData()
})

onBeforeUnmount(() => {
  window.removeEventListener('message', handleDrawioMessage)
})
</script>

<template>
  <div v-loading="loading" class="topology-page">
    <!-- 页头 -->
    <div class="page-head">
      <div>
        <h1>网络拓扑图</h1>
        <p class="sub" v-if="currentTopology">
          当前版本：{{ currentTopology.version_no }}
          · 创建于 {{ currentTopology.created_at }}
        </p>
        <p class="sub" v-else>暂无拓扑图，请先生成或手动创建</p>
      </div>
      <div class="actions">
        <el-button :loading="generating" @click="handleGenerate">
          <el-icon><MagicStick /></el-icon>
          LLM 生成
        </el-button>
        <el-button type="primary" @click="handleSave" :disabled="!drawioXml && !drawioReady">
          <el-icon><Check /></el-icon>
          保存版本
        </el-button>
      </div>
    </div>

    <!-- 主内容区：编辑器 + 版本列表 -->
    <div class="content-grid">
      <!-- drawio 编辑器区域 -->
      <div class="editor-card">
        <iframe
          ref="iframeRef"
          :src="DRAWIO_URL"
          class="drawio-iframe"
          frameborder="0"
          allow="clipboard-read; clipboard-write"
        />
      </div>

      <!-- 版本列表 -->
      <div class="versions-card">
        <h3>历史版本</h3>
        <div v-if="versions.length === 0" class="empty-versions">暂无历史版本</div>
        <div v-else class="version-list">
          <div
            v-for="v in versions"
            :key="v.id"
            class="version-item"
            :class="{ current: v.is_current }"
          >
            <div class="v-info">
              <span class="v-no mono">{{ v.version_no }}</span>
              <span class="v-title" v-if="v.title">{{ v.title }}</span>
              <span class="v-time">{{ v.created_at }}</span>
            </div>
            <div class="v-actions">
              <el-tag v-if="v.is_current" size="small" type="success">当前</el-tag>
              <el-button
                v-else
                link
                size="small"
                type="primary"
                @click="handleRollback(v.id, v.version_no)"
              >
                回滚
              </el-button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.topology-page {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.page-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}
.page-head h1 {
  margin: 0;
  font-size: var(--fs-h2);
  color: var(--neutral-900);
  font-weight: 600;
}
.sub { margin-top: 6px; font-size: var(--fs-caption); color: var(--neutral-500); }
.actions { display: flex; gap: var(--space-2); }

.content-grid {
  display: grid;
  grid-template-columns: 1fr 280px;
  gap: var(--space-4);
  min-height: 600px;
}

/* drawio 编辑器 */
.editor-card {
  background: var(--neutral-0);
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-lg);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.drawio-iframe {
  width: 100%;
  height: 100%;
  min-height: 600px;
  border: none;
}

/* 版本列表 */
.versions-card {
  background: var(--neutral-0);
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  overflow-y: auto;
}
.versions-card h3 {
  margin: 0 0 var(--space-3);
  font-size: var(--fs-h4);
  color: var(--neutral-900);
  font-weight: 600;
}

.empty-versions {
  font-size: var(--fs-caption);
  color: var(--neutral-400);
  text-align: center;
  padding: var(--space-6) 0;
}

.version-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.version-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
  border: 1px solid var(--neutral-200);
}
.version-item.current {
  background: var(--color-primary-50);
  border-color: var(--color-primary-200);
}
.v-info { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.v-no { font-size: 12px; color: var(--neutral-900); font-weight: 500; }
.v-title { font-size: 12px; color: var(--neutral-500); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.v-time { font-size: 11px; color: var(--neutral-400); font-family: var(--font-mono); }

.mono { font-family: var(--font-mono); }
</style>
