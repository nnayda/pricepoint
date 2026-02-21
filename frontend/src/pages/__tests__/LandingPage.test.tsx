import { describe, it, expect, vi, beforeAll } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { axe } from "vitest-axe";
import LandingPage from "../LandingPage";

beforeAll(() => {
  // jsdom doesn't have IntersectionObserver
  const mockObserver = vi.fn(() => ({
    observe: vi.fn(),
    unobserve: vi.fn(),
    disconnect: vi.fn(),
  }));
  vi.stubGlobal("IntersectionObserver", mockObserver);
});

vi.mock("../../components/SearchBar/SearchBar", () => ({
  default: ({
    onSelect,
    placeholder,
  }: {
    onSelect: (r: unknown) => void;
    placeholder?: string;
    variant?: string;
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
  // -- Navigation --
  it("renders the PricePoint brand in the nav bar", () => {
    renderLandingPage();
    const brands = screen.getAllByText("PricePoint");
    expect(brands.length).toBeGreaterThanOrEqual(1);
  });

  it("renders Sign In and Get Started links", () => {
    renderLandingPage();
    expect(screen.getByText("Sign In")).toBeInTheDocument();
    expect(screen.getByText("Get Started")).toBeInTheDocument();
  });

  // -- Hero --
  it("renders the hero headline", () => {
    renderLandingPage();
    expect(screen.getByText(/really worth/i)).toBeInTheDocument();
  });

  it("renders the hero subtitle with value proposition", () => {
    renderLandingPage();
    expect(screen.getByText(/combines listing data, crime statistics/i)).toBeInTheDocument();
  });

  it("renders the search bar with landing placeholder", () => {
    renderLandingPage();
    expect(screen.getByPlaceholderText("Search any address...")).toBeInTheDocument();
  });

  it("renders the social proof line", () => {
    renderLandingPage();
    expect(screen.getByText(/48 states/i)).toBeInTheDocument();
    expect(screen.getByText(/2M\+ listings indexed/i)).toBeInTheDocument();
  });

  it("navigates to property dashboard on address selection", async () => {
    const { default: userEvent } = await import("@testing-library/user-event");
    const user = userEvent.setup();
    renderLandingPage();
    const searchBar = screen.getByTestId("search-bar");
    await user.type(searchBar, "a");
    expect(mockNavigate).toHaveBeenCalledWith(
      `/property/${encodeURIComponent("123 Main St")}`,
    );
  });

  // -- Feature Showcase --
  it("renders the feature showcase section heading", () => {
    renderLandingPage();
    expect(screen.getByText("What PricePoint Analyzes")).toBeInTheDocument();
  });

  it("renders all four feature cards", () => {
    renderLandingPage();
    expect(screen.getByText("AI Valuation Model")).toBeInTheDocument();
    expect(screen.getByText("Crime & Safety")).toBeInTheDocument();
    expect(screen.getByText("Schools & Demographics")).toBeInTheDocument();
    expect(screen.getByText("Neighborhood Quality")).toBeInTheDocument();
  });

  // -- Dashboard Preview --
  it("renders the dashboard preview section", () => {
    renderLandingPage();
    expect(screen.getByText("Deep analysis at your fingertips")).toBeInTheDocument();
  });

  it("renders dashboard mockup annotations", () => {
    renderLandingPage();
    expect(screen.getByText("AI-predicted value")).toBeInTheDocument();
    expect(screen.getByText("What drives the estimate")).toBeInTheDocument();
    expect(screen.getByText("Six risk categories")).toBeInTheDocument();
    expect(screen.getByText("Real-time mortgage modeling")).toBeInTheDocument();
  });

  // -- Data Sources --
  it("renders the data sources section", () => {
    renderLandingPage();
    expect(screen.getByText("Built on primary sources, not black boxes")).toBeInTheDocument();
  });

  it("renders data source badges", () => {
    renderLandingPage();
    expect(screen.getByText("Redfin")).toBeInTheDocument();
    expect(screen.getByText("U.S. Census (ACS)")).toBeInTheDocument();
    expect(screen.getByText("FRED")).toBeInTheDocument();
    expect(screen.getByText("USGS / FEMA")).toBeInTheDocument();
  });

  // -- How It Works --
  it("renders the how it works section", () => {
    renderLandingPage();
    expect(screen.getByText("Three steps to clarity")).toBeInTheDocument();
  });

  it("renders the three steps", () => {
    renderLandingPage();
    expect(screen.getByText("Search a property")).toBeInTheDocument();
    expect(screen.getByText("We analyze the data")).toBeInTheDocument();
    expect(screen.getByText("Make a confident decision")).toBeInTheDocument();
  });

  // -- Sign-Up CTA --
  it("renders the sign-up CTA section", () => {
    renderLandingPage();
    expect(screen.getByText("Start your analysis free")).toBeInTheDocument();
  });

  it("renders the email input", () => {
    renderLandingPage();
    expect(screen.getByPlaceholderText("Enter your email")).toBeInTheDocument();
  });

  it("renders the Get Early Access button", () => {
    renderLandingPage();
    expect(screen.getByText("Get Early Access")).toBeInTheDocument();
  });

  // -- Footer --
  it("renders the footer with copyright", () => {
    renderLandingPage();
    const year = new Date().getFullYear().toString();
    expect(screen.getByText(new RegExp(year))).toBeInTheDocument();
  });

  it("renders footer links", () => {
    renderLandingPage();
    expect(screen.getByText("About")).toBeInTheDocument();
    expect(screen.getByText("Privacy Policy")).toBeInTheDocument();
    expect(screen.getByText("Terms of Service")).toBeInTheDocument();
    expect(screen.getByText("Contact")).toBeInTheDocument();
  });

  // -- Dark theme --
  it("uses the dark dashboard background", () => {
    const { container } = renderLandingPage();
    const root = container.firstElementChild;
    expect(root?.className).toContain("min-h-screen");
    expect(root?.className).toContain("bg-[var(--color-db-bg)]");
  });

  // -- Accessibility --
  it("has no axe accessibility violations", async () => {
    const { container } = renderLandingPage();
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
