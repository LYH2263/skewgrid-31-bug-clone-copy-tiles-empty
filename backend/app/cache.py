import json
from pathlib import Path

from app.providers.procedural import ProceduralProvider
from app.tiles import grid_size


def layer_root(root: Path, slug: str) -> Path:
    return root / "layers" / slug


def tile_dir(root: Path, slug: str, scheme: str, z: int, x: int) -> Path:
    return layer_root(root, slug) / scheme / str(z) / str(x)


def png_path(root: Path, slug: str, scheme: str, z: int, x: int, y: int) -> Path:
    return tile_dir(root, slug, scheme, z, x) / f"{y}.png"


def meta_path(root: Path, slug: str, scheme: str, z: int, x: int, y: int) -> Path:
    return tile_dir(root, slug, scheme, z, x) / f"{y}.json"


def write_tile(
    root: Path,
    slug: str,
    scheme: str,
    z: int,
    x: int,
    y: int,
    baked_z: int,
    baked_x: int,
    baked_y: int,
) -> None:
    folder = tile_dir(root, slug, scheme, z, x)
    folder.mkdir(parents=True, exist_ok=True)
    ProceduralProvider().render(baked_z, baked_x, baked_y).save(
        png_path(root, slug, scheme, z, x, y)
    )
    meta = {
        "scheme": scheme,
        "z": z,
        "x": x,
        "y": y,
        "baked_z": baked_z,
        "baked_x": baked_x,
        "baked_y": baked_y,
    }
    meta_path(root, slug, scheme, z, x, y).write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )


def read_meta(root: Path, slug: str, scheme: str, z: int, x: int, y: int) -> dict | None:
    path = meta_path(root, slug, scheme, z, x, y)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def diagnose_one(root: Path, slug: str, scheme: str, z: int, x: int, y: int) -> dict:
    png = png_path(root, slug, scheme, z, x, y)
    if not png.exists():
        return {
            "kind": "missing",
            "z": z,
            "x": x,
            "y": y,
            "message": "缓存中没有这块瓦片",
        }
    meta = read_meta(root, slug, scheme, z, x, y)
    if meta is None:
        return {
            "kind": "meta_missing",
            "z": z,
            "x": x,
            "y": y,
            "message": "PNG 在但 sidecar 丢失或损坏",
        }
    if meta.get("baked_z") != z or meta.get("baked_x") != x or meta.get("baked_y") != y:
        return {
            "kind": "y_flip",
            "z": z,
            "x": x,
            "y": y,
            "message": (
                f"路径是 z={z} x={x} y={y}，像素烘焙的是 "
                f"z={meta.get('baked_z')} x={meta.get('baked_x')} y={meta.get('baked_y')}"
            ),
        }
    return {"kind": "ok", "z": z, "x": x, "y": y, "message": ""}


def scan_layer(root: Path, slug: str, scheme: str, max_z: int) -> list[dict]:
    issues: list[dict] = []
    for z in range(max_z + 1):
        n = grid_size(z)
        for x in range(n):
            for y in range(n):
                item = diagnose_one(root, slug, scheme, z, x, y)
                if item["kind"] != "ok":
                    item["scheme"] = scheme
                    issues.append(item)
    return issues


def coverage_grid(root: Path, slug: str, scheme: str, z: int) -> dict:
    n = grid_size(z)
    cells = []
    counts = {"ok": 0, "missing": 0, "y_flip": 0, "meta_missing": 0}
    for y in range(n):
        row = []
        for x in range(n):
            kind = diagnose_one(root, slug, scheme, z, x, y)["kind"]
            counts[kind] = counts.get(kind, 0) + 1
            row.append({"x": x, "y": y, "status": kind})
        cells.append(row)
    return {"z": z, "n": n, "counts": counts, "cells": cells}
