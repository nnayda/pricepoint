import { useRef, useEffect, useCallback, useMemo, useState } from "react";
import maplibregl from "maplibre-gl";
import MapGL, {
  Marker,
  Popup,
  Source,
  Layer,
  NavigationControl,
  type MapRef,
  type ViewStateChangeEvent,
  type MapLayerMouseEvent,
} from "react-map-gl/maplibre";
import "maplibre-gl/dist/maplibre-gl.css";
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
  /** Persistent label shown next to the marker on the map */
  priceLabel?: string;
  /** Optional logo/image URL — renders a circular image marker with colored border */
  imageUrl?: string;
}

export type MapStyle = "street" | "satellite" | "dark" | "light";

export interface RadiusCircle {
  /** Radius in miles */
  radiusMiles: number;
  /** Stroke color (CSS) */
  color?: string;
  /** Stroke opacity 0–1 */
  opacity?: number;
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
  cluster?: boolean;
  interactiveLayerIds?: string[];
  /** Dotted radius circle drawn around `center` */
  radiusCircle?: RadiusCircle;
  onLayerClick?: (e: MapLayerMouseEvent) => void;
  onMoveEnd?: (bounds: { swLat: number; swLon: number; neLat: number; neLon: number }) => void;
  /** Called when the user clicks a marker on the map (id of clicked marker) */
  onMarkerSelect?: (id: string) => void;
  /** Called when the user closes a popup (to deselect the marker) */
  onMarkerDeselect?: () => void;
  /** Custom popup renderer — receives the active marker; falls back to label text */
  renderPopup?: (marker: MapMarker) => React.ReactNode;
}

// MapLibre GL style definitions — CARTO vector tiles for street/dark/light,
// Esri raster tiles for satellite
const MAP_STYLES: Record<MapStyle, string | maplibregl.StyleSpecification> = {
  street: "https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json",
  dark: "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
  light: "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
  satellite: {
    version: 8,
    sources: {
      esri: {
        type: "raster",
        tiles: [
          "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        ],
        tileSize: 256,
      },
    },
    layers: [{ id: "esri-satellite", type: "raster", source: "esri" }],
  },
};

const STYLE_LABELS: Record<MapStyle, string> = {
  street: "Street",
  satellite: "Satellite",
  dark: "Dark",
  light: "Light",
};

const MAP_STYLE_KEYS: MapStyle[] = ["street", "satellite", "dark", "light"];

function getDefaultStyle(resolvedTheme: string): MapStyle {
  return resolvedTheme === "light" ? "light" : "dark";
}

const INFRA_SVG_PATHS: Record<string, string> = {
  cell_tower: "M12 2v8m0 0l-3-3m3 3l3-3M8 22h8m-4 0v-6m-6-2a6 6 0 0112 0m-16-2a10 10 0 0120 0",
  transmission_line: "M13 2L3 14h9l-1 10 10-12h-9l1-10z",
  power_plant: "M2 20h20M4 20v-8l4 2v-6l4 2V4l4 4v12M6 20v-3h2v3m4-3v-5h2v5",
  nat_gas_pipeline:
    "M12 2c-2 4-6 6-6 10a6 6 0 0012 0c0-4-4-6-6-10zm0 14a2 2 0 01-2-2c0-2 2-3 2-3s2 1 2 3a2 2 0 01-2 2z",
  petroleum_pipeline: "M12 2c-4 5.5-8 9-8 13a8 8 0 0016 0c0-4-4-7.5-8-13z",
};

function MarkerIcon({ marker, highlighted }: { marker: MapMarker; highlighted: boolean }) {
  const color = marker.color || COLOR_INDIGO;

  if (marker.imageUrl) {
    const size = highlighted ? 32 : 26;
    return (
      <div
        style={{
          width: size,
          height: size,
          borderRadius: "50%",
          border: `3px solid ${color}`,
          boxShadow: highlighted ? `0 0 12px ${color}` : `0 0 6px ${color}80`,
          overflow: "hidden",
          transition: "all 0.15s ease",
          cursor: "pointer",
          background: "#fff",
        }}
      >
        <img
          src={marker.imageUrl}
          alt={marker.label}
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
        />
      </div>
    );
  }

  if (marker.isProperty) {
    const size = highlighted ? 32 : 28;
    return (
      <div
        style={{
          width: size,
          height: size,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: color,
          borderRadius: 6,
          border: `2px solid rgba(255,255,255,${highlighted ? 1 : 0.9})`,
          boxShadow: highlighted ? `0 0 14px ${color}` : `0 0 8px ${color}80`,
          transition: "all 0.15s ease",
          cursor: "pointer",
        }}
      >
        <svg
          width={size * 0.6}
          height={size * 0.6}
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            d="M3 10.5L12 3L21 10.5V20C21 20.55 20.55 21 20 21H15V14H9V21H4C3.45 21 3 20.55 3 20V10.5Z"
            fill="white"
            stroke="white"
            strokeWidth="1"
            strokeLinejoin="round"
          />
        </svg>
      </div>
    );
  }

  if (marker.infrastructureType) {
    const size = highlighted ? 28 : 24;
    const svgSize = size * 0.58;
    const path = INFRA_SVG_PATHS[marker.infrastructureType] ?? INFRA_SVG_PATHS.cell_tower;
    return (
      <div
        style={{
          width: size,
          height: size,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: color,
          borderRadius: 6,
          border: `2px solid rgba(255,255,255,${highlighted ? 1 : 0.9})`,
          boxShadow: highlighted ? `0 0 14px ${color}` : `0 0 8px ${color}80`,
          transition: "all 0.15s ease",
          cursor: "pointer",
        }}
      >
        <svg
          width={svgSize}
          height={svgSize}
          viewBox="0 0 24 24"
          fill="none"
          stroke="white"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d={path} />
        </svg>
      </div>
    );
  }

  const size = highlighted ? 18 : 12;
  const border = highlighted ? 3 : 2;
  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: "50%",
        background: color,
        border: `${border}px solid rgba(255,255,255,${highlighted ? 1 : 0.8})`,
        boxShadow: highlighted ? `0 0 12px ${color}` : `0 0 6px ${color}80`,
        transition: "all 0.15s ease",
        cursor: "pointer",
      }}
    />
  );
}

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
      style={{
        position: "absolute",
        top: 10,
        right: 10,
        zIndex: 1000,
        pointerEvents: "none",
      }}
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
            {MAP_STYLE_KEYS.map((s) => (
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

// Cluster source + layers using MapLibre's native clustering
const CLUSTER_LAYER: maplibregl.LayerSpecification = {
  id: "cluster-circles",
  type: "circle",
  source: "clustered-markers",
  filter: ["has", "point_count"],
  paint: {
    "circle-color": "#6366F1",
    "circle-radius": ["step", ["get", "point_count"], 16, 10, 19, 50, 22],
    "circle-stroke-width": 2,
    "circle-stroke-color": "rgba(255,255,255,0.9)",
  },
};

const CLUSTER_COUNT_LAYER: maplibregl.LayerSpecification = {
  id: "cluster-count",
  type: "symbol",
  source: "clustered-markers",
  filter: ["has", "point_count"],
  layout: {
    "text-field": "{point_count_abbreviated}",
    "text-size": 12,
  },
  paint: {
    "text-color": "#ffffff",
  },
};

/** Individual (unclustered) points — color read from GeoJSON feature properties */
const UNCLUSTERED_POINT_LAYER: maplibregl.LayerSpecification = {
  id: "unclustered-point",
  type: "circle",
  source: "clustered-markers",
  filter: ["!", ["has", "point_count"]],
  paint: {
    "circle-color": ["get", "color"],
    "circle-radius": 8,
    "circle-stroke-width": 2,
    "circle-stroke-color": "rgba(255,255,255,0.9)",
  },
};

/** Convert miles to pixels at a given latitude and zoom level. */
function milesToPixels(lat: number, miles: number, zoom: number): number {
  const metersPerMile = 1609.344;
  const metersPerPixel = (156543.03392 * Math.cos((lat * Math.PI) / 180)) / Math.pow(2, zoom);
  return (miles * metersPerMile) / metersPerPixel;
}

/** SVG circle overlay rendered as a single Marker at the center point. */
function RadiusOverlay({
  center,
  radiusCircle,
  mapRef,
}: {
  center: [number, number];
  radiusCircle: RadiusCircle;
  mapRef: React.RefObject<MapRef | null>;
}) {
  const [radiusPx, setRadiusPx] = useState(0);

  const update = useCallback(() => {
    const map = mapRef.current?.getMap();
    if (!map) return;
    const px = milesToPixels(center[0], radiusCircle.radiusMiles, map.getZoom());
    setRadiusPx(px);
  }, [center, radiusCircle.radiusMiles, mapRef]);

  useEffect(() => {
    const map = mapRef.current?.getMap();
    if (!map) return;
    update();
    map.on("zoom", update);
    map.on("move", update);
    return () => {
      map.off("zoom", update);
      map.off("move", update);
    };
  }, [mapRef, update]);

  if (radiusPx < 2) return null;

  const size = radiusPx * 2 + 4; // +4 for stroke width
  const color = radiusCircle.color ?? "#475569";
  const opacity = radiusCircle.opacity ?? 0.85;

  return (
    <Marker longitude={center[1]} latitude={center[0]} anchor="center">
      <svg width={size} height={size} style={{ pointerEvents: "none", overflow: "visible" }}>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radiusPx}
          fill="none"
          stroke={color}
          strokeWidth={2}
          strokeDasharray="6 4"
          opacity={opacity}
        />
      </svg>
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
  cluster = false,
  interactiveLayerIds: extraInteractiveIds = [],
  radiusCircle,
  onLayerClick,
  onMoveEnd,
  onMarkerSelect,
  onMarkerDeselect,
  renderPopup,
}: DashboardMapProps) {
  const { resolvedTheme } = useTheme();
  const [mapStyle, handleStyleChange] = useMapStyle(getDefaultStyle(resolvedTheme));
  const mapRef = useRef<MapRef>(null);
  const [popupMarker, setPopupMarker] = useState<MapMarker | null>(null);

  // radiusCircle is rendered via RadiusOverlay component below

  // Clear popup when selection is removed
  useEffect(() => {
    if (!selectedId) setPopupMarker(null);
  }, [selectedId]);

  const propertyMarkers = markers.filter((m) => m.isProperty);
  const otherMarkers = markers.filter((m) => !m.isProperty);

  // GeoJSON for clustered markers
  const clusterGeojson = useMemo(() => {
    if (!cluster) return null;
    return {
      type: "FeatureCollection" as const,
      features: otherMarkers.map((m) => ({
        type: "Feature" as const,
        geometry: {
          type: "Point" as const,
          coordinates: [m.lon, m.lat],
        },
        properties: {
          id: m.id ?? `${m.lat}-${m.lon}`,
          label: m.label,
          color: m.color ?? COLOR_INDIGO,
        },
      })),
    };
  }, [cluster, otherMarkers]);

  const handleMoveEnd = useCallback(
    (evt: ViewStateChangeEvent) => {
      if (!onMoveEnd) return;
      const map = evt.target;
      const bounds = map.getBounds();
      onMoveEnd({
        swLat: bounds.getSouth(),
        swLon: bounds.getWest(),
        neLat: bounds.getNorth(),
        neLon: bounds.getEast(),
      });
    },
    [onMoveEnd],
  );

  // Handle click on cluster to zoom in, or unclustered point to show popup
  const handleClusterClick = useCallback(
    (e: MapLayerMouseEvent) => {
      const features = e.features;
      if (!features || features.length === 0) return;
      const feature = features[0];

      // Unclustered point — notify parent to select, which triggers PanToSelected
      if (feature.layer?.id === "unclustered-point" && feature.properties?.id) {
        const matchId = feature.properties.id as string;
        if (onMarkerSelect) {
          onMarkerSelect(matchId);
        } else {
          const match = markers.find((m) => (m.id ?? `${m.lat}-${m.lon}`) === matchId);
          if (match) setPopupMarker(match);
        }
        return;
      }

      // Cluster bubble — zoom in
      if (!feature.properties?.cluster_id) return;
      const map = mapRef.current?.getMap();
      if (!map) return;
      const source = map.getSource("clustered-markers") as maplibregl.GeoJSONSource;
      source.getClusterExpansionZoom(feature.properties.cluster_id).then((zoom) => {
        const geometry = feature.geometry as GeoJSON.Point;
        map.easeTo({
          center: geometry.coordinates as [number, number],
          zoom,
        });
      });
    },
    [markers, onMarkerSelect],
  );

  // Emit initial bounds after map loads
  const handleLoad = useCallback(() => {
    if (!onMoveEnd || !mapRef.current) return;
    const map = mapRef.current.getMap();
    const bounds = map.getBounds();
    onMoveEnd({
      swLat: bounds.getSouth(),
      swLon: bounds.getWest(),
      neLat: bounds.getNorth(),
      neLon: bounds.getEast(),
    });
  }, [onMoveEnd]);

  return (
    <div
      className="dashboard-map overflow-hidden rounded-[var(--radius-db-sm)] border border-[var(--color-db-border-subtle)]"
      style={{ height, minHeight, position: "relative" }}
    >
      <MapGL
        ref={mapRef}
        initialViewState={{
          longitude: center[1],
          latitude: center[0],
          zoom,
        }}
        style={{ width: "100%", height: "100%" }}
        mapStyle={MAP_STYLES[mapStyle]}
        mapLib={maplibregl}
        onMoveEnd={handleMoveEnd}
        onLoad={handleLoad}
        interactiveLayerIds={[
          ...(cluster ? ["cluster-circles", "unclustered-point"] : []),
          ...extraInteractiveIds,
        ]}
        onClick={(e: MapLayerMouseEvent) => {
          if (cluster) handleClusterClick(e);
          if (onLayerClick) onLayerClick(e);
        }}
      >
        <NavigationControl position="top-left" />

        {/* Optional radius circle around center (SVG overlay) */}
        {radiusCircle && (
          <RadiusOverlay center={center} radiusCircle={radiusCircle} mapRef={mapRef} />
        )}

        {/* Property markers always rendered as React markers */}
        {propertyMarkers.map((m) => (
          <Marker
            key={m.id ?? `prop-${m.lat}-${m.lon}`}
            longitude={m.lon}
            latitude={m.lat}
            anchor="center"
          >
            <MarkerIcon
              marker={m}
              highlighted={
                (m.id != null && m.id === highlightedId) || (m.id != null && m.id === selectedId)
              }
            />
          </Marker>
        ))}

        {/* Non-property markers: clustered or individual */}
        {cluster && clusterGeojson ? (
          <Source
            id="clustered-markers"
            type="geojson"
            data={clusterGeojson}
            cluster={true}
            clusterMaxZoom={14}
            clusterRadius={40}
          >
            <Layer {...CLUSTER_LAYER} />
            <Layer {...CLUSTER_COUNT_LAYER} />
            <Layer {...UNCLUSTERED_POINT_LAYER} />
          </Source>
        ) : (
          otherMarkers.map((m) => (
            <Marker
              key={m.id ?? `${m.lat}-${m.lon}-${m.label}`}
              longitude={m.lon}
              latitude={m.lat}
              anchor="center"
              onClick={(e) => {
                e.originalEvent.stopPropagation();
                if (onMarkerSelect && m.id) {
                  onMarkerSelect(m.id);
                } else {
                  setPopupMarker(m);
                }
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                <MarkerIcon
                  marker={m}
                  highlighted={
                    (m.id != null && m.id === highlightedId) ||
                    (m.id != null && m.id === selectedId)
                  }
                />
                {m.priceLabel && (
                  <span
                    style={{
                      fontSize: 10,
                      fontWeight: 600,
                      fontFamily: "var(--font-db-mono)",
                      color: "#fff",
                      background: "rgba(0,0,0,0.6)",
                      padding: "1px 4px",
                      borderRadius: 3,
                      whiteSpace: "nowrap",
                      pointerEvents: "none",
                    }}
                  >
                    {m.priceLabel}
                  </span>
                )}
              </div>
            </Marker>
          ))
        )}

        {/* Popup for selected marker */}
        {popupMarker && (
          <Popup
            longitude={popupMarker.lon}
            latitude={popupMarker.lat}
            anchor="bottom"
            onClose={() => {
              setPopupMarker(null);
              onMarkerDeselect?.();
            }}
            closeOnClick={false}
            maxWidth="280px"
          >
            {renderPopup ? (
              renderPopup(popupMarker)
            ) : (
              <span
                style={{
                  fontFamily: "var(--font-db-sans)",
                  fontSize: 12,
                  color: "var(--color-db-text-primary)",
                }}
              >
                {popupMarker.label}
              </span>
            )}
          </Popup>
        )}

        {/* Pan to selected marker and show popup */}
        {selectedId && (
          <PanToSelected
            markers={markers}
            selectedId={selectedId}
            mapRef={mapRef}
            onSelect={setPopupMarker}
          />
        )}

        {/* Tab-specific layers passed as children */}
        {children}
      </MapGL>
      <MapStyleControl style={mapStyle} onChange={handleStyleChange} />
    </div>
  );
}

/** Pans the map to the selected marker and opens its popup. */
function PanToSelected({
  markers,
  selectedId,
  mapRef,
  onSelect,
}: {
  markers: MapMarker[];
  selectedId: string;
  mapRef: React.RefObject<MapRef | null>;
  onSelect: (m: MapMarker | null) => void;
}) {
  useEffect(() => {
    const marker = markers.find((m) => m.id === selectedId);
    if (marker && mapRef.current) {
      mapRef.current.jumpTo({
        center: [marker.lon, marker.lat],
      });
      onSelect(marker);
    }
  }, [selectedId, markers, mapRef, onSelect]);

  return null;
}

export default DashboardMap;
