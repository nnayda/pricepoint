import { Marker, Popup } from "react-leaflet";
import type { GreenspaceFeature } from "../../../types";

interface GreenspaceLayerProps {
  data: GreenspaceFeature[];
}

function GreenspaceLayer({ data }: GreenspaceLayerProps) {
  if (data.length === 0) return null;

  return (
    <>
      {data.map((feature) => (
        <Marker key={feature.id} position={[feature.lat, feature.lon]}>
          <Popup>
            <div className="text-sm">
              <p className="font-bold">{feature.name}</p>
              <p className="text-text-sec">{feature.feature_type}</p>
              <p className="text-text-sec">{feature.distance_miles.toFixed(1)} mi</p>
              {feature.acreage != null && (
                <p className="text-text-sec">{feature.acreage.toFixed(1)} acres</p>
              )}
            </div>
          </Popup>
        </Marker>
      ))}
    </>
  );
}

export default GreenspaceLayer;
