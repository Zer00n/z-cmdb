/**
 * 资产类型 → 操作系统字段过滤策略
 * 配合 AssetForm.vue 的 osFieldMode / visibleOsGroups 派生使用
 *
 * 设计：
 *   - physical / virtual / cloud_server: 显示 7 个主流分组（含"其他/未知"作兜底）
 *   - network_device: 仅显示"网络设备"分组
 *   - other: 切换为 input 模式，OS 字段不显示分组下拉
 */
import type { OsOptionGroup } from '@/constants/os-options'

export type OsFieldMode = 'select' | 'input'

/**
 * 资产类型到可见 OS 分组 label 白名单的映射。
 * 'other' 走 input 模式，故不在此表中。
 */
export const OS_GROUP_POLICY: Record<'physical' | 'virtual' | 'network_device' | 'cloud_server', string[]> = {
  physical: [
    'Linux · 主流发行版',
    'Linux · 国产化',
    'Windows Server',
    'Windows 桌面',
    'macOS',
    'Unix 与虚拟化平台',
    '其他/未知',
  ],
  virtual: [
    'Linux · 主流发行版',
    'Linux · 国产化',
    'Windows Server',
    'Windows 桌面',
    'macOS',
    'Unix 与虚拟化平台',
    '其他/未知',
  ],
  cloud_server: [
    'Linux · 主流发行版',
    'Linux · 国产化',
    'Windows Server',
    'Windows 桌面',
    'macOS',
    'Unix 与虚拟化平台',
    '其他/未知',
  ],
  network_device: ['网络设备'],
}

/**
 * 根据资产类型决定 OS 字段渲染模式。
 * 仅在 'other' 时返回 'input'，其余（含非法值）一律 'select'。
 */
export function getOsFieldMode(assetType: string): OsFieldMode {
  return assetType === 'other' ? 'input' : 'select'
}

/**
 * 根据资产类型过滤可见的 OS 分组。
 * - input 模式 → 返回空数组
 * - select 模式 → 按 OS_GROUP_POLICY[assetType] 白名单过滤；非法 assetType 返回空数组
 *
 * 守恒：不修改 groups 数组，仅返回过滤后的浅引用切片。
 */
export function filterVisibleOsGroups(
  assetType: string,
  groups: OsOptionGroup[],
): OsOptionGroup[] {
  if (getOsFieldMode(assetType) === 'input') return []
  const allowed = OS_GROUP_POLICY[assetType as keyof typeof OS_GROUP_POLICY]
  if (!allowed) return []
  return groups.filter((g) => allowed.includes(g.label))
}
