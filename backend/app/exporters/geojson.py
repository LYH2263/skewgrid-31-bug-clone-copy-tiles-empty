from app.tiles import grid_size


def issues_to_geojson(layer_slug: str, issues: list[dict]) -> dict:
    """Export scan issues as polygon features in WGS84 tile bounds."""
    features = []
    for issue in issues:
        z, x, y = issue["z"], issue["x"], issue["y"]
        west, south, east, north = _tile_bbox(z, x, y)
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "layer": layer_slug,
                    "kind": issue["kind"],
                    "z": z,
                    "x": x,
                    "y": y,
                    "message": issue["message"],
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [west, south],
                            [east, south],
                            [east, north],
                            [west, north],
                            [west, south],
                        ]
                    ],
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


def _tile_bbox(z: int, x: int, y: int) -> tuple[float, float, float, float]:
    n = float(grid_size(z))
    west = x / n * 360.0 - 180.0
    east = (x + 1) / n * 360.0 - 180.0

    def lat(ty: float) -> float:
        import math

        rad = math.pi - 2.0 * math.pi * ty / n
        return 180.0 / math.pi * math.atan(math.sinh(rad))

    north = lat(y)
    south = lat(y + 1)
    return west, south, east, north
