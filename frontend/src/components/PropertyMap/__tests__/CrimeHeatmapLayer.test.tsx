import { describe, it, expect, vi, beforeEach } from "vitest";
import { render } from "@testing-library/react";
import CrimeHeatmapLayer from "../layers/CrimeHeatmapLayer";
import type { CrimeHeatmapPoint } from "../../../types";

const mockAddTo = vi.fn();
const mockRemoveLayer = vi.fn();
const mockHeatLayer = vi.fn(() => ({ addTo: mockAddTo }));
const mockMap = { removeLayer: mockRemoveLayer };

vi.mock("react-leaflet", () => ({
  useMap: () => mockMap,
}));

vi.mock("leaflet", () => ({
  default: { heatLayer: (...args: unknown[]) => mockHeatLayer(...args) },
}));

vi.mock("leaflet.heat", () => ({}));

const mockData: CrimeHeatmapPoint[] = [
  { lat: 35.78, lon: -78.64, intensity: 0.8 },
  { lat: 35.79, lon: -78.65, intensity: 0.4 },
];

describe("CrimeHeatmapLayer", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("creates a heat layer with the data points", () => {
    render(<CrimeHeatmapLayer data={mockData} />);
    expect(mockHeatLayer).toHaveBeenCalledWith(
      [
        [35.78, -78.64, 0.8],
        [35.79, -78.65, 0.4],
      ],
      expect.objectContaining({ radius: 25, blur: 15, maxZoom: 17 }),
    );
  });

  it("adds the heat layer to the map", () => {
    render(<CrimeHeatmapLayer data={mockData} />);
    expect(mockAddTo).toHaveBeenCalledWith(mockMap);
  });

  it("removes the heat layer on unmount", () => {
    const { unmount } = render(<CrimeHeatmapLayer data={mockData} />);
    unmount();
    expect(mockRemoveLayer).toHaveBeenCalled();
  });

  it("does not create a heat layer when data is empty", () => {
    render(<CrimeHeatmapLayer data={[]} />);
    expect(mockHeatLayer).not.toHaveBeenCalled();
  });

  it("renders null (no DOM output)", () => {
    const { container } = render(<CrimeHeatmapLayer data={mockData} />);
    expect(container.innerHTML).toBe("");
  });
});
