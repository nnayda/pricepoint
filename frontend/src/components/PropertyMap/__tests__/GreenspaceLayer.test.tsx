import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import GreenspaceLayer from "../layers/GreenspaceLayer";
import type { GreenspaceFeature } from "../../../types";

vi.mock("react-leaflet", () => ({
  Marker: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="marker">{children}</div>
  ),
  Popup: ({ children }: { children: React.ReactNode }) => <div data-testid="popup">{children}</div>,
}));

const mockFeatures: GreenspaceFeature[] = [
  {
    id: "gs-1",
    name: "Fred Fletcher Park",
    feature_type: "Park",
    lat: 35.78,
    lon: -78.64,
    distance_miles: 0.5,
    acreage: 12.3,
  },
  {
    id: "gs-2",
    name: "Greenway Trail",
    feature_type: "Trail",
    lat: 35.79,
    lon: -78.65,
    distance_miles: 1.1,
  },
];

describe("GreenspaceLayer", () => {
  it("renders a marker for each feature", () => {
    render(<GreenspaceLayer data={mockFeatures} />);
    const markers = screen.getAllByTestId("marker");
    expect(markers).toHaveLength(2);
  });

  it("renders feature name in popup", () => {
    render(<GreenspaceLayer data={mockFeatures} />);
    expect(screen.getByText("Fred Fletcher Park")).toBeInTheDocument();
    expect(screen.getByText("Greenway Trail")).toBeInTheDocument();
  });

  it("renders feature type in popup", () => {
    render(<GreenspaceLayer data={mockFeatures} />);
    expect(screen.getByText("Park")).toBeInTheDocument();
    expect(screen.getByText("Trail")).toBeInTheDocument();
  });

  it("renders distance", () => {
    render(<GreenspaceLayer data={mockFeatures} />);
    expect(screen.getByText("0.5 mi")).toBeInTheDocument();
    expect(screen.getByText("1.1 mi")).toBeInTheDocument();
  });

  it("renders acreage when present", () => {
    render(<GreenspaceLayer data={mockFeatures} />);
    expect(screen.getByText("12.3 acres")).toBeInTheDocument();
  });

  it("does not render acreage when absent", () => {
    render(<GreenspaceLayer data={mockFeatures} />);
    // Greenway Trail has no acreage — its popup should not mention acres
    const popups = screen.getAllByTestId("popup");
    expect(popups[1].textContent).not.toContain("acres");
  });

  it("returns null when data is empty", () => {
    const { container } = render(<GreenspaceLayer data={[]} />);
    expect(container.innerHTML).toBe("");
  });
});
