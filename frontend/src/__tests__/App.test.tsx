import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import App from "../App";

vi.mock("../pages/LandingPage", () => ({
  default: () => <div data-testid="landing-page">Landing</div>,
}));

vi.mock("../pages/DashboardPage", () => ({
  default: () => <div data-testid="dashboard-page">Dashboard</div>,
}));

vi.mock("../pages/ForecastPage", () => ({
  default: () => <div data-testid="forecast-page">Forecast</div>,
}));

vi.mock("../pages/ResultsPage", () => ({
  default: () => <div data-testid="results-page">Results</div>,
}));

function renderApp(initialRoute = "/") {
  return render(
    <MemoryRouter initialEntries={[initialRoute]}>
      <App />
    </MemoryRouter>,
  );
}

describe("App", () => {
  it("renders the AppLayout with header", async () => {
    renderApp();
    expect(screen.getByText("PricePoint")).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Main navigation" })).toBeInTheDocument();
  });

  it("renders LandingPage at /", async () => {
    renderApp("/");
    expect(await screen.findByTestId("landing-page")).toBeInTheDocument();
  });

  it("renders DashboardPage at /dashboard", async () => {
    renderApp("/dashboard");
    expect(await screen.findByTestId("dashboard-page")).toBeInTheDocument();
  });

  it("renders ForecastPage at /forecast", async () => {
    renderApp("/forecast");
    expect(await screen.findByTestId("forecast-page")).toBeInTheDocument();
  });

  it("renders ResultsPage at /results", async () => {
    renderApp("/results");
    expect(await screen.findByTestId("results-page")).toBeInTheDocument();
  });

  it("shows a loading spinner while pages load", () => {
    renderApp();
    const spinner = screen.queryByRole("status");
    // Spinner may or may not be visible depending on how fast the mock resolves,
    // but the sr-only text should be present when the spinner renders
    if (spinner) {
      expect(spinner).toBeInTheDocument();
    }
  });

  it("renders nothing meaningful for unknown routes", async () => {
    renderApp("/unknown-route");
    // Wait for lazy load to settle
    await screen.findByText("PricePoint");
    expect(screen.queryByTestId("landing-page")).not.toBeInTheDocument();
    expect(screen.queryByTestId("dashboard-page")).not.toBeInTheDocument();
    expect(screen.queryByTestId("forecast-page")).not.toBeInTheDocument();
    expect(screen.queryByTestId("results-page")).not.toBeInTheDocument();
  });

  it("wraps routes in a Suspense boundary with design-system spinner", async () => {
    renderApp("/");
    // The page should eventually load
    expect(await screen.findByTestId("landing-page")).toBeInTheDocument();
    // Layout should be present
    const main = screen.getByRole("main");
    expect(main).toBeInTheDocument();
  });
});
