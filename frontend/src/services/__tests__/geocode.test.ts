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

const { getGeocode } = await import("../geocode");

describe("Geocode service", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("calls GET /api/geocode with q param", async () => {
    const response = {
      results: [
        {
          display_name: "123 Main St",
          lat: 40.7128,
          lon: -74.006,
          place_id: 1,
          osm_type: "node",
          osm_id: 100,
          boundingbox: [40.71, 40.72, -74.01, -74.0],
        },
      ],
      cached: false,
    };
    mockAxiosInstance.get.mockResolvedValue({ data: response });

    const result = await getGeocode("123 Main St");

    expect(mockAxiosInstance.get).toHaveBeenCalledWith("/api/geocode", {
      params: { q: "123 Main St" },
    });
    expect(result).toEqual(response);
  });

  it("passes limit param when provided", async () => {
    const response = { results: [], cached: false };
    mockAxiosInstance.get.mockResolvedValue({ data: response });

    const result = await getGeocode("test", 5);

    expect(mockAxiosInstance.get).toHaveBeenCalledWith("/api/geocode", {
      params: { q: "test", limit: 5 },
    });
    expect(result).toEqual(response);
  });
});
