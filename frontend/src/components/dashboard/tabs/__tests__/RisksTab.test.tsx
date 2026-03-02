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

const mockUseRisksReturn = {
  data: { features: mockFeatures },
  loading: false,
};

vi.mock("../../../../hooks/useRisks", () => ({
  useRisks: vi.fn(() => mockUseRisksReturn),
}));

vi.mock("react-map-gl/maplibre", () => ({
  Source: ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="vector-source">{children}</div>
  ),
  Layer: ({ id }: { id?: string }) => <div data-testid="vector-layer" data-layer-id={id} />,
  Popup: ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="map-popup">{children}</div>
  ),
  useMap: () => ({ current: null }),
}));

let capturedMarkers: Record<string, unknown>[] = [];

vi.mock("../../maps/DashboardMap", () => ({
  default: ({
    children,
    markers,
  }: {
    children?: React.ReactNode;
    center: [number, number];
    zoom: number;
    markers: Record<string, unknown>[];
    height: string;
    minHeight: string;
    highlightedId?: string | null;
    selectedId?: string | null;
  }) => {
    capturedMarkers = markers;
    return <div data-testid="dashboard-map">{children}</div>;
  },
}));

describe("RisksTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    capturedMarkers = [];
    mockUseRisksReturn.data = { features: mockFeatures };
    mockUseRisksReturn.loading = false;
  });

  it("renders infrastructure risk cards (only Caution/Concern in sidebar)", () => {
    render(<RisksTab data={mockDashboardData} />);
    // Safe items should NOT appear in the sidebar
    expect(screen.queryByText("AT&T Tower")).not.toBeInTheDocument();
    // Caution and Concern items should appear
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
    expect(screen.getByRole("button", { name: "Cell Towers" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Transmission Lines" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Power Plants" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Gas Pipelines" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Oil Pipelines" })).toBeInTheDocument();
  });

  it("filters cards when toggle is clicked", () => {
    render(<RisksTab data={mockDashboardData} />);

    expect(screen.getByText("Duke Energy Line")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Transmission Lines" }));

    expect(screen.queryByText("Duke Energy Line")).not.toBeInTheDocument();
    expect(screen.getByText("Shearon Harris")).toBeInTheDocument();
  });

  it("shows loading spinner", () => {
    mockUseRisksReturn.loading = true;
    const { container } = render(<RisksTab data={mockDashboardData} />);
    const spinners = container.querySelectorAll(".animate-spin");
    expect(spinners.length).toBeGreaterThan(0);
  });

  it("shows empty state when no features", () => {
    mockUseRisksReturn.data = { features: [] };
    render(<RisksTab data={mockDashboardData} />);
    expect(screen.getByText("No infrastructure risks found")).toBeInTheDocument();
  });

  it("shows empty state when all features are Safe", () => {
    mockUseRisksReturn.data = { features: [mockFeatures[0]] };
    render(<RisksTab data={mockDashboardData} />);
    expect(screen.getByText("No infrastructure risks found")).toBeInTheDocument();
  });

  it("renders Risk Map heading", () => {
    render(<RisksTab data={mockDashboardData} />);
    expect(screen.getByText("Risk Map")).toBeInTheDocument();
  });

  it("renders distance for each sidebar card", () => {
    render(<RisksTab data={mockDashboardData} />);
    expect(screen.getByText(/0\.3 mi/)).toBeInTheDocument();
    expect(screen.getByText(/1\.2 mi/)).toBeInTheDocument();
    expect(screen.queryByText(/0\.8 mi/)).not.toBeInTheDocument();
  });

  it("re-enables filter when toggle clicked twice", () => {
    render(<RisksTab data={mockDashboardData} />);

    fireEvent.click(screen.getByRole("button", { name: "Transmission Lines" }));
    expect(screen.queryByText("Duke Energy Line")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Transmission Lines" }));
    expect(screen.getByText("Duke Energy Line")).toBeInTheDocument();
  });

  it("passes infrastructureType to DashboardMap markers", () => {
    render(<RisksTab data={mockDashboardData} />);
    const infraMarkers = capturedMarkers.filter((m) => m.infrastructureType);
    expect(infraMarkers.length).toBe(3);
    expect(infraMarkers.map((m) => m.infrastructureType)).toEqual(
      expect.arrayContaining(["cell_tower", "transmission_line", "power_plant"]),
    );
  });

  it("renders vector tile sources for risk boundaries and infrastructure", () => {
    render(<RisksTab data={mockDashboardData} />);
    const sources = screen.getAllByTestId("vector-source");
    expect(sources.length).toBeGreaterThanOrEqual(2);
  });
});
