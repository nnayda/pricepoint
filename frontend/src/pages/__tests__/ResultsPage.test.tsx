import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import ResultsPage from "../ResultsPage";

const mockExecute = vi.fn();
const mockUseApi = vi.fn(() => ({
  data: null,
  loading: false,
  error: null,
  execute: mockExecute,
}));

vi.mock("../../hooks/useApi", () => ({
  useApi: (...args: unknown[]) => mockUseApi(...args),
}));

vi.mock("../../services/api", () => ({
  postForecast: vi.fn(),
}));

function renderResultsPage(address?: string) {
  const initialEntries = address
    ? [`/results?address=${encodeURIComponent(address)}`]
    : ["/results"];
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <ResultsPage />
    </MemoryRouter>,
  );
}

describe("ResultsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseApi.mockReturnValue({
      data: null,
      loading: false,
      error: null,
      execute: mockExecute,
    });
  });

  it("renders empty state when no address is provided", () => {
    renderResultsPage();
    expect(screen.getByText("No address provided")).toBeInTheDocument();
    expect(screen.getByText(/please search for a property/i)).toBeInTheDocument();
  });

  it("renders a link back to search in empty state", () => {
    renderResultsPage();
    const link = screen.getByRole("link", { name: /go to search/i });
    expect(link).toHaveAttribute("href", "/");
  });

  it("calls execute with the address from search params", () => {
    renderResultsPage("123 Main St");
    expect(mockExecute).toHaveBeenCalledWith({ address: "123 Main St" });
  });

  it("renders loading state", () => {
    mockUseApi.mockReturnValue({
      data: null,
      loading: true,
      error: null,
      execute: mockExecute,
    });
    renderResultsPage("123 Main St");
    expect(screen.getByText("Analyzing property data...")).toBeInTheDocument();
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("renders error state", () => {
    mockUseApi.mockReturnValue({
      data: null,
      loading: false,
      error: "Network error",
      execute: mockExecute,
    });
    renderResultsPage("123 Main St");
    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
    expect(screen.getByText("Network error")).toBeInTheDocument();
  });

  it("renders a link to try another address in error state", () => {
    mockUseApi.mockReturnValue({
      data: null,
      loading: false,
      error: "Network error",
      execute: mockExecute,
    });
    renderResultsPage("123 Main St");
    const link = screen.getByRole("link", { name: /try another address/i });
    expect(link).toHaveAttribute("href", "/");
  });

  it("renders forecast results", () => {
    mockUseApi.mockReturnValue({
      data: {
        address: "123 Main St, Philadelphia, PA",
        predicted_value: 350000,
        confidence_interval_low: 320000,
        confidence_interval_high: 380000,
        model_version: "v1.2.0",
      },
      loading: false,
      error: null,
      execute: mockExecute,
    });
    renderResultsPage("123 Main St");

    expect(screen.getByText("123 Main St, Philadelphia, PA")).toBeInTheDocument();
    expect(screen.getByText("$350,000")).toBeInTheDocument();
    expect(screen.getByText(/\$320,000/)).toBeInTheDocument();
    expect(screen.getByText(/\$380,000/)).toBeInTheDocument();
    expect(screen.getByText("v1.2.0")).toBeInTheDocument();
  });

  it("renders back to search link in results view", () => {
    mockUseApi.mockReturnValue({
      data: {
        address: "123 Main St, Philadelphia, PA",
        predicted_value: 350000,
        confidence_interval_low: 320000,
        confidence_interval_high: 380000,
        model_version: "v1.2.0",
      },
      loading: false,
      error: null,
      execute: mockExecute,
    });
    renderResultsPage("123 Main St");
    const link = screen.getByRole("link", { name: /back to search/i });
    expect(link).toHaveAttribute("href", "/");
  });

  it("applies design system styles to value card", () => {
    mockUseApi.mockReturnValue({
      data: {
        address: "123 Main St, Philadelphia, PA",
        predicted_value: 350000,
        confidence_interval_low: 320000,
        confidence_interval_high: 380000,
        model_version: "v1.2.0",
      },
      loading: false,
      error: null,
      execute: mockExecute,
    });
    renderResultsPage("123 Main St");

    const valueCard = screen.getByText("$350,000").closest("div");
    expect(valueCard?.className).toContain("rounded-md");
    expect(valueCard?.className).toContain("bg-bg-card");
    expect(valueCard?.className).toContain("shadow-soft");
  });

  it("applies design system styles to detail cards", () => {
    mockUseApi.mockReturnValue({
      data: {
        address: "123 Main St, Philadelphia, PA",
        predicted_value: 350000,
        confidence_interval_low: 320000,
        confidence_interval_high: 380000,
        model_version: "v1.2.0",
      },
      loading: false,
      error: null,
      execute: mockExecute,
    });
    renderResultsPage("123 Main St");

    const confidenceCard = screen.getByText("Confidence Range").closest("div");
    expect(confidenceCard?.className).toContain("rounded-md");
    expect(confidenceCard?.className).toContain("bg-bg-card");
    expect(confidenceCard?.className).toContain("shadow-soft");
  });
});
