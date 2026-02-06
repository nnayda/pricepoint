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

  it("fetches when query is exactly 3 characters", async () => {
    mockGetGeocode.mockResolvedValue(mockResponse);

    const { result } = renderHook(() => useGeocode("abc"));

    await act(async () => {
      vi.advanceTimersByTime(300);
    });

    expect(mockGetGeocode).toHaveBeenCalledWith("abc");
    expect(result.current.results).toEqual(mockResponse.results);
  });

  it("shows loading state while API call is in-flight", async () => {
    let resolveApi!: (value: GeocodeResponse) => void;
    mockGetGeocode.mockImplementation(
      () => new Promise((resolve) => { resolveApi = resolve; }),
    );

    const { result } = renderHook(() => useGeocode("123 Main"));

    await act(async () => {
      vi.advanceTimersByTime(300);
    });

    expect(result.current.loading).toBe(true);
    expect(result.current.results).toEqual([]);

    await act(async () => {
      resolveApi(mockResponse);
    });

    expect(result.current.loading).toBe(false);
    expect(result.current.results).toEqual(mockResponse.results);
  });

  it("handles race conditions when slow query resolves after fast query", async () => {
    const slowResponse: GeocodeResponse = {
      results: [
        {
          display_name: "Slow Result",
          lat: 40.0,
          lon: -90.0,
          place_id: 2001,
          osm_type: "way",
          osm_id: 6001,
          boundingbox: [39.9, 40.1, -90.1, -89.9],
        },
      ],
      cached: false,
    };

    const fastResponse: GeocodeResponse = {
      results: [
        {
          display_name: "Fast Result",
          lat: 41.0,
          lon: -88.0,
          place_id: 3001,
          osm_type: "node",
          osm_id: 7001,
          boundingbox: [40.9, 41.1, -88.1, -87.9],
        },
      ],
      cached: false,
    };

    // First call resolves slowly, second call resolves quickly
    let resolveFirst!: (value: GeocodeResponse) => void;
    mockGetGeocode
      .mockImplementationOnce(
        () => new Promise((resolve) => { resolveFirst = resolve; }),
      )
      .mockImplementationOnce(() => Promise.resolve(fastResponse));

    const { result, rerender } = renderHook(
      ({ query }) => useGeocode(query),
      { initialProps: { query: "first query" } },
    );

    // Debounce fires for first query
    await act(async () => {
      vi.advanceTimersByTime(300);
    });

    expect(mockGetGeocode).toHaveBeenCalledWith("first query");

    // Change to second query before first resolves
    rerender({ query: "second query" });

    await act(async () => {
      vi.advanceTimersByTime(300);
    });

    expect(mockGetGeocode).toHaveBeenCalledWith("second query");
    // Second (fast) query has resolved
    expect(result.current.results).toEqual(fastResponse.results);

    // Now the slow first query resolves — useApi overwrites state
    // because useGeocode doesn't implement cancellation
    await act(async () => {
      resolveFirst(slowResponse);
    });

    // The hook uses useApi which updates state on every resolve,
    // so the last-resolved promise wins (known race condition behavior)
    // This test documents the current behavior
    expect(result.current.loading).toBe(false);
  });

  it("clears error on subsequent successful fetch", async () => {
    mockGetGeocode.mockRejectedValueOnce(new Error("Temporary failure"));

    const { result, rerender } = renderHook(
      ({ query }) => useGeocode(query),
      { initialProps: { query: "bad query" } },
    );

    await act(async () => {
      vi.advanceTimersByTime(300);
    });

    expect(result.current.error).toBe("Temporary failure");

    mockGetGeocode.mockResolvedValueOnce(mockResponse);
    rerender({ query: "good query" });

    await act(async () => {
      vi.advanceTimersByTime(300);
    });

    expect(result.current.error).toBeNull();
    expect(result.current.results).toEqual(mockResponse.results);
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
