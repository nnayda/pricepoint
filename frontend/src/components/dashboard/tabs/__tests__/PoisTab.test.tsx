import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import PoisTab from "../PoisTab";
import { mockDashboardData } from "../../../../data/mockDashboardData";
import type { DashboardData, DashboardPoi } from "../../../../types";

vi.mock("react-map-gl/maplibre", () => ({
  Source: ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="vector-source">{children}</div>
  ),
  Layer: ({ id }: { id?: string }) => <div data-testid="vector-layer" data-layer-id={id} />,
  Popup: ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="map-popup">{children}</div>
  ),
}));

vi.mock("../../maps/DashboardMap", () => ({
  default: ({
    children,
    markers,
  }: {
    children?: React.ReactNode;
    markers: unknown[];
    [key: string]: unknown;
  }) => (
    <div data-testid="dashboard-map" data-marker-count={markers?.length ?? 0}>
      {children}
    </div>
  ),
}));

const savedPoi: DashboardPoi = {
  id: "SAVED-1",
  name: "Costco",
  category: "Groceries",
  subcategory: "store",
  lat: 35.8,
  lon: -78.7,
  distance_miles: 2.5,
  drive_minutes: 7,
  icon: "star",
  isSaved: true,
  marker_color: "#10B981",
  address: "123 Main St",
};

const regularPoi: DashboardPoi = {
  id: "MEDICAL-1",
  name: "Rex Hospital",
  category: "medical",
  subcategory: "hospital",
  lat: 35.81,
  lon: -78.71,
  distance_miles: 1.2,
  drive_minutes: 4,
  icon: "hospital",
};

function makeData(pois: DashboardPoi[]): DashboardData {
  return { ...mockDashboardData, pois };
}

describe("PoisTab", () => {
  it("renders saved place cards when saved POIs exist", () => {
    render(<PoisTab data={makeData([savedPoi, regularPoi])} />);
    expect(screen.getByText("Saved Places")).toBeInTheDocument();
    expect(screen.getByText("Costco")).toBeInTheDocument();
    expect(screen.getByText("123 Main St")).toBeInTheDocument();
  });

  it("renders regular POI accordion", () => {
    render(<PoisTab data={makeData([regularPoi])} />);
    expect(screen.getByText("medical")).toBeInTheDocument();
    expect(screen.getByText("Rex Hospital")).toBeInTheDocument();
  });

  it("does not render saved places section when no saved POIs", () => {
    render(<PoisTab data={makeData([regularPoi])} />);
    expect(screen.queryByText("Saved Places")).not.toBeInTheDocument();
  });

  it("clicking a saved card toggles selection", () => {
    render(<PoisTab data={makeData([savedPoi])} />);
    const card = screen.getByText("Costco").closest("[class*=cursor-pointer]")!;
    fireEvent.click(card);
    // Check it has accent muted background (selected)
    expect(card.style.backgroundColor).toContain("accent-muted");
    // Click again to deselect
    fireEvent.click(card);
    expect(card.style.backgroundColor).toContain("surface-alt");
  });

  it("renders map with correct marker count", () => {
    render(<PoisTab data={makeData([savedPoi, regularPoi])} />);
    const map = screen.getByTestId("dashboard-map");
    // 1 property + 1 saved + 1 regular = 3
    expect(map.getAttribute("data-marker-count")).toBe("3");
  });

  it("accordion collapse/expand works", () => {
    render(<PoisTab data={makeData([regularPoi])} />);
    // Category header button
    const catButton = screen.getByText("medical").closest("button")!;
    expect(screen.getByText("Rex Hospital")).toBeInTheDocument();
    fireEvent.click(catButton);
    expect(screen.queryByText("Rex Hospital")).not.toBeInTheDocument();
    fireEvent.click(catButton);
    expect(screen.getByText("Rex Hospital")).toBeInTheDocument();
  });

  it("saved POI card shows distance and drive time", () => {
    render(<PoisTab data={makeData([savedPoi])} />);
    expect(screen.getByText("2.5 mi")).toBeInTheDocument();
    expect(screen.getByText("7 min")).toBeInTheDocument();
  });
});
