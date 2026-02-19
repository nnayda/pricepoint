import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "vitest-axe";
import PropertyMap from "../PropertyMap";
import type { CrimeResponse, PoisResponse } from "../../../types";

// Mock react-leaflet
vi.mock("react-leaflet", () => ({
  MapContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="map-container">{children}</div>
  ),
  TileLayer: () => <div data-testid="tile-layer" />,
  Marker: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="marker">{children}</div>
  ),
  Popup: ({ children }: { children: React.ReactNode }) => <div data-testid="popup">{children}</div>,
}));

// Mock layer components
vi.mock("../layers/CrimeHeatmapLayer", () => ({
  default: () => <div data-testid="crime-heatmap-layer" />,
}));
vi.mock("../layers/CrimeIncidentsLayer", () => ({
  default: () => <div data-testid="crime-incidents-layer" />,
}));
vi.mock("../layers/PoisLayer", () => ({
  default: () => <div data-testid="pois-layer" />,
}));
vi.mock("../layers/GreenspaceLayer", () => ({
  default: () => <div data-testid="greenspace-layer" />,
}));
vi.mock("../layers/UtilitiesLayer", () => ({
  default: () => <div data-testid="utilities-layer" />,
}));

// useApi mock with configurable return per call index
let useApiCallIndex = 0;
const mockCrimeExecute = vi.fn();
const mockPoisExecute = vi.fn();
const mockGreenspaceExecute = vi.fn();
const mockUtilitiesExecute = vi.fn();

type MockApiConfig = {
  data: unknown;
  loading: boolean;
  error: string | null;
  execute: ReturnType<typeof vi.fn>;
};

let apiConfigs: MockApiConfig[] = [];

function setApiConfigs(configs: MockApiConfig[]) {
  apiConfigs = configs;
}

function defaultApiConfigs(): MockApiConfig[] {
  return [
    { data: null, loading: false, error: null, execute: mockCrimeExecute },
    { data: null, loading: false, error: null, execute: mockPoisExecute },
    { data: null, loading: false, error: null, execute: mockGreenspaceExecute },
    { data: null, loading: false, error: null, execute: mockUtilitiesExecute },
  ];
}

vi.mock("../../../hooks/useApi", () => ({
  useApi: () => {
    const idx = useApiCallIndex % 4;
    useApiCallIndex++;
    return apiConfigs[idx] ?? apiConfigs[0];
  },
}));

// Mock usePoiPreferences
vi.mock("../../../hooks/usePoiPreferences", () => ({
  usePoiPreferences: () => ({
    preferences: [
      { id: "p1", name: "Grocery", category: "Grocery", enabled: true },
      { id: "p2", name: "Pharmacy", category: "Pharmacy", enabled: false },
    ],
    togglePoi: vi.fn(),
    toggleCategory: vi.fn(),
    addCustomPoi: vi.fn(),
    removeCustomPoi: vi.fn(),
  }),
}));

// Mock services
vi.mock("../../../services/property", () => ({
  getCrime: vi.fn(),
  getPois: vi.fn(),
  getGreenspace: vi.fn(),
  getUtilities: vi.fn(),
}));

const MOCK_CRIME_DATA: CrimeResponse = {
  heatmap: [{ lat: 35.78, lon: -78.64, intensity: 0.5 }],
  incidents: [
    {
      id: "1",
      incident_type: "Theft",
      category: "Property",
      date: "2025-01-01",
      lat: 35.78,
      lon: -78.64,
    },
  ],
  metrics: {
    total_incidents_1mi: 42,
    incidents_per_1000_people: 3.5,
    crime_z_score: 0.82,
    trend: "Decreasing",
  },
};

const MOCK_EMPTY_CRIME_DATA: CrimeResponse = {
  heatmap: [],
  incidents: [],
  metrics: {
    total_incidents_1mi: 0,
    incidents_per_1000_people: 0,
    crime_z_score: 0,
    trend: "Stable",
  },
};

const MOCK_EMPTY_POIS_DATA: PoisResponse = { pois: [] };

describe("PropertyMap", () => {
  beforeEach(() => {
    useApiCallIndex = 0;
    mockCrimeExecute.mockReset();
    mockPoisExecute.mockReset();
    mockGreenspaceExecute.mockReset();
    mockUtilitiesExecute.mockReset();
    setApiConfigs(defaultApiConfigs());
  });

  it("renders the section with accessible label", () => {
    render(<PropertyMap lat={35.78} lon={-78.64} address="123 Main St" />);
    expect(screen.getByLabelText("Property map")).toBeInTheDocument();
  });

  it("renders the map container", () => {
    render(<PropertyMap lat={35.78} lon={-78.64} address="123 Main St" />);
    expect(screen.getByTestId("map-container")).toBeInTheDocument();
  });

  it("renders the tile layer", () => {
    render(<PropertyMap lat={35.78} lon={-78.64} address="123 Main St" />);
    expect(screen.getByTestId("tile-layer")).toBeInTheDocument();
  });

  it("renders the property marker with address popup", () => {
    render(<PropertyMap lat={35.78} lon={-78.64} address="123 Main St" />);
    expect(screen.getByText("123 Main St")).toBeInTheDocument();
  });

  it("renders the tab bar with all 5 tabs", () => {
    render(<PropertyMap lat={35.78} lon={-78.64} address="123 Main St" />);
    expect(screen.getByRole("tablist", { name: "Map layers" })).toBeInTheDocument();
    expect(screen.getAllByRole("tab")).toHaveLength(5);
  });

  it("renders crime density tab as active by default", () => {
    render(<PropertyMap lat={35.78} lon={-78.64} address="123 Main St" />);
    expect(screen.getByText("Crime Density")).toHaveAttribute("aria-selected", "true");
  });

  it("renders the tab panel", () => {
    render(<PropertyMap lat={35.78} lon={-78.64} address="123 Main St" />);
    expect(screen.getByRole("tabpanel", { name: "crime-density metrics" })).toBeInTheDocument();
  });

  it("switches active tab on click", async () => {
    const user = userEvent.setup();
    render(<PropertyMap lat={35.78} lon={-78.64} address="123 Main St" />);

    await user.click(screen.getByText("Points of Interest"));
    expect(screen.getByText("Points of Interest")).toHaveAttribute("aria-selected", "true");
    expect(screen.getByText("Crime Density")).toHaveAttribute("aria-selected", "false");
  });

  it("has no accessibility violations", async () => {
    const { container } = render(<PropertyMap lat={35.78} lon={-78.64} address="123 Main St" />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  // --- New tests for dynamic map controls ---

  it("renders the radius dropdown with default value of 1 mile", () => {
    render(<PropertyMap lat={35.78} lon={-78.64} address="123 Main St" />);
    const radiusSelect = screen.getByLabelText("Search radius");
    expect(radiusSelect).toBeInTheDocument();
    expect(radiusSelect).toHaveValue("1");
  });

  it("renders all radius options (0.5, 1, 2, 3, 5 miles)", () => {
    render(<PropertyMap lat={35.78} lon={-78.64} address="123 Main St" />);
    const radiusSelect = screen.getByLabelText("Search radius");
    const options = within(radiusSelect).getAllByRole("option");
    expect(options).toHaveLength(5);
    expect(options.map((o) => o.textContent)).toEqual([
      "0.5 miles",
      "1 mile",
      "2 miles",
      "3 miles",
      "5 miles",
    ]);
  });

  it("shows crime date range filter when crime tab is active", () => {
    render(<PropertyMap lat={35.78} lon={-78.64} address="123 Main St" />);
    const dateSelect = screen.getByLabelText("Crime date range");
    expect(dateSelect).toBeInTheDocument();
  });

  it("hides crime date range filter when non-crime tab is active", async () => {
    const user = userEvent.setup();
    render(<PropertyMap lat={35.78} lon={-78.64} address="123 Main St" />);

    await user.click(screen.getByText("Points of Interest"));
    expect(screen.queryByLabelText("Crime date range")).not.toBeInTheDocument();
  });

  it("refetches data when radius changes", async () => {
    const user = userEvent.setup();
    render(<PropertyMap lat={35.78} lon={-78.64} address="123 Main St" />);

    // Initial fetch on mount
    expect(mockCrimeExecute).toHaveBeenCalledWith(35.78, -78.64, 1, 365);

    await user.selectOptions(screen.getByLabelText("Search radius"), "2");
    expect(mockCrimeExecute).toHaveBeenCalledWith(35.78, -78.64, 2, 365);
  });

  it("refetches crime data when days back changes", async () => {
    const user = userEvent.setup();
    render(<PropertyMap lat={35.78} lon={-78.64} address="123 Main St" />);

    expect(mockCrimeExecute).toHaveBeenCalledWith(35.78, -78.64, 1, 365);

    await user.selectOptions(screen.getByLabelText("Crime date range"), "30");
    expect(mockCrimeExecute).toHaveBeenCalledWith(35.78, -78.64, 1, 30);
  });

  it("shows empty results message when crime data has no incidents", () => {
    setApiConfigs([
      {
        data: MOCK_EMPTY_CRIME_DATA,
        loading: false,
        error: null,
        execute: mockCrimeExecute,
      },
      { data: null, loading: false, error: null, execute: mockPoisExecute },
      { data: null, loading: false, error: null, execute: mockGreenspaceExecute },
      { data: null, loading: false, error: null, execute: mockUtilitiesExecute },
    ]);
    render(<PropertyMap lat={35.78} lon={-78.64} address="123 Main St" />);
    expect(screen.getByText("No data found within 1 mile")).toBeInTheDocument();
  });

  it("shows empty results message for empty POIs on the pois tab", async () => {
    const user = userEvent.setup();
    setApiConfigs([
      { data: MOCK_CRIME_DATA, loading: false, error: null, execute: mockCrimeExecute },
      {
        data: MOCK_EMPTY_POIS_DATA,
        loading: false,
        error: null,
        execute: mockPoisExecute,
      },
      { data: null, loading: false, error: null, execute: mockGreenspaceExecute },
      { data: null, loading: false, error: null, execute: mockUtilitiesExecute },
    ]);
    render(<PropertyMap lat={35.78} lon={-78.64} address="123 Main St" />);

    await user.click(screen.getByText("Points of Interest"));
    expect(screen.getByText("No data found within 1 mile")).toBeInTheDocument();
  });

  it("shows loading spinner with text when tab is loading", () => {
    setApiConfigs([
      { data: null, loading: true, error: null, execute: mockCrimeExecute },
      { data: null, loading: false, error: null, execute: mockPoisExecute },
      { data: null, loading: false, error: null, execute: mockGreenspaceExecute },
      { data: null, loading: false, error: null, execute: mockUtilitiesExecute },
    ]);
    render(<PropertyMap lat={35.78} lon={-78.64} address="123 Main St" />);
    expect(screen.getByLabelText("Loading tab data")).toBeInTheDocument();
    expect(screen.getByText("Loading data...")).toBeInTheDocument();
  });

  it("shows crime metrics when crime data has results", () => {
    setApiConfigs([
      { data: MOCK_CRIME_DATA, loading: false, error: null, execute: mockCrimeExecute },
      { data: null, loading: false, error: null, execute: mockPoisExecute },
      { data: null, loading: false, error: null, execute: mockGreenspaceExecute },
      { data: null, loading: false, error: null, execute: mockUtilitiesExecute },
    ]);
    render(<PropertyMap lat={35.78} lon={-78.64} address="123 Main St" />);
    expect(screen.getByText("42")).toBeInTheDocument();
    expect(screen.getByText("Decreasing")).toBeInTheDocument();
  });
});
