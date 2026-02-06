import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { axe } from "vitest-axe";
import LandingPage from "../LandingPage";

vi.mock("../../components/SearchBar/SearchBar", () => ({
  default: ({
    onSelect,
    placeholder,
  }: {
    onSelect: (r: unknown) => void;
    placeholder?: string;
  }) => (
    <input
      data-testid="search-bar"
      placeholder={placeholder}
      onChange={() =>
        onSelect({ display_name: "123 Main St", lat: 39.95, lon: -75.16, place_id: 1 })
      }
    />
  ),
}));

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return { ...actual, useNavigate: () => mockNavigate };
});

function renderLandingPage() {
  return render(
    <MemoryRouter>
      <LandingPage />
    </MemoryRouter>,
  );
}

describe("LandingPage", () => {
  it("renders the PricePoint brand name", () => {
    renderLandingPage();
    expect(screen.getByText("PricePoint")).toBeInTheDocument();
  });

  it("styles the brand name with brand-blue", () => {
    renderLandingPage();
    const brand = screen.getByText("PricePoint");
    expect(brand.className).toContain("text-brand-blue");
  });

  it("renders the headline", () => {
    renderLandingPage();
    expect(
      screen.getByRole("heading", { name: /know your home's future value/i }),
    ).toBeInTheDocument();
  });

  it("renders the subtitle", () => {
    renderLandingPage();
    expect(screen.getByText(/ml-powered forecasts/i)).toBeInTheDocument();
  });

  it("renders the search bar with custom placeholder", () => {
    renderLandingPage();
    expect(screen.getByPlaceholderText("Enter a property address...")).toBeInTheDocument();
  });

  it("renders three stat cards", () => {
    renderLandingPage();
    expect(screen.getByText("50K+")).toBeInTheDocument();
    expect(screen.getByText("94%")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
  });

  it("renders stat card labels", () => {
    renderLandingPage();
    expect(screen.getByText("Properties analyzed")).toBeInTheDocument();
    expect(screen.getByText("Prediction accuracy")).toBeInTheDocument();
    expect(screen.getByText("Data sources")).toBeInTheDocument();
  });

  it("navigates to forecast page on address selection", async () => {
    const { default: userEvent } = await import("@testing-library/user-event");
    const user = userEvent.setup();
    renderLandingPage();
    const searchBar = screen.getByTestId("search-bar");
    await user.type(searchBar, "a");
    expect(mockNavigate).toHaveBeenCalledWith(
      `/forecast?address=${encodeURIComponent("123 Main St")}`,
    );
  });

  it("applies design system styles to stat cards", () => {
    renderLandingPage();
    const statCard = screen.getByText("50K+").closest("div");
    expect(statCard?.className).toContain("rounded-md");
    expect(statCard?.className).toContain("bg-bg-card");
    expect(statCard?.className).toContain("shadow-soft");
  });

  it("centers content vertically", () => {
    renderLandingPage();
    const container = screen
      .getByRole("heading", { name: /know your home/i })
      .closest("div.flex.flex-1");
    expect(container?.className).toContain("justify-center");
    expect(container?.className).toContain("items-center");
  });

  it("has no axe accessibility violations", async () => {
    const { container } = renderLandingPage();
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
