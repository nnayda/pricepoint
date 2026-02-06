import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { axe } from "vitest-axe";
import SaleTaxHistoryChart from "../SaleTaxHistoryChart";
import type { SaleHistoryEntry, TaxHistoryEntry } from "../../../types";

// Mock recharts to avoid rendering issues in jsdom
vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
  ComposedChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="composed-chart">{children}</div>
  ),
  Line: () => <div data-testid="line" />,
  Area: () => <div data-testid="area" />,
  XAxis: () => <div data-testid="x-axis" />,
  YAxis: () => <div data-testid="y-axis" />,
  Tooltip: () => <div data-testid="tooltip" />,
  Legend: () => <div data-testid="legend" />,
  CartesianGrid: () => <div data-testid="cartesian-grid" />,
}));

const saleHistory: SaleHistoryEntry[] = [
  { date: "2005-03-22", price: 245000, event_type: "Sold" },
  { date: "2018-06-15", price: 310000, event_type: "Sold" },
  { date: "2025-01-02", price: 485000, event_type: "Listed" },
];

const taxHistory: TaxHistoryEntry[] = [
  { year: 2005, assessed_value: 240000, tax_amount: 2160 },
  { year: 2010, assessed_value: 258000, tax_amount: 2322 },
  { year: 2024, assessed_value: 412000, tax_amount: 4234 },
];

describe("SaleTaxHistoryChart", () => {
  it("renders the heading", () => {
    render(<SaleTaxHistoryChart saleHistory={saleHistory} taxHistory={taxHistory} />);
    expect(screen.getByText("Sale & Tax History")).toBeInTheDocument();
  });

  it("renders the chart container", () => {
    render(<SaleTaxHistoryChart saleHistory={saleHistory} taxHistory={taxHistory} />);
    expect(screen.getByTestId("responsive-container")).toBeInTheDocument();
  });

  it("renders chart components", () => {
    render(<SaleTaxHistoryChart saleHistory={saleHistory} taxHistory={taxHistory} />);
    expect(screen.getByTestId("composed-chart")).toBeInTheDocument();
    expect(screen.getByTestId("line")).toBeInTheDocument();
    expect(screen.getByTestId("area")).toBeInTheDocument();
  });

  it("shows empty state when no data", () => {
    render(<SaleTaxHistoryChart saleHistory={[]} taxHistory={[]} />);
    expect(screen.getByText("No history data available.")).toBeInTheDocument();
  });

  it("has aria-label for the section", () => {
    render(<SaleTaxHistoryChart saleHistory={saleHistory} taxHistory={taxHistory} />);
    expect(screen.getByLabelText("Sale and tax history")).toBeInTheDocument();
  });

  it("has no accessibility violations", async () => {
    const { container } = render(
      <SaleTaxHistoryChart saleHistory={saleHistory} taxHistory={taxHistory} />,
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
