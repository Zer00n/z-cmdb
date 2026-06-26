"""V0.6 department-level billing aggregation service"""
from sqlalchemy.orm import Session

from app.repositories import project_repo, billing_repo


def get_department_billing(db: Session, period: str) -> dict:
    """
    Aggregate bill_snapshot costs grouped by project.department.

    Projects without a department are labeled "(未分配部门)".
    Only projects with billing_enabled=1 and an existing snapshot contribute cost.
    """
    projects, _ = project_repo.list_projects(db, page=1, page_size=10000)

    dept_map: dict[str, list] = {}
    for p in projects:
        dept = p.department or "(未分配部门)"
        dept_map.setdefault(dept, []).append(p)

    items = []
    grand_total = 0.0
    for dept in sorted(dept_map.keys()):
        dept_projects = dept_map[dept]
        total_cost = 0.0
        billing_count = 0
        for p in dept_projects:
            if p.billing_enabled:
                snapshot = billing_repo.get_bill_snapshot(db, p.id, period)
                if snapshot:
                    total_cost += snapshot.total_cost
                    billing_count += 1
        grand_total += total_cost
        items.append({
            "department": dept,
            "project_count": len(dept_projects),
            "total_cost": round(total_cost, 2),
            "billing_enabled_count": billing_count,
        })

    return {
        "period": period,
        "items": items,
        "grand_total": round(grand_total, 2),
    }
