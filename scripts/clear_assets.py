#!/usr/bin/env python3
"""
Clear all asset data from the database.
Usage: cd backend && python ../scripts/clear_assets.py
Requires: backend directory, activated venv.

Cleans: assets, asset_ports, asset_apps, asset_cost_items,
        asset_dept_assignments, asset_relations.
Preserves: scan_snapshot_items (sets matched_asset_id to NULL),
           users, audit_logs, system_configs, scan_batches, etc.
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))


TABLES = [
    "assets",
    "asset_ports",
    "asset_apps",
    "asset_cost_items",
    "asset_dept_assignments",
    "asset_relations",
]


def main():
    import sqlite3

    db_path = backend_dir / "data" / "cmdb.db"
    if not db_path.exists():
        print(f"Database not found: {db_path}")
        sys.exit(1)

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    c = conn.cursor()

    # Show current counts
    print("=" * 50)
    print("  Z-CMDB Lite - Clear Asset Data")
    print("=" * 50)
    print("\nBefore cleanup:")
    total_before = 0
    for t in TABLES:
        c.execute(f"SELECT COUNT(*) FROM {t}")
        count = c.fetchone()[0]
        total_before += count
        print(f"  {t}: {count}")

    c.execute("SELECT COUNT(*) FROM scan_snapshot_items")
    snapshot_count = c.fetchone()[0]
    print(f"  scan_snapshot_items: {snapshot_count} (will keep, FK set to NULL)")

    if total_before == 0:
        print("\nNo asset data to clear.")
        conn.close()
        return

    # Confirm
    print(f"\nThis will delete {total_before} records across {len(TABLES)} tables.")
    answer = input("Continue? [y/N] ").strip().lower()
    if answer != "y":
        print("Cancelled.")
        conn.close()
        return

    # Clear snapshot FK references first (no CASCADE on this column)
    c.execute("UPDATE scan_snapshot_items SET matched_asset_id = NULL WHERE matched_asset_id IS NOT NULL")

    # Delete assets — CASCADE handles the rest
    c.execute("DELETE FROM assets")
    deleted = c.rowcount
    conn.commit()

    # Show results
    print(f"\nDeleted {deleted} assets.")
    print("\nAfter cleanup:")
    for t in TABLES:
        c.execute(f"SELECT COUNT(*) FROM {t}")
        print(f"  {t}: {c.fetchone()[0]}")
    c.execute("SELECT COUNT(*) FROM scan_snapshot_items")
    print(f"  scan_snapshot_items: {c.fetchone()[0]} (preserved)")

    conn.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
