import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import ForecastPage from "../ForecastPage";
import type { ForecastResponse } from "../../types";

const mockExecute = vi.fn();
let mockState: {
  data: ForecastResponse | null;
  loading: boolean;
  error: string | null;
};

vi.mock("../../hooks/useApi", () => ({
  useApi: () => ({
    ...mockState,
    execute: mockExecute,
  }),
}));

function renderPage() {
  return render(
    <MemoryRouter>
      <ForecastPage />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  mockState = { data: null, loading: false, error: null };
});

describe("ForecastPage", () => {
  it("renders all form fields", () => {
    renderPage();
    expect(screen.getByPlaceholderText("Address")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("City")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("State")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Zip Code")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Get Forecast" })).toBeInTheDocument();
  });

  it("does not submit when address is empty", async () => {
    renderPage();
    await userEvent.click(screen.getByRole("button", { name: "Get Forecast" }));
    expect(mockExecute).not.toHaveBeenCalled();
  });

  it("submits with address and optional fields", async () => {
    renderPage();
    await userEvent.type(screen.getByPlaceholderText("Address"), "123 Main St");
    await userEvent.type(screen.getByPlaceholderText("City"), "Raleigh");
    await userEvent.type(screen.getByPlaceholderText("State"), "NC");
    await userEvent.type(screen.getByPlaceholderText("Zip Code"), "27601");
    await userEvent.click(screen.getByRole("button", { name: "Get Forecast" }));
    expect(mockExecute).toHaveBeenCalledWith({
      address: "123 Main St",
      city: "Raleigh",
      state: "NC",
      zip_code: "27601",
    });
  });

  it("shows loading spinner during submission", () => {
    mockState = { data: null, loading: true, error: null };
    renderPage();
    expect(screen.getByRole("status")).toBeInTheDocument();
    expect(screen.getByText("Loading forecast...")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Loading..." })).toBeDisabled();
  });

  it("displays prediction result with formatted currency", () => {
    mockState = {
      data: {
        address: "123 Main St, Raleigh, NC 27601",
        predicted_value: 345000,
        confidence_interval_low: 320000,
        confidence_interval_high: 370000,
        model_version: "v1.2.0",
      },
      loading: false,
      error: null,
    };
    renderPage();
    expect(screen.getByText("$345,000")).toBeInTheDocument();
    expect(screen.getByText("123 Main St, Raleigh, NC 27601")).toBeInTheDocument();
    expect(screen.getByText("Model version: v1.2.0")).toBeInTheDocument();
  });

  it("shows confidence interval range", () => {
    mockState = {
      data: {
        address: "123 Main St",
        predicted_value: 345000,
        confidence_interval_low: 320000,
        confidence_interval_high: 370000,
        model_version: "v1.2.0",
      },
      loading: false,
      error: null,
    };
    renderPage();
    const interval = screen.getByTestId("confidence-interval");
    expect(interval.textContent).toContain("$320,000");
    expect(interval.textContent).toContain("$370,000");
  });

  it("shows error state when model is unavailable", () => {
    mockState = {
      data: {
        address: "123 Main St",
        predicted_value: 0,
        confidence_interval_low: 0,
        confidence_interval_high: 0,
        model_version: "unavailable",
      },
      loading: false,
      error: null,
    };
    renderPage();
    expect(screen.getByText("Forecast Unavailable")).toBeInTheDocument();
    expect(
      screen.getByText("The prediction model is currently unavailable. Please try again later."),
    ).toBeInTheDocument();
    expect(screen.queryByText("$0")).not.toBeInTheDocument();
  });

  it("shows API error message", () => {
    mockState = { data: null, loading: false, error: "Network error" };
    renderPage();
    expect(screen.getByRole("alert")).toHaveTextContent("Error: Network error");
  });

  it("submits with only address when optional fields are empty", async () => {
    renderPage();
    await userEvent.type(screen.getByPlaceholderText("Address"), "456 Oak Ave");
    await userEvent.click(screen.getByRole("button", { name: "Get Forecast" }));
    expect(mockExecute).toHaveBeenCalledWith({
      address: "456 Oak Ave",
    });
  });
});
