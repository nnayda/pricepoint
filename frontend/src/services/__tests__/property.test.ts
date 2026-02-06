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

const { getProperty, getCrime, getPois, getGreenspace, getUtilities } = await import("../property");

describe("Property service", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("getProperty", () => {
    it("calls GET /api/property with correct params", async () => {
      const mockData = { property: { address: "123 Main St" } };
      mockAxiosInstance.get.mockResolvedValue({ data: mockData });

      const result = await getProperty(35.79, -78.78, "123 Main St");

      expect(mockAxiosInstance.get).toHaveBeenCalledWith("/api/property", {
        params: { lat: 35.79, lon: -78.78, address: "123 Main St" },
      });
      expect(result).toEqual(mockData);
    });

    it("returns the data from the response", async () => {
      const mockData = { property: { address: "Test" }, valuation: {} };
      mockAxiosInstance.get.mockResolvedValue({ data: mockData });

      const result = await getProperty(0, 0, "Test");
      expect(result).toEqual(mockData);
    });

    it("propagates errors from axios", async () => {
      mockAxiosInstance.get.mockRejectedValue(new Error("Network Error"));

      await expect(getProperty(0, 0, "Test")).rejects.toThrow("Network Error");
    });
  });

  describe("getCrime", () => {
    it("calls GET /api/crime with lat and lon", async () => {
      const mockData = { heatmap: [], incidents: [], metrics: {} };
      mockAxiosInstance.get.mockResolvedValue({ data: mockData });

      const result = await getCrime(35.79, -78.78);

      expect(mockAxiosInstance.get).toHaveBeenCalledWith("/api/crime", {
        params: { lat: 35.79, lon: -78.78 },
      });
      expect(result).toEqual(mockData);
    });

    it("includes radius_miles when provided", async () => {
      mockAxiosInstance.get.mockResolvedValue({ data: {} });

      await getCrime(35.79, -78.78, 5.0);

      expect(mockAxiosInstance.get).toHaveBeenCalledWith("/api/crime", {
        params: { lat: 35.79, lon: -78.78, radius_miles: 5.0 },
      });
    });

    it("omits radius_miles when undefined", async () => {
      mockAxiosInstance.get.mockResolvedValue({ data: {} });

      await getCrime(35.79, -78.78);

      const callParams = mockAxiosInstance.get.mock.calls[0][1].params;
      expect(callParams).not.toHaveProperty("radius_miles");
    });
  });

  describe("getPois", () => {
    it("calls GET /api/pois with lat and lon", async () => {
      const mockData = { pois: [] };
      mockAxiosInstance.get.mockResolvedValue({ data: mockData });

      const result = await getPois(35.79, -78.78);

      expect(mockAxiosInstance.get).toHaveBeenCalledWith("/api/pois", {
        params: { lat: 35.79, lon: -78.78 },
      });
      expect(result).toEqual(mockData);
    });

    it("includes radius_miles when provided", async () => {
      mockAxiosInstance.get.mockResolvedValue({ data: {} });

      await getPois(35.79, -78.78, 3.0);

      expect(mockAxiosInstance.get).toHaveBeenCalledWith("/api/pois", {
        params: { lat: 35.79, lon: -78.78, radius_miles: 3.0 },
      });
    });

    it("omits radius_miles when undefined", async () => {
      mockAxiosInstance.get.mockResolvedValue({ data: {} });

      await getPois(35.79, -78.78);

      const callParams = mockAxiosInstance.get.mock.calls[0][1].params;
      expect(callParams).not.toHaveProperty("radius_miles");
    });
  });

  describe("getGreenspace", () => {
    it("calls GET /api/greenspace with lat and lon", async () => {
      const mockData = { features: [], metrics: {} };
      mockAxiosInstance.get.mockResolvedValue({ data: mockData });

      const result = await getGreenspace(35.79, -78.78);

      expect(mockAxiosInstance.get).toHaveBeenCalledWith("/api/greenspace", {
        params: { lat: 35.79, lon: -78.78 },
      });
      expect(result).toEqual(mockData);
    });

    it("includes radius_miles when provided", async () => {
      mockAxiosInstance.get.mockResolvedValue({ data: {} });

      await getGreenspace(35.79, -78.78, 2.0);

      expect(mockAxiosInstance.get).toHaveBeenCalledWith("/api/greenspace", {
        params: { lat: 35.79, lon: -78.78, radius_miles: 2.0 },
      });
    });

    it("omits radius_miles when undefined", async () => {
      mockAxiosInstance.get.mockResolvedValue({ data: {} });

      await getGreenspace(35.79, -78.78);

      const callParams = mockAxiosInstance.get.mock.calls[0][1].params;
      expect(callParams).not.toHaveProperty("radius_miles");
    });
  });

  describe("getUtilities", () => {
    it("calls GET /api/utilities with lat and lon", async () => {
      const mockData = { features: [], metrics: {} };
      mockAxiosInstance.get.mockResolvedValue({ data: mockData });

      const result = await getUtilities(35.79, -78.78);

      expect(mockAxiosInstance.get).toHaveBeenCalledWith("/api/utilities", {
        params: { lat: 35.79, lon: -78.78 },
      });
      expect(result).toEqual(mockData);
    });

    it("includes radius_miles when provided", async () => {
      mockAxiosInstance.get.mockResolvedValue({ data: {} });

      await getUtilities(35.79, -78.78, 1.0);

      expect(mockAxiosInstance.get).toHaveBeenCalledWith("/api/utilities", {
        params: { lat: 35.79, lon: -78.78, radius_miles: 1.0 },
      });
    });

    it("omits radius_miles when undefined", async () => {
      mockAxiosInstance.get.mockResolvedValue({ data: {} });

      await getUtilities(35.79, -78.78);

      const callParams = mockAxiosInstance.get.mock.calls[0][1].params;
      expect(callParams).not.toHaveProperty("radius_miles");
    });
  });
});
