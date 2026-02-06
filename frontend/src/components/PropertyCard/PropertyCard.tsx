import type { ForecastResponse } from "../../types";

interface PropertyCardProps {
  forecast: ForecastResponse;
}

function PropertyCard({ forecast }: PropertyCardProps) {
  const formatter = new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  });

  return (
    <div className="max-w-md rounded-md bg-bg-card p-6 shadow-soft">
      <h3 className="mt-0 text-lg font-semibold text-text-pri">
        {forecast.address}
      </h3>
      <p className="mt-2 text-2xl font-bold tracking-tight text-brand-blue">
        {formatter.format(forecast.predicted_value)}
      </p>
      <p className="mt-1 text-sm font-medium text-text-sec">
        Range: {formatter.format(forecast.confidence_interval_low)} &ndash;{" "}
        {formatter.format(forecast.confidence_interval_high)}
      </p>
      <p className="mt-1 text-xs text-text-sec">
        Model: {forecast.model_version}
      </p>
    </div>
  );
}

export default PropertyCard;
