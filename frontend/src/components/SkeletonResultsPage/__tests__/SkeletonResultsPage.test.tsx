import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { axe } from "vitest-axe";
import SkeletonResultsPage from "../SkeletonResultsPage";

describe("SkeletonResultsPage", () => {
  it("renders with loading status role", () => {
    render(<SkeletonResultsPage />);
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("has aria-label for loading state", () => {
    render(<SkeletonResultsPage />);
    expect(screen.getByLabelText("Loading property data")).toBeInTheDocument();
  });

  it("renders screen reader text", () => {
    render(<SkeletonResultsPage />);
    expect(screen.getByText("Loading property data...")).toBeInTheDocument();
  });

  it("renders multiple skeleton blocks", () => {
    const { container } = render(<SkeletonResultsPage />);
    const pulseElements = container.querySelectorAll(".animate-pulse");
    expect(pulseElements.length).toBeGreaterThan(5);
  });

  it("has no accessibility violations", async () => {
    const { container } = render(<SkeletonResultsPage />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
