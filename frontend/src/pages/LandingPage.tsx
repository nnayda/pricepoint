import { useNavigate } from "react-router-dom";
import SearchBar from "../components/SearchBar/SearchBar";
import type { GeocodeResult } from "../types";

function LandingPage() {
  const navigate = useNavigate();

  function handleSelect(result: GeocodeResult) {
    navigate(`/forecast?address=${encodeURIComponent(result.display_name)}`);
  }

  return (
    <div className="flex flex-1 flex-col items-center justify-center px-4">
      <section className="flex w-full max-w-2xl flex-col items-center gap-8 text-center">
        <div className="flex flex-col gap-3">
          <h1 className="text-4xl font-bold tracking-tight text-text-pri">
            Know your home&apos;s future value
          </h1>
          <p className="text-lg font-medium text-text-sec">
            ML-powered forecasts combining neighborhood data, market trends, and economic
            indicators.
          </p>
        </div>

        <SearchBar onSelect={handleSelect} placeholder="Enter a property address..." />

        <div className="grid w-full grid-cols-1 gap-grid sm:grid-cols-3">
          <div className="rounded-md bg-bg-card p-6 shadow-soft">
            <p className="text-3xl font-bold text-brand-blue">50K+</p>
            <p className="mt-1 text-sm font-medium text-text-sec">Properties analyzed</p>
          </div>
          <div className="rounded-md bg-bg-card p-6 shadow-soft">
            <p className="text-3xl font-bold text-status-maint">94%</p>
            <p className="mt-1 text-sm font-medium text-text-sec">Prediction accuracy</p>
          </div>
          <div className="rounded-md bg-bg-card p-6 shadow-soft">
            <p className="text-3xl font-bold text-status-rented">12</p>
            <p className="mt-1 text-sm font-medium text-text-sec">Data sources</p>
          </div>
        </div>
      </section>
    </div>
  );
}

export default LandingPage;
