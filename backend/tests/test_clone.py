from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import main
from app.cache import coverage_grid, png_path, read_meta
from app.db import init_db
from app.store import CloneError, clone_layer, create_layer, get_layer, list_layers


def _make_layer(db: Path, slug: str = "src-layer", max_z: int = 1) -> dict:
    return create_layer(
        db,
        {
            "slug": slug,
            "name": "源图层",
            "description": "带瓦片",
            "provider": "procedural",
            "default_scheme": "xyz",
            "min_z": 0,
            "max_z": max_z,
        },
    )


def test_clone_metadata_only(tmp_path: Path):
    db = tmp_path / "data" / "x.db"
    init_db(db)
    _make_layer(db)

    cloned = clone_layer(db, tmp_path / "data", "src-layer", "dst-layer")

    assert cloned["slug"] == "dst-layer"
    assert cloned["name"] == "源图层 副本"
    for key in ("description", "provider", "default_scheme", "min_z", "max_z"):
        assert cloned[key] == get_layer(db, "src-layer")[key]
    assert cloned["tiles_copied"] == 0
    assert not (tmp_path / "data" / "layers" / "dst-layer").exists()
    assert {l["slug"] for l in list_layers(db)} == {"src-layer", "dst-layer"}


def test_clone_with_tiles_copies_pyramid(tmp_path: Path):
    data_dir = tmp_path / "data"
    db = data_dir / "x.db"
    init_db(db)
    _make_layer(db)
    from app.cache import write_tile

    write_tile(data_dir, "src-layer", "xyz", 1, 0, 0, 1, 0, 0)
    src_png = png_path(data_dir, "src-layer", "xyz", 1, 0, 0)

    cloned = clone_layer(db, data_dir, "src-layer", "dst-layer", copy_tiles=True)

    assert cloned["tiles_copied"] == 1
    dst_png = png_path(data_dir, "dst-layer", "xyz", 1, 0, 0)
    assert dst_png.read_bytes() == src_png.read_bytes()
    assert read_meta(data_dir, "dst-layer", "xyz", 1, 0, 0)["baked_z"] == 1
    # 覆盖率与源图层一致，可直接在新图层上核对。
    assert coverage_grid(data_dir, "dst-layer", "xyz", 1)["counts"] == coverage_grid(
        data_dir, "src-layer", "xyz", 1
    )["counts"]


def test_clone_keeps_source_intact(tmp_path: Path):
    data_dir = tmp_path / "data"
    db = data_dir / "x.db"
    init_db(db)
    _make_layer(db)
    from app.cache import write_tile

    write_tile(data_dir, "src-layer", "xyz", 0, 0, 0, 0, 0, 0)

    clone_layer(db, data_dir, "src-layer", "dst-layer", copy_tiles=True)

    # 修改克隆层的瓦片不影响原图层。
    png_path(data_dir, "dst-layer", "xyz", 0, 0, 0).unlink()
    assert png_path(data_dir, "src-layer", "xyz", 0, 0, 0).exists()
    assert get_layer(db, "src-layer") is not None


def test_clone_unknown_source(tmp_path: Path):
    db = tmp_path / "x.db"
    init_db(db)
    with pytest.raises(CloneError) as exc:
        clone_layer(db, tmp_path, "ghost", "dst-layer")
    assert exc.value.status_code == 404
    assert "ghost" in str(exc.value)


def test_clone_slug_conflict(tmp_path: Path):
    db = tmp_path / "x.db"
    init_db(db)
    _make_layer(db)
    _make_layer(db, slug="dst-layer")
    with pytest.raises(CloneError) as exc:
        clone_layer(db, tmp_path, "src-layer", "dst-layer")
    assert exc.value.status_code == 409
    assert "dst-layer" in str(exc.value)


def test_clone_same_slug_rejected(tmp_path: Path):
    db = tmp_path / "x.db"
    init_db(db)
    _make_layer(db)
    with pytest.raises(CloneError) as exc:
        clone_layer(db, tmp_path, "src-layer", "src-layer")
    assert exc.value.status_code == 400


def test_clone_copy_tiles_without_pyramid(tmp_path: Path):
    data_dir = tmp_path / "data"
    db = data_dir / "x.db"
    init_db(db)
    _make_layer(db)  # 只建元数据，不写任何瓦片目录
    with pytest.raises(CloneError) as exc:
        clone_layer(db, data_dir, "src-layer", "dst-layer", copy_tiles=True)
    assert exc.value.status_code == 400
    assert get_layer(db, "dst-layer") is None


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    data_dir = tmp_path / "data"
    monkeypatch.setattr(main, "DATA_DIR", data_dir)
    monkeypatch.setattr(main, "DB_PATH", data_dir / "skewgrid.db")
    with TestClient(main.app) as client:
        yield client


def test_api_clone_with_tiles_listable_and_tile_served(client: TestClient):
    res = client.post(
        "/api/layers/demo-grid/clone",
        json={"target_slug": "demo-copy", "copy_tiles": True},
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["slug"] == "demo-copy"
    assert body["max_z"] == 3
    assert body["tiles_copied"] > 0

    slugs = {l["slug"] for l in client.get("/api/layers").json()}
    assert {"demo-grid", "demo-copy"} <= slugs

    # 克隆层地图能取到瓦，覆盖率与含缺口的源图层一致。
    tile = client.get("/tiles/demo-copy/xyz/0/0/0.png")
    assert tile.status_code == 200
    assert tile.headers["content-type"] == "image/png"
    src_counts = client.get("/api/layers/demo-grid/coverage?z=2").json()["counts"]
    dst_counts = client.get("/api/layers/demo-copy/coverage?z=2").json()["counts"]
    assert dst_counts == src_counts

    # 原图层数据仍可访问。
    assert client.get("/tiles/demo-grid/xyz/0/0/0.png").status_code == 200


def test_api_clone_metadata_only(client: TestClient):
    res = client.post(
        "/api/layers/clean-atlas/clone",
        json={"target_slug": "atlas-meta", "name": "仅元数据副本"},
    )
    assert res.status_code == 201, res.text
    assert res.json()["name"] == "仅元数据副本"
    # 没有瓦片目录，地图请求应返回 tile not cached。
    assert client.get("/tiles/atlas-meta/xyz/0/0/0.png").status_code == 404


def test_api_clone_errors_are_readable(client: TestClient):
    missing = client.post("/api/layers/nope/clone", json={"target_slug": "nope-copy"})
    assert missing.status_code == 404
    assert "nope" in missing.json()["detail"]

    client.post("/api/layers/demo-grid/clone", json={"target_slug": "dup-copy"})
    conflict = client.post(
        "/api/layers/demo-grid/clone", json={"target_slug": "dup-copy"}
    )
    assert conflict.status_code == 409
    assert "dup-copy" in conflict.json()["detail"]

    bad_slug = client.post("/api/layers/demo-grid/clone", json={"target_slug": "BAD SLUG"})
    assert bad_slug.status_code == 422

    # 只有元数据、没有金字塔目录的图层，请求拷贝瓦片时返回可读的 400。
    client.post("/api/layers", json={"slug": "empty-one", "name": "空", "max_z": 1})
    no_tiles = client.post(
        "/api/layers/empty-one/clone",
        json={"target_slug": "empty-copy", "copy_tiles": True},
    )
    assert no_tiles.status_code == 400
    assert "金字塔" in no_tiles.json()["detail"]
    assert client.get("/api/layers/empty-copy").status_code == 404
