import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { axe } from "vitest-axe";
import SchoolsSection from "../SchoolsSection";
import type { SchoolNearby } from "../../../types";

const mockSchools: SchoolNearby[] = [
  {
    name: "Mills Park Elementary",
    school_type: "Elementary",
    rating: 9,
    distance_miles: 0.8,
    drive_minutes: 3,
    walk_minutes: 16,
  },
  {
    name: "Green Hope High",
    school_type: "High",
    rating: 8,
    distance_miles: 2.1,
    drive_minutes: 7,
  },
  {
    name: "Salem Middle",
    school_type: "Middle",
    rating: 3,
    distance_miles: 3.2,
    drive_minutes: 10,
  },
];

describe("SchoolsSection", () => {
  it("renders the heading", () => {
    render(<SchoolsSection schools={mockSchools} />);
    expect(screen.getByText("Nearby Schools")).toBeInTheDocument();
  });

  it("renders school names", () => {
    render(<SchoolsSection schools={mockSchools} />);
    expect(screen.getByText("Mills Park Elementary")).toBeInTheDocument();
    expect(screen.getByText("Green Hope High")).toBeInTheDocument();
    expect(screen.getByText("Salem Middle")).toBeInTheDocument();
  });

  it("renders school types", () => {
    render(<SchoolsSection schools={mockSchools} />);
    expect(screen.getByText("Elementary")).toBeInTheDocument();
    expect(screen.getByText("High")).toBeInTheDocument();
    expect(screen.getByText("Middle")).toBeInTheDocument();
  });

  it("renders ratings", () => {
    render(<SchoolsSection schools={mockSchools} />);
    expect(screen.getByLabelText("Rating 9 out of 10")).toBeInTheDocument();
    expect(screen.getByLabelText("Rating 8 out of 10")).toBeInTheDocument();
    expect(screen.getByLabelText("Rating 3 out of 10")).toBeInTheDocument();
  });

  it("renders distance and drive time", () => {
    render(<SchoolsSection schools={mockSchools} />);
    expect(screen.getByText("0.8 mi")).toBeInTheDocument();
    expect(screen.getByText("3 min drive")).toBeInTheDocument();
  });

  it("renders walk time when available", () => {
    render(<SchoolsSection schools={mockSchools} />);
    expect(screen.getByText("16 min walk")).toBeInTheDocument();
  });

  it("does not render walk time when not available", () => {
    render(<SchoolsSection schools={mockSchools} />);
    // Green Hope High has no walk_minutes, so check there's no walk time for it
    const items = screen.getAllByText(/min walk/);
    expect(items.length).toBe(1); // Only Mills Park has walk time
  });

  it("shows empty state when no schools", () => {
    render(<SchoolsSection schools={[]} />);
    expect(screen.getByText("No school data available.")).toBeInTheDocument();
  });

  it("has no accessibility violations", async () => {
    const { container } = render(<SchoolsSection schools={mockSchools} />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
