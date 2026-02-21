import { useMemo } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import DashboardLayout from "../components/dashboard/DashboardLayout";
import PropertyNotFoundDialog from "../components/PropertyNotFoundDialog";
import { usePropertyLookup } from "../hooks/usePropertyLookup";
import { mockDashboardData } from "../data/mockDashboardData";
import { mapPropertyResponse } from "../utils/mapPropertyResponse";

function PropertyDashboardPage() {
  const { address } = useParams<{ address: string }>();
  const [searchParams] = useSearchParams();
  const lat = searchParams.get("lat") ? Number(searchParams.get("lat")) : null;
  const lon = searchParams.get("lon") ? Number(searchParams.get("lon")) : null;
  const decodedAddress = address ? decodeURIComponent(address) : null;

  const { data, loading, notFound, error } = usePropertyLookup(lat, lon, decodedAddress);

  const dashboardData = useMemo(() => {
    if (data) return mapPropertyResponse(data);
    return mockDashboardData;
  }, [data]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[var(--color-db-bg)]">
        <div className="flex flex-col items-center gap-3">
          <div
            className="h-8 w-8 animate-spin rounded-full border-4 border-[var(--color-db-accent)] border-t-transparent"
            role="status"
          >
            <span className="sr-only">Loading property data...</span>
          </div>
          <p className="text-sm text-[var(--color-db-text-secondary)]">Loading property data...</p>
        </div>
      </div>
    );
  }

  if (notFound && decodedAddress && lat != null && lon != null) {
    return <PropertyNotFoundDialog address={decodedAddress} lat={lat} lon={lon} />;
  }

  if (error || lat == null || lon == null) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[var(--color-db-bg)]">
        <div className="mx-4 max-w-md rounded-[var(--radius-db-lg)] border border-[var(--color-db-border)] bg-[var(--color-db-surface)] p-6 text-center">
          <p className="mb-2 text-sm font-medium text-[var(--color-db-red)]">
            {error || "Invalid property URL — missing location parameters."}
          </p>
          <a href="/" className="text-sm text-[var(--color-db-accent)] hover:underline">
            Back to search
          </a>
        </div>
      </div>
    );
  }

  return <DashboardLayout data={dashboardData} />;
}

export default PropertyDashboardPage;
