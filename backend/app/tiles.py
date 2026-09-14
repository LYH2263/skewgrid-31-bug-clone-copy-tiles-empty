def tms_y(z: int, y: int) -> int:
    """TMS y origin is south; XYZ / slippy-map y origin is north."""
    return (1 << z) - 1 - y


def xyz_y_from_tms(z: int, tms: int) -> int:
    return tms_y(z, tms)


def grid_size(z: int) -> int:
    return 1 << z


def valid_coord(z: int, x: int, y: int) -> bool:
    if z < 0 or z > 8:
        return False
    n = grid_size(z)
    return 0 <= x < n and 0 <= y < n
