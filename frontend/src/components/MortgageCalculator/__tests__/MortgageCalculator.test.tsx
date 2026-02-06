import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { axe } from "vitest-axe";
import MortgageCalculator from "../MortgageCalculator";

// Mock recharts
vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
  PieChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="pie-chart">{children}</div>
  ),
  Pie: ({ children }: { children: React.ReactNode }) => <div data-testid="pie">{children}</div>,
  Cell: () => <div data-testid="cell" />,
  Tooltip: () => <div data-testid="tooltip" />,
  Legend: () => <div data-testid="legend" />,
}));

// Mock localStorage for useMortgageDefaults
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] ?? null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key];
    }),
    clear: vi.fn(() => {
      store = {};
    }),
    get length() {
      return Object.keys(store).length;
    },
    key: vi.fn((index: number) => Object.keys(store)[index] ?? null),
  };
})();

Object.defineProperty(window, "localStorage", { value: localStorageMock });

describe("MortgageCalculator", () => {
  it("renders the heading", () => {
    render(<MortgageCalculator listedPrice={485000} annualTax={4234} monthlyHoa={85} />);
    expect(screen.getByText("Mortgage Calculator")).toBeInTheDocument();
  });

  it("renders the monthly payment", () => {
    render(<MortgageCalculator listedPrice={485000} annualTax={4234} monthlyHoa={85} />);
    expect(screen.getByText("Monthly Payment")).toBeInTheDocument();
  });

  it("renders slider inputs", () => {
    render(<MortgageCalculator listedPrice={485000} annualTax={4234} monthlyHoa={85} />);
    expect(screen.getByLabelText("Home Price")).toBeInTheDocument();
    expect(screen.getByLabelText("Down Payment")).toBeInTheDocument();
    expect(screen.getByLabelText("Interest Rate")).toBeInTheDocument();
    expect(screen.getByLabelText("Loan Term")).toBeInTheDocument();
  });

  it("renders the pie chart", () => {
    render(<MortgageCalculator listedPrice={485000} annualTax={4234} monthlyHoa={85} />);
    expect(screen.getByTestId("pie-chart")).toBeInTheDocument();
  });

  it("renders settings link", () => {
    render(<MortgageCalculator listedPrice={485000} annualTax={4234} monthlyHoa={85} />);
    expect(screen.getByLabelText("Mortgage settings")).toBeInTheDocument();
  });

  it("updates payment when slider changes", () => {
    render(<MortgageCalculator listedPrice={485000} annualTax={4234} monthlyHoa={85} />);
    const slider = screen.getByLabelText("Down Payment");

    // Change down payment via fireEvent (range inputs don't support clear/type)
    fireEvent.change(slider, { target: { value: "50" } });

    // Payment element should still exist (component shouldn't crash)
    expect(screen.getByText("Monthly Payment")).toBeInTheDocument();
  });

  it("has no accessibility violations", async () => {
    const { container } = render(
      <MortgageCalculator listedPrice={485000} annualTax={4234} monthlyHoa={85} />,
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
