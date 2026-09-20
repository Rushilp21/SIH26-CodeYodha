import { useEffect, useMemo, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { GeoJSONPolygon } from "@shared/types";

type Vertex = { ringIndex: number; vertexIndex: number };

const EARTH_RADIUS_M = 6_371_008.8;

function featureCollection(geometry: GeoJSONPolygon) {
  return {
    polygon: { type: "Feature" as const, properties: {}, geometry },
    vertices: {
      type: "FeatureCollection" as const,
      features: geometry.coordinates.flatMap((ring, ringIndex) => ring.slice(0, -1).map((coordinate, vertexIndex) => ({
        type: "Feature" as const,
        properties: { ringIndex, vertexIndex },
        geometry: { type: "Point" as const, coordinates: coordinate },
      }))),
    },
  };
}

function updateSources(map: maplibregl.Map, geometry: GeoJSONPolygon) {
  const data = featureCollection(geometry);
  (map.getSource("edit-polygon") as maplibregl.GeoJSONSource | undefined)?.setData(data.polygon as never);
  (map.getSource("edit-vertices") as maplibregl.GeoJSONSource | undefined)?.setData(data.vertices as never);
}

function radians(value: number) { return value * Math.PI / 180; }

function ringPerimeter(ring: number[][]) {
  return ring.slice(1).reduce((total, point, index) => {
    const previous = ring[index];
    const lat1 = radians(previous[1]);
    const lat2 = radians(point[1]);
    const deltaLat = lat2 - lat1;
    const deltaLon = radians(point[0] - previous[0]);
    const a = Math.sin(deltaLat / 2) ** 2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin(deltaLon / 2) ** 2;
    return total + 2 * EARTH_RADIUS_M * Math.asin(Math.min(1, Math.sqrt(a)));
  }, 0);
}

function ringArea(ring: number[][]) {
  const area = ring.slice(1).reduce((total, point, index) => {
    const previous = ring[index];
    return total + radians(point[0] - previous[0]) * (2 + Math.sin(radians(previous[1])) + Math.sin(radians(point[1])));
  }, 0);
  return Math.abs(area * EARTH_RADIUS_M * EARTH_RADIUS_M / 2);
}

function measurements(geometry: GeoJSONPolygon) {
  const [outer, ...holes] = geometry.coordinates;
  return {
    area: Math.max(0, ringArea(outer) - holes.reduce((total, ring) => total + ringArea(ring), 0)),
    perimeter: geometry.coordinates.reduce((total, ring) => total + ringPerimeter(ring), 0),
  };
}

function formatDistance(value: number) { return value >= 1_000 ? `${(value / 1_000).toFixed(2)} km` : `${value.toFixed(1)} m`; }
function formatArea(value: number) { return value >= 1_000_000 ? `${(value / 1_000_000).toFixed(2)} km²` : `${Math.round(value).toLocaleString()} m²`; }

export function EditableParcelMap({ geometry, onChange }: { geometry: GeoJSONPolygon; onChange: (geometry: GeoJSONPolygon) => void }) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const geometryRef = useRef(geometry);
  const changeRef = useRef(onChange);
  const dragRef = useRef<Vertex | null>(null);
  const [ready, setReady] = useState(false);
  const [measure, setMeasure] = useState(false);
  const [mapError, setMapError] = useState<string | null>(null);
  const metrics = useMemo(() => measurements(geometry), [geometry]);

  useEffect(() => { changeRef.current = onChange; }, [onChange]);
  useEffect(() => {
    geometryRef.current = geometry;
    if (mapRef.current && ready) updateSources(mapRef.current, geometry);
  }, [geometry, ready]);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: {
        version: 8,
        sources: { basemap: { type: "raster", tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"], tileSize: 256, maxzoom: 19, attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' } },
        layers: [{ id: "basemap", type: "raster", source: "basemap" }],
      },
      center: [85.31, 23.345],
      zoom: 16,
      attributionControl: false,
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    map.addControl(new maplibregl.AttributionControl({ compact: true }), "bottom-right");

    const finishDrag = () => {
      if (!dragRef.current) return;
      dragRef.current = null;
      map.dragPan.enable();
      map.getCanvas().style.cursor = "";
      changeRef.current(geometryRef.current);
    };
    const moveVertex = (event: maplibregl.MapMouseEvent | maplibregl.MapTouchEvent) => {
      const active = dragRef.current;
      if (!active) return;
      const next: GeoJSONPolygon = { type: "Polygon", coordinates: geometryRef.current.coordinates.map((ring) => ring.map((point) => [...point])) };
      const ring = next.coordinates[active.ringIndex];
      if (!ring?.[active.vertexIndex]) return;
      ring[active.vertexIndex] = [event.lngLat.lng, event.lngLat.lat];
      if (active.vertexIndex === 0) ring[ring.length - 1] = [...ring[0]];
      geometryRef.current = next;
      updateSources(map, next);
      changeRef.current(next);
    };

    map.on("load", () => {
      const data = featureCollection(geometryRef.current);
      map.addSource("edit-polygon", { type: "geojson", data: data.polygon as never });
      map.addSource("edit-vertices", { type: "geojson", data: data.vertices as never });
      map.addLayer({ id: "edit-fill", type: "fill", source: "edit-polygon", paint: { "fill-color": "#1e5aa8", "fill-opacity": 0.2 } });
      map.addLayer({ id: "edit-line", type: "line", source: "edit-polygon", paint: { "line-color": "#f59e0b", "line-width": 3 } });
      map.addLayer({ id: "edit-vertices", type: "circle", source: "edit-vertices", paint: { "circle-radius": 6, "circle-color": "#ffffff", "circle-stroke-color": "#1e5aa8", "circle-stroke-width": 2.5 } });
      const ring = geometryRef.current.coordinates.flat();
      if (ring.length) {
        const bounds = ring.reduce((current, coordinate) => current.extend(coordinate as [number, number]), new maplibregl.LngLatBounds(ring[0] as [number, number], ring[0] as [number, number]));
        map.fitBounds(bounds, { padding: 70, maxZoom: 19, duration: 0 });
      }
      setReady(true);
      setMapError(null);
    });
    map.on("error", () => setMapError("Basemap unavailable. Boundary editing still works."));
    map.on("mouseenter", "edit-vertices", () => { if (!dragRef.current) map.getCanvas().style.cursor = "grab"; });
    map.on("mouseleave", "edit-vertices", () => { if (!dragRef.current) map.getCanvas().style.cursor = ""; });
    map.on("mousedown", "edit-vertices", (event) => {
      const properties = event.features?.[0]?.properties;
      if (!properties) return;
      event.preventDefault();
      dragRef.current = { ringIndex: Number(properties.ringIndex), vertexIndex: Number(properties.vertexIndex) };
      map.dragPan.disable();
      map.getCanvas().style.cursor = "grabbing";
    });
    map.on("touchstart", "edit-vertices", (event) => {
      const properties = event.features?.[0]?.properties;
      if (!properties) return;
      event.preventDefault();
      dragRef.current = { ringIndex: Number(properties.ringIndex), vertexIndex: Number(properties.vertexIndex) };
      map.dragPan.disable();
    });
    map.on("mousemove", moveVertex);
    map.on("touchmove", moveVertex);
    map.on("mouseup", finishDrag);
    map.on("touchend", finishDrag);

    const observer = new ResizeObserver(() => map.resize());
    observer.observe(containerRef.current);
    mapRef.current = map;
    return () => {
      observer.disconnect();
      setReady(false);
      map.remove();
      mapRef.current = null;
    };
  }, []);

  return <div className="boundary-edit-map">
    <div ref={containerRef} className="boundary-edit-canvas" />
    <button type="button" className={`measure-toggle ${measure ? "active" : ""}`} onClick={() => setMeasure((value) => !value)} aria-pressed={measure}>Measure</button>
    {measure && <div className="measure-readout"><span>Area <strong>{formatArea(metrics.area)}</strong></span><span>Perimeter <strong>{formatDistance(metrics.perimeter)}</strong></span></div>}
    {!ready && <div className="edit-map-status">Loading map…</div>}
    {mapError && <div className="edit-map-status warning">{mapError}</div>}
  </div>;
}
