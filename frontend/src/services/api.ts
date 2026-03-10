import axios from "axios";
import type { ForecastRequest, ForecastResponse, HealthResponse, StatsResponse } from "../types";

const client = axios.create({
  baseURL: "/",
  headers: { "Content-Type": "application/json" },
});

export async function getHealth(): Promise<HealthResponse> {
  const { data } = await client.get<HealthResponse>("/health");
  return data;
}

export async function postForecast(request: ForecastRequest): Promise<ForecastResponse> {
  const { data } = await client.post<ForecastResponse>("/api/forecast", request);
  return data;
}

export async function getStats(): Promise<StatsResponse> {
  const { data } = await client.get<StatsResponse>("/api/stats");
  return data;
}
