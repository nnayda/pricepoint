import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import Badge from "../Badge";

describe("Badge", () => {
  it("renders children text", () => {
    render(<Badge>Active</Badge>);
    expect(screen.getByText("Active")).toBeInTheDocument();
  });

  it("applies neutral variant by default", () => {
    render(<Badge>Neutral</Badge>);
    const badge = screen.getByText("Neutral").closest("span");
    expect(badge?.className).toContain("border");
  });

  it("applies success variant classes", () => {
    render(<Badge variant="success">Success</Badge>);
    const badge = screen.getByText("Success").closest("span");
    expect(badge?.className).toContain("text-[var(--color-db-green)]");
  });

  it("applies warning variant classes", () => {
    render(<Badge variant="warning">Warning</Badge>);
    const badge = screen.getByText("Warning").closest("span");
    expect(badge?.className).toContain("text-[var(--color-db-yellow)]");
  });

  it("applies danger variant classes", () => {
    render(<Badge variant="danger">Danger</Badge>);
    const badge = screen.getByText("Danger").closest("span");
    expect(badge?.className).toContain("text-[var(--color-db-red)]");
  });

  it("applies info variant classes", () => {
    render(<Badge variant="info">Info</Badge>);
    const badge = screen.getByText("Info").closest("span");
    expect(badge?.className).toContain("text-[var(--color-db-cyan)]");
  });

  it("applies accent variant classes", () => {
    render(<Badge variant="accent">Accent</Badge>);
    const badge = screen.getByText("Accent").closest("span");
    expect(badge?.className).toContain("text-[var(--color-db-accent)]");
  });

  it("shows dot indicator when dot prop is true", () => {
    const { container } = render(<Badge dot>With Dot</Badge>);
    const dots = container.querySelectorAll(".rounded-full.bg-current");
    expect(dots.length).toBe(1);
  });

  it("hides dot indicator by default", () => {
    const { container } = render(<Badge>No Dot</Badge>);
    const dots = container.querySelectorAll(".bg-current");
    expect(dots.length).toBe(0);
  });

  it("appends custom className", () => {
    render(<Badge className="my-class">Custom</Badge>);
    const badge = screen.getByText("Custom").closest("span");
    expect(badge?.className).toContain("my-class");
  });
});
