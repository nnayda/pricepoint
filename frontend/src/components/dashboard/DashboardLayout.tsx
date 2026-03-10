import type { ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import type { DashboardData } from "../../types";
import { useAuth } from "../../contexts/AuthContext";
import { useSavedProperty } from "../../hooks/useSavedProperty";
import DashboardNav from "./DashboardNav";
import DashboardBreadcrumb from "./DashboardBreadcrumb";
import DashboardTabs from "./DashboardTabs";
import PhotoCarousel from "./left/PhotoCarousel";
import KeyFactsCard from "./left/KeyFactsCard";
import DescriptionCard from "./left/DescriptionCard";

interface DashboardLayoutProps {
  data: DashboardData;
  banner?: ReactNode;
}

function DashboardLayout({ data, banner }: DashboardLayoutProps) {
  const { property } = data;
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const { isSaved, isLoading: isSaveLoading, toggle } = useSavedProperty(
    data.listing_id,
    isAuthenticated,
  );

  function handleSaveToggle() {
    if (!isAuthenticated) {
      navigate("/signin");
      return;
    }
    void toggle();
  }

  return (
    <div
      className="min-h-screen bg-[var(--th-bg-base)] font-db-sans"
    >
      <DashboardNav />
      <DashboardBreadcrumb
        city={`${property.city}, ${property.state}`}
        neighborhood={property.neighborhood}
        address={property.address}
      />

      {banner}

      <div className="mx-auto max-w-[1680px] px-1 py-6 xl:px-1.5">
        <div className="flex flex-col gap-4 xl:flex-row">
          {/* Left Column — sticky on desktop */}
          <aside className="scrollbar-none w-full shrink-0 xl:sticky xl:top-[calc(64px+36px+12px)] xl:h-[calc(100vh-64px-36px-24px)] xl:w-[360px] xl:overflow-y-auto">
            <div className="flex flex-col gap-4">
              <PhotoCarousel images={property.images} />
              <KeyFactsCard
                property={property}
                valuation={data.valuation}
                notFound={data.notFound}
                listingId={data.listing_id}
                isSaved={isSaved}
                isSaveLoading={isSaveLoading}
                onSaveToggle={handleSaveToggle}
              />
              <DescriptionCard property={property} listingQuality={data.listing_quality} />
            </div>
          </aside>

          {/* Right Column — tab content */}
          <main className="isolate min-w-0 flex-1">
            <div className="rounded-[var(--radius-db-lg)] border border-[var(--color-db-border-subtle)] bg-[var(--color-db-surface)] shadow-[var(--shadow-db-card)]">
              <DashboardTabs data={data} />
            </div>
          </main>
        </div>
      </div>

      {/* Floating Compare Button (FAB) */}
      <button
        type="button"
        className="fixed right-6 bottom-6 z-50 flex h-14 items-center gap-2 rounded-full bg-[var(--color-db-accent)] px-5 shadow-lg transition-transform hover:scale-105 hover:bg-[var(--color-db-accent-hover)]"
        aria-label="Compare properties"
        onClick={() =>
          navigate(
            `/compare/${encodeURIComponent(property.address)}?lat=${property.lat}&lon=${property.lon}`,
          )
        }
      >
        <svg
          className="h-5 w-5 text-white"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4"
          />
        </svg>
        <span className="text-sm font-semibold text-white">Compare</span>
      </button>
    </div>
  );
}

export default DashboardLayout;
