import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import PropertyDashboardPage from "../PropertyDashboardPage";
import { mockDashboardData } from "../../data/mockDashboardData";

// Mock hooks
const mockUsePropertyLookup = vi.fn();
vi.mock("../../hooks/usePropertyLookup", () => ({
  usePropertyLookup: (...args: unknown[]) => mockUsePropertyLookup(...args),
}));

vi.mock("../../hooks/useDemographics", () => ({
  useDemographics: () => ({ data: null, loading: false, error: null }),
}));

vi.mock("../../hooks/useNeighborhoodValuation", () => ({
  useNeighborhoodValuation: () => ({ data: null, loading: false, error: null }),
  useNeighborhoodValuationHistory: () => ({ data: null, loading: false, error: null }),
}));

// Mock mapPropertyResponse to return mockDashboardData
vi.mock("../../utils/mapPropertyResponse", () => ({
  mapPropertyResponse: () => mockDashboardData,
}));

// Mock heavy child components
vi.mock("../../components/dashboard/DashboardLayout", () => ({
  default: ({
    data,
    banner,
  }: {
    data: { property: { address: string } };
    banner?: React.ReactNode;
  }) => (
    <div data-testid="dashboard-layout" data-address={data.property.address}>
      {banner}
    </div>
  ),
}));

vi.mock("../../components/DataRequestBanner", () => ({
  default: ({ address, onDismiss }: { address: string; onDismiss: () => void }) => (
    <div data-testid="data-request-banner" data-address={address}>
      <button onClick={onDismiss}>Dismiss</button>
    </div>
  ),
}));

function renderPage(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/property/:address" element={<PropertyDashboardPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("PropertyDashboardPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading spinner while data is loading", () => {
    mockUsePropertyLookup.mockReturnValue({
      data: null,
      loading: true,
      notFound: false,
      error: null,
    });

    renderPage("/property/123%20Main%20St?lat=35.5&lon=-78.7");
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("shows error state when lat/lon missing", () => {
    mockUsePropertyLookup.mockReturnValue({
      data: null,
      loading: false,
      notFound: false,
      error: null,
    });

    renderPage("/property/123%20Main%20St");
    expect(
      screen.getByText("Invalid property URL — missing location parameters."),
    ).toBeInTheDocument();
  });

  it("shows error state when hook returns error", () => {
    mockUsePropertyLookup.mockReturnValue({
      data: null,
      loading: false,
      notFound: false,
      error: "Failed to load property data",
    });

    renderPage("/property/123%20Main%20St?lat=35.5&lon=-78.7");
    expect(screen.getByText("Failed to load property data")).toBeInTheDocument();
  });

  it("renders dashboard without banner when property is found", () => {
    mockUsePropertyLookup.mockReturnValue({
      data: { property: { address: "123 Main St" } },
      loading: false,
      notFound: false,
      error: null,
    });

    renderPage("/property/123%20Main%20St?lat=35.5&lon=-78.7");
    expect(screen.getByTestId("dashboard-layout")).toBeInTheDocument();
    expect(screen.queryByTestId("data-request-banner")).not.toBeInTheDocument();
  });

  it("renders dashboard WITH banner when property is not found", () => {
    mockUsePropertyLookup.mockReturnValue({
      data: null,
      loading: false,
      notFound: true,
      error: null,
    });

    renderPage("/property/123%20Main%20St?lat=35.5&lon=-78.7");

    // Dashboard should still render (not blocked)
    expect(screen.getByTestId("dashboard-layout")).toBeInTheDocument();

    // Banner should be present
    expect(screen.getByTestId("data-request-banner")).toBeInTheDocument();
  });

  it("uses the decoded address in the empty dashboard data when not found", () => {
    mockUsePropertyLookup.mockReturnValue({
      data: null,
      loading: false,
      notFound: true,
      error: null,
    });

    renderPage("/property/123%20Main%20St?lat=35.5&lon=-78.7");
    expect(screen.getByTestId("dashboard-layout")).toHaveAttribute("data-address", "123 Main St");
  });

  it("passes address to DataRequestBanner", () => {
    mockUsePropertyLookup.mockReturnValue({
      data: null,
      loading: false,
      notFound: true,
      error: null,
    });

    renderPage("/property/123%20Main%20St?lat=35.5&lon=-78.7");
    expect(screen.getByTestId("data-request-banner")).toHaveAttribute(
      "data-address",
      "123 Main St",
    );
  });

  it("hides banner after dismiss without removing dashboard", () => {
    mockUsePropertyLookup.mockReturnValue({
      data: null,
      loading: false,
      notFound: true,
      error: null,
    });

    renderPage("/property/123%20Main%20St?lat=35.5&lon=-78.7");

    expect(screen.getByTestId("data-request-banner")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Dismiss"));

    // Banner should be gone, dashboard still present
    expect(screen.queryByTestId("data-request-banner")).not.toBeInTheDocument();
    expect(screen.getByTestId("dashboard-layout")).toBeInTheDocument();
  });
});
