import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";

interface MapViewProps {
  center?: [number, number];
  zoom?: number;
}

function MapView({ center = [39.9526, -75.1652], zoom = 12 }: MapViewProps) {
  return (
    <div className="overflow-hidden rounded-md shadow-soft">
      <MapContainer
        center={center}
        zoom={zoom}
        style={{ height: "500px", width: "100%" }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <Marker position={center}>
          <Popup>Home Value Forecast</Popup>
        </Marker>
      </MapContainer>
    </div>
  );
}

export default MapView;
