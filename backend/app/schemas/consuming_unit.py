"""
V0.6 consuming unit / placement / unit_relation Pydantic v2 schemas
"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# ── ConsumingUnit ─────────────────────────────────────────────────

ConsumingUnitType = Literal["k8s_workload", "docker", "vm_app", "host_process"]
EnvironmentType = Literal["prod", "staging", "dev"]


class ConsumingUnitRead(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    project_id: str | None
    name: str
    type: str
    owner: str | None
    environment: str | None
    created_at: datetime
    updated_at: datetime


class ConsumingUnitPatch(BaseModel):
    """Strict allowlist: only stable fields may be edited"""
    name: str | None = Field(None, min_length=1, max_length=200)
    type: ConsumingUnitType | None = None
    owner: str | None = Field(None, max_length=100)
    environment: EnvironmentType | None = None


class ConsumingUnitCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    type: ConsumingUnitType
    owner: str | None = Field(None, max_length=100)
    environment: EnvironmentType | None = None
    project_id: str = Field(..., min_length=1, description="Target project ID")


# ── Placement (read-only) ────────────────────────────────────────

class PlacementRead(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    unit_id: str
    host_id: str
    cpu_request: float
    mem_request: float
    instances: int
    source: str | None
    observed_at: str


class PlacementCreate(BaseModel):
    host_id: str = Field(..., min_length=1, description="Target host ID")
    cpu_request: float = Field(..., gt=0, description="CPU cores requested")
    mem_request: float = Field(..., gt=0, description="Memory in MB requested")
    instances: int = Field(1, ge=1, le=1000)
    source: str = Field("manual", pattern=r"^(k8s|agent|manual)$")


# ── UnitRelation ─────────────────────────────────────────────────

RelType = Literal["HTTP", "SQL", "cache", "mq", "depends"]


class RelationCreate(BaseModel):
    source_unit_id: str = Field(..., min_length=1)
    target_unit_id: str = Field(..., min_length=1)
    rel_type: RelType


class RelationRead(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    source_unit_id: str
    target_unit_id: str
    rel_type: str
    source: str
    created_at: datetime
