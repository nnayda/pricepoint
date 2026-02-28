import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import NuisancesTab from "../NuisancesTab";
import { mockDashboardData } from "../../../../data/mockDashboardData";
import type { NuisanceSourceItem } from "../../../../types";

const mockUseNuisanceSourcesReturn = {
  sources: [] as NuisanceSourceItem[],
  loading: false,
  error: null as string | null,
};

vi.mock("../../../../hooks/useNuisanceSources", () => ({
  useNuisanceSources: vi.fn(() => mockUseNuisanceSourcesReturn),
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
    mockUseNuisanceSourcesReturn.sources = [];
    mockUseNuisanceSourcesReturn.loading = false;
    mockUseNuisanceSourcesReturn.error = null;
  });

  it("renders noise source toggle buttons", () => {
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

  it("renders vector tile layers for noise and infrastructure", () => {
    render(<NuisancesTab data={mockDashboardData} />);

    const sources = screen.getAllByTestId("vector-source");
    expect(sources.length).toBeGreaterThanOrEqual(2);
  });

  it("renders infrastructure toggle buttons", () => {
    render(<NuisancesTab data={mockDashboardData} />);
    expect(screen.getByText("Roads")).toBeInTheDocument();
    expect(screen.getByText("Rail")).toBeInTheDocument();
    expect(screen.getByText("Airports")).toBeInTheDocument();
  });

  it("clicking noise toggle updates active state", () => {
    render(<NuisancesTab data={mockDashboardData} />);

    const airportButton = screen.getByText("Airport");
    expect(airportButton.className).toContain("bg-[var(--color-db-accent)]");

    fireEvent.click(airportButton);
    expect(airportButton.className).not.toContain("bg-[var(--color-db-accent)]");
  });
});
