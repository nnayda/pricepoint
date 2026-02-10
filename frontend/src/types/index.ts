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
