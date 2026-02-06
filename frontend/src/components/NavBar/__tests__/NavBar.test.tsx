import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { axe } from "vitest-axe";
import NavBar from "../NavBar";
import type { GeocodeResult } from "../../../types";

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return { ...actual, useNavigate: () => mockNavigate };
});

const mockUseGeocode = vi.fn(() => ({
  results: [] as GeocodeResult[],
  loading: false,
  error: null as string | null,
}));

vi.mock("../../../hooks/useGeocode", () => ({
  useGeocode: (...args: unknown[]) => mockUseGeocode(...(args as [])),
}));

function renderNavBar(initialPath = "/") {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <NavBar />
    </MemoryRouter>,
  );
}

describe("NavBar", () => {
  beforeEach(() => {
    mockUseGeocode.mockReturnValue({ results: [], loading: false, error: null });
    mockNavigate.mockReset();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // -- Nav landmark --

  it("renders a nav element with accessible label", () => {
    renderNavBar();
    expect(screen.getByRole("navigation", { name: "Main navigation" })).toBeInTheDocument();
  });

  it("has glassmorphism styles on the nav container", () => {
    renderNavBar();
    const nav = screen.getByRole("navigation");
    expect(nav.className).toContain("rounded-pill");
    expect(nav.className).toContain("backdrop-blur-md");
  });

  // -- Home link --

  it("renders PricePoint home link", () => {
    renderNavBar();
    expect(screen.getByRole("link", { name: "PricePoint" })).toBeInTheDocument();
  });

  it("home link points to /", () => {
    renderNavBar();
    expect(screen.getByRole("link", { name: "PricePoint" })).toHaveAttribute("href", "/");
  });

  // -- Compact SearchBar --

  it("renders a compact SearchBar with combobox role", () => {
    renderNavBar();
    expect(screen.getByRole("combobox", { name: "Search address" })).toBeInTheDocument();
  });

  it("compact SearchBar has the navbar placeholder", () => {
    renderNavBar();
    expect(screen.getByPlaceholderText("Search address...")).toBeInTheDocument();
  });

  // -- Navigation --

  it("navigates to /results with lat/lon on address selection", async () => {
    const mockResults: GeocodeResult[] = [
      {
        display_name: "123 Main St, Philadelphia, PA",
        lat: 39.9526,
        lon: -75.1652,
        place_id: 1001,
        osm_type: "way",
        osm_id: 5001,
        boundingbox: [39.95, 39.96, -75.17, -75.16],
      },
    ];
    mockUseGeocode.mockReturnValue({ results: mockResults, loading: false, error: null });

    const { default: userEvent } = await import("@testing-library/user-event");
    const user = userEvent.setup();
    renderNavBar();

    const input = screen.getByRole("combobox");
    await user.type(input, "123 Main");
    await user.click(screen.getByText("123 Main St, Philadelphia, PA"));

    expect(mockNavigate).toHaveBeenCalledWith(
      `/results?address=${encodeURIComponent("123 Main St, Philadelphia, PA")}&lat=39.9526&lon=-75.1652`,
    );
  });

  // -- Accessibility (axe) --

  describe("accessibility (axe)", () => {
    it("has no a11y violations", async () => {
      const { container } = renderNavBar();
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });
});
