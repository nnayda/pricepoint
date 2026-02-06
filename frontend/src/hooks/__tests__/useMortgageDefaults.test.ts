import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";

// Must mock localStorage before importing the hook
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

const { useMortgageDefaults } = await import("../useMortgageDefaults");

const STORAGE_KEY = "pricepoint-mortgage-defaults";

describe("useMortgageDefaults", () => {
  beforeEach(() => {
    localStorageMock.clear();
    vi.clearAllMocks();
  });

  it("returns default values when nothing is saved", () => {
    const { result } = renderHook(() => useMortgageDefaults());
    expect(result.current.defaults).toEqual({
      downPaymentPercent: 20,
      interestRate: 6.5,
      loanTermYears: 30,
      annualInsurance: 1200,
    });
  });

  it("reads saved values from localStorage", () => {
    localStorageMock.setItem(
      STORAGE_KEY,
      JSON.stringify({ downPaymentPercent: 10, interestRate: 7.0 }),
    );

    const { result } = renderHook(() => useMortgageDefaults());
    expect(result.current.defaults.downPaymentPercent).toBe(10);
    expect(result.current.defaults.interestRate).toBe(7.0);
    // Unsaved values use defaults
    expect(result.current.defaults.loanTermYears).toBe(30);
    expect(result.current.defaults.annualInsurance).toBe(1200);
  });

  it("updateDefaults merges partial updates", () => {
    const { result } = renderHook(() => useMortgageDefaults());

    act(() => {
      result.current.updateDefaults({ downPaymentPercent: 15 });
    });

    expect(result.current.defaults.downPaymentPercent).toBe(15);
    // Other values unchanged
    expect(result.current.defaults.interestRate).toBe(6.5);
    expect(result.current.defaults.loanTermYears).toBe(30);
  });

  it("persists updates to localStorage", () => {
    const { result } = renderHook(() => useMortgageDefaults());

    act(() => {
      result.current.updateDefaults({ interestRate: 7.25 });
    });

    const stored = JSON.parse(localStorageMock.getItem(STORAGE_KEY)!);
    expect(stored.interestRate).toBe(7.25);
  });

  it("handles corrupt localStorage data gracefully", () => {
    localStorageMock.setItem(STORAGE_KEY, "not valid json{{{");

    const { result } = renderHook(() => useMortgageDefaults());
    // Falls back to defaults
    expect(result.current.defaults.downPaymentPercent).toBe(20);
  });

  it("multiple updates accumulate correctly", () => {
    const { result } = renderHook(() => useMortgageDefaults());

    act(() => {
      result.current.updateDefaults({ downPaymentPercent: 10 });
    });
    act(() => {
      result.current.updateDefaults({ interestRate: 5.0 });
    });

    expect(result.current.defaults.downPaymentPercent).toBe(10);
    expect(result.current.defaults.interestRate).toBe(5.0);
    expect(result.current.defaults.loanTermYears).toBe(30);
  });
});
