/**
 * Asset type → OS field filter policy
 * Used with AssetForm.vue's osFieldMode / visibleOsGroups derived state
 *
 * Design:
 *   - physical / virtual / cloud_server: show 7 mainstream groups (with "Other/Unknown" as fallback)
 *   - network_device: only show "Network Device" group
 *   - other: switch to input mode, OS field does not show group dropdown
 */
import type { OsOptionGroup } from '@/constants/os-options'

export type OsFieldMode = 'select' | 'input'

/**
 * Mapping from asset type to visible OS group label whitelist.
 * 'other' uses input mode, so it is not in this table.
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
 * Determine OS field rendering mode based on asset type.
 * Returns 'input' only for 'other'; everything else (including invalid values) returns 'select'.
 */
export function getOsFieldMode(assetType: string): OsFieldMode {
  return assetType === 'other' ? 'input' : 'select'
}

/**
 * Filter visible OS groups based on asset type.
 * - input mode → returns empty array
 * - select mode → filters by OS_GROUP_POLICY[assetType] whitelist; invalid assetType returns empty array
 *
 * Invariant: does not mutate the groups array, only returns a filtered shallow reference slice.
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
