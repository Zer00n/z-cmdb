<script setup lang="ts">
/**
 * 系统配置页
 * 复用 AssetForm（Design 06）的分段卡片布局
 */
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchConfig, updateConfig } from '@/api/config'

interface ConfigItem {
  value: string
  description: string
  updated_at: string | null
}

const loading = ref(false)
const saving = ref(false)
const config = ref<Record<string, ConfigItem>>({})

// 分组定义：按业务逻辑把配置项分到不同段卡片
const groups = [
  {
    num: '01',
    title: '扫描与资产',
    desc: '扫描批次和资产管理相关参数',
    keys: ['missing_threshold', 'upload_max_size_mb', 'asset_no_prefix'],
  },
  {
    num: '02',
    title: '会话与安全',
    desc: '用户会话超时设置',
    keys: ['session_timeout_minutes'],
  },
  {
    num: '03',
    title: 'LLM 配置',
    desc: '拓扑图生成所用的大语言模型配置',
    keys: ['llm_provider', 'llm_base_url', 'llm_api_key', 'llm_model', 'llm_ollama_model', 'llm_cloud_enabled', 'llm_route_core_to_local'],
  },
]

// 配置项中文标签覆盖（替代后端 description）
const labelMap: Record<string, string> = {
  missing_threshold: '消失保护阈值',
  upload_max_size_mb: '上传文件上限 (MB)',
  asset_no_prefix: '资产编号前缀',
  session_timeout_minutes: 'Session 超时 (分钟)',
  llm_provider: 'LLM 提供方',
  llm_api_key: 'API Key',
  llm_model: '模型名称',
  llm_base_url: 'API 地址',
  llm_ollama_model: '本地模型名称',
  llm_route_core_to_local: '核心资产路由本地',
  llm_cloud_enabled: '允许使用云端 LLM',
}

// 配置项占位提示
const placeholderMap: Record<string, string> = {
  missing_threshold: '默认 3，连续未扫到 N 次后标记离线',
  upload_max_size_mb: '默认 50',
  asset_no_prefix: '默认 CMDB',
  session_timeout_minutes: '默认 30',
  llm_api_key: '加密存储，留空则不更新',
  llm_model: '例如 deepseek-chat / gpt-4o / claude-3-5-sonnet',
  llm_base_url: '例如 https://api.deepseek.com/v1',
  llm_ollama_model: '默认 qwen2.5',
}

// 布尔类型配置项（渲染为开关而非输入框）
const booleanKeys = new Set(['llm_cloud_enabled', 'llm_route_core_to_local'])

// 数字类型配置项（渲染为数字输入框）
const numberKeys = new Set(['missing_threshold', 'upload_max_size_mb', 'session_timeout_minutes'])

// LLM 提供方为「本地」时隐藏 URL 和 Key
const isCustomProvider = computed(() => {
  const p = config.value['llm_provider']?.value || ''
  return p !== 'ollama' && p !== ''
})

function isPasswordKey(key: string): boolean {
  return key.includes('api_key')
}

function getLabel(key: string): string {
  return labelMap[key] || config.value[key]?.description || key
}

function getPlaceholder(key: string): string {
  return placeholderMap[key] || ''
}

// 布尔值适配（从字符串 'true'/'false' 转布尔）
function getBoolValue(key: string): boolean {
  const v = config.value[key]?.value
  return v === 'true' || v === '1'
}

function setBoolValue(key: string, val: boolean) {
  if (config.value[key]) {
    config.value[key].value = val ? 'true' : 'false'
  }
}

async function loadConfig() {
  loading.value = true
  try {
    config.value = await fetchConfig()
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  saving.value = true
  try {
    const data: Record<string, string> = {}
    for (const [key, item] of Object.entries(config.value)) {
      data[key] = item.value
    }
    await updateConfig(data)
    ElMessage.success('配置已保存')
    loadConfig()
  } finally {
    saving.value = false
  }
}

onMounted(loadConfig)
</script>

<template>
  <div v-loading="loading" class="settings-page">
    <div class="container">
      <!-- 页头 -->
      <div class="ui-page-head" style="margin-bottom: var(--space-6)">
        <div>
          <h1 class="ui-page-title">系统配置</h1>
          <p class="ui-page-subtitle">调整运行时参数 · 配置项立即生效，无需重启服务</p>
        </div>
        <div class="ui-page-actions">
          <el-button @click="loadConfig">
            <el-icon><Refresh /></el-icon>
            重置
          </el-button>
          <el-button type="primary" :loading="saving" @click="handleSave">
            <el-icon><Check /></el-icon>
            保存配置
          </el-button>
        </div>
      </div>

      <el-form label-width="160px" label-position="right">
        <!-- 各分组段卡片 -->
        <div
          v-for="group in groups"
          :key="group.num"
          class="sec-card"
        >
          <div class="sec-head">
            <span class="sec-num">{{ group.num }}</span>
            <span class="sec-title">{{ group.title }}</span>
            <span class="sec-desc">{{ group.desc }}</span>
          </div>
          <div class="sec-body">
            <template v-for="key in group.keys" :key="key">
              <!-- LLM 相关字段条件渲染 -->
              <template v-if="group.num === '03'">
                <!-- 自定义模式下隐藏本地模型字段；本地模式下隐藏 URL/Key/模型字段 -->
                <template v-if="
                  (key === 'llm_ollama_model' && isCustomProvider) ||
                  ((key === 'llm_base_url' || key === 'llm_api_key' || key === 'llm_model') && !isCustomProvider)
                " />
                <el-form-item v-else-if="config[key]" :label="getLabel(key)">
                  <!-- 提供方下拉 -->
                  <template v-if="key === 'llm_provider'">
                    <el-select
                      v-model="config[key].value"
                      style="width: 240px"
                    >
                      <el-option label="自定义" value="openrouter" />
                      <el-option label="本地 (Ollama)" value="ollama" />
                    </el-select>
                    <span class="config-key">{{ key }}</span>
                  </template>
                  <!-- 布尔开关 -->
                  <template v-else-if="booleanKeys.has(key)">
                    <el-switch
                      :model-value="getBoolValue(key)"
                      @update:model-value="(v: boolean) => setBoolValue(key, v)"
                    />
                    <span class="config-key">{{ key }}</span>
                  </template>
                  <!-- 密码输入 -->
                  <template v-else-if="isPasswordKey(key)">
                    <el-input
                      v-model="config[key].value"
                      type="password"
                      show-password
                      :placeholder="getPlaceholder(key)"
                      style="width: 360px"
                    />
                    <span class="config-key">{{ key }}</span>
                  </template>
                  <!-- 普通文本 -->
                  <template v-else>
                    <el-input
                      v-model="config[key].value"
                      :placeholder="getPlaceholder(key)"
                      style="width: 360px"
                      :class="{ 'mono-input': key === 'llm_base_url' || key === 'llm_model' || key === 'llm_ollama_model' }"
                    />
                    <span class="config-key">{{ key }}</span>
                  </template>
                </el-form-item>
              </template>

              <!-- 非 LLM 配置项（原逻辑） -->
              <template v-else>
                <el-form-item v-if="config[key]" :label="getLabel(key)">
                  <template v-if="booleanKeys.has(key)">
                    <el-switch
                      :model-value="getBoolValue(key)"
                      @update:model-value="(v: boolean) => setBoolValue(key, v)"
                    />
                    <span class="config-key">{{ key }}</span>
                  </template>
                  <template v-else-if="numberKeys.has(key)">
                    <el-input
                      v-model="config[key].value"
                      type="number"
                      :placeholder="getPlaceholder(key)"
                      style="width: 240px"
                    />
                    <span class="config-key">{{ key }}</span>
                  </template>
                  <template v-else>
                    <el-input
                      v-model="config[key].value"
                      :placeholder="getPlaceholder(key)"
                      style="width: 360px"
                    />
                    <span class="config-key">{{ key }}</span>
                  </template>
                </el-form-item>
              </template>
            </template>
          </div>
        </div>
      </el-form>

      <!-- 底部提示 -->
      <div class="hint-card">
        <el-icon size="14" color="var(--neutral-400)"><InfoFilled /></el-icon>
        <span>API Key 等敏感字段在数据库中以 <b>Fernet 加密</b>方式存储；显示时已脱敏。</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.settings-page {
  padding-bottom: var(--space-12);
}

.container {
  max-width: 960px;
}

/* 段卡片 */
.sec-card {
  background: var(--surface-base);
  border: var(--border-base);
  border-radius: var(--radius-lg);
  margin-bottom: var(--space-4);
  box-shadow: var(--shadow-subtle);
  transition: box-shadow var(--dur-base) var(--ease-out);
}
.sec-card:hover {
  box-shadow: var(--shadow-medium);
}
.sec-head {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-4) var(--space-6);
  border-bottom: var(--border-base);
  background: linear-gradient(180deg, rgba(37, 99, 235, 0.02) 0%, transparent 100%);
}
.sec-num {
  width: 28px;
  height: 28px;
  border-radius: var(--radius-md);
  background: var(--accent-gradient);
  color: #FFFFFF;
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 2px 6px -1px rgba(37, 99, 235, 0.4);
}
.sec-title {
  font-size: var(--fs-h4);
  font-weight: 600;
  color: var(--neutral-900);
}
.sec-desc {
  font-size: 12.5px;
  color: var(--neutral-500);
  margin-left: var(--space-2);
}
.sec-body {
  padding: var(--space-6);
}

/* 配置项 key 标识（输入框后） */
.config-key {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--neutral-400);
  margin-left: var(--space-3);
  background: var(--surface-sunken);
  padding: 1px 6px;
  border-radius: 3px;
  border: 1px solid var(--neutral-200);
}

/* 等宽输入框 */
:deep(.mono-input .el-input__inner) {
  font-family: var(--font-mono);
  font-size: 13px;
}

/* 底部提示 */
.hint-card {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  background: linear-gradient(90deg, rgba(37, 99, 235, 0.04) 0%, rgba(99, 102, 241, 0.02) 100%);
  border: 1px solid rgba(37, 99, 235, 0.12);
  border-radius: var(--radius-md);
  font-size: var(--fs-caption);
  color: var(--neutral-700);
  margin-top: var(--space-2);
}
.hint-card b {
  font-weight: 600;
  color: var(--color-primary-700);
}
</style>
