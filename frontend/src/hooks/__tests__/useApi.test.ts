import { describe, it, expect, vi } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useApi } from "../useApi";

describe("useApi hook", () => {
  it("has correct initial state", () => {
    const mockFn = vi.fn();
    const { result } = renderHook(() => useApi(mockFn));

    expect(result.current.data).toBeNull();
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it("sets loading state during execution", async () => {
    let resolve: (value: string) => void;
    const promise = new Promise<string>((r) => {
      resolve = r;
    });
    const mockFn = vi.fn().mockReturnValue(promise);
    const { result } = renderHook(() => useApi(mockFn));

    act(() => {
      result.current.execute();
    });

    expect(result.current.loading).toBe(true);

    await act(async () => {
      resolve!("done");
      await promise;
    });

    expect(result.current.loading).toBe(false);
  });

  it("sets data on success", async () => {
    const mockFn = vi.fn().mockResolvedValue({ value: 42 });
    const { result } = renderHook(() => useApi(mockFn));

    await act(async () => {
      await result.current.execute();
    });

    expect(result.current.data).toEqual({ value: 42 });
    expect(result.current.error).toBeNull();
    expect(result.current.loading).toBe(false);
  });

  it("sets error on failure", async () => {
    const mockFn = vi.fn().mockRejectedValue(new Error("Network error"));
    const { result } = renderHook(() => useApi(mockFn));

    await act(async () => {
      await result.current.execute();
    });

    expect(result.current.data).toBeNull();
    expect(result.current.error).toBe("Network error");
    expect(result.current.loading).toBe(false);
  });

  it("passes arguments through to the API function", async () => {
    const mockFn = vi.fn().mockResolvedValue("ok");
    const { result } = renderHook(() => useApi(mockFn));

    await act(async () => {
      await result.current.execute("arg1", "arg2");
    });

    expect(mockFn).toHaveBeenCalledWith("arg1", "arg2");
  });
});
