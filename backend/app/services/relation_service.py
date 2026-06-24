"""V0.6 unit relation service"""
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.consuming_unit import ConsumingUnit
from app.repositories import relation_repo


def create_relation(db: Session, source_unit_id: str, target_unit_id: str, rel_type: str):
    """Create a dependency edge between two consuming units."""
    # Verify both units exist
    src = db.get(ConsumingUnit, source_unit_id)
    if not src:
        raise NotFoundError(f"Source unit {source_unit_id} not found")
    tgt = db.get(ConsumingUnit, target_unit_id)
    if not tgt:
        raise NotFoundError(f"Target unit {target_unit_id} not found")

    return relation_repo.create_relation(
        db,
        source_unit_id=source_unit_id,
        target_unit_id=target_unit_id,
        rel_type=rel_type,
        source="manual",
    )


def delete_relation(db: Session, relation_id: str) -> None:
    rel = relation_repo.get_by_id(db, relation_id)
    if not rel:
        raise NotFoundError(f"Relation {relation_id} not found")
    relation_repo.delete_relation(db, rel)
