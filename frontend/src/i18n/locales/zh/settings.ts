export default {
  title: '系统配置',
  subtitle: '调整运行时参数 · 配置项立即生效，无需重启服务',
  reset: '重置',
  save: '保存配置',
  saveSuccess: '配置已保存',
  groups: {
    scan: {
      title: '扫描与资产',
      desc: '扫描批次和资产管理相关参数',
    },
    session: {
      title: '会话与安全',
      desc: '用户会话超时设置',
    },
    llm: {
      title: 'LLM 配置',
      desc: '拓扑图生成所用的大语言模型配置',
    },
    language: {
      title: '语言设置',
      desc: '界面语言设置',
      label: '显示语言',
    },
  },
  labels: {
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
  },
  placeholders: {
    missing_threshold: '默认 3，连续未扫到 N 次后标记离线',
    upload_max_size_mb: '默认 50',
    asset_no_prefix: '默认 CMDB',
    session_timeout_minutes: '默认 30',
    llm_api_key: '加密存储，留空则不更新',
    llm_model: '例如 deepseek-chat / gpt-4o / claude-3-5-sonnet',
    llm_base_url: '例如 https://api.deepseek.com/v1',
    llm_ollama_model: '默认 qwen2.5',
  },
  providers: {
    custom: '自定义',
    local: '本地 (Ollama)',
  },
  hint: 'API Key 等敏感字段在数据库中以 <b>Fernet 加密</b>方式存储；显示时已脱敏。',
}
