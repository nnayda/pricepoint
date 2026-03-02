import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useSavedProperties } from "../useSavedProperties";

const mockGetSaved = vi.fn();
const mockDeleteSaved = vi.fn();

vi.mock("../../services/saved", () => ({
  getSavedProperties: (...args: unknown[]) => mockGetSaved(...args),
  deleteSavedProperty: (...args: unknown[]) => mockDeleteSaved(...args),
}));

const FAKE_TOKEN = "test-token";

function setToken() {
  localStorage.setItem("pricepoint-auth-token", FAKE_TOKEN);
}

function makeSaved(id: number, address: string) {
  return {
    id,
    listing_id: id * 10,
    notes: null,
    created_at: "2025-06-01T12:00:00Z",
    listing_address: address,
    city: "Cary",
    state: "NC",
    zip_code: "27513",
    listing_status: "Sold",
    listing_price: 350000,
    sold_price: 345000,
    num_beds: 3,
    num_baths: 2.5,
    sqft: 1800,
    year_built: 2005,
    photo_url: "/api/photos/photos/abc.jpg",
    lat: 35.79,
    lon: -78.78,
  };
}

describe("useSavedProperties", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  afterEach(() => {
    localStorage.clear();
  });

  it("does not fetch when unauthenticated", () => {
    renderHook(() => useSavedProperties(false));
    expect(mockGetSaved).not.toHaveBeenCalled();
  });

  it("fetches properties when authenticated", async () => {
    setToken();
    const items = [makeSaved(1, "123 Main St")];
    mockGetSaved.mockResolvedValue(items);

    const { result } = renderHook(() => useSavedProperties(true));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(mockGetSaved).toHaveBeenCalledWith(FAKE_TOKEN);
    expect(result.current.properties).toHaveLength(1);
    expect(result.current.properties[0].listing_address).toBe("123 Main St");
    expect(result.current.error).toBeNull();
  });

  it("sets error on fetch failure", async () => {
    setToken();
    mockGetSaved.mockRejectedValue(new Error("Network error"));

    const { result } = renderHook(() => useSavedProperties(true));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.error).toBe("Failed to load saved properties.");
    expect(result.current.properties).toHaveLength(0);
  });

  it("remove calls API and filters state", async () => {
    setToken();
    const items = [makeSaved(1, "123 Main St"), makeSaved(2, "456 Oak Ave")];
    mockGetSaved.mockResolvedValue(items);
    mockDeleteSaved.mockResolvedValue(undefined);

    const { result } = renderHook(() => useSavedProperties(true));

    await waitFor(() => {
      expect(result.current.properties).toHaveLength(2);
    });

    await act(async () => {
      await result.current.remove(1);
    });

    expect(mockDeleteSaved).toHaveBeenCalledWith(FAKE_TOKEN, 1);
    expect(result.current.properties).toHaveLength(1);
    expect(result.current.properties[0].id).toBe(2);
  });

  it("refetch triggers reload", async () => {
    setToken();
    mockGetSaved.mockResolvedValue([makeSaved(1, "123 Main St")]);

    const { result } = renderHook(() => useSavedProperties(true));

    await waitFor(() => {
      expect(result.current.properties).toHaveLength(1);
    });

    mockGetSaved.mockResolvedValue([makeSaved(1, "123 Main St"), makeSaved(2, "456 Oak Ave")]);

    act(() => {
      result.current.refetch();
    });

    await waitFor(() => {
      expect(result.current.properties).toHaveLength(2);
    });

    expect(mockGetSaved).toHaveBeenCalledTimes(2);
  });
});
