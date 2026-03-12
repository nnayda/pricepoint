import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import PoliceTab from "../PoliceTab";
import { mockDashboardData } from "../../../../data/mockDashboardData";
import type { CrimeIncident } from "../../../../types";

const mockIncidents: CrimeIncident[] = [
  {
    id: "RPD-1001",
    incident_type: "Larceny",
    category: "Crimes Against Property",
    date: "2025-12-01",
    lat: 35.79,
    lon: -78.78,
    description: "Larceny from vehicle",
    address: "100 Main St, Raleigh, NC",
    crime_group: "Crimes Against Property",
    offense_class: "Group A",
  },
  {
    id: "CPD-2001",
    incident_type: "Simple Assault",
    category: "Crimes Against Persons",
    date: "2025-11-20",
    lat: 35.791,
    lon: -78.781,
    description: "Simple assault",
    address: "200 Oak Ave, Cary, NC",
    crime_group: "Group B",
    offense_class: "Group B",
  },
  {
    id: "MPD-3001",
    incident_type: "Unknown",
    category: "Other",
    date: "2025-11-15",
    lat: 35.792,
    lon: -78.782,
    description: "Suspicious activity",
    address: null as unknown as string,
    crime_group: null,
    offense_class: null,
  },
];

const mockUsePoliceIncidents = vi.fn();

vi.mock("../../../../hooks/usePoliceIncidents", () => ({
  usePoliceIncidents: (...args: unknown[]) => mockUsePoliceIncidents(...args),
  preloadPoliceIncidents: vi.fn(),
}));

vi.mock("../../maps/DashboardMap", () => ({
  __esModule: true,
  default: ({ markers }: { markers: { id?: string; label: string }[] }) => (
    <div data-testid="dashboard-map">
      {markers.map((m, i) => (
        <span key={i} data-testid="map-marker">
          {m.label}
        </span>
      ))}
    </div>
  ),
}));

describe("PoliceTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders loading state", () => {
    mockUsePoliceIncidents.mockReturnValue({
      incidents: [],
      loading: true,
      error: null,
    });
    render(<PoliceTab data={mockDashboardData} />);
    expect(screen.getByRole("status")).toBeInTheDocument();
    expect(screen.getAllByText("Loading crime incidents...")).toHaveLength(2);
  });

  it("renders error state when error and no incidents", () => {
    mockUsePoliceIncidents.mockReturnValue({
      incidents: [],
      loading: false,
      error: "Network error",
    });
    render(<PoliceTab data={mockDashboardData} />);
    expect(
      screen.getByText("Unable to load crime incidents. Please try again later."),
    ).toBeInTheDocument();
  });

  it("renders empty state with map when no incidents", () => {
    mockUsePoliceIncidents.mockReturnValue({
      incidents: [],
      loading: false,
      error: null,
    });
    render(<PoliceTab data={mockDashboardData} />);
    expect(screen.getByText("No crime incidents found near this property.")).toBeInTheDocument();
    // Map should still render with property marker
    expect(screen.getByTestId("dashboard-map")).toBeInTheDocument();
    expect(screen.getAllByTestId("map-marker")).toHaveLength(1);
  });

  it("renders incident cards with data", () => {
    mockUsePoliceIncidents.mockReturnValue({
      incidents: mockIncidents,
      loading: false,
      error: null,
    });
    render(<PoliceTab data={mockDashboardData} />);
    expect(screen.getByText("Crime Incidents")).toBeInTheDocument();
    expect(screen.getAllByTestId("incident-card")).toHaveLength(3);
  });

  it("displays incident details on cards", () => {
    mockUsePoliceIncidents.mockReturnValue({
      incidents: mockIncidents,
      loading: false,
      error: null,
    });
    render(<PoliceTab data={mockDashboardData} />);
    // incident_type is now the card title, category is secondary
    expect(screen.getByText("Larceny")).toBeInTheDocument();
    expect(screen.getByText("Crimes Against Property")).toBeInTheDocument();
    expect(screen.getByText("100 Main St, Raleigh, NC")).toBeInTheDocument();
    expect(screen.getByText("RPD-1001")).toBeInTheDocument();
  });

  it("renders correct offense group dot colors", () => {
    mockUsePoliceIncidents.mockReturnValue({
      incidents: mockIncidents,
      loading: false,
      error: null,
    });
    render(<PoliceTab data={mockDashboardData} />);
    const dots = screen.getAllByTestId("offense-dot");
    expect(dots).toHaveLength(3);
    // Group A (not null, not "Group B") → red
    expect(dots[0]).toHaveStyle({ backgroundColor: "#F87171" });
    // Group B → blue
    expect(dots[1]).toHaveStyle({ backgroundColor: "#5B7FFF" });
    // null → gray
    expect(dots[2]).toHaveStyle({ backgroundColor: "#94A3B8" });
  });

  it("renders the map with markers", () => {
    mockUsePoliceIncidents.mockReturnValue({
      incidents: mockIncidents,
      loading: false,
      error: null,
    });
    render(<PoliceTab data={mockDashboardData} />);
    expect(screen.getByTestId("dashboard-map")).toBeInTheDocument();
    // Property marker + 3 incident markers
    expect(screen.getAllByTestId("map-marker")).toHaveLength(4);
  });

  it("shows legend with all three groups", () => {
    mockUsePoliceIncidents.mockReturnValue({
      incidents: mockIncidents,
      loading: false,
      error: null,
    });
    render(<PoliceTab data={mockDashboardData} />);
    expect(screen.getByText("Severe")).toBeInTheDocument();
    expect(screen.getByText("Minor")).toBeInTheDocument();
    expect(screen.getAllByText("Unknown").length).toBeGreaterThanOrEqual(1);
  });
});
