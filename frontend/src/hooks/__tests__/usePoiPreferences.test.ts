import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";

const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] ?? null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key];
    }),
    clear: vi.fn(() => {
      store = {};
    }),
    get length() {
      return Object.keys(store).length;
    },
    key: vi.fn((index: number) => Object.keys(store)[index] ?? null),
  };
})();

Object.defineProperty(window, "localStorage", { value: localStorageMock });

const { usePoiPreferences } = await import("../usePoiPreferences");

const STORAGE_KEY = "pricepoint-poi-preferences";

describe("usePoiPreferences", () => {
  beforeEach(() => {
    localStorageMock.clear();
    vi.clearAllMocks();
  });

  it("returns default POI list when nothing is saved", () => {
    const { result } = renderHook(() => usePoiPreferences());
    expect(result.current.preferences.length).toBe(10);
    expect(result.current.preferences[0].id).toBe("costco");
    expect(result.current.preferences.every((p) => p.enabled)).toBe(true);
  });

  it("reads saved preferences from localStorage", () => {
    const saved = [
      {
        id: "costco",
        name: "Costco",
        category: "Grocery",
        enabled: false,
      },
    ];
    localStorageMock.setItem(STORAGE_KEY, JSON.stringify(saved));

    const { result } = renderHook(() => usePoiPreferences());
    expect(result.current.preferences.length).toBe(1);
    expect(result.current.preferences[0].enabled).toBe(false);
  });

  it("togglePoi toggles a single POI's enabled state", () => {
    const { result } = renderHook(() => usePoiPreferences());

    act(() => {
      result.current.togglePoi("costco");
    });

    const costco = result.current.preferences.find((p) => p.id === "costco");
    expect(costco?.enabled).toBe(false);

    // Other POIs unchanged
    const target = result.current.preferences.find((p) => p.id === "target");
    expect(target?.enabled).toBe(true);
  });

  it("togglePoi toggles back on second call", () => {
    const { result } = renderHook(() => usePoiPreferences());

    act(() => {
      result.current.togglePoi("costco");
    });
    act(() => {
      result.current.togglePoi("costco");
    });

    const costco = result.current.preferences.find((p) => p.id === "costco");
    expect(costco?.enabled).toBe(true);
  });

  it("toggleCategory disables all when all are enabled", () => {
    const { result } = renderHook(() => usePoiPreferences());

    act(() => {
      result.current.toggleCategory("Grocery");
    });

    const groceryPois = result.current.preferences.filter((p) => p.category === "Grocery");
    expect(groceryPois.every((p) => !p.enabled)).toBe(true);

    // Other categories unchanged
    const retailPois = result.current.preferences.filter((p) => p.category === "Retail");
    expect(retailPois.every((p) => p.enabled)).toBe(true);
  });

  it("toggleCategory enables all when some are disabled", () => {
    const { result } = renderHook(() => usePoiPreferences());

    // First disable one grocery item
    act(() => {
      result.current.togglePoi("costco");
    });

    // Now toggle category - should enable all since not all are enabled
    act(() => {
      result.current.toggleCategory("Grocery");
    });

    const groceryPois = result.current.preferences.filter((p) => p.category === "Grocery");
    expect(groceryPois.every((p) => p.enabled)).toBe(true);
  });

  it("addCustomPoi adds a new POI", () => {
    const { result } = renderHook(() => usePoiPreferences());
    const initialCount = result.current.preferences.length;

    act(() => {
      result.current.addCustomPoi("My Coffee Shop", "Restaurant");
    });

    expect(result.current.preferences.length).toBe(initialCount + 1);
    const custom = result.current.preferences[result.current.preferences.length - 1];
    expect(custom.name).toBe("My Coffee Shop");
    expect(custom.category).toBe("Restaurant");
    expect(custom.enabled).toBe(true);
    expect(custom.isCustom).toBe(true);
    expect(custom.id).toContain("custom-");
  });

  it("removeCustomPoi removes a custom POI", () => {
    const { result } = renderHook(() => usePoiPreferences());

    act(() => {
      result.current.addCustomPoi("Test Place", "Retail");
    });

    const custom = result.current.preferences.find((p) => p.isCustom);
    expect(custom).toBeDefined();

    act(() => {
      result.current.removeCustomPoi(custom!.id);
    });

    expect(result.current.preferences.find((p) => p.id === custom!.id)).toBeUndefined();
  });

  it("removeCustomPoi does not remove default POIs", () => {
    const { result } = renderHook(() => usePoiPreferences());
    const initialCount = result.current.preferences.length;

    act(() => {
      result.current.removeCustomPoi("costco");
    });

    // Default POIs cannot be removed (they don't have isCustom flag)
    expect(result.current.preferences.length).toBe(initialCount);
  });

  it("persists togglePoi changes to localStorage", () => {
    const { result } = renderHook(() => usePoiPreferences());

    act(() => {
      result.current.togglePoi("costco");
    });

    expect(localStorageMock.setItem).toHaveBeenCalledWith(STORAGE_KEY, expect.any(String));
    const stored = JSON.parse(localStorageMock.getItem(STORAGE_KEY)!);
    const costco = stored.find((p: { id: string }) => p.id === "costco");
    expect(costco.enabled).toBe(false);
  });

  it("persists addCustomPoi changes to localStorage", () => {
    const { result } = renderHook(() => usePoiPreferences());

    act(() => {
      result.current.addCustomPoi("New Place", "Other");
    });

    const stored = JSON.parse(localStorageMock.getItem(STORAGE_KEY)!);
    expect(stored.length).toBe(11);
    expect(stored[stored.length - 1].name).toBe("New Place");
  });

  it("handles corrupt localStorage data gracefully", () => {
    localStorageMock.setItem(STORAGE_KEY, "{{invalid json}}");

    const { result } = renderHook(() => usePoiPreferences());
    // Falls back to defaults
    expect(result.current.preferences.length).toBe(10);
  });
});
