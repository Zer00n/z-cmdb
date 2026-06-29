export default {
  // ── 首次 Setup ──────────────────────────────────────────────
  setup: {
    title: '初始化数据库加密',
    subtitle: '首次部署需设置管理员口令并生成恢复码',
    username: '管理员用户名',
    usernamePlaceholder: '默认 admin',
    password: '设置管理员口令',
    passwordPlaceholder: '≥12 位，含大小写 + 数字 + 特殊字符',
    passwordHint: '留空则系统随机生成',
    submit: '初始化并生成恢复码',
    submitting: '正在初始化…',
  },

  // ── 恢复码展示 ──────────────────────────────────────────────
  recovery: {
    title: '恢复码已生成',
    warning: '恢复码仅展示一次，是所有口令丢失时的唯一出路。请立即离线保存！',
    code: '恢复码',
    adminPassword: '管理员口令（系统生成）',
    username: '用户名',
    copied: '已复制到剪贴板',
    enter: '进入系统',
  },

  // ── 解锁 ────────────────────────────────────────────────────
  unlock: {
    title: '数据库已锁定',
    subtitle: '请输入管理员口令或恢复码解锁',
    tabPassword: '口令解锁',
    tabRecovery: '恢复码解锁',
    username: '用户名',
    usernamePlaceholder: '管理员用户名',
    password: '口令',
    passwordPlaceholder: '输入管理员口令',
    recoveryCode: '恢复码',
    recoveryCodePlaceholder: '输入恢复码',
    submit: '解 锁',
    submitting: '正在解锁…',
    success: '解锁成功',
  },

  // ── 状态 ────────────────────────────────────────────────────
  status: {
    locked: '已锁定',
    unlocked: '已解锁',
    needsSetup: '需要初始化',
  },

  // ── 校验 ────────────────────────────────────────────────────
  validation: {
    usernameRequired: '请输入用户名',
    passwordRequired: '请输入口令',
    recoveryRequired: '请输入恢复码',
    passwordPolicy: '≥12 位，含大小写 + 数字 + 特殊字符',
  },

  // ── 通用 ────────────────────────────────────────────────────
  brand: 'Z-CMDB 数据加密',
}
