<script setup lang="ts">
/**
 * 帮助页面 - nmap 命令一键复制
 */
import { ElMessage } from 'element-plus'

const commands = [
  {
    title: '标准扫描（推荐）',
    desc: '覆盖 1-10000 端口，适用于日常资产盘点，耗时约 10-30 分钟（/24 网段）',
    cmd: 'nmap -sS -sV -O --osscan-guess -p 1-10000 --version-intensity 5 -T4 -oX scan_$(date +%Y%m%d_%H%M).xml <目标网段>',
    cmdWin: 'nmap -sS -sV -O --osscan-guess -p 1-10000 --version-intensity 5 -T4 -oX scan_$(Get-Date -Format yyyyMMdd_HHmm).xml <目标网段>',
  },
  {
    title: '快速扫描',
    desc: '仅扫描 Top 1000 端口，适用于快速确认主机存活，耗时约 3-10 分钟',
    cmd: 'nmap -sS -sV -O --osscan-guess --top-ports 1000 -T4 -oX scan_quick_$(date +%Y%m%d_%H%M).xml <目标网段>',
    cmdWin: 'nmap -sS -sV -O --osscan-guess --top-ports 1000 -T4 -oX scan_quick_$(Get-Date -Format yyyyMMdd_HHmm).xml <目标网段>',
  },
  {
    title: '深度扫描',
    desc: '扫描全部 65535 端口，适用于安全审计/HVV 前全面盘点，耗时 30 分钟 - 数小时',
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
  <div class="help-page">
    <div class="page-head">
      <h1>nmap 扫描命令参考</h1>
      <p class="sub">以下命令模板可直接复制使用。输出格式必须为 XML（-oX），系统只解析 XML。</p>
    </div>

    <div class="cmd-list">
      <div v-for="item in commands" :key="item.title" class="cmd-card">
        <div class="cmd-head">
          <h3>{{ item.title }}</h3>
          <p>{{ item.desc }}</p>
        </div>
        <div class="cmd-body">
          <div class="cmd-section">
            <span class="cmd-label">Linux / macOS</span>
            <div class="cmd-row">
              <pre class="cmd-text">{{ item.cmd }}</pre>
              <el-button type="primary" size="small" @click="copyCommand(item.cmd)">
                <el-icon><CopyDocument /></el-icon>
                复制
              </el-button>
            </div>
          </div>
          <div class="cmd-section">
            <span class="cmd-label">Windows PowerShell</span>
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

    <div class="notice-card">
      <h3>注意事项</h3>
      <ul>
        <li><code>-sS</code>（SYN 扫描）和 <code>-O</code>（OS 检测）需要 root/管理员权限</li>
        <li>上传文件大小上限 50 MB（可在系统配置中调整）</li>
        <li>建议按 /24 网段拆分扫描，避免单次文件过大</li>
        <li>Windows 环境下 <code>$(date ...)</code> 不可用，请手动命名文件</li>
        <li>如果大量端口显示 filtered，考虑降低扫描速度（<code>-T3</code> 或 <code>-T2</code>）</li>
      </ul>
    </div>
  </div>
</template>

<style scoped>
.help-page {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.page-head h1 {
  margin: 0;
  font-size: var(--fs-h2);
  color: var(--neutral-900);
  font-weight: 600;
}
.sub {
  margin-top: 6px;
  font-size: var(--fs-caption);
  color: var(--neutral-500);
}

.cmd-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.cmd-card {
  background: var(--neutral-0);
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-lg);
  overflow: hidden;
}
.cmd-head {
  padding: var(--space-4) var(--space-6);
  border-bottom: 1px solid var(--neutral-200);
}
.cmd-head h3 {
  margin: 0 0 4px;
  font-size: var(--fs-h4);
  color: var(--neutral-900);
  font-weight: 600;
}
.cmd-head p {
  margin: 0;
  font-size: var(--fs-caption);
  color: var(--neutral-500);
}
.cmd-body {
  padding: var(--space-4) var(--space-6);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  background: var(--neutral-50);
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
  letter-spacing: 0.06em;
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
  line-height: 20px;
  color: var(--neutral-900);
  white-space: pre-wrap;
  word-break: break-all;
  background: var(--neutral-0);
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-sm);
  padding: var(--space-2) var(--space-3);
}

.notice-card {
  background: var(--neutral-0);
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
}
.notice-card h3 {
  margin: 0 0 var(--space-3);
  font-size: var(--fs-h4);
  color: var(--neutral-900);
  font-weight: 600;
}
.notice-card ul {
  margin: 0;
  padding-left: var(--space-6);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.notice-card li {
  font-size: var(--fs-body);
  color: var(--neutral-700);
  line-height: 22px;
}
.notice-card code {
  font-family: var(--font-mono);
  font-size: 12px;
  background: var(--neutral-100);
  padding: 1px 4px;
  border-radius: 3px;
}
</style>
