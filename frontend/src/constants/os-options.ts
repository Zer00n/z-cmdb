/**
 * OS dropdown options
 * Grouped by category, covering common server/desktop/network device OS
 *
 * Usage:
 *   import { osOptionGroups, allOsOptions } from '@/constants/os-options'
 *
 * Option values are "strings shown to user and stored in DB"; frontend does no mapping.
 * If customers use niche or domestic OS, enable filterable + allow-create on el-select for free input.
 */

export interface OsOption {
  label: string
  value: string
}

export interface OsOptionGroup {
  label: string
  options: OsOption[]
}

export const osOptionGroups: OsOptionGroup[] = [
  {
    label: 'Linux · 主流发行版',
    options: [
      { label: 'Ubuntu 24.04 LTS', value: 'Ubuntu 24.04 LTS' },
      { label: 'Ubuntu 22.04 LTS', value: 'Ubuntu 22.04 LTS' },
      { label: 'Ubuntu 20.04 LTS', value: 'Ubuntu 20.04 LTS' },
      { label: 'Debian 12', value: 'Debian 12' },
      { label: 'Debian 11', value: 'Debian 11' },
      { label: 'CentOS Stream 9', value: 'CentOS Stream 9' },
      { label: 'CentOS Stream 8', value: 'CentOS Stream 8' },
      { label: 'CentOS 7', value: 'CentOS 7' },
      { label: 'Red Hat Enterprise Linux 9', value: 'Red Hat Enterprise Linux 9' },
      { label: 'Red Hat Enterprise Linux 8', value: 'Red Hat Enterprise Linux 8' },
      { label: 'Rocky Linux 9', value: 'Rocky Linux 9' },
      { label: 'Rocky Linux 8', value: 'Rocky Linux 8' },
      { label: 'AlmaLinux 9', value: 'AlmaLinux 9' },
      { label: 'AlmaLinux 8', value: 'AlmaLinux 8' },
      { label: 'openSUSE Leap 15', value: 'openSUSE Leap 15' },
      { label: 'SUSE Linux Enterprise Server 15', value: 'SUSE Linux Enterprise Server 15' },
      { label: 'Fedora 40', value: 'Fedora 40' },
      { label: 'Alpine Linux', value: 'Alpine Linux' },
      { label: 'Arch Linux', value: 'Arch Linux' },
    ],
  },
  {
    label: 'Linux · 国产化',
    options: [
      { label: '麒麟 Kylin V10', value: '麒麟 Kylin V10' },
      { label: '银河麒麟 Kylin SP3', value: '银河麒麟 Kylin SP3' },
      { label: '统信 UOS V20', value: '统信 UOS V20' },
      { label: '欧拉 openEuler 22.03 LTS', value: '欧拉 openEuler 22.03 LTS' },
      { label: '欧拉 openEuler 24.03 LTS', value: '欧拉 openEuler 24.03 LTS' },
      { label: '龙蜥 Anolis OS 8', value: '龙蜥 Anolis OS 8' },
      { label: '中标麒麟 NeoKylin V7', value: '中标麒麟 NeoKylin V7' },
      { label: '深度 Deepin 23', value: '深度 Deepin 23' },
    ],
  },
  {
    label: 'Windows Server',
    options: [
      { label: 'Windows Server 2025', value: 'Windows Server 2025' },
      { label: 'Windows Server 2022', value: 'Windows Server 2022' },
      { label: 'Windows Server 2019', value: 'Windows Server 2019' },
      { label: 'Windows Server 2016', value: 'Windows Server 2016' },
      { label: 'Windows Server 2012 R2', value: 'Windows Server 2012 R2' },
    ],
  },
  {
    label: 'Windows 桌面',
    options: [
      { label: 'Windows 11 Pro', value: 'Windows 11 Pro' },
      { label: 'Windows 11 Enterprise', value: 'Windows 11 Enterprise' },
      { label: 'Windows 10 Pro', value: 'Windows 10 Pro' },
      { label: 'Windows 10 Enterprise', value: 'Windows 10 Enterprise' },
      { label: 'Windows 7 SP1', value: 'Windows 7 SP1' },
    ],
  },
  {
    label: 'macOS',
    options: [
      { label: 'macOS 15 Sequoia', value: 'macOS 15 Sequoia' },
      { label: 'macOS 14 Sonoma', value: 'macOS 14 Sonoma' },
      { label: 'macOS 13 Ventura', value: 'macOS 13 Ventura' },
      { label: 'macOS 12 Monterey', value: 'macOS 12 Monterey' },
    ],
  },
  {
    label: 'Unix 与虚拟化平台',
    options: [
      { label: 'VMware ESXi 8.0', value: 'VMware ESXi 8.0' },
      { label: 'VMware ESXi 7.0', value: 'VMware ESXi 7.0' },
      { label: 'Proxmox VE 8', value: 'Proxmox VE 8' },
      { label: 'FreeBSD 14', value: 'FreeBSD 14' },
      { label: 'OpenBSD 7', value: 'OpenBSD 7' },
      { label: 'IBM AIX 7', value: 'IBM AIX 7' },
      { label: 'Oracle Solaris 11', value: 'Oracle Solaris 11' },
    ],
  },
  {
    label: '网络设备',
    options: [
      { label: 'Cisco IOS', value: 'Cisco IOS' },
      { label: 'Cisco NX-OS', value: 'Cisco NX-OS' },
      { label: 'Huawei VRP', value: 'Huawei VRP' },
      { label: 'H3C Comware', value: 'H3C Comware' },
      { label: 'Juniper Junos', value: 'Juniper Junos' },
      { label: 'Fortinet FortiOS', value: 'Fortinet FortiOS' },
      { label: 'pfSense', value: 'pfSense' },
    ],
  },
  {
    label: '其他/未知',
    options: [
      { label: 'Other / Unknown', value: 'Other / Unknown' },
    ],
  },
]

/** Flatten all options for reverse lookup by value */
export const allOsOptions: OsOption[] = osOptionGroups.flatMap((g) => g.options)
