import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import AppLayout from "../AppLayout";

function renderLayout(children = <p>Page content</p>) {
  return render(
    <MemoryRouter>
      <AppLayout>{children}</AppLayout>
    </MemoryRouter>,
  );
}

describe("AppLayout", () => {
  it("renders the brand name", () => {
    renderLayout();
    expect(screen.getByText("PricePoint")).toBeInTheDocument();
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

  it("has a sticky header with backdrop blur", () => {
    renderLayout();
    const header = screen.getByRole("banner");
    expect(header.className).toContain("sticky");
    expect(header.className).toContain("backdrop-blur-md");
  });

  it("uses the design-system background color", () => {
    renderLayout();
    const wrapper = screen.getByRole("banner").parentElement!;
    expect(wrapper.className).toContain("bg-bg-main");
  });

  it("header places brand and nav with space-between", () => {
    renderLayout();
    const header = screen.getByRole("banner");
    expect(header.className).toContain("justify-between");
  });

  it("main area fills remaining vertical space", () => {
    renderLayout();
    const main = screen.getByRole("main");
    expect(main.className).toContain("flex-1");
  });
});
