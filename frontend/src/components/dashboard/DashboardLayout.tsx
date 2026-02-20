import type { DashboardData } from "../../types";
import DashboardNav from "./DashboardNav";
import DashboardBreadcrumb from "./DashboardBreadcrumb";
import DashboardTabs from "./DashboardTabs";
import PhotoCarousel from "./left/PhotoCarousel";
import KeyFactsCard from "./left/KeyFactsCard";
import DescriptionCard from "./left/DescriptionCard";

interface DashboardLayoutProps {
  data: DashboardData;
}

function DashboardLayout({ data }: DashboardLayoutProps) {
  const { property } = data;

  return (
    <div
      className="min-h-screen bg-[var(--color-db-bg)]"
      style={{ fontFamily: "var(--font-db-sans)" }}
    >
      <DashboardNav />
      <DashboardBreadcrumb
        city={`${property.city}, ${property.state}`}
        neighborhood={property.neighborhood}
        address={property.address}
      />

      <div className="mx-auto max-w-[1680px] px-4 py-6 xl:px-6">
        <div className="flex flex-col gap-6 xl:flex-row">
          {/* Left Column — sticky on desktop */}
          <aside className="w-full shrink-0 xl:sticky xl:top-[calc(64px+36px+12px)] xl:h-[calc(100vh-64px-36px-24px)] xl:w-[380px] xl:overflow-y-auto xl:scrollbar-none">
            <div className="flex flex-col gap-4">
              <PhotoCarousel images={property.images} />
              <KeyFactsCard property={property} valuation={data.valuation} />
              <DescriptionCard property={property} />
            </div>
          </aside>

          {/* Right Column — tab content */}
          <main className="min-w-0 flex-1">
            <div className="rounded-[var(--radius-db-lg)] border border-[var(--color-db-border-subtle)] bg-[var(--color-db-surface)] shadow-[var(--shadow-db-card)]">
              <DashboardTabs data={data} />
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}

export default DashboardLayout;
