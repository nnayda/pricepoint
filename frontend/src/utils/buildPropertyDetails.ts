import type { PropertyResponse, PropertyDetailSection } from "../types";

/** Values treated as empty / unknown — these items are omitted. */
const EMPTY_VALUES = new Set(["unknown", "none", "", "0"]);

function isPresent(value: string | undefined | null): value is string {
  if (!value) return false;
  return !EMPTY_VALUES.has(value.toLowerCase().trim());
}

function formatCurrency(amount: number): string {
  return amount.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  });
}

function formatNumber(n: number): string {
  return n.toLocaleString("en-US");
}

function pushIf(
  items: { key: string; value: string }[],
  key: string,
  value: string | undefined | null,
) {
  if (isPresent(value)) {
    items.push({ key, value: value! });
  }
}

/**
 * Build PropertyDetailSection[] from the API PropertyResponse.
 * Sections with zero items are excluded.
 */
export function buildPropertyDetails(resp: PropertyResponse): PropertyDetailSection[] {
  const sections: PropertyDetailSection[] = [];

  // Interior
  const interior: { key: string; value: string }[] = [];
  if (resp.interior.flooring.length > 0) {
    interior.push({ key: "Flooring", value: resp.interior.flooring.join(", ") });
  }
  if (resp.interior.appliances.length > 0) {
    interior.push({ key: "Appliances", value: resp.interior.appliances.join(", ") });
  }
  pushIf(interior, "Heating", resp.interior.heating);
  pushIf(interior, "Cooling", resp.interior.cooling);
  interior.push({ key: "Fireplace", value: resp.interior.fireplace ? "Yes" : "No" });
  pushIf(interior, "Basement", resp.interior.basement);
  pushIf(interior, "Laundry", resp.interior.laundry);
  if (interior.length > 0) sections.push({ label: "Interior", items: interior });

  // Exterior
  const exterior: { key: string; value: string }[] = [];
  pushIf(exterior, "Roof", resp.exterior.roof);
  pushIf(exterior, "Siding", resp.exterior.siding);
  pushIf(exterior, "Foundation", resp.exterior.foundation);
  pushIf(exterior, "Parking", resp.exterior.parking);
  exterior.push({ key: "Pool", value: resp.exterior.pool ? "Yes" : "No" });
  pushIf(exterior, "Fence", resp.exterior.fence);
  pushIf(exterior, "Lot Features", resp.exterior.lot_features);
  if (exterior.length > 0) sections.push({ label: "Exterior", items: exterior });

  // Utilities
  if (resp.utilities) {
    const utilities: { key: string; value: string }[] = [];
    pushIf(utilities, "Water", resp.utilities.water);
    pushIf(utilities, "Sewer", resp.utilities.sewer);
    pushIf(utilities, "Electric", resp.utilities.electric);
    if (utilities.length > 0) sections.push({ label: "Utilities", items: utilities });
  }

  // HOA & Financial
  const financial: { key: string; value: string }[] = [];
  if (resp.financial.hoa_monthly != null && resp.financial.hoa_monthly > 0) {
    financial.push({ key: "HOA (Monthly)", value: formatCurrency(resp.financial.hoa_monthly) });
  }
  if (resp.financial.tax_year > 0) {
    financial.push({ key: "Tax Year", value: String(resp.financial.tax_year) });
  }
  if (resp.financial.tax_annual > 0) {
    financial.push({ key: "Annual Tax", value: formatCurrency(resp.financial.tax_annual) });
  }
  if (resp.financial.assessed_value > 0) {
    financial.push({ key: "Assessed Value", value: formatCurrency(resp.financial.assessed_value) });
  }
  if (financial.length > 0) sections.push({ label: "HOA & Financial", items: financial });

  // Listing Information
  const listing: { key: string; value: string }[] = [];
  pushIf(listing, "Status", resp.property.listing_status);
  pushIf(listing, "Listed Date", resp.property.listed_date);
  if (resp.property.days_on_market != null && resp.property.days_on_market > 0) {
    listing.push({ key: "Days on Market", value: String(resp.property.days_on_market) });
  }
  pushIf(listing, "Property Type", resp.property.property_type);
  if (resp.property.sqft > 0) {
    listing.push({ key: "Square Footage", value: formatNumber(resp.property.sqft) });
  }
  if (resp.property.lot_size_sqft > 0) {
    listing.push({ key: "Lot Size (sqft)", value: formatNumber(resp.property.lot_size_sqft) });
  }
  if (resp.property.year_built > 0) {
    listing.push({ key: "Year Built", value: String(resp.property.year_built) });
  }
  if (resp.property.stories > 0) {
    listing.push({ key: "Stories", value: String(resp.property.stories) });
  }
  if (resp.property.garage_spaces > 0) {
    listing.push({ key: "Garage Spaces", value: String(resp.property.garage_spaces) });
  }
  if (listing.length > 0) sections.push({ label: "Listing Information", items: listing });

  return sections;
}
