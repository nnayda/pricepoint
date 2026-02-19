import { describe, it, expect, vi } from "vitest";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { axe } from "vitest-axe";
import NavBar from "../../components/NavBar/NavBar";
import PropertyCard from "../../components/PropertyCard/PropertyCard";
import SearchBar from "../../components/SearchBar/SearchBar";
import AppLayout from "../../components/Layout/AppLayout";
import LandingPage from "../../pages/LandingPage";
import ForecastPage from "../../pages/ForecastPage";

vi.mock("../../hooks/useGeocode", () => ({
  useGeocode: () => ({ results: [], loading: false, error: null }),
}));

vi.mock("../../contexts/AuthContext", () => ({
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

vi.mock("../../hooks/useApi", () => ({
  useApi: () => ({ data: null, loading: false, error: null, execute: vi.fn() }),
}));

function renderWithRouter(ui: React.ReactElement) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

describe("Accessibility (axe)", () => {
  it("NavBar has no a11y violations", async () => {
    const { container } = renderWithRouter(<NavBar />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it("PropertyCard has no a11y violations", async () => {
    const forecast = {
      address: "123 Main St, Philadelphia, PA",
      predicted_value: 350000,
      confidence_interval_low: 320000,
      confidence_interval_high: 380000,
      model_version: "v1.2.0",
    };
    const { container } = render(<PropertyCard forecast={forecast} />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it("SearchBar has no a11y violations", async () => {
    const { container } = render(<SearchBar onSelect={vi.fn()} />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it("AppLayout has no a11y violations", async () => {
    const { container } = renderWithRouter(
      <AppLayout>
        <p>Test content</p>
      </AppLayout>,
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it("LandingPage has no a11y violations", async () => {
    const { container } = renderWithRouter(<LandingPage />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it("ForecastPage has no a11y violations", async () => {
    const { container } = renderWithRouter(<ForecastPage />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
