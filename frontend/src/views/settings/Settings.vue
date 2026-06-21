<script setup lang="ts">
/**
 * System configuration page
 * Reuses the section card layout from AssetForm (Design 06)
 */
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { fetchConfig, updateConfig } from '@/api/config'
import { useFeatureStore } from '@/stores/feature'
import { useAuthStore } from '@/stores/auth'
import { useI18n } from 'vue-i18n'
import { setLocale } from '@/i18n'

const { t, locale } = useI18n()
const featureStore = useFeatureStore()
const authStore = useAuthStore()

interface ConfigItem {
  value: string
  description: string
  updated_at: string | null
}

const loading = ref(false)
const saving = ref(false)
const config = ref<Record<string, ConfigItem>>({})

// Group definitions: organize config items into section cards by business logic
const groups = [
  {
    num: '01',
    titleKey: 'settings.groups.scan.title',
    descKey: 'settings.groups.scan.desc',
    keys: ['missing_threshold', 'upload_max_size_mb', 'asset_no_prefix'],
  },
  {
    num: '02',
    titleKey: 'settings.groups.session.title',
    descKey: 'settings.groups.session.desc',
    keys: ['session_timeout_minutes'],
  },
  {
    num: '03',
    titleKey: 'settings.groups.llm.title',
    descKey: 'settings.groups.llm.desc',
    keys: ['llm_provider', 'llm_base_url', 'llm_api_key', 'llm_model', 'llm_ollama_model', 'llm_cloud_enabled', 'llm_route_core_to_local'],
  },
]

// Boolean config items (rendered as switches instead of input fields)
const booleanKeys = new Set(['llm_cloud_enabled', 'llm_route_core_to_local'])

// Number type config items (rendered as number inputs)
const numberKeys = new Set(['missing_threshold', 'upload_max_size_mb', 'session_timeout_minutes'])

// Hide URL and Key when LLM provider is "local"
const isCustomProvider = computed(() => {
  const p = config.value['llm_provider']?.value || ''
  return p !== 'ollama' && p !== ''
})

function isPasswordKey(key: string): boolean {
  return key.includes('api_key')
}

function getLabel(key: string): string {
  return t(`settings.labels.${key}`)
}

function getPlaceholder(key: string): string {
  return t(`settings.placeholders.${key}`)
}

// Boolean value adapter (convert string 'true'/'false' to boolean)
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
    ElMessage.success(t('settings.saveSuccess'))
    loadConfig()
  } finally {
    saving.value = false
  }
}

const costToggling = ref(false)

async function handleCostToggle(val: boolean) {
  if (!val) {
    try {
      await ElMessageBox.confirm(
        t('settings.costCard.confirmOff'),
        t('settings.costCard.confirmTitle'),
        { confirmButtonText: t('settings.costCard.confirmYes'), cancelButtonText: t('settings.costCard.confirmCancel'), type: 'warning' },
      )
    } catch {
      return // user cancelled
    }
  }
  costToggling.value = true
  try {
    await updateConfig({ feature_cost_accounting_enabled: val ? 'true' : 'false' })
    await featureStore.fetchFeatureFlags()
    ElMessage.success(val ? t('settings.costCard.enabled') : t('settings.costCard.disabled'))
  } finally {
    costToggling.value = false
  }
}

onMounted(loadConfig)
</script>

<template>
  <div v-loading="loading" class="settings-page">
    <div class="container">
      <!-- Page header -->
      <div class="ui-page-head" style="margin-bottom: var(--space-6)">
        <div>
          <h1 class="ui-page-title">{{ t('settings.title') }}</h1>
          <p class="ui-page-subtitle">{{ t('settings.subtitle') }}</p>
        </div>
        <div class="ui-page-actions">
          <el-button @click="loadConfig">
            <el-icon><Refresh /></el-icon>
            {{ t('settings.reset') }}
          </el-button>
          <el-button type="primary" :loading="saving" @click="handleSave">
            <el-icon><Check /></el-icon>
            {{ t('settings.save') }}
          </el-button>
        </div>
      </div>

      <!-- Feature toggle: asset cost accounting -->
      <div
        class="feature-card"
        :class="{ 'feature-card--enabled': featureStore.costAccounting }"
      >
        <div class="feature-card__body">
          <div class="feature-card__left">
            <div class="feature-card__icon" :class="{ 'feature-card__icon--enabled': featureStore.costAccounting }">
              <el-icon size="22"><TrendCharts /></el-icon>
            </div>
            <div class="feature-card__info">
              <div class="feature-card__title-row">
                <span class="feature-card__title">{{ t('settings.costCard.title') }}</span>
                <span
                  class="feature-card__badge"
                  :class="featureStore.costAccounting ? 'feature-card__badge--on' : 'feature-card__badge--off'"
                >
                  {{ featureStore.costAccounting ? t('settings.costCard.badgeOn') : t('settings.costCard.badgeOff') }}
                </span>
              </div>
              <p class="feature-card__desc">{{ t('settings.costCard.desc') }}</p>
              <div class="feature-card__meta">
                <span class="feature-card__dep" v-for="dep in ['costOverview', 'deptBilling', 'costRates', 'assetCost']" :key="dep">
                  <span class="feature-card__dot" :class="featureStore.costAccounting ? 'feature-card__dot--on' : ''"></span>
                  {{ t(`settings.costCard.dep.${dep}`) }}
                </span>
              </div>
            </div>
          </div>
          <div class="feature-card__right">
            <el-switch
              :model-value="featureStore.costAccounting"
              :disabled="!authStore.isSuperAdmin || costToggling"
              :loading="costToggling"
              @update:model-value="handleCostToggle"
            />
          </div>
        </div>
        <transition name="fade">
          <div v-if="featureStore.costAccounting" class="feature-card__links">
            <router-link to="/cost/overview" class="feature-card__link">
              <el-icon><DataLine /></el-icon> {{ t('settings.costCard.links.overview') }}
            </router-link>
            <router-link to="/cost/billing" class="feature-card__link">
              <el-icon><OfficeBuilding /></el-icon> {{ t('settings.costCard.links.billing') }}
            </router-link>
            <router-link to="/cost/rates" class="feature-card__link">
              <el-icon><PriceTag /></el-icon> {{ t('settings.costCard.links.rates') }}
            </router-link>
          </div>
        </transition>
      </div>

      <el-form label-width="160px" label-position="right">
        <!-- Language settings section 00 -->
        <div class="sec-card">
          <div class="sec-head">
            <span class="sec-num">00</span>
            <span class="sec-title">{{ t('settings.groups.language.title') }}</span>
            <span class="sec-desc">{{ t('settings.groups.language.desc') }}</span>
          </div>
          <div class="sec-body">
            <el-form-item :label="t('settings.groups.language.label')">
              <el-select
                :model-value="locale"
                @update:model-value="(val: string) => setLocale(val as 'en' | 'zh')"
                style="width: 240px"
              >
                <el-option label="English" value="en" />
                <el-option label="中文" value="zh" />
              </el-select>
            </el-form-item>
          </div>
        </div>

        <!-- Group section cards -->
        <div
          v-for="group in groups"
          :key="group.num"
          class="sec-card"
        >
          <div class="sec-head">
            <span class="sec-num">{{ group.num }}</span>
            <span class="sec-title">{{ t(group.titleKey) }}</span>
            <span class="sec-desc">{{ t(group.descKey) }}</span>
          </div>
          <div class="sec-body">
            <template v-for="key in group.keys" :key="key">
              <!-- LLM-related field conditional rendering -->
              <template v-if="group.num === '03'">
                <!-- Hide local model field in custom mode; hide URL/Key/model in local mode -->
                <template v-if="
                  (key === 'llm_ollama_model' && isCustomProvider) ||
                  ((key === 'llm_base_url' || key === 'llm_api_key' || key === 'llm_model') && !isCustomProvider)
                " />
                <el-form-item v-else-if="config[key]" :label="getLabel(key)">
                  <!-- Provider dropdown -->
                  <template v-if="key === 'llm_provider'">
                    <el-select
                      v-model="config[key].value"
                      style="width: 240px"
                    >
                      <el-option :label="t('settings.providers.custom')" value="openrouter" />
                      <el-option :label="t('settings.providers.local')" value="ollama" />
                    </el-select>
                    <span class="config-key">{{ key }}</span>
                  </template>
                  <!-- Boolean toggle -->
                  <template v-else-if="booleanKeys.has(key)">
                    <el-switch
                      :model-value="getBoolValue(key)"
                      @update:model-value="(v: boolean) => setBoolValue(key, v)"
                    />
                    <span class="config-key">{{ key }}</span>
                  </template>
                  <!-- Password input -->
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
                  <!-- Plain text -->
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

              <!-- Non-LLM config items (original logic) -->
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

      <!-- Bottom hint -->
      <div class="hint-card">
        <el-icon size="14" color="var(--neutral-400)"><InfoFilled /></el-icon>
        <span v-html="t('settings.hint')" />
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

/* Section card */
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

/* Config key identifier (after input field) */
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

/* Monospace input */
:deep(.mono-input .el-input__inner) {
  font-family: var(--font-mono);
  font-size: 13px;
}

/* Bottom hint */
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

/* ── Feature toggle Hero Card ── */
.feature-card {
  background: var(--surface-base);
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-lg);
  margin-bottom: var(--space-4);
  box-shadow: var(--shadow-subtle);
  transition: border-color var(--dur-base) var(--ease-out), box-shadow var(--dur-base) var(--ease-out);
  overflow: hidden;
}
.feature-card--enabled {
  border-color: var(--color-primary-200);
  box-shadow: 0 0 0 1px var(--color-primary-100), var(--shadow-medium);
}
.feature-card__body {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4) var(--space-6);
  border-bottom: var(--border-base);
  background: linear-gradient(180deg, rgba(37, 99, 235, 0.02) 0%, transparent 100%);
}
.feature-card__left {
  display: flex;
  align-items: flex-start;
  gap: var(--space-4);
  min-width: 0;
}
.feature-card__icon {
  width: 44px;
  height: 44px;
  border-radius: var(--radius-md);
  background: var(--neutral-100);
  color: var(--neutral-500);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: background var(--dur-base) var(--ease-out), color var(--dur-base) var(--ease-out);
}
.feature-card__icon--enabled {
  background: rgba(37, 99, 235, 0.1);
  color: var(--color-primary-600);
}
.feature-card__info {
  min-width: 0;
}
.feature-card__title-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-1);
}
.feature-card__title {
  font-size: var(--fs-h4);
  font-weight: 600;
  color: var(--neutral-900);
}
.feature-card__badge {
  font-size: 11px;
  font-weight: 600;
  padding: 1px 8px;
  border-radius: 10px;
  line-height: 1.6;
}
.feature-card__badge--on {
  background: rgba(16, 185, 129, 0.12);
  color: #059669;
}
.feature-card__badge--off {
  background: var(--neutral-100);
  color: var(--neutral-500);
}
.feature-card__desc {
  font-size: var(--fs-caption);
  color: var(--neutral-500);
  margin: 0;
  max-width: 480px;
  line-height: 1.5;
}
.feature-card__meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
  margin-top: var(--space-2);
}
.feature-card__dep {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  font-size: 11px;
  color: var(--neutral-500);
}
.feature-card__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--neutral-300);
  transition: background var(--dur-base) var(--ease-out);
}
.feature-card__dot--on {
  background: #10b981;
}
.feature-card__right {
  flex-shrink: 0;
  margin-left: var(--space-4);
}

/* Quick links */
.feature-card__links {
  display: flex;
  gap: var(--space-3);
  padding: var(--space-4) var(--space-6) var(--space-6);
  padding-left: calc(var(--space-6) + 44px + var(--space-4));
}
.feature-card__link {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  font-size: 13px;
  font-weight: 500;
  color: var(--color-primary-600);
  text-decoration: none;
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-md);
  background: rgba(37, 99, 235, 0.04);
  transition: background var(--dur-fast) var(--ease-out), color var(--dur-fast) var(--ease-out);
}
.feature-card__link:hover {
  background: rgba(37, 99, 235, 0.1);
  color: var(--color-primary-700);
}

/* fade transition */
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.25s ease, max-height 0.25s ease;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
  max-height: 0;
}
.fade-enter-to, .fade-leave-from {
  opacity: 1;
  max-height: 60px;
}
</style>
