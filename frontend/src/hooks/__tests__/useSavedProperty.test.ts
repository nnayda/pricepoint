import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { useSavedProperty } from "../useSavedProperty";
import * as savedService from "../../services/saved";

vi.mock("../../services/saved", () => ({
  getSavedProperties: vi.fn(),
  saveProperty: vi.fn(),
  deleteSavedProperty: vi.fn(),
}));

const mockGetSaved = vi.mocked(savedService.getSavedProperties);
const mockSave = vi.mocked(savedService.saveProperty);
const mockDelete = vi.mocked(savedService.deleteSavedProperty);

const TOKEN = "test-token";

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
});

function setToken() {
  localStorage.setItem("pricepoint-auth-token", TOKEN);
}

describe("useSavedProperty", () => {
  it("does not fetch when not authenticated", () => {
    const { result } = renderHook(() => useSavedProperty(42, false));
    expect(result.current.isSaved).toBe(false);
    expect(result.current.isLoading).toBe(false);
    expect(mockGetSaved).not.toHaveBeenCalled();
  });

  it("does not fetch when listingId is null", () => {
    setToken();
    const { result } = renderHook(() => useSavedProperty(null, true));
    expect(result.current.isSaved).toBe(false);
    expect(mockGetSaved).not.toHaveBeenCalled();
  });

  it("fetches and sets isSaved=true when listing is found", async () => {
    setToken();
    mockGetSaved.mockResolvedValue([
      {
        id: 10,
        listing_id: 42,
        notes: null,
        created_at: "2025-01-01",
        listing_address: "123 Main",
      },
    ]);

    const { result } = renderHook(() => useSavedProperty(42, true));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });
    expect(result.current.isSaved).toBe(true);
    expect(result.current.savedId).toBe(10);
  });

  it("sets isSaved=false when listing not in saved list", async () => {
    setToken();
    mockGetSaved.mockResolvedValue([
      { id: 10, listing_id: 99, notes: null, created_at: "2025-01-01", listing_address: "Other" },
    ]);

    const { result } = renderHook(() => useSavedProperty(42, true));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });
    expect(result.current.isSaved).toBe(false);
    expect(result.current.savedId).toBeNull();
  });

  it("toggle saves when not saved", async () => {
    setToken();
    mockGetSaved.mockResolvedValue([]);
    mockSave.mockResolvedValue({
      id: 20,
      listing_id: 42,
      notes: null,
      created_at: "2025-01-01",
      listing_address: "123 Main",
    });

    const { result } = renderHook(() => useSavedProperty(42, true));
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => {
      await result.current.toggle();
    });

    expect(mockSave).toHaveBeenCalled();
    expect(result.current.isSaved).toBe(true);
    expect(result.current.savedId).toBe(20);
  });

  it("toggle deletes when already saved", async () => {
    setToken();
    mockGetSaved.mockResolvedValue([
      {
        id: 10,
        listing_id: 42,
        notes: null,
        created_at: "2025-01-01",
        listing_address: "123 Main",
      },
    ]);
    mockDelete.mockResolvedValue(undefined);

    const { result } = renderHook(() => useSavedProperty(42, true));
    await waitFor(() => expect(result.current.isSaved).toBe(true));

    await act(async () => {
      await result.current.toggle();
    });

    expect(mockDelete).toHaveBeenCalledWith(TOKEN, 10);
    expect(result.current.isSaved).toBe(false);
    expect(result.current.savedId).toBeNull();
  });

  it("toggle is a no-op when listingId is null", async () => {
    setToken();
    const { result } = renderHook(() => useSavedProperty(null, true));

    await act(async () => {
      await result.current.toggle();
    });

    expect(mockSave).not.toHaveBeenCalled();
    expect(mockDelete).not.toHaveBeenCalled();
  });
});
