import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useMapStyle } from "../useMapStyle";

const STORAGE_KEY = "pricepoint-map-style";
const SYNC_EVENT = "pricepoint-map-style-change";

describe("useMapStyle hook", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    localStorage.clear();
  });

  it("returns the default style when nothing is stored", () => {
    const { result } = renderHook(() => useMapStyle("dark"));
    const [style, , userHasChosen] = result.current;
    expect(style).toBe("dark");
    expect(userHasChosen).toBe(false);
  });

  it("returns the stored style from localStorage", () => {
    localStorage.setItem(STORAGE_KEY, "satellite");
    const { result } = renderHook(() => useMapStyle("dark"));
    const [style, , userHasChosen] = result.current;
    expect(style).toBe("satellite");
    expect(userHasChosen).toBe(true);
  });

  it("ignores invalid localStorage values", () => {
    localStorage.setItem(STORAGE_KEY, "invalid-value");
    const { result } = renderHook(() => useMapStyle("light"));
    expect(result.current[0]).toBe("light");
    expect(result.current[2]).toBe(false);
  });

  it("persists style to localStorage when set", () => {
    const { result } = renderHook(() => useMapStyle("dark"));
    act(() => {
      result.current[1]("street");
    });
    expect(result.current[0]).toBe("street");
    expect(localStorage.getItem(STORAGE_KEY)).toBe("street");
    expect(result.current[2]).toBe(true);
  });

  it("dispatches a custom event when style changes", () => {
    const listener = vi.fn();
    window.addEventListener(SYNC_EVENT, listener);

    const { result } = renderHook(() => useMapStyle("dark"));
    act(() => {
      result.current[1]("satellite");
    });

    expect(listener).toHaveBeenCalledTimes(1);
    expect((listener.mock.calls[0][0] as CustomEvent).detail).toBe("satellite");

    window.removeEventListener(SYNC_EVENT, listener);
  });

  it("syncs style across multiple hook instances via custom event", () => {
    const { result: hook1 } = renderHook(() => useMapStyle("dark"));
    const { result: hook2 } = renderHook(() => useMapStyle("dark"));

    // Both start at dark
    expect(hook1.current[0]).toBe("dark");
    expect(hook2.current[0]).toBe("dark");

    // Change hook1 — hook2 should sync via the custom event
    act(() => {
      hook1.current[1]("satellite");
    });

    expect(hook1.current[0]).toBe("satellite");
    expect(hook2.current[0]).toBe("satellite");
  });

  it("follows default style changes when user has not chosen", () => {
    const { result, rerender } = renderHook(({ defaultStyle }) => useMapStyle(defaultStyle), {
      initialProps: { defaultStyle: "dark" as const },
    });

    expect(result.current[0]).toBe("dark");

    rerender({ defaultStyle: "light" as const });
    expect(result.current[0]).toBe("light");
  });

  it("does not follow default style changes after user has chosen", () => {
    const { result, rerender } = renderHook(({ defaultStyle }) => useMapStyle(defaultStyle), {
      initialProps: { defaultStyle: "dark" as const },
    });

    act(() => {
      result.current[1]("street");
    });

    rerender({ defaultStyle: "light" as const });
    // Should stay on street, not follow the default
    expect(result.current[0]).toBe("street");
  });

  it("cleans up event listener on unmount", () => {
    const removeSpy = vi.spyOn(window, "removeEventListener");
    const { unmount } = renderHook(() => useMapStyle("dark"));

    unmount();

    const syncCalls = removeSpy.mock.calls.filter(([event]) => event === SYNC_EVENT);
    expect(syncCalls.length).toBeGreaterThan(0);

    removeSpy.mockRestore();
  });

  it("reads all four valid style values from localStorage", () => {
    for (const style of ["street", "satellite", "dark", "light"] as const) {
      localStorage.setItem(STORAGE_KEY, style);
      const { result } = renderHook(() => useMapStyle("dark"));
      expect(result.current[0]).toBe(style);
    }
  });
});
