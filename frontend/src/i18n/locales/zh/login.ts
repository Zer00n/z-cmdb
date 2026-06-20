export default {
  tag: '准确性优先 · 中小团队',
  title: '把内网资产\n真正搞清楚',
  desc: '手动 nmap 扫描 + 人工 review 兜底，确保资产数据可信。内置安全视角报表与可审计的 LLM 拓扑生成。',
  features: {
    accuracy: '人工兜底的资产准确性',
    desensitize: 'LLM 数据本地脱敏',
    rbac: '三权分立 + 不可变审计',
    exposure: '端口暴露面与影子资产分析',
  },
  stats: {
    setup: '从 0 到运行',
    roles: '权限角色',
    deploy: '单文件部署',
  },
  card: {
    title: '欢迎回来',
    subtitle: '请使用账号登录管理控制台',
  },
  form: {
    username: '用户名',
    password: '密码',
    usernameRequired: '请输入用户名',
    passwordRequired: '请输入密码',
    login: '登 录',
  },
  help: '忘记密码？请联系系统管理员重置',
  status: {
    serviceOk: '服务正常',
    rateLimit: '5 次 / 15 分钟',
    intranetOnly: '仅企业内网',
  },
  footer: 'Z-CMDB Lite · 内部运维平台',
}
