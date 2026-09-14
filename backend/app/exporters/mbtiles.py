"""
0-1 扩展点：把某图层本地 PNG 金字塔打成 MBTiles。

预期：创建 SQLite，表 tiles(zoom_level, tile_column, tile_row, tile_data)
与 metadata；TMS row 与 XYZ y 的换算必须走 app.tiles.tms_y。
路由 POST /api/layers/{slug}/export?format=mbtiles 现在返回 501。
"""


class MbtilesNotImplemented(NotImplementedError):
    pass


def export_mbtiles(layer_root, dest_path) -> None:
    raise MbtilesNotImplemented(
        "MBTiles 导出未实现。见 app/exporters/mbtiles.py 顶部说明。"
    )
