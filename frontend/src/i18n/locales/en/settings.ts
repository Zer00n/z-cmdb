export default {
  title: 'System Config',
  subtitle: 'Runtime parameters · Changes take effect immediately, no restart needed',
  reset: 'Reset',
  save: 'Save Config',
  saveSuccess: 'Config saved',
  groups: {
    scan: {
      title: 'Scan & Assets',
      desc: 'Scan batch and asset management parameters',
    },
    session: {
      title: 'Session & Security',
      desc: 'User session timeout settings',
    },
    llm: {
      title: 'LLM Config',
      desc: 'Large language model configuration for topology generation',
    },
    language: {
      title: 'Language',
      desc: 'Interface language settings',
      label: 'Display Language',
    },
  },
  labels: {
    missing_threshold: 'Disappearance Protection Threshold',
    upload_max_size_mb: 'Upload File Limit (MB)',
    asset_no_prefix: 'Asset Number Prefix',
    session_timeout_minutes: 'Session Timeout (min)',
    llm_provider: 'LLM Provider',
    llm_api_key: 'API Key',
    llm_model: 'Model Name',
    llm_base_url: 'API URL',
    llm_ollama_model: 'Local Model Name',
    llm_route_core_to_local: 'Route Core Assets to Local',
    llm_cloud_enabled: 'Allow Cloud LLM',
  },
  placeholders: {
    missing_threshold: 'Default 3, mark offline after N consecutive missed scans',
    upload_max_size_mb: 'Default 50',
    asset_no_prefix: 'Default CMDB',
    session_timeout_minutes: 'Default 30',
    llm_api_key: 'Encrypted storage, leave blank to skip update',
    llm_model: 'e.g., deepseek-chat / gpt-4o / claude-3-5-sonnet',
    llm_base_url: 'e.g., https://api.deepseek.com/v1',
    llm_ollama_model: 'Default qwen2.5',
  },
  providers: {
    custom: 'Custom',
    local: 'Local (Ollama)',
  },
  hint: 'API Key and other sensitive fields are stored with <b>Fernet encryption</b>; displayed values are masked.',
}
