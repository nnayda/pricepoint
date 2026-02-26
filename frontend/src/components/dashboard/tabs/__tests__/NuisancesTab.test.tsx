import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import NuisancesTab from "../NuisancesTab";
import { mockDashboardData } from "../../../../data/mockDashboardData";
import type { NuisanceSourceItem } from "../../../../types";

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
];

const EMPTY_COLLECTION = { type: "FeatureCollection" as const, features: [] };

const mockUseNuisancesReturn = {
  data: { type: "FeatureCollection" as const, features: mockNoiseFeatures },
  infraData: EMPTY_COLLECTION,
  loading: false,
  infraLoading: false,
};

const mockUseNuisanceSourcesReturn = {
  sources: [] as NuisanceSourceItem[],
  loading: false,
  error: null as string | null,
};

vi.mock("../../../../hooks/useNuisances", () => ({
  useNuisances: vi.fn(() => mockUseNuisancesReturn),
}));

vi.mock("../../../../hooks/useNuisanceSources", () => ({
  useNuisanceSources: vi.fn(() => mockUseNuisanceSourcesReturn),
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

const mockApiSources: NuisanceSourceItem[] = [
  {
    id: "src-1",
    name: "RDU Airport",
    source_type: "aviation",
    severity: "Concern",
    distance_miles: 1.2,
    lat: 35.88,
    lon: -78.79,
    detail: "Airport noise zone — 65 dB average",
    noise_min_db: 65,
    noise_band: "65-70 dB",
  },
  {
    id: "src-2",
    name: "US-401",
    source_type: "road",
    severity: "Caution",
    distance_miles: 0.3,
    lat: 35.57,
    lon: -78.78,
    detail: "Major highway within 0.3 mi — potential noise impact",
    noise_min_db: 50,
    noise_band: "50-55 dB",
  },
];

describe("NuisancesTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseNuisancesReturn.data = {
      type: "FeatureCollection",
      features: mockNoiseFeatures,
    };
    mockUseNuisancesReturn.loading = false;
    mockUseNuisanceSourcesReturn.sources = [];
    mockUseNuisanceSourcesReturn.loading = false;
    mockUseNuisanceSourcesReturn.error = null;
  });

  it("renders 3 noise source toggle buttons", () => {
    render(<NuisancesTab data={mockDashboardData} />);
    expect(screen.getByText("Airport")).toBeInTheDocument();
    expect(screen.getByText("Road")).toBeInTheDocument();
    expect(screen.getByText("Railroad")).toBeInTheDocument();
  });

  it("renders group labels to distinguish noise levels from locations", () => {
    render(<NuisancesTab data={mockDashboardData} />);
    expect(screen.getByText("Noise")).toBeInTheDocument();
    expect(screen.getByText("Locations")).toBeInTheDocument();
  });

  it("all toggles are active by default (all features shown)", () => {
    render(<NuisancesTab data={mockDashboardData} />);
    const geojson = screen.getByTestId("geojson-layer");
    expect(geojson.getAttribute("data-feature-count")).toBe("3");
  });

  it("clicking a toggle removes its features from the map", () => {
    render(<NuisancesTab data={mockDashboardData} />);

    fireEvent.click(screen.getByText("Airport"));

    const geojson = screen.getByTestId("geojson-layer");
    expect(geojson.getAttribute("data-feature-count")).toBe("2");
  });

  it("clicking a toggle again re-adds its features", () => {
    render(<NuisancesTab data={mockDashboardData} />);

    // Toggle off
    fireEvent.click(screen.getByText("Road"));
    expect(screen.getByTestId("geojson-layer").getAttribute("data-feature-count")).toBe("2");

    // Toggle back on
    fireEvent.click(screen.getByText("Road"));
    expect(screen.getByTestId("geojson-layer").getAttribute("data-feature-count")).toBe("3");
  });

  it("toggling off all sources hides the GeoJSON layer", () => {
    render(<NuisancesTab data={mockDashboardData} />);

    fireEvent.click(screen.getByText("Airport"));
    fireEvent.click(screen.getByText("Road"));
    fireEvent.click(screen.getByText("Railroad"));

    expect(screen.queryByTestId("geojson-layer")).not.toBeInTheDocument();
  });

  it("toggling multiple sources filters correctly", () => {
    render(<NuisancesTab data={mockDashboardData} />);

    fireEvent.click(screen.getByText("Airport"));
    fireEvent.click(screen.getByText("Railroad"));

    const geojson = screen.getByTestId("geojson-layer");
    expect(geojson.getAttribute("data-feature-count")).toBe("1");
  });

  it("shows empty state when no nuisance sources are found", () => {
    render(<NuisancesTab data={mockDashboardData} />);

    expect(screen.getByText("No nuisances found")).toBeInTheDocument();
    expect(
      screen.getByText(
        "No significant noise or infrastructure concerns were detected near this property.",
      ),
    ).toBeInTheDocument();
  });

  it("renders nuisance source cards from API data", () => {
    mockUseNuisanceSourcesReturn.sources = mockApiSources;

    render(<NuisancesTab data={mockDashboardData} />);

    expect(screen.getByText("RDU Airport")).toBeInTheDocument();
    expect(screen.getByText("US-401")).toBeInTheDocument();
    expect(screen.getByText(/Airport noise zone/)).toBeInTheDocument();
    expect(screen.getByText(/Major highway within 0.3 mi/)).toBeInTheDocument();
  });

  it("displays source type and severity on cards", () => {
    mockUseNuisanceSourcesReturn.sources = mockApiSources;

    render(<NuisancesTab data={mockDashboardData} />);

    expect(screen.getByText(/Airport · Concern/)).toBeInTheDocument();
    expect(screen.getByText(/Road · Caution/)).toBeInTheDocument();
  });

  it("displays distance on source cards", () => {
    mockUseNuisanceSourcesReturn.sources = mockApiSources;

    render(<NuisancesTab data={mockDashboardData} />);

    expect(screen.getByText("1.2 mi")).toBeInTheDocument();
    expect(screen.getByText("0.3 mi")).toBeInTheDocument();
  });

  it("sorts sources by severity (Concern before Caution)", () => {
    mockUseNuisanceSourcesReturn.sources = mockApiSources;

    render(<NuisancesTab data={mockDashboardData} />);

    const names = screen.getAllByRole("heading", { level: 4 }).map((h) => h.textContent);
    expect(names).toEqual(["RDU Airport", "US-401"]);
  });

  it("does not show empty state when sources are loading", () => {
    mockUseNuisanceSourcesReturn.loading = true;

    render(<NuisancesTab data={mockDashboardData} />);

    expect(screen.queryByText("No nuisances found")).not.toBeInTheDocument();
  });

  it("does not show empty state when API returns sources", () => {
    mockUseNuisanceSourcesReturn.sources = mockApiSources;

    render(<NuisancesTab data={mockDashboardData} />);

    expect(screen.queryByText("No nuisances found")).not.toBeInTheDocument();
  });
});
