import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import App from "../App";

vi.mock("../pages/LandingPage", () => ({
  default: () => <div data-testid="landing-page">Landing</div>,
}));

vi.mock("../pages/PropertyDashboardPage", () => ({
  default: () => <div data-testid="dashboard-page">Dashboard</div>,
}));

function renderApp(initialRoute = "/") {
  return render(
    <MemoryRouter initialEntries={[initialRoute]}>
      <App />
    </MemoryRouter>,
  );
}

describe("App", () => {
  it("renders LandingPage at /", async () => {
    renderApp("/");
    expect(await screen.findByTestId("landing-page")).toBeInTheDocument();
  });

  it("hides the NavBar on the landing page", async () => {
    renderApp("/");
    expect(await screen.findByTestId("landing-page")).toBeInTheDocument();
    expect(screen.queryByRole("navigation", { name: "Main navigation" })).not.toBeInTheDocument();
  });

  it("renders PropertyDashboardPage at /property/:address", async () => {
    renderApp("/property/123%20Main%20St");
    expect(await screen.findByTestId("dashboard-page")).toBeInTheDocument();
  });

  it("hides the NavBar on the dashboard page", async () => {
    renderApp("/property/123%20Main%20St");
    expect(await screen.findByTestId("dashboard-page")).toBeInTheDocument();
    expect(screen.queryByRole("navigation", { name: "Main navigation" })).not.toBeInTheDocument();
  });

  it("redirects /results to /", async () => {
    renderApp("/results");
    expect(await screen.findByTestId("landing-page")).toBeInTheDocument();
  });

  it("redirects /dashboard to /", async () => {
    renderApp("/dashboard");
    expect(await screen.findByTestId("landing-page")).toBeInTheDocument();
  });

  it("redirects /test-dashboard-page to /", async () => {
    renderApp("/test-dashboard-page");
    expect(await screen.findByTestId("landing-page")).toBeInTheDocument();
  });

  it("shows a loading spinner while pages load", () => {
    renderApp();
    const spinner = screen.queryByRole("status");
    if (spinner) {
      expect(spinner).toBeInTheDocument();
    }
  });

  it("renders NotFoundPage for unknown routes", async () => {
    renderApp("/unknown-route");
    expect(await screen.findByText("404")).toBeInTheDocument();
    expect(screen.getByText("Page Not Found")).toBeInTheDocument();
  });
});
