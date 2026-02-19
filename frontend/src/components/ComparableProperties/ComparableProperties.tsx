import type { ComparableProperty } from "../../types";

interface ComparablePropertiesProps {
  comparables: ComparableProperty[];
}

function formatPrice(value: number): string {
  return `$${value.toLocaleString()}`;
}

export default function ComparableProperties({ comparables }: ComparablePropertiesProps) {
  if (comparables.length === 0) {
    return (
      <div
        className="flex items-center justify-center rounded-lg border border-gray-200 bg-gray-50 p-8"
        data-testid="comparables-empty"
      >
        <p className="text-gray-500">No comparables found</p>
      </div>
    );
  }

  return (
    <div
      className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3"
      data-testid="comparables-grid"
    >
      {comparables.map((comp) => (
        <div
          key={comp.id}
          className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm transition-shadow hover:shadow-md"
          data-testid={`comparable-card-${comp.id}`}
        >
          {comp.thumbnail_url && (
            <img src={comp.thumbnail_url} alt={comp.address} className="h-40 w-full object-cover" />
          )}
          <div className="p-4">
            <h3 className="truncate text-sm font-semibold text-gray-900">{comp.address}</h3>
            <p className="mt-1 text-lg font-bold text-blue-600">{formatPrice(comp.sale_price)}</p>
            <p className="mt-1 text-xs text-gray-500">Sold {comp.sold_date}</p>
            <div className="mt-2 flex items-center gap-3 text-sm text-gray-600">
              <span>{comp.beds} bd</span>
              <span>{comp.baths} ba</span>
              <span>{comp.sqft.toLocaleString()} sqft</span>
            </div>
            <p className="mt-1 text-xs text-gray-500">{formatPrice(comp.price_per_sqft)}/sqft</p>
          </div>
        </div>
      ))}
    </div>
  );
}
