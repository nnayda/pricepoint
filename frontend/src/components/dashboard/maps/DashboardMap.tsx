import { MapContainer, Marker, Popup, useMap } from "react-leaflet";
import MarkerClusterGroup from "react-leaflet-cluster";
import L from "leaflet";
import { useEffect, useRef, useCallback, useMemo, useState } from "react";
import { useTheme } from "../../../contexts/ThemeContext";
import { useMapStyle } from "../../../hooks/useMapStyle";
import { COLOR_INDIGO } from "../../../utils/chartTokens";

export interface MapMarker {
  lat: number;
  lon: number;
  label: string;
  color?: string;
  id?: string;
  isProperty?: boolean;
  infrastructureType?: string;
}

export type MapStyle = "street" | "satellite" | "dark" | "light";

interface DashboardMapProps {
  center: [number, number];
  zoom?: number;
  markers?: MapMarker[];
  height?: string;
  minHeight?: string;
  children?: React.ReactNode;
  highlightedId?: string | null;
  selectedId?: string | null;
  cluster?: boolean;
}

function createPropertyIcon(color: string = COLOR_INDIGO, highlighted: boolean = false) {
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

function createIcon(color: string = COLOR_INDIGO, highlighted: boolean = false) {
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

const INFRA_SVG_PATHS: Record<string, string> = {
  // Antenna / signal tower
  cell_tower: "M12 2v8m0 0l-3-3m3 3l3-3M8 22h8m-4 0v-6m-6-2a6 6 0 0112 0m-16-2a10 10 0 0120 0",
  // Lightning bolt / zap
  transmission_line: "M13 2L3 14h9l-1 10 10-12h-9l1-10z",
  // Factory / smokestack
  power_plant: "M2 20h20M4 20v-8l4 2v-6l4 2V4l4 4v12M6 20v-3h2v3m4-3v-5h2v5",
  // Flame
  nat_gas_pipeline:
    "M12 2c-2 4-6 6-6 10a6 6 0 0012 0c0-4-4-6-6-10zm0 14a2 2 0 01-2-2c0-2 2-3 2-3s2 1 2 3a2 2 0 01-2 2z",
  // Droplet
  petroleum_pipeline: "M12 2c-4 5.5-8 9-8 13a8 8 0 0016 0c0-4-4-7.5-8-13z",
};

function createInfraIcon(type: string, color: string = COLOR_INDIGO, highlighted: boolean = false) {
  const size = highlighted ? 28 : 24;
  const svgSize = size * 0.58;
  const glow = highlighted ? `0 0 14px ${color}` : `0 0 8px ${color}80`;
  const path = INFRA_SVG_PATHS[type] ?? INFRA_SVG_PATHS.cell_tower;
  return L.divIcon({
    className: "",
    html: `<div style="width:${size}px;height:${size}px;display:flex;align-items:center;justify-content:center;background:${color};border-radius:6px;border:2px solid rgba(255,255,255,${highlighted ? 1 : 0.9});box-shadow:${glow};transition:all 0.15s ease;">
      <svg width="${svgSize}" height="${svgSize}" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="${path}"/>
      </svg>
    </div>`,
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
        : marker.infrastructureType
          ? createInfraIcon(marker.infrastructureType, marker.color, highlighted || selected)
          : createIcon(marker.color, highlighted || selected),
    [marker.color, marker.isProperty, marker.infrastructureType, highlighted, selected],
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
    <Marker ref={setRef} position={[marker.lat, marker.lon]} icon={icon}>
      <Popup>
        <span style={{ fontFamily: "var(--font-db-sans)", fontSize: 12 }}>{marker.label}</span>
      </Popup>
    </Marker>
  );
}

const TILE_CONFIGS: Record<MapStyle, { url: string; attribution: string; maxZoom: number }> = {
  street: {
    url: "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png",
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>',
    maxZoom: 20,
  },
  satellite: {
    url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attribution: '&copy; <a href="https://www.esri.com/">Esri</a>, Maxar, Earthstar Geographics',
    maxZoom: 19,
  },
  dark: {
    url: "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>',
    maxZoom: 20,
  },
  light: {
    url: "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>',
    maxZoom: 20,
  },
};

const STYLE_LABELS: Record<MapStyle, string> = {
  street: "Street",
  satellite: "Satellite",
  dark: "Dark",
  light: "Light",
};

function getDefaultStyle(resolvedTheme: string): MapStyle {
  return resolvedTheme === "light" ? "light" : "dark";
}

/** Syncs the tile layer when style or theme changes. */
function TileLayerController({ style }: { style: MapStyle }) {
  const map = useMap();
  const layerRef = useRef<L.TileLayer | null>(null);

  useEffect(() => {
    if (layerRef.current) {
      map.removeLayer(layerRef.current);
    }
    const config = TILE_CONFIGS[style];
    const layer = L.tileLayer(config.url, {
      attribution: config.attribution,
      maxZoom: config.maxZoom,
    });
    layer.addTo(map);
    map.setMaxZoom(config.maxZoom);
    layerRef.current = layer;
    return () => {
      map.removeLayer(layer);
    };
  }, [style, map]);

  return null;
}

const MAP_STYLES: MapStyle[] = ["street", "satellite", "dark", "light"];

function MapStyleControl({
  style,
  onChange,
}: {
  style: MapStyle;
  onChange: (s: MapStyle) => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  return (
    <div
      ref={ref}
      style={{ position: "absolute", top: 10, right: 10, zIndex: 1000, pointerEvents: "none" }}
    >
      <div style={{ margin: 0, pointerEvents: "auto" }}>
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          aria-label="Map style"
          title="Map style"
          style={{
            display: "flex",
            alignItems: "center",
            gap: 4,
            padding: "5px 10px",
            background: "var(--color-db-surface, #1C2333)",
            color: "var(--color-db-text-primary, #E8ECF4)",
            border: "1px solid var(--color-db-border, #2E3553)",
            borderRadius: "var(--radius-db-sm, 6px)",
            cursor: "pointer",
            fontSize: 12,
            fontFamily: "var(--font-db-sans)",
            lineHeight: 1,
            whiteSpace: "nowrap",
            boxShadow: "0 1px 4px rgba(0,0,0,0.3)",
          }}
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6" />
            <line x1="8" y1="2" x2="8" y2="18" />
            <line x1="16" y1="6" x2="16" y2="22" />
          </svg>
          {STYLE_LABELS[style]}
        </button>
        {open && (
          <div
            style={{
              marginTop: 4,
              background: "var(--color-db-surface, #1C2333)",
              border: "1px solid var(--color-db-border, #2E3553)",
              borderRadius: "var(--radius-db-sm, 6px)",
              overflow: "hidden",
              boxShadow: "0 4px 12px rgba(0,0,0,0.4)",
            }}
          >
            {MAP_STYLES.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => {
                  onChange(s);
                  setOpen(false);
                }}
                style={{
                  display: "block",
                  width: "100%",
                  padding: "6px 12px",
                  background:
                    s === style ? "var(--color-db-surface-hover, #252D44)" : "transparent",
                  color: "var(--color-db-text-primary, #E8ECF4)",
                  border: "none",
                  cursor: "pointer",
                  fontSize: 12,
                  fontFamily: "var(--font-db-sans)",
                  textAlign: "left",
                  whiteSpace: "nowrap",
                }}
                onMouseEnter={(e) => {
                  if (s !== style)
                    e.currentTarget.style.background = "var(--color-db-surface-hover, #252D44)";
                }}
                onMouseLeave={(e) => {
                  if (s !== style) e.currentTarget.style.background = "transparent";
                }}
              >
                {STYLE_LABELS[s]}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function createClusterIcon(cluster: any) {
  const count = cluster.getChildCount();
  const size = count < 10 ? 32 : count < 50 ? 38 : 44;
  return L.divIcon({
    html: `<div style="width:${size}px;height:${size}px;display:flex;align-items:center;justify-content:center;background:var(--color-db-accent, #6366F1);border-radius:50%;border:2px solid rgba(255,255,255,0.9);box-shadow:0 0 8px rgba(99,102,241,0.5);color:#fff;font-size:12px;font-weight:600;font-family:var(--font-db-sans);">${count}</div>`,
    className: "",
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
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
  cluster = false,
}: DashboardMapProps) {
  const { resolvedTheme } = useTheme();
  const [mapStyle, handleStyleChange] = useMapStyle(getDefaultStyle(resolvedTheme));

  const propertyMarkers = markers.filter((m) => m.isProperty);
  const otherMarkers = markers.filter((m) => !m.isProperty);

  const renderMarker = (m: MapMarker) => (
    <InteractiveMarker
      key={m.id ?? `${m.lat}-${m.lon}-${m.label}`}
      marker={m}
      highlighted={m.id != null && m.id === highlightedId}
      selected={m.id != null && m.id === selectedId}
    />
  );

  return (
    <div
      className="dashboard-map overflow-hidden rounded-[var(--radius-db-sm)] border border-[var(--color-db-border-subtle)]"
      style={{ height, minHeight, position: "relative" }}
    >
      <MapContainer
        center={center}
        zoom={zoom}
        style={{ height: "100%", width: "100%" }}
        zoomControl={true}
        attributionControl={true}
      >
        <TileLayerController style={mapStyle} />
        {propertyMarkers.map(renderMarker)}
        {cluster ? (
          <MarkerClusterGroup
            maxClusterRadius={40}
            spiderfyOnMaxZoom={true}
            showCoverageOnHover={false}
            iconCreateFunction={createClusterIcon}
          >
            {otherMarkers.map(renderMarker)}
          </MarkerClusterGroup>
        ) : (
          otherMarkers.map(renderMarker)
        )}
        {children}
      </MapContainer>
      <MapStyleControl style={mapStyle} onChange={handleStyleChange} />
    </div>
  );
}

export default DashboardMap;
