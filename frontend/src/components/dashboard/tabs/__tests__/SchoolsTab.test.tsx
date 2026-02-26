import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import SchoolsTab from "../SchoolsTab";
import { mockDashboardData } from "../../../../data/mockDashboardData";
import type { SchoolNearby, SchoolDistrictInfo } from "../../../../types";

const mockSchools: SchoolNearby[] = [
  {
    name: "Oak Elementary",
    address: "100 Oak St, Cary, NC, 27513",
    school_type: "Regular",
    school_level: "Elementary",
    rating: 8,
    grades: "K-5",
    distance_miles: 1.2,
    drive_minutes: 4,
    walk_minutes: 18,
    student_teacher_ratio: 15.0,
    enrollment: 500,
    assigned: true,
    lat: 35.79,
    lon: -78.78,
    pct_frl_eligible: 20.0,
    in_district: true,
  },
  {
    name: "Pine Middle",
    address: "200 Pine Ave, Cary, NC, 27513",
    school_type: "Regular",
    school_level: "Middle",
    rating: 7,
    grades: "6-8",
    distance_miles: 2.0,
    drive_minutes: 6,
    walk_minutes: null,
    student_teacher_ratio: 18.0,
    enrollment: 800,
    assigned: false,
    lat: 35.795,
    lon: -78.785,
    pct_frl_eligible: 30.0,
    in_district: true,
  },
  {
    name: "Elm High",
    address: "300 Elm Blvd, Cary, NC, 27513",
    school_type: "Regular",
    school_level: "High",
    rating: 6,
    grades: "9-12",
    distance_miles: 3.5,
    drive_minutes: 10,
    walk_minutes: null,
    student_teacher_ratio: 20.0,
    enrollment: 1500,
    assigned: false,
    lat: 35.8,
    lon: -78.79,
    pct_frl_eligible: 25.0,
    in_district: true,
  },
];

const mockDistricts: SchoolDistrictInfo[] = [
  {
    name: "Wake County Schools",
    geoid: "3700390",
    district_type: "unified",
    geojson: {
      type: "MultiPolygon",
      coordinates: [
        [
          [
            [0, 0],
            [1, 0],
            [1, 1],
            [0, 0],
          ],
        ],
      ],
    } as unknown as GeoJSON.GeoJsonObject,
    is_home: true,
    label_lat: 35.79,
    label_lon: -78.78,
  },
  {
    name: "Durham Elementary District",
    geoid: "3701170",
    district_type: "elementary",
    geojson: {
      type: "MultiPolygon",
      coordinates: [
        [
          [
            [1, 0],
            [2, 0],
            [2, 1],
            [1, 0],
          ],
        ],
      ],
    } as unknown as GeoJSON.GeoJsonObject,
    is_home: false,
    label_lat: 36.0,
    label_lon: -78.9,
  },
  {
    name: "Durham Secondary District",
    geoid: "3701171",
    district_type: "secondary",
    geojson: {
      type: "MultiPolygon",
      coordinates: [
        [
          [
            [2, 0],
            [3, 0],
            [3, 1],
            [2, 0],
          ],
        ],
      ],
    } as unknown as GeoJSON.GeoJsonObject,
    is_home: false,
    label_lat: 36.01,
    label_lon: -78.91,
  },
];

vi.mock("../../../../hooks/useSchoolsNearby", () => ({
  useSchoolsNearby: () => ({
    schools: mockSchools,
    schoolDistricts: mockDistricts,
    loading: false,
    error: null,
  }),
}));

vi.mock("react-leaflet", async () => {
  const React = await import("react");
  return {
    MapContainer: ({ children }: { children: React.ReactNode }) =>
      React.createElement("div", { "data-testid": "map-container" }, children),
    TileLayer: () => null,
    Marker: () => null,
    Popup: () => null,
    GeoJSON: ({ data }: { data: unknown }) =>
      React.createElement("div", {
        "data-testid": "geojson-layer",
        "data-geojson": JSON.stringify(data),
      }),
    useMap: () => ({
      getBounds: () => ({
        getSouth: () => 35.5,
        getWest: () => -79.0,
        getNorth: () => 36.1,
        getEast: () => -78.5,
      }),
    }),
    useMapEvents: () => ({
      getBounds: () => ({
        getSouth: () => 35.5,
        getWest: () => -79.0,
        getNorth: () => 36.1,
        getEast: () => -78.5,
      }),
    }),
  };
});

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

describe("SchoolsTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders school cards for all schools", () => {
    render(<SchoolsTab data={mockDashboardData} />);
    expect(screen.getByText("Oak Elementary")).toBeInTheDocument();
    expect(screen.getByText("Pine Middle")).toBeInTheDocument();
    expect(screen.getByText("Elm High")).toBeInTheDocument();
  });

  it("shows assigned badge on assigned school", () => {
    render(<SchoolsTab data={mockDashboardData} />);
    expect(screen.getByText("Assigned")).toBeInTheDocument();
  });

  it("renders level filter buttons", () => {
    render(<SchoolsTab data={mockDashboardData} />);
    expect(screen.getByText("Elementary")).toBeInTheDocument();
    expect(screen.getByText("Middle")).toBeInTheDocument();
    expect(screen.getByText("High")).toBeInTheDocument();
  });

  it("displays home district name in header", () => {
    render(<SchoolsTab data={mockDashboardData} />);
    expect(screen.getByText("Wake County Schools Schools")).toBeInTheDocument();
  });

  it("renders GeoJSON layers for district boundaries", () => {
    render(<SchoolsTab data={mockDashboardData} />);
    const geojsonLayers = screen.getAllByTestId("geojson-layer");
    // 3 districts: 1 home + 2 neighbors
    expect(geojsonLayers.length).toBe(3);
  });

  it("filters school cards when toggling level filter", () => {
    render(<SchoolsTab data={mockDashboardData} />);

    // Click Elementary to toggle it off
    fireEvent.click(screen.getByText("Elementary"));

    // Oak Elementary should be hidden (assigned schools always show but only if they pass level filter)
    expect(screen.queryByText("Oak Elementary")).not.toBeInTheDocument();
    expect(screen.getByText("Pine Middle")).toBeInTheDocument();
    expect(screen.getByText("Elm High")).toBeInTheDocument();
  });

  it("shows school distance and drive time", () => {
    render(<SchoolsTab data={mockDashboardData} />);
    expect(screen.getByText("1.2 mi")).toBeInTheDocument();
    expect(screen.getByText("4 min drive")).toBeInTheDocument();
  });

  it("shows walk time when available", () => {
    render(<SchoolsTab data={mockDashboardData} />);
    // Oak Elementary has walk_minutes: 18
    expect(screen.getByText("18 min walk")).toBeInTheDocument();
  });

  it("hides walk time when null", () => {
    render(<SchoolsTab data={mockDashboardData} />);
    // Pine Middle has walk_minutes: null, drive_minutes: 6
    expect(screen.getByText("6 min drive")).toBeInTheDocument();
    // Should not show a walk time for schools with null walk_minutes
    expect(screen.queryByText("0 min walk")).not.toBeInTheDocument();
  });

  it("shows drive times for all schools", () => {
    render(<SchoolsTab data={mockDashboardData} />);
    expect(screen.getByText("4 min drive")).toBeInTheDocument();
    expect(screen.getByText("6 min drive")).toBeInTheDocument();
    expect(screen.getByText("10 min drive")).toBeInTheDocument();
  });

  it("shows enrollment count", () => {
    render(<SchoolsTab data={mockDashboardData} />);
    expect(screen.getByText("500 students")).toBeInTheDocument();
  });
});
