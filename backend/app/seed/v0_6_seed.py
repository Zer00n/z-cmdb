"""
V0.6 seed data — reproduces the screenshot scenario.

"Full capacity" assumption (装满假设):
  node-1 and node-2 are fully occupied by Project A's units —
  their capacity exactly equals the sum of request values (no idle).
  This is a demo alignment constraint; the apportion engine always
  computes from real request vs. capacity, so in production there
  will be idle and unallocated costs.

Seed summary:
  - 3 hosts (node-1/2/3) + 1 zombie host
  - 2 projects (A: billing on, B: billing off)
  - 5 consuming units (4 for Project A, 1 unclaimed)
  - 4 placement records
  - 3 dependency edges (nginx→springboot, springboot→redis, springboot→mysql)
  - Expected Project A bill: ¥10,000 (3000 + 4000 + 3000)

Usage:
  cd backend && python -m app.seed.v0_6_seed
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.database import SessionLocal, utc_now
from app.models.project import Project
from app.models.host_resource import HostResource
from app.models.consuming_unit import ConsumingUnit
from app.models.placement import Placement
from app.models.unit_relation import UnitRelation


def _now_iso() -> str:
    """ISO string for placement.observed_at (String column)"""
    return datetime.now(timezone.utc).isoformat()


def _now_utc() -> datetime:
    """datetime object for model timestamps (DateTime column)"""
    return utc_now()


def _uid() -> str:
    return str(uuid.uuid4())


def seed_v06(db: Session | None = None) -> None:
    """Create v0.6 demo data. Idempotent — skips if data already exists."""
    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True

    try:
        # Idempotency check: skip if projects already exist
        existing = db.query(Project).count()
        if existing > 0:
            print("[seed] v0.6 data already exists, skipping.")
            return

        now = _now_utc()
        now_iso = _now_iso()

        # ── Projects ────────────────────────────────────────────
        proj_a = Project(
            id="proj-a", name="电商核心交易", business_unit="交易中台",
            owner="PM 张", billing_enabled=1, created_at=now, updated_at=now,
        )
        proj_b = Project(
            id="proj-b", name="数据中台", business_unit="数据平台",
            owner="PM 刘", billing_enabled=0, created_at=now, updated_at=now,
        )
        db.add_all([proj_a, proj_b])
        db.flush()

        # ── Host Resources ──────────────────────────────────────
        # node-1: 1.0 core, 512 MB, ¥3,000 — nginx alone (full capacity)
        # node-2: 8.5 core, 8704 MB, ¥4,000 — springboot + redis (full capacity)
        # node-3: 4.0 core, 6827 MB, ¥5,000 — mysql + project-B component (shared)
        # zombie-host: has cost but no placements
        host1 = HostResource(
            id="node-1", name="node-1", ip_address="172.16.1.1", type="physical",
            cpu_total=1.0, mem_total=512, monthly_cost=3000,
            source="cmdb", created_at=now, updated_at=now,
        )
        host2 = HostResource(
            id="node-2", name="node-2", ip_address="172.16.1.2", type="physical",
            cpu_total=8.5, mem_total=8704, monthly_cost=4000,
            source="cmdb", created_at=now, updated_at=now,
        )
        host3 = HostResource(
            id="node-3", name="node-3", ip_address="172.16.1.3", type="physical",
            cpu_total=4.0, mem_total=6827, monthly_cost=5000,
            source="cmdb", created_at=now, updated_at=now,
        )
        zombie = HostResource(
            id="zombie-host", name="zombie-host", ip_address="172.16.1.99", type="physical",
            cpu_total=2.0, mem_total=4096, monthly_cost=520,
            source="cmdb", created_at=now, updated_at=now,
        )
        db.add_all([host1, host2, host3, zombie])
        db.flush()

        # ── Consuming Units ─────────────────────────────────────
        # Project A: 4 units
        u_nginx = ConsumingUnit(
            id="u-nginx", project_id="proj-a", name="nginx 反向代理",
            type="k8s_workload", owner="运维 李", environment="prod",
            created_at=now, updated_at=now,
        )
        u_spring = ConsumingUnit(
            id="u-spring", project_id="proj-a", name="springboot 应用",
            type="k8s_workload", owner="开发 王", environment="prod",
            created_at=now, updated_at=now,
        )
        u_redis = ConsumingUnit(
            id="u-redis", project_id="proj-a", name="redis 缓存",
            type="k8s_workload", owner="开发 王", environment="prod",
            created_at=now, updated_at=now,
        )
        u_mysql = ConsumingUnit(
            id="u-mysql", project_id="proj-a", name="mysql 数据库",
            type="k8s_workload", owner="DBA 赵", environment="prod",
            created_at=now, updated_at=now,
        )
        # Project B: 1 unit on node-3
        u_b_comp = ConsumingUnit(
            id="u-b-comp", project_id="proj-b", name="项目B 组件",
            type="k8s_workload", owner="开发 陈", environment="prod",
            created_at=now, updated_at=now,
        )
        # Unclaimed unit (no project)
        u_unclaimed = ConsumingUnit(
            id="u-orphan", project_id=None, name="orphan-batch-processor",
            type="docker", owner=None, environment="dev",
            created_at=now, updated_at=now,
        )
        db.add_all([u_nginx, u_spring, u_redis, u_mysql, u_b_comp, u_unclaimed])
        db.flush()

        # ── Placements ──────────────────────────────────────────
        # node-1: nginx 0.5×2 cpu=1.0, mem=512 (full)
        p1 = Placement(
            id="p-nginx-1", unit_id="u-nginx", host_id="node-1",
            cpu_request=0.5, mem_request=256, instances=2,
            source="k8s", observed_at="2026-06-24T00:00:00Z",
        )
        # node-2: springboot 2×4 cpu=8.0, mem=8192 (almost full)
        p2 = Placement(
            id="p-spring-2", unit_id="u-spring", host_id="node-2",
            cpu_request=2.0, mem_request=2048, instances=4,
            source="k8s", observed_at="2026-06-24T00:00:00Z",
        )
        # node-2: redis 0.5×1 cpu=0.5, mem=512
        p3 = Placement(
            id="p-redis-2", unit_id="u-redis", host_id="node-2",
            cpu_request=0.5, mem_request=512, instances=1,
            source="k8s", observed_at="2026-06-24T00:00:00Z",
        )
        # node-3: mysql 2×1 cpu=2.0, mem=4096
        p4 = Placement(
            id="p-mysql-3", unit_id="u-mysql", host_id="node-3",
            cpu_request=2.0, mem_request=4096, instances=1,
            source="k8s", observed_at="2026-06-24T00:00:00Z",
        )
        # node-3: project-B component: mem=2731, cpu~1.0 (to make mysql share ~0.6 by mem)
        p5 = Placement(
            id="p-bcomp-3", unit_id="u-b-comp", host_id="node-3",
            cpu_request=1.0, mem_request=2731, instances=1,
            source="k8s", observed_at="2026-06-24T00:00:00Z",
        )
        db.add_all([p1, p2, p3, p4, p5])
        db.flush()

        # ── Dependency Edges (unit_relation) ────────────────────
        r1 = UnitRelation(
            id="r1", source_unit_id="u-nginx", target_unit_id="u-spring",
            rel_type="HTTP", source="manual", created_at=now,
        )
        r2 = UnitRelation(
            id="r2", source_unit_id="u-spring", target_unit_id="u-redis",
            rel_type="cache", source="manual", created_at=now,
        )
        r3 = UnitRelation(
            id="r3", source_unit_id="u-spring", target_unit_id="u-mysql",
            rel_type="SQL", source="manual", created_at=now,
        )
        db.add_all([r1, r2, r3])

        db.commit()
        print("[seed] v0.6 data seeded successfully.")
        print("  - 2 projects (A: billing on, B: billing off)")
        print("  - 4 hosts (3 real + 1 zombie)")
        print("  - 6 consuming units (4 project-A + 1 project-B + 1 unclaimed)")
        print("  - 5 placements")
        print("  - 3 dependency edges")
        print("  - Expected Project A bill: CNY 10,000")

    except Exception:
        db.rollback()
        raise
    finally:
        if close_session:
            db.close()


if __name__ == "__main__":
    seed_v06()
