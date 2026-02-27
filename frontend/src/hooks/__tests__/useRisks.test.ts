import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useRisks } from "../useRisks";
import { getRisksData } from "../../services/property";
import type { RisksApiResponse } from "../../types";

vi.mock("../../services/property", () => ({
  getRisksData: vi.fn(),
}));

const mockGetRisksData = vi.mocked(getRisksData);

const mockResponse: RisksApiResponse = {
  features: [
    {
      id: "RB-C-10",
      name: "AT&T Tower",
      infrastructure_type: "cell_tower",
      severity: "Safe",
      distance_miles: 0.8,
      lat: 35.8,
      lon: -78.77,
      detail: "Cell Tower — outside risk zones",
    },
    {
      id: "RB-P-30",
      name: "Shearon Harris",
      infrastructure_type: "power_plant",
      severity: "Concern",
      distance_miles: 1.2,
      lat: 35.785,
      lon: -78.769,
      detail: "Power Plant — within critical risk zone",
    },
  ],
};

describe("useRisks hook", () => {
  beforeEach(() => {
    mockGetRisksData.mockReset();
  });

  it("starts in loading state", () => {
    mockGetRisksData.mockReturnValue(new Promise(() => {}));
    const { result } = renderHook(() => useRisks(35.79, -78.78));
    expect(result.current.loading).toBe(true);
    expect(result.current.data.features).toEqual([]);
  });

  it("returns data on success", async () => {
    mockGetRisksData.mockResolvedValue(mockResponse);
    const { result } = renderHook(() => useRisks(35.79, -78.78));

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.data.features).toHaveLength(2);
    expect(result.current.data.features[0].name).toBe("AT&T Tower");
  });

  it("returns empty data on error", async () => {
    mockGetRisksData.mockRejectedValue(new Error("Network error"));
    const { result } = renderHook(() => useRisks(35.79, -78.78));

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.data.features).toEqual([]);
  });

  it("calls getRisksData with correct params", async () => {
    mockGetRisksData.mockResolvedValue(mockResponse);
    renderHook(() => useRisks(35.79, -78.78, 5));

    await waitFor(() => expect(mockGetRisksData).toHaveBeenCalledWith(35.79, -78.78, 5));
  });

  it("refetches when coords change", async () => {
    mockGetRisksData.mockResolvedValue(mockResponse);
    const { rerender } = renderHook(({ lat, lon }) => useRisks(lat, lon), {
      initialProps: { lat: 35.79, lon: -78.78 },
    });

    await waitFor(() => expect(mockGetRisksData).toHaveBeenCalledTimes(1));

    rerender({ lat: 36.0, lon: -79.0 });

    await waitFor(() => expect(mockGetRisksData).toHaveBeenCalledTimes(2));
  });
});
