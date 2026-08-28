import { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { Parcel } from "@shared/types";

export function ParcelMap({
  parcels,
  selectedId,
  onSelect,
}: {
  parcels: Parcel[];
  selectedId?: string;
  onSelect?: (id: string) => void;
}) {
  const ref = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);

  useEffect(() => {
    if (!ref.current || mapRef.current) return;
    const map = new maplibregl.Map({
      container: ref.current,
      style: "https://demotiles.maplibre.org/style.json",
      center: [85.31, 23.345],
      zoom: 15,
    });
    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const draw = () => {
      const fc = {
        type: "FeatureCollection" as const,
        features: parcels.map((p) => ({
          type: "Feature" as const,
          properties: { id: p.id, selected: p.id === selectedId },
          geometry: p.geom,
        })),
      };
      const src = map.getSource("parcels") as maplibregl.GeoJSONSource | undefined;
      if (src) {
        src.setData(fc as never);
      } else {
        map.addSource("parcels", { type: "geojson", data: fc as never });
        map.addLayer({
          id: "parcels-fill",
          type: "fill",
          source: "parcels",
          paint: { "fill-color": "#38bdf8", "fill-opacity": 0.25 },
        });
        map.addLayer({
          id: "parcels-line",
          type: "line",
          source: "parcels",
          paint: { "line-color": "#e2e8f0", "line-width": 2 },
        });
        map.on("click", "parcels-fill", (e) => {
          const id = e.features?.[0]?.properties?.id as string | undefined;
          if (id && onSelect) onSelect(id);
        });
      }
      const sel = parcels.find((p) => p.id === selectedId);
      if (sel?.geom?.coordinates?.[0]?.[0]) {
        const [lon, lat] = sel.geom.coordinates[0][0];
        map.easeTo({ center: [lon, lat], zoom: 17 });
      }
    };

    if (map.loaded()) draw();
    else map.on("load", draw);
  }, [parcels, selectedId, onSelect]);

  return <div ref={ref} className="h-[420px] w-full rounded border border-slate-700" />;
}
