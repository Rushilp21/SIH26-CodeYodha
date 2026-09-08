import { useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { Parcel } from "@shared/types";

export function ParcelMap({
  parcels,
  selectedId,
  onSelect,
  className,
  fitParcels,
}: {
  parcels: Parcel[];
  selectedId?: string;
  onSelect?: (id: string) => void;
  className?: string;
  fitParcels?: Parcel[];
}) {
  const ref = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const selectRef = useRef(onSelect);
  const [ready, setReady] = useState(false);
  const [mapError, setMapError] = useState<string | null>(null);

  useEffect(() => { selectRef.current = onSelect; }, [onSelect]);

  useEffect(() => {
    if (!ref.current || mapRef.current) return;
    const map = new maplibregl.Map({
      container: ref.current,
      style: {
        version: 8,
        sources: { basemap: { type: "raster", tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"], tileSize: 256, maxzoom: 19, attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' } },
        layers: [{ id: "basemap", type: "raster", source: "basemap" }],
      },
      center: [85.31, 23.345],
      zoom: 15,
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    map.on("load", () => { setReady(true); setMapError(null); });
    map.on("error", () => setMapError("The basemap could not be fully loaded. Check your connection; parcel evidence remains available."));
    const observer = new ResizeObserver(() => map.resize());
    observer.observe(ref.current);
    mapRef.current = map;
    return () => {
      observer.disconnect();
      setReady(false);
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;

    const fc = {
        type: "FeatureCollection" as const,
        features: parcels.map((p) => ({
          type: "Feature" as const,
          properties: { id: p.id, status: p.status, source: p.source, selected: p.id === selectedId },
          geometry: p.geom,
        })),
      };
    const src = map.getSource("parcels") as maplibregl.GeoJSONSource | undefined;
    if (src) {
      src.setData(fc as never);
    } else {
      map.addSource("parcels", { type: "geojson", data: fc as never });
      const color = ["match", ["get", "status"], "verified", "#10B981", "needs_review", "#F59E0B", "rejected", "#EF4444", "ai_processed", "#3B82F6", "#64748B"] as never;
      map.addLayer({ id: "parcels-fill", type: "fill", source: "parcels", paint: { "fill-color": color, "fill-opacity": ["case", ["boolean", ["get", "selected"], false], 0.42, 0.18] as never } });
      map.addLayer({ id: "parcels-line", type: "line", source: "parcels", paint: { "line-color": color, "line-width": ["case", ["boolean", ["get", "selected"], false], 3.5, 1.8] as never } });
      map.on("click", "parcels-fill", (event) => {
        const id = event.features?.[0]?.properties?.id as string | undefined;
        if (id) selectRef.current?.(id);
      });
      map.on("mouseenter", "parcels-fill", () => { map.getCanvas().style.cursor = "pointer"; });
      map.on("mouseleave", "parcels-fill", () => { map.getCanvas().style.cursor = ""; });
    }
  }, [parcels, ready, selectedId]);

  useEffect(() => {
    const map = mapRef.current;
    const selected = parcels.find((parcel) => parcel.id === selectedId);
    const ring = fitParcels ? fitParcels.flatMap(parcel => parcel.geom.coordinates.flat()) : selected ? selected.geom.coordinates.flat() : parcels.flatMap((parcel) => parcel.geom.coordinates.flat());
    if (!map || !ready || !ring.length) return;
    const bounds = ring.reduce((current, coordinate) => current.extend(coordinate as [number, number]), new maplibregl.LngLatBounds(ring[0] as [number, number], ring[0] as [number, number]));
    const padding = Math.max(20, Math.min(80, map.getContainer().clientWidth / 5, map.getContainer().clientHeight / 5));
    map.fitBounds(bounds, { padding, maxZoom: 18, duration: 500 });
  }, [parcels, ready, selectedId, fitParcels]);

  return <div className={className ?? "parcel-map"} style={{ position: "relative" }}><div ref={ref} style={{ width: "100%", height: "100%" }} />{mapError && <p role="status" style={{ position: "absolute", bottom: 64, left: 12, right: 12, background: "white", padding: 8, fontSize: 11 }}>{mapError}</p>}</div>;
}
