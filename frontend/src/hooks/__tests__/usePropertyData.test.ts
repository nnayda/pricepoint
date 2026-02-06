import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";

const mockGetProperty = vi.fn();

vi.mock("../../services/property", () => ({
  getProperty: (...args: unknown[]) => mockGetProperty(...args),
}));

const { usePropertyData } = await import("../usePropertyData");

describe("usePropertyData", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns initial state with no data", () => {
    const { result } = renderHook(() => usePropertyData(0, 0, ""));
    expect(result.current.data).toBeNull();
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it("does not fetch when address is empty", () => {
    renderHook(() => usePropertyData(35.79, -78.78, ""));
    expect(mockGetProperty).not.toHaveBeenCalled();
  });

  it("fetches data when address is provided", async () => {
    const mockData = { property: { address: "123 Main St" } };
    mockGetProperty.mockResolvedValue(mockData);

    const { result } = renderHook(() => usePropertyData(35.79, -78.78, "123 Main St"));

    await waitFor(() => {
      expect(result.current.data).toEqual(mockData);
    });
    expect(mockGetProperty).toHaveBeenCalledWith(35.79, -78.78, "123 Main St");
  });

  it("sets loading state while fetching", async () => {
    let resolvePromise: (value: unknown) => void;
    mockGetProperty.mockReturnValue(
      new Promise((resolve) => {
        resolvePromise = resolve;
      }),
    );

    const { result } = renderHook(() => usePropertyData(35.79, -78.78, "Test"));

    await waitFor(() => {
      expect(result.current.loading).toBe(true);
    });

    resolvePromise!({ property: {} });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });
  });

  it("sets error on fetch failure", async () => {
    mockGetProperty.mockRejectedValue(new Error("API Error"));

    const { result } = renderHook(() => usePropertyData(35.79, -78.78, "Test"));

    await waitFor(() => {
      expect(result.current.error).toBe("API Error");
    });
    expect(result.current.data).toBeNull();
    expect(result.current.loading).toBe(false);
  });

  it("refetches when params change", async () => {
    mockGetProperty.mockResolvedValue({ property: {} });

    const { rerender } = renderHook(({ lat, lon, address }) => usePropertyData(lat, lon, address), {
      initialProps: { lat: 35.79, lon: -78.78, address: "First" },
    });

    await waitFor(() => {
      expect(mockGetProperty).toHaveBeenCalledTimes(1);
    });

    rerender({ lat: 36.0, lon: -79.0, address: "Second" });

    await waitFor(() => {
      expect(mockGetProperty).toHaveBeenCalledTimes(2);
    });
    expect(mockGetProperty).toHaveBeenLastCalledWith(36.0, -79.0, "Second");
  });

  it("does not refetch when params are the same", async () => {
    mockGetProperty.mockResolvedValue({ property: {} });

    const { rerender } = renderHook(({ lat, lon, address }) => usePropertyData(lat, lon, address), {
      initialProps: { lat: 35.79, lon: -78.78, address: "Same" },
    });

    await waitFor(() => {
      expect(mockGetProperty).toHaveBeenCalledTimes(1);
    });

    rerender({ lat: 35.79, lon: -78.78, address: "Same" });

    // Still only called once
    expect(mockGetProperty).toHaveBeenCalledTimes(1);
  });
});
