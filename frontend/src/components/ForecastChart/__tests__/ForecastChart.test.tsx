import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import ForecastChart from "../ForecastChart";
import type { ForecastTimeline } from "../../../types";

vi.mock("recharts", () => {
  const MockResponsiveContainer = ({ children }: { children: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  );
  const MockComposedChart = ({
    children,
    data,
  }: {
    children: React.ReactNode;
    data: unknown[];
  }) => (
    <div data-testid="composed-chart" data-count={data.length}>
      {children}
    </div>
  );
  const MockLine = (props: Record<string, unknown>) => (
    <div data-testid={`line-${props.name}`} data-stroke={props.stroke} />
  );
  const MockArea = (props: Record<string, unknown>) => (
    <div data-testid={`area-${props.name}`} data-fill={props.fill} />
  );
  const MockScatter = (props: Record<string, unknown>) => (
    <div data-testid={`scatter-${props.name}`} />
  );
  const MockXAxis = () => <div data-testid="x-axis" />;
  const MockYAxis = () => <div data-testid="y-axis" />;
  const MockCartesianGrid = () => <div data-testid="cartesian-grid" />;
  const MockTooltip = () => <div data-testid="tooltip" />;
  const MockLegend = () => <div data-testid="legend" />;

  return {
    ResponsiveContainer: MockResponsiveContainer,
    ComposedChart: MockComposedChart,
    Line: MockLine,
    Area: MockArea,
    Scatter: MockScatter,
    XAxis: MockXAxis,
    YAxis: MockYAxis,
    CartesianGrid: MockCartesianGrid,
    Tooltip: MockTooltip,
    Legend: MockLegend,
  };
});

const mockTimeline: ForecastTimeline[] = [
  { date: "2026-03", value: 350000, low: 330000, high: 370000 },
  { date: "2026-06", value: 360000, low: 335000, high: 385000 },
  { date: "2026-09", value: 370000, low: 340000, high: 400000 },
];

const mockSaleHistory = [
  { date: "2024-01", price: 300000 },
  { date: "2025-06", price: 340000 },
];

describe("ForecastChart", () => {
  it("renders the chart with forecast data", () => {
    render(<ForecastChart timeline={mockTimeline} />);
    expect(screen.getByTestId("forecast-chart")).toBeInTheDocument();
    expect(screen.getByTestId("composed-chart")).toBeInTheDocument();
  });

  it("shows empty state when no data provided", () => {
    render(<ForecastChart timeline={[]} />);
    expect(screen.getByTestId("forecast-chart-empty")).toBeInTheDocument();
    expect(screen.getByText("No forecast data available")).toBeInTheDocument();
  });

  it("renders responsive container", () => {
    render(<ForecastChart timeline={mockTimeline} />);
    expect(screen.getByTestId("responsive-container")).toBeInTheDocument();
  });

  it("renders forecast line with orange stroke", () => {
    render(<ForecastChart timeline={mockTimeline} />);
    const forecastLine = screen.getByTestId("line-Forecast");
    expect(forecastLine).toHaveAttribute("data-stroke", "#f97316");
  });

  it("renders sale history line with blue stroke when saleHistory provided", () => {
    render(<ForecastChart timeline={mockTimeline} saleHistory={mockSaleHistory} />);
    const historyLine = screen.getByTestId("line-Sale Price");
    expect(historyLine).toHaveAttribute("data-stroke", "#3b82f6");
  });

  it("renders confidence band area", () => {
    render(<ForecastChart timeline={mockTimeline} />);
    expect(screen.getByTestId("area-Confidence Band")).toBeInTheDocument();
  });

  it("combines history and forecast data sorted by date", () => {
    render(<ForecastChart timeline={mockTimeline} saleHistory={mockSaleHistory} />);
    const chart = screen.getByTestId("composed-chart");
    // 2 history + 3 forecast = 5 data points
    expect(chart).toHaveAttribute("data-count", "5");
  });

  it("renders chart without sale history", () => {
    render(<ForecastChart timeline={mockTimeline} />);
    const chart = screen.getByTestId("composed-chart");
    expect(chart).toHaveAttribute("data-count", "3");
  });
});
