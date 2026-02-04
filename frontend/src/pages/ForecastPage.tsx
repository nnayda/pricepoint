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
    <div>
      <h2>Forecast</h2>
      <form onSubmit={handleSubmit} style={{ marginBottom: "1.5rem" }}>
        <input
          type="text"
          value={address}
          onChange={(e) => setAddress(e.target.value)}
          placeholder="Enter property address"
          style={{ padding: "0.5rem", width: "300px", marginRight: "0.5rem" }}
        />
        <button type="submit" disabled={loading}>
          {loading ? "Loading..." : "Get Forecast"}
        </button>
      </form>

      {error && <p style={{ color: "red" }}>Error: {error}</p>}
      {data && <PropertyCard forecast={data} />}
    </div>
  );
}

export default ForecastPage;
