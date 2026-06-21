"""
Topology routes
POST   /api/topology/generate    LLM generates initial draft
GET    /api/topology             Current topology
GET    /api/topology/versions    History version list
POST   /api/topology             Save new version
POST   /api/topology/{id}/rollback  Rollback to a version
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import AdminUser, AnyUser
from app.core.exceptions import TopologyNotFoundError, ValidationError
from app.models.config import SystemConfig
from app.models.topology import Topology
from app.services import audit_service, topology_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/topology", tags=["topology"])


class TopologyGenerateRequest(BaseModel):
    """Manually specify LLM parameters (optional; defaults read from system config)"""
    provider: str | None = None
    model: str | None = None


class TopologySaveRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    drawio_xml: str


class TopologyRead(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    version_no: str
    title: str | None
    description: str | None
    drawio_xml: str
    created_by: int | None
    created_at: datetime
    is_current: bool


def _get_llm_config(db: Session) -> dict:
    """Read LLM parameters from system config (api_key is automatically decrypted)"""
    from app.core.encryption import decrypt_value
    keys = ["llm_provider", "llm_api_key", "llm_model", "llm_base_url"]
    config = {}
    for key in keys:
        cfg = db.get(SystemConfig, key)
        value = cfg.value if cfg else ""
        # api_key decryption
        if key == "llm_api_key" and value:
            value = decrypt_value(value)
        config[key] = value
    return config


def _generate_version_no() -> str:
    """Generate version number: topo_YYYYMMDD_NNN"""
    from datetime import date
    return f"topo_{date.today().strftime('%Y%m%d')}_{int(datetime.now(timezone.utc).timestamp()) % 1000:03d}"


@router.post("/generate")
def generate_topology(
    body: TopologyGenerateRequest,
    request: Request,
    current_user: AdminUser = None,
    db: Session = Depends(get_db),
) -> dict:
    """LLM generates a topology initial draft"""
    llm_config = _get_llm_config(db)

    provider = body.provider or llm_config.get("llm_provider", "")
    model = body.model or llm_config.get("llm_model", "")
    api_key = llm_config.get("llm_api_key", "")
    base_url = llm_config.get("llm_base_url", "")

    if not provider:
        raise ValidationError("LLM provider not configured. Please set it in system configuration.")

    result = topology_service.generate_topology(
        db=db,
        user=current_user,  # type: ignore[arg-type]
        provider_name=provider,
        api_key=api_key,
        base_url=base_url,
        model=model,
    )

    audit_service.log_from_request(
        db, request, action_type="LLM_CALL", user=current_user,  # type: ignore[arg-type]
        target_type="topology", details={"provider": provider, "model": model},
    )
    db.commit()
    return result


@router.get("", response_model=TopologyRead | None)
def get_current_topology(
    _current_user: AnyUser = None,
    db: Session = Depends(get_db),
) -> TopologyRead | None:
    """Get current topology"""
    stmt = select(Topology).where(Topology.is_current == True).limit(1)
    topo = db.scalar(stmt)
    if topo is None:
        return None
    return topo  # type: ignore[return-value]


@router.get("/versions")
def list_versions(
    _current_user: AnyUser = None,
    db: Session = Depends(get_db),
) -> list[dict]:
    """History version list (excluding XML content)"""
    stmt = select(Topology).order_by(Topology.created_at.desc()).limit(50)
    topos = list(db.scalars(stmt).all())
    return [
        {
            "id": t.id,
            "version_no": t.version_no,
            "title": t.title,
            "created_at": t.created_at.isoformat(),
            "is_current": t.is_current,
        }
        for t in topos
    ]


@router.post("", response_model=TopologyRead, status_code=201)
def save_topology(
    body: TopologySaveRequest,
    request: Request,
    current_user: AdminUser = None,
    db: Session = Depends(get_db),
) -> TopologyRead:
    """Save new version"""
    # Clear current version flag
    stmt = select(Topology).where(Topology.is_current == True)
    current = db.scalar(stmt)
    if current:
        current.is_current = False

    topo = Topology(
        version_no=_generate_version_no(),
        title=body.title,
        description=body.description,
        drawio_xml=body.drawio_xml,
        created_by=current_user.id if current_user else None,  # type: ignore[union-attr]
        is_current=True,
    )
    db.add(topo)

    audit_service.log_from_request(
        db, request, action_type="CREATE", user=current_user,  # type: ignore[arg-type]
        target_type="topology", target_id=topo.version_no,
    )
    db.commit()
    db.refresh(topo)
    return topo  # type: ignore[return-value]


@router.post("/{topo_id}/rollback", response_model=TopologyRead)
def rollback_topology(
    topo_id: int,
    request: Request,
    current_user: AdminUser = None,
    db: Session = Depends(get_db),
) -> TopologyRead:
    """Rollback to a version"""
    target = db.get(Topology, topo_id)
    if target is None:
        raise TopologyNotFoundError(f"Topology version {topo_id} not found")

    # Clear current version
    stmt = select(Topology).where(Topology.is_current == True)
    current = db.scalar(stmt)
    if current:
        current.is_current = False

    target.is_current = True

    audit_service.log_from_request(
        db, request, action_type="UPDATE", user=current_user,  # type: ignore[arg-type]
        target_type="topology", target_id=topo_id,
        details={"action": "rollback", "version": target.version_no},
    )
    db.commit()
    return target  # type: ignore[return-value]
