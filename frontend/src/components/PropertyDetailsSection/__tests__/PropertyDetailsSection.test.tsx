import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { axe } from "vitest-axe";
import PropertyDetailsSection from "../PropertyDetailsSection";
import type { InteriorFeatures, ExteriorFeatures, FinancialDetails } from "../../../types";

const interior: InteriorFeatures = {
  flooring: ["Hardwood", "Carpet", "Tile"],
  appliances: ["Dishwasher", "Microwave", "Refrigerator"],
  heating: "Forced Air",
  cooling: "Central Air",
  fireplace: true,
  basement: undefined,
};

const exterior: ExteriorFeatures = {
  roof: "Architectural Shingle",
  siding: "Fiber Cement",
  foundation: "Slab",
  parking: "2-Car Garage",
  pool: false,
  fence: "Wood",
};

const financial: FinancialDetails = {
  hoa_monthly: 85,
  tax_annual: 4234,
  tax_year: 2024,
  assessed_value: 412000,
};

describe("PropertyDetailsSection", () => {
  it("renders the heading", () => {
    render(
      <PropertyDetailsSection interior={interior} exterior={exterior} financial={financial} />,
    );
    expect(screen.getByText("Property Details")).toBeInTheDocument();
  });

  it("renders interior section", () => {
    render(
      <PropertyDetailsSection interior={interior} exterior={exterior} financial={financial} />,
    );
    expect(screen.getByText("Interior")).toBeInTheDocument();
    expect(screen.getByText("Hardwood, Carpet, Tile")).toBeInTheDocument();
    expect(screen.getByText("Forced Air")).toBeInTheDocument();
    expect(screen.getByText("Central Air")).toBeInTheDocument();
  });

  it("renders fireplace as Yes when true", () => {
    render(
      <PropertyDetailsSection interior={interior} exterior={exterior} financial={financial} />,
    );
    const yesTexts = screen.getAllByText("Yes");
    expect(yesTexts.length).toBeGreaterThan(0);
  });

  it("does not render basement when undefined", () => {
    render(
      <PropertyDetailsSection interior={interior} exterior={exterior} financial={financial} />,
    );
    expect(screen.queryByText("Basement")).not.toBeInTheDocument();
  });

  it("renders exterior section", () => {
    render(
      <PropertyDetailsSection interior={interior} exterior={exterior} financial={financial} />,
    );
    expect(screen.getByText("Exterior")).toBeInTheDocument();
    expect(screen.getByText("Architectural Shingle")).toBeInTheDocument();
    expect(screen.getByText("2-Car Garage")).toBeInTheDocument();
  });

  it("renders financial section", () => {
    render(
      <PropertyDetailsSection interior={interior} exterior={exterior} financial={financial} />,
    );
    expect(screen.getByText("Financial")).toBeInTheDocument();
    expect(screen.getByText("$4,234")).toBeInTheDocument();
    expect(screen.getByText("$412,000")).toBeInTheDocument();
  });

  it("renders HOA when available", () => {
    render(
      <PropertyDetailsSection interior={interior} exterior={exterior} financial={financial} />,
    );
    expect(screen.getByText("HOA (monthly)")).toBeInTheDocument();
    expect(screen.getByText("$85")).toBeInTheDocument();
  });

  it("does not render HOA when null", () => {
    const noHoa = { ...financial, hoa_monthly: undefined };
    render(
      <PropertyDetailsSection
        interior={interior}
        exterior={exterior}
        financial={noHoa as FinancialDetails}
      />,
    );
    expect(screen.queryByText("HOA (monthly)")).not.toBeInTheDocument();
  });

  it("has no accessibility violations", async () => {
    const { container } = render(
      <PropertyDetailsSection interior={interior} exterior={exterior} financial={financial} />,
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
