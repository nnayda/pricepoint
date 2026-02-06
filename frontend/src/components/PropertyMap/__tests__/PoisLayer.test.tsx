import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import PoisLayer from "../layers/PoisLayer";
import type { PointOfInterest } from "../../../types";

vi.mock("react-leaflet", () => ({
  Marker: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="marker">{children}</div>
  ),
  Popup: ({ children }: { children: React.ReactNode }) => <div data-testid="popup">{children}</div>,
}));

const mockPois: PointOfInterest[] = [
  {
    id: "poi-1",
    name: "Trader Joe's",
    category: "Grocery",
    lat: 35.78,
    lon: -78.64,
    distance_miles: 1.2,
    drive_minutes: 5,
  },
  {
    id: "poi-2",
    name: "CVS Pharmacy",
    category: "Pharmacy",
    lat: 35.79,
    lon: -78.65,
    distance_miles: 0.8,
    drive_minutes: 3,
  },
];

describe("PoisLayer", () => {
  it("renders a marker for each POI", () => {
    render(<PoisLayer data={mockPois} />);
    const markers = screen.getAllByTestId("marker");
    expect(markers).toHaveLength(2);
  });

  it("renders POI name in popup", () => {
    render(<PoisLayer data={mockPois} />);
    expect(screen.getByText("Trader Joe's")).toBeInTheDocument();
    expect(screen.getByText("CVS Pharmacy")).toBeInTheDocument();
  });

  it("renders POI category in popup", () => {
    render(<PoisLayer data={mockPois} />);
    expect(screen.getByText("Grocery")).toBeInTheDocument();
    expect(screen.getByText("Pharmacy")).toBeInTheDocument();
  });

  it("renders distance and drive time", () => {
    render(<PoisLayer data={mockPois} />);
    expect(screen.getByText(/1\.2 mi/)).toBeInTheDocument();
    expect(screen.getByText(/5 min drive/)).toBeInTheDocument();
  });

  it("returns null when data is empty", () => {
    const { container } = render(<PoisLayer data={[]} />);
    expect(container.innerHTML).toBe("");
  });
});
