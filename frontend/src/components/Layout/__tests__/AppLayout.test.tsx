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

function renderLayout(children = <p>Page content</p>) {
  return render(
    <MemoryRouter>
      <AppLayout>{children}</AppLayout>
    </MemoryRouter>,
  );
}

describe("AppLayout", () => {
  it("renders the NavBar with PricePoint brand link", () => {
    renderLayout();
    expect(screen.getByRole("link", { name: "PricePoint" })).toBeInTheDocument();
  });

  it("renders the NavBar", () => {
    renderLayout();
    expect(screen.getByRole("navigation", { name: "Main navigation" })).toBeInTheDocument();
  });

  it("renders children inside main", () => {
    renderLayout(<p>Test child</p>);
    const main = screen.getByRole("main");
    expect(main).toHaveTextContent("Test child");
  });

  it("has a sticky header", () => {
    renderLayout();
    const header = screen.getByRole("banner");
    expect(header.className).toContain("sticky");
  });

  it("uses the design-system background color", () => {
    renderLayout();
    const wrapper = screen.getByRole("banner").parentElement!;
    expect(wrapper.className).toContain("bg-bg-main");
  });

  it("main area fills remaining vertical space", () => {
    renderLayout();
    const main = screen.getByRole("main");
    expect(main.className).toContain("flex-1");
  });
});
