import { useState } from "react";
import { useApi } from "../hooks/useApi";
import { postForecast } from "../services/api";
import type { ForecastResponse } from "../types";

const formatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

function ResultCard({ forecast }: { forecast: ForecastResponse }) {
  const isUnavailable = forecast.model_version === "unavailable";

  if (isUnavailable) {
    return (
      <div
        role="alert"
        className="rounded-md border border-status-rented/30 bg-status-rented/10 p-6 text-center"
      >
        <p className="text-lg font-semibold text-status-rented">Forecast Unavailable</p>
        <p className="mt-2 text-sm text-text-sec">
          The prediction model is currently unavailable. Please try again later.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-md bg-bg-card p-6 shadow-soft">
      <h3 className="text-lg font-semibold text-text-pri">{forecast.address}</h3>
      <p className="mt-3 text-3xl font-bold tracking-tight text-brand-blue">
        {formatter.format(forecast.predicted_value)}
      </p>
      <div className="mt-4 flex items-center gap-2 text-sm font-medium text-text-sec">
        <span>Confidence Interval:</span>
        <span data-testid="confidence-interval">
          {formatter.format(forecast.confidence_interval_low)} &ndash;{" "}
          {formatter.format(forecast.confidence_interval_high)}
        </span>
      </div>
      <p className="mt-2 text-xs text-text-sec">Model version: {forecast.model_version}</p>
    </div>
  );
}

function ForecastPage() {
  const [address, setAddress] = useState("");
  const [city, setCity] = useState("");
  const [state, setState] = useState("");
  const [zipCode, setZipCode] = useState("");
  const { data, loading, error, execute } = useApi(postForecast);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!address.trim()) return;
    execute({
      address: address.trim(),
      ...(city.trim() && { city: city.trim() }),
      ...(state.trim() && { state: state.trim() }),
      ...(zipCode.trim() && { zip_code: zipCode.trim() }),
    });
  };

  const inputClass =
    "w-full rounded-pill bg-bg-card px-5 py-2.5 text-base font-medium text-text-pri shadow-card outline-none placeholder:text-text-sec focus:ring-2 focus:ring-brand-blue";

  return (
    <div className="flex flex-1 flex-col items-center px-4 py-8">
      <div className="flex w-full max-w-2xl flex-col gap-grid">
        <h2 className="text-2xl font-bold tracking-tight text-text-pri">Forecast</h2>

        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <input
            type="text"
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            placeholder="Address"
            required
            className={inputClass}
          />
          <div className="grid grid-cols-3 gap-3">
            <input
              type="text"
              value={city}
              onChange={(e) => setCity(e.target.value)}
              placeholder="City"
              className={inputClass}
            />
            <input
              type="text"
              value={state}
              onChange={(e) => setState(e.target.value)}
              placeholder="State"
              className={inputClass}
            />
            <input
              type="text"
              value={zipCode}
              onChange={(e) => setZipCode(e.target.value)}
              placeholder="Zip Code"
              className={inputClass}
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="rounded-pill bg-brand-blue px-6 py-2.5 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            {loading ? "Loading..." : "Get Forecast"}
          </button>
        </form>

        {error && (
          <p role="alert" className="text-base font-medium text-status-rented">
            Error: {error}
          </p>
        )}

        {loading && (
          <div className="flex justify-center py-8" role="status">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-blue border-t-transparent" />
            <span className="sr-only">Loading forecast...</span>
          </div>
        )}

        {data && !loading && <ResultCard forecast={data} />}
      </div>
    </div>
  );
}

export default ForecastPage;
