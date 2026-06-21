<script setup lang="ts">
/**
 * Help page — nmap command one-click copy
 * 2026 UI Redesign: upgraded command card visuals, logic unchanged
 */
import { computed } from 'vue'
import { ElMessage } from 'element-plus'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const commands = computed(() => [
  {
    title: t('help.commands.standard.title'),
    badge: t('help.commands.standard.badge'),
    badgeClass: 'is-success',
    desc: t('help.commands.standard.desc'),
    cmd: 'nmap -sS -sV -O --osscan-guess -p 1-10000 --version-intensity 5 -T4 -oX scan_$(date +%Y%m%d_%H%M).xml <目标网段>',
    cmdWin: 'nmap -sS -sV -O --osscan-guess -p 1-10000 --version-intensity 5 -T4 -oX scan_$(Get-Date -Format yyyyMMdd_HHmm).xml <目标网段>',
  },
  {
    title: t('help.commands.quick.title'),
    badge: t('help.commands.quick.badge'),
    badgeClass: 'is-info',
    desc: t('help.commands.quick.desc'),
    cmd: 'nmap -sS -sV -O --osscan-guess --top-ports 1000 -T4 -oX scan_quick_$(date +%Y%m%d_%H%M).xml <目标网段>',
    cmdWin: 'nmap -sS -sV -O --osscan-guess --top-ports 1000 -T4 -oX scan_quick_$(Get-Date -Format yyyyMMdd_HHmm).xml <目标网段>',
  },
  {
    title: t('help.commands.deep.title'),
    badge: t('help.commands.deep.badge'),
    badgeClass: 'is-warning',
    desc: t('help.commands.deep.desc'),
    cmd: 'nmap -sS -sV -O --osscan-guess -p- --version-intensity 7 -T3 -oX scan_deep_$(date +%Y%m%d_%H%M).xml <目标网段>',
    cmdWin: 'nmap -sS -sV -O --osscan-guess -p- --version-intensity 7 -T3 -oX scan_deep_$(Get-Date -Format yyyyMMdd_HHmm).xml <目标网段>',
  },
])

function copyCommand(cmd: string) {
  navigator.clipboard.writeText(cmd).then(() => {
    ElMessage.success(t('help.copySuccess'))
  }).catch(() => {
    ElMessage.warning(t('help.copyFailed'))
  })
}
</script>

<template>
  <div class="ui-page">
    <div class="ui-page-head">
      <div>
        <h1 class="ui-page-title">{{ t('help.title') }}</h1>
        <p class="ui-page-subtitle">{{ t('help.subtitle') }}</p>
      </div>
    </div>

    <div class="cmd-list">
      <div v-for="item in commands" :key="item.title" class="ui-card cmd-card">
        <div class="cmd-head">
          <div class="cmd-head-main">
            <h3>{{ item.title }}</h3>
            <span class="ui-badge" :class="item.badgeClass">
              <span class="ui-badge-dot" />
              {{ item.badge }}
            </span>
          </div>
          <p>{{ item.desc }}</p>
        </div>
        <div class="cmd-body">
          <div class="cmd-section">
            <span class="cmd-label">
              <el-icon size="12"><Monitor /></el-icon>
              Linux / macOS
            </span>
            <div class="cmd-row">
              <pre class="cmd-text">{{ item.cmd }}</pre>
              <el-button type="primary" size="small" @click="copyCommand(item.cmd)">
                <el-icon><CopyDocument /></el-icon>
                {{ t('help.copy') }}
              </el-button>
            </div>
          </div>
          <div class="cmd-section">
            <span class="cmd-label">
              <el-icon size="12"><Platform /></el-icon>
              Windows PowerShell
            </span>
            <div class="cmd-row">
              <pre class="cmd-text">{{ item.cmdWin }}</pre>
              <el-button type="primary" size="small" @click="copyCommand(item.cmdWin)">
                <el-icon><CopyDocument /></el-icon>
                {{ t('help.copy') }}
              </el-button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="ui-card ui-card-padded">
      <h3 class="ui-section-title">
        <el-icon size="16" color="var(--color-warning)"><InfoFilled /></el-icon>
        {{ t('help.notices.title') }}
      </h3>
      <ul class="notice-list">
        <li v-html="t('help.notices.items.privileges')"></li>
        <li v-html="t('help.notices.items.uploadLimit')"></li>
        <li>{{ t('help.notices.items.subnet') }}</li>
        <li>{{ t('help.notices.items.windows') }}</li>
        <li>{{ t('help.notices.items.filtered') }}</li>
      </ul>
    </div>
  </div>
</template>

<style scoped>
.cmd-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.cmd-card {
  overflow: hidden;
  transition: box-shadow var(--dur-base) var(--ease-out);
}
.cmd-card:hover {
  box-shadow: var(--shadow-card-hover);
}

.cmd-head {
  padding: var(--space-4) var(--space-6);
  border-bottom: var(--border-base);
  background: linear-gradient(180deg, rgba(37, 99, 235, 0.03) 0%, transparent 100%);
}
.cmd-head-main {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: 4px;
}
.cmd-head h3 {
  margin: 0;
  font-size: var(--fs-h4);
  color: var(--neutral-900);
  font-weight: 600;
}
.cmd-head p {
  margin: 0;
  font-size: 12.5px;
  color: var(--neutral-500);
}

.cmd-body {
  padding: var(--space-4) var(--space-6);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  background: var(--surface-sunken);
}

.cmd-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.cmd-label {
  font-size: 11px;
  font-family: var(--font-mono);
  color: var(--neutral-500);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.cmd-row {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
}
.cmd-text {
  flex: 1;
  margin: 0;
  font-family: var(--font-mono);
  font-size: 13px;
  line-height: 22px;
  color: var(--neutral-900);
  white-space: pre-wrap;
  word-break: break-all;
  background: var(--surface-base);
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-md);
  padding: var(--space-3) var(--space-4);
  box-shadow: inset 0 1px 0 rgba(15, 23, 42, 0.02);
}

.notice-list {
  margin: 0;
  padding-left: var(--space-6);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.notice-list li {
  font-size: var(--fs-body);
  color: var(--neutral-700);
  line-height: 22px;
}
.notice-list code {
  font-family: var(--font-mono);
  font-size: 12px;
  background: var(--surface-sunken);
  border: 1px solid var(--neutral-200);
  padding: 1px 6px;
  border-radius: 3px;
  color: var(--neutral-900);
}
.notice-list b {
  font-weight: 600;
  color: var(--color-primary-700);
}
</style>
