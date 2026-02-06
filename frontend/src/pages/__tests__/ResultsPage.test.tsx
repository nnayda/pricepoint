import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { axe } from "vitest-axe";
import ResultsPage from "../ResultsPage";
import type { PropertyResponse } from "../../types";

// Mock usePropertyData
const mockUsePropertyData = vi.fn(() => ({
  data: null as PropertyResponse | null,
  loading: false,
  error: null as string | null,
}));

vi.mock("../../hooks/usePropertyData", () => ({
  usePropertyData: (...args: unknown[]) => mockUsePropertyData(...args),
}));

// Mock section components to isolate ResultsPage logic
vi.mock("../../components/PropertyHeader/PropertyHeader", () => ({
  default: (props: Record<string, unknown>) => (
    <div data-testid="property-header" data-props={JSON.stringify(props)} />
  ),
}));

vi.mock("../../components/ValueSection/ValueSection", () => ({
  default: (props: Record<string, unknown>) => (
    <div data-testid="value-section" data-props={JSON.stringify(props)} />
  ),
}));

vi.mock("../../components/PropertyDescription/PropertyDescription", () => ({
  default: (props: Record<string, unknown>) => (
    <div data-testid="property-description" data-props={JSON.stringify(props)} />
  ),
}));

vi.mock("../../components/SchoolsSection/SchoolsSection", () => ({
  default: (props: Record<string, unknown>) => (
    <div data-testid="schools-section" data-props={JSON.stringify(props)} />
  ),
}));

vi.mock("../../components/PropertyDetailsSection/PropertyDetailsSection", () => ({
  default: (props: Record<string, unknown>) => (
    <div data-testid="property-details-section" data-props={JSON.stringify(props)} />
  ),
}));

vi.mock("../../components/SaleTaxHistoryChart/SaleTaxHistoryChart", () => ({
  default: (props: Record<string, unknown>) => (
    <div data-testid="sale-tax-history-chart" data-props={JSON.stringify(props)} />
  ),
}));

vi.mock("../../components/ClimateRiskSection/ClimateRiskSection", () => ({
  default: (props: Record<string, unknown>) => (
    <div data-testid="climate-risk-section" data-props={JSON.stringify(props)} />
  ),
}));

vi.mock("../../components/MortgageCalculator/MortgageCalculator", () => ({
  default: (props: Record<string, unknown>) => (
    <div data-testid="mortgage-calculator" data-props={JSON.stringify(props)} />
  ),
}));

vi.mock("../../components/PropertyMap/PropertyMap", () => ({
  default: (props: Record<string, unknown>) => (
    <div data-testid="property-map" data-props={JSON.stringify(props)} />
  ),
}));

vi.mock("../../components/SectionSidebar/SectionSidebar", () => ({
  default: () => <nav data-testid="section-sidebar" />,
}));

vi.mock("../../components/SkeletonResultsPage/SkeletonResultsPage", () => ({
  default: () => <div data-testid="skeleton-results-page" />,
}));

const mockPropertyData: PropertyResponse = {
  property: {
    address: "123 Main St",
    city: "Cary",
    state: "NC",
    zip_code: "27513",
    lat: 35.73,
    lon: -78.78,
    bedrooms: 4,
    bathrooms: 2.5,
    sqft: 2200,
    lot_size_sqft: 8500,
    year_built: 2005,
    property_type: "Single Family",
    stories: 2,
    garage_spaces: 2,
    description: "A beautiful home.",
    highlights: ["Open floor plan", "Granite countertops"],
    images: [{ url: "https://example.com/img.jpg", alt: "Front", is_primary: true }],
  },
  valuation: {
    listed_price: 485000,
    last_sold_price: 310000,
    last_sold_date: "2018-06-15",
    predicted_value: 472000,
    confidence_interval_low: 449000,
    confidence_interval_high: 495000,
    model_version: "v2.3.1",
    prediction_date: "2025-01-15",
  },
  interior: {
    flooring: ["Hardwood", "Tile"],
    appliances: ["Dishwasher", "Microwave"],
    heating: "Forced Air",
    cooling: "Central AC",
    fireplace: true,
    basement: "Finished",
  },
  exterior: {
    roof: "Asphalt Shingle",
    siding: "Vinyl",
    foundation: "Slab",
    parking: "Attached Garage",
    pool: false,
    fence: "Wood",
  },
  financial: {
    hoa_monthly: 85,
    tax_annual: 4234,
    tax_year: 2024,
    assessed_value: 420000,
  },
  schools: [
    {
      name: "Cary Elementary",
      school_type: "Elementary",
      rating: 8,
      distance_miles: 0.5,
      drive_minutes: 3,
      walk_minutes: 10,
    },
  ],
  sale_history: [{ date: "2018-06-15", price: 310000, event_type: "Sold" }],
  tax_history: [{ year: 2024, assessed_value: 420000, tax_amount: 4234 }],
  climate_risk: {
    flood_risk: "Low",
    flood_score: 2,
    fire_risk: "Moderate",
    fire_score: 5,
  },
};

function renderResultsPage(path = "/results?address=123+Main+St&lat=35.73&lon=-78.78") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <ResultsPage />
    </MemoryRouter>,
  );
}

describe("ResultsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUsePropertyData.mockReturnValue({
      data: null,
      loading: false,
      error: null,
    });
  });

  // -- No address --

  it("renders empty state when no address is provided", () => {
    renderResultsPage("/results");
    expect(screen.getByText("No address provided")).toBeInTheDocument();
  });

  it("renders a link back to search in empty state", () => {
    renderResultsPage("/results");
    const link = screen.getByRole("link", { name: /go to search/i });
    expect(link).toHaveAttribute("href", "/");
  });

  // -- Loading --

  it("renders skeleton loading page when loading", () => {
    mockUsePropertyData.mockReturnValue({
      data: null,
      loading: true,
      error: null,
    });
    renderResultsPage();
    expect(screen.getByTestId("skeleton-results-page")).toBeInTheDocument();
  });

  // -- Error --

  it("renders error message", () => {
    mockUsePropertyData.mockReturnValue({
      data: null,
      loading: false,
      error: "Network error",
    });
    renderResultsPage();
    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
    expect(screen.getByText("Network error")).toBeInTheDocument();
  });

  it("renders a link to try another address in error state", () => {
    mockUsePropertyData.mockReturnValue({
      data: null,
      loading: false,
      error: "Network error",
    });
    renderResultsPage();
    const link = screen.getByRole("link", { name: /try another address/i });
    expect(link).toHaveAttribute("href", "/");
  });

  // -- Success: all sections rendered --

  it("renders all 9 section components", () => {
    mockUsePropertyData.mockReturnValue({
      data: mockPropertyData,
      loading: false,
      error: null,
    });
    renderResultsPage();

    expect(screen.getByTestId("property-header")).toBeInTheDocument();
    expect(screen.getByTestId("value-section")).toBeInTheDocument();
    expect(screen.getByTestId("property-description")).toBeInTheDocument();
    expect(screen.getByTestId("schools-section")).toBeInTheDocument();
    expect(screen.getByTestId("property-details-section")).toBeInTheDocument();
    expect(screen.getByTestId("sale-tax-history-chart")).toBeInTheDocument();
    expect(screen.getByTestId("climate-risk-section")).toBeInTheDocument();
    expect(screen.getByTestId("mortgage-calculator")).toBeInTheDocument();
    expect(screen.getByTestId("property-map")).toBeInTheDocument();
  });

  // -- SectionSidebar --

  it("renders SectionSidebar", () => {
    mockUsePropertyData.mockReturnValue({
      data: mockPropertyData,
      loading: false,
      error: null,
    });
    renderResultsPage();
    expect(screen.getByTestId("section-sidebar")).toBeInTheDocument();
  });

  // -- Section IDs for anchor navigation --

  it("has section IDs for anchor navigation", () => {
    mockUsePropertyData.mockReturnValue({
      data: mockPropertyData,
      loading: false,
      error: null,
    });
    const { container } = renderResultsPage();

    const expectedIds = [
      "property-header",
      "valuation",
      "description",
      "schools",
      "details",
      "history",
      "climate",
      "mortgage",
      "map",
    ];
    expectedIds.forEach((id) => {
      expect(container.querySelector(`#${id}`)).not.toBeNull();
    });
  });

  // -- Props passed to child components --

  it("passes property data to PropertyHeader", () => {
    mockUsePropertyData.mockReturnValue({
      data: mockPropertyData,
      loading: false,
      error: null,
    });
    renderResultsPage();
    const el = screen.getByTestId("property-header");
    const props = JSON.parse(el.getAttribute("data-props")!);
    expect(props.property.address).toBe("123 Main St");
    expect(props.property.bedrooms).toBe(4);
  });

  it("passes valuation data to ValueSection", () => {
    mockUsePropertyData.mockReturnValue({
      data: mockPropertyData,
      loading: false,
      error: null,
    });
    renderResultsPage();
    const el = screen.getByTestId("value-section");
    const props = JSON.parse(el.getAttribute("data-props")!);
    expect(props.valuation.predicted_value).toBe(472000);
  });

  it("passes schools array to SchoolsSection", () => {
    mockUsePropertyData.mockReturnValue({
      data: mockPropertyData,
      loading: false,
      error: null,
    });
    renderResultsPage();
    const el = screen.getByTestId("schools-section");
    const props = JSON.parse(el.getAttribute("data-props")!);
    expect(props.schools).toHaveLength(1);
    expect(props.schools[0].name).toBe("Cary Elementary");
  });

  it("passes lat/lon/address to PropertyMap", () => {
    mockUsePropertyData.mockReturnValue({
      data: mockPropertyData,
      loading: false,
      error: null,
    });
    renderResultsPage();
    const el = screen.getByTestId("property-map");
    const props = JSON.parse(el.getAttribute("data-props")!);
    expect(props.lat).toBe(35.73);
    expect(props.lon).toBe(-78.78);
    expect(props.address).toBe("123 Main St");
  });

  it("passes price/tax/HOA to MortgageCalculator", () => {
    mockUsePropertyData.mockReturnValue({
      data: mockPropertyData,
      loading: false,
      error: null,
    });
    renderResultsPage();
    const el = screen.getByTestId("mortgage-calculator");
    const props = JSON.parse(el.getAttribute("data-props")!);
    expect(props.listedPrice).toBe(485000);
    expect(props.annualTax).toBe(4234);
    expect(props.monthlyHoa).toBe(85);
  });

  it("uses predicted_value when listed_price is absent", () => {
    const noListed = {
      ...mockPropertyData,
      valuation: { ...mockPropertyData.valuation, listed_price: undefined },
    };
    mockUsePropertyData.mockReturnValue({
      data: noListed,
      loading: false,
      error: null,
    });
    renderResultsPage();
    const el = screen.getByTestId("mortgage-calculator");
    const props = JSON.parse(el.getAttribute("data-props")!);
    expect(props.listedPrice).toBe(472000);
  });

  // -- Back link --

  it("renders back to search link in success state", () => {
    mockUsePropertyData.mockReturnValue({
      data: mockPropertyData,
      loading: false,
      error: null,
    });
    renderResultsPage();
    const link = screen.getByRole("link", { name: /back to search/i });
    expect(link).toHaveAttribute("href", "/");
  });

  // -- Calls usePropertyData with correct args --

  it("calls usePropertyData with parsed lat, lon, and address", () => {
    renderResultsPage("/results?address=123+Main+St&lat=35.73&lon=-78.78");
    expect(mockUsePropertyData).toHaveBeenCalledWith(35.73, -78.78, "123 Main St");
  });

  // -- null data --

  it("returns null when data is null and not loading/error", () => {
    mockUsePropertyData.mockReturnValue({
      data: null,
      loading: false,
      error: null,
    });
    renderResultsPage();
    // Should not render any section components or error/loading
    expect(screen.queryByTestId("property-header")).not.toBeInTheDocument();
    expect(screen.queryByText("Something went wrong")).not.toBeInTheDocument();
    expect(screen.queryByTestId("skeleton-results-page")).not.toBeInTheDocument();
  });

  // -- Accessibility --

  it("has no axe violations in empty state", async () => {
    const { container } = renderResultsPage("/results");
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it("has no axe violations in success state", async () => {
    mockUsePropertyData.mockReturnValue({
      data: mockPropertyData,
      loading: false,
      error: null,
    });
    const { container } = renderResultsPage();
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
