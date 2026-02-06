import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useScrollProgress } from "../useScrollProgress";

describe("useScrollProgress", () => {
  let scrollY: number;

  beforeEach(() => {
    scrollY = 0;
    Object.defineProperty(window, "scrollY", { get: () => scrollY, configurable: true });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("returns 0 when page is at the top", () => {
    const { result } = renderHook(() => useScrollProgress(100));
    expect(result.current).toBe(0);
  });

  it("returns 1 when scrolled past the threshold", () => {
    scrollY = 200;
    const { result } = renderHook(() => useScrollProgress(100));
    expect(result.current).toBe(1);
  });

  it("returns proportional value when partially scrolled", () => {
    scrollY = 50;
    const { result } = renderHook(() => useScrollProgress(100));
    expect(result.current).toBe(0.5);
  });

  it("clamps at 1 and does not exceed threshold", () => {
    scrollY = 500;
    const { result } = renderHook(() => useScrollProgress(100));
    expect(result.current).toBe(1);
  });

  it("responds to scroll events", () => {
    const { result } = renderHook(() => useScrollProgress(100));
    expect(result.current).toBe(0);

    scrollY = 75;
    act(() => {
      window.dispatchEvent(new Event("scroll"));
    });
    expect(result.current).toBe(0.75);
  });

  it("removes scroll listener on unmount", () => {
    const removeSpy = vi.spyOn(window, "removeEventListener");
    const { unmount } = renderHook(() => useScrollProgress(100));

    unmount();

    expect(removeSpy).toHaveBeenCalledWith("scroll", expect.any(Function));
    removeSpy.mockRestore();
  });

  it("uses custom threshold", () => {
    scrollY = 100;
    const { result } = renderHook(() => useScrollProgress(200));
    expect(result.current).toBe(0.5);
  });

  it("defaults to threshold of 100", () => {
    scrollY = 100;
    const { result } = renderHook(() => useScrollProgress());
    expect(result.current).toBe(1);
  });
});
