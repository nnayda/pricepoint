import { describe, it, expect, vi, beforeEach } from "vitest";
import axios from "axios";

vi.mock("axios");

const mockAxiosInstance = {
  get: vi.fn(),
  post: vi.fn(),
  delete: vi.fn(),
  interceptors: {
    request: { use: vi.fn() },
    response: { use: vi.fn() },
  },
};

vi.mocked(axios.create).mockReturnValue(mockAxiosInstance as never);

const { getSavedProperties, saveProperty, deleteSavedProperty } = await import("../saved");

describe("saved property service", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("getSavedProperties", () => {
    it("calls GET /api/saved with auth header", async () => {
      const items = [
        {
          id: 1,
          listing_id: 42,
          notes: null,
          created_at: "2025-01-01",
          listing_address: "123 Main St",
        },
      ];
      mockAxiosInstance.get.mockResolvedValue({ data: items });

      const result = await getSavedProperties("tok123");
      expect(mockAxiosInstance.get).toHaveBeenCalledWith("/api/saved", {
        headers: { Authorization: "Bearer tok123" },
      });
      expect(result).toEqual(items);
    });
  });

  describe("saveProperty", () => {
    it("calls POST /api/saved with listing_id and auth header", async () => {
      const saved = {
        id: 1,
        listing_id: 42,
        notes: null,
        created_at: "2025-01-01",
        listing_address: "123 Main St",
      };
      mockAxiosInstance.post.mockResolvedValue({ data: saved });

      const result = await saveProperty("tok123", 42);
      expect(mockAxiosInstance.post).toHaveBeenCalledWith(
        "/api/saved",
        { listing_id: 42, notes: null },
        { headers: { Authorization: "Bearer tok123" } },
      );
      expect(result).toEqual(saved);
    });

    it("passes notes when provided", async () => {
      const saved = {
        id: 1,
        listing_id: 42,
        notes: "Great house",
        created_at: "2025-01-01",
        listing_address: null,
      };
      mockAxiosInstance.post.mockResolvedValue({ data: saved });

      await saveProperty("tok123", 42, "Great house");
      expect(mockAxiosInstance.post).toHaveBeenCalledWith(
        "/api/saved",
        { listing_id: 42, notes: "Great house" },
        { headers: { Authorization: "Bearer tok123" } },
      );
    });
  });

  describe("deleteSavedProperty", () => {
    it("calls DELETE /api/saved/:id with auth header", async () => {
      mockAxiosInstance.delete.mockResolvedValue({ status: 204 });

      await deleteSavedProperty("tok123", 7);
      expect(mockAxiosInstance.delete).toHaveBeenCalledWith("/api/saved/7", {
        headers: { Authorization: "Bearer tok123" },
      });
    });
  });
});
