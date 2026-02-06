import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { startViewTransition } from "../viewTransition";

describe("startViewTransition", () => {
  const originalStartViewTransition = document.startViewTransition;

  afterEach(() => {
    document.startViewTransition = originalStartViewTransition;
  });

  describe("when browser supports View Transitions API", () => {
    it("delegates to document.startViewTransition", () => {
      const transition: ViewTransition = {
        finished: Promise.resolve(),
        ready: Promise.resolve(),
        updateCallbackDone: Promise.resolve(),
        skipTransition: vi.fn(),
      };
      document.startViewTransition = vi.fn(() => transition);

      const callback = vi.fn();
      const result = startViewTransition(callback);

      expect(document.startViewTransition).toHaveBeenCalledWith(callback);
      expect(result).toBe(transition);
    });
  });

  describe("when browser does not support View Transitions API", () => {
    beforeEach(() => {
      // @ts-expect-error -- simulate unsupported browser
      document.startViewTransition = undefined;
    });

    it("executes the sync callback immediately", () => {
      const callback = vi.fn();
      startViewTransition(callback);

      expect(callback).toHaveBeenCalledOnce();
    });

    it("executes the async callback immediately", async () => {
      const callback = vi.fn().mockResolvedValue(undefined);
      const result = startViewTransition(callback);

      expect(callback).toHaveBeenCalledOnce();
      await expect(result.finished).resolves.toBeUndefined();
    });

    it("returns a ViewTransition-shaped object", async () => {
      const result = startViewTransition(() => {});

      expect(result.finished).toBeInstanceOf(Promise);
      expect(result.ready).toBeInstanceOf(Promise);
      expect(result.updateCallbackDone).toBeInstanceOf(Promise);
      expect(typeof result.skipTransition).toBe("function");

      await expect(result.finished).resolves.toBeUndefined();
      await expect(result.ready).resolves.toBeUndefined();
      await expect(result.updateCallbackDone).resolves.toBeUndefined();
    });

    it("skipTransition is a no-op", () => {
      const result = startViewTransition(() => {});
      expect(() => result.skipTransition()).not.toThrow();
    });

    it("propagates errors from the callback", async () => {
      const error = new Error("callback failed");
      const result = startViewTransition(() => {
        throw error;
      });

      await expect(result.finished).rejects.toThrow("callback failed");
      await expect(result.updateCallbackDone).rejects.toThrow("callback failed");
    });
  });
});
