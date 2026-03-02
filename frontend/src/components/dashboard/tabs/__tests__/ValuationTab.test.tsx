import { describe, it, expect, vi, beforeAll } from "vitest";
import { render, screen } from "@testing-library/react";
import ValuationTab from "../ValuationTab";
import { mockDashboardData } from "../../../../data/mockDashboardData";
import type { DashboardData } from "../../../../types";

beforeAll(() => {
  globalThis.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver;
});

// Mock leaflet / map components to avoid DOM errors in jsdom
vi.mock("../../maps/DashboardMap", () => ({
  default: () => <div data-testid="mock-map" />,
}));

vi.mock("../../charts/PriceHistoryChart", () => ({
  default: () => <div data-testid="mock-price-history" />,
}));

vi.mock("../../charts/ShapWaterfall", () => ({
  default: () => <div data-testid="mock-shap" />,
}));

function buildData(overrides: Partial<DashboardData["valuation"]> = {}): DashboardData {
  return {
    ...mockDashboardData,
    valuation: {
      ...mockDashboardData.valuation,
      ...overrides,
    },
  };
}

describe("ValuationTab", () => {
  it("renders outcome badge and model estimate card when all model data is present", () => {
    const data = buildData({
      listed_price: 430000,
      predicted_value: 440000,
      confidence_low: 420000,
      confidence_high: 460000,
    });
    render(<ValuationTab data={data} />);

    expect(screen.getByText("Model Valuation Estimate")).toBeInTheDocument();
    expect(screen.getByText("Value")).toBeInTheDocument();
    expect(screen.getByText("Model Estimate")).toBeInTheDocument();
  });

  it("shows Bargain badge when listed price is below confidence low", () => {
    const data = buildData({
      listed_price: 400000,
      predicted_value: 450000,
      confidence_low: 420000,
      confidence_high: 460000,
    });
    render(<ValuationTab data={data} />);
    expect(screen.getByText("Bargain")).toBeInTheDocument();
  });

  it("shows model estimate card without CI when predicted_value exists but CI is missing", () => {
    const data = buildData({
      listed_price: 430000,
      predicted_value: 440000,
      confidence_low: undefined,
      confidence_high: undefined,
    });
    render(<ValuationTab data={data} />);

    // Still shows model estimate heading and card
    expect(screen.getByText("Model Valuation Estimate")).toBeInTheDocument();
    expect(screen.getByText("Model Estimate")).toBeInTheDocument();
    // Outcome badge should show (Value since listed < predicted)
    expect(screen.getByText("Value")).toBeInTheDocument();
  });

  it("shows Price Comparison heading when predicted_value is undefined", () => {
    const data = buildData({
      predicted_value: undefined,
      confidence_low: undefined,
      confidence_high: undefined,
    });
    render(<ValuationTab data={data} />);

    expect(screen.getByText("Price Comparison")).toBeInTheDocument();
    expect(screen.queryByText("Model Valuation Estimate")).not.toBeInTheDocument();
    // No outcome badge
    expect(screen.queryByText("Bargain")).not.toBeInTheDocument();
    expect(screen.queryByText("Value")).not.toBeInTheDocument();
    expect(screen.queryByText("Fair")).not.toBeInTheDocument();
    expect(screen.queryByText("Overpriced")).not.toBeInTheDocument();
    // Model Estimate card hidden
    expect(screen.queryByText("Model Estimate")).not.toBeInTheDocument();
  });

  it("still renders range bar when predicted_value is absent", () => {
    const data = buildData({
      predicted_value: undefined,
      confidence_low: undefined,
      confidence_high: undefined,
    });
    const { container } = render(<ValuationTab data={data} />);

    expect(
      container.querySelector(".rounded-full.bg-\\[var\\(--color-db-surface-alt\\)\\]"),
    ).toBeInTheDocument();
  });

  it("shows SHAP no-data overlay when predicted_value is undefined", () => {
    const data = buildData({
      predicted_value: undefined,
      confidence_low: undefined,
      confidence_high: undefined,
    });
    render(<ValuationTab data={data} />);

    const overlays = screen.getAllByText("Value drivers not available.");
    expect(overlays.length).toBeGreaterThanOrEqual(1);
  });

  it("uses notFound overlay on valuation card when notFound is true", () => {
    const data = {
      ...buildData({
        predicted_value: undefined,
        confidence_low: undefined,
        confidence_high: undefined,
      }),
      notFound: true,
    };
    render(<ValuationTab data={data} />);

    expect(screen.getByText("Valuation estimate not available.")).toBeInTheDocument();
  });
});
