import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { axe } from "vitest-axe";
import ClimateRiskSection from "../ClimateRiskSection";
import type { ClimateRisk } from "../../../types";

const mockClimateRisk: ClimateRisk = {
  flood_risk: "Moderate",
  flood_score: 3,
  fire_risk: "Low",
  fire_score: 2,
};

describe("ClimateRiskSection", () => {
  it("renders the heading", () => {
    render(<ClimateRiskSection climateRisk={mockClimateRisk} />);
    expect(screen.getByText("Climate Risk")).toBeInTheDocument();
  });

  it("renders flood risk label and level", () => {
    render(<ClimateRiskSection climateRisk={mockClimateRisk} />);
    expect(screen.getByText("Flood Risk")).toBeInTheDocument();
    expect(screen.getByText("Moderate")).toBeInTheDocument();
  });

  it("renders fire risk label and level", () => {
    render(<ClimateRiskSection climateRisk={mockClimateRisk} />);
    expect(screen.getByText("Fire Risk")).toBeInTheDocument();
    expect(screen.getByText("Low")).toBeInTheDocument();
  });

  it("renders flood score meter", () => {
    render(<ClimateRiskSection climateRisk={mockClimateRisk} />);
    const meter = screen.getByLabelText("Flood Risk score");
    expect(meter).toHaveAttribute("aria-valuenow", "3");
    expect(meter).toHaveAttribute("aria-valuemin", "1");
    expect(meter).toHaveAttribute("aria-valuemax", "10");
  });

  it("renders fire score meter", () => {
    render(<ClimateRiskSection climateRisk={mockClimateRisk} />);
    const meter = screen.getByLabelText("Fire Risk score");
    expect(meter).toHaveAttribute("aria-valuenow", "2");
  });

  it("shows score out of 10", () => {
    render(<ClimateRiskSection climateRisk={mockClimateRisk} />);
    expect(screen.getByText("3/10")).toBeInTheDocument();
    expect(screen.getByText("2/10")).toBeInTheDocument();
  });

  it("has no accessibility violations", async () => {
    const { container } = render(<ClimateRiskSection climateRisk={mockClimateRisk} />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
