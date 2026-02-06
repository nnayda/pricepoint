import { useMemo } from "react";
import type { MortgageInputs, MortgageBreakdown } from "../types";

export function useMortgageCalculator(inputs: MortgageInputs): MortgageBreakdown {
  return useMemo(() => {
    const {
      homePrice,
      downPaymentPercent,
      interestRate,
      loanTermYears,
      annualTax,
      annualInsurance,
      monthlyHoa,
    } = inputs;

    const loanAmount = homePrice * (1 - downPaymentPercent / 100);
    const monthlyRate = interestRate / 100 / 12;
    const totalPayments = loanTermYears * 12;

    let monthlyPrincipalAndInterest: number;
    if (monthlyRate === 0) {
      monthlyPrincipalAndInterest = loanAmount / totalPayments;
    } else {
      const factor = Math.pow(1 + monthlyRate, totalPayments);
      monthlyPrincipalAndInterest = (loanAmount * (monthlyRate * factor)) / (factor - 1);
    }

    // For the first month, interest portion = loan balance * monthly rate
    const interest = loanAmount * monthlyRate;
    const principal = monthlyPrincipalAndInterest - interest;
    const tax = annualTax / 12;
    const insurance = annualInsurance / 12;
    const hoa = monthlyHoa;
    const total = monthlyPrincipalAndInterest + tax + insurance + hoa;

    return { principal, interest, tax, insurance, hoa, total };
  }, [inputs]);
}
