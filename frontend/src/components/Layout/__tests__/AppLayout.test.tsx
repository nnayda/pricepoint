import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import AppLayout from "../AppLayout";

function renderLayout(children = <p>Page content</p>, initialPath = "/") {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <AppLayout>{children}</AppLayout>
    </MemoryRouter>,
  );
}

describe("AppLayout", () => {
  it("renders children directly as a passthrough shell", () => {
    renderLayout(<p>Test child</p>);
    expect(screen.getByText("Test child")).toBeInTheDocument();
  });

  it("does not render any wrapping navigation", () => {
    renderLayout(<p>content</p>, "/some-path");
    expect(screen.queryByRole("navigation")).not.toBeInTheDocument();
  });

  it("renders children for any route", () => {
    renderLayout(<p>Dashboard content</p>, "/property/123-main-st");
    expect(screen.getByText("Dashboard content")).toBeInTheDocument();
  });
});
