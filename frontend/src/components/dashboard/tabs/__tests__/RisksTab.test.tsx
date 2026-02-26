import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import RisksTab from "../RisksTab";
import { mockDashboardData } from "../../../../data/mockDashboardData";
import type { RiskFeature } from "../../../../types";

const mockFeatures: RiskFeature[] = [
  {
    id: "RB-C-10",
    name: "AT&T Tower",
    infrastructure_type: "cell_tower",
    severity: "Safe",
    distance_miles: 0.8,
    lat: 35.8,
    lon: -78.77,
    detail: "Cell Tower — outside risk zones",
  },
  {
    id: "RB-T-20",
    name: "Duke Energy Line",
    infrastructure_type: "transmission_line",
    severity: "Caution",
    distance_miles: 0.3,
    lat: 35.791,
    lon: -78.781,
    detail: "Transmission Line — within caution risk zone",
  },
  {
    id: "RB-P-30",
    name: "Shearon Harris",
    infrastructure_type: "power_plant",
    severity: "Concern",
    distance_miles: 1.2,
    lat: 35.785,
    lon: -78.769,
    detail: "Power Plant — within critical risk zone",
  },
];

const mockBoundaryGeojson: GeoJSON.FeatureCollection = {
  type: "FeatureCollection",
  features: [
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
      properties: {
        infrastructure_type: "power_plant",
        infrastructure_id: 30,
        severity: "critical",
      },
    },
  ],
};

const mockUseRisksReturn = {
  data: { features: mockFeatures, boundaryGeojson: mockBoundaryGeojson },
  loading: false,
};

vi.mock("../../../../hooks/useRisks", () => ({
  useRisks: vi.fn(() => mockUseRisksReturn),
}));

// Mock react-leaflet to avoid DOM issues
vi.mock("react-leaflet", () => ({
  MapContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="map-container">{children}</div>
  ),
  TileLayer: () => <div data-testid="tile-layer" />,
  Marker: () => <div data-testid="marker" />,
  Popup: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  GeoJSON: () => <div data-testid="geojson-layer" />,
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

describe("RisksTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseRisksReturn.data = {
      features: mockFeatures,
      boundaryGeojson: mockBoundaryGeojson,
    };
    mockUseRisksReturn.loading = false;
  });

  it("renders infrastructure risk cards", () => {
    render(<RisksTab data={mockDashboardData} />);
    expect(screen.getByText("AT&T Tower")).toBeInTheDocument();
    expect(screen.getByText("Duke Energy Line")).toBeInTheDocument();
    expect(screen.getByText("Shearon Harris")).toBeInTheDocument();
  });

  it("renders cards sorted by severity (Concern first)", () => {
    render(<RisksTab data={mockDashboardData} />);
    const cards = screen.getAllByText(/risk zone|outside risk/);
    // Concern (critical) should be first
    expect(cards[0].textContent).toContain("critical risk zone");
  });

  it("renders filter toggle buttons", () => {
    render(<RisksTab data={mockDashboardData} />);
    expect(screen.getByText("Cell Towers")).toBeInTheDocument();
    expect(screen.getByText("Transmission Lines")).toBeInTheDocument();
    expect(screen.getByText("Power Plants")).toBeInTheDocument();
    expect(screen.getByText("Gas Pipelines")).toBeInTheDocument();
    expect(screen.getByText("Oil Pipelines")).toBeInTheDocument();
  });

  it("filters cards when toggle is clicked", () => {
    render(<RisksTab data={mockDashboardData} />);

    // Initially all 3 cards visible
    expect(screen.getByText("AT&T Tower")).toBeInTheDocument();

    // Click "Cell Towers" to deactivate
    fireEvent.click(screen.getByText("Cell Towers"));

    // Cell tower card should disappear
    expect(screen.queryByText("AT&T Tower")).not.toBeInTheDocument();
    // Others still visible
    expect(screen.getByText("Duke Energy Line")).toBeInTheDocument();
  });

  it("shows loading spinner", () => {
    mockUseRisksReturn.loading = true;
    const { container } = render(<RisksTab data={mockDashboardData} />);
    const spinners = container.querySelectorAll(".animate-spin");
    expect(spinners.length).toBeGreaterThan(0);
  });

  it("shows empty state when no features", () => {
    mockUseRisksReturn.data = {
      features: [],
      boundaryGeojson: { type: "FeatureCollection", features: [] },
    };
    render(<RisksTab data={mockDashboardData} />);
    expect(screen.getByText("No infrastructure risks found nearby")).toBeInTheDocument();
  });

  it("renders Risk Map heading", () => {
    render(<RisksTab data={mockDashboardData} />);
    expect(screen.getByText("Risk Map")).toBeInTheDocument();
  });

  it("renders distance for each card", () => {
    render(<RisksTab data={mockDashboardData} />);
    expect(screen.getByText(/0\.8 mi/)).toBeInTheDocument();
    expect(screen.getByText(/0\.3 mi/)).toBeInTheDocument();
    expect(screen.getByText(/1\.2 mi/)).toBeInTheDocument();
  });

  it("re-enables filter when toggle clicked twice", () => {
    render(<RisksTab data={mockDashboardData} />);

    // Disable then re-enable
    fireEvent.click(screen.getByText("Cell Towers"));
    expect(screen.queryByText("AT&T Tower")).not.toBeInTheDocument();

    fireEvent.click(screen.getByText("Cell Towers"));
    expect(screen.getByText("AT&T Tower")).toBeInTheDocument();
  });
});
