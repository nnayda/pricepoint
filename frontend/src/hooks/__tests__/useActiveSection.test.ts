import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useActiveSection } from "../useActiveSection";

// Mock IntersectionObserver
let observerCallback: IntersectionObserverCallback;
const mockObserve = vi.fn();
const mockDisconnect = vi.fn();

const MockIntersectionObserver = vi.fn((callback: IntersectionObserverCallback) => {
  observerCallback = callback;
  return {
    observe: mockObserve,
    disconnect: mockDisconnect,
    unobserve: vi.fn(),
    root: null,
    rootMargin: "",
    thresholds: [],
    takeRecords: vi.fn(() => []),
  };
});

vi.stubGlobal("IntersectionObserver", MockIntersectionObserver);

describe("useActiveSection", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Set up DOM elements for sections
    document.body.innerHTML = "";
  });

  it("returns first section id as initial active section", () => {
    const { result } = renderHook(() => useActiveSection(["section-a", "section-b"]));
    expect(result.current).toBe("section-a");
  });

  it("returns empty string when no sections provided", () => {
    const { result } = renderHook(() => useActiveSection([]));
    expect(result.current).toBe("");
  });

  it("observes DOM elements matching section ids", () => {
    // Create DOM elements
    const el1 = document.createElement("div");
    el1.id = "sec-1";
    document.body.appendChild(el1);

    const el2 = document.createElement("div");
    el2.id = "sec-2";
    document.body.appendChild(el2);

    renderHook(() => useActiveSection(["sec-1", "sec-2"]));

    expect(mockObserve).toHaveBeenCalledTimes(2);
    expect(mockObserve).toHaveBeenCalledWith(el1);
    expect(mockObserve).toHaveBeenCalledWith(el2);
  });

  it("skips elements that do not exist in the DOM", () => {
    const el = document.createElement("div");
    el.id = "exists";
    document.body.appendChild(el);

    renderHook(() => useActiveSection(["exists", "does-not-exist"]));

    expect(mockObserve).toHaveBeenCalledTimes(1);
    expect(mockObserve).toHaveBeenCalledWith(el);
  });

  it("disconnects observer on unmount", () => {
    const { unmount } = renderHook(() => useActiveSection(["a"]));
    unmount();
    expect(mockDisconnect).toHaveBeenCalled();
  });

  it("updates active section based on intersection", () => {
    const el1 = document.createElement("div");
    el1.id = "top";
    document.body.appendChild(el1);

    const el2 = document.createElement("div");
    el2.id = "bottom";
    document.body.appendChild(el2);

    const { result } = renderHook(() => useActiveSection(["top", "bottom"]));

    // Simulate intersection: bottom section becomes most visible
    const mockEntries = [
      { target: el1, intersectionRatio: 0.1 } as unknown as IntersectionObserverEntry,
      { target: el2, intersectionRatio: 0.8 } as unknown as IntersectionObserverEntry,
    ];
    act(() => {
      observerCallback(mockEntries, {} as IntersectionObserver);
    });

    expect(result.current).toBe("bottom");
  });

  it("creates observer with correct options", () => {
    renderHook(() => useActiveSection(["a"]));

    expect(MockIntersectionObserver).toHaveBeenCalledWith(expect.any(Function), {
      rootMargin: "-10% 0px -10% 0px",
      threshold: [0, 0.25, 0.5, 0.75, 1],
    });
  });
});
