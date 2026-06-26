/**
 * Deterministic template layout algorithm for project topology.
 *
 * Pure function: TopologyResponse → Vue Flow Node[] + Edge[]
 *
 * Layout rules:
 * 1. Group units by host_id
 * 2. Sort hosts by topological order (upstream left, downstream right)
 * 3. Stack units vertically within each host group
 * 4. Deterministic: same input → same coordinates every time
 */
import type { Node, Edge } from '@vue-flow/core'
import type { TopologyResponse, TopologyHost, TopologyUnit, TopologyDependency } from '@/types/project'

// ── Layout constants ───────────────────────────────────────────

const HOST_GROUP_WIDTH = 280
const HOST_GAP_X = 80
const GROUP_PADDING_X = 16
const GROUP_PADDING_TOP = 52   // space for host header
const GROUP_PADDING_BOTTOM = 16
const UNIT_WIDTH = 248         // HOST_GROUP_WIDTH - 2 * GROUP_PADDING_X
const UNIT_HEIGHT = 80
const UNIT_GAP_Y = 12

// ── Color map for unit type left bar ───────────────────────────

export const UNIT_TYPE_COLORS: Record<string, string> = {
  k8s_workload: '#3B82F6',
  docker: '#10B981',
  vm_app: '#F59E0B',
  host_process: '#8B5CF6',
}

// ── Helpers ────────────────────────────────────────────────────

/**
 * Topological sort of units by dependency direction.
 * Returns unit IDs in order: upstream first, downstream last.
 * Falls back to ID sort when no edges exist.
 */
function topologicalSortUnitIds(
  units: TopologyUnit[],
  deps: TopologyDependency[],
): string[] {
  if (deps.length === 0) {
    return [...units].map(u => u.id).sort()
  }

  const adj = new Map<string, string[]>()
  const inDegree = new Map<string, number>()

  for (const u of units) {
    adj.set(u.id, [])
    inDegree.set(u.id, 0)
  }

  for (const d of deps) {
    if (adj.has(d.source) && inDegree.has(d.target)) {
      adj.get(d.source)!.push(d.target)
      inDegree.set(d.target, (inDegree.get(d.target) || 0) + 1)
    }
  }

  // Kahn's algorithm
  const queue: string[] = []
  for (const [id, deg] of inDegree) {
    if (deg === 0) queue.push(id)
  }
  queue.sort() // deterministic tie-breaking

  const result: string[] = []
  while (queue.length > 0) {
    const node = queue.shift()!
    result.push(node)
    const neighbors = adj.get(node) || []
    neighbors.sort()
    for (const nb of neighbors) {
      const newDeg = (inDegree.get(nb) || 1) - 1
      inDegree.set(nb, newDeg)
      if (newDeg === 0) queue.push(nb)
    }
    queue.sort()
  }

  // Append any nodes not reached (isolated or in cycles) by ID
  const visited = new Set(result)
  for (const u of units) {
    if (!visited.has(u.id)) result.push(u.id)
  }

  return result
}

/**
 * Sort hosts by the order their units appear in the topological sort.
 * Host with the earliest upstream unit comes first.
 * Falls back to host identifier sort when no dependencies exist.
 */
function sortHostsByTopology(
  hosts: TopologyHost[],
  units: TopologyUnit[],
  topoOrder: string[],
): TopologyHost[] {
  if (hosts.length <= 1) return [...hosts]

  // Map unit_id → host_id
  const unitToHost = new Map<string, string>()
  for (const u of units) {
    if (u.host_id) unitToHost.set(u.id, u.host_id)
  }

  // For each host, find the earliest position in topo order
  const hostFirstPos = new Map<string, number>()
  for (let i = 0; i < topoOrder.length; i++) {
    const hostId = unitToHost.get(topoOrder[i])
    if (hostId && !hostFirstPos.has(hostId)) {
      hostFirstPos.set(hostId, i)
    }
  }

  // Hosts with no units in topo order get a high position
  const maxPos = topoOrder.length
  return [...hosts].sort((a, b) => {
    const posA = hostFirstPos.get(a.id) ?? maxPos
    const posB = hostFirstPos.get(b.id) ?? maxPos
    if (posA !== posB) return posA - posB
    // Deterministic tie-breaking by host identifier
    const nameA = a.ip_address || a.name || a.id
    const nameB = b.ip_address || b.name || b.id
    return nameA.localeCompare(nameB)
  })
}

// ── Main layout function ───────────────────────────────────────

export interface TopologyLayoutResult {
  nodes: Node[]
  edges: Edge[]
}

export function computeTopologyLayout(topo: TopologyResponse): TopologyLayoutResult {
  const { hosts, units, dependencies } = topo

  if (hosts.length === 0 && units.length === 0) {
    return { nodes: [], edges: [] }
  }

  // 1. Topological sort of units
  const topoOrder = topologicalSortUnitIds(units, dependencies)

  // 2. Sort hosts by topological order
  const sortedHosts = sortHostsByTopology(hosts, units, topoOrder)

  // 3. Group units by host_id
  const unitsByHost = new Map<string, TopologyUnit[]>()
  const orphanUnits: TopologyUnit[] = [] // units without a host

  for (const u of units) {
    if (u.host_id) {
      if (!unitsByHost.has(u.host_id)) unitsByHost.set(u.host_id, [])
      unitsByHost.get(u.host_id)!.push(u)
    } else {
      orphanUnits.push(u)
    }
  }

  // Sort units within each host by topo order
  const topoRank = new Map<string, number>()
  topoOrder.forEach((id, i) => topoRank.set(id, i))

  for (const [, hostUnits] of unitsByHost) {
    hostUnits.sort((a, b) => (topoRank.get(a.id) ?? 999) - (topoRank.get(b.id) ?? 999))
  }

  // 4. Compute positions and build nodes
  const nodes: Node[] = []
  let currentX = 0

  for (let hi = 0; hi < sortedHosts.length; hi++) {
    const host = sortedHosts[hi]
    const hostUnits = unitsByHost.get(host.id) || []
    const groupHeight = GROUP_PADDING_TOP + hostUnits.length * (UNIT_HEIGHT + UNIT_GAP_Y) - UNIT_GAP_Y + GROUP_PADDING_BOTTOM

    // Host group node
    nodes.push({
      id: `host-${host.id}`,
      type: 'hostGroup',
      position: { x: currentX, y: 0 },
      style: { width: `${HOST_GROUP_WIDTH}px`, height: `${groupHeight}px` },
      data: {
        host,
        unitCount: hostUnits.length,
      },
    })

    // Unit nodes inside this host group
    for (let ui = 0; ui < hostUnits.length; ui++) {
      const unit = hostUnits[ui]
      nodes.push({
        id: `unit-${unit.id}`,
        type: 'unit',
        parentNode: `host-${host.id}`,
        position: {
          x: GROUP_PADDING_X,
          y: GROUP_PADDING_TOP + ui * (UNIT_HEIGHT + UNIT_GAP_Y),
        },
        style: { width: `${UNIT_WIDTH}px`, height: `${UNIT_HEIGHT}px` },
        data: {
          unit,
          color: UNIT_TYPE_COLORS[unit.type] || '#94A3B8',
        },
        extent: 'parent',
      })
    }

    currentX += HOST_GROUP_WIDTH + HOST_GAP_X
  }

  // Handle orphan units (no host) — render them in a virtual group at the end
  if (orphanUnits.length > 0) {
    const groupHeight = GROUP_PADDING_TOP + orphanUnits.length * (UNIT_HEIGHT + UNIT_GAP_Y) - UNIT_GAP_Y + GROUP_PADDING_BOTTOM

    nodes.push({
      id: 'host-orphan',
      type: 'hostGroup',
      position: { x: currentX, y: 0 },
      style: { width: `${HOST_GROUP_WIDTH}px`, height: `${groupHeight}px` },
      data: {
        host: { id: 'orphan', name: '未分配主机', ip_address: null, monthly_cost: 0, shared: false, shares: [] },
        unitCount: orphanUnits.length,
      },
    })

    for (let ui = 0; ui < orphanUnits.length; ui++) {
      const unit = orphanUnits[ui]
      nodes.push({
        id: `unit-${unit.id}`,
        type: 'unit',
        parentNode: 'host-orphan',
        position: {
          x: GROUP_PADDING_X,
          y: GROUP_PADDING_TOP + ui * (UNIT_HEIGHT + UNIT_GAP_Y),
        },
        style: { width: `${UNIT_WIDTH}px`, height: `${UNIT_HEIGHT}px` },
        data: {
          unit,
          color: UNIT_TYPE_COLORS[unit.type] || '#94A3B8',
        },
        extent: 'parent',
      })
    }
  }

  // 5. Build dependency edges
  const edges: Edge[] = dependencies.map(dep => ({
    id: `edge-${dep.id}`,
    source: `unit-${dep.source}`,
    target: `unit-${dep.target}`,
    type: 'smoothstep',
    animated: false,
    label: dep.type,
    style: dep.in_cycle
      ? { stroke: '#F59E0B', strokeWidth: 2, strokeDasharray: '6 3' }
      : { stroke: '#64748B', strokeWidth: 1.5 },
    labelStyle: { fontSize: '11px', fontFamily: 'var(--font-mono)', fill: dep.in_cycle ? '#D97706' : '#64748B' },
    labelBgStyle: { fill: 'white', fillOpacity: 0.9 },
    labelBgPadding: [4, 2] as [number, number],
    markerEnd: 'arrowclosed',
  }))

  return { nodes, edges }
}
