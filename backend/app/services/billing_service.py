"""
Billing service
Department billing: daily rate * days occupied within the period
Calculation basis: see PRD section 4.5 and development guide section 3
"""
from datetime import date, datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.cost import AssetDeptAssignment
from app.repositories import cost_repo
from app.services import cost_service


def _parse_date(d: Optional[str]) -> date:
    """Parse an ISO date string; None defaults to today"""
    if d is None:
        return date.today()
    return date.fromisoformat(d)


def _segment_days(effective_from: str, effective_to: Optional[str],
                  bill_from: date, bill_to: date) -> int:
    """Calculate the actual number of days an ownership segment overlaps with the billing period"""
    seg_start = _parse_date(effective_from)
    seg_end = _parse_date(effective_to)

    # Take the intersection
    overlap_start = max(seg_start, bill_from)
    overlap_end = min(seg_end, bill_to)

    days = (overlap_end - overlap_start).days
    return max(days, 0)


def department_bill(
    db: Session,
    dept_id: int,
    date_from: str,
    date_to: str,
    granularity: str = "month",
) -> dict:
    """
    Calculate a department bill.
    Iterates through the department's assignment segments, accumulating
    daily rate * days occupied in each segment.
    unit_price mode uses price_book * usage * days.
    Output: per-resource detail + cost type breakdown.
    """
    from app.models.asset import Asset

    bill_from = _parse_date(date_from)
    bill_to = _parse_date(date_to)
    bill_days = (bill_to - bill_from).days

    # Get all assignment segments for this department
    assignments = cost_repo.get_dept_assignments_by_dept(db, dept_id)

    resources = []
    cost_type_totals: dict[str, float] = {}

    for assignment in assignments:
        asset = db.get(Asset, assignment.asset_id)
        if asset is None:
            continue

        # Get cost data for this asset
        asset_cost = cost_service.compute_asset_full_cost(db, asset)
        fm = asset_cost["full_loaded_monthly"]
        dr = cost_service.daily_rate(fm)

        # Calculate how many days this segment overlaps with the billing period
        seg_days = _segment_days(
            assignment.effective_from,
            assignment.effective_to,
            bill_from,
            bill_to,
        )
        if seg_days <= 0:
            continue

        if assignment.billing_mode == "cost":
            period_amount = round(dr * seg_days, 2)
        else:
            # unit_price mode: price_book * usage * days
            import json
            usage = json.loads(assignment.share_or_usage) if assignment.share_or_usage else {}
            unit_price = usage.get("unit_price", dr)
            quantity = usage.get("quantity", 1)
            period_amount = round(unit_price * quantity * seg_days, 2)

        resources.append({
            "asset_id": asset.id,
            "asset_no": asset.asset_no,
            "hostname": asset.hostname,
            "ip_address": asset.ip_address,
            "asset_type": asset.asset_type,
            "billing_mode": assignment.billing_mode,
            "monthly_cost": round(fm, 2),
            "daily_rate": round(dr, 2),
            "days_used": seg_days,
            "period_amount": period_amount,
            "cost_breakdown": asset_cost.get("cost_breakdown", {}),
        })

        # Accumulate by cost type
        for ct, amt in asset_cost.get("cost_breakdown", {}).items():
            cost_type_totals[ct] = cost_type_totals.get(ct, 0) + amt

    total = round(sum(r["period_amount"] for r in resources), 2)
    daily_avg = round(total / bill_days, 2) if bill_days > 0 else 0
    annualized = round(daily_avg * 365, 2)

    return {
        "dept_id": dept_id,
        "date_from": date_from,
        "date_to": date_to,
        "granularity": granularity,
        "bill_days": bill_days,
        "total": total,
        "daily_avg": daily_avg,
        "annualized": annualized,
        "resources": resources,
        "cost_type_totals": cost_type_totals,
        "resource_count": len(resources),
    }
