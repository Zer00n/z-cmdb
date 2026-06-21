"""
V0.4 纯计算函数：资产成本核算
=================================
所有函数均为纯计算（pure functions），不依赖数据库会话。
仅使用 stdlib（datetime, math）。

PRD 方程索引
------------
月折旧(直线，期内) = 购置价 × (1 - 残值率) / 折旧月数
续用期月折旧       = 续值金额 / 续用月数
直接月成本         = 月折旧 + Σ(成本行归一到月)
分摊月成本(消费方) = Σ[ 共享设备直接月成本 × 该消费方动因占比 ]  (无动因 → 均摊)
全负载月成本       = 直接月成本 + 分摊月成本
年成本 = 月成本 × 12 ；日费率 = 年成本 / 365
部门账单 = Σ over 归属分段[ 日费率(段) × 段内占用天数 ]
守恒校验：Σ 各消费方对共享设备的分摊 == 共享设备直接月成本
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
    """计算月折旧及累计折旧、净值。

    PRD 方程
    --------
    月折旧(直线，期内) = 购置价 × (1 − 残值率) / 折旧月数
    续用期月折旧       = 续值金额 / 续用月数

    Parameters
    ----------
    purchase_price : float
        购置价（原值）。
    depreciation_months : int
        折旧月数。
    residual_rate : float
        残值率，0-1 之间。
    end_of_life_strategy : str
        到期策略，"zero"（月折旧归零）或 "revalue"（续用期折旧）。
    revalue_amount : float | None
        续用期续值金额，仅 revalue 策略需要。
    revalue_months : int | None
        续用期月数，仅 revalue 策略需要。
    months_elapsed : int | None
        已使用月数。默认 0。

    Returns
    -------
    dict
        monthly_depr, accumulated_depr, net_value,
        remaining_months, strategy, is_expired
    """
    if months_elapsed is None:
        months_elapsed = 0

    depreciable_base = purchase_price * (1 - residual_rate)
    # 直线法：月折旧 = 购置价 × (1 − 残值率) / 折旧月数
    base_monthly = depreciable_base / depreciation_months if depreciation_months else 0.0

    is_expired = months_elapsed >= depreciation_months
    strategy_used = "straight_line"

    if not is_expired:
        # 折旧期内
        monthly_depr = base_monthly
        remaining_months = depreciation_months - months_elapsed
    else:
        # 已过折旧期
        if end_of_life_strategy == "revalue" and revalue_amount and revalue_months:
            # 续用期月折旧 = 续值金额 / 续用月数
            revalue_elapsed = months_elapsed - depreciation_months
            if revalue_elapsed < revalue_months:
                monthly_depr = revalue_amount / revalue_months
                remaining_months = revalue_months - revalue_elapsed
                strategy_used = "revalue"
            else:
                # 续用期也已结束
                monthly_depr = 0.0
                remaining_months = 0
                strategy_used = "revalue_expired"
        else:
            # zero 策略：月折旧归零
            monthly_depr = 0.0
            remaining_months = 0
            strategy_used = "zero"

    # 累计折旧 = min(月折旧 × 已用月数, 可折旧基数)
    # 期内用 base_monthly 计算，到期后累计 = 可折旧基数
    if is_expired:
        accumulated_depr = depreciable_base
    else:
        accumulated_depr = min(base_monthly * months_elapsed, depreciable_base)

    # 净值
    if is_expired and end_of_life_strategy == "zero":
        # zero 策略到期：净值 = 购置价 × 残值率
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
    """将任意计费周期金额归一化为月金额。

    PRD 方程
    --------
    成本行归一到月

    Parameters
    ----------
    amount : float
        原始金额。
    cycle : str
        计费周期："year", "quarter", "month", "once"。

    Returns
    -------
    float
        归一化后的月金额。
    """
    cycle = cycle.lower().strip()
    if cycle == "year":
        return amount / 12.0
    if cycle == "quarter":
        return amount / 3.0
    # month / once — 直接作为月金额
    return amount


# ---------------------------------------------------------------------------
# 3. direct_monthly_cost
# ---------------------------------------------------------------------------
def direct_monthly_cost(
    depr_monthly: float,
    cost_items: list[Any],
    power_estimate: float | None = None,
) -> float:
    """计算直接月成本 = 月折旧 + Σ(成本行归一到月) + 电力估算。

    PRD 方程
    --------
    直接月成本 = 月折旧 + Σ(成本行归一到月)

    Parameters
    ----------
    depr_monthly : float
        月折旧额（来自 monthly_depreciation）。
    cost_items : list
        成本行列表。每项需有 ``.amount`` 和 ``.billing_cycle`` 属性
        （或 dict 带 "amount" / "billing_cycle" 键）。
    power_estimate : float | None
        月电力成本估算（来自 estimate_monthly_power），可选。

    Returns
    -------
    float
        直接月成本。
    """
    total = depr_monthly
    for item in cost_items:
        # 兼容 ORM 对象和 dict
        amount = item.amount if hasattr(item, "amount") else item["amount"]
        cycle = (
            item.billing_cycle
            if hasattr(item, "billing_cycle")
            else item["billing_cycle"]
        )
        # 折旧类型的 cost_item 不重复计入（depr_monthly 已含折旧）
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
    """估算设备月电力成本。

    PRD 方程
    --------
    月电力 = 额定功率(kW) × 24h × 30天 × 电价 × 负载率 × PUE

    Parameters
    ----------
    rated_power_kw : float
        额定功率 (kW)。
    electricity_price : float
        电价 (元/kWh)。
    pue : float
        电力使用效率，默认 1.4。
    load_factor : float
        负载率，默认 0.6。
    is_idc_with_power : bool
        如果 IDC 已含电费计费项，返回 0 避免重复计算。

    Returns
    -------
    float
        月电力成本（元）。
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
    """将共享设备的直接月成本分摊给消费方。

    PRD 方程
    --------
    分摊月成本(消费方) = Σ[ 共享设备直接月成本 × 该消费方动因占比 ]
    无动因 → 均摊

    Parameters
    ----------
    shared_direct_cost : float
        共享设备的直接月成本。
    consumers_with_drivers : list[dict]
        消费方列表，每项含 ``consumer_id`` 和 ``driver_value``
        （可为 None 表示无动因数据）。
    driver_type : str
        动因类型："percent", "gb", "vcpu_weight", "protected_count",
        "port_count", "even"。

    Returns
    -------
    list[dict]
        [{"consumer_id": int, "allocated_amount": float, "driver_share": float}]
        保证 Σ allocated_amount == shared_direct_cost（守恒）。
    """
    if not consumers_with_drivers:
        return []

    n = len(consumers_with_drivers)

    # 判断是否所有 driver_value 均为 None / 0
    has_drivers = driver_type != "even" and any(
        (c.get("driver_value") or 0) > 0 for c in consumers_with_drivers
    )

    if has_drivers:
        total_driver = sum(c.get("driver_value") or 0 for c in consumers_with_drivers)
        if total_driver <= 0:
            # 回退到均摊
            has_drivers = False

    results: list[dict[str, Any]] = []

    if has_drivers:
        # 按动因比例分摊
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
        # 守恒修正：将尾差加到最大份额方
        _fix_rounding(results, shared_direct_cost)
    else:
        # 均摊
        share = 1.0 / n
        base = round(shared_direct_cost * share, 4)
        remainder = round(shared_direct_cost - base * n, 4)

        for i, c in enumerate(consumers_with_drivers):
            amt = base
            if i == 0:
                # 将尾差分配给第一项
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
    """修正浮点尾差，保证 allocated_amount 之和 == target。"""
    current = sum(r["allocated_amount"] for r in results)
    delta = round(target - current, 4)
    if abs(delta) >= 0.0001:
        # 将尾差加到最大值项
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
    """全负载月成本 = 直接月成本 + 分摊月成本。

    PRD 方程
    --------
    全负载月成本 = 直接月成本 + 分摊月成本

    Parameters
    ----------
    asset_id : int
        资产 ID（仅用于日志/审计，不参与计算）。
    direct_cost : float
        直接月成本。
    received_allocations : list[float]
        从其他共享设备接收到的分摊金额列表。

    Returns
    -------
    float
        全负载月成本。
    """
    return round(direct_cost + sum(received_allocations), 4)


# ---------------------------------------------------------------------------
# 7. daily_rate
# ---------------------------------------------------------------------------
def daily_rate(full_loaded_monthly: float) -> float:
    """日费率 = 年成本 / 365 = 月成本 × 12 / 365。

    PRD 方程
    --------
    年成本 = 月成本 × 12 ；日费率 = 年成本 / 365

    Parameters
    ----------
    full_loaded_monthly : float
        全负载月成本。

    Returns
    -------
    float
        日费率（元/天）。
    """
    return round(full_loaded_monthly * 12 / 365, 6)


# ---------------------------------------------------------------------------
# 8. conservation_check
# ---------------------------------------------------------------------------
def conservation_check(
    shared_direct_cost: float,
    allocations: list[dict[str, Any]],
) -> dict[str, Any]:
    """守恒校验：Σ 各消费方分摊 == 共享设备直接月成本。

    PRD 方程
    --------
    守恒校验：Σ 各消费方对共享设备的分摊 == 共享设备直接月成本

    Parameters
    ----------
    shared_direct_cost : float
        共享设备直接月成本。
    allocations : list[dict]
        分摊结果列表，每项含 ``allocated_amount``。

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
    """部门账单（单个归属分段）= 日费率 × 段内占用天数。

    PRD 方程
    --------
    部门账单 = Σ over 归属分段[ 日费率(段) × 段内占用天数 ]

    Parameters
    ----------
    daily_rate_val : float
        日费率（来自 daily_rate）。
    days_in_segment : int
        段内占用天数。

    Returns
    -------
    float
        该段账单金额，保留两位小数。
    """
    return round(daily_rate_val * days_in_segment, 2)


# ---------------------------------------------------------------------------
# 10. days_between
# ---------------------------------------------------------------------------
def days_between(date_from_str: str, date_to_str: str | None = None) -> int:
    """计算两个 ISO 日期字符串之间的天数。

    Parameters
    ----------
    date_from_str : str
        起始日期，ISO 格式（"YYYY-MM-DD"）。
    date_to_str : str | None
        结束日期，ISO 格式。None 则取今天。

    Returns
    -------
    int
        天数差（非负）。

    Raises
    ------
    ValueError
        日期格式不合法时。
    """
    d_from = _parse_date(date_from_str)
    d_to = _parse_date(date_to_str) if date_to_str else date.today()
    return max(0, (d_to - d_from).days)


def _parse_date(s: str) -> date:
    """解析 ISO 日期字符串，支持 'YYYY-MM-DD' 和 'YYYY-MM-DDTHH:MM:SS'。"""
    s = s.strip()
    try:
        return datetime.fromisoformat(s).date()
    except ValueError:
        # 兜底：尝试只取前 10 位
        return date.fromisoformat(s[:10])


# ---------------------------------------------------------------------------
# Higher-level orchestration (DB-aware)
# ---------------------------------------------------------------------------

def _months_elapsed(purchase_date: str | None) -> int:
    """从购置日期算到今天已过月数"""
    if not purchase_date:
        return 0
    try:
        d = _parse_date(purchase_date)
        today = date.today()
        return max(0, (today.year - d.year) * 12 + (today.month - d.month))
    except (ValueError, TypeError):
        return 0


def _default_rates() -> dict:
    """全局默认费率（当 cost_rates 表为空时使用）"""
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
    """从 cost_rates 表加载费率，合并默认值"""
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
    计算单资产的全负载成本与构成。
    返回: full_loaded_monthly, cost_breakdown, depreciation_info, daily_rate 等
    """
    from app.repositories import cost_repo
    from app.models.asset import Asset
    import json

    rates = _load_rates_from_db(db)
    dep_defaults = rates.get("depreciation_defaults", {})
    # Guard: dep_defaults may be a list (from CostRates page save format)
    if not isinstance(dep_defaults, dict):
        dep_defaults = _default_rates()["depreciation_defaults"]

    # 折旧计算
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
        # 无购置信息，折旧为 0
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

    # 成本行
    cost_items = cost_repo.get_cost_items(db, asset.id)

    # 分项月成本
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

    # 分摊（查找该资产作为 target 的关系，计算 received allocations）
    received_allocations = []
    allocation_details = []
    relations = cost_repo.get_relations(db, asset.id)
    # 找出所有该资产作为消费者（source）指向共享设备（target）的关系
    for rel in relations:
        if rel.source_asset_id == asset.id:
            shared_asset = db.get(Asset, rel.target_asset_id)
            if shared_asset is None:
                continue
            shared_direct = direct_monthly_cost(0, cost_repo.get_cost_items(db, shared_asset.id))
            # 查找所有消费该共享设备的其他关系
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

    # 折旧信息
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
    成本看板聚合：KPI + 图表数据 + 治理清单
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

        # CapEx (折旧) vs OpEx (其他)
        depr = ac["cost_breakdown"].get("depreciation", 0)
        capex_monthly += depr
        opex_monthly += (fm - depr)

        # 按部门
        if asset.responsible_dept_id:
            dept = db.get(Department, asset.responsible_dept_id)
            if dept:
                dept_costs[dept.name] = dept_costs.get(dept.name, 0) + fm

        # 按类型
        type_costs[asset.asset_type] = type_costs.get(asset.asset_type, 0) + fm

    missing_count = cost_repo.get_assets_without_cost_data(db)

    # 部门排行
    dept_ranking = sorted(
        [{"name": k, "monthly_cost": round(v, 2)} for k, v in dept_costs.items()],
        key=lambda x: x["monthly_cost"],
        reverse=True,
    )

    # 类型占比
    type_breakdown = [
        {"name": k, "value": round(v, 2)} for k, v in
        sorted(type_costs.items(), key=lambda x: x[1], reverse=True)
    ]

    # 治理清单
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
                "message": f"已下线资产仍计费 · 月成本 ¥{ac['full_loaded_monthly']:,.0f}",
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
                    "message": f"折旧即将到期 · 剩余 {remaining} 个月",
                })

    if missing_count > 0:
        governance.append({
            "type": "missing_data",
            "severity": "info",
            "count": missing_count,
            "message": f"{missing_count} 台资产缺少成本数据",
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
