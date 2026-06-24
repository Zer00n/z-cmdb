"""
V0.6 deterministic topology generation

Reads from DB (consuming_unit, placement, host_resource, unit_relation, billing_policy)
and returns a JSON-serializable dict matching the PRD section 6.1 contract.

Includes cycle detection for dependency edges.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.engine.apportion import (
    HostInput,
    PlacementInput,
    PolicyInput,
    UnitInput,
    apportion,
)
from app.models.billing_policy import BillingPolicy
from app.models.consuming_unit import ConsumingUnit
from app.models.host_resource import HostResource
from app.models.placement import Placement
from app.models.project import Project
from app.models.unit_relation import UnitRelation


def _detect_cycles(
    adj: dict[str, list[tuple[str, str]]],  # node → [(target, edge_id)]
) -> list[dict]:
    """
    Detect cycles in a directed graph using iterative DFS.

    Returns a list of cycle descriptions: {"edges": [...], "nodes": [...]}.
    """
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {node: WHITE for node in adj}
    parent: dict[str, str | None] = {}  # node → parent node
    edge_to: dict[str, str] = {}  # node → edge_id that led to this node
    cycles: list[dict] = []

    for start in list(adj.keys()):
        if color.get(start, WHITE) != WHITE:
            continue

        stack = [start]
        parent[start] = None

        while stack:
            node = stack[-1]
            if color.get(node, WHITE) == WHITE:
                color[node] = GRAY

            found_child = False
            for target, edge_id in adj.get(node, []):
                if color.get(target, WHITE) == GRAY:
                    # Found a back edge → cycle detected
                    cycle_edges = [edge_id]
                    cycle_nodes = [target, node]
                    cur = node
                    while cur != target and parent.get(cur) is not None:
                        cur = parent[cur]
                        cycle_nodes.append(cur)
                        if cur in edge_to:
                            cycle_edges.append(edge_to[cur])
                    cycle_nodes.reverse()
                    cycle_edges.reverse()
                    cycles.append({"edges": cycle_edges, "nodes": cycle_nodes})
                elif color.get(target, WHITE) == WHITE:
                    found_child = True
                    parent[target] = node
                    edge_to[target] = edge_id
                    stack.append(target)
                    break

            if not found_child:
                color[node] = BLACK
                stack.pop()

    return cycles


def generate_topology(db: Session, project_id: str) -> dict[str, Any]:
    """
    Generate deterministic topology data for a project.

    Returns JSON matching PRD §6.1 contract:
    {
        "project_id": str,
        "generated_at": str (ISO),
        "source": "cmdb_relation_db",
        "hosts": [...],
        "units": [...],
        "dependencies": [...],
        "cycles": [...]
    }
    """
    # 1. Fetch project
    project = db.get(Project, project_id)
    if not project:
        raise NotFoundError(f"Project {project_id} not found")

    # 2. Fetch units for this project
    units = (
        db.query(ConsumingUnit)
        .filter(ConsumingUnit.project_id == project_id)
        .order_by(ConsumingUnit.id)
        .all()
    )
    unit_ids = {u.id for u in units}

    # 3. Fetch current placements for each unit (latest observed_at per unit)
    placements = []
    for u in units:
        p = (
            db.query(Placement)
            .filter(Placement.unit_id == u.id)
            .order_by(Placement.observed_at.desc())
            .first()
        )
        if p:
            placements.append(p)

    # 4. Fetch hosts referenced by placements
    host_ids = {p.host_id for p in placements}
    hosts = []
    if host_ids:
        hosts = (
            db.query(HostResource)
            .filter(HostResource.id.in_(host_ids))
            .order_by(HostResource.id)
            .all()
        )
    hosts_by_id = {h.id: h for h in hosts}

    # 5. Get active policy for share computation
    policy_row = (
        db.query(BillingPolicy)
        .filter(BillingPolicy.is_active == 1)
        .first()
    )
    policy = PolicyInput(
        denominator=policy_row.denominator if policy_row else "allocatable",
        weight_mode=policy_row.weight_mode if policy_row else "mem",
        weight_cpu=policy_row.weight_cpu if policy_row else 0.5,
        weight_mem=policy_row.weight_mem if policy_row else 0.5,
        idle_cost=policy_row.idle_cost if policy_row else "unallocated_bucket",
    )

    # 6. Compute shares using the apportion engine
    #    We need all units that share these hosts (not just this project's)
    all_placement_units = set()
    for p in placements:
        all_placement_units.add(p.host_id)
    # Get all placements on these hosts (for share calculation)
    all_placements_on_hosts = (
        db.query(Placement)
        .filter(Placement.host_id.in_(host_ids))
        .all()
    ) if host_ids else []

    all_unit_ids_for_hosts = {p.unit_id for p in all_placements_on_hosts}
    all_units = (
        db.query(ConsumingUnit)
        .filter(ConsumingUnit.id.in_(all_unit_ids_for_hosts))
        .all()
    )

    apportion_input_hosts = []
    for h in hosts:
        apportion_input_hosts.append(HostInput(
            id=h.id, cpu_total=h.cpu_total,
            mem_total=h.mem_total, monthly_cost=h.monthly_cost,
        ))
    apportion_input_placements = [
        PlacementInput(
            id=p.id, unit_id=p.unit_id, host_id=p.host_id,
            cpu_request=p.cpu_request, mem_request=p.mem_request,
            instances=p.instances,
        )
        for p in all_placements_on_hosts
    ]
    apportion_input_units = [
        UnitInput(id=u.id, project_id=u.project_id)
        for u in all_units
    ]

    # Run apportion to get shares per host per unit
    result = apportion(apportion_input_hosts, apportion_input_placements,
                       apportion_input_units, policy)

    # Build shares per host
    host_shares: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for d in result.detail:
        host_shares[d.host_id][d.unit_id] = d.share

    # 7. Fetch dependency edges (unit_relation) involving project's units
    relations = (
        db.query(UnitRelation)
        .filter(
            (UnitRelation.source_unit_id.in_(unit_ids))
            | (UnitRelation.target_unit_id.in_(unit_ids))
        )
        .order_by(UnitRelation.id)
        .all()
    )

    # 8. Cycle detection
    adj: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for r in relations:
        adj[r.source_unit_id].append((r.target_unit_id, r.id))

    cycles = _detect_cycles(adj)
    cycled_edge_ids = set()
    for c in cycles:
        cycled_edge_ids.update(c["edges"])

    # 9. Build response
    # Hosts
    hosts_out = []
    for h in sorted(hosts, key=lambda x: x.id):
        h_shares = host_shares.get(h.id, {})
        # Check if host is shared across projects
        units_on_host = [
            uid for uid, share in h_shares.items() if share > 0
        ]
        projects_on_host = set()
        for uid in units_on_host:
            u = next((u for u in all_units if u.id == uid), None)
            if u and u.project_id:
                projects_on_host.add(u.project_id)
        shared = len(projects_on_host) > 1

        shares_out = []
        if shared:
            for uid in sorted(units_on_host):
                u = next((u for u in all_units if u.id == uid), None)
                if u and u.project_id:
                    shares_out.append({
                        "project_id": u.project_id,
                        "ratio": round(h_shares[uid], 6),
                    })

        hosts_out.append({
            "id": h.id,
            "monthly_cost": h.monthly_cost,
            "shared": shared,
            "shares": shares_out if shared else [],
        })

    # Units
    units_out = []
    for u in sorted(units, key=lambda x: x.id):
        # Find current placement
        p = next((p for p in placements if p.unit_id == u.id), None)
        runtime = None
        host_id = None
        if p:
            host_id = p.host_id
            runtime = {
                "instances": p.instances,
                "cpu": p.cpu_request,
                "mem": p.mem_request,
                "source": p.source,
                "observed_at": p.observed_at,
            }
        units_out.append({
            "id": u.id,
            "name": u.name,
            "type": u.type,
            "owner": u.owner,
            "environment": u.environment,
            "host_id": host_id,
            "runtime": runtime,
        })

    # Dependencies
    deps_out = []
    for r in sorted(relations, key=lambda x: x.id):
        deps_out.append({
            "id": r.id,
            "source": r.source_unit_id,
            "target": r.target_unit_id,
            "type": r.rel_type,
            "in_cycle": r.id in cycled_edge_ids,
        })

    return {
        "project_id": project_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "cmdb_relation_db",
        "hosts": hosts_out,
        "units": units_out,
        "dependencies": deps_out,
        "cycles": cycles,
    }
