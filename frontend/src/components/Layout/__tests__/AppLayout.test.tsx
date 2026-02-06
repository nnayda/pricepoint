import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import AppLayout from "../AppLayout";
import type { GeocodeResult } from "../../../types";

vi.mock("../../../hooks/useGeocode", () => ({
  useGeocode: () => ({
    results: [] as GeocodeResult[],
    loading: false,
    error: null,
  }),
}));

function renderLayout(children = <p>Page content</p>, initialPath = "/forecast") {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <AppLayout>{children}</AppLayout>
    </MemoryRouter>,
  );
}

describe("AppLayout", () => {
  it("renders the NavBar on non-landing pages", () => {
    renderLayout(<p>content</p>, "/forecast");
    expect(screen.getByRole("navigation", { name: "Main navigation" })).toBeInTheDocument();
  });

  it("renders the NavBar with PricePoint brand link on non-landing pages", () => {
    renderLayout(<p>content</p>, "/forecast");
    expect(screen.getByRole("link", { name: "PricePoint" })).toBeInTheDocument();
  });

  it("hides the NavBar on the landing page", () => {
    renderLayout(<p>content</p>, "/");
    expect(screen.queryByRole("navigation", { name: "Main navigation" })).not.toBeInTheDocument();
  });

  it("hides the header on the landing page", () => {
    renderLayout(<p>content</p>, "/");
    expect(screen.queryByRole("banner")).not.toBeInTheDocument();
  });

  it("renders children inside main", () => {
    renderLayout(<p>Test child</p>);
    const main = screen.getByRole("main");
    expect(main).toHaveTextContent("Test child");
  });

  it("has a sticky header on non-landing pages", () => {
    renderLayout(<p>content</p>, "/forecast");
    const header = screen.getByRole("banner");
    expect(header.className).toContain("sticky");
  });

  it("uses the design-system background color", () => {
    renderLayout(<p>content</p>, "/forecast");
    const wrapper = screen.getByRole("banner").parentElement!;
    expect(wrapper.className).toContain("bg-bg-main");
  });

  it("main area fills remaining vertical space", () => {
    renderLayout();
    const main = screen.getByRole("main");
    expect(main.className).toContain("flex-1");
  });
});
