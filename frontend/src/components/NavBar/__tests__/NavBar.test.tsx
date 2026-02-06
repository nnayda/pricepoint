import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import NavBar from "../NavBar";

function renderWithRouter(initialPath = "/") {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <NavBar />
    </MemoryRouter>,
  );
}

describe("NavBar", () => {
  it("renders a navigation element with accessible label", () => {
    renderWithRouter();
    expect(screen.getByRole("navigation", { name: "Main navigation" })).toBeInTheDocument();
  });

  it("renders Home and Forecast links", () => {
    renderWithRouter();
    expect(screen.getByRole("link", { name: "Home" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Forecast" })).toBeInTheDocument();
  });

  it("links point to correct routes", () => {
    renderWithRouter();
    expect(screen.getByRole("link", { name: "Home" })).toHaveAttribute("href", "/");
    expect(screen.getByRole("link", { name: "Forecast" })).toHaveAttribute("href", "/forecast");
  });

  it("marks Home as current page on root path", () => {
    renderWithRouter("/");
    expect(screen.getByRole("link", { name: "Home" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Forecast" })).not.toHaveAttribute("aria-current");
  });

  it("marks Forecast as current page on /forecast path", () => {
    renderWithRouter("/forecast");
    expect(screen.getByRole("link", { name: "Forecast" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Home" })).not.toHaveAttribute("aria-current");
  });

  it("applies active styles to the current page link", () => {
    renderWithRouter("/");
    const homeLink = screen.getByRole("link", { name: "Home" });
    expect(homeLink.className).toContain("bg-brand-blue");
    expect(homeLink.className).toContain("text-white");
  });

  it("applies inactive styles to non-current links", () => {
    renderWithRouter("/");
    const forecastLink = screen.getByRole("link", { name: "Forecast" });
    expect(forecastLink.className).toContain("text-text-sec");
    expect(forecastLink.className).not.toContain("bg-brand-blue");
  });

  it("has pill-shaped border radius on the nav container", () => {
    renderWithRouter();
    const nav = screen.getByRole("navigation");
    expect(nav.className).toContain("rounded-pill");
  });

  it("has glassmorphism backdrop blur", () => {
    renderWithRouter();
    const nav = screen.getByRole("navigation");
    expect(nav.className).toContain("backdrop-blur-md");
  });
});
