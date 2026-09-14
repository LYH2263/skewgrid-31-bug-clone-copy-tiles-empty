import type { LatLngBoundsExpression } from "leaflet";

export function tile2lat(y: number, z: number) {
  const n = Math.PI - (2 * Math.PI * y) / 2 ** z;
  return (180 / Math.PI) * Math.atan(0.5 * (Math.exp(n) - Math.exp(-n)));
}

export function tileBounds(z: number, x: number, y: number): LatLngBoundsExpression {
  const n = 2 ** z;
  const west = (x / n) * 360 - 180;
  const east = ((x + 1) / n) * 360 - 180;
  const north = tile2lat(y, z);
  const south = tile2lat(y + 1, z);
  return [
    [south, west],
    [north, east],
  ];
}
