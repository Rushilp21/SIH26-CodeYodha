import type { GeoJSONPolygon } from "@shared/types";

const EARTH_RADIUS_M = 6_371_008.8;

function radians(value: number) { return value * Math.PI / 180; }

function ringAreaSquareMetres(ring: number[][]) {
  const area = ring.slice(1).reduce((total, point, index) => {
    const previous = ring[index];
    return total + radians(point[0] - previous[0]) * (2 + Math.sin(radians(previous[1])) + Math.sin(radians(point[1])));
  }, 0);
  return Math.abs(area * EARTH_RADIUS_M * EARTH_RADIUS_M / 2);
}

function triangleArea(a: number[], b: number[], c: number[]) {
  return Math.abs((a[0] * (b[1] - c[1]) + b[0] * (c[1] - a[1]) + c[0] * (a[1] - b[1])) / 2);
}

/**
 * Keeps the most shape-defining vertices by repeatedly removing the point
 * with the smallest local triangle. The returned ring remains closed.
 */
function simplifyRing(ring: number[][], target: number) {
  const points = ring.slice(0, -1).map((point) => [...point]);
  const keep = Math.max(3, Math.min(target, points.length));
  while (points.length > keep) {
    let removeIndex = 0;
    let smallestArea = Number.POSITIVE_INFINITY;
    for (let index = 0; index < points.length; index += 1) {
      const area = triangleArea(points[(index - 1 + points.length) % points.length], points[index], points[(index + 1) % points.length]);
      if (area < smallestArea) {
        smallestArea = area;
        removeIndex = index;
      }
    }
    points.splice(removeIndex, 1);
  }
  return [...points, [...points[0]]];
}

/** Large or highly detailed parcels get ten edit handles; smaller parcels get five. */
export function simplifyGeometryForEditing(geometry: GeoJSONPolygon): GeoJSONPolygon {
  const outer = geometry.coordinates[0];
  const vertexCount = Math.max(0, outer.length - 1);
  const outerTarget = ringAreaSquareMetres(outer) >= 5_000 || vertexCount > 40 ? 10 : 5;
  return {
    type: "Polygon",
    coordinates: geometry.coordinates.map((ring, index) => simplifyRing(ring, index === 0 ? outerTarget : 4)),
  };
}

export function editableVertexCount(geometry: GeoJSONPolygon) {
  return geometry.coordinates.reduce((total, ring) => total + Math.max(0, ring.length - 1), 0);
}
