import { useCallback, useState } from "react";
import type { MortgageDefaults } from "../types";

const STORAGE_KEY = "pricepoint-mortgage-defaults";

const DEFAULT_VALUES: MortgageDefaults = {
  downPaymentPercent: 20,
  interestRate: 6.5,
  loanTermYears: 30,
  annualInsurance: 1200,
};

function loadDefaults(): MortgageDefaults {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      return { ...DEFAULT_VALUES, ...JSON.parse(stored) };
    }
  } catch {
    // ignore parse errors
  }
  return DEFAULT_VALUES;
}

export function useMortgageDefaults() {
  const [defaults, setDefaults] = useState<MortgageDefaults>(loadDefaults);

  const updateDefaults = useCallback((updates: Partial<MortgageDefaults>) => {
    setDefaults((prev) => {
      const next = { ...prev, ...updates };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      return next;
    });
  }, []);

  return { defaults, updateDefaults };
}
