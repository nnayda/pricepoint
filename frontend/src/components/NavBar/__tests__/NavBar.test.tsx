import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { axe } from "vitest-axe";
import NavBar from "../NavBar";
import type { GeocodeResult } from "../../../types";

let scrollY = 0;
Object.defineProperty(window, "scrollY", { get: () => scrollY, configurable: true });

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

vi.mock("../../../contexts/AuthContext", () => ({
  useAuth: () => ({
    user: null,
    isAuthenticated: false,
    isLoading: false,
    error: null,
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
    refreshAuth: vi.fn(),
  }),
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
    scrollY = 0;
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

  // -- Scroll-based opacity & shadow --

  it("starts with low background opacity at the top of the page", () => {
    scrollY = 0;
    renderNavBar();
    const nav = screen.getByRole("navigation");
    expect(nav.style.backgroundColor).toBe("rgba(255, 255, 255, 0.4)");
  });

  it("increases background opacity on scroll", () => {
    scrollY = 0;
    renderNavBar();
    const nav = screen.getByRole("navigation");

    scrollY = 100;
    act(() => {
      window.dispatchEvent(new Event("scroll"));
    });

    expect(nav.style.backgroundColor).toBe("rgba(255, 255, 255, 0.95)");
  });

  it("starts with no box shadow at the top of the page", () => {
    scrollY = 0;
    renderNavBar();
    const nav = screen.getByRole("navigation");
    expect(nav.style.boxShadow).toBe("0px 10px 30px rgba(0, 0, 0, 0)");
  });

  it("increases box shadow on scroll", () => {
    scrollY = 0;
    renderNavBar();
    const nav = screen.getByRole("navigation");

    scrollY = 100;
    act(() => {
      window.dispatchEvent(new Event("scroll"));
    });

    expect(nav.style.boxShadow).toBe("0px 10px 30px rgba(0, 0, 0, 0.05)");
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

  it("navigates to /property/:address on address selection", async () => {
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
      `/property/${encodeURIComponent("123 Main St, Philadelphia, PA")}`,
    );
  });

  // -- Mobile responsiveness --

  it("uses responsive text size on brand link", () => {
    renderNavBar();
    const link = screen.getByRole("link", { name: "PricePoint" });
    expect(link.className).toContain("text-base");
    expect(link.className).toContain("sm:text-lg");
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
