import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import ForecastPage from "../ForecastPage";

// Mock the API service
vi.mock("../../services/api", () => ({
  postForecast: vi.fn(),
}));

function renderForecastPage() {
  return render(
    <MemoryRouter>
      <ForecastPage />
    </MemoryRouter>,
  );
}

describe("ForecastPage", () => {
  it("renders the heading", () => {
    renderForecastPage();
    expect(screen.getByText("Forecast")).toBeInTheDocument();
  });

  it("renders the address input", () => {
    renderForecastPage();
    expect(screen.getByPlaceholderText("Enter property address")).toBeInTheDocument();
  });

  it("renders the submit button", () => {
    renderForecastPage();
    expect(screen.getByRole("button", { name: "Get Forecast" })).toBeInTheDocument();
  });

  it("does not call API when address is empty", async () => {
    const { postForecast } = await import("../../services/api");
    renderForecastPage();
    const button = screen.getByRole("button", { name: "Get Forecast" });
    await userEvent.click(button);
    expect(postForecast).not.toHaveBeenCalled();
  });
});
