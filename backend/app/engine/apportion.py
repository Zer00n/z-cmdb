"""
V0.6 deterministic apportion engine

Pure function, no DB dependency.  Takes plain dataclasses as input
and returns project-level cost allocations plus detail breakdowns.

Algorithm matches PRD section 5.1 exactly.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Sequence

TOLERANCE = 1e-6


class ConservationViolationError(Exception):
    """Raised when cost shares on a host do not sum to 1.0 within tolerance."""

    def __init__(self, host_id: str, allocated: float, idle_share: float) -> None:
        self.host_id = host_id
        self.allocated = allocated
        self.idle_share = idle_share
        super().__init__(
            f"Conservation violated on host {host_id}: "
            f"allocated={allocated:.8f} + idle={idle_share:.8f} "
            f"!= 1.0 (diff={abs(allocated + idle_share - 1.0):.8f})"
        )


@dataclass
class HostInput:
    id: str
    cpu_total: float
    mem_total: float
    monthly_cost: float


@dataclass
class PlacementInput:
    id: str
    unit_id: str
    host_id: str
    cpu_request: float
    mem_request: float
    instances: int


@dataclass
class UnitInput:
    id: str
    project_id: str | None


@dataclass
class PolicyInput:
    denominator: str    # "allocatable" | "sum_requests"
    weight_mode: str    # "mem" | "cpu" | "weighted" | "max"
    weight_cpu: float
    weight_mem: float
    idle_cost: str      # "unallocated_bucket" | "force_allocate"


@dataclass
class DetailLine:
    unit_id: str
    host_id: str
    share: float
    amount: float


@dataclass
class ApportionResult:
    project_cost: dict[str, float] = field(default_factory=dict)
    bucket_idle: float = 0.0
    detail: list[DetailLine] = field(default_factory=list)


def combine(cpu_share: float, mem_share: float, policy: PolicyInput) -> float:
    """Combine CPU and memory shares into a single share value per weight_mode."""
    mode = policy.weight_mode
    if mode == "mem":
        return mem_share
    if mode == "cpu":
        return cpu_share
    if mode == "max":
        return max(cpu_share, mem_share)
    # weighted
    return policy.weight_cpu * cpu_share + policy.weight_mem * mem_share


def apportion(
    hosts: Sequence[HostInput],
    placements: Sequence[PlacementInput],
    units: Sequence[UnitInput],
    policy: PolicyInput,
) -> ApportionResult:
    """
    Deterministic cost apportionment engine.

    For each host, computes per-unit cost shares based on the active policy,
    distributes costs to projects, and handles idle/unallocated costs.

    Raises ConservationViolationError if shares do not conserve.
    """
    units_by_id = {u.id: u for u in units}

    # Group placements by host
    placements_by_host: dict[str, list[PlacementInput]] = defaultdict(list)
    for p in placements:
        placements_by_host[p.host_id].append(p)

    project_cost: dict[str, float] = defaultdict(float)
    bucket_idle = 0.0
    detail: list[DetailLine] = []

    for h in hosts:
        ps = placements_by_host.get(h.id, [])
        if not ps:
            continue

        # Determine denominator
        if policy.denominator == "allocatable":
            denom_cpu = h.cpu_total
            denom_mem = h.mem_total
        else:  # sum_requests
            denom_cpu = sum(p.cpu_request * p.instances for p in ps)
            denom_mem = sum(p.mem_request * p.instances for p in ps)

        allocated = 0.0
        host_detail: list[tuple[str, float, float]] = []  # (unit_id, share, amount)

        for p in ps:
            used_cpu = p.cpu_request * p.instances
            used_mem = p.mem_request * p.instances

            cpu_share = (used_cpu / denom_cpu) if denom_cpu else 0.0
            mem_share = (used_mem / denom_mem) if denom_mem else 0.0

            share = combine(cpu_share, mem_share, policy)

            # v0.6: time_factor = 1.0 (simplified; function signature reserves param)
            tf = 1.0
            amount = h.monthly_cost * share * tf

            unit = units_by_id.get(p.unit_id)
            if unit and unit.project_id:
                project_cost[unit.project_id] += amount
            else:
                # Unclaimed unit cost goes to bucket
                bucket_idle += amount

            allocated += share * tf
            host_detail.append((p.unit_id, share, amount))
            detail.append(DetailLine(unit_id=p.unit_id, host_id=h.id, share=share, amount=amount))

        # Idle handling (only for allocatable denominator)
        idle_share = 0.0
        if policy.denominator == "allocatable":
            idle_share = max(0.0, 1.0 - allocated)
            idle_amount = h.monthly_cost * idle_share

            if policy.idle_cost == "unallocated_bucket":
                bucket_idle += idle_amount
            else:
                # force_allocate: redistribute idle proportionally to existing shares
                total_allocated_cost = h.monthly_cost * allocated
                if total_allocated_cost > 0:
                    for uid, share, amount in host_detail:
                        unit = units_by_id.get(uid)
                        if unit and unit.project_id and share > 0:
                            ratio = amount / total_allocated_cost
                            project_cost[unit.project_id] += idle_amount * ratio

        # Conservation assertion
        total = allocated + idle_share
        if abs(total - 1.0) > TOLERANCE:
            raise ConservationViolationError(h.id, allocated, idle_share)

    return ApportionResult(
        project_cost=dict(project_cost),
        bucket_idle=bucket_idle,
        detail=detail,
    )
