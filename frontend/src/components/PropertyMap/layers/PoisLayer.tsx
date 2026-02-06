import { Marker, Popup } from "react-leaflet";
import type { PointOfInterest } from "../../../types";

interface PoisLayerProps {
  data: PointOfInterest[];
}

function PoisLayer({ data }: PoisLayerProps) {
  if (data.length === 0) return null;

  return (
    <>
      {data.map((poi) => (
        <Marker key={poi.id} position={[poi.lat, poi.lon]}>
          <Popup>
            <div className="text-sm">
              <p className="font-bold">{poi.name}</p>
              <p className="text-text-sec">{poi.category}</p>
              <p className="text-text-sec">
                {poi.distance_miles.toFixed(1)} mi &middot; {poi.drive_minutes} min drive
              </p>
            </div>
          </Popup>
        </Marker>
      ))}
    </>
  );
}

export default PoisLayer;
