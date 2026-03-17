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

export interface StatsResponse {
  listing_count: number;
}

export interface GeocodeResult {
  display_name: string;
  lat: number;
  lon: number;
  place_id: number | null;
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
  price_per_sqft?: number;
  days_on_market?: number;
  listed_date?: string;
  hoa_monthly?: number;
  redfin_url?: string;
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
  laundry?: string;
}

export interface ExteriorFeatures {
  roof: string;
  siding: string;
  foundation: string;
  parking: string;
  pool: boolean;
  fence: string;
  lot_features?: string;
}

export interface UtilityDetails {
  water?: string;
  sewer?: string;
  electric?: string;
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
  school_level?: string;
  rating: number | null;
  grades?: string;
  distance_miles: number;
  drive_minutes: number;
  walk_minutes?: number;
  student_teacher_ratio?: number;
  enrollment?: number;
  assigned?: boolean;
  lat?: number;
  lon?: number;
  pct_frl_eligible?: number;
  in_district?: boolean;
}

export interface SchoolDistrictInfo {
  name: string;
  geoid: string;
  district_type: string | null;
  geojson: GeoJSON.GeoJsonObject | null;
  is_home: boolean;
  label_lat: number | null;
  label_lon: number | null;
}

export interface SchoolsNearbyResponse {
  schools: SchoolNearby[];
  school_districts: SchoolDistrictInfo[];
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

export interface ApiListingQuality {
  description_score?: number;
  quality_reasoning?: string;
  positive_factors?: string[];
}

export interface PropertyResponse {
  listing_id?: number | null;
  property: PropertyDetails;
  valuation: ValuationData;
  interior: InteriorFeatures;
  exterior: ExteriorFeatures;
  financial: FinancialDetails;
  utilities?: UtilityDetails;
  schools: SchoolNearby[];
  sale_history: SaleHistoryEntry[];
  tax_history: TaxHistoryEntry[];
  climate_risk: ClimateRisk;
  listing_quality?: ApiListingQuality;
  feature_attributions?: FeatureAttribution[];
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
  address?: string;
  crime_group?: string | null;
  offense_class?: string | null;
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
  subcategory?: string;
  address?: string;
}

export interface PoisResponse {
  pois: PointOfInterest[];
}

export interface PoisSearchResponse {
  pois: PointOfInterest[];
  total_count: number;
  query: string;
}

// Saved POI types
export interface PoiAutocompleteItem {
  match_type: "brand" | "name";
  match_value: string;
  display_name: string;
  category: string | null;
  count: number;
}

export interface PoiAutocompleteResponse {
  results: PoiAutocompleteItem[];
  query: string;
}

export interface SavedPoiResponse {
  id: number;
  match_type: "brand" | "name";
  match_value: string;
  display_name: string;
  category: string | null;
  user_category: string | null;
  marker_color: string | null;
  marker_image_url: string | null;
  alternate_names?: string[] | null;
  created_at: string;
}

export interface SavedPoiMatch {
  id: string;
  name: string;
  address: string | null;
  lat: number;
  lon: number;
  distance_miles: number;
  drive_minutes: number;
}

export interface SavedPoiNearbyGroup {
  saved_poi_id: number;
  display_name: string;
  category: string | null;
  match_type: string;
  matches: SavedPoiMatch[];
  user_category: string | null;
  marker_color: string | null;
  marker_image_url: string | null;
}

export interface SavedPoiNearbyResponse {
  groups: SavedPoiNearbyGroup[];
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
  length_miles?: number;
}

export interface GreenspaceMetrics {
  parks_within_1mi: number;
  nearest_park_miles: number;
  nearest_greenway_miles: number;
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
  nearest_cell_tower_miles: number;
  nearest_transmission_line_miles: number;
  nearest_power_plant_miles: number;
  nearest_pipeline_miles: number;
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
  group?: string;
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
  | "police"
  | "demographics"
  | "schools"
  | "pois"
  | "nuisances"
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
  sold_date?: string;
  redfin_url?: string;
}

export interface DashboardValuation {
  listed_price: number;
  predicted_value?: number;
  confidence_low?: number;
  confidence_high?: number;
  redfin_estimate: number;
  tax_assessment: number;
  price_per_sqft: number;
  neighborhood_median?: number;
  neighborhood_max?: number;
  model_version?: string;
  prediction_date?: string;
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
  price?: number;
  neighborhood_median?: number;
  event?: string;
  sale_price?: number;
  sale_event?: string;
  tax_assessed?: number;
}

export interface NeighborhoodMedianPoint {
  date: string;
  median_value: number;
}

export interface NeighborhoodValuationHistory {
  tract_geoid: string;
  sample_size: number;
  monthly_medians: NeighborhoodMedianPoint[];
}

export interface NeighborhoodProperty {
  address: string;
  lat: number;
  lon: number;
  effective_price: number;
  listing_status: string;
  sold_date?: string | null;
}

export interface NeighborhoodPropertiesResponse {
  tract_geoid: string;
  sample_size: number;
  properties: NeighborhoodProperty[];
  tract_boundary?: GeoJSON.Geometry | null;
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

export interface RaceEthnicityTrendPoint {
  year: number;
  white: number;
  black: number;
  hispanic: number;
  asian: number;
  other: number;
}

export interface AgeDistributionTrendPoint {
  year: number;
  under18: number;
  age18_22: number;
  age23_29: number;
  age30_39: number;
  age40_49: number;
  age50_64: number;
  age65plus: number;
}

export interface IncomeTrendPoint {
  year: number;
  median_income: number;
}

export interface HomeOwnershipTrendPoint {
  year: number;
  ownership_rate: number;
}

export interface MedianAgeTrendPoint {
  year: number;
  median_age: number;
}

export interface RaceSubgroup {
  label: string;
  value: number;
  percentage: number;
  color: string;
}

export interface RaceDetailedBreakdown {
  race_category: string;
  total: number;
  subgroups: RaceSubgroup[];
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
  race_ethnicity_trend: RaceEthnicityTrendPoint[];
  age_distribution_trend: AgeDistributionTrendPoint[];
  income_trend: IncomeTrendPoint[];
  home_ownership_trend: HomeOwnershipTrendPoint[];
  median_age_trend: MedianAgeTrendPoint[];
  race_detailed?: Record<string, RaceDetailedBreakdown>;
}

export type DemographicContext = "subdivision" | "block_group" | "neighborhood" | "town" | "county";
export type DemographicSubTab = "population" | "race" | "age" | "income" | "ownership";

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
  race_ethnicity_trend: RaceEthnicityTrendPoint[];
  age_distribution_trend: AgeDistributionTrendPoint[];
  income_trend: IncomeTrendPoint[];
  home_ownership_trend: HomeOwnershipTrendPoint[];
  median_age_trend: MedianAgeTrendPoint[];
  benchmarks?: Record<string, DemographicDataset>;
}

export interface DemographicsApiContextData {
  race_ethnicity: { label: string; value: number }[];
  age_distribution: { range: string; male: number; female: number }[];
  median_income: number;
  income_brackets: { label: string; value: number }[];
  home_ownership_rate: number;
  median_home_value: number;
  population: number;
  population_trend: { year: number; population: number }[];
  race_ethnicity_trend: RaceEthnicityTrendPoint[];
  age_distribution_trend: AgeDistributionTrendPoint[];
  income_trend: IncomeTrendPoint[];
  home_ownership_trend: HomeOwnershipTrendPoint[];
  median_age_trend: MedianAgeTrendPoint[];
  race_detailed?: Record<
    string,
    {
      race_category: string;
      total: number;
      subgroups: { label: string; value: number; percentage: number }[];
    }
  >;
}

export interface ChoroplethFeatureProperties {
  geoid: string;
  name: string;
  is_home: boolean;
  population: number;
  median_income: number;
  median_age: number;
  home_ownership_rate: number;
  dominant_race: string;
  dominant_race_pct: number;
  pct_under_18: number;
  pct_65_plus: number;
  pct_white: number;
  pct_black: number;
  pct_hispanic: number;
  pct_asian: number;
  pct_other: number;
}

export interface DemographicsApiResponse {
  contexts: Record<string, DemographicsApiContextData>;
  benchmarks: Record<string, DemographicsApiContextData>;
}

export interface DashboardSchool {
  name: string;
  address: string;
  school_type: "Elementary" | "Middle" | "High" | "K-8" | "Charter";
  rating: number | null;
  grades: string;
  distance_miles: number;
  drive_minutes: number;
  walk_minutes?: number;
  student_teacher_ratio: number;
  enrollment?: number;
  test_scores: number;
  assigned: boolean;
  lat: number;
  lon: number;
  pct_frl_eligible?: number;
  in_district: boolean;
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
  isSaved?: boolean;
  marker_color?: string;
  marker_image_url?: string;
  address?: string;
  saved_place_name?: string;
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

export interface NuisanceSourceItem {
  id: string;
  name: string;
  source_type: string;
  severity: "Caution" | "Concern";
  distance_miles: number;
  lat: number | null;
  lon: number | null;
  detail: string;
  noise_min_db: number | null;
  noise_band: string | null;
}

export interface NuisanceSourcesResponse {
  sources: NuisanceSourceItem[];
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

// Risk types
export type InfrastructureType =
  | "cell_tower"
  | "transmission_line"
  | "power_plant"
  | "nat_gas_pipeline"
  | "petroleum_pipeline";

export interface RiskFeature {
  id: string;
  name: string;
  infrastructure_type: InfrastructureType;
  severity: "Safe" | "Caution" | "Concern";
  distance_miles: number;
  lat: number;
  lon: number;
  detail: string;
  metadata: Record<string, string | number | null>;
}

export interface RisksApiResponse {
  features: RiskFeature[];
}

// Data request types
export interface DataRequestCreate {
  address: string;
  lat: number;
  lon: number;
  email?: string;
}

export interface DataRequestResponse {
  id: number;
  address: string;
  status: string;
  created_at: string;
}

// ── Comparables Types ──

export interface CompFeatureGroup {
  category: string;
  features: Record<string, number | string | boolean | null>;
}

export interface CompNuisance {
  name: string;
  source_type: string;
  severity: string;
  distance_miles: number;
  detail: string;
}

export interface CompRisk {
  name: string;
  infrastructure_type: string;
  severity: string;
  distance_miles: number;
  detail: string;
}

export interface CompPropertyDetail {
  listing_id: number;
  address: string;
  city: string;
  state: string;
  zip_code: string;
  lat: number;
  lon: number;
  sold_price: number | null;
  sold_date: string | null;
  listing_price: number | null;
  beds: number;
  baths: number;
  sqft: number | null;
  lot_size: number | null;
  year_built: number | null;
  garage_spaces: number;
  price_per_sqft: number | null;
  photos: string[];
  description_score: number | null;
  photo_score: number | null;
  feature_groups: CompFeatureGroup[];
  nuisances: CompNuisance[];
  risks: CompRisk[];
  similarity_distance: number | null;
}

export interface ComparablesResponse {
  subject: CompPropertyDetail;
  comparables: CompPropertyDetail[];
  total_candidates: number;
}

export interface ComparablesSearchCriteria {
  time_period_months: 3 | 6 | 9 | 12;
  distance_miles: 0.5 | 1 | 2 | 5;
  same_schools: boolean;
  sqft_pct: number;
  lot_pct: number;
  same_beds: boolean;
  same_baths: boolean;
  year_built_diff: number;
}

// ── Model Methodology Types ──

export interface ModelMetadata {
  model_name: string;
  model_version: string;
  run_id: string;
  training_date: string;
  n_features: number;
  n_training_samples: number;
  algorithm: string;
  hyperparameters: Record<string, string | number | null>;
}

export interface ModelMetrics {
  mae: number | null;
  rmse: number | null;
  mape: number | null;
  r2: number | null;
  median_ae: number | null;
  mae_mean: number | null;
  mae_std: number | null;
  rmse_mean: number | null;
  rmse_std: number | null;
  r2_mean: number | null;
  r2_std: number | null;
  data_n_rows: number | null;
  data_n_features: number | null;
  data_target_mean: number | null;
  data_target_median: number | null;
  data_target_std: number | null;
}

export interface FeatureImportanceItem {
  feature: string;
  gain: number;
}

export interface ModelMethodologyResponse {
  metadata: ModelMetadata;
  metrics: ModelMetrics;
  feature_importance: FeatureImportanceItem[];
  available_plots: string[];
  available_eda_plots: string[];
}

export interface FeatureCatalogEntry {
  name: string;
  category: string;
  sql_type: string;
  source: string;
  derivation: string;
  example: string;
  default: string;
}

export interface FeatureCatalogResponse {
  features: FeatureCatalogEntry[];
  categories: string[];
}

export interface DashboardData {
  listing_id?: number | null;
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
  nuisances: NegativePoi[];
  greenspace: DashboardGreenspace;
  mortgage_defaults: DashboardMortgage;
  listing_quality?: ListingQualityScore;
  property_details: PropertyDetailSection[];
  model_features: ModelFeature[];
  neighborhood_properties?: NeighborhoodProperty[];
  tract_boundary?: GeoJSON.Geometry | null;
  /** True when the property was not found in the database */
  notFound?: boolean;
}
