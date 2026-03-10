import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { usePois } from "../usePois";
import { getPois } from "../../services/property";
import type { PoisResponse } from "../../types";

vi.mock("../../services/property", () => ({
  getPois: vi.fn(),
}));

const mockGetPois = vi.mocked(getPois);

const mockResponse: PoisResponse = {
  pois: [
    {
      id: "OVERTURE-100",
      name: "Publix",
      category: "Grocery",
      lat: 35.79,
      lon: -78.78,
      distance_miles: 0.4,
      drive_minutes: 1,
      subcategory: "grocery",
      address: "100 Market St",
    },
    {
      id: "HEALTHCARE-1",
      name: "WakeMed",
      category: "Healthcare",
      lat: 35.793,
      lon: -78.783,
      distance_miles: 1.5,
      drive_minutes: 5,
    },
  ],
};

describe("usePois hook", () => {
  beforeEach(() => {
    mockGetPois.mockReset();
  });

  it("starts in loading state when coords provided", () => {
    mockGetPois.mockReturnValue(new Promise(() => {}));
    const { result } = renderHook(() => usePois(35.79, -78.78));
    expect(result.current.loading).toBe(true);
    expect(result.current.data).toBeNull();
  });

  it("does not fetch when lat is null", () => {
    const { result } = renderHook(() => usePois(null, -78.78));
    expect(result.current.loading).toBe(false);
    expect(result.current.data).toBeNull();
    expect(mockGetPois).not.toHaveBeenCalled();
  });

  it("does not fetch when lon is null", () => {
    const { result } = renderHook(() => usePois(35.79, null));
    expect(result.current.loading).toBe(false);
    expect(result.current.data).toBeNull();
    expect(mockGetPois).not.toHaveBeenCalled();
  });

  it("returns data on success", async () => {
    mockGetPois.mockResolvedValue(mockResponse);
    const { result } = renderHook(() => usePois(35.79, -78.78));

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.data).toEqual(mockResponse);
    expect(result.current.data!.pois).toHaveLength(2);
    expect(result.current.data!.pois[0].name).toBe("Publix");
    expect(result.current.error).toBeNull();
  });

  it("returns error on failure", async () => {
    mockGetPois.mockRejectedValue(new Error("Network error"));
    const { result } = renderHook(() => usePois(35.79, -78.78));

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.data).toBeNull();
    expect(result.current.error).toBe("Failed to load POI data");
  });

  it("calls getPois with correct params", async () => {
    mockGetPois.mockResolvedValue(mockResponse);
    renderHook(() => usePois(35.79, -78.78));

    await waitFor(() => expect(mockGetPois).toHaveBeenCalledWith(35.79, -78.78));
  });

  it("refetches when coords change", async () => {
    mockGetPois.mockResolvedValue(mockResponse);
    const { rerender } = renderHook(({ lat, lon }) => usePois(lat, lon), {
      initialProps: { lat: 35.79 as number | null, lon: -78.78 as number | null },
    });

    await waitFor(() => expect(mockGetPois).toHaveBeenCalledTimes(1));

    rerender({ lat: 36.0, lon: -79.0 });

    await waitFor(() => expect(mockGetPois).toHaveBeenCalledTimes(2));
  });
});
