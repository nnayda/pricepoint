import type {
  PropertyResponse,
  DashboardData,
  DashboardProperty,
  DashboardValuation,
} from "../types";
import { mockDashboardData } from "../data/mockDashboardData";
import { buildPriceHistory } from "./buildPriceHistory";
import { buildPropertyDetails } from "./buildPropertyDetails";

/**
 * Normalize listing status from the API ("FOR SALE", "SOLD", "PENDING")
 * to the display format used by the dashboard ("For Sale", "Sold", "Pending").
 */
function normalizeStatus(raw?: string): "For Sale" | "Pending" | "Sold" {
  if (!raw) return "For Sale";
  const upper = raw.toUpperCase();
  if (upper.includes("SOLD")) return "Sold";
  if (upper.includes("PENDING")) return "Pending";
  return "For Sale";
}

/**
 * Extract the street-only portion of an address by stripping the
 * city / state / zip suffix when present (e.g. "102 Loch Ryan Way, Cary, NC 27513" → "102 Loch Ryan Way").
 */
function streetOnly(address: string, city: string): string {
  if (!city) return address;
  const idx = address.indexOf(`, ${city}`);
  if (idx !== -1) return address.slice(0, idx);
  return address;
}

/**
 * Map a PropertyResponse from the API into the DashboardData structure.
 * Fields that the API provides are mapped directly; everything else
 * falls back to mock data so the dashboard still renders fully.
 */
export function mapPropertyResponse(resp: PropertyResponse): DashboardData {
  const p = resp.property;
  const v = resp.valuation;

  const property: DashboardProperty = {
    address: streetOnly(p.address, p.city),
    city: p.city,
    state: p.state,
    zip_code: p.zip_code,
    neighborhood: mockDashboardData.property.neighborhood,
    lat: p.lat,
    lon: p.lon,
    bedrooms: p.bedrooms,
    bathrooms: p.bathrooms,
    sqft: p.sqft,
    lot_size_sqft: p.lot_size_sqft,
    year_built: p.year_built,
    property_type: p.property_type,
    stories: p.stories,
    garage_spaces: p.garage_spaces,
    description: p.description,
    ai_summary: resp.listing_quality?.quality_reasoning ?? "",
    highlights:
      resp.listing_quality?.positive_factors && resp.listing_quality.positive_factors.length > 0
        ? resp.listing_quality.positive_factors
        : p.highlights.length > 0
          ? p.highlights
          : mockDashboardData.property.highlights,
    images:
      p.images.length > 0 ? p.images.map((img) => img.url) : mockDashboardData.property.images,
    listing_status: normalizeStatus(p.listing_status),
    days_on_market: p.days_on_market ?? mockDashboardData.property.days_on_market,
    mls_number: mockDashboardData.property.mls_number,
    listed_date: p.listed_date ?? mockDashboardData.property.listed_date,
    sold_date: v.last_sold_date ?? undefined,
  };

  const displayPrice = v.listed_price ?? v.last_sold_price ?? 0;

  const pricePerSqft =
    p.price_per_sqft ?? (p.sqft > 0 && displayPrice ? Math.round(displayPrice / p.sqft) : 0);

  const valuation: DashboardValuation = {
    listed_price: displayPrice,
    predicted_value: v.predicted_value ?? undefined,
    confidence_low: v.confidence_interval_low ?? undefined,
    confidence_high: v.confidence_interval_high ?? undefined,
    redfin_estimate: v.redfin_estimate ?? mockDashboardData.valuation.redfin_estimate,
    tax_assessment: resp.financial.assessed_value ?? mockDashboardData.valuation.tax_assessment,
    price_per_sqft: pricePerSqft,
    neighborhood_median: mockDashboardData.valuation.neighborhood_median,
    neighborhood_max: mockDashboardData.valuation.neighborhood_max,
    model_version: v.model_version ?? undefined,
    prediction_date: v.prediction_date ?? undefined,
    verdict: mockDashboardData.valuation.verdict,
    verdict_detail: mockDashboardData.valuation.verdict_detail,
  };

  return {
    listing_id: resp.listing_id ?? null,
    property,
    valuation,
    shap_features:
      resp.feature_attributions && resp.feature_attributions.length > 0
        ? resp.feature_attributions.map((fa) => ({
            feature: fa.feature,
            display_name: fa.display_name,
            impact_dollars: fa.impact_dollars,
            group: fa.group ?? "Other",
          }))
        : mockDashboardData.shap_features,
    price_history:
      resp.sale_history.length > 0 || resp.tax_history.length > 0
        ? buildPriceHistory(resp.sale_history, resp.tax_history, [])
        : mockDashboardData.price_history,
    risks: mockDashboardData.risks,
    crime: mockDashboardData.crime,
    demographics: mockDashboardData.demographics, // overridden by useDemographics hook when API data available
    schools:
      resp.schools.length > 0
        ? resp.schools.map((s) => ({
            name: s.name,
            address: s.address ?? "",
            school_type: (s.school_level ?? s.school_type ?? "Elementary") as
              | "Elementary"
              | "Middle"
              | "High"
              | "K-8"
              | "Charter",
            rating: s.rating,
            grades: s.grades ?? "",
            distance_miles: s.distance_miles,
            drive_minutes: s.drive_minutes,
            walk_minutes: s.walk_minutes,
            student_teacher_ratio: s.student_teacher_ratio ?? 0,
            enrollment: s.enrollment,
            test_scores: 0,
            assigned: s.assigned ?? false,
            lat: s.lat ?? 0,
            lon: s.lon ?? 0,
            pct_frl_eligible: s.pct_frl_eligible,
            in_district: s.in_district ?? false,
          }))
        : mockDashboardData.schools,
    pois: [],
    nuisances: [],
    greenspace: mockDashboardData.greenspace,
    mortgage_defaults: {
      ...mockDashboardData.mortgage_defaults,
      home_price: displayPrice || mockDashboardData.mortgage_defaults.home_price,
      annual_tax: resp.financial.tax_annual ?? mockDashboardData.mortgage_defaults.annual_tax,
      monthly_hoa: p.hoa_monthly ?? mockDashboardData.mortgage_defaults.monthly_hoa,
    },
    listing_quality:
      resp.listing_quality?.description_score != null
        ? {
            photo_score: mockDashboardData.listing_quality?.photo_score ?? 0,
            listing_health: mockDashboardData.listing_quality?.listing_health ?? 0,
            description_score: resp.listing_quality.description_score,
          }
        : undefined,
    property_details: (() => {
      const sections = buildPropertyDetails(resp);
      return sections.length > 0 ? sections : mockDashboardData.property_details;
    })(),
    model_features: mockDashboardData.model_features,
  };
}
