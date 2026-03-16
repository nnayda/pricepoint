import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect } from "vitest";
import CompColumn from "../CompColumn";
import type { CompPropertyDetail } from "../../../types";

const MOCK_PROPERTY: CompPropertyDetail = {
  listing_id: 1,
  address: "100 Main St",
  city: "Cary",
  state: "NC",
  zip_code: "27513",
  lat: 35.7,
  lon: -78.8,
  sold_price: 400000,
  sold_date: "2025-01-15",
  listing_price: 410000,
  beds: 3,
  baths: 2,
  sqft: 2000,
  lot_size: 0.25,
  year_built: 2005,
  garage_spaces: 2,
  price_per_sqft: 200,
  photos: [],
  description_score: 7,
  photo_score: 8,
  feature_groups: [
    {
      category: "Core Stats",
      features: { property_age: 20, bed_bath_ratio: 1.5 },
    },
  ],
  nuisances: [
    {
      name: "RDU Airport",
      source_type: "aviation",
      severity: "Concern",
      distance_miles: 5.2,
      detail: "Airport noise zone",
    },
  ],
  risks: [
    {
      name: "Duke Energy",
      infrastructure_type: "transmission_line",
      severity: "Caution",
      distance_miles: 0.8,
      detail: "Transmission Line — within caution risk zone",
    },
  ],
  similarity_distance: null,
};

function renderWithRouter(ui: React.ReactElement) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

describe("CompColumn", () => {
  it("renders property address", () => {
    renderWithRouter(<CompColumn property={MOCK_PROPERTY} />);
    expect(screen.getByText("100 Main St")).toBeInTheDocument();
  });

  it("renders sold price for comparables", () => {
    renderWithRouter(<CompColumn property={MOCK_PROPERTY} />);
    expect(screen.getByText("$400,000")).toBeInTheDocument();
    expect(screen.getByText("$200")).toBeInTheDocument();
  });

  it("renders listing price for subject", () => {
    renderWithRouter(<CompColumn property={MOCK_PROPERTY} isSubject />);
    expect(screen.getByText("$410,000")).toBeInTheDocument();
  });

  it("shows SUBJECT badge when isSubject", () => {
    renderWithRouter(<CompColumn property={MOCK_PROPERTY} isSubject />);
    expect(screen.getByText("SUBJECT")).toBeInTheDocument();
  });

  it("shows similarity distance for comps", () => {
    const comp = { ...MOCK_PROPERTY, similarity_distance: 2.34 };
    renderWithRouter(<CompColumn property={comp} />);
    expect(screen.getByText("Sim: 2.34")).toBeInTheDocument();
  });

  it("shows price difference label next to sim score", () => {
    const subject = { ...MOCK_PROPERTY, listing_price: 400000 };
    const comp = { ...MOCK_PROPERTY, sold_price: 420000, similarity_distance: 1.5 };
    renderWithRouter(<CompColumn property={comp} subjectProperty={subject} />);
    expect(screen.getByText("+$20,000")).toBeInTheDocument();
  });

  it("renders score badges", () => {
    renderWithRouter(<CompColumn property={MOCK_PROPERTY} />);
    expect(screen.getByText("Desc: 7/10")).toBeInTheDocument();
    expect(screen.getByText("Photo: 8/10")).toBeInTheDocument();
  });

  it("renders nuisances", () => {
    renderWithRouter(<CompColumn property={MOCK_PROPERTY} />);
    expect(screen.getByText("RDU Airport")).toBeInTheDocument();
  });

  it("renders risks", () => {
    renderWithRouter(<CompColumn property={MOCK_PROPERTY} />);
    expect(screen.getByText("Duke Energy")).toBeInTheDocument();
  });

  it("shows no photo placeholder when no photos", () => {
    renderWithRouter(<CompColumn property={MOCK_PROPERTY} />);
    expect(screen.getByText("No photo")).toBeInTheDocument();
  });

  it("renders photo when available", () => {
    const withPhoto = { ...MOCK_PROPERTY, photos: ["/api/photos/test.jpg"] };
    renderWithRouter(<CompColumn property={withPhoto} />);
    const img = screen.getByAltText("100 Main St");
    expect(img).toBeInTheDocument();
    expect(img).toHaveAttribute("src", "/api/photos/test.jpg");
  });

  it("shows 'View property' link for comparable properties", () => {
    renderWithRouter(<CompColumn property={MOCK_PROPERTY} />);
    const link = screen.getByRole("link", { name: /view property/i });
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute(
      "href",
      `/property/${encodeURIComponent("100 Main St")}?lat=35.7&lon=-78.8`,
    );
  });

  it("does not show 'View property' link for subject property", () => {
    renderWithRouter(<CompColumn property={MOCK_PROPERTY} isSubject />);
    expect(screen.queryByRole("link", { name: /view property/i })).not.toBeInTheDocument();
  });
});
