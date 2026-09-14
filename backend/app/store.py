import shutil
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from app.cache import layer_root, scan_layer, write_tile
from app.db import row_dict, session
from app.exporters.geojson import issues_to_geojson
from app.exporters.mbtiles import MbtilesNotImplemented, export_mbtiles
from app.tiles import grid_size, valid_coord


class CloneError(Exception):
    """克隆图层失败，status_code 对应 HTTP 响应码。"""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def list_layers(db: Path) -> list[dict]:
    with session(db) as conn:
        rows = conn.execute("SELECT * FROM layers ORDER BY id").fetchall()
    return [dict(r) for r in rows]


def get_layer(db: Path, slug: str) -> dict | None:
    with session(db) as conn:
        row = conn.execute("SELECT * FROM layers WHERE slug = ?", (slug,)).fetchone()
    return row_dict(row)


def create_layer(db: Path, body: dict) -> dict:
    slug = body["slug"]
    with session(db) as conn:
        conn.execute(
            """INSERT INTO layers (slug, name, description, provider, default_scheme, min_z, max_z, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                slug,
                body.get("name") or slug,
                body.get("description") or "",
                body.get("provider") or "procedural",
                body.get("default_scheme") or "xyz",
                int(body.get("min_z") or 0),
                int(body.get("max_z") or 3),
                _now(),
            ),
        )
    return get_layer(db, slug)


def clone_layer(
    db: Path,
    data_dir: Path,
    source_slug: str,
    target_slug: str,
    *,
    name: str | None = None,
    description: str | None = None,
    copy_tiles: bool = False,
) -> dict:
    """把源图层元数据复制为新 slug；copy_tiles 时连同本地金字塔目录一起拷贝。

    只复制 layers 表元数据与磁盘瓦片；scan_runs / jobs / repair_log 属于源图层
    的历史记录，不带入新图层。
    """
    source = get_layer(db, source_slug)
    if not source:
        raise CloneError(f"源图层不存在：{source_slug}", status_code=404)
    if target_slug == source_slug:
        raise CloneError("新 slug 不能与源图层相同")
    if get_layer(db, target_slug):
        raise CloneError(f"slug 已被占用：{target_slug}", status_code=409)

    src_root = layer_root(data_dir, source_slug)
    dst_root = layer_root(data_dir, target_slug)
    tiles_copied = 0
    if copy_tiles:
        if not src_root.exists():
            raise CloneError(
                f"源图层没有本地金字塔目录（{src_root}），无法拷贝瓦片；"
                "可取消“拷贝瓦片”仅克隆元数据"
            )
        if dst_root.exists():
            raise CloneError(f"目标金字塔目录已存在：{dst_root}", status_code=409)
        tiles_copied = sum(1 for _ in src_root.rglob("*.png"))
        shadow = data_dir / ".clone_shadow" / target_slug
        if shadow.exists():
            shutil.rmtree(shadow)
        shutil.copytree(src_root, shadow)

    try:
        with session(db) as conn:
            conn.execute(
                """INSERT INTO layers (slug, name, description, provider, default_scheme, min_z, max_z, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    target_slug,
                    (name or "").strip() or f"{source['name']} 副本",
                    source["description"] if description is None else description,
                    source["provider"],
                    source["default_scheme"],
                    source["min_z"],
                    source["max_z"],
                    _now(),
                ),
            )
    except sqlite3.IntegrityError as exc:
        # 并发请求可能绕过前面的存在性检查，靠 UNIQUE 约束兜底并回滚已拷贝文件。
        if copy_tiles:
            shutil.rmtree(data_dir / ".clone_shadow" / target_slug, ignore_errors=True)
        raise CloneError(f"slug 已被占用：{target_slug}", status_code=409) from exc

    layer = get_layer(db, target_slug)
    layer["tiles_copied"] = tiles_copied
    return layer


def run_scan(db: Path, data_dir: Path, slug: str, scheme: str, max_z: int) -> dict:
    layer = get_layer(db, slug)
    if not layer:
        raise KeyError(slug)
    max_z = min(max_z, int(layer["max_z"]))
    issues = scan_layer(data_dir, slug, scheme, max_z)
    counts = Counter(i["kind"] for i in issues)
    with session(db) as conn:
        cur = conn.execute(
            """INSERT INTO scan_runs (layer_slug, scheme, max_z, status, total, missing, y_flip, meta_missing, created_at, finished_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                slug,
                scheme,
                max_z,
                "done",
                len(issues),
                counts.get("missing", 0),
                counts.get("y_flip", 0),
                counts.get("meta_missing", 0),
                _now(),
                _now(),
            ),
        )
        run_id = cur.lastrowid
        for issue in issues:
            conn.execute(
                """INSERT INTO scan_issues (run_id, kind, z, x, y, message)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (run_id, issue["kind"], issue["z"], issue["x"], issue["y"], issue["message"]),
            )
    return get_scan(db, run_id)


def list_scans(db: Path, slug: str | None = None) -> list[dict]:
    sql = "SELECT * FROM scan_runs"
    args: list = []
    if slug:
        sql += " WHERE layer_slug = ?"
        args.append(slug)
    sql += " ORDER BY id DESC"
    with session(db) as conn:
        rows = conn.execute(sql, args).fetchall()
    return [dict(r) for r in rows]


def get_scan(db: Path, run_id: int) -> dict | None:
    with session(db) as conn:
        run = conn.execute("SELECT * FROM scan_runs WHERE id = ?", (run_id,)).fetchone()
        if not run:
            return None
        issues = conn.execute(
            "SELECT * FROM scan_issues WHERE run_id = ? ORDER BY z, x, y", (run_id,)
        ).fetchall()
    data = dict(run)
    data["issues"] = [dict(i) for i in issues]
    return data


def repair_tile(db: Path, data_dir: Path, slug: str, scheme: str, z: int, x: int, y: int) -> None:
    if not valid_coord(z, x, y):
        raise ValueError("invalid coord")
    write_tile(data_dir, slug, scheme, z, x, y, z, x, y)
    with session(db) as conn:
        conn.execute(
            """INSERT INTO repair_log (layer_slug, z, x, y, action, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (slug, z, x, y, "rewrite_aligned", _now()),
        )


def list_repairs(db: Path, slug: str) -> list[dict]:
    with session(db) as conn:
        rows = conn.execute(
            "SELECT * FROM repair_log WHERE layer_slug = ? ORDER BY id DESC LIMIT 100",
            (slug,),
        ).fetchall()
    return [dict(r) for r in rows]


def run_job(db: Path, data_dir: Path, slug: str, kind: str, payload: dict) -> dict:
    layer = get_layer(db, slug)
    if not layer:
        raise KeyError(slug)
    created = _now()
    with session(db) as conn:
        cur = conn.execute(
            """INSERT INTO jobs (layer_slug, kind, status, payload, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (slug, kind, "running", str(payload), created),
        )
        job_id = cur.lastrowid

    result = ""
    status = "done"
    try:
        if kind == "prerender":
            z = int(payload.get("z", layer["max_z"]))
            n = grid_size(z)
            written = 0
            for x in range(n):
                for y in range(n):
                    write_tile(data_dir, slug, "xyz", z, x, y, z, x, y)
                    written += 1
            result = f"wrote {written} tiles at z={z}"
        elif kind == "repair_all":
            scans = list_scans(db, slug)
            if not scans:
                result = "no scan yet"
            else:
                detail = get_scan(db, scans[0]["id"])
                n = 0
                for issue in detail["issues"]:
                    repair_tile(db, data_dir, slug, "xyz", issue["z"], issue["x"], issue["y"])
                    n += 1
                result = f"repaired {n} tiles"
        elif kind == "export_geojson":
            scans = list_scans(db, slug)
            if not scans:
                raise RuntimeError("先跑一次扫描再导出")
            detail = get_scan(db, scans[0]["id"])
            geo = issues_to_geojson(slug, detail["issues"])
            dest = data_dir / "exports" / f"{slug}-issues.geojson"
            dest.parent.mkdir(parents=True, exist_ok=True)
            import json

            dest.write_text(json.dumps(geo, ensure_ascii=False, indent=2), encoding="utf-8")
            result = str(dest)
        elif kind == "export_mbtiles":
            export_mbtiles(data_dir / "layers" / slug, data_dir / "exports" / f"{slug}.mbtiles")
        else:
            raise RuntimeError(f"unknown job kind {kind}")
    except MbtilesNotImplemented as exc:
        status = "blocked"
        result = str(exc)
    except Exception as exc:  # noqa: BLE001
        status = "failed"
        result = str(exc)

    with session(db) as conn:
        conn.execute(
            "UPDATE jobs SET status = ?, result = ?, finished_at = ? WHERE id = ?",
            (status, result, _now(), job_id),
        )
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    return dict(row)


def list_jobs(db: Path) -> list[dict]:
    with session(db) as conn:
        rows = conn.execute("SELECT * FROM jobs ORDER BY id DESC").fetchall()
    return [dict(r) for r in rows]


def get_setting(db: Path, key: str, default: str = "") -> str:
    with session(db) as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(db: Path, key: str, value: str) -> None:
    with session(db) as conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )


def all_settings(db: Path) -> dict:
    with session(db) as conn:
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
    return {r["key"]: r["value"] for r in rows}
