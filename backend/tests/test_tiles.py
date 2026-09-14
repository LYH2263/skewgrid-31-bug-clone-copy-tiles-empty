from pathlib import Path

from app.cache import scan_layer, write_tile
from app.exporters.geojson import issues_to_geojson
from app.exporters.mbtiles import MbtilesNotImplemented, export_mbtiles
from app.tiles import tms_y


def test_tms_roundtrip():
    assert tms_y(2, 0) == 3
    assert tms_y(2, tms_y(2, 1)) == 1


def test_scan_finds_flip_and_gap(tmp_path: Path):
    write_tile(tmp_path, "demo", "xyz", 1, 0, 0, 1, 0, 0)
    write_tile(tmp_path, "demo", "xyz", 1, 0, 1, 1, 0, 0)
    write_tile(tmp_path, "demo", "xyz", 1, 1, 0, 1, 1, 0)
    issues = scan_layer(tmp_path, "demo", "xyz", 1)
    kinds = {(i["kind"], i["x"], i["y"]) for i in issues if i["z"] == 1}
    assert ("y_flip", 0, 1) in kinds
    assert ("missing", 1, 1) in kinds


def test_geojson_has_polygon():
    geo = issues_to_geojson(
        "demo",
        [{"kind": "missing", "z": 1, "x": 0, "y": 0, "message": "gap"}],
    )
    assert geo["type"] == "FeatureCollection"
    assert geo["features"][0]["geometry"]["type"] == "Polygon"


def test_mbtiles_not_implemented(tmp_path: Path):
    try:
        export_mbtiles(tmp_path, tmp_path / "out.mbtiles")
        assert False, "should raise"
    except MbtilesNotImplemented:
        pass
