import { useState, useMemo } from "react";
import type { DashboardData, MortgageBreakdown } from "../../../types";
import DashboardCard from "../DashboardCard";
import StatChip from "../ui/StatChip";
import MonoValue from "../ui/MonoValue";
import EstimateRangeBar from "../charts/EstimateRangeBar";
import PriceHistoryChart from "../charts/PriceHistoryChart";
import ShapWaterfall from "../charts/ShapWaterfall";
import SemiCircularGauge from "../charts/SemiCircularGauge";
import DashboardDonut from "../charts/DashboardDonut";

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

function ValuationTab({ data }: ValuationTabProps) {
  const { valuation, shap_features, price_history, listing_quality, mortgage_defaults } = data;
  const [showNeighborhood, setShowNeighborhood] = useState(true);

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
    { label: "Principal", value: mortgage.principal, color: "#6366F1" },
    { label: "Interest", value: mortgage.interest, color: "#22D3EE" },
    { label: "Tax", value: mortgage.tax, color: "#FBBF24" },
    { label: "Insurance", value: mortgage.insurance, color: "#34D399" },
    { label: "HOA", value: mortgage.hoa, color: "#A78BFA" },
  ];

  return (
    <div className="flex flex-col gap-4">
      {/* Verdict callout — prominent at top per spec */}
      <DashboardCard>
        <div className="rounded-[var(--radius-db-sm)] border border-[var(--color-db-green)] border-opacity-30 bg-[var(--color-db-green-muted)] px-4 py-3">
          <span className="text-sm font-semibold text-[var(--color-db-green)]">
            {valuation.verdict}
          </span>
          <p className="mt-1 text-xs text-[var(--color-db-text-secondary)]">
            {valuation.verdict_detail}
          </p>
        </div>
      </DashboardCard>

      {/* Estimate Range + AI Listing Quality + Stats row */}
      <div className="grid gap-4 lg:grid-cols-3">
        <DashboardCard className="lg:col-span-2">
          <h3 className="mb-3 text-sm font-semibold text-[var(--color-db-text-primary)]">
            Valuation Range
          </h3>
          <EstimateRangeBar valuation={valuation} />
          <div className="mt-3 grid grid-cols-3 gap-2">
            <StatChip label="Predicted" value={fmtUsd(valuation.predicted_value)} compact />
            <StatChip label="Redfin Est." value={fmtUsd(valuation.redfin_estimate)} compact />
            <StatChip label="Nbhd Median" value={fmtUsd(valuation.neighborhood_median)} compact />
          </div>
        </DashboardCard>

        <DashboardCard>
          <h3 className="mb-3 text-sm font-semibold text-[var(--color-db-text-primary)]">
            AI Listing Quality
          </h3>
          <div className="flex flex-col items-center gap-1">
            <SemiCircularGauge
              value={listing_quality.listing_health}
              label="Listing Health"
              color="var(--color-db-green)"
              size={100}
            />
            <div className="mt-1 flex w-full justify-around">
              <SemiCircularGauge
                value={listing_quality.photo_score}
                label="Photo"
                color="var(--color-db-cyan)"
                size={72}
              />
              <SemiCircularGauge
                value={listing_quality.description_score}
                label="Description"
                color="var(--color-db-accent)"
                size={72}
              />
            </div>
          </div>
        </DashboardCard>
      </div>

      {/* Price History + SHAP side by side */}
      <div className="grid gap-4 lg:grid-cols-2">
        <DashboardCard>
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-[var(--color-db-text-primary)]">
              Price History
            </h3>
            <label className="flex items-center gap-2 text-xs text-[var(--color-db-text-tertiary)]">
              <input
                type="checkbox"
                checked={showNeighborhood}
                onChange={(e) => setShowNeighborhood(e.target.checked)}
                className="rounded border-[var(--color-db-border)] bg-[var(--color-db-surface-alt)]"
              />
              Neighborhood median
            </label>
          </div>
          <PriceHistoryChart data={price_history} showNeighborhood={showNeighborhood} />
        </DashboardCard>

        <DashboardCard>
          <h3 className="mb-3 text-sm font-semibold text-[var(--color-db-text-primary)]">
            Value Drivers (SHAP)
          </h3>
          <ShapWaterfall features={shap_features} />
        </DashboardCard>
      </div>

      {/* Mortgage Calculator */}
      <DashboardCard>
        <h3 className="mb-4 text-sm font-semibold text-[var(--color-db-text-primary)]">
          Mortgage Calculator
        </h3>
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

          {/* Donut + breakdown */}
          <div className="flex flex-col items-center gap-3">
            <DashboardDonut
              data={donutData}
              centerLabel="Monthly"
              centerValue={fmtUsd(Math.round(mortgage.total))}
              size={170}
            />
            <div className="w-full space-y-1.5">
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
