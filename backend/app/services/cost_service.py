"""
V0.4 Pure computation functions: asset cost accounting
=================================
All functions are pure computations (pure functions) and do not depend on database sessions.
Only stdlib is used (datetime, math).

PRD Equation Index
------------
Monthly depreciation (straight-line, within period) = Purchase price * (1 - residual rate) / depreciation months
Post-life monthly depreciation       = Revalue amount / revalue months
Direct monthly cost         = Monthly depreciation + SUM(cost items normalized to monthly)
Allocated monthly cost (consumer) = SUM[ shared device direct monthly cost * consumer driver share ]  (no driver -> split evenly)
Fully loaded monthly cost       = Direct monthly cost + Allocated monthly cost
Annual cost = Monthly cost * 12 ; Daily rate = Annual cost / 365
Department bill = SUM over ownership segments[ daily rate(segment) * days in segment ]
Conservation check: SUM of each consumer's allocation to shared device == shared device direct monthly cost
"""

from __future__ import annotations

import math
from datetime import date, datetime
from typing import Any


# ---------------------------------------------------------------------------
# 1. monthly_depreciation
# ---------------------------------------------------------------------------
def monthly_depreciation(
    purchase_price: float,
    depreciation_months: int,
    residual_rate: float,
    end_of_life_strategy: str = "zero",
    revalue_amount: float | None = None,
    revalue_months: int | None = None,
    months_elapsed: int | None = None,
) -> dict[str, Any]:
    """Calculate monthly depreciation, accumulated depreciation, and net value.

    PRD Equation
    --------
    Monthly depreciation (straight-line, within period) = Purchase price * (1 - residual rate) / depreciation months
    Post-life monthly depreciation       = Revalue amount / revalue months

    Parameters
    ----------
    purchase_price : float
        Purchase price (original value).
    depreciation_months : int
        Number of depreciation months.
    residual_rate : float
        Residual value rate, between 0 and 1.
    end_of_life_strategy : str
        End-of-life strategy: "zero" (monthly depreciation drops to zero) or "revalue" (continued depreciation).
    revalue_amount : float | None
        Revalue amount for the post-life period; only required for the revalue strategy.
    revalue_months : int | None
        Number of months for the post-life period; only required for the revalue strategy.
    months_elapsed : int | None
        Number of months already elapsed. Defaults to 0.

    Returns
    -------
    dict
        monthly_depr, accumulated_depr, net_value,
        remaining_months, strategy, is_expired
    """
    if months_elapsed is None:
        months_elapsed = 0

    depreciable_base = purchase_price * (1 - residual_rate)
    # Straight-line method: monthly depreciation = Purchase price * (1 - residual rate) / depreciation months
    base_monthly = depreciable_base / depreciation_months if depreciation_months else 0.0

    is_expired = months_elapsed >= depreciation_months
    strategy_used = "straight_line"

    if not is_expired:
        # Within depreciation period
        monthly_depr = base_monthly
        remaining_months = depreciation_months - months_elapsed
    else:
        # Past depreciation period
        if end_of_life_strategy == "revalue" and revalue_amount and revalue_months:
            # Post-life monthly depreciation = Revalue amount / revalue months
            revalue_elapsed = months_elapsed - depreciation_months
            if revalue_elapsed < revalue_months:
                monthly_depr = revalue_amount / revalue_months
                remaining_months = revalue_months - revalue_elapsed
                strategy_used = "revalue"
            else:
                # Post-life period also expired
                monthly_depr = 0.0
                remaining_months = 0
                strategy_used = "revalue_expired"
        else:
            # zero strategy: monthly depreciation drops to zero
            monthly_depr = 0.0
            remaining_months = 0
            strategy_used = "zero"

    # Accumulated depreciation = min(monthly_depr * months_elapsed, depreciable_base)
    # Uses base_monthly during the period; accumulated = depreciable_base after expiry
    if is_expired:
        accumulated_depr = depreciable_base
    else:
        accumulated_depr = min(base_monthly * months_elapsed, depreciable_base)

    # Net value
    if is_expired and end_of_life_strategy == "zero":
        # zero strategy expired: net value = purchase price * residual rate
        net_value = purchase_price * residual_rate
    else:
        net_value = purchase_price - accumulated_depr

    return {
        "monthly_depr": round(monthly_depr, 4),
        "accumulated_depr": round(accumulated_depr, 4),
        "net_value": round(net_value, 4),
        "remaining_months": max(0, remaining_months),
        "strategy": strategy_used,
        "is_expired": is_expired,
    }


# ---------------------------------------------------------------------------
# 2. normalize_to_monthly
# ---------------------------------------------------------------------------
def normalize_to_monthly(amount: float, cycle: str) -> float:
    """Normalize any billing cycle amount to a monthly amount.

    PRD Equation
    --------
    Cost item normalized to monthly

    Parameters
    ----------
    amount : float
        Original amount.
    cycle : str
        Billing cycle: "year", "quarter", "month", "once".

    Returns
    -------
    float
        Normalized monthly amount.
    """
    cycle = cycle.lower().strip()
    if cycle == "year":
        return amount / 12.0
    if cycle == "quarter":
        return amount / 3.0
    # month / once — used directly as monthly amount
    return amount


# ---------------------------------------------------------------------------
# 3. direct_monthly_cost
# ---------------------------------------------------------------------------
def direct_monthly_cost(
    depr_monthly: float,
    cost_items: list[Any],
    power_estimate: float | None = None,
) -> float:
    """Calculate direct monthly cost = monthly depreciation + SUM(cost items normalized to monthly) + power estimate.

    PRD Equation
    --------
    Direct monthly cost = Monthly depreciation + SUM(cost items normalized to monthly)

    Parameters
    ----------
    depr_monthly : float
        Monthly depreciation (from monthly_depreciation).
    cost_items : list
        List of cost line items. Each item needs ``.amount`` and ``.billing_cycle`` attributes
        (or a dict with "amount" / "billing_cycle" keys).
    power_estimate : float | None
        Monthly power cost estimate (from estimate_monthly_power), optional.

    Returns
    -------
    float
        Direct monthly cost.
    """
    total = depr_monthly
    for item in cost_items:
        # Compatible with both ORM objects and dicts
        amount = item.amount if hasattr(item, "amount") else item["amount"]
        cycle = (
            item.billing_cycle
            if hasattr(item, "billing_cycle")
            else item["billing_cycle"]
        )
        # Depreciation cost_items are not double-counted (depr_monthly already includes depreciation)
        cost_type = item.cost_type if hasattr(item, "cost_type") else item.get("cost_type", "")
        if cost_type == "depreciation":
            continue
        total += normalize_to_monthly(amount, cycle)

    if power_estimate:
        total += power_estimate

    return round(total, 4)


# ---------------------------------------------------------------------------
# 4. estimate_monthly_power
# ---------------------------------------------------------------------------
def estimate_monthly_power(
    rated_power_kw: float,
    electricity_price: float,
    pue: float = 1.4,
    load_factor: float = 0.6,
    is_idc_with_power: bool = False,
) -> float:
    """Estimate monthly power cost for a device.

    PRD Equation
    --------
    Monthly power = Rated power (kW) * 24h * 30 days * electricity price * load factor * PUE

    Parameters
    ----------
    rated_power_kw : float
        Rated power (kW).
    electricity_price : float
        Electricity price (yuan/kWh).
    pue : float
        Power Usage Effectiveness, default 1.4.
    load_factor : float
        Load factor, default 0.6.
    is_idc_with_power : bool
        If the IDC already includes electricity in billing, returns 0 to avoid double-counting.

    Returns
    -------
    float
        Monthly power cost (yuan).
    """
    if is_idc_with_power:
        return 0.0
    return rated_power_kw * 24 * 30 * electricity_price * load_factor * pue


# ---------------------------------------------------------------------------
# 5. allocate_shared
# ---------------------------------------------------------------------------
def allocate_shared(
    shared_direct_cost: float,
    consumers_with_drivers: list[dict[str, Any]],
    driver_type: str = "even",
) -> list[dict[str, Any]]:
    """Allocate a shared device's direct monthly cost to consumers.

    PRD Equation
    --------
    Allocated monthly cost (consumer) = SUM[ shared device direct monthly cost * consumer driver share ]
    No driver -> split evenly

    Parameters
    ----------
    shared_direct_cost : float
        Direct monthly cost of the shared device.
    consumers_with_drivers : list[dict]
        Consumer list, each item containing ``consumer_id`` and ``driver_value``
        (may be None if no driver data is available).
    driver_type : str
        Driver type: "percent", "gb", "vcpu_weight", "protected_count",
        "port_count", "even".

    Returns
    -------
    list[dict]
        [{"consumer_id": int, "allocated_amount": float, "driver_share": float}]
        Guaranteed SUM(allocated_amount) == shared_direct_cost (conservation).
    """
    if not consumers_with_drivers:
        return []

    n = len(consumers_with_drivers)

    # Check if all driver_values are None / 0
    has_drivers = driver_type != "even" and any(
        (c.get("driver_value") or 0) > 0 for c in consumers_with_drivers
    )

    if has_drivers:
        total_driver = sum(c.get("driver_value") or 0 for c in consumers_with_drivers)
        if total_driver <= 0:
            # Fall back to even split
            has_drivers = False

    results: list[dict[str, Any]] = []

    if has_drivers:
        # Allocate by driver share proportion
        for c in consumers_with_drivers:
            dv = c.get("driver_value") or 0
            share = dv / total_driver
            results.append(
                {
                    "consumer_id": c["consumer_id"],
                    "allocated_amount": round(shared_direct_cost * share, 4),
                    "driver_share": round(share, 6),
                }
            )
        # Conservation fix: add rounding remainder to the largest share
        _fix_rounding(results, shared_direct_cost)
    else:
        # Even split
        share = 1.0 / n
        base = round(shared_direct_cost * share, 4)
        remainder = round(shared_direct_cost - base * n, 4)

        for i, c in enumerate(consumers_with_drivers):
            amt = base
            if i == 0:
                # Assign rounding remainder to the first item
                amt = round(amt + remainder, 4)
            results.append(
                {
                    "consumer_id": c["consumer_id"],
                    "allocated_amount": amt,
                    "driver_share": round(share, 6),
                }
            )

    return results


def _fix_rounding(results: list[dict[str, Any]], target: float) -> None:
    """Fix floating-point rounding errors so that allocated_amount sums == target."""
    current = sum(r["allocated_amount"] for r in results)
    delta = round(target - current, 4)
    if abs(delta) >= 0.0001:
        # Add the remainder to the largest-value item
        max_idx = max(range(len(results)), key=lambda i: results[i]["allocated_amount"])
        results[max_idx]["allocated_amount"] = round(
            results[max_idx]["allocated_amount"] + delta, 4
        )


# ---------------------------------------------------------------------------
# 6. full_loaded_monthly
# ---------------------------------------------------------------------------
def full_loaded_monthly(
    asset_id: int,
    direct_cost: float,
    received_allocations: list[float],
) -> float:
    """Fully loaded monthly cost = direct monthly cost + allocated monthly cost.

    PRD Equation
    --------
    Fully loaded monthly cost = Direct monthly cost + Allocated monthly cost

    Parameters
    ----------
    asset_id : int
        Asset ID (used for logging/audit only, not in calculation).
    direct_cost : float
        Direct monthly cost.
    received_allocations : list[float]
        List of allocation amounts received from other shared devices.

    Returns
    -------
    float
        Fully loaded monthly cost.
    """
    return round(direct_cost + sum(received_allocations), 4)


# ---------------------------------------------------------------------------
# 7. daily_rate
# ---------------------------------------------------------------------------
def daily_rate(full_loaded_monthly: float) -> float:
    """Daily rate = annual cost / 365 = monthly cost * 12 / 365.

    PRD Equation
    --------
    Annual cost = Monthly cost * 12 ; Daily rate = Annual cost / 365

    Parameters
    ----------
    full_loaded_monthly : float
        Fully loaded monthly cost.

    Returns
    -------
    float
        Daily rate (yuan/day).
    """
    return round(full_loaded_monthly * 12 / 365, 6)


# ---------------------------------------------------------------------------
# 8. conservation_check
# ---------------------------------------------------------------------------
def conservation_check(
    shared_direct_cost: float,
    allocations: list[dict[str, Any]],
) -> dict[str, Any]:
    """Conservation check: SUM of each consumer's allocation == shared device direct monthly cost.

    PRD Equation
    --------
    Conservation check: SUM of each consumer's allocation to shared device == shared device direct monthly cost

    Parameters
    ----------
    shared_direct_cost : float
        Shared device direct monthly cost.
    allocations : list[dict]
        Allocation results list, each item containing ``allocated_amount``.

    Returns
    -------
    dict
        total_allocated, expected, delta, is_conserved
    """
    total_allocated = sum(a["allocated_amount"] for a in allocations)
    delta = round(total_allocated - shared_direct_cost, 4)
    return {
        "total_allocated": round(total_allocated, 4),
        "expected": round(shared_direct_cost, 4),
        "delta": delta,
        "is_conserved": abs(delta) < 0.01,
    }


# ---------------------------------------------------------------------------
# 9. department_bill_for_segment
# ---------------------------------------------------------------------------
def department_bill_for_segment(
    daily_rate_val: float,
    days_in_segment: int,
) -> float:
    """Department bill (single ownership segment) = daily rate * days occupied in segment.

    PRD Equation
    --------
    Department bill = SUM over ownership segments[ daily rate(segment) * days in segment ]

    Parameters
    ----------
    daily_rate_val : float
        Daily rate (from daily_rate).
    days_in_segment : int
        Days occupied in this segment.

    Returns
    -------
    float
        Bill amount for this segment, rounded to two decimal places.
    """
    return round(daily_rate_val * days_in_segment, 2)


# ---------------------------------------------------------------------------
# 10. days_between
# ---------------------------------------------------------------------------
def days_between(date_from_str: str, date_to_str: str | None = None) -> int:
    """Calculate the number of days between two ISO date strings.

    Parameters
    ----------
    date_from_str : str
        Start date in ISO format ("YYYY-MM-DD").
    date_to_str : str | None
        End date in ISO format. None defaults to today.

    Returns
    -------
    int
        Days difference (non-negative).

    Raises
    ------
    ValueError
        If the date format is invalid.
    """
    d_from = _parse_date(date_from_str)
    d_to = _parse_date(date_to_str) if date_to_str else date.today()
    return max(0, (d_to - d_from).days)


def _parse_date(s: str) -> date:
    """Parse an ISO date string, supporting 'YYYY-MM-DD' and 'YYYY-MM-DDTHH:MM:SS'."""
    s = s.strip()
    try:
        return datetime.fromisoformat(s).date()
    except ValueError:
        # Fallback: try taking only the first 10 characters
        return date.fromisoformat(s[:10])


# ---------------------------------------------------------------------------
# Higher-level orchestration (DB-aware)
# ---------------------------------------------------------------------------

def _months_elapsed(purchase_date: str | None) -> int:
    """Calculate months elapsed from purchase date to today"""
    if not purchase_date:
        return 0
    try:
        d = _parse_date(purchase_date)
        today = date.today()
        return max(0, (today.year - d.year) * 12 + (today.month - d.month))
    except (ValueError, TypeError):
        return 0


def _default_rates() -> dict:
    """Global default rates (used when cost_rates table is empty)"""
    return {
        "electricity_price": 0.72,
        "pue": 1.45,
        "load_factor": 0.65,
        "depreciation_defaults": {
            "physical": {"years": 5, "residual_rate": 0.05, "method": "straight_line", "eol_strategy": "zero"},
            "virtual": {"years": 3, "residual_rate": 0.0, "method": "straight_line", "eol_strategy": "zero"},
            "network_device": {"years": 5, "residual_rate": 0.05, "method": "straight_line", "eol_strategy": "zero"},
            "other": {"years": 5, "residual_rate": 0.05, "method": "straight_line", "eol_strategy": "zero"},
            "cloud_server": {"years": 3, "residual_rate": 0.0, "method": "straight_line", "eol_strategy": "zero"},
        },
    }


def _load_rates_from_db(db) -> dict:
    """Load rates from cost_rates table and merge with defaults"""
    import json
    from app.repositories import cost_repo
    rates = _default_rates()
    try:
        db_rates = cost_repo.get_all_cost_rates(db)
        for r in db_rates:
            try:
                rates[r.key] = json.loads(r.value)
            except (json.JSONDecodeError, TypeError):
                rates[r.key] = r.value
    except Exception:
        pass
    return rates


def compute_asset_full_cost(db, asset) -> dict:
    """
    Calculate the fully loaded cost breakdown for a single asset.
    Returns: full_loaded_monthly, cost_breakdown, depreciation_info, daily_rate, etc.
    """
    from app.repositories import cost_repo
    from app.models.asset import Asset
    import json

    rates = _load_rates_from_db(db)
    dep_defaults = rates.get("depreciation_defaults", {})
    # Guard: dep_defaults may be a list (from CostRates page save format)
    if not isinstance(dep_defaults, dict):
        dep_defaults = _default_rates()["depreciation_defaults"]

    # Depreciation calculation
    if asset.purchase_price and asset.depreciation_months:
        dep_months = asset.depreciation_months
        res_rate = asset.residual_rate if asset.residual_rate is not None else 0.05
        eol = asset.end_of_life_strategy or "zero"
        months_el = _months_elapsed(asset.purchase_date)

        depr = monthly_depreciation(
            purchase_price=asset.purchase_price,
            depreciation_months=dep_months,
            residual_rate=res_rate,
            end_of_life_strategy=eol,
            revalue_amount=asset.revalue_amount,
            revalue_months=asset.revalue_months,
            months_elapsed=months_el,
        )
        depr_monthly = depr["monthly_depr"]
    else:
        # No purchase info, depreciation is 0
        dep_defaults_for_type = dep_defaults.get(asset.asset_type, {})
        depr = {
            "monthly_depr": 0.0,
            "accumulated_depr": 0.0,
            "net_value": 0.0,
            "remaining_months": 0,
            "strategy": "none",
            "is_expired": False,
        }
        depr_monthly = 0.0
        dep_months = dep_defaults_for_type.get("years", 5) * 12
        res_rate = dep_defaults_for_type.get("residual_rate", 0.05)

    # Cost line items
    cost_items = cost_repo.get_cost_items(db, asset.id)

    # Itemized monthly cost
    breakdown = {}
    if depr_monthly > 0:
        breakdown["depreciation"] = round(depr_monthly, 2)

    for item in cost_items:
        if item.cost_type == "depreciation":
            continue
        monthly = normalize_to_monthly(item.amount, item.billing_cycle)
        label = item.cost_type
        if item.cost_type == "allocation" and item.note:
            label = item.note
        breakdown[label] = breakdown.get(label, 0) + monthly

    direct = direct_monthly_cost(depr_monthly, cost_items)

    # Allocations (find relations where this asset is the target, compute received allocations)
    received_allocations = []
    allocation_details = []
    relations = cost_repo.get_relations(db, asset.id)
    # Find all relations where this asset is a consumer (source) pointing to a shared device (target)
    for rel in relations:
        if rel.source_asset_id == asset.id:
            shared_asset = db.get(Asset, rel.target_asset_id)
            if shared_asset is None:
                continue
            shared_direct = direct_monthly_cost(0, cost_repo.get_cost_items(db, shared_asset.id))
            # Find all other relations that consume this shared device
            all_rels = cost_repo.get_relations(db, shared_asset.id)
            consumers = []
            for r in all_rels:
                if r.target_asset_id == shared_asset.id and r.relation_type == rel.relation_type:
                    consumers.append({
                        "consumer_id": r.source_asset_id,
                        "driver_value": r.driver_value,
                    })
            if consumers:
                allocations = allocate_shared(shared_direct, consumers, rel.driver_type)
                for a in allocations:
                    if a["consumer_id"] == asset.id:
                        received_allocations.append(a["allocated_amount"])
                        allocation_details.append({
                            "from_asset_id": shared_asset.id,
                            "from_asset_no": shared_asset.asset_no,
                            "relation_type": rel.relation_type,
                            "amount": round(a["allocated_amount"], 2),
                        })
                        if rel.relation_type not in ("depreciation",):
                            breakdown[f"{rel.relation_type}_alloc"] = breakdown.get(
                                f"{rel.relation_type}_alloc", 0
                            ) + a["allocated_amount"]

    fm = full_loaded_monthly(asset.id, direct, received_allocations)
    dr = daily_rate(fm)

    # Depreciation info
    dep_info = {
        "purchase_price": asset.purchase_price,
        "purchase_date": asset.purchase_date,
        "depreciation_months": asset.depreciation_months,
        "residual_rate": asset.residual_rate,
        "depreciation_method": asset.depreciation_method or "straight_line",
        "end_of_life_strategy": asset.end_of_life_strategy or "zero",
        "months_elapsed": _months_elapsed(asset.purchase_date),
        **depr,
    }

    return {
        "asset_id": asset.id,
        "asset_no": asset.asset_no,
        "full_loaded_monthly": round(fm, 2),
        "daily_rate": round(dr, 4),
        "annual_cost": round(fm * 12, 2),
        "direct_monthly": round(direct, 2),
        "allocation_monthly": round(sum(received_allocations), 2),
        "cost_breakdown": {k: round(v, 2) for k, v in breakdown.items()},
        "depreciation_info": dep_info,
        "allocation_details": allocation_details,
    }


def compute_global_summary(db) -> dict:
    """
    Cost dashboard aggregation: KPI + chart data + governance checklist
    """
    from app.repositories import cost_repo
    from sqlalchemy import select, func
    from app.models.asset import Asset
    from app.models.cost import Department, AssetDeptAssignment

    total_monthly = 0.0
    capex_monthly = 0.0
    opex_monthly = 0.0
    dept_costs: dict[str, float] = {}
    type_costs: dict[str, float] = {}
    new_cost_assets = 0
    assets = list(db.scalars(select(Asset)).all())

    for asset in assets:
        if asset.purchase_price is None:
            continue
        ac = compute_asset_full_cost(db, asset)
        fm = ac["full_loaded_monthly"]
        total_monthly += fm

        # CapEx (depreciation) vs OpEx (other)
        depr = ac["cost_breakdown"].get("depreciation", 0)
        capex_monthly += depr
        opex_monthly += (fm - depr)

        # By department
        if asset.responsible_dept_id:
            dept = db.get(Department, asset.responsible_dept_id)
            if dept:
                dept_costs[dept.name] = dept_costs.get(dept.name, 0) + fm

        # By type
        type_costs[asset.asset_type] = type_costs.get(asset.asset_type, 0) + fm

    missing_count = cost_repo.get_assets_without_cost_data(db)

    # Department ranking
    dept_ranking = sorted(
        [{"name": k, "monthly_cost": round(v, 2)} for k, v in dept_costs.items()],
        key=lambda x: x["monthly_cost"],
        reverse=True,
    )

    # Type breakdown
    type_breakdown = [
        {"name": k, "value": round(v, 2)} for k, v in
        sorted(type_costs.items(), key=lambda x: x[1], reverse=True)
    ]

    # Governance checklist
    governance = []
    from datetime import date as _date
    today = _date.today()
    for asset in assets:
        if asset.status == "decommissioned" and asset.purchase_price:
            ac = compute_asset_full_cost(db, asset)
            governance.append({
                "type": "shadow_cost",
                "severity": "critical",
                "asset_id": asset.id,
                "asset_no": asset.asset_no,
                "monthly_cost": ac["full_loaded_monthly"],
                "message": f"Decommissioned asset still incurring cost - monthly cost CNY {ac['full_loaded_monthly']:,.0f}",
            })
        if asset.depreciation_months and asset.purchase_date:
            months_el = _months_elapsed(asset.purchase_date)
            remaining = asset.depreciation_months - months_el
            if 0 < remaining <= 3:
                governance.append({
                    "type": "depreciation_expiring",
                    "severity": "warning",
                    "asset_id": asset.id,
                    "asset_no": asset.asset_no,
                    "remaining_months": remaining,
                    "message": f"Depreciation expiring soon - {remaining} months remaining",
                })

    if missing_count > 0:
        governance.append({
            "type": "missing_data",
            "severity": "info",
            "count": missing_count,
            "message": f"{missing_count} assets missing cost data",
        })

    return {
        "total_monthly": round(total_monthly, 2),
        "annualized": round(total_monthly * 12, 2),
        "capex_ratio": round(capex_monthly / total_monthly * 100, 1) if total_monthly > 0 else 0,
        "opex_ratio": round(opex_monthly / total_monthly * 100, 1) if total_monthly > 0 else 0,
        "capex_monthly": round(capex_monthly, 2),
        "opex_monthly": round(opex_monthly, 2),
        "new_cost_assets": new_cost_assets,
        "missing_cost_data": missing_count,
        "dept_ranking": dept_ranking,
        "type_breakdown": type_breakdown,
        "governance": governance,
        "governance_count": len(governance),
    }
