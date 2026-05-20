/**
 * 应用大类选项
 * v2.5: 前端引导，后端不强约束
 *
 * 使用：
 *   import { APP_CATEGORIES } from '@/constants/app-categories'
 *
 * 在 el-select 上开启 filterable + allow-create 支持自由输入。
 */

export interface AppCategoryOption {
  value: string
  label: string
}

export const APP_CATEGORIES: AppCategoryOption[] = [
  { value: 'web_server', label: 'Web 服务器（Nginx / Apache / IIS）' },
  { value: 'database', label: '数据库（MySQL / PostgreSQL / Oracle / MSSQL / MongoDB / Redis）' },
  { value: 'app_server', label: '应用服务器（Tomcat / JBoss / Node.js）' },
  { value: 'message_queue', label: '消息队列（Kafka / RabbitMQ / RocketMQ）' },
  { value: 'cache', label: '缓存（Redis / Memcached）' },
  { value: 'search', label: '搜索引擎（Elasticsearch / OpenSearch）' },
  { value: 'monitor', label: '监控（Zabbix / Prometheus / Grafana）' },
  { value: 'devops', label: 'DevOps（Jenkins / GitLab / Harbor）' },
  { value: 'security', label: '安全（堡垒机 / WAF / 防病毒）' },
  { value: 'business_app', label: '业务系统（自研 / 第三方）' },
  { value: 'other', label: '其他' },
]

/** 根据 value 获取 label */
export function getCategoryLabel(value: string | null): string {
  if (!value) return '-'
  const found = APP_CATEGORIES.find((c) => c.value === value)
  return found ? found.label : value
}
