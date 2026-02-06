import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "vitest-axe";
import PropertyMap from "../PropertyMap";

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

// Mock useApi
const mockExecute = vi.fn();
const createMockApi = (data: unknown = null, loading = false, error: string | null = null) => ({
  data,
  loading,
  error,
  execute: mockExecute,
});

vi.mock("../../../hooks/useApi", () => ({
  useApi: () => {
    // PropertyMap calls useApi 4 times: crime, pois, greenspace, utilities
    return createMockApi();
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

describe("PropertyMap", () => {
  beforeEach(() => {
    mockExecute.mockReset();
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
});
