import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import PoisTab from "../PoisTab";
import { mockDashboardData } from "../../../../data/mockDashboardData";
import type { DashboardData, DashboardPoi } from "../../../../types";

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

function makeData(pois: DashboardPoi[]): DashboardData {
  return { ...mockDashboardData, pois };
}

function renderWithRouter(ui: React.ReactElement) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

describe("PoisTab", () => {
  it("renders saved place cards when saved POIs exist", () => {
    renderWithRouter(<PoisTab data={makeData([savedPoi])} />);
    expect(screen.getByText("Saved Places")).toBeInTheDocument();
    expect(screen.getByText("Costco")).toBeInTheDocument();
    expect(screen.getByText("123 Main St")).toBeInTheDocument();
  });

  it("shows empty state when no saved POIs", () => {
    renderWithRouter(<PoisTab data={makeData([])} />);
    expect(screen.queryByText("Saved Places")).not.toBeInTheDocument();
    expect(screen.getByText("No saved places yet")).toBeInTheDocument();
    expect(screen.getByText("Settings")).toHaveAttribute("href", "/settings");
  });

  it("clicking a saved card toggles selection", () => {
    renderWithRouter(<PoisTab data={makeData([savedPoi])} />);
    const card = screen.getByText("Costco").closest("[class*=cursor-pointer]")!;
    fireEvent.click(card);
    // Check it has accent muted background (selected)
    expect(card.style.backgroundColor).toContain("accent-muted");
    // Click again to deselect
    fireEvent.click(card);
    expect(card.style.backgroundColor).toContain("surface-alt");
  });

  it("renders map with correct marker count", () => {
    renderWithRouter(<PoisTab data={makeData([savedPoi])} />);
    const map = screen.getByTestId("dashboard-map");
    // 1 property + 1 saved = 2
    expect(map.getAttribute("data-marker-count")).toBe("2");
  });

  it("saved POI card shows distance and drive time", () => {
    renderWithRouter(<PoisTab data={makeData([savedPoi])} />);
    expect(screen.getByText("2.5 mi")).toBeInTheDocument();
    expect(screen.getByText("7 min")).toBeInTheDocument();
  });

  it("renders map with only property marker when no POIs", () => {
    renderWithRouter(<PoisTab data={makeData([])} />);
    const map = screen.getByTestId("dashboard-map");
    // 1 property only
    expect(map.getAttribute("data-marker-count")).toBe("1");
  });
});
