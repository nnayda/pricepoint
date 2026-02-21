import { describe, it, expect, vi } from "vitest";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { axe } from "vitest-axe";
import NavBar from "../../components/NavBar/NavBar";
import SearchBar from "../../components/SearchBar/SearchBar";
import AppLayout from "../../components/Layout/AppLayout";
import LandingPage from "../../pages/LandingPage";

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
});
