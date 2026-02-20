import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import L from "leaflet";

interface MapMarker {
  lat: number;
  lon: number;
  label: string;
  color?: string;
}

interface DashboardMapProps {
  center: [number, number];
  zoom?: number;
  markers?: MapMarker[];
  height?: string;
  children?: React.ReactNode;
}

function createIcon(color: string = "#6366F1") {
  return L.divIcon({
    className: "",
    html: `<div style="width:12px;height:12px;border-radius:50%;background:${color};border:2px solid rgba(255,255,255,0.8);box-shadow:0 0 6px ${color}80;"></div>`,
    iconSize: [12, 12],
    iconAnchor: [6, 6],
  });
}

function DashboardMap({
  center,
  zoom = 14,
  markers = [],
  height = "300px",
  children,
}: DashboardMapProps) {
  return (
    <div
      className="dashboard-map overflow-hidden rounded-[var(--radius-db-sm)] border border-[var(--color-db-border-subtle)]"
      style={{ height }}
    >
      <MapContainer
        center={center}
        zoom={zoom}
        style={{ height: "100%", width: "100%" }}
        zoomControl={true}
        attributionControl={true}
      >
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>'
        />
        {markers.map((m) => (
          <Marker
            key={`${m.lat}-${m.lon}-${m.label}`}
            position={[m.lat, m.lon]}
            icon={createIcon(m.color)}
          >
            <Popup>
              <span style={{ fontFamily: "var(--font-db-sans)", fontSize: 12 }}>{m.label}</span>
            </Popup>
          </Marker>
        ))}
        {children}
      </MapContainer>
    </div>
  );
}

export default DashboardMap;
