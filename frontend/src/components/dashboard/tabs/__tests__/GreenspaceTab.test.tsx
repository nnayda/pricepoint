import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import GreenspaceTab from "../GreenspaceTab";
import { mockDashboardData } from "../../../../data/mockDashboardData";
import type { GreenspaceResponse } from "../../../../types";

vi.mock("react-map-gl/maplibre", () => ({
  Source: ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="vector-source">{children}</div>
  ),
  Layer: ({ id }: { id?: string }) => <div data-testid="vector-layer" data-layer-id={id} />,
}));

const mockGreenspaceResponse: GreenspaceResponse = {
  features: [
    {
      id: "park-padus-10",
      name: "Umstead State Park",
      feature_type: "park",
      lat: 35.87,
      lon: -78.75,
      distance_miles: 0.5,
      acreage: 55.3,
    },
    {
      id: "trail-usgs-100",
      name: "Black Creek Greenway",
      feature_type: "trail",
      lat: 35.79,
      lon: -78.78,
      distance_miles: 0.3,
    },
    {
      id: "park-padus-20",
      name: "Lake Johnson Park",
      feature_type: "park",
      lat: 35.76,
      lon: -78.71,
      distance_miles: 1.5,
      acreage: 28.0,
    },
  ],
  metrics: {
    parks_within_1mi: 1,
    nearest_park_miles: 0.5,
    nearest_greenway_miles: 0.3,
    total_green_acres_1mi: 55.3,
    greenspace_z_score: 0.0,
  },
};

const mockUseGreenspaceReturn = {
  data: mockGreenspaceResponse,
  loading: false,
};

vi.mock("../../../../hooks/useGreenspace", () => ({
  useGreenspace: vi.fn(() => mockUseGreenspaceReturn),
}));

let capturedOnMarkerSelect: ((id: string) => void) | undefined;
let capturedOnMarkerDeselect: (() => void) | undefined;
let capturedRenderPopup:
  | ((marker: { id?: string; label: string }) => React.ReactNode)
  | undefined;

vi.mock("../../maps/DashboardMap", () => ({
  default: ({
    markers,
    children,
    onMarkerSelect,
    onMarkerDeselect,
    renderPopup,
  }: {
    children?: React.ReactNode;
    center: [number, number];
    zoom: number;
    markers: { id?: string; lat: number; lon: number; label: string; color: string }[];
    height: string;
    minHeight: string;
    highlightedId?: string | null;
    selectedId?: string | null;
    onMoveEnd?: (bbox: { swLat: number; swLon: number; neLat: number; neLon: number }) => void;
    onMarkerSelect?: (id: string) => void;
    onMarkerDeselect?: () => void;
    renderPopup?: (marker: { id?: string; label: string }) => React.ReactNode;
  }) => {
    capturedOnMarkerSelect = onMarkerSelect;
    capturedOnMarkerDeselect = onMarkerDeselect;
    capturedRenderPopup = renderPopup;
    return (
      <div data-testid="dashboard-map" data-marker-count={markers.length}>
        {markers.map((m, i) => (
          <div key={i} data-testid="map-marker" data-label={m.label} data-color={m.color} />
        ))}
        {children}
      </div>
    );
  },
}));

describe("GreenspaceTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseGreenspaceReturn.data = mockGreenspaceResponse;
    mockUseGreenspaceReturn.loading = false;
    capturedOnMarkerSelect = undefined;
    capturedOnMarkerDeselect = undefined;
    capturedRenderPopup = undefined;
  });

  it("renders feature cards for all greenspace features", () => {
    render(<GreenspaceTab data={mockDashboardData} />);

    expect(screen.getByText("Umstead State Park")).toBeInTheDocument();
    expect(screen.getByText("Black Creek Greenway")).toBeInTheDocument();
    expect(screen.getByText("Lake Johnson Park")).toBeInTheDocument();
  });

  it("displays feature type labels (Park/Trail)", () => {
    render(<GreenspaceTab data={mockDashboardData} />);

    // Card labels + filter button labels
    const parkLabels = screen.getAllByText("Park");
    const trailLabels = screen.getAllByText("Trail");
    expect(parkLabels.length).toBeGreaterThanOrEqual(2);
    expect(trailLabels.length).toBeGreaterThanOrEqual(1);
  });

  it("shows distance for each feature", () => {
    render(<GreenspaceTab data={mockDashboardData} />);

    expect(screen.getAllByText("0.5 mi").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("0.3 mi").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("1.5 mi")).toBeInTheDocument();
  });

  it("shows acreage for park features", () => {
    render(<GreenspaceTab data={mockDashboardData} />);

    expect(screen.getByText("55.3 acres")).toBeInTheDocument();
    expect(screen.getByText("28 acres")).toBeInTheDocument();
  });

  it("renders metric stats from API data", () => {
    render(<GreenspaceTab data={mockDashboardData} />);

    expect(screen.getByText("Nearest Park")).toBeInTheDocument();
    expect(screen.getByText("Nearest Trail")).toBeInTheDocument();
    expect(screen.getByText("Green Acres")).toBeInTheDocument();
  });

  it("displays nearest park distance in metrics", () => {
    render(<GreenspaceTab data={mockDashboardData} />);

    const nearestParkStat = screen
      .getByText("Nearest Park")
      .closest("div")
      ?.querySelector(".font-db-mono");
    expect(nearestParkStat?.textContent).toBe("0.5 mi");
  });

  it("displays nearest trail distance in metrics", () => {
    render(<GreenspaceTab data={mockDashboardData} />);

    const nearestTrailStat = screen
      .getByText("Nearest Trail")
      .closest("div")
      ?.querySelector(".font-db-mono");
    expect(nearestTrailStat?.textContent).toBe("0.3 mi");
  });

  it("renders map with property marker and feature markers", () => {
    render(<GreenspaceTab data={mockDashboardData} />);

    const map = screen.getByTestId("dashboard-map");
    // 1 property + 3 features = 4 markers
    expect(map.getAttribute("data-marker-count")).toBe("4");
  });

  it("colors park markers green and trail markers cyan", () => {
    render(<GreenspaceTab data={mockDashboardData} />);

    const markers = screen.getAllByTestId("map-marker");
    const parkMarkers = markers.filter((m) => m.getAttribute("data-color") === "#34D399");
    const trailMarkers = markers.filter((m) => m.getAttribute("data-color") === "#22D3EE");
    expect(parkMarkers).toHaveLength(2);
    expect(trailMarkers).toHaveLength(1);
  });

  it("renders scope toggle buttons", () => {
    render(<GreenspaceTab data={mockDashboardData} />);

    expect(screen.getByText("subdivision")).toBeInTheDocument();
    expect(screen.getByText("neighborhood")).toBeInTheDocument();
    expect(screen.getByText("town")).toBeInTheDocument();
  });

  it("can toggle map scope", () => {
    render(<GreenspaceTab data={mockDashboardData} />);

    const townButton = screen.getByText("town");
    fireEvent.click(townButton);
    expect(townButton.className).toContain("bg-[var(--color-db-accent)]");
  });

  it("shows loading skeleton when data is loading", () => {
    mockUseGreenspaceReturn.loading = true;
    mockUseGreenspaceReturn.data = {
      features: [],
      metrics: {
        parks_within_1mi: 0,
        nearest_park_miles: 0,
        nearest_greenway_miles: 0,
        total_green_acres_1mi: 0,
        greenspace_z_score: 0,
      },
    };

    render(<GreenspaceTab data={mockDashboardData} />);

    expect(screen.queryByText("Umstead State Park")).not.toBeInTheDocument();
  });

  it("shows empty state when no features returned", () => {
    mockUseGreenspaceReturn.data = {
      features: [],
      metrics: {
        parks_within_1mi: 0,
        nearest_park_miles: 0,
        nearest_greenway_miles: 0,
        total_green_acres_1mi: 0,
        greenspace_z_score: 0,
      },
    };

    render(<GreenspaceTab data={mockDashboardData} />);

    expect(screen.getByText("No greenspaces or trails found nearby.")).toBeInTheDocument();
  });

  it("shows dash for nearest park when value is 0", () => {
    mockUseGreenspaceReturn.data = {
      features: [],
      metrics: {
        parks_within_1mi: 0,
        nearest_park_miles: 0,
        nearest_greenway_miles: 0,
        total_green_acres_1mi: 0,
        greenspace_z_score: 0,
      },
    };

    render(<GreenspaceTab data={mockDashboardData} />);

    const nearestParkStat = screen
      .getByText("Nearest Park")
      .closest("div")
      ?.querySelector(".font-db-mono");
    expect(nearestParkStat?.textContent).toBe("—");
  });

  it("renders vector tile layers for greenspaces and trails", () => {
    render(<GreenspaceTab data={mockDashboardData} />);

    const sources = screen.getAllByTestId("vector-source");
    expect(sources.length).toBeGreaterThanOrEqual(2);
  });

  // --- Type filter tests ---

  it("renders Parks and Trails filter toggle buttons", () => {
    render(<GreenspaceTab data={mockDashboardData} />);

    expect(screen.getByRole("button", { name: "Parks" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Trails" })).toBeInTheDocument();
  });

  it("filters out trails when Trails toggle is deactivated", () => {
    render(<GreenspaceTab data={mockDashboardData} />);

    const trailsButton = screen.getByRole("button", { name: "Trails" });
    fireEvent.click(trailsButton);

    // Trail card should be hidden
    expect(screen.queryByText("Black Creek Greenway")).not.toBeInTheDocument();
    // Park cards remain
    expect(screen.getByText("Umstead State Park")).toBeInTheDocument();
    expect(screen.getByText("Lake Johnson Park")).toBeInTheDocument();
  });

  it("filters out parks when Parks toggle is deactivated", () => {
    render(<GreenspaceTab data={mockDashboardData} />);

    const parksButton = screen.getByRole("button", { name: "Parks" });
    fireEvent.click(parksButton);

    // Park cards should be hidden
    expect(screen.queryByText("Umstead State Park")).not.toBeInTheDocument();
    expect(screen.queryByText("Lake Johnson Park")).not.toBeInTheDocument();
    // Trail card remains
    expect(screen.getByText("Black Creek Greenway")).toBeInTheDocument();
  });

  it("filters map markers when type toggle is used", () => {
    render(<GreenspaceTab data={mockDashboardData} />);

    const trailsButton = screen.getByRole("button", { name: "Trails" });
    fireEvent.click(trailsButton);

    const map = screen.getByTestId("dashboard-map");
    // 1 property + 2 parks = 3 markers (trail excluded)
    expect(map.getAttribute("data-marker-count")).toBe("3");
  });

  // --- Map interaction tests ---

  it("passes onMarkerSelect and onMarkerDeselect to the map", () => {
    render(<GreenspaceTab data={mockDashboardData} />);

    expect(capturedOnMarkerSelect).toBeTypeOf("function");
    expect(capturedOnMarkerDeselect).toBeTypeOf("function");
  });

  it("passes renderPopup to the map", () => {
    render(<GreenspaceTab data={mockDashboardData} />);

    expect(capturedRenderPopup).toBeTypeOf("function");
  });

  it("renderPopup returns feature details for a known marker", () => {
    render(<GreenspaceTab data={mockDashboardData} />);

    const popup = capturedRenderPopup!({
      id: "park-padus-10",
      label: "Umstead State Park (Park)",
    });
    const { container } = render(popup as React.ReactElement);

    expect(container.textContent).toContain("Umstead State Park");
    expect(container.textContent).toContain("Park");
    expect(container.textContent).toContain("0.5 mi");
    expect(container.textContent).toContain("55.3 acres");
  });

  it("renderPopup returns label for unknown marker", () => {
    render(<GreenspaceTab data={mockDashboardData} />);

    const popup = capturedRenderPopup!({
      id: "unknown-id",
      label: "Unknown Feature",
    });
    const { container } = render(popup as React.ReactElement);

    expect(container.textContent).toContain("Unknown Feature");
  });

  it("highlights card when it is hovered", () => {
    render(<GreenspaceTab data={mockDashboardData} />);

    const card = screen.getByText("Umstead State Park").closest("[class*=cursor-pointer]")!;
    fireEvent.mouseEnter(card);

    // After hover the card should have accent-muted background
    expect(card.style.backgroundColor).toBe("var(--color-db-accent-muted)");
  });

  it("selects card on click and toggles on second click", () => {
    render(<GreenspaceTab data={mockDashboardData} />);

    const card = screen.getByText("Umstead State Park").closest("[class*=cursor-pointer]")!;

    // Click to select
    fireEvent.click(card);
    expect(card.style.borderColor).toBe("var(--color-db-accent)");

    // Click again to deselect
    fireEvent.click(card);
    expect(card.style.borderColor).toBe("var(--color-db-border-subtle)");
  });
});
