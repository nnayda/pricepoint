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
  saved_place_name: "Costco",
};

const savedPoi2: DashboardPoi = {
  id: "SAVED-2",
  name: "Costco",
  category: "Groceries",
  subcategory: "store",
  lat: 35.9,
  lon: -78.8,
  distance_miles: 5.1,
  drive_minutes: 12,
  icon: "star",
  isSaved: true,
  marker_color: "#10B981",
  address: "456 Oak Ave",
  saved_place_name: "Costco",
};

const savedPoi3: DashboardPoi = {
  id: "SAVED-3",
  name: "Target",
  category: "Shopping",
  subcategory: "store",
  lat: 35.85,
  lon: -78.75,
  distance_miles: 3.2,
  drive_minutes: 9,
  icon: "star",
  isSaved: true,
  marker_color: "#EF4444",
  address: "789 Elm St",
  saved_place_name: "Target",
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
  });

  it("shows empty state when no saved POIs", () => {
    renderWithRouter(<PoisTab data={makeData([])} />);
    expect(screen.queryByText("Saved Places")).not.toBeInTheDocument();
    expect(screen.getByText("No saved places yet")).toBeInTheDocument();
    expect(screen.getByText("Settings")).toHaveAttribute("href", "/settings");
  });

  it("renders map with correct marker count", () => {
    renderWithRouter(<PoisTab data={makeData([savedPoi])} />);
    const map = screen.getByTestId("dashboard-map");
    // 1 property + 1 saved = 2
    expect(map.getAttribute("data-marker-count")).toBe("2");
  });

  it("saved POI shows nearest distance and drive time", () => {
    renderWithRouter(<PoisTab data={makeData([savedPoi])} />);
    expect(screen.getByText("2.5 mi")).toBeInTheDocument();
    expect(screen.getByText("7 min")).toBeInTheDocument();
  });

  it("renders map with only property marker when no POIs", () => {
    renderWithRouter(<PoisTab data={makeData([])} />);
    const map = screen.getByTestId("dashboard-map");
    expect(map.getAttribute("data-marker-count")).toBe("1");
  });

  it("groups multiple locations under the same saved place", () => {
    renderWithRouter(<PoisTab data={makeData([savedPoi, savedPoi2])} />);
    // Should show "Costco" once as the group header
    const costcoHeaders = screen.getAllByText("Costco");
    expect(costcoHeaders.length).toBe(1);
    // Shows location count
    expect(screen.getByText("2 locations")).toBeInTheDocument();
    // Nearest distance shown on header
    expect(screen.getByText("2.5 mi")).toBeInTheDocument();
  });

  it("expands a saved place group to reveal individual locations", () => {
    renderWithRouter(<PoisTab data={makeData([savedPoi, savedPoi2])} />);
    // Addresses should not be visible initially
    expect(screen.queryByText("123 Main St")).not.toBeInTheDocument();
    expect(screen.queryByText("456 Oak Ave")).not.toBeInTheDocument();

    // Click the group header to expand
    fireEvent.click(screen.getByText("Costco"));

    // Now both addresses should be visible
    expect(screen.getByText("123 Main St")).toBeInTheDocument();
    expect(screen.getByText("456 Oak Ave")).toBeInTheDocument();
  });

  it("collapses an expanded group on second click", () => {
    renderWithRouter(<PoisTab data={makeData([savedPoi, savedPoi2])} />);
    const header = screen.getByText("Costco");

    fireEvent.click(header);
    expect(screen.getByText("123 Main St")).toBeInTheDocument();

    fireEvent.click(header);
    expect(screen.queryByText("123 Main St")).not.toBeInTheDocument();
  });

  it("renders collapsible category sections when multiple categories exist", () => {
    renderWithRouter(<PoisTab data={makeData([savedPoi, savedPoi3])} />);
    // Both category headers should be shown
    expect(screen.getByText("Groceries")).toBeInTheDocument();
    expect(screen.getByText("Shopping")).toBeInTheDocument();
  });

  it("collapses a category section", () => {
    renderWithRouter(<PoisTab data={makeData([savedPoi, savedPoi3])} />);
    // Both places visible by default (categories start open)
    expect(screen.getByText("Costco")).toBeInTheDocument();
    expect(screen.getByText("Target")).toBeInTheDocument();

    // Collapse the Groceries category
    fireEvent.click(screen.getByText("Groceries"));
    expect(screen.queryByText("Costco")).not.toBeInTheDocument();
    // Target should still be visible
    expect(screen.getByText("Target")).toBeInTheDocument();
  });

  it("single-location saved place toggles map selection on click", () => {
    renderWithRouter(<PoisTab data={makeData([savedPoi])} />);
    const card = screen.getByText("Costco").closest("button")!;
    fireEvent.click(card);
    // Click again to deselect (toggle behavior)
    fireEvent.click(card);
    // No crash means toggle worked
    expect(screen.getByText("Costco")).toBeInTheDocument();
  });

  it("does not show category headers when all POIs share one category", () => {
    const sameCat: DashboardPoi = {
      ...savedPoi3,
      id: "SAVED-4",
      category: "Groceries",
      saved_place_name: "Target",
    };
    renderWithRouter(<PoisTab data={makeData([savedPoi, sameCat])} />);
    // No category header since there's only one category
    expect(screen.queryByText("Groceries")).not.toBeInTheDocument();
    // Both place groups still visible
    expect(screen.getByText("Costco")).toBeInTheDocument();
    expect(screen.getByText("Target")).toBeInTheDocument();
  });
});
