import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import PropertyCard from "../PropertyCard";
import type { ForecastResponse } from "../../../types";

const mockForecast: ForecastResponse = {
  address: "456 Oak Ave",
  predicted_value: 425000,
  confidence_interval_low: 400000,
  confidence_interval_high: 450000,
  model_version: "v2.1",
};

describe("PropertyCard", () => {
  it("renders the address", () => {
    render(<PropertyCard forecast={mockForecast} />);
    expect(screen.getByText("456 Oak Ave")).toBeInTheDocument();
  });

  it("renders the predicted value in currency format", () => {
    render(<PropertyCard forecast={mockForecast} />);
    const formatted = new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      maximumFractionDigits: 0,
    }).format(425000);
    expect(screen.getByText(formatted)).toBeInTheDocument();
  });

  it("renders confidence range", () => {
    render(<PropertyCard forecast={mockForecast} />);
    const formatter = new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      maximumFractionDigits: 0,
    });
    // The range text contains both values with an en-dash
    const rangeText = screen.getByText(/Range:/);
    expect(rangeText.textContent).toContain(formatter.format(400000));
    expect(rangeText.textContent).toContain(formatter.format(450000));
  });

  it("renders model version", () => {
    render(<PropertyCard forecast={mockForecast} />);
    expect(screen.getByText(/v2\.1/)).toBeInTheDocument();
  });
});
