import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { axe } from "vitest-axe";
import PropertyHeader from "../PropertyHeader";
import type { PropertyDetails } from "../../../types";

const mockProperty: PropertyDetails = {
  address: "123 Main St",
  city: "Cary",
  state: "NC",
  zip_code: "27513",
  lat: 35.79,
  lon: -78.78,
  bedrooms: 4,
  bathrooms: 3.0,
  sqft: 2847,
  lot_size_sqft: 10890,
  year_built: 2005,
  property_type: "Single Family",
  stories: 2,
  garage_spaces: 2,
  description: "A nice home",
  highlights: ["Open floor plan"],
  images: [
    { url: "/images/front.jpg", alt: "Front view", is_primary: true },
    { url: "/images/kitchen.jpg", alt: "Kitchen", is_primary: false },
  ],
};

describe("PropertyHeader", () => {
  it("renders the address", () => {
    render(<PropertyHeader property={mockProperty} />);
    expect(screen.getByText("123 Main St")).toBeInTheDocument();
  });

  it("renders city, state, and zip", () => {
    render(<PropertyHeader property={mockProperty} />);
    expect(screen.getByText("Cary, NC 27513")).toBeInTheDocument();
  });

  it("renders property stats", () => {
    render(<PropertyHeader property={mockProperty} />);
    expect(screen.getByText("Beds")).toBeInTheDocument();
    expect(screen.getByText("Baths")).toBeInTheDocument();
    expect(screen.getByText("Sq Ft")).toBeInTheDocument();
    expect(screen.getByText("Built")).toBeInTheDocument();
    expect(screen.getByText("Type")).toBeInTheDocument();
  });

  it("renders bedroom count", () => {
    render(<PropertyHeader property={mockProperty} />);
    expect(screen.getByText("4")).toBeInTheDocument();
  });

  it("renders primary image", () => {
    render(<PropertyHeader property={mockProperty} />);
    const img = screen.getByAltText("Front view");
    expect(img).toBeInTheDocument();
    expect(img).toHaveAttribute("src", "/images/front.jpg");
  });

  it("renders fallback when no images", () => {
    const noImages = { ...mockProperty, images: [] };
    render(<PropertyHeader property={noImages} />);
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  });

  it("has property header aria-label", () => {
    render(<PropertyHeader property={mockProperty} />);
    expect(screen.getByLabelText("Property header")).toBeInTheDocument();
  });

  it("has no accessibility violations", async () => {
    const { container } = render(<PropertyHeader property={mockProperty} />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
