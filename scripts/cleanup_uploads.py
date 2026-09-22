#!/usr/bin/env python3
"""
清理 backend/uploads/ 下的历史明文扫描文件（.xml / .xlsx / .json）。

扫描数据在解析时已进入加密数据库（scan_snapshot_items），原始上传文件自上传后
无任何读取方（见安全审计 V7）。删除它们可消除加密数据库之外的明文暴露。

用法（仓库根目录）：
  python scripts/cleanup_uploads.py          # 预览待删清单
  python scripts/cleanup_uploads.py --yes    # 执行删除
"""
import argparse
import pathlib

SUFFIXES = {".xml", ".xlsx", ".json"}


def uploads_dir() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parent.parent / "backend" / "uploads"


def collect_files(target_dir: pathlib.Path) -> list[pathlib.Path]:
    if not target_dir.exists():
        return []
    return [
        p for p in target_dir.iterdir()
        if p.is_file() and p.suffix.lower() in SUFFIXES
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="清理历史明文扫描文件")
    parser.add_argument("--yes", action="store_true", help="确认执行删除（默认仅预览）")
    args = parser.parse_args()

    target = uploads_dir()
    files = collect_files(target)
    if not files:
        print("没有需要清理的文件")
        return

    for p in files:
        print(f"  {p.name}")
    print(f"共 {len(files)} 个文件")

    if not args.yes:
        print("预览模式 — 加 --yes 执行删除")
        return

    for p in files:
        p.unlink()
    print(f"已删除 {len(files)} 个文件")


if __name__ == "__main__":
    main()
