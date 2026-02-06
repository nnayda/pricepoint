import { describe, it, expect } from "vitest";
import { renderHook } from "@testing-library/react";
import { useMortgageCalculator } from "../useMortgageCalculator";
import type { MortgageInputs } from "../../types";

const baseInputs: MortgageInputs = {
  homePrice: 400000,
  downPaymentPercent: 20,
  interestRate: 6.5,
  loanTermYears: 30,
  annualTax: 4000,
  annualInsurance: 1200,
  monthlyHoa: 100,
};

describe("useMortgageCalculator", () => {
  it("returns a breakdown with all fields", () => {
    const { result } = renderHook(() => useMortgageCalculator(baseInputs));
    const breakdown = result.current;
    expect(breakdown).toHaveProperty("principal");
    expect(breakdown).toHaveProperty("interest");
    expect(breakdown).toHaveProperty("tax");
    expect(breakdown).toHaveProperty("insurance");
    expect(breakdown).toHaveProperty("hoa");
    expect(breakdown).toHaveProperty("total");
  });

  it("calculates correct tax and insurance", () => {
    const { result } = renderHook(() => useMortgageCalculator(baseInputs));
    expect(result.current.tax).toBeCloseTo(4000 / 12, 2);
    expect(result.current.insurance).toBeCloseTo(1200 / 12, 2);
  });

  it("passes through HOA directly", () => {
    const { result } = renderHook(() => useMortgageCalculator(baseInputs));
    expect(result.current.hoa).toBe(100);
  });

  it("total equals sum of all components", () => {
    const { result } = renderHook(() => useMortgageCalculator(baseInputs));
    const { principal, interest, tax, insurance, hoa, total } = result.current;
    expect(total).toBeCloseTo(principal + interest + tax + insurance + hoa, 2);
  });

  it("calculates correct loan amount with 20% down", () => {
    const { result } = renderHook(() => useMortgageCalculator(baseInputs));
    // Loan = 400000 * 0.80 = 320000
    // Monthly rate = 6.5/100/12 = 0.00541667
    // P&I = 320000 * (0.00541667 * 1.00541667^360) / (1.00541667^360 - 1)
    const { principal, interest } = result.current;
    const pAndI = principal + interest;
    // Standard amortization for 320k at 6.5% over 30yr = ~$2022.75
    expect(pAndI).toBeCloseTo(2022.75, 0);
  });

  it("handles 0% interest rate", () => {
    const inputs: MortgageInputs = {
      ...baseInputs,
      interestRate: 0,
    };
    const { result } = renderHook(() => useMortgageCalculator(inputs));
    // With 0% rate, P&I = loan / totalPayments = 320000 / 360
    expect(result.current.interest).toBe(0);
    expect(result.current.principal).toBeCloseTo(320000 / 360, 2);
  });

  it("handles 100% down payment", () => {
    const inputs: MortgageInputs = {
      ...baseInputs,
      downPaymentPercent: 100,
    };
    const { result } = renderHook(() => useMortgageCalculator(inputs));
    // No loan means no P&I
    expect(result.current.principal).toBe(0);
    expect(result.current.interest).toBe(0);
    // Total is just tax + insurance + hoa
    const expected = 4000 / 12 + 1200 / 12 + 100;
    expect(result.current.total).toBeCloseTo(expected, 2);
  });

  it("handles 0% down payment", () => {
    const inputs: MortgageInputs = {
      ...baseInputs,
      downPaymentPercent: 0,
    };
    const { result } = renderHook(() => useMortgageCalculator(inputs));
    // Loan = full 400000
    const pAndI = result.current.principal + result.current.interest;
    // Standard amortization for 400k at 6.5% over 30yr = ~$2528.44
    expect(pAndI).toBeCloseTo(2528.44, 0);
  });

  it("handles 15-year term", () => {
    const inputs: MortgageInputs = {
      ...baseInputs,
      loanTermYears: 15,
    };
    const { result } = renderHook(() => useMortgageCalculator(inputs));
    const pAndI = result.current.principal + result.current.interest;
    // 320k at 6.5% over 15yr = ~$2787.83
    expect(pAndI).toBeCloseTo(2787.83, 0);
  });

  it("recalculates when inputs change", () => {
    const { result, rerender } = renderHook(
      (inputs: MortgageInputs) => useMortgageCalculator(inputs),
      { initialProps: baseInputs },
    );

    const firstTotal = result.current.total;

    rerender({ ...baseInputs, homePrice: 500000 });

    expect(result.current.total).not.toBe(firstTotal);
    expect(result.current.total).toBeGreaterThan(firstTotal);
  });

  it("handles zero HOA", () => {
    const inputs: MortgageInputs = {
      ...baseInputs,
      monthlyHoa: 0,
    };
    const { result } = renderHook(() => useMortgageCalculator(inputs));
    expect(result.current.hoa).toBe(0);
  });

  it("principal and interest sum to P&I payment", () => {
    const { result } = renderHook(() => useMortgageCalculator(baseInputs));
    const { principal, interest } = result.current;
    // First month interest = 320000 * 0.065/12
    const expectedInterest = 320000 * (6.5 / 100 / 12);
    expect(interest).toBeCloseTo(expectedInterest, 2);
    expect(principal).toBeGreaterThan(0);
  });
});
