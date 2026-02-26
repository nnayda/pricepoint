import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import GreenspaceTab from "../GreenspaceTab";
import { mockDashboardData } from "../../../../data/mockDashboardData";
import type { GreenspaceResponse } from "../../../../types";

/* Default mock bounds — wide enough to include all test features */
const mockBounds = {
  south: 35.5,
  west: -79.0,
  north: 36.1,
  east: -78.5,
};

vi.mock("react-leaflet", async () => {
  const React = await import("react");
  return {
    MapContainer: ({ children }: { children: React.ReactNode }) =>
      React.createElement("div", { "data-testid": "map-container" }, children),
    TileLayer: () => null,
    Marker: () => null,
    Popup: () => null,
    useMap: () => ({
      getBounds: () => ({
        getSouth: () => mockBounds.south,
        getWest: () => mockBounds.west,
        getNorth: () => mockBounds.north,
        getEast: () => mockBounds.east,
      }),
    }),
    useMapEvents: () => ({
      getBounds: () => ({
        getSouth: () => mockBounds.south,
        getWest: () => mockBounds.west,
        getNorth: () => mockBounds.north,
        getEast: () => mockBounds.east,
      }),
    }),
  };
});

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

vi.mock("../../maps/DashboardMap", () => ({
  default: ({
    markers,
    children,
  }: {
    children?: React.ReactNode;
    center: [number, number];
    zoom: number;
    markers: { id?: string; lat: number; lon: number; label: string; color: string }[];
    height: string;
    minHeight: string;
    highlightedId?: string | null;
    selectedId?: string | null;
  }) => (
    <div data-testid="dashboard-map" data-marker-count={markers.length}>
      {markers.map((m, i) => (
        <div key={i} data-testid="map-marker" data-label={m.label} data-color={m.color} />
      ))}
      {children}
    </div>
  ),
}));

describe("GreenspaceTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    mockUseGreenspaceReturn.data = mockGreenspaceResponse;
    mockUseGreenspaceReturn.loading = false;
    // Reset to wide bounds that include all features
    mockBounds.south = 35.5;
    mockBounds.west = -79.0;
    mockBounds.north = 36.1;
    mockBounds.east = -78.5;
  });

  it("renders feature cards for all greenspace features", () => {
    render(<GreenspaceTab data={mockDashboardData} />);

    expect(screen.getByText("Umstead State Park")).toBeInTheDocument();
    expect(screen.getByText("Black Creek Greenway")).toBeInTheDocument();
    expect(screen.getByText("Lake Johnson Park")).toBeInTheDocument();
  });

  it("displays feature type labels (Park/Trail)", () => {
    render(<GreenspaceTab data={mockDashboardData} />);

    const parkLabels = screen.getAllByText("Park");
    const trailLabels = screen.getAllByText("Trail");
    expect(parkLabels).toHaveLength(2);
    expect(trailLabels).toHaveLength(1);
  });

  it("shows distance for each feature", () => {
    render(<GreenspaceTab data={mockDashboardData} />);

    // Distances appear in feature cards (may also appear in metrics)
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

    expect(screen.getByText("Parks")).toBeInTheDocument();
    expect(screen.getByText("Trails")).toBeInTheDocument();
    expect(screen.getByText("Nearest Park")).toBeInTheDocument();
    expect(screen.getByText("Nearest Trail")).toBeInTheDocument();
    expect(screen.getByText("Green Acres")).toBeInTheDocument();
  });

  it("displays parks count as 2 (total park features)", () => {
    render(<GreenspaceTab data={mockDashboardData} />);

    const parksStatValue = screen.getByText("Parks").closest("div")?.querySelector(".font-db-mono");
    expect(parksStatValue?.textContent).toBe("2");
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
    // Button should have active class after click
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

    // Should not show feature names
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

  describe("map bounds filtering", () => {
    it("filters cards to only features within map bounds", () => {
      // Narrow bounds that only include Umstead State Park (lat 35.87, lon -78.75)
      mockBounds.south = 35.85;
      mockBounds.north = 35.9;
      mockBounds.west = -78.8;
      mockBounds.east = -78.7;

      render(<GreenspaceTab data={mockDashboardData} />);
      act(() => {
        vi.advanceTimersByTime(150);
      });

      expect(screen.getByText("Umstead State Park")).toBeInTheDocument();
      expect(screen.queryByText("Black Creek Greenway")).not.toBeInTheDocument();
      expect(screen.queryByText("Lake Johnson Park")).not.toBeInTheDocument();
    });

    it("updates park and trail counts based on visible features", () => {
      // Bounds that only include the trail (lat 35.79, lon -78.78)
      mockBounds.south = 35.78;
      mockBounds.north = 35.8;
      mockBounds.west = -78.8;
      mockBounds.east = -78.76;

      render(<GreenspaceTab data={mockDashboardData} />);
      act(() => {
        vi.advanceTimersByTime(150);
      });

      const parksStatValue = screen
        .getByText("Parks")
        .closest("div")
        ?.querySelector(".font-db-mono");
      const trailsStatValue = screen
        .getByText("Trails")
        .closest("div")
        ?.querySelector(".font-db-mono");
      expect(parksStatValue?.textContent).toBe("0");
      expect(trailsStatValue?.textContent).toBe("1");
    });

    it("shows all features when map bounds are wide", () => {
      render(<GreenspaceTab data={mockDashboardData} />);
      act(() => {
        vi.advanceTimersByTime(150);
      });

      expect(screen.getByText("Umstead State Park")).toBeInTheDocument();
      expect(screen.getByText("Black Creek Greenway")).toBeInTheDocument();
      expect(screen.getByText("Lake Johnson Park")).toBeInTheDocument();
    });

    it("shows empty state when no features are within bounds", () => {
      // Bounds that exclude all features
      mockBounds.south = 40.0;
      mockBounds.north = 41.0;
      mockBounds.west = -75.0;
      mockBounds.east = -74.0;

      render(<GreenspaceTab data={mockDashboardData} />);
      act(() => {
        vi.advanceTimersByTime(150);
      });

      expect(screen.getByText("No greenspaces or trails found nearby.")).toBeInTheDocument();
    });

    it("keeps all markers on map regardless of bounds", () => {
      // Narrow bounds — only one feature visible in cards
      mockBounds.south = 35.85;
      mockBounds.north = 35.9;
      mockBounds.west = -78.8;
      mockBounds.east = -78.7;

      render(<GreenspaceTab data={mockDashboardData} />);
      act(() => {
        vi.advanceTimersByTime(150);
      });

      const map = screen.getByTestId("dashboard-map");
      // All markers still on map: 1 property + 3 features = 4
      expect(map.getAttribute("data-marker-count")).toBe("4");
    });
  });
});
