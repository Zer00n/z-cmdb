"""V0.6 billing policy service"""
from sqlalchemy.orm import Session

from app.core.exceptions import PolicyFreezeError, ValidationError
from app.models.billing_policy import BillingPolicy
from app.repositories import billing_repo


def get_active_policy(db: Session) -> BillingPolicy | None:
    return billing_repo.get_active_policy(db)


def update_policy(
    db: Session,
    denominator: str,
    weight_mode: str,
    weight_cpu: float,
    weight_mem: float,
    idle_cost: str,
    sampling: str,
) -> BillingPolicy:
    """
    Create a new billing policy version.
    - Validates freeze (must always be 1)
    - Validates weight_sum when weight_mode=weighted
    - Deactivates old policy, activates new one
    """
    # Validate weights
    if weight_mode == "weighted":
        if abs(weight_cpu + weight_mem - 1.0) > 1e-6:
            raise ValidationError(
                f"weight_cpu + weight_mem must equal 1, got {weight_cpu + weight_mem}"
            )

    # Get current version
    current = billing_repo.get_active_policy(db)
    current_version = billing_repo.get_latest_version(db)
    new_version = current_version + 1

    # Deactivate old policy
    if current:
        billing_repo.deactivate_policy(db, current)

    # Create new policy
    new_policy = billing_repo.create_policy(
        db,
        version=new_version,
        denominator=denominator,
        weight_mode=weight_mode,
        weight_cpu=weight_cpu,
        weight_mem=weight_mem,
        idle_cost=idle_cost,
        sampling=sampling,
        freeze=1,  # Always 1 — defense in depth
        is_active=1,
    )

    return new_policy
