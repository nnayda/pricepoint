import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useSavedPois, useSavedPoisNearby, usePoiAutocomplete } from "../useSavedPois";

const mockGetSavedPois = vi.fn();
const mockCreateSavedPoi = vi.fn();
const mockDeleteSavedPoi = vi.fn();
const mockGetSavedPoisNearby = vi.fn();
const mockAutocompletePoIs = vi.fn();

vi.mock("../../services/savedPois", () => ({
  getSavedPois: (...args: unknown[]) => mockGetSavedPois(...args),
  createSavedPoi: (...args: unknown[]) => mockCreateSavedPoi(...args),
  deleteSavedPoi: (...args: unknown[]) => mockDeleteSavedPoi(...args),
  getSavedPoisNearby: (...args: unknown[]) => mockGetSavedPoisNearby(...args),
  autocompletePoIs: (...args: unknown[]) => mockAutocompletePoIs(...args),
}));

const FAKE_TOKEN = "test-token";

function setToken() {
  localStorage.setItem("pricepoint-auth-token", FAKE_TOKEN);
}

function makeSavedPoi(id: number, name: string) {
  return {
    id,
    match_type: "brand" as const,
    match_value: name,
    display_name: name,
    category: "store",
    created_at: "2025-06-01T12:00:00Z",
  };
}

describe("useSavedPois", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  afterEach(() => {
    localStorage.clear();
  });

  it("does not fetch when unauthenticated", () => {
    renderHook(() => useSavedPois());
    expect(mockGetSavedPois).not.toHaveBeenCalled();
  });

  it("fetches saved pois when authenticated", async () => {
    setToken();
    const items = [makeSavedPoi(1, "Costco")];
    mockGetSavedPois.mockResolvedValue(items);

    const { result } = renderHook(() => useSavedPois());

    await waitFor(() => {
      expect(result.current.pois).toHaveLength(1);
    });
    expect(result.current.pois[0].display_name).toBe("Costco");
  });

  it("adds a saved poi", async () => {
    setToken();
    mockGetSavedPois.mockResolvedValue([]);
    const newPoi = makeSavedPoi(2, "Target");
    mockCreateSavedPoi.mockResolvedValue(newPoi);

    const { result } = renderHook(() => useSavedPois());
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => {
      await result.current.add({
        match_type: "brand",
        match_value: "Target",
        display_name: "Target",
        category: "store",
      });
    });

    expect(result.current.pois).toHaveLength(1);
    expect(result.current.pois[0].display_name).toBe("Target");
  });

  it("removes a saved poi", async () => {
    setToken();
    mockGetSavedPois.mockResolvedValue([makeSavedPoi(1, "Costco")]);
    mockDeleteSavedPoi.mockResolvedValue(undefined);

    const { result } = renderHook(() => useSavedPois());
    await waitFor(() => expect(result.current.pois).toHaveLength(1));

    await act(async () => {
      await result.current.remove(1);
    });

    expect(result.current.pois).toHaveLength(0);
  });
});

describe("useSavedPoisNearby", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  afterEach(() => {
    localStorage.clear();
  });

  it("returns empty when no lat/lon", () => {
    const { result } = renderHook(() => useSavedPoisNearby(null, null));
    expect(result.current.groups).toEqual([]);
  });

  it("fetches nearby groups", async () => {
    setToken();
    const groups = [
      {
        saved_poi_id: 1,
        display_name: "Costco",
        category: "store",
        match_type: "brand",
        matches: [
          {
            id: "SAVED-1",
            name: "Costco #101",
            address: "123 Main St",
            lat: 35.7,
            lon: -78.6,
            distance_miles: 2.5,
            drive_minutes: 8,
          },
        ],
      },
    ];
    mockGetSavedPoisNearby.mockResolvedValue({ groups });

    const { result } = renderHook(() => useSavedPoisNearby(35.7, -78.6));

    await waitFor(() => {
      expect(result.current.groups).toHaveLength(1);
    });
    expect(result.current.groups[0].display_name).toBe("Costco");
    expect(result.current.groups[0].matches).toHaveLength(1);
  });
});

describe("usePoiAutocomplete", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("does not fetch for short queries", () => {
    renderHook(() => usePoiAutocomplete("c"));
    vi.advanceTimersByTime(500);
    expect(mockAutocompletePoIs).not.toHaveBeenCalled();
  });

  it("fetches after debounce", async () => {
    vi.useRealTimers();
    const items = [
      {
        match_type: "brand",
        match_value: "Costco",
        display_name: "Costco",
        category: "store",
        count: 47,
      },
    ];
    mockAutocompletePoIs.mockResolvedValue({ results: items, query: "cos" });

    const { result } = renderHook(() => usePoiAutocomplete("cos"));

    await waitFor(() => {
      expect(result.current.results).toHaveLength(1);
    });
    expect(result.current.results[0].match_value).toBe("Costco");
  });
});
