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
    <div
      style={{
        border: "1px solid #e0e0e0",
        borderRadius: "8px",
        padding: "1.5rem",
        maxWidth: "400px",
      }}
    >
      <h3 style={{ marginTop: 0 }}>{forecast.address}</h3>
      <p style={{ fontSize: "1.5rem", fontWeight: "bold" }}>
        {formatter.format(forecast.predicted_value)}
      </p>
      <p style={{ color: "#666" }}>
        Range: {formatter.format(forecast.confidence_interval_low)} &ndash;{" "}
        {formatter.format(forecast.confidence_interval_high)}
      </p>
      <p style={{ fontSize: "0.875rem", color: "#999" }}>
        Model: {forecast.model_version}
      </p>
    </div>
  );
}

export default PropertyCard;
