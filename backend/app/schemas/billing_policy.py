"""
V0.6 billing policy / bill snapshot Pydantic v2 schemas
"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


# ── BillingPolicy ─────────────────────────────────────────────────

class BillingPolicyRead(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    version: int
    denominator: str
    weight_mode: str
    weight_cpu: float
    weight_mem: float
    idle_cost: str
    sampling: str
    freeze: int
    is_active: int
    created_at: datetime


class BillingPolicyUpdate(BaseModel):
    denominator: Literal["allocatable", "sum_requests"] = "allocatable"
    weight_mode: Literal["mem", "cpu", "weighted", "max"] = "mem"
    weight_cpu: float = Field(0.5, ge=0, le=1)
    weight_mem: float = Field(0.5, ge=0, le=1)
    idle_cost: Literal["unallocated_bucket", "force_allocate"] = "unallocated_bucket"
    sampling: Literal["daily", "hourly"] = "daily"

    @model_validator(mode="after")
    def check_weight_sum(self):
        if self.weight_mode == "weighted":
            total = self.weight_cpu + self.weight_mem
            if abs(total - 1.0) > 1e-6:
                raise ValueError(
                    f"weight_cpu + weight_mem must equal 1, got {total}"
                )
        return self


# ── BillSnapshot ──────────────────────────────────────────────────

class BillSnapshotRead(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    project_id: str
    period: str
    policy_version: int
    total_cost: float
    detail_json: str
    generated_at: datetime
    frozen: int


# ── Unclaimed ─────────────────────────────────────────────────────

class UnclaimedUnitRead(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    name: str
    type: str
    owner: str | None
    environment: str | None
    created_at: datetime
    # Denormalized: first placement info for display
    host_name: str | None = None
    cpu_request: float | None = None
    mem_request: float | None = None
    instances: int | None = None
    monthly_cost: float | None = None


class ZombieHostRead(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    name: str
    type: str
    cpu_total: float
    mem_total: float
    monthly_cost: float
    source: str | None
    created_at: datetime


class UnclaimedSummary(BaseModel):
    unclaimed_count: int
    zombie_count: int
    total_monthly_waste: float


class UnclaimedResponse(BaseModel):
    unclaimed_units: list[UnclaimedUnitRead]
    zombie_hosts: list[ZombieHostRead]
    summary: UnclaimedSummary
