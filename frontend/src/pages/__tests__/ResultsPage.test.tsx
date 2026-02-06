import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { axe } from "vitest-axe";
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

vi.mock("react-leaflet", () => ({
  MapContainer: ({
    children,
    ...props
  }: {
    children: React.ReactNode;
    style?: React.CSSProperties;
  }) => (
    <div data-testid="map-container" style={props.style}>
      {children}
    </div>
  ),
  TileLayer: () => <div data-testid="tile-layer" />,
  Marker: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="marker">{children}</div>
  ),
  Popup: ({ children }: { children: React.ReactNode }) => <div data-testid="popup">{children}</div>,
}));

function renderResultsPage(address?: string, coords?: { lat: number; lon: number }) {
  let path = "/results";
  if (address) {
    path += `?address=${encodeURIComponent(address)}`;
    if (coords) {
      path += `&lat=${coords.lat}&lon=${coords.lon}`;
    }
  }
  return render(
    <MemoryRouter initialEntries={[path]}>
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

  it("applies glassmorphism styles to value card", () => {
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
    expect(valueCard?.className).toContain("rounded-lg");
    expect(valueCard?.className).toContain("bg-bg-card/80");
    expect(valueCard?.className).toContain("shadow-soft");
    expect(valueCard?.className).toContain("backdrop-blur-md");
  });

  it("applies glassmorphism styles to detail cards", () => {
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
    expect(confidenceCard?.className).toContain("rounded-lg");
    expect(confidenceCard?.className).toContain("bg-bg-card/80");
    expect(confidenceCard?.className).toContain("shadow-soft");
    expect(confidenceCard?.className).toContain("backdrop-blur-md");
  });

  it("applies glassmorphism styles to error card", () => {
    mockUseApi.mockReturnValue({
      data: null,
      loading: false,
      error: "Network error",
      execute: mockExecute,
    });
    renderResultsPage("123 Main St");

    const errorCard = screen.getByText("Something went wrong").closest("div");
    expect(errorCard?.className).toContain("rounded-lg");
    expect(errorCard?.className).toContain("bg-bg-card/80");
    expect(errorCard?.className).toContain("backdrop-blur-md");
  });

  it("applies glassmorphism styles to model version card", () => {
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

    const modelCard = screen.getByText("Model Version").closest("div");
    expect(modelCard?.className).toContain("rounded-lg");
    expect(modelCard?.className).toContain("bg-bg-card/80");
    expect(modelCard?.className).toContain("backdrop-blur-md");
  });

  it("renders map when lat and lon params are provided", () => {
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
    renderResultsPage("123 Main St", { lat: 39.9526, lon: -75.1652 });
    expect(screen.getByTestId("map-container")).toBeInTheDocument();
    expect(screen.getByTestId("marker")).toBeInTheDocument();
  });

  it("does not render map when lat and lon params are missing", () => {
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
    expect(screen.queryByTestId("map-container")).not.toBeInTheDocument();
  });

  it("has no axe accessibility violations in empty state", async () => {
    const { container } = renderResultsPage();
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  // -- Mobile responsiveness --

  it("uses responsive text sizes on results page", () => {
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

    const heading = screen.getByText("123 Main St, Philadelphia, PA");
    expect(heading.className).toContain("text-xl");
    expect(heading.className).toContain("sm:text-2xl");
  });

  it("uses responsive padding on value card", () => {
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
    expect(valueCard?.className).toContain("p-5");
    expect(valueCard?.className).toContain("sm:p-8");
  });

  it("uses responsive padding on detail cards", () => {
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
    expect(confidenceCard?.className).toContain("p-4");
    expect(confidenceCard?.className).toContain("sm:p-6");
  });

  it("address heading has break-words for long addresses on mobile", () => {
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

    const heading = screen.getByText("123 Main St, Philadelphia, PA");
    expect(heading.className).toContain("break-words");
  });

  it("uses responsive padding on error card", () => {
    mockUseApi.mockReturnValue({
      data: null,
      loading: false,
      error: "Network error",
      execute: mockExecute,
    });
    renderResultsPage("123 Main St");

    const errorCard = screen.getByText("Something went wrong").closest("div");
    expect(errorCard?.className).toContain("p-5");
    expect(errorCard?.className).toContain("sm:p-8");
  });

  it("has no axe accessibility violations in results state", async () => {
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
    const { container } = renderResultsPage("123 Main St", {
      lat: 39.9526,
      lon: -75.1652,
    });
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
