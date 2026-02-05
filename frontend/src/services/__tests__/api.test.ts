import { describe, it, expect, vi, beforeEach } from "vitest";
import axios from "axios";

vi.mock("axios");

const mockAxiosInstance = {
  get: vi.fn(),
  post: vi.fn(),
  interceptors: {
    request: { use: vi.fn() },
    response: { use: vi.fn() },
  },
};

vi.mocked(axios.create).mockReturnValue(mockAxiosInstance as never);

// Re-import to pick up the mock
const { getHealth: getHealthFresh, postForecast: postForecastFresh } = await import("../api");

describe("API service", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("getHealth calls GET /health", async () => {
    mockAxiosInstance.get.mockResolvedValue({ data: { status: "ok" } });
    const result = await getHealthFresh();
    expect(mockAxiosInstance.get).toHaveBeenCalledWith("/health");
    expect(result).toEqual({ status: "ok" });
  });

  it("postForecast calls POST /api/forecast", async () => {
    const request = { address: "123 Main St" };
    const response = {
      address: "123 Main St",
      predicted_value: 350000,
      confidence_interval_low: 300000,
      confidence_interval_high: 400000,
      model_version: "v1",
    };
    mockAxiosInstance.post.mockResolvedValue({ data: response });
    const result = await postForecastFresh(request);
    expect(mockAxiosInstance.post).toHaveBeenCalledWith("/api/forecast", request);
    expect(result).toEqual(response);
  });
});
