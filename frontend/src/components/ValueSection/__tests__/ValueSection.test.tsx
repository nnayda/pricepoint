import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { axe } from "vitest-axe";
import ValueSection from "../ValueSection";
import type { ValuationData } from "../../../types";

const mockValuation: ValuationData = {
  listed_price: 485000,
  last_sold_price: 310000,
  last_sold_date: "2018-06-15",
  predicted_value: 472000,
  confidence_interval_low: 449000,
  confidence_interval_high: 495000,
  model_version: "v2.3.1",
  prediction_date: "2025-01-15",
};

describe("ValueSection", () => {
  it("renders the heading", () => {
    render(<ValueSection valuation={mockValuation} />);
    expect(screen.getByText("Valuation")).toBeInTheDocument();
  });

  it("renders the predicted value", () => {
    render(<ValueSection valuation={mockValuation} />);
    expect(screen.getByText("$472,000")).toBeInTheDocument();
  });

  it("renders listed price when available", () => {
    render(<ValueSection valuation={mockValuation} />);
    const elements = screen.getAllByText("Listed Price");
    expect(elements.length).toBeGreaterThan(0);
    expect(screen.getByText("$485,000")).toBeInTheDocument();
  });

  it("shows Good Deal when listed price above predicted", () => {
    render(<ValueSection valuation={mockValuation} />);
    expect(screen.getByText("Good Deal")).toBeInTheDocument();
  });

  it("shows Over Predicted when predicted above listed", () => {
    const overPredicted = { ...mockValuation, predicted_value: 500000 };
    render(<ValueSection valuation={overPredicted} />);
    expect(screen.getByText("Over Predicted")).toBeInTheDocument();
  });

  it("shows model version", () => {
    render(<ValueSection valuation={mockValuation} />);
    expect(screen.getByText("Model: v2.3.1")).toBeInTheDocument();
  });

  it("shows confidence interval", () => {
    render(<ValueSection valuation={mockValuation} />);
    expect(screen.getByText(/\$449,000/)).toBeInTheDocument();
    expect(screen.getByText(/\$495,000/)).toBeInTheDocument();
  });

  it("handles missing listed_price by showing last sold", () => {
    const noListed = { ...mockValuation, listed_price: undefined };
    render(<ValueSection valuation={noListed} />);
    const elements = screen.getAllByText("Last Sold Price");
    expect(elements.length).toBeGreaterThan(0);
  });

  it("renders Redfin estimate when present", () => {
    const withRedfin = { ...mockValuation, redfin_estimate: 468000 };
    render(<ValueSection valuation={withRedfin} />);
    expect(screen.getByText("Redfin Estimate")).toBeInTheDocument();
    expect(screen.getByText("$468,000")).toBeInTheDocument();
  });

  it("does not render Redfin estimate when undefined", () => {
    render(<ValueSection valuation={mockValuation} />);
    expect(screen.queryByText("Redfin Estimate")).not.toBeInTheDocument();
  });

  it("handles missing predicted_value gracefully", () => {
    const noPrediction: ValuationData = {
      listed_price: 485000,
      last_sold_price: 310000,
      redfin_estimate: 470000,
    };
    render(<ValueSection valuation={noPrediction} />);
    expect(screen.queryByText("Predicted Value")).not.toBeInTheDocument();
    expect(screen.getByText("Redfin Estimate")).toBeInTheDocument();
    expect(screen.queryByText("Good Deal")).not.toBeInTheDocument();
  });

  it("has no accessibility violations", async () => {
    const { container } = render(<ValueSection valuation={mockValuation} />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
