import { useMemo, useState } from "react";
import type { DashboardData, MortgageBreakdown } from "../../../types";
import DashboardCard from "../DashboardCard";
import MonoValue from "../ui/MonoValue";
import EstimateRangeBar from "../charts/EstimateRangeBar";
import PriceHistoryChart from "../charts/PriceHistoryChart";
import ShapWaterfall from "../charts/ShapWaterfall";
import DashboardDonut from "../charts/DashboardDonut";
import SectionHeading from "../ui/SectionHeading";
import { MORTGAGE_COLORS } from "../../../utils/chartTokens";

interface ValuationTabProps {
  data: DashboardData;
}

function fmtUsd(n: number): string {
  return "$" + n.toLocaleString("en-US");
}

function calcMortgage(
  price: number,
  downPct: number,
  rate: number,
  termYears: number,
  annualTax: number,
  annualInsurance: number,
  monthlyHoa: number,
): MortgageBreakdown {
  const principal = price * (1 - downPct / 100);
  const monthlyRate = rate / 100 / 12;
  const n = termYears * 12;
  const payment =
    monthlyRate > 0
      ? (principal * (monthlyRate * Math.pow(1 + monthlyRate, n))) /
        (Math.pow(1 + monthlyRate, n) - 1)
      : principal / n;
  const interestPortion = principal * monthlyRate;
  const principalPortion = payment - interestPortion;
  const tax = annualTax / 12;
  const insurance = annualInsurance / 12;

  return {
    principal: principalPortion,
    interest: interestPortion,
    tax,
    insurance,
    hoa: monthlyHoa,
    total: payment + tax + insurance + monthlyHoa,
  };
}

type Outcome = { label: string; style: string };

function getOutcome(v: DashboardData["valuation"]): Outcome {
  if (v.listed_price < v.confidence_low)
    return {
      label: "Bargain",
      style: "bg-[var(--color-db-green-muted)] text-[var(--color-db-green)]",
    };
  if (v.listed_price < v.predicted_value)
    return {
      label: "Value",
      style: "bg-[var(--color-db-surface-alt)] text-[var(--color-db-text-secondary)]",
    };
  if (v.listed_price < v.confidence_high)
    return {
      label: "Fair",
      style:
        "bg-[var(--color-db-orange-muted,rgba(251,146,60,0.15))] text-[var(--color-db-orange)]",
    };
  return {
    label: "Overpriced",
    style: "bg-[var(--color-db-red-muted)] text-[var(--color-db-red)]",
  };
}

function ValuationTab({ data }: ValuationTabProps) {
  const { valuation, shap_features, price_history, mortgage_defaults } = data;
  const outcome = getOutcome(valuation);

  const [homePrice, setHomePrice] = useState(mortgage_defaults.home_price);
  const [downPct, setDownPct] = useState(mortgage_defaults.down_payment_pct);
  const [rate, setRate] = useState(mortgage_defaults.interest_rate);
  const [term, setTerm] = useState(mortgage_defaults.loan_term_years);

  const mortgage = useMemo(
    () =>
      calcMortgage(
        homePrice,
        downPct,
        rate,
        term,
        mortgage_defaults.annual_tax,
        mortgage_defaults.annual_insurance,
        mortgage_defaults.monthly_hoa,
      ),
    [homePrice, downPct, rate, term, mortgage_defaults],
  );

  const donutData = [
    { label: "Principal", value: mortgage.principal, color: MORTGAGE_COLORS.principal },
    { label: "Interest", value: mortgage.interest, color: MORTGAGE_COLORS.interest },
    { label: "Tax", value: mortgage.tax, color: MORTGAGE_COLORS.tax },
    { label: "Insurance", value: mortgage.insurance, color: MORTGAGE_COLORS.insurance },
    { label: "HOA", value: mortgage.hoa, color: MORTGAGE_COLORS.hoa },
  ];

  return (
    <div className="flex flex-col gap-4">
      {/* Model Valuation Estimate — full width */}
      <DashboardCard>
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-[var(--color-db-text-primary)]">
              Model Valuation Estimate
            </h3>
            <a
              href="/model-methodology"
              aria-label="How model estimates are derived"
              className="rounded-full p-0.5 text-[var(--color-db-text-muted)] transition-colors hover:bg-[var(--color-db-surface-alt)] hover:text-[var(--color-db-text-secondary)]"
            >
              <svg
                className="h-4 w-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z"
                />
              </svg>
            </a>
          </div>
          <span
            className={`rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-wider ${outcome.style}`}
          >
            {outcome.label}
          </span>
        </div>
        <EstimateRangeBar valuation={valuation} />
      </DashboardCard>

      {/* Price History + SHAP side by side */}
      <div className="grid gap-4 lg:grid-cols-2">
        <DashboardCard>
          <div className="mb-3">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-[var(--color-db-text-primary)]">
              Price History
            </h3>
          </div>
          <PriceHistoryChart data={price_history} showNeighborhood={true} />
        </DashboardCard>

        <DashboardCard>
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-[var(--color-db-text-primary)]">
              Value Drivers (SHAP)
            </h3>
            <button
              type="button"
              className="rounded-[var(--radius-db-xs)] p-1 text-[var(--color-db-text-muted)] transition-colors hover:bg-[var(--color-db-surface-alt)] hover:text-[var(--color-db-text-secondary)]"
              aria-label="Expand SHAP chart"
            >
              <svg
                className="h-4 w-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5v-4m0 4h-4m4 0l-5-5"
                />
              </svg>
            </button>
          </div>
          <ShapWaterfall features={shap_features} />
        </DashboardCard>
      </div>

      {/* Mortgage Calculator */}
      <DashboardCard>
        <SectionHeading className="mb-4">Mortgage Calculator</SectionHeading>
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Sliders */}
          <div className="flex flex-col gap-3">
            <div>
              <div className="mb-1 flex justify-between text-xs text-[var(--color-db-text-tertiary)]">
                <span>Home Price</span>
                <MonoValue value={fmtUsd(homePrice)} size="sm" />
              </div>
              <input
                type="range"
                min={100000}
                max={1000000}
                step={5000}
                value={homePrice}
                onChange={(e) => setHomePrice(Number(e.target.value))}
                className="w-full accent-[var(--color-db-accent)]"
              />
            </div>
            <div>
              <div className="mb-1 flex justify-between text-xs text-[var(--color-db-text-tertiary)]">
                <span>Down Payment</span>
                <MonoValue
                  value={`${downPct}% (${fmtUsd(Math.round((homePrice * downPct) / 100))})`}
                  size="sm"
                />
              </div>
              <input
                type="range"
                min={0}
                max={50}
                step={1}
                value={downPct}
                onChange={(e) => setDownPct(Number(e.target.value))}
                className="w-full accent-[var(--color-db-accent)]"
              />
            </div>
            <div>
              <div className="mb-1 flex justify-between text-xs text-[var(--color-db-text-tertiary)]">
                <span>Interest Rate</span>
                <MonoValue value={`${rate}%`} size="sm" />
              </div>
              <input
                type="range"
                min={2}
                max={10}
                step={0.125}
                value={rate}
                onChange={(e) => setRate(Number(e.target.value))}
                className="w-full accent-[var(--color-db-accent)]"
              />
            </div>
            <div>
              <div className="mb-1 flex justify-between text-xs text-[var(--color-db-text-tertiary)]">
                <span>Loan Term</span>
                <MonoValue value={`${term} yrs`} size="sm" />
              </div>
              <div className="flex gap-2">
                {[15, 20, 30].map((t) => (
                  <button
                    key={t}
                    type="button"
                    onClick={() => setTerm(t)}
                    className={`flex-1 rounded-[var(--radius-db-xs)] border px-3 py-1.5 text-xs font-medium transition-colors ${
                      term === t
                        ? "border-[var(--color-db-accent)] bg-[var(--color-db-accent-muted)] text-[var(--color-db-accent)]"
                        : "border-[var(--color-db-border)] bg-[var(--color-db-surface-alt)] text-[var(--color-db-text-tertiary)] hover:bg-[var(--color-db-surface-hover)]"
                    }`}
                  >
                    {t} yr
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Donut + breakdown — side by side */}
          <div className="flex items-center gap-4">
            <DashboardDonut
              data={donutData}
              centerLabel="Monthly"
              centerValue={fmtUsd(Math.round(mortgage.total))}
              size={200}
            />
            <div className="flex-1 space-y-1.5">
              {donutData.map((d) => (
                <div key={d.label} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span
                      className="h-2.5 w-2.5 rounded-full"
                      style={{ backgroundColor: d.color }}
                    />
                    <span className="text-xs text-[var(--color-db-text-secondary)]">{d.label}</span>
                  </div>
                  <MonoValue value={fmtUsd(Math.round(d.value))} size="sm" />
                </div>
              ))}
            </div>
          </div>
        </div>
      </DashboardCard>
    </div>
  );
}

export default ValuationTab;
