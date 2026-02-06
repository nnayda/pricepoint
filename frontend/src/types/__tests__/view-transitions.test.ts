import { describe, it, expect, vi } from "vitest";

describe("ViewTransition", () => {
  it("has required promise properties", () => {
    const transition: ViewTransition = {
      finished: Promise.resolve(),
      ready: Promise.resolve(),
      updateCallbackDone: Promise.resolve(),
      skipTransition: vi.fn(),
    };

    expect(transition.finished).toBeInstanceOf(Promise);
    expect(transition.ready).toBeInstanceOf(Promise);
    expect(transition.updateCallbackDone).toBeInstanceOf(Promise);
    expect(typeof transition.skipTransition).toBe("function");
  });
});

describe("document.startViewTransition", () => {
  it("accepts a sync callback", () => {
    const transition: ViewTransition = {
      finished: Promise.resolve(),
      ready: Promise.resolve(),
      updateCallbackDone: Promise.resolve(),
      skipTransition: vi.fn(),
    };

    const mockStartViewTransition = vi.fn(() => transition);
    document.startViewTransition = mockStartViewTransition;

    const result = document.startViewTransition(() => {});

    expect(mockStartViewTransition).toHaveBeenCalledOnce();
    expect(result.finished).toBeInstanceOf(Promise);
    expect(result.ready).toBeInstanceOf(Promise);
  });

  it("accepts an async callback", () => {
    const transition: ViewTransition = {
      finished: Promise.resolve(),
      ready: Promise.resolve(),
      updateCallbackDone: Promise.resolve(),
      skipTransition: vi.fn(),
    };

    const mockStartViewTransition = vi.fn(() => transition);
    document.startViewTransition = mockStartViewTransition;

    const result = document.startViewTransition(async () => {});

    expect(mockStartViewTransition).toHaveBeenCalledOnce();
    expect(result).toBe(transition);
  });

  it("supports skipTransition to cancel", () => {
    const skipFn = vi.fn();
    const transition: ViewTransition = {
      finished: Promise.resolve(),
      ready: Promise.resolve(),
      updateCallbackDone: Promise.resolve(),
      skipTransition: skipFn,
    };

    transition.skipTransition();
    expect(skipFn).toHaveBeenCalledOnce();
  });
});
