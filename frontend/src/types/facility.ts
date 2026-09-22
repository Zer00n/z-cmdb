/** Facility (datacenter / rack / rack elevation) type definitions */

export interface Rack {
  id: number
  datacenter: string | null
  name: string
  u_height: number
  room: string | null
  row_label: string | null
  col_label: string | null
  description: string | null
}

export interface RackCreatePayload {
  datacenter?: string | null
  name: string
  u_height?: number
  room?: string | null
  row_label?: string | null
  col_label?: string | null
  description?: string | null
}

export interface RackUpdatePayload {
  datacenter?: string | null
  name?: string
  u_height?: number
  room?: string | null
  row_label?: string | null
  col_label?: string | null
  description?: string | null
}

export interface ConnectedSwitch {
  id: number
  asset_no: string
  hostname: string | null
  asset_type: string
}

export interface DeviceInterface {
  id: number
  name: string | null
  mac_address: string | null
  ip_address: string | null
  role: string
  vlan_id: number | null
  bond_master: string | null
  is_primary: boolean
  connected_asset_id: number | null
  connected_port: string | null
  connected_switch: ConnectedSwitch | null
  source: 'port' | 'asset'
}

export interface ElevationDevice {
  id: number
  asset_no: string
  hostname: string | null
  asset_type: string
  importance: string
  status: string
  u_start: number | null
  u_height: number | null
  interfaces: DeviceInterface[]
}

export interface RackWarning {
  code: 'out_of_range' | 'overlap' | 'missing_u_start'
  message: string
  asset_id: number | null
}

export interface RackElevation extends Rack {
  devices: ElevationDevice[]
  warnings: RackWarning[]
}

export interface RackSummary {
  id: number
  name: string
  u_height: number
  device_count: number
  used_u: number
  utilization: number
}

export interface UnlocatedAsset {
  id: number
  asset_no: string
  hostname: string | null
  ip_address: string
  reason: 'no_rack' | 'no_u_start'
}

export interface DatacenterRacks {
  datacenter: string
  racks: RackSummary[]
  unlocated: UnlocatedAsset[]
}

export interface DatacenterSummary {
  datacenter: string
  rack_count: number
  device_count: number
  used_u: number
  total_u: number
  utilization: number
  unlocated_count: number
}
