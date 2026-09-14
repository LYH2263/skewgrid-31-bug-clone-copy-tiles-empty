from datetime import datetime, timezone
from pathlib import Path

from app.cache import meta_path, png_path, write_tile
from app.db import init_db, session
from app.tiles import grid_size, tms_y


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _fill(root: Path, slug: str, max_z: int) -> None:
    for z in range(max_z + 1):
        n = grid_size(z)
        for x in range(n):
            for y in range(n):
                write_tile(root, slug, "xyz", z, x, y, z, x, y)


def seed_if_empty(root: Path, db_path: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    init_db(db_path)
    with session(db_path) as conn:
        count = conn.execute("SELECT COUNT(*) AS n FROM layers").fetchone()["n"]
    if count:
        return

    _fill(root, "demo-grid", 3)
    flips = [(2, 1, 0), (2, 2, 1), (3, 4, 2), (3, 1, 6)]
    for z, x, y in flips:
        wrong_y = tms_y(z, y)
        png_path(root, "demo-grid", "xyz", z, x, y).unlink(missing_ok=True)
        meta_path(root, "demo-grid", "xyz", z, x, y).unlink(missing_ok=True)
        write_tile(root, "demo-grid", "xyz", z, x, wrong_y, z, x, y)
    for z, x, y in [(1, 0, 1), (3, 7, 0), (3, 2, 5)]:
        png_path(root, "demo-grid", "xyz", z, x, y).unlink(missing_ok=True)
        meta_path(root, "demo-grid", "xyz", z, x, y).unlink(missing_ok=True)

    _fill(root, "clean-atlas", 2)

    with session(db_path) as conn:
        conn.execute(
            """INSERT INTO layers (slug, name, description, provider, default_scheme, min_z, max_z, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "demo-grid",
                "演示网格（含错层）",
                "种子种植了 TMS/XYZ y 翻转和缺口，用来出 Bugfix / 扫描题。",
                "procedural",
                "xyz",
                0,
                3,
                _now(),
            ),
        )
        conn.execute(
            """INSERT INTO layers (slug, name, description, provider, default_scheme, min_z, max_z, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "clean-atlas",
                "干净图集",
                "z=0..2 全部对齐，对照层。可在此做 Feature：提高 max_z、换 provider。",
                "procedural",
                "xyz",
                0,
                2,
                _now(),
            ),
        )
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?), (?, ?) ON CONFLICT(key) DO NOTHING",
            ("default_scheme", "xyz", "scan_max_z_cap", "6"),
        )
