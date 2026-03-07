import { Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { useSavedProperties } from "../hooks/useSavedProperties";
import DashboardNav from "../components/dashboard/DashboardNav";
import type { SavedPropertyResponse } from "../services/saved";

function statusColor(status: string | null): { bg: string; text: string } {
  if (!status) return { bg: "rgba(107,114,128,0.85)", text: "#ffffff" };
  const s = status.toLowerCase();
  if (s.includes("sold")) return { bg: "rgba(185,28,28,0.85)", text: "#ffffff" };
  if (s.includes("active") || s.includes("for sale"))
    return { bg: "rgba(21,128,61,0.85)", text: "#ffffff" };
  if (s.includes("pending") || s.includes("contingent"))
    return { bg: "rgba(161,98,7,0.85)", text: "#ffffff" };
  return { bg: "rgba(107,114,128,0.85)", text: "#ffffff" };
}

function formatPrice(price: number | null): string {
  if (price == null) return "--";
  return "$" + price.toLocaleString("en-US", { maximumFractionDigits: 0 });
}

function PropertyCard({
  property,
  onRemove,
  onClick,
}: {
  property: SavedPropertyResponse;
  onRemove: () => void;
  onClick: () => void;
}) {
  const badge = statusColor(property.listing_status);
  const displayPrice = property.sold_price ?? property.listing_price;

  return (
    <div
      role="article"
      className="group relative cursor-pointer overflow-hidden rounded-xl transition-shadow hover:shadow-lg"
      style={{
        backgroundColor: "var(--th-bg-surface)",
        border: "1px solid var(--color-db-border)",
      }}
      onClick={onClick}
      data-testid="property-card"
    >
      {/* Photo */}
      <div className="relative h-44 overflow-hidden bg-gray-200">
        {property.photo_url ? (
          <img
            src={property.photo_url}
            alt={property.listing_address ?? "Property"}
            className="h-full w-full object-cover transition-transform group-hover:scale-105"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-gray-100 to-gray-200">
            <svg
              className="h-12 w-12 text-gray-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M2.25 21h19.5M3.75 21V6.75a.75.75 0 01.75-.75h6a.75.75 0 01.75.75V21m7.5 0V10.5a.75.75 0 01.75-.75h3a.75.75 0 01.75.75V21"
              />
            </svg>
          </div>
        )}
        {/* Status badge */}
        {property.listing_status && (
          <span
            className="absolute left-3 top-3 rounded-full px-2.5 py-0.5 text-xs font-semibold"
            style={{ backgroundColor: badge.bg, color: badge.text }}
          >
            {property.listing_status}
          </span>
        )}
        {/* Remove button */}
        <button
          type="button"
          aria-label={`Remove ${property.listing_address ?? "property"}`}
          onClick={(e) => {
            e.stopPropagation();
            onRemove();
          }}
          className="absolute right-2 top-2 rounded-full bg-white/80 p-1.5 opacity-0 shadow transition-opacity hover:bg-white group-hover:opacity-100"
        >
          <svg className="h-4 w-4 text-red-500" viewBox="0 0 20 20" fill="currentColor">
            <path
              fillRule="evenodd"
              d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
              clipRule="evenodd"
            />
          </svg>
        </button>
      </div>

      {/* Content */}
      <div className="p-4">
        <p
          className="truncate text-base font-semibold"
          style={{ color: "var(--color-db-text-primary)" }}
        >
          {property.listing_address ?? "Unknown address"}
        </p>
        {(property.city || property.state || property.zip_code) && (
          <p className="truncate text-sm" style={{ color: "var(--color-db-text-secondary)" }}>
            {[property.city, property.state].filter(Boolean).join(", ")}
            {property.zip_code ? ` ${property.zip_code}` : ""}
          </p>
        )}

        <p className="mt-2 text-lg font-bold" style={{ color: "var(--color-db-text-primary)" }}>
          {formatPrice(displayPrice)}
        </p>

        {/* Stats row */}
        <div
          className="mt-2 flex items-center gap-3 text-sm"
          style={{ color: "var(--color-db-text-secondary)" }}
        >
          {property.num_beds != null && <span>{property.num_beds} bd</span>}
          {property.num_baths != null && <span>{property.num_baths} ba</span>}
          {property.sqft != null && <span>{property.sqft.toLocaleString()} sqft</span>}
          {property.year_built != null && <span>Built {property.year_built}</span>}
        </div>
      </div>
    </div>
  );
}

function SavedPropertiesPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { properties, isLoading, error, remove } = useSavedProperties(isAuthenticated);
  const navigate = useNavigate();

  if (authLoading) return null;
  if (!isAuthenticated) return <Navigate to="/signin" replace />;

  function handleCardClick(prop: SavedPropertyResponse) {
    const addr = prop.listing_address ?? "";
    let url = `/property/${encodeURIComponent(addr)}`;
    if (prop.lat != null && prop.lon != null) {
      url += `?lat=${prop.lat}&lon=${prop.lon}`;
    }
    navigate(url);
  }

  return (
    <div className="font-db-sans min-h-screen" style={{ backgroundColor: "var(--color-db-bg)" }}>
      <DashboardNav />
      <div className="mx-auto max-w-6xl px-4 pb-12 pt-24 sm:px-6">
        <h1 className="mb-8 text-2xl font-bold" style={{ color: "var(--color-db-text-primary)" }}>
          Saved Properties
        </h1>

        {error && (
          <div
            className="mb-6 rounded-lg px-4 py-3 text-sm"
            role="alert"
            style={{
              backgroundColor: "rgba(239, 68, 68, 0.1)",
              color: "#ef4444",
            }}
          >
            {error}
          </div>
        )}

        {isLoading && (
          <div className="flex items-center justify-center py-20">
            <div
              className="h-8 w-8 animate-spin rounded-full border-4 border-t-transparent"
              style={{ borderColor: "var(--color-db-accent)", borderTopColor: "transparent" }}
              role="status"
            >
              <span className="sr-only">Loading...</span>
            </div>
          </div>
        )}

        {!isLoading && !error && properties.length === 0 && (
          <div className="flex flex-col items-center justify-center py-20">
            <svg
              className="mb-4 h-16 w-16"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1}
              style={{ color: "var(--color-db-text-muted)" }}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M17.593 3.322c1.1.128 1.907 1.077 1.907 2.185V21L12 17.25 4.5 21V5.507c0-1.108.806-2.057 1.907-2.185a48.507 48.507 0 0111.186 0z"
              />
            </svg>
            <p
              className="mb-2 text-lg font-medium"
              style={{ color: "var(--color-db-text-secondary)" }}
            >
              No saved properties
            </p>
            <p className="mb-4 text-sm" style={{ color: "var(--color-db-text-muted)" }}>
              Properties you save will appear here.
            </p>
            <a
              href="/"
              className="rounded-lg px-4 py-2 text-sm font-medium text-white"
              style={{ backgroundColor: "var(--color-db-accent)" }}
            >
              Search properties
            </a>
          </div>
        )}

        {!isLoading && !error && properties.length > 0 && (
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
            {properties.map((prop) => (
              <PropertyCard
                key={prop.id}
                property={prop}
                onRemove={() => remove(prop.id)}
                onClick={() => handleCardClick(prop)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default SavedPropertiesPage;
