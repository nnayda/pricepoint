import { useCallback, useMemo, useState } from "react";
import type { DashboardData, MortgageBreakdown } from "../../../types";
import type { MapMarker } from "../maps/DashboardMap";
import DashboardCard from "../DashboardCard";
import DashboardMap from "../maps/DashboardMap";
import MonoValue from "../ui/MonoValue";
import EstimateRangeBar from "../charts/EstimateRangeBar";
import PriceHistoryChart from "../charts/PriceHistoryChart";
import ShapWaterfall from "../charts/ShapWaterfall";
import DashboardDonut from "../charts/DashboardDonut";
import SectionHeading from "../ui/SectionHeading";
import NoDataOverlay from "../ui/NoDataOverlay";
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
  const { listed_price, confidence_low, predicted_value, confidence_high } = v;
  if (confidence_low != null && listed_price < confidence_low)
    return {
      label: "Bargain",
      style: "bg-[var(--color-db-green-muted)] text-[var(--color-db-green)]",
    };
  if (predicted_value != null && listed_price < predicted_value)
    return {
      label: "Value",
      style: "bg-[var(--color-db-surface-alt)] text-[var(--color-db-text-secondary)]",
    };
  if (confidence_high != null && listed_price < confidence_high)
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

function fmtPrice(n: number): string {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000) return `$${Math.round(n / 1_000)}K`;
  return `$${n.toLocaleString("en-US")}`;
}

function NeighborhoodPricesCard({ data }: { data: DashboardData }) {
  const { property, neighborhood_properties } = data;
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const markers: MapMarker[] = useMemo(() => {
    const subjectMarker: MapMarker = {
      lat: property.lat,
      lon: property.lon,
      label: property.address,
      color: "#6366F1",
      id: "subject",
      isProperty: true,
    };

    if (!neighborhood_properties || neighborhood_properties.length === 0) {
      return [subjectMarker];
    }

    const propMarkers: MapMarker[] = neighborhood_properties.map((p, i) => ({
      lat: p.lat,
      lon: p.lon,
      label: `${p.address} — ${fmtPrice(p.effective_price)}`,
      color:
        p.listing_status === "Sold"
          ? "#94A3B8"
          : p.listing_status === "Estimated"
            ? "#A78BFA"
            : "#34D399",
      id: `np-${i}`,
      priceLabel: fmtPrice(p.effective_price),
    }));

    return [subjectMarker, ...propMarkers];
  }, [property, neighborhood_properties]);

  const renderPopup = useCallback(
    (marker: MapMarker) => {
      if (marker.id === "subject") {
        return (
          <div style={{ fontFamily: "var(--font-db-sans)", minWidth: 160 }}>
            <div style={{ fontWeight: 600, fontSize: 13 }}>Your Property</div>
            <div style={{ fontSize: 11, color: "#9BA3BF" }}>{property.address}</div>
          </div>
        );
      }
      const idx = marker.id ? parseInt(marker.id.replace("np-", ""), 10) : -1;
      const np = neighborhood_properties?.[idx];
      if (!np) return <span>{marker.label}</span>;
      return (
        <div style={{ fontFamily: "var(--font-db-sans)", minWidth: 160 }}>
          <div style={{ fontWeight: 600, fontSize: 13 }}>{fmtPrice(np.effective_price)}</div>
          <div style={{ fontSize: 11, color: "#9BA3BF" }}>{np.address}</div>
          <div
            style={{
              fontSize: 10,
              marginTop: 2,
              color: np.listing_status === "Sold" ? "#94A3B8" : "#34D399",
            }}
          >
            {np.listing_status}
          </div>
        </div>
      );
    },
    [property, neighborhood_properties],
  );

  return (
    <DashboardCard className="flex flex-col">
      <SectionHeading className="mb-3">Neighborhood Prices</SectionHeading>
      <div className="flex-1" style={{ minHeight: 300 }}>
        <DashboardMap
          center={[property.lat, property.lon]}
          zoom={14}
          markers={markers}
          height="100%"
          minHeight="300px"
          selectedId={selectedId}
          onMarkerSelect={setSelectedId}
          onMarkerDeselect={() => setSelectedId(null)}
          renderPopup={renderPopup}
        />
      </div>
      {neighborhood_properties && neighborhood_properties.length > 0 && (
        <div className="mt-2 flex items-center gap-4 text-[10px] text-[var(--color-db-text-muted)]">
          <span className="flex items-center gap-1">
            <span className="inline-block h-2 w-2 rounded-full bg-[#34D399]" />
            For Sale
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block h-2 w-2 rounded-full bg-[#94A3B8]" />
            Sold
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block h-2 w-2 rounded-full bg-[#A78BFA]" />
            Estimated
          </span>
          <span className="ml-auto">{neighborhood_properties.length} properties</span>
        </div>
      )}
    </DashboardCard>
  );
}

function ValuationTab({ data }: ValuationTabProps) {
  const { valuation, shap_features, price_history, mortgage_defaults, notFound } = data;
  const hasEstimate = valuation.predicted_value != null;
  const outcome = hasEstimate ? getOutcome(valuation) : null;

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
    {
      label: "Principal & Interest",
      value: mortgage.principal + mortgage.interest,
      color: MORTGAGE_COLORS.principal,
    },
    { label: "Tax", value: mortgage.tax, color: MORTGAGE_COLORS.tax },
    { label: "Insurance", value: mortgage.insurance, color: MORTGAGE_COLORS.insurance },
    { label: "HOA", value: mortgage.hoa, color: MORTGAGE_COLORS.hoa },
  ];

  return (
    <div className="flex flex-col gap-4">
      {/* Model Valuation Estimate — full width */}
      <DashboardCard className="relative overflow-hidden">
        {notFound && <NoDataOverlay message="Valuation estimate not available." />}
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-[var(--color-db-text-primary)]">
              {hasEstimate ? "Model Valuation Estimate" : "Price Comparison"}
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
          {outcome && (
            <span
              className={`rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-wider ${outcome.style}`}
            >
              {outcome.label}
            </span>
          )}
        </div>
        <EstimateRangeBar valuation={valuation} />
      </DashboardCard>

      {/* Price History + SHAP side by side */}
      <div className="grid gap-4 lg:grid-cols-2">
        <DashboardCard className="relative overflow-hidden" expandable title="Price History">
          {notFound && <NoDataOverlay message="Price history not available." />}
          <div className="mb-3">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-[var(--color-db-text-primary)]">
              Price History
            </h3>
          </div>
          <PriceHistoryChart data={price_history} showNeighborhood={true} />
        </DashboardCard>

        <DashboardCard className="relative overflow-hidden">
          {notFound && <NoDataOverlay message="Value drivers not available." />}
          {!notFound && !hasEstimate && <NoDataOverlay message="Value drivers not available." />}
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

      {/* Mortgage Calculator + Neighborhood Prices — side by side */}
      <div className="grid gap-4 lg:grid-cols-2">
        <DashboardCard>
          <SectionHeading className="mb-4">Mortgage Calculator</SectionHeading>

          {/* Donut + breakdown */}
          <div className="flex items-center gap-4">
            <DashboardDonut
              data={donutData}
              centerLabel="Monthly"
              centerValue={fmtUsd(Math.round(mortgage.total))}
              size={170}
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

          {/* Sliders */}
          <div className="mt-4 flex flex-col gap-3">
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
        </DashboardCard>

        <NeighborhoodPricesCard data={data} />
      </div>
    </div>
  );
}

export default ValuationTab;
