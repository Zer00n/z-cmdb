"""V0.6 billing policy and bill snapshot repository"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.bill_snapshot import BillSnapshot
from app.models.billing_policy import BillingPolicy


def get_active_policy(db: Session) -> BillingPolicy | None:
    return db.scalars(
        select(BillingPolicy).where(BillingPolicy.is_active == 1)
    ).first()


def get_latest_version(db: Session) -> int:
    """Get the latest policy version number."""
    from sqlalchemy import func
    result = db.scalar(select(func.max(BillingPolicy.version)))
    return result or 0


def create_policy(db: Session, **kwargs) -> BillingPolicy:
    policy = BillingPolicy(**kwargs)
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


def deactivate_policy(db: Session, policy: BillingPolicy) -> None:
    policy.is_active = 0
    db.commit()


def get_bill_snapshot(db: Session, project_id: str, period: str) -> BillSnapshot | None:
    return db.scalars(
        select(BillSnapshot).where(
            BillSnapshot.project_id == project_id,
            BillSnapshot.period == period,
        )
    ).first()


def create_bill_snapshot(db: Session, **kwargs) -> BillSnapshot:
    snapshot = BillSnapshot(**kwargs)
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot
