import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";

// Mock react-leaflet — jsdom lacks canvas APIs needed by Leaflet
vi.mock("react-leaflet", () => ({
  MapContainer: ({ children, ...props }: { children: React.ReactNode; style?: React.CSSProperties }) => (
    <div data-testid="map-container" style={props.style}>
      {children}
    </div>
  ),
  TileLayer: () => <div data-testid="tile-layer" />,
  Marker: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="marker">{children}</div>
  ),
  Popup: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="popup">{children}</div>
  ),
}));

import MapView from "../MapView";

describe("MapView", () => {
  it("renders the map container", () => {
    render(<MapView />);
    expect(screen.getByTestId("map-container")).toBeInTheDocument();
  });

  it("renders a marker", () => {
    render(<MapView />);
    expect(screen.getByTestId("marker")).toBeInTheDocument();
  });

  it("renders popup with forecast text", () => {
    render(<MapView />);
    expect(screen.getByText("Home Value Forecast")).toBeInTheDocument();
  });
});
