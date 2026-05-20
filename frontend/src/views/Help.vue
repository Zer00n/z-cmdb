<script setup lang="ts">
/**
 * 帮助页面 - nmap 命令一键复制
 * 2026 UI Redesign：升级命令卡视觉，逻辑保持不变
 */
import { ElMessage } from 'element-plus'

const commands = [
  {
    title: '标准扫描',
    badge: '推荐',
    badgeClass: 'is-success',
    desc: '覆盖 1-10000 端口，适用于日常资产盘点，耗时约 10-30 分钟（/24 网段）',
    cmd: 'nmap -sS -sV -O --osscan-guess -p 1-10000 --version-intensity 5 -T4 -oX scan_$(date +%Y%m%d_%H%M).xml <目标网段>',
    cmdWin: 'nmap -sS -sV -O --osscan-guess -p 1-10000 --version-intensity 5 -T4 -oX scan_$(Get-Date -Format yyyyMMdd_HHmm).xml <目标网段>',
  },
  {
    title: '快速扫描',
    badge: '快',
    badgeClass: 'is-info',
    desc: '仅扫描 Top 1000 端口，适用于快速确认主机存活，耗时约 3-10 分钟',
    cmd: 'nmap -sS -sV -O --osscan-guess --top-ports 1000 -T4 -oX scan_quick_$(date +%Y%m%d_%H%M).xml <目标网段>',
    cmdWin: 'nmap -sS -sV -O --osscan-guess --top-ports 1000 -T4 -oX scan_quick_$(Get-Date -Format yyyyMMdd_HHmm).xml <目标网段>',
  },
  {
    title: '深度扫描',
    badge: '慢但全面',
    badgeClass: 'is-warning',
    desc: '扫描全部 65535 端口，适用于安全审计 / HVV 前全面盘点，耗时 30 分钟 - 数小时',
    cmd: 'nmap -sS -sV -O --osscan-guess -p- --version-intensity 7 -T3 -oX scan_deep_$(date +%Y%m%d_%H%M).xml <目标网段>',
    cmdWin: 'nmap -sS -sV -O --osscan-guess -p- --version-intensity 7 -T3 -oX scan_deep_$(Get-Date -Format yyyyMMdd_HHmm).xml <目标网段>',
  },
]

function copyCommand(cmd: string) {
  navigator.clipboard.writeText(cmd).then(() => {
    ElMessage.success('命令已复制到剪贴板')
  }).catch(() => {
    ElMessage.warning('复制失败，请手动选择复制')
  })
}
</script>

<template>
  <div class="ui-page">
    <div class="ui-page-head">
      <div>
        <h1 class="ui-page-title">nmap 扫描命令参考</h1>
        <p class="ui-page-subtitle">命令模板可直接复制使用 · 输出格式必须为 XML（-oX），系统只解析 XML</p>
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
                复制
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
                复制
              </el-button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="ui-card ui-card-padded">
      <h3 class="ui-section-title">
        <el-icon size="16" color="var(--color-warning)"><InfoFilled /></el-icon>
        注意事项
      </h3>
      <ul class="notice-list">
        <li><code>-sS</code>（SYN 扫描）和 <code>-O</code>（OS 检测）需要 root / 管理员权限</li>
        <li>上传文件大小上限 <b>50 MB</b>（可在系统配置中调整）</li>
        <li>建议按 /24 网段拆分扫描，避免单次文件过大</li>
        <li>Windows 环境下 <code>$(date ...)</code> 不可用，请手动命名文件</li>
        <li>如果大量端口显示 filtered，考虑降低扫描速度（<code>-T3</code> 或 <code>-T2</code>）</li>
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
