import type { ValuationData } from "../../types";

interface ValueSectionProps {
  valuation: ValuationData;
}

const currency = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

function ValueSection({ valuation }: ValueSectionProps) {
  const referencePrice = valuation.listed_price ?? valuation.last_sold_price;
  const referenceLabel = valuation.listed_price != null ? "Listed Price" : "Last Sold Price";
  const predicted = valuation.predicted_value;

  const delta = referencePrice != null && predicted != null ? referencePrice - predicted : null;
  const isGoodDeal = delta != null && delta > 0;

  const maxVal = Math.max(referencePrice ?? 0, predicted ?? 0);
  const refPct = referencePrice != null && maxVal > 0 ? (referencePrice / maxVal) * 100 : 0;
  const predPct = predicted != null && maxVal > 0 ? (predicted / maxVal) * 100 : 0;

  return (
    <section
      aria-label="Property valuation"
      className="rounded-lg bg-bg-card/80 p-5 shadow-soft backdrop-blur-md sm:p-8"
    >
      <h2 className="text-lg font-bold text-text-pri">Valuation</h2>

      <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-6">
        {referencePrice != null && (
          <div>
            <p className="text-xs font-medium text-text-sec">{referenceLabel}</p>
            <p className="text-xl font-bold text-text-pri">{currency.format(referencePrice)}</p>
          </div>
        )}
        {predicted != null && (
          <div>
            <p className="text-xs font-medium text-text-sec">Predicted Value</p>
            <p className="text-xl font-bold text-brand-blue">{currency.format(predicted)}</p>
          </div>
        )}
        {valuation.redfin_estimate != null && (
          <div>
            <p className="text-xs font-medium text-text-sec">Redfin Estimate</p>
            <p className="text-xl font-bold text-text-pri">
              {currency.format(valuation.redfin_estimate)}
            </p>
          </div>
        )}
        {delta != null && (
          <span
            className={`inline-block rounded-full px-3 py-1 text-xs font-bold text-white ${isGoodDeal ? "bg-status-maint" : "bg-status-rented"}`}
          >
            {isGoodDeal ? "Good Deal" : "Over Predicted"}
          </span>
        )}
      </div>

      {delta != null && (
        <p
          className={`mt-2 text-sm font-medium ${isGoodDeal ? "text-status-maint" : "text-status-rented"}`}
        >
          {currency.format(Math.abs(delta))} {isGoodDeal ? "below" : "above"}{" "}
          {referenceLabel.toLowerCase()}
        </p>
      )}

      {referencePrice != null && predicted != null && (
        <div className="mt-4 space-y-2" aria-label="Price comparison bars">
          <div>
            <p className="mb-1 text-xs font-medium text-text-sec">{referenceLabel}</p>
            <div className="h-3 w-full rounded-full bg-bg-main">
              <div className="h-3 rounded-full bg-text-sec" style={{ width: `${refPct}%` }} />
            </div>
          </div>
          <div>
            <p className="mb-1 text-xs font-medium text-text-sec">Predicted</p>
            <div className="h-3 w-full rounded-full bg-bg-main">
              <div className="h-3 rounded-full bg-brand-blue" style={{ width: `${predPct}%` }} />
            </div>
          </div>
        </div>
      )}

      {(predicted != null || valuation.redfin_estimate != null) && (
        <div className="mt-4 flex flex-wrap gap-4 text-xs text-text-sec">
          {valuation.confidence_interval_low != null &&
            valuation.confidence_interval_high != null && (
              <p>
                Confidence: {currency.format(valuation.confidence_interval_low)} &ndash;{" "}
                {currency.format(valuation.confidence_interval_high)}
              </p>
            )}
          {valuation.model_version != null && <p>Model: {valuation.model_version}</p>}
          {valuation.prediction_date != null && <p>Predicted: {valuation.prediction_date}</p>}
        </div>
      )}
    </section>
  );
}

export default ValueSection;
