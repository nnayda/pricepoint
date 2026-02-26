import { describe, it, expect, vi } from "vitest";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import DashboardLayout from "../DashboardLayout";
import { mockDashboardData } from "../../../data/mockDashboardData";

// Mock child components to keep tests focused on layout
vi.mock("../DashboardNav", () => ({
  default: () => <nav data-testid="dashboard-nav" />,
}));
vi.mock("../DashboardBreadcrumb", () => ({
  default: () => <div data-testid="dashboard-breadcrumb" />,
}));
vi.mock("../DashboardTabs", () => ({
  default: () => <div data-testid="dashboard-tabs" />,
}));
vi.mock("../left/PhotoCarousel", () => ({
  default: () => <div data-testid="photo-carousel" />,
}));
vi.mock("../left/KeyFactsCard", () => ({
  default: () => <div data-testid="key-facts-card" />,
}));
vi.mock("../left/DescriptionCard", () => ({
  default: () => <div data-testid="description-card" />,
}));

describe("DashboardLayout", () => {
  it("renders all layout sections", () => {
    const { getByTestId } = render(
      <MemoryRouter>
        <DashboardLayout data={mockDashboardData} />
      </MemoryRouter>,
    );
    expect(getByTestId("dashboard-nav")).toBeInTheDocument();
    expect(getByTestId("dashboard-breadcrumb")).toBeInTheDocument();
    expect(getByTestId("dashboard-tabs")).toBeInTheDocument();
    expect(getByTestId("photo-carousel")).toBeInTheDocument();
    expect(getByTestId("key-facts-card")).toBeInTheDocument();
    expect(getByTestId("description-card")).toBeInTheDocument();
  });

  it("applies isolate class to main content area to contain stacking contexts", () => {
    const { getByTestId } = render(
      <MemoryRouter>
        <DashboardLayout data={mockDashboardData} />
      </MemoryRouter>,
    );
    const main = getByTestId("dashboard-tabs").closest("main");
    expect(main).toHaveClass("isolate");
  });
});
