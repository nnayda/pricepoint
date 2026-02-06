import { Marker, Popup } from "react-leaflet";
import MarkerClusterGroup from "react-leaflet-cluster";
import type { CrimeIncident } from "../../../types";

interface CrimeIncidentsLayerProps {
  data: CrimeIncident[];
}

function CrimeIncidentsLayer({ data }: CrimeIncidentsLayerProps) {
  if (data.length === 0) return null;

  return (
    <MarkerClusterGroup chunkedLoading>
      {data.map((incident) => (
        <Marker key={incident.id} position={[incident.lat, incident.lon]}>
          <Popup>
            <div className="text-sm">
              <p className="font-bold">{incident.incident_type}</p>
              <p className="text-text-sec">{incident.category}</p>
              <p className="text-text-sec">{incident.date}</p>
              {incident.description && <p className="mt-1">{incident.description}</p>}
            </div>
          </Popup>
        </Marker>
      ))}
    </MarkerClusterGroup>
  );
}

export default CrimeIncidentsLayer;
