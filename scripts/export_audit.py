#!/usr/bin/env python3
"""
CLI 导出审计日志（绕过 Web，用于应急或离线审计）
用法：python scripts/export_audit.py [--output audit_report.csv]
"""
import argparse
import csv
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))


def main():
    parser = argparse.ArgumentParser(description="导出 Z-CMDB Lite 审计日志")
    parser.add_argument(
        "--output", "-o",
        default="audit_report.csv",
        help="输出文件路径（默认 audit_report.csv）",
    )
    parser.add_argument(
        "--limit", "-n",
        type=int,
        default=0,
        help="最大导出条数（0 = 全部）",
    )
    args = parser.parse_args()

    from app.core.database import SessionLocal
    from app.services import audit_service

    print(f"正在导出审计日志到 {args.output} ...")

    with SessionLocal() as db:
        limit = args.limit if args.limit > 0 else 1000000
        logs, total = audit_service.list_logs(db, page=1, page_size=limit)

        with open(args.output, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow([
                "ID", "时间", "用户ID", "用户名", "角色",
                "操作类型", "目标类型", "目标ID", "来源IP", "结果", "详情",
            ])
            for log in logs:
                writer.writerow([
                    log.id,
                    log.timestamp.isoformat(),
                    log.user_id,
                    log.username,
                    log.user_role,
                    log.action_type,
                    log.target_type,
                    log.target_id,
                    log.ip_address,
                    log.result,
                    log.details or "",
                ])

        print(f"完成！共导出 {len(logs)} 条记录（总计 {total} 条）")


if __name__ == "__main__":
    main()
