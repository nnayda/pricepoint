export interface ForecastRequest {
  address: string;
  city?: string;
  state?: string;
  zip_code?: string;
}

export interface ForecastResponse {
  address: string;
  predicted_value: number;
  confidence_interval_low: number;
  confidence_interval_high: number;
  model_version: string;
}

export interface HealthResponse {
  status: string;
}

export interface GeocodeResult {
  display_name: string;
  lat: number;
  lon: number;
  place_id: number;
  osm_type: string;
  osm_id: number;
  boundingbox: number[];
}

export interface GeocodeResponse {
  results: GeocodeResult[];
  cached: boolean;
}

// Property types
export interface PropertyImage {
  url: string;
  alt: string;
  is_primary: boolean;
}

export interface PropertyDetails {
  address: string;
  city: string;
  state: string;
  zip_code: string;
  lat: number;
  lon: number;
  bedrooms: number;
  bathrooms: number;
  sqft: number;
  lot_size_sqft: number;
  year_built: number;
  property_type: string;
  stories: number;
  garage_spaces: number;
  description: string;
  highlights: string[];
  images: PropertyImage[];
  listing_status?: string;
}

export interface ValuationData {
  listed_price?: number;
  last_sold_price?: number;
  last_sold_date?: string;
  redfin_estimate?: number;
  predicted_value?: number;
  confidence_interval_low?: number;
  confidence_interval_high?: number;
  model_version?: string;
  prediction_date?: string;
}

export interface InteriorFeatures {
  flooring: string[];
  appliances: string[];
  heating: string;
  cooling: string;
  fireplace: boolean;
  basement?: string;
}

export interface ExteriorFeatures {
  roof: string;
  siding: string;
  foundation: string;
  parking: string;
  pool: boolean;
  fence: string;
}

export interface FinancialDetails {
  hoa_monthly?: number;
  tax_annual: number;
  tax_year: number;
  assessed_value: number;
}

export interface SchoolNearby {
  name: string;
  address?: string;
  school_type: string;
  rating: number;
  distance_miles: number;
  drive_minutes: number;
  walk_minutes?: number;
}

export interface SaleHistoryEntry {
  date: string;
  price: number;
  event_type: string;
}

export interface TaxHistoryEntry {
  year: number;
  assessed_value: number;
  tax_amount: number;
}

export interface ClimateRisk {
  flood_risk: string;
  flood_score: number;
  fire_risk: string;
  fire_score: number;
}

export interface PropertyResponse {
  property: PropertyDetails;
  valuation: ValuationData;
  interior: InteriorFeatures;
  exterior: ExteriorFeatures;
  financial: FinancialDetails;
  schools: SchoolNearby[];
  sale_history: SaleHistoryEntry[];
  tax_history: TaxHistoryEntry[];
  climate_risk: ClimateRisk;
}

// Crime types
export interface CrimeHeatmapPoint {
  lat: number;
  lon: number;
  intensity: number;
}

export interface CrimeIncident {
  id: string;
  incident_type: string;
  category: string;
  date: string;
  lat: number;
  lon: number;
  description?: string;
}

export interface CrimeMetrics {
  total_incidents_1mi: number;
  incidents_per_1000_people: number;
  crime_z_score: number;
  trend: string;
}

export interface CrimeResponse {
  heatmap: CrimeHeatmapPoint[];
  incidents: CrimeIncident[];
  metrics: CrimeMetrics;
}

// POI types
export interface PointOfInterest {
  id: string;
  name: string;
  category: string;
  lat: number;
  lon: number;
  distance_miles: number;
  drive_minutes: number;
}

export interface PoisResponse {
  pois: PointOfInterest[];
}

// Greenspace types
export interface GreenspaceFeature {
  id: string;
  name: string;
  feature_type: string;
  lat: number;
  lon: number;
  distance_miles: number;
  acreage?: number;
}

export interface GreenspaceMetrics {
  parks_within_1mi: number;
  nearest_park_miles: number;
  total_green_acres_1mi: number;
  greenspace_z_score: number;
}

export interface GreenspaceResponse {
  features: GreenspaceFeature[];
  metrics: GreenspaceMetrics;
}

// Utility types
export interface UtilityFeature {
  id: string;
  name: string;
  feature_type: string;
  lat: number;
  lon: number;
  distance_miles: number;
}

export interface UtilitiesMetrics {
  nearest_highway_miles: number;
  nearest_railroad_miles: number;
  nearest_powerline_miles: number;
  nuisance_score: number;
}

export interface UtilitiesResponse {
  features: UtilityFeature[];
  metrics: UtilitiesMetrics;
}

// App types
export type MapTab = "crime-density" | "crime-incidents" | "pois" | "greenspace" | "utilities";

export interface MortgageInputs {
  homePrice: number;
  downPaymentPercent: number;
  interestRate: number;
  loanTermYears: number;
  annualTax: number;
  annualInsurance: number;
  monthlyHoa: number;
}

export interface MortgageBreakdown {
  principal: number;
  interest: number;
  tax: number;
  insurance: number;
  hoa: number;
  total: number;
}

export interface PoiPreference {
  id: string;
  name: string;
  category: string;
  enabled: boolean;
  isCustom?: boolean;
}

export interface MortgageDefaults {
  downPaymentPercent: number;
  interestRate: number;
  loanTermYears: number;
  annualInsurance: number;
}

export interface ForecastTimeline {
  date: string;
  value: number;
  low: number;
  high: number;
}

export interface FeatureAttribution {
  feature: string;
  display_name: string;
  impact_dollars: number;
}

export interface ComparableProperty {
  id: number;
  address: string;
  sale_price: number;
  sold_date: string;
  beds: number;
  baths: number;
  sqft: number;
  price_per_sqft: number;
  lat: number;
  lon: number;
  thumbnail_url?: string;
}

export interface ForecastData {
  predicted_value: number;
  confidence_low: number;
  confidence_high: number;
  model_version: string;
  timeline: ForecastTimeline[];
  feature_attributions: FeatureAttribution[];
  comparables: ComparableProperty[];
}

export interface RecentlyViewedItem {
  address: string;
  lat: number;
  lon: number;
  price?: number;
  thumbnailUrl?: string;
  viewedAt: string;
}

// ── Dashboard Types ──

export type DashboardTab =
  | "valuation"
  | "risks"
  | "demographics"
  | "schools"
  | "pois"
  | "negative-pois"
  | "greenspace"
  | "property-details";

export interface DashboardProperty {
  address: string;
  city: string;
  state: string;
  zip_code: string;
  neighborhood: string;
  lat: number;
  lon: number;
  bedrooms: number;
  bathrooms: number;
  sqft: number;
  lot_size_sqft: number;
  year_built: number;
  property_type: string;
  stories: number;
  garage_spaces: number;
  description: string;
  ai_summary: string;
  highlights: string[];
  images: string[];
  listing_status: "For Sale" | "Pending" | "Sold";
  days_on_market: number;
  mls_number: string;
  listed_date: string;
}

export interface DashboardValuation {
  listed_price: number;
  predicted_value: number;
  confidence_low: number;
  confidence_high: number;
  redfin_estimate: number;
  tax_assessment: number;
  price_per_sqft: number;
  neighborhood_median: number;
  neighborhood_max: number;
  model_version: string;
  prediction_date: string;
  verdict: string;
  verdict_detail: string;
}

export interface ShapFeature {
  feature: string;
  display_name: string;
  impact_dollars: number;
  group: string;
}

export interface PriceHistoryPoint {
  date: string;
  price: number;
  neighborhood_median?: number;
  event?: string;
}

export interface RiskCategory {
  id: string;
  label: string;
  score: number;
  level: "Low" | "Moderate" | "High" | "Very High";
  detail: string;
  icon: string;
}

export interface CrimeBreakdown {
  category: string;
  count: number;
  pct_change: number;
}

export interface DemographicDataset {
  race_ethnicity: { label: string; value: number; color: string }[];
  age_distribution: { range: string; male: number; female: number }[];
  median_income: number;
  income_brackets: { label: string; value: number }[];
  home_ownership_rate: number;
  median_home_value: number;
  population: number;
  population_trend: { year: number; population: number }[];
}

export type DemographicContext = "subdivision" | "neighborhood" | "town";

export interface DemographicData {
  geography_level: string;
  contexts: Record<DemographicContext, DemographicDataset>;
  race_ethnicity: { label: string; value: number; color: string }[];
  age_distribution: { range: string; male: number; female: number }[];
  median_income: number;
  income_brackets: { label: string; value: number }[];
  home_ownership_rate: number;
  median_home_value: number;
  population: number;
  population_trend: { year: number; population: number }[];
}

export interface DashboardSchool {
  name: string;
  address: string;
  school_type: "Elementary" | "Middle" | "High" | "K-8" | "Charter";
  rating: number;
  grades: string;
  distance_miles: number;
  drive_minutes: number;
  walk_minutes?: number;
  student_teacher_ratio: number;
  test_scores: number;
  assigned: boolean;
  lat: number;
  lon: number;
}

export interface DashboardPoi {
  id: string;
  name: string;
  category: string;
  subcategory: string;
  lat: number;
  lon: number;
  distance_miles: number;
  drive_minutes: number;
  icon: string;
}

export interface NegativePoi {
  id: string;
  name: string;
  type: string;
  severity: "Safe" | "Caution" | "Concern";
  distance_miles: number;
  lat: number;
  lon: number;
  detail: string;
}

export interface DashboardGreenspace {
  composite_score: number;
  walk_minutes_nearest: number;
  parks_within_1mi: number;
  trails_within_1mi: number;
  pct_greenspace: number;
  greenspace_z_score: number;
  tree_canopy_pct: number;
  has_dog_park: boolean;
  features: {
    id: string;
    name: string;
    type: string;
    lat: number;
    lon: number;
    distance_miles: number;
    acreage: number;
  }[];
}

export interface DashboardMortgage {
  home_price: number;
  down_payment_pct: number;
  interest_rate: number;
  loan_term_years: number;
  annual_tax: number;
  annual_insurance: number;
  monthly_hoa: number;
}

export interface ListingQualityScore {
  photo_score: number;
  description_score: number;
  listing_health: number;
}

export interface PropertyDetailSection {
  label: string;
  items: { key: string; value: string }[];
}

export interface ModelFeature {
  feature_name: string;
  raw_value: string;
  engineered_value: string;
  source: string;
}

export interface DashboardData {
  property: DashboardProperty;
  valuation: DashboardValuation;
  shap_features: ShapFeature[];
  price_history: PriceHistoryPoint[];
  risks: { overall_score: number; categories: RiskCategory[] };
  crime: {
    incidents: CrimeIncident[];
    heatmap: CrimeHeatmapPoint[];
    breakdown: CrimeBreakdown[];
    z_score: number;
    growth_rate: number;
    total_incidents: number;
  };
  demographics: DemographicData;
  schools: DashboardSchool[];
  pois: DashboardPoi[];
  negative_pois: NegativePoi[];
  greenspace: DashboardGreenspace;
  mortgage_defaults: DashboardMortgage;
  listing_quality: ListingQualityScore;
  property_details: PropertyDetailSection[];
  model_features: ModelFeature[];
}
