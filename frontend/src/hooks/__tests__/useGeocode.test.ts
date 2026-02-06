import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useGeocode } from "../useGeocode";
import { getGeocode } from "../../services/geocode";
import type { GeocodeResponse } from "../../types";

vi.mock("../../services/geocode", () => ({
  getGeocode: vi.fn(),
}));

const mockGetGeocode = vi.mocked(getGeocode);

const mockResponse: GeocodeResponse = {
  results: [
    {
      display_name: "123 Main St, Springfield, IL",
      lat: 39.7817,
      lon: -89.6501,
      place_id: 1001,
      osm_type: "way",
      osm_id: 5001,
      boundingbox: [39.78, 39.79, -89.66, -89.64],
    },
  ],
  cached: false,
};

describe("useGeocode hook", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    mockGetGeocode.mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("returns empty results for short queries", () => {
    const { result } = renderHook(() => useGeocode("ab"));

    act(() => {
      vi.advanceTimersByTime(300);
    });

    expect(result.current.results).toEqual([]);
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
    expect(mockGetGeocode).not.toHaveBeenCalled();
  });

  it("fetches geocode results after debounce for valid queries", async () => {
    mockGetGeocode.mockResolvedValue(mockResponse);

    const { result } = renderHook(() => useGeocode("123 Main"));

    await act(async () => {
      vi.advanceTimersByTime(300);
    });

    expect(mockGetGeocode).toHaveBeenCalledWith("123 Main");
    expect(result.current.results).toEqual(mockResponse.results);
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it("does not fetch before debounce delay elapses on query change", async () => {
    mockGetGeocode.mockResolvedValue(mockResponse);

    const { rerender } = renderHook(({ query }) => useGeocode(query), {
      initialProps: { query: "ab" },
    });

    rerender({ query: "123 Main" });

    act(() => {
      vi.advanceTimersByTime(299);
    });

    expect(mockGetGeocode).not.toHaveBeenCalled();

    await act(async () => {
      vi.advanceTimersByTime(1);
    });

    expect(mockGetGeocode).toHaveBeenCalledWith("123 Main");
  });

  it("debounces rapid query changes", async () => {
    mockGetGeocode.mockResolvedValue(mockResponse);

    const { rerender } = renderHook(({ query }) => useGeocode(query), {
      initialProps: { query: "" },
    });

    rerender({ query: "1" });
    act(() => {
      vi.advanceTimersByTime(100);
    });

    rerender({ query: "123" });
    act(() => {
      vi.advanceTimersByTime(100);
    });

    rerender({ query: "123 Main St" });

    await act(async () => {
      vi.advanceTimersByTime(300);
    });

    expect(mockGetGeocode).toHaveBeenCalledTimes(1);
    expect(mockGetGeocode).toHaveBeenCalledWith("123 Main St");
  });

  it("sets error on API failure", async () => {
    mockGetGeocode.mockRejectedValue(new Error("Network error"));

    const { result } = renderHook(() => useGeocode("123 Main"));

    await act(async () => {
      vi.advanceTimersByTime(300);
    });

    expect(result.current.results).toEqual([]);
    expect(result.current.error).toBe("Network error");
    expect(result.current.loading).toBe(false);
  });

  it("does not re-fetch for the same debounced query", async () => {
    mockGetGeocode.mockResolvedValue(mockResponse);

    const { rerender } = renderHook(({ query }) => useGeocode(query), {
      initialProps: { query: "123 Main" },
    });

    await act(async () => {
      vi.advanceTimersByTime(300);
    });

    expect(mockGetGeocode).toHaveBeenCalledTimes(1);

    // Rerender with same query
    rerender({ query: "123 Main" });

    await act(async () => {
      vi.advanceTimersByTime(300);
    });

    expect(mockGetGeocode).toHaveBeenCalledTimes(1);
  });
});
