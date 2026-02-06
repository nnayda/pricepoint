import { Marker, Popup } from "react-leaflet";
import type { UtilityFeature } from "../../../types";

interface UtilitiesLayerProps {
  data: UtilityFeature[];
}

function UtilitiesLayer({ data }: UtilitiesLayerProps) {
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
            </div>
          </Popup>
        </Marker>
      ))}
    </>
  );
}

export default UtilitiesLayer;
