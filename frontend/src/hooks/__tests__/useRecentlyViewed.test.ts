import { describe, it, expect, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useRecentlyViewed } from "../useRecentlyViewed";
import type { RecentlyViewedItem } from "../../types";

function makeItem(overrides: Partial<RecentlyViewedItem> = {}): RecentlyViewedItem {
  return {
    address: "123 Main St",
    lat: 35.8,
    lon: -78.6,
    viewedAt: new Date().toISOString(),
    ...overrides,
  };
}

beforeEach(() => {
  localStorage.clear();
});

describe("useRecentlyViewed", () => {
  it("initially returns an empty array", () => {
    const { result } = renderHook(() => useRecentlyViewed());
    expect(result.current.recentlyViewed).toEqual([]);
  });

  it("adds an item via addRecentlyViewed", () => {
    const { result } = renderHook(() => useRecentlyViewed());
    const item = makeItem();
    act(() => {
      result.current.addRecentlyViewed(item);
    });
    expect(result.current.recentlyViewed).toHaveLength(1);
    expect(result.current.recentlyViewed[0].address).toBe("123 Main St");
  });

  it("enforces a maximum of 10 items", () => {
    const { result } = renderHook(() => useRecentlyViewed());
    act(() => {
      for (let i = 0; i < 12; i++) {
        result.current.addRecentlyViewed(makeItem({ address: `Address ${i}` }));
      }
    });
    expect(result.current.recentlyViewed).toHaveLength(10);
    // Most recent should be first
    expect(result.current.recentlyViewed[0].address).toBe("Address 11");
  });

  it("moves duplicate address to front and updates viewedAt", () => {
    const { result } = renderHook(() => useRecentlyViewed());
    act(() => {
      result.current.addRecentlyViewed(makeItem({ address: "First" }));
      result.current.addRecentlyViewed(makeItem({ address: "Second" }));
    });
    expect(result.current.recentlyViewed[0].address).toBe("Second");

    act(() => {
      result.current.addRecentlyViewed(
        makeItem({ address: "First", viewedAt: "2099-01-01T00:00:00Z" }),
      );
    });
    expect(result.current.recentlyViewed[0].address).toBe("First");
    expect(result.current.recentlyViewed[0].viewedAt).toBe("2099-01-01T00:00:00Z");
    expect(result.current.recentlyViewed).toHaveLength(2);
  });

  it("clears all items via clearRecentlyViewed", () => {
    const { result } = renderHook(() => useRecentlyViewed());
    act(() => {
      result.current.addRecentlyViewed(makeItem());
      result.current.addRecentlyViewed(makeItem({ address: "456 Oak Ave" }));
    });
    expect(result.current.recentlyViewed).toHaveLength(2);

    act(() => {
      result.current.clearRecentlyViewed();
    });
    expect(result.current.recentlyViewed).toEqual([]);
  });

  it("persists to localStorage", () => {
    const { result } = renderHook(() => useRecentlyViewed());
    const item = makeItem();
    act(() => {
      result.current.addRecentlyViewed(item);
    });

    const stored = JSON.parse(localStorage.getItem("pricepoint-recently-viewed")!);
    expect(stored).toHaveLength(1);
    expect(stored[0].address).toBe("123 Main St");
  });

  it("loads persisted items on mount", () => {
    const items = [makeItem({ address: "Persisted St" })];
    localStorage.setItem("pricepoint-recently-viewed", JSON.stringify(items));

    const { result } = renderHook(() => useRecentlyViewed());
    expect(result.current.recentlyViewed).toHaveLength(1);
    expect(result.current.recentlyViewed[0].address).toBe("Persisted St");
  });

  it("handles corrupted localStorage gracefully", () => {
    localStorage.setItem("pricepoint-recently-viewed", "not-json{{{");
    const { result } = renderHook(() => useRecentlyViewed());
    expect(result.current.recentlyViewed).toEqual([]);
  });
});
