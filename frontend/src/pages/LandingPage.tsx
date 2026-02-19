import { useNavigate } from "react-router-dom";
import SearchBar from "../components/SearchBar/SearchBar";
import RecentlyViewed from "../components/RecentlyViewed/RecentlyViewed";
import { startViewTransition } from "../utils/viewTransition";
import type { GeocodeResult } from "../types";

function LandingPage() {
  const navigate = useNavigate();

  function handleSelect(result: GeocodeResult) {
    const url = `/results?address=${encodeURIComponent(result.display_name)}&lat=${result.lat}&lon=${result.lon}`;
    startViewTransition(() => {
      navigate(url);
    });
  }

  return (
    <div className="flex flex-1 flex-col items-center justify-center px-4">
      <section className="flex w-full max-w-2xl flex-col items-center gap-6 text-center sm:gap-8">
        <div className="flex flex-col gap-2 sm:gap-3">
          <p className="text-base font-bold tracking-tight text-brand-blue sm:text-lg">
            PricePoint
          </p>
          <h1 className="text-2xl font-bold tracking-tight text-text-pri sm:text-4xl">
            Know your home&apos;s future value
          </h1>
          <p className="text-base font-medium text-text-sec sm:text-lg">
            ML-powered forecasts combining neighborhood data, market trends, and economic
            indicators.
          </p>
        </div>

        <SearchBar onSelect={handleSelect} placeholder="Enter a property address..." />

        <RecentlyViewed />

        <div className="grid w-full grid-cols-1 gap-grid sm:grid-cols-3">
          <div className="rounded-md bg-bg-card p-4 shadow-soft sm:p-6">
            <p className="text-2xl font-bold text-brand-blue sm:text-3xl">50K+</p>
            <p className="mt-1 text-sm font-medium text-text-sec">Properties analyzed</p>
          </div>
          <div className="rounded-md bg-bg-card p-4 shadow-soft sm:p-6">
            <p className="text-2xl font-bold text-status-maint sm:text-3xl">94%</p>
            <p className="mt-1 text-sm font-medium text-text-sec">Prediction accuracy</p>
          </div>
          <div className="rounded-md bg-bg-card p-4 shadow-soft sm:p-6">
            <p className="text-2xl font-bold text-status-rented sm:text-3xl">12</p>
            <p className="mt-1 text-sm font-medium text-text-sec">Data sources</p>
          </div>
        </div>
      </section>
    </div>
  );
}

export default LandingPage;
