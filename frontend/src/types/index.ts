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
