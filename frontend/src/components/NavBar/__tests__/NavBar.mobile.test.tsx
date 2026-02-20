import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import NavBar from "../NavBar";
import type { GeocodeResult } from "../../../types";

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return { ...actual, useNavigate: () => mockNavigate };
});

vi.mock("../../../hooks/useGeocode", () => ({
  useGeocode: () => ({
    results: [] as GeocodeResult[],
    loading: false,
    error: null as string | null,
  }),
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

function renderNavBar() {
  return render(
    <MemoryRouter>
      <NavBar />
    </MemoryRouter>,
  );
}

describe("NavBar mobile", () => {
  it("renders the hamburger menu button", () => {
    renderNavBar();
    const btn = screen.getByRole("button", { name: "Toggle menu" });
    expect(btn).toBeInTheDocument();
  });

  it("hamburger button has sm:hidden class for mobile-only visibility", () => {
    renderNavBar();
    const btn = screen.getByRole("button", { name: "Toggle menu" });
    expect(btn.className).toContain("sm:hidden");
  });

  it("mobile menu is not visible by default", () => {
    renderNavBar();
    expect(screen.queryByTestId("mobile-menu")).not.toBeInTheDocument();
  });

  it("toggles mobile menu open on hamburger click", async () => {
    const user = userEvent.setup();
    renderNavBar();
    const btn = screen.getByRole("button", { name: "Toggle menu" });

    await user.click(btn);
    expect(screen.getByTestId("mobile-menu")).toBeInTheDocument();
    expect(btn).toHaveAttribute("aria-expanded", "true");
  });

  it("toggles mobile menu closed on second hamburger click", async () => {
    const user = userEvent.setup();
    renderNavBar();
    const btn = screen.getByRole("button", { name: "Toggle menu" });

    await user.click(btn);
    expect(screen.getByTestId("mobile-menu")).toBeInTheDocument();

    await user.click(btn);
    expect(screen.queryByTestId("mobile-menu")).not.toBeInTheDocument();
    expect(btn).toHaveAttribute("aria-expanded", "false");
  });

  it("mobile menu contains Upload Listings and Settings links", async () => {
    const user = userEvent.setup();
    renderNavBar();
    await user.click(screen.getByRole("button", { name: "Toggle menu" }));

    const menu = screen.getByTestId("mobile-menu");
    expect(menu).toHaveTextContent("Upload Listings");
    expect(menu).toHaveTextContent("Settings");
  });

  it("desktop nav links have hidden sm:block classes", () => {
    renderNavBar();
    const uploadLink = screen.getByRole("link", { name: "Upload listings" });
    expect(uploadLink.className).toContain("hidden");
    expect(uploadLink.className).toContain("sm:block");
  });
});
