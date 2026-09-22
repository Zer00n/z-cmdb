/** Facility management API wrappers */
import request from './request'
import type {
  DatacenterRacks,
  DatacenterSummary,
  Rack,
  RackCreatePayload,
  RackElevation,
  RackUpdatePayload,
} from '@/types/facility'

/** All datacenters with capacity / unlocated summary */
export function fetchDatacenters(): Promise<DatacenterSummary[]> {
  return request.get('/api/facility/datacenters')
}

/** Racks and unlocated devices in one datacenter */
export function fetchDatacenterRacks(
  datacenter: string,
): Promise<DatacenterRacks> {
  return request.get(
    `/api/facility/datacenters/${encodeURIComponent(datacenter)}/racks`,
  )
}

/** Full rack elevation: devices, links and warnings */
export function fetchRackElevation(rackId: number): Promise<RackElevation> {
  return request.get(`/api/facility/racks/${rackId}/elevation`)
}

/** Add an empty rack */
export function createRack(data: RackCreatePayload): Promise<Rack> {
  return request.post('/api/facility/racks', data)
}

/** Edit rack metadata */
export function updateRack(
  rackId: number,
  data: RackUpdatePayload,
): Promise<Rack> {
  return request.patch(`/api/facility/racks/${rackId}`, data)
}
