import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { axe } from "vitest-axe";
import PropertyHeader from "../PropertyHeader";
import type { PropertyDetails } from "../../../types";

const mockProperty: PropertyDetails = {
  address: "123 Main St, Cary, NC 27513",
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
  listing_status: "FOR SALE",
  images: [
    { url: "/images/front.jpg", alt: "Front view", is_primary: true },
    { url: "/images/kitchen.jpg", alt: "Kitchen", is_primary: false },
  ],
};

describe("PropertyHeader", () => {
  it("renders only the street portion of the address", () => {
    render(<PropertyHeader property={mockProperty} />);
    expect(screen.getByText("123 Main St")).toBeInTheDocument();
  });

  it("renders city, state, and zip", () => {
    render(<PropertyHeader property={mockProperty} />);
    expect(screen.getByText("Cary, NC 27513")).toBeInTheDocument();
  });

  it("renders property stats with aria-labels", () => {
    render(<PropertyHeader property={mockProperty} />);
    expect(screen.getByLabelText("4 bedrooms")).toBeInTheDocument();
    expect(screen.getByLabelText("3 bathrooms")).toBeInTheDocument();
    expect(screen.getByLabelText("2,847 square feet")).toBeInTheDocument();
    expect(screen.getByLabelText("Built in 2005")).toBeInTheDocument();
  });

  it("renders bedroom count", () => {
    render(<PropertyHeader property={mockProperty} />);
    expect(screen.getByLabelText("4 bedrooms")).toHaveTextContent("4");
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

  it("renders property type as secondary badge on photo", () => {
    render(<PropertyHeader property={mockProperty} />);
    const badge = screen.getByText("Single Family");
    expect(badge.tagName).toBe("SPAN");
    expect(badge.className).toContain("bg-black/50");
  });

  it("renders listing status badge", () => {
    render(<PropertyHeader property={mockProperty} />);
    const badge = screen.getByTestId("status-badge");
    expect(badge).toHaveTextContent("For Sale");
    expect(badge.className).toContain("bg-status-maint");
  });

  it("renders SOLD status badge with red color", () => {
    const sold = { ...mockProperty, listing_status: "SOLD" };
    render(<PropertyHeader property={sold} />);
    const badge = screen.getByTestId("status-badge");
    expect(badge).toHaveTextContent("Sold");
    expect(badge.className).toContain("bg-status-rented");
  });

  it("renders PENDING status badge with blue color", () => {
    const pending = { ...mockProperty, listing_status: "PENDING" };
    render(<PropertyHeader property={pending} />);
    const badge = screen.getByTestId("status-badge");
    expect(badge).toHaveTextContent("Pending");
    expect(badge.className).toContain("bg-brand-blue");
  });

  it("renders OFF MARKET status badge with gray color", () => {
    const offMarket = { ...mockProperty, listing_status: "OFF MARKET" };
    render(<PropertyHeader property={offMarket} />);
    const badge = screen.getByTestId("status-badge");
    expect(badge).toHaveTextContent("Off Market");
    expect(badge.className).toContain("bg-status-vacant");
  });

  it("defaults to For Sale when listing_status is undefined", () => {
    const noStatus = { ...mockProperty, listing_status: undefined };
    render(<PropertyHeader property={noStatus} />);
    const badge = screen.getByTestId("status-badge");
    expect(badge).toHaveTextContent("For Sale");
    expect(badge.className).toContain("bg-status-maint");
  });

  it("shows lot size in acres for large lots", () => {
    const bigLot = { ...mockProperty, lot_size_sqft: 43560 };
    render(<PropertyHeader property={bigLot} />);
    expect(screen.getByLabelText("Lot size 1.00 acres")).toBeInTheDocument();
  });

  it("shows lot size in sqft for small lots", () => {
    const smallLot = { ...mockProperty, lot_size_sqft: 5000 };
    render(<PropertyHeader property={smallLot} />);
    expect(screen.getByLabelText("Lot size 5,000 sqft")).toBeInTheDocument();
  });

  it("renders singular bedroom label for 1 bedroom", () => {
    const oneBed = { ...mockProperty, bedrooms: 1 };
    render(<PropertyHeader property={oneBed} />);
    expect(screen.getByLabelText("1 bedroom")).toBeInTheDocument();
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
