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

// ── 生成日志 ──────────────────────────────────────────────
interface LogEntry {
  time: string
  level: 'info' | 'warn' | 'error' | 'success'
  message: string
}

const rightTab = ref<'versions' | 'logs'>('versions')
const genLogs = ref<LogEntry[]>([])

function addLog(level: LogEntry['level'], message: string) {
  const now = new Date()
  const hh = String(now.getHours()).padStart(2, '0')
  const mm = String(now.getMinutes()).padStart(2, '0')
  const ss = String(now.getSeconds()).padStart(2, '0')
  genLogs.value.push({ time: `${hh}:${mm}:${ss}`, level, message })
}

const llmDetail = ref<{
  provider?: string
  model?: string
  elapsed_ms?: number
  success?: boolean
  prompt_length?: number
} | null>(null)

async function fetchLatestLlmLog() {
  try {
    const resp: any = await (await import('@/api/request')).default.get('/api/audit/llm-logs', { params: { page: 1, page_size: 1 } })
    if (resp.items?.length) {
      const log = resp.items[0]
      llmDetail.value = {
        provider: log.provider,
        model: log.model,
        elapsed_ms: log.elapsed_ms,
        success: log.success,
      }
    }
  } catch {
    // 无权限或接口不存在时静默
  }
}

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
  rightTab.value = 'logs'
  genLogs.value = []
  llmDetail.value = null
  addLog('info', '开始生成拓扑图...')
  addLog('info', '正在获取在线资产数据...')

  const startTime = Date.now()
  try {
    addLog('info', '正在调用 LLM 接口，请耐心等待...')
    const result = await generateTopology()
    const elapsed = ((Date.now() - startTime) / 1000).toFixed(1)
    drawioXml.value = result.drawio_xml
    if (drawioReady.value) {
      sendToDrawio({ action: 'load', xml: drawioXml.value })
    }
    addLog('success', `生成完成，耗时 ${elapsed}s，包含 ${result.asset_count} 个资产`)
    ElMessage.success(`拓扑图已生成（${result.asset_count} 个资产）`)
    // 拉取 LLM 调用详情
    fetchLatestLlmLog()
  } catch (e: any) {
    const elapsed = ((Date.now() - startTime) / 1000).toFixed(1)
    addLog('error', `生成失败（${elapsed}s）：${e?.response?.data?.message || e?.message || '未知错误'}`)
    throw e
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
  <div v-loading="loading" class="ui-page topology-page">
    <!-- 页头 -->
    <div class="ui-page-head">
      <div>
        <h1 class="ui-page-title">
          网络拓扑图
          <span v-if="currentTopology" class="ui-page-count">{{ currentTopology.version_no }}</span>
        </h1>
        <p class="ui-page-subtitle" v-if="currentTopology">
          当前版本创建于 {{ currentTopology.created_at }} · 共 {{ versions.length }} 个历史版本
        </p>
        <p class="ui-page-subtitle" v-else>暂无拓扑图，请先用 LLM 生成或手动创建</p>
      </div>
      <div class="ui-page-actions">
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
      <!-- drawio 编辑器 -->
      <div class="editor-card">
        <div class="editor-toolbar">
          <span class="editor-label">
            <span class="editor-dot" />
            drawio · embed.diagrams.net
          </span>
          <span class="editor-hint">在编辑器中拖拽节点 · 双击文本编辑 · Ctrl+S 临时保存</span>
        </div>
        <iframe
          ref="iframeRef"
          :src="DRAWIO_URL"
          class="drawio-iframe"
          frameborder="0"
          allow="clipboard-read; clipboard-write"
        />
      </div>

      <!-- 右侧面板：Tab 切换 -->
      <div class="ui-card versions-card">
        <!-- Tab 栏 -->
        <div class="right-tabs">
          <button
            :class="['right-tab', { active: rightTab === 'versions' }]"
            @click="rightTab = 'versions'"
          >
            历史版本
            <span class="tab-badge">{{ versions.length }}</span>
          </button>
          <button
            :class="['right-tab', { active: rightTab === 'logs' }]"
            @click="rightTab = 'logs'"
          >
            生成日志
            <span v-if="genLogs.length" class="tab-badge">{{ genLogs.length }}</span>
          </button>
        </div>

        <!-- 历史版本 -->
        <div v-show="rightTab === 'versions'" class="tab-content">
          <div v-if="versions.length === 0" class="ui-empty">
            <div class="ui-empty-title">暂无历史版本</div>
            <div class="ui-empty-desc">保存后将出现在此</div>
          </div>
          <div v-else class="version-list">
            <div
              v-for="v in versions"
              :key="v.id"
              class="version-item"
              :class="{ current: v.is_current }"
            >
              <div class="v-info">
                <div class="v-line-1">
                  <span class="v-no">{{ v.version_no }}</span>
                  <span v-if="v.is_current" class="ui-badge is-success">
                    <span class="ui-badge-dot" />
                    当前
                  </span>
                </div>
                <span class="v-title" v-if="v.title">{{ v.title }}</span>
                <span class="v-time">{{ v.created_at }}</span>
              </div>
              <div class="v-actions">
                <el-button
                  v-if="!v.is_current"
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

        <!-- 生成日志 -->
        <div v-show="rightTab === 'logs'" class="tab-content log-content">
          <div v-if="genLogs.length === 0 && !llmDetail" class="ui-empty">
            <div class="ui-empty-title">暂无日志</div>
            <div class="ui-empty-desc">点击「LLM 生成」后日志将在此显示</div>
          </div>
          <template v-else>
            <!-- LLM 调用详情 -->
            <div v-if="llmDetail" class="llm-detail-card">
              <div class="llm-row">
                <span class="llm-label">提供方</span>
                <span class="llm-value">{{ llmDetail.provider || '-' }}</span>
              </div>
              <div class="llm-row">
                <span class="llm-label">模型</span>
                <span class="llm-value llm-model">{{ llmDetail.model || '-' }}</span>
              </div>
              <div class="llm-row">
                <span class="llm-label">耗时</span>
                <span class="llm-value">{{ llmDetail.elapsed_ms ? (llmDetail.elapsed_ms / 1000).toFixed(1) + 's' : '-' }}</span>
              </div>
              <div class="llm-row">
                <span class="llm-label">结果</span>
                <span :class="['llm-value', llmDetail.success ? 'text-success' : 'text-error']">
                  {{ llmDetail.success ? '成功' : '失败' }}
                </span>
              </div>
            </div>
            <!-- 日志列表 -->
            <div class="log-list">
              <div v-for="(log, i) in genLogs" :key="i" :class="['log-entry', log.level]">
                <span class="log-time">{{ log.time }}</span>
                <span class="log-icon">
                  <template v-if="log.level === 'info'">●</template>
                  <template v-else-if="log.level === 'success'">✓</template>
                  <template v-else-if="log.level === 'warn'">▲</template>
                  <template v-else>✕</template>
                </span>
                <span class="log-msg">{{ log.message }}</span>
              </div>
            </div>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.topology-page {
  height: calc(100vh - var(--topbar-h) - var(--space-12));
}

.content-grid {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: var(--space-4);
  flex: 1;
  min-height: 600px;
}

/* drawio 编辑器 */
.editor-card {
  background: var(--surface-base);
  border: var(--border-base);
  border-radius: var(--radius-lg);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-subtle);
}

.editor-toolbar {
  height: 38px;
  padding: 0 var(--space-4);
  border-bottom: var(--border-base);
  background: linear-gradient(180deg, rgba(37, 99, 235, 0.03) 0%, transparent 100%);
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
}
.editor-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-family: var(--font-mono);
  font-size: 11.5px;
  color: var(--neutral-500);
  font-weight: 500;
}
.editor-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-success);
  box-shadow: 0 0 0 3px rgba(22, 163, 74, 0.18);
}
.editor-hint {
  font-size: 11.5px;
  color: var(--neutral-400);
}

.drawio-iframe {
  width: 100%;
  flex: 1;
  min-height: 600px;
  border: none;
  background: var(--surface-sunken);
}

/* 版本列表 */
.versions-card {
  display: flex;
  flex-direction: column;
  padding: 0;
  overflow: hidden;
}

/* 右侧 Tab 栏 */
.right-tabs {
  display: flex;
  border-bottom: var(--border-base);
  flex-shrink: 0;
}
.right-tab {
  flex: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px 0;
  font-size: 13px;
  font-weight: 500;
  color: var(--neutral-500);
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  transition: color 0.15s, border-color 0.15s;
}
.right-tab:hover { color: var(--neutral-700); }
.right-tab.active {
  color: var(--color-primary);
  border-bottom-color: var(--color-primary);
}
.tab-badge {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--neutral-500);
  background: var(--surface-sunken);
  padding: 0 7px;
  border-radius: 999px;
  line-height: 18px;
}
.right-tab.active .tab-badge {
  color: var(--color-primary);
  background: rgba(37, 99, 235, 0.08);
}

.tab-content {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}

.version-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-3);
}
.version-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3);
  border-radius: var(--radius-md);
  border: 1px solid var(--neutral-200);
  background: var(--surface-base);
  transition: border-color var(--dur-fast) var(--ease-out),
              background-color var(--dur-fast) var(--ease-out);
}
.version-item:hover {
  border-color: var(--neutral-300);
  background: var(--surface-sunken);
}
.version-item.current {
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.06), rgba(99, 102, 241, 0.04));
  border-color: rgba(37, 99, 235, 0.25);
}
.v-info { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.v-line-1 {
  display: flex;
  align-items: center;
  gap: 8px;
}
.v-no {
  font-family: var(--font-mono);
  font-size: 12.5px;
  color: var(--neutral-900);
  font-weight: 600;
}
.v-title {
  font-size: 12px;
  color: var(--neutral-500);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.v-time {
  font-size: 11px;
  color: var(--neutral-400);
  font-family: var(--font-mono);
}

/* LLM 详情卡片 */
.llm-detail-card {
  margin: var(--space-3);
  padding: var(--space-3);
  background: var(--surface-sunken);
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-md);
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex-shrink: 0;
}
.llm-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
}
.llm-label { color: var(--neutral-500); }
.llm-value { color: var(--neutral-800); font-weight: 500; font-family: var(--font-mono); font-size: 11.5px; }
.llm-model { max-width: 160px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.text-success { color: var(--color-success) !important; }
.text-error { color: var(--color-danger) !important; }

/* 日志列表 */
.log-content { padding: 0; }
.log-list {
  display: flex;
  flex-direction: column;
  padding: var(--space-2) var(--space-3);
  gap: 2px;
}
.log-entry {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 3px 0;
  font-size: 12px;
  line-height: 1.5;
}
.log-time {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--neutral-400);
  flex-shrink: 0;
  width: 52px;
}
.log-icon {
  flex-shrink: 0;
  width: 14px;
  text-align: center;
  font-size: 10px;
}
.log-entry.info .log-icon { color: var(--color-primary); }
.log-entry.success .log-icon { color: var(--color-success); }
.log-entry.warn .log-icon { color: var(--color-warning); }
.log-entry.error .log-icon { color: var(--color-danger); }
.log-msg {
  color: var(--neutral-700);
  word-break: break-all;
}
.log-entry.error .log-msg { color: var(--color-danger); }
.log-entry.success .log-msg { color: var(--color-success); }
</style>
