import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { axe } from "vitest-axe";
import PropertyDescription from "../PropertyDescription";

describe("PropertyDescription", () => {
  it("renders the heading", () => {
    render(<PropertyDescription highlights={[]} description="A home." />);
    expect(screen.getByText("Description")).toBeInTheDocument();
  });

  it("renders the description text", () => {
    render(<PropertyDescription highlights={[]} description="A beautiful home in Cary." />);
    expect(screen.getByText("A beautiful home in Cary.")).toBeInTheDocument();
  });

  it("renders highlights as list items", () => {
    render(
      <PropertyDescription
        highlights={["Open floor plan", "Granite countertops"]}
        description="Nice."
      />,
    );
    expect(screen.getByText("Open floor plan")).toBeInTheDocument();
    expect(screen.getByText("Granite countertops")).toBeInTheDocument();
  });

  it("renders highlights list with aria-label", () => {
    render(<PropertyDescription highlights={["Open floor plan"]} description="Nice." />);
    expect(screen.getByLabelText("Property highlights")).toBeInTheDocument();
  });

  it("does not render highlights list when empty", () => {
    render(<PropertyDescription highlights={[]} description="Nice." />);
    expect(screen.queryByLabelText("Property highlights")).not.toBeInTheDocument();
  });

  it("has no accessibility violations", async () => {
    const { container } = render(
      <PropertyDescription
        highlights={["Open floor plan", "Granite countertops"]}
        description="A nice home."
      />,
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
