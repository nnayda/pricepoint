import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import ComparableProperties from "../ComparableProperties";
import type { ComparableProperty } from "../../../types";

const mockComparables: ComparableProperty[] = [
  {
    id: 1,
    address: "123 Main St, Raleigh NC 27601",
    sale_price: 425000,
    sold_date: "2025-11-15",
    beds: 3,
    baths: 2,
    sqft: 1800,
    price_per_sqft: 236,
    lat: 35.78,
    lon: -78.64,
    thumbnail_url: "https://example.com/photo1.jpg",
  },
  {
    id: 2,
    address: "456 Oak Ave, Raleigh NC 27605",
    sale_price: 389000,
    sold_date: "2025-10-20",
    beds: 3,
    baths: 2,
    sqft: 1650,
    price_per_sqft: 236,
    lat: 35.79,
    lon: -78.65,
  },
  {
    id: 3,
    address: "789 Pine Rd, Raleigh NC 27607",
    sale_price: 450000,
    sold_date: "2025-12-01",
    beds: 4,
    baths: 3,
    sqft: 2200,
    price_per_sqft: 205,
    lat: 35.8,
    lon: -78.66,
  },
];

describe("ComparableProperties", () => {
  it("renders the grid of comparable cards", () => {
    render(<ComparableProperties comparables={mockComparables} />);
    expect(screen.getByTestId("comparables-grid")).toBeInTheDocument();
  });

  it("shows empty state when no comparables", () => {
    render(<ComparableProperties comparables={[]} />);
    expect(screen.getByTestId("comparables-empty")).toBeInTheDocument();
    expect(screen.getByText("No comparables found")).toBeInTheDocument();
  });

  it("renders a card for each comparable", () => {
    render(<ComparableProperties comparables={mockComparables} />);
    expect(screen.getByTestId("comparable-card-1")).toBeInTheDocument();
    expect(screen.getByTestId("comparable-card-2")).toBeInTheDocument();
    expect(screen.getByTestId("comparable-card-3")).toBeInTheDocument();
  });

  it("displays addresses", () => {
    render(<ComparableProperties comparables={mockComparables} />);
    expect(screen.getByText("123 Main St, Raleigh NC 27601")).toBeInTheDocument();
    expect(screen.getByText("456 Oak Ave, Raleigh NC 27605")).toBeInTheDocument();
  });

  it("displays formatted sale prices", () => {
    render(<ComparableProperties comparables={mockComparables} />);
    expect(screen.getByText("$425,000")).toBeInTheDocument();
    expect(screen.getByText("$389,000")).toBeInTheDocument();
    expect(screen.getByText("$450,000")).toBeInTheDocument();
  });

  it("displays sold dates", () => {
    render(<ComparableProperties comparables={mockComparables} />);
    expect(screen.getByText("Sold 2025-11-15")).toBeInTheDocument();
    expect(screen.getByText("Sold 2025-10-20")).toBeInTheDocument();
  });

  it("displays beds, baths, and sqft", () => {
    render(<ComparableProperties comparables={mockComparables} />);
    const card1 = screen.getByTestId("comparable-card-1");
    expect(card1).toHaveTextContent("3 bd");
    expect(card1).toHaveTextContent("2 ba");
    expect(card1).toHaveTextContent("1,800 sqft");
  });

  it("renders thumbnail when provided", () => {
    render(<ComparableProperties comparables={mockComparables} />);
    const images = screen.getAllByRole("img");
    expect(images).toHaveLength(1);
    expect(images[0]).toHaveAttribute("src", "https://example.com/photo1.jpg");
  });

  it("does not render image when no thumbnail_url", () => {
    render(<ComparableProperties comparables={[mockComparables[1]]} />);
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  });
});
