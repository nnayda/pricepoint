import { useState } from "react";
import PropertyCard from "../components/PropertyCard/PropertyCard";
import { useApi } from "../hooks/useApi";
import { postForecast } from "../services/api";

function ForecastPage() {
  const [address, setAddress] = useState("");
  const { data, loading, error, execute } = useApi(postForecast);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (address.trim()) {
      execute({ address: address.trim() });
    }
  };

  return (
    <div className="flex flex-1 flex-col items-center px-4 py-8">
      <div className="flex w-full max-w-2xl flex-col gap-grid">
        <h2 className="text-2xl font-bold tracking-tight text-text-pri">Forecast</h2>

        <form onSubmit={handleSubmit} className="flex gap-3">
          <input
            type="text"
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            placeholder="Enter property address"
            className="flex-1 rounded-pill bg-bg-card px-5 py-2.5 text-base font-medium text-text-pri shadow-card outline-none placeholder:text-text-sec focus:ring-2 focus:ring-brand-blue"
          />
          <button
            type="submit"
            disabled={loading}
            className="rounded-pill bg-brand-blue px-6 py-2.5 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            {loading ? "Loading..." : "Get Forecast"}
          </button>
        </form>

        {error && <p className="text-base font-medium text-status-rented">Error: {error}</p>}
        {data && <PropertyCard forecast={data} />}
      </div>
    </div>
  );
}

export default ForecastPage;
