import { useEffect } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { useApi } from "../hooks/useApi";
import { postForecast } from "../services/api";

const currencyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

function ResultsPage() {
  const [searchParams] = useSearchParams();
  const address = searchParams.get("address") ?? "";
  const { data, loading, error, execute } = useApi(postForecast);

  useEffect(() => {
    if (address) {
      execute({ address });
    }
  }, [address, execute]);

  if (!address) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center px-4">
        <div className="flex max-w-md flex-col items-center gap-4 text-center">
          <h1 className="text-2xl font-bold text-text-pri">No address provided</h1>
          <p className="text-base font-medium text-text-sec">
            Please search for a property to see its forecast.
          </p>
          <Link
            to="/"
            className="rounded-pill bg-brand-blue px-6 py-2.5 text-sm font-semibold text-white transition-opacity hover:opacity-90"
          >
            Go to search
          </Link>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center px-4">
        <div className="flex flex-col items-center gap-3">
          <div
            className="h-8 w-8 animate-spin rounded-full border-4 border-brand-blue border-t-transparent"
            role="status"
          >
            <span className="sr-only">Loading forecast...</span>
          </div>
          <p className="text-base font-medium text-text-sec">Analyzing property data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center px-4">
        <div className="flex max-w-md flex-col items-center gap-4 rounded-md bg-bg-card p-8 text-center shadow-soft">
          <h1 className="text-2xl font-bold text-text-pri">Something went wrong</h1>
          <p className="text-base font-medium text-status-rented">{error}</p>
          <Link
            to="/"
            className="rounded-pill bg-brand-blue px-6 py-2.5 text-sm font-semibold text-white transition-opacity hover:opacity-90"
          >
            Try another address
          </Link>
        </div>
      </div>
    );
  }

  if (!data) {
    return null;
  }

  return (
    <div className="flex flex-1 flex-col items-center px-4 py-8">
      <div className="flex w-full max-w-3xl flex-col gap-grid">
        {/* Header */}
        <div className="flex flex-col gap-1">
          <Link to="/" className="text-sm font-medium text-text-sec hover:text-brand-blue">
            &larr; Back to search
          </Link>
          <h1 className="text-2xl font-bold tracking-tight text-text-pri">{data.address}</h1>
        </div>

        {/* Predicted Value Card */}
        <div className="rounded-md bg-bg-card p-8 shadow-soft">
          <p className="text-sm font-medium text-text-sec">Estimated Value</p>
          <p className="mt-2 text-4xl font-bold tracking-tight text-brand-blue">
            {currencyFormatter.format(data.predicted_value)}
          </p>
        </div>

        {/* Detail Cards */}
        <div className="grid grid-cols-1 gap-grid sm:grid-cols-2">
          <div className="rounded-md bg-bg-card p-6 shadow-soft">
            <p className="text-sm font-medium text-text-sec">Confidence Range</p>
            <p className="mt-2 text-xl font-bold text-text-pri">
              {currencyFormatter.format(data.confidence_interval_low)} &ndash;{" "}
              {currencyFormatter.format(data.confidence_interval_high)}
            </p>
          </div>
          <div className="rounded-md bg-bg-card p-6 shadow-soft">
            <p className="text-sm font-medium text-text-sec">Model Version</p>
            <p className="mt-2 text-xl font-bold text-text-pri">{data.model_version}</p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ResultsPage;
