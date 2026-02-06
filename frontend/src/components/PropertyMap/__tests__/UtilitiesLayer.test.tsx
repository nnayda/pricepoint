import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import UtilitiesLayer from "../layers/UtilitiesLayer";
import type { UtilityFeature } from "../../../types";

vi.mock("react-leaflet", () => ({
  Marker: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="marker">{children}</div>
  ),
  Popup: ({ children }: { children: React.ReactNode }) => <div data-testid="popup">{children}</div>,
}));

const mockFeatures: UtilityFeature[] = [
  {
    id: "ut-1",
    name: "I-440",
    feature_type: "Highway",
    lat: 35.78,
    lon: -78.64,
    distance_miles: 0.3,
  },
  {
    id: "ut-2",
    name: "CSX Main Line",
    feature_type: "Railroad",
    lat: 35.79,
    lon: -78.65,
    distance_miles: 1.5,
  },
];

describe("UtilitiesLayer", () => {
  it("renders a marker for each feature", () => {
    render(<UtilitiesLayer data={mockFeatures} />);
    const markers = screen.getAllByTestId("marker");
    expect(markers).toHaveLength(2);
  });

  it("renders feature name in popup", () => {
    render(<UtilitiesLayer data={mockFeatures} />);
    expect(screen.getByText("I-440")).toBeInTheDocument();
    expect(screen.getByText("CSX Main Line")).toBeInTheDocument();
  });

  it("renders feature type in popup", () => {
    render(<UtilitiesLayer data={mockFeatures} />);
    expect(screen.getByText("Highway")).toBeInTheDocument();
    expect(screen.getByText("Railroad")).toBeInTheDocument();
  });

  it("renders distance", () => {
    render(<UtilitiesLayer data={mockFeatures} />);
    expect(screen.getByText("0.3 mi")).toBeInTheDocument();
    expect(screen.getByText("1.5 mi")).toBeInTheDocument();
  });

  it("returns null when data is empty", () => {
    const { container } = render(<UtilitiesLayer data={[]} />);
    expect(container.innerHTML).toBe("");
  });
});
