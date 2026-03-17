import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import MetricCard from "../MetricCard";

describe("MetricCard", () => {
  it("renders currency format", () => {
    render(<MetricCard name="MAE" value={25000} format="currency" />);
    expect(screen.getByText("MAE")).toBeInTheDocument();
    expect(screen.getByText("$25,000")).toBeInTheDocument();
  });

  it("renders percentage format", () => {
    render(<MetricCard name="MAPE" value={0.085} format="percentage" />);
    expect(screen.getByText("8.50%")).toBeInTheDocument();
  });

  it("renders number format", () => {
    render(<MetricCard name="R2" value={0.92} format="number" />);
    expect(screen.getByText("0.92")).toBeInTheDocument();
  });

  it("renders N/A for null value", () => {
    render(<MetricCard name="Test" value={null} format="currency" />);
    expect(screen.getByText("N/A")).toBeInTheDocument();
  });

  it("renders subtitle when provided", () => {
    render(<MetricCard name="MAE" value={25000} format="currency" subtitle="Mean Error" />);
    expect(screen.getByText("Mean Error")).toBeInTheDocument();
  });
});
