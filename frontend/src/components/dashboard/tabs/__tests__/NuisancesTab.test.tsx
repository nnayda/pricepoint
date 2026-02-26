import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import NuisancesTab from "../NuisancesTab";
import { mockDashboardData } from "../../../../data/mockDashboardData";

const mockNoiseFeatures: GeoJSON.Feature[] = [
  {
    type: "Feature",
    geometry: {
      type: "Polygon",
      coordinates: [
        [
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 0],
        ],
      ],
    },
    properties: { noise_band: "65-70 dB", source_layer: "aviation" },
  },
  {
    type: "Feature",
    geometry: {
      type: "Polygon",
      coordinates: [
        [
          [2, 2],
          [3, 2],
          [3, 3],
          [2, 2],
        ],
      ],
    },
    properties: { noise_band: "70-75 dB", source_layer: "road" },
  },
  {
    type: "Feature",
    geometry: {
      type: "Polygon",
      coordinates: [
        [
          [4, 4],
          [5, 4],
          [5, 5],
          [4, 4],
        ],
      ],
    },
    properties: { noise_band: "60-65 dB", source_layer: "rail" },
  },
  {
    type: "Feature",
    geometry: {
      type: "Polygon",
      coordinates: [
        [
          [6, 6],
          [7, 6],
          [7, 7],
          [6, 6],
        ],
      ],
    },
    properties: { noise_band: "75-80 dB", source_layer: "aviation_road_rail" },
  },
];

const mockUseNuisancesReturn = {
  data: { type: "FeatureCollection" as const, features: mockNoiseFeatures },
  loading: false,
};

vi.mock("../../../../hooks/useNuisances", () => ({
  useNuisances: vi.fn(() => mockUseNuisancesReturn),
}));

vi.mock("react-leaflet", () => ({
  MapContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="map-container">{children}</div>
  ),
  TileLayer: () => <div data-testid="tile-layer" />,
  Marker: () => <div data-testid="marker" />,
  Popup: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  GeoJSON: ({ data }: { data: GeoJSON.FeatureCollection }) => (
    <div data-testid="geojson-layer" data-feature-count={data.features.length} />
  ),
  useMap: () => ({ fitBounds: vi.fn(), setView: vi.fn() }),
}));

vi.mock("../../maps/DashboardMap", () => ({
  default: ({
    children,
  }: {
    children?: React.ReactNode;
    center: [number, number];
    zoom: number;
    markers: unknown[];
    height: string;
    minHeight: string;
    highlightedId?: string | null;
    selectedId?: string | null;
  }) => <div data-testid="dashboard-map">{children}</div>,
}));

describe("NuisancesTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseNuisancesReturn.data = {
      type: "FeatureCollection",
      features: mockNoiseFeatures,
    };
    mockUseNuisancesReturn.loading = false;
  });

  it("renders all 4 noise source toggle buttons", () => {
    render(<NuisancesTab data={mockDashboardData} />);
    expect(screen.getByText("Aviation")).toBeInTheDocument();
    expect(screen.getByText("Road")).toBeInTheDocument();
    expect(screen.getByText("Rail")).toBeInTheDocument();
    expect(screen.getByText("Combined")).toBeInTheDocument();
  });

  it("all toggles are active by default (all features shown)", () => {
    render(<NuisancesTab data={mockDashboardData} />);
    const geojson = screen.getByTestId("geojson-layer");
    expect(geojson.getAttribute("data-feature-count")).toBe("4");
  });

  it("clicking a toggle removes its features from the map", () => {
    render(<NuisancesTab data={mockDashboardData} />);

    fireEvent.click(screen.getByText("Aviation"));

    const geojson = screen.getByTestId("geojson-layer");
    expect(geojson.getAttribute("data-feature-count")).toBe("3");
  });

  it("clicking a toggle again re-adds its features", () => {
    render(<NuisancesTab data={mockDashboardData} />);

    // Toggle off
    fireEvent.click(screen.getByText("Road"));
    expect(screen.getByTestId("geojson-layer").getAttribute("data-feature-count")).toBe("3");

    // Toggle back on
    fireEvent.click(screen.getByText("Road"));
    expect(screen.getByTestId("geojson-layer").getAttribute("data-feature-count")).toBe("4");
  });

  it("toggling off all sources hides the GeoJSON layer", () => {
    render(<NuisancesTab data={mockDashboardData} />);

    fireEvent.click(screen.getByText("Aviation"));
    fireEvent.click(screen.getByText("Road"));
    fireEvent.click(screen.getByText("Rail"));
    fireEvent.click(screen.getByText("Combined"));

    expect(screen.queryByTestId("geojson-layer")).not.toBeInTheDocument();
  });

  it("toggling multiple sources filters correctly", () => {
    render(<NuisancesTab data={mockDashboardData} />);

    fireEvent.click(screen.getByText("Aviation"));
    fireEvent.click(screen.getByText("Rail"));

    const geojson = screen.getByTestId("geojson-layer");
    expect(geojson.getAttribute("data-feature-count")).toBe("2");
  });
});
