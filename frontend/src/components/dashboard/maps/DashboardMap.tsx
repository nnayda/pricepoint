import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import { useEffect, useRef, useCallback, useMemo } from "react";

export interface MapMarker {
  lat: number;
  lon: number;
  label: string;
  color?: string;
  id?: string;
  isProperty?: boolean;
}

interface DashboardMapProps {
  center: [number, number];
  zoom?: number;
  markers?: MapMarker[];
  height?: string;
  minHeight?: string;
  children?: React.ReactNode;
  highlightedId?: string | null;
  selectedId?: string | null;
}

function createPropertyIcon(color: string = "#6366F1", highlighted: boolean = false) {
  const size = highlighted ? 32 : 28;
  const glow = highlighted ? `0 0 14px ${color}` : `0 0 8px ${color}80`;
  return L.divIcon({
    className: "",
    html: `<div style="width:${size}px;height:${size}px;display:flex;align-items:center;justify-content:center;background:${color};border-radius:6px;border:2px solid rgba(255,255,255,${highlighted ? 1 : 0.9});box-shadow:${glow};transition:all 0.15s ease;">
      <svg width="${size * 0.6}" height="${size * 0.6}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M3 10.5L12 3L21 10.5V20C21 20.55 20.55 21 20 21H15V14H9V21H4C3.45 21 3 20.55 3 20V10.5Z" fill="white" stroke="white" stroke-width="1" stroke-linejoin="round"/>
      </svg>
    </div>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

function createIcon(color: string = "#6366F1", highlighted: boolean = false) {
  const size = highlighted ? 18 : 12;
  const border = highlighted ? 3 : 2;
  const glow = highlighted ? `0 0 12px ${color}` : `0 0 6px ${color}80`;
  return L.divIcon({
    className: "",
    html: `<div style="width:${size}px;height:${size}px;border-radius:50%;background:${color};border:${border}px solid rgba(255,255,255,${highlighted ? 1 : 0.8});box-shadow:${glow};transition:all 0.15s ease;"></div>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

function InteractiveMarker({
  marker,
  highlighted,
  selected,
}: {
  marker: MapMarker;
  highlighted: boolean;
  selected: boolean;
}) {
  const markerRef = useRef<L.Marker>(null);
  const map = useMap();

  const icon = useMemo(
    () =>
      marker.isProperty
        ? createPropertyIcon(marker.color, highlighted || selected)
        : createIcon(marker.color, highlighted || selected),
    [marker.color, marker.isProperty, highlighted, selected],
  );

  useEffect(() => {
    if (selected && markerRef.current) {
      markerRef.current.openPopup();
      map.panTo([marker.lat, marker.lon], { animate: true, duration: 0.3 });
    } else if (!selected && markerRef.current) {
      markerRef.current.closePopup();
    }
  }, [selected, map, marker.lat, marker.lon]);

  // Bring highlighted/selected/property markers to front
  useEffect(() => {
    if ((highlighted || selected) && markerRef.current) {
      markerRef.current.setZIndexOffset(1000);
    } else if (marker.isProperty && markerRef.current) {
      markerRef.current.setZIndexOffset(500);
    } else if (markerRef.current) {
      markerRef.current.setZIndexOffset(0);
    }
  }, [highlighted, selected, marker.isProperty]);

  const setRef = useCallback((el: L.Marker | null) => {
    (markerRef as React.MutableRefObject<L.Marker | null>).current = el;
  }, []);

  return (
    <Marker
      ref={setRef}
      position={[marker.lat, marker.lon]}
      icon={icon}
    >
      <Popup>
        <span style={{ fontFamily: "var(--font-db-sans)", fontSize: 12 }}>{marker.label}</span>
      </Popup>
    </Marker>
  );
}

function DashboardMap({
  center,
  zoom = 14,
  markers = [],
  height = "300px",
  minHeight,
  children,
  highlightedId,
  selectedId,
}: DashboardMapProps) {
  return (
    <div
      className="dashboard-map overflow-hidden rounded-[var(--radius-db-sm)] border border-[var(--color-db-border-subtle)]"
      style={{ height, minHeight }}
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
          <InteractiveMarker
            key={m.id ?? `${m.lat}-${m.lon}-${m.label}`}
            marker={m}
            highlighted={m.id != null && m.id === highlightedId}
            selected={m.id != null && m.id === selectedId}
          />
        ))}
        {children}
      </MapContainer>
    </div>
  );
}

export default DashboardMap;
