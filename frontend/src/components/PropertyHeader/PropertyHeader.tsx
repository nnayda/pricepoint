import { useState } from "react";
import { Bed, Bath, Ruler, TreePine, Calendar } from "lucide-react";
import type { PropertyDetails } from "../../types";

interface PropertyHeaderProps {
  property: PropertyDetails;
}

const fmt = new Intl.NumberFormat("en-US");

function formatLotSize(sqft: number): string {
  if (sqft > 10890) {
    return `${(sqft / 43560).toFixed(2)} acres`;
  }
  return `${fmt.format(sqft)} sqft`;
}

function statusColor(status: string): string {
  switch (status.toUpperCase()) {
    case "SOLD":
      return "bg-status-rented";
    case "FOR SALE":
      return "bg-status-maint";
    case "PENDING":
      return "bg-brand-blue";
    case "OFF MARKET":
      return "bg-status-vacant text-text-pri";
    default:
      return "bg-status-maint";
  }
}

function statusLabel(status: string): string {
  switch (status.toUpperCase()) {
    case "SOLD":
      return "Sold";
    case "FOR SALE":
      return "For Sale";
    case "PENDING":
      return "Pending";
    case "OFF MARKET":
      return "Off Market";
    default:
      return status;
  }
}

function PropertyHeader({ property }: PropertyHeaderProps) {
  const [imgError, setImgError] = useState(false);

  const listingStatus = property.listing_status ?? "FOR SALE";

  const stats = [
    {
      icon: Bed,
      value: property.bedrooms,
      ariaLabel: `${property.bedrooms} bedroom${property.bedrooms !== 1 ? "s" : ""}`,
    },
    {
      icon: Bath,
      value: property.bathrooms,
      ariaLabel: `${property.bathrooms} bathroom${property.bathrooms !== 1 ? "s" : ""}`,
    },
    {
      icon: Ruler,
      value: `${fmt.format(property.sqft)} sqft`,
      ariaLabel: `${fmt.format(property.sqft)} square feet`,
    },
    {
      icon: TreePine,
      value: formatLotSize(property.lot_size_sqft),
      ariaLabel: `Lot size ${formatLotSize(property.lot_size_sqft)}`,
    },
    {
      icon: Calendar,
      value: property.year_built,
      ariaLabel: `Built in ${property.year_built}`,
    },
  ];

  const streetAddress = property.address.split(",")[0];

  const primaryUrl = property.images.find((i) => i.is_primary)?.url ?? property.images[0]?.url;
  const primaryAlt = property.images.find((i) => i.is_primary)?.alt ?? property.images[0]?.alt;

  const placeholder = (
    <div
      className="flex h-48 w-full items-center justify-center bg-gray-200 sm:h-64 md:h-72 lg:h-80"
      aria-hidden="true"
    >
      <svg
        className="h-12 w-12 text-gray-400"
        fill="none"
        stroke="currentColor"
        strokeWidth={1.5}
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M2.25 12l8.954-8.955a1.126 1.126 0 011.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25"
        />
      </svg>
    </div>
  );

  return (
    <section
      aria-label="Property header"
      className="overflow-hidden rounded-lg bg-bg-card/80 shadow-soft backdrop-blur-md"
    >
      <div className="relative">
        {property.images.length > 0 && !imgError ? (
          <img
            src={primaryUrl}
            alt={primaryAlt}
            className="h-48 w-full object-cover sm:h-64 md:h-72 lg:h-80"
            onError={() => setImgError(true)}
          />
        ) : (
          placeholder
        )}
        <div className="absolute bottom-3 left-3 flex items-center gap-2">
          <span
            className={`rounded-full px-3 py-1 text-sm font-semibold text-white shadow-card ${statusColor(listingStatus)}`}
            data-testid="status-badge"
          >
            {statusLabel(listingStatus)}
          </span>
          <span className="rounded-full bg-black/50 px-3 py-1 text-sm font-medium text-white">
            {property.property_type}
          </span>
        </div>
      </div>
      <div className="p-5 sm:p-8">
        <h1 className="text-xl font-bold text-text-pri sm:text-2xl">{streetAddress}</h1>
        <p className="mt-1 text-sm font-medium text-text-sec">
          {property.city}, {property.state} {property.zip_code}
        </p>
        <div
          className="mt-4 flex flex-wrap items-center gap-4 sm:gap-5"
          role="list"
          aria-label="Property stats"
        >
          {stats.map((s, idx) => (
            <div key={s.ariaLabel} className="contents">
              {idx > 0 && <span className="h-5 w-px bg-text-sec/20" aria-hidden="true" />}
              <div role="listitem" aria-label={s.ariaLabel} className="flex items-center gap-1.5">
                <s.icon size={18} className="text-text-sec" aria-hidden="true" />
                <span className="text-xl font-bold text-text-pri sm:text-2xl">{s.value}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

export default PropertyHeader;
