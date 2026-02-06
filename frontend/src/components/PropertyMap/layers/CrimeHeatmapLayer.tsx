import { useEffect } from "react";
import { useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet.heat";
import type { CrimeHeatmapPoint } from "../../../types";

interface CrimeHeatmapLayerProps {
  data: CrimeHeatmapPoint[];
}

function CrimeHeatmapLayer({ data }: CrimeHeatmapLayerProps) {
  const map = useMap();

  useEffect(() => {
    if (data.length === 0) return;

    const points: [number, number, number][] = data.map((p) => [p.lat, p.lon, p.intensity]);

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const heat = (L as any).heatLayer(points, {
      radius: 25,
      blur: 15,
      maxZoom: 17,
      gradient: {
        0.0: "blue",
        0.5: "yellow",
        1.0: "red",
      },
    });

    heat.addTo(map);
    return () => {
      map.removeLayer(heat);
    };
  }, [map, data]);

  return null;
}

export default CrimeHeatmapLayer;
