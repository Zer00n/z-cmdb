export default {
  title: 'nmap 扫描命令参考',
  subtitle: '命令模板可直接复制使用 · 输出格式必须为 XML（-oX），系统只解析 XML',
  commands: {
    standard: {
      title: '标准扫描',
      badge: '推荐',
      desc: '覆盖 1-10000 端口，适用于日常资产盘点，耗时约 10-30 分钟（/24 网段）',
    },
    quick: {
      title: '快速扫描',
      badge: '快',
      desc: '仅扫描 Top 1000 端口，适用于快速确认主机存活，耗时约 3-10 分钟',
    },
    deep: {
      title: '深度扫描',
      badge: '慢但全面',
      desc: '扫描全部 65535 端口，适用于安全审计 / HVV 前全面盘点，耗时 30 分钟 - 数小时',
    },
  },
  copy: '复制',
  copySuccess: '命令已复制到剪贴板',
  copyFailed: '复制失败，请手动选择复制',
  notices: {
    title: '注意事项',
    items: {
      privileges: '<code>-sS</code>（SYN 扫描）和 <code>-O</code>（OS 检测）需要 root / 管理员权限',
      uploadLimit: '上传文件大小上限 <b>50 MB</b>（可在系统配置中调整）',
      subnet: '建议按 /24 网段拆分扫描，避免单次文件过大',
      windows: 'Windows 环境下 $(date ...) 不可用，请手动命名文件',
      filtered: '如果大量端口显示 filtered，考虑降低扫描速度（-T3 或 -T2）',
    },
  },
}
