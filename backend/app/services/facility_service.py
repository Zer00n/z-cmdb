"""
Facility business logic: datacenter / rack aggregation, rack elevation.

Racks are auto-merged from an asset's (datacenter, rack) text pair; they can
also be added as empty cabinets. Everything is read aggregation except rack
CRUD; data volumes are small (single on-prem SQLite).
"""
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import (
    DuplicateError, NotFoundError, ValidationError,
)
from app.models.asset import Asset, NetworkInterface
from app.models.cost import AssetRelation
from app.models.rack import Rack
from app.schemas.facility import (
    ConnectedSwitch,
    DatacenterRacks,
    DatacenterSummary,
    DeviceInterface,
    ElevationDevice,
    RackCreate,
    RackElevation,
    RackSummary,
    RackUpdate,
    RackWarning,
    UnlocatedAsset,
)

logger = logging.getLogger(__name__)


def _norm(value: str | None) -> str | None:
    """Trim; empty string becomes None."""
    if value is None:
        return None
    value = value.strip()
    return value or None


# ── Auto merge of racks from asset text ──────────────────────────

def resolve_rack_id(
    db: Session, datacenter: str | None, rack_name: str | None
) -> int | None:
    """Find or create the rack for a (datacenter, rack name) pair.

    Returns None when rack name is missing (asset is not rack-located).
    """
    datacenter = _norm(datacenter)
    rack_name = _norm(rack_name)
    if rack_name is None:
        return None

    stmt = select(Rack).where(Rack.name == rack_name)
    if datacenter is None:
        stmt = stmt.where(Rack.datacenter.is_(None))
    else:
        stmt = stmt.where(Rack.datacenter == datacenter)
    rack = db.scalar(stmt)
    if rack is None:
        rack = Rack(datacenter=datacenter, name=rack_name, u_height=42)
        db.add(rack)
        db.flush()
        logger.info(
            "rack auto-created",
            extra={"rack_id": rack.id, "datacenter": datacenter,
                   "rack_name": rack_name},
        )
    return rack.id


# ── Rack CRUD ────────────────────────────────────────────────────

def create_rack(db: Session, data: RackCreate) -> Rack:
    datacenter = _norm(data.datacenter)
    name = _norm(data.name)
    if name is None:
        raise ValidationError("Rack name is required")
    if db.scalar(
        select(Rack).where(
            Rack.name == name,
            Rack.datacenter.is_(None) if datacenter is None else Rack.datacenter == datacenter,
        )
    ):
        raise DuplicateError(f"Rack {name} already exists in this datacenter")

    rack = Rack(
        datacenter=datacenter,
        name=name,
        u_height=data.u_height,
        room=_norm(data.room),
        row_label=_norm(data.row_label),
        col_label=_norm(data.col_label),
        description=data.description,
    )
    db.add(rack)
    db.flush()
    return rack


def update_rack(db: Session, rack_id: int, data: RackUpdate) -> Rack:
    rack = db.get(Rack, rack_id)
    if rack is None:
        raise NotFoundError(f"Rack {rack_id} not found")

    payload = data.model_dump(exclude_none=True)
    # Normalize text fields; a supplied (possibly empty) datacenter moves the rack
    for key in ("datacenter", "room", "row_label", "col_label"):
        if key in payload:
            payload[key] = _norm(payload[key])
    if "name" in payload:
        payload["name"] = _norm(payload["name"])
        if payload["name"] is None:
            raise ValidationError("Rack name cannot be empty")

    new_dc = payload.get("datacenter", rack.datacenter)
    new_name = payload.get("name", rack.name)
    conflict = db.scalar(
        select(Rack).where(
            Rack.id != rack.id,
            Rack.name == new_name,
            Rack.datacenter.is_(None) if new_dc is None else Rack.datacenter == new_dc,
        )
    )
    if conflict:
        raise DuplicateError(f"Rack {new_name} already exists in this datacenter")

    for key, value in payload.items():
        setattr(rack, key, value)
    db.flush()
    return rack


# ── Aggregation (everything loaded into memory; small scale) ─────

def _all_racks(db: Session) -> list[Rack]:
    return list(db.scalars(select(Rack).order_by(Rack.datacenter, Rack.name)).all())


def _all_assets(db: Session) -> list[Asset]:
    return list(db.scalars(select(Asset)).all())


def list_datacenters(db: Session) -> list[DatacenterSummary]:
    racks = _all_racks(db)
    assets = _all_assets(db)
    rack_by_id = {r.id: r for r in racks}

    # datacenter key -> rack ids / asset ids / used U
    dc_racks: dict[str | None, list[Rack]] = {}
    for rack in racks:
        dc_racks.setdefault(_norm(rack.datacenter), []).append(rack)

    dc_assets: dict[str | None, list[Asset]] = {}
    for asset in assets:
        rack = rack_by_id.get(asset.rack_id)
        key = _norm(rack.datacenter) if rack is not None else _norm(asset.datacenter)
        dc_assets.setdefault(key, []).append(asset)

    keys = set(dc_racks) | set(dc_assets)
    result: list[DatacenterSummary] = []
    for key in keys:
        dc_rack_list = dc_racks.get(key, [])
        dc_asset_list = dc_assets.get(key, [])
        rack_ids = {r.id for r in dc_rack_list}

        unlocated = [
            a for a in dc_asset_list
            if a.rack_id not in rack_ids or a.rack_u_start is None
        ]
        located = [a for a in dc_asset_list if a not in unlocated]
        used_u = sum(a.rack_u_height or 1 for a in located)
        total_u = sum(r.u_height for r in dc_rack_list)

        result.append(DatacenterSummary(
            datacenter=key or "",
            rack_count=len(dc_rack_list),
            device_count=len(dc_asset_list),
            used_u=used_u,
            total_u=total_u,
            utilization=round(used_u / total_u, 3) if total_u else 0.0,
            unlocated_count=len(unlocated),
        ))

    # Named datacenters first, then the unassigned bucket
    result.sort(key=lambda d: (d.datacenter == "", d.datacenter))
    return result


def list_datacenter_racks(db: Session, datacenter: str) -> DatacenterRacks:
    key = _norm(datacenter)
    racks = _all_racks(db)
    assets = _all_assets(db)

    dc_racks = [r for r in racks if _norm(r.datacenter) == key]
    rack_ids = {r.id for r in dc_racks}

    def _device_used_u(rack: Rack) -> int:
        devices = [
            a for a in assets
            if a.rack_id == rack.id and a.rack_u_start is not None
        ]
        return sum(a.rack_u_height or 1 for a in devices)

    summaries = [
        RackSummary(
            id=r.id,
            name=r.name,
            u_height=r.u_height,
            device_count=sum(1 for a in assets if a.rack_id == r.id),
            used_u=_device_used_u(r),
            utilization=round(_device_used_u(r) / r.u_height, 3),
        )
        for r in dc_racks
    ]
    summaries.sort(key=lambda s: s.name)

    unlocated: list[UnlocatedAsset] = []
    for asset in assets:
        in_dc = (
            asset.rack_id in rack_ids
            if asset.rack_id is not None
            else _norm(asset.datacenter) == key
        )
        if not in_dc:
            continue
        if asset.rack_id not in rack_ids:
            reason = "no_rack"
        elif asset.rack_u_start is None:
            reason = "no_u_start"
        else:
            continue
        unlocated.append(UnlocatedAsset(
            id=asset.id,
            asset_no=asset.asset_no,
            hostname=asset.hostname,
            ip_address=asset.ip_address,
            reason=reason,
        ))

    return DatacenterRacks(
        datacenter=key or "", racks=summaries, unlocated=unlocated
    )


# ── Rack elevation ───────────────────────────────────────────────

def get_rack_elevation(db: Session, rack_id: int) -> RackElevation:
    rack = db.get(Rack, rack_id)
    if rack is None:
        raise NotFoundError(f"Rack {rack_id} not found")

    devices = list(db.scalars(
        select(Asset).where(Asset.rack_id == rack_id)
    ).all())
    device_ids = [d.id for d in devices]

    # Port-level interfaces
    nics: list[NetworkInterface] = []
    if device_ids:
        nics = list(db.scalars(
            select(NetworkInterface).where(NetworkInterface.asset_id.in_(device_ids))
        ).all())

    switch_ids = {n.connected_asset_id for n in nics if n.connected_asset_id}
    switches = {
        a.id: a for a in db.scalars(
            select(Asset).where(Asset.id.in_(switch_ids))
        ).all()
    } if switch_ids else {}

    # Device-level fallback relations (connected_to) for devices lacking port data
    fallback: dict[int, AssetRelation] = {}
    nics_by_device: dict[int, list[NetworkInterface]] = {}
    for nic in nics:
        nics_by_device.setdefault(nic.asset_id, []).append(nic)
    if device_ids:
        rels = list(db.scalars(
            select(AssetRelation).where(
                AssetRelation.source_asset_id.in_(device_ids),
                AssetRelation.relation_type == "connected_to",
            )
        ).all())
        fallback_target_ids = {r.target_asset_id for r in rels}
        fallback_switches = {
            a.id: a for a in db.scalars(
                select(Asset).where(Asset.id.in_(fallback_target_ids))
            ).all()
        } if fallback_target_ids else {}
        for rel in rels:
            device_nics = nics_by_device.get(rel.source_asset_id, [])
            has_port_link = any(n.connected_asset_id for n in device_nics)
            if not has_port_link:
                fallback.setdefault(rel.source_asset_id, rel)
                switches.setdefault(rel.target_asset_id,
                                    fallback_switches.get(rel.target_asset_id))

    def _switch_ref(asset_id: int | None) -> ConnectedSwitch | None:
        if asset_id is None or asset_id not in switches or switches[asset_id] is None:
            return None
        sw = switches[asset_id]
        return ConnectedSwitch(
            id=sw.id, asset_no=sw.asset_no,
            hostname=sw.hostname, asset_type=sw.asset_type,
        )

    elevation_devices: list[ElevationDevice] = []
    for device in devices:
        iface_list = [
            DeviceInterface(
                id=nic.id,
                name=nic.name,
                mac_address=nic.mac_address,
                ip_address=nic.ip_address,
                role=nic.role,
                vlan_id=nic.vlan_id,
                bond_master=nic.bond_master,
                is_primary=nic.is_primary,
                connected_asset_id=nic.connected_asset_id,
                connected_port=nic.connected_port,
                connected_switch=_switch_ref(nic.connected_asset_id),
                source="port",
            )
            for nic in nics_by_device.get(device.id, [])
        ]
        rel = fallback.get(device.id)
        if rel is not None:
            iface_list.append(DeviceInterface(
                id=0,
                name=None, mac_address=None, ip_address=None,
                role="other", vlan_id=None, bond_master=None, is_primary=False,
                connected_asset_id=rel.target_asset_id,
                connected_port=None,
                connected_switch=_switch_ref(rel.target_asset_id),
                source="asset",
            ))

        elevation_devices.append(ElevationDevice(
            id=device.id,
            asset_no=device.asset_no,
            hostname=device.hostname,
            asset_type=device.asset_type,
            importance=device.importance,
            status=device.status,
            u_start=device.rack_u_start,
            u_height=device.rack_u_height,
            interfaces=iface_list,
        ))

    warnings = _build_warnings(rack, elevation_devices)
    return RackElevation(
        id=rack.id,
        datacenter=rack.datacenter,
        name=rack.name,
        u_height=rack.u_height,
        room=rack.room,
        row_label=rack.row_label,
        col_label=rack.col_label,
        description=rack.description,
        devices=elevation_devices,
        warnings=warnings,
    )


def _build_warnings(
    rack: Rack, devices: list[ElevationDevice]
) -> list[RackWarning]:
    warnings: list[RackWarning] = []

    intervals: dict[int, tuple[int, int, ElevationDevice]] = {}
    for device in devices:
        start = device.u_start
        height = device.u_height or 1
        if start is None:
            warnings.append(RackWarning(
                code="missing_u_start",
                message=f"{device.hostname or device.asset_no}: missing U position",
                asset_id=device.id,
            ))
            continue
        end = start + height - 1
        if start < 1 or end > rack.u_height:
            warnings.append(RackWarning(
                code="out_of_range",
                message=(f"{device.hostname or device.asset_no}: U{start}-U{end} "
                         f"exceeds rack height {rack.u_height}U"),
                asset_id=device.id,
            ))
        intervals[device.id] = (start, end, device)

    ids = list(intervals)
    for i in range(len(ids)):
        s1, e1, d1 = intervals[ids[i]]
        for j in range(i + 1, len(ids)):
            s2, e2, d2 = intervals[ids[j]]
            if s1 <= e2 and s2 <= e1:
                for dev in (d1, d2):
                    warnings.append(RackWarning(
                        code="overlap",
                        message=(f"{dev.hostname or dev.asset_no}: U positions "
                                 f"overlap another device"),
                        asset_id=dev.id,
                    ))

    return warnings
