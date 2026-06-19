/**
 * 资产总览常量（单源）
 * 网络区域配色 / 危险端口定义等，供 Dashboard 与未来复用方共享
 */

/** 网络区域 → 显示名 */
const ZONE_LABELS: Record<string, string> = {
  dmz: 'DMZ', intranet: '内网', office: '办公网', management: '管理网',
  aliyun: '阿里云', tencent: '腾讯云', huawei: '华为云', aws: 'AWS',
  azure: 'Azure', gcp: 'GCP', other_cloud: '其他云', other: '其他',
}
export function zoneLabel(z: string): string {
  return ZONE_LABELS[z] || z
}

/** 网络区域 → 主题色 */
export const ZONE_COLORS: Record<string, string> = {
  intranet: '#2563EB', office: '#0E7490', dmz: '#B45309', management: '#6D28D9',
  aliyun: '#EA580C', tencent: '#0891B2', huawei: '#CF0A2C', aws: '#FF9900',
  azure: '#0078D4', gcp: '#4285F4', other_cloud: '#94A3B8', other: '#94A3B8',
}

/** 资产类型 / 重要性 / 操作系统 调色板 */
export const TYPE_COLORS = ['#2563EB', '#0E7490', '#EA580C', '#6D28D9', '#94A3B8']
export const IMP_COLORS = ['#DC2626', '#D97706', '#94A3B8']
export const OS_COLORS = ['#2563EB', '#0E7490', '#94A3B8']

/** 危险端口集合（模块级一次创建） */
export const DANGEROUS_PORTS = new Set<number>([
  21, 22, 23, 135, 139, 445, 1433, 1521, 2375, 3306,
  3389, 5432, 5984, 6379, 8080, 8888, 9200, 11211, 27017,
])
