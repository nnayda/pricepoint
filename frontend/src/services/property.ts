import axios from "axios";
import type {
  PropertyResponse,
  CrimeResponse,
  PoisResponse,
  GreenspaceResponse,
  UtilitiesResponse,
  ComparableProperty,
  FeatureAttribution,
} from "../types";

const client = axios.create({
  baseURL: "/",
  headers: { "Content-Type": "application/json" },
});

export async function getProperty(
  lat: number,
  lon: number,
  address: string,
): Promise<PropertyResponse> {
  const { data } = await client.get<PropertyResponse>("/api/property", {
    params: { lat, lon, address },
  });
  return data;
}

export async function getCrime(
  lat: number,
  lon: number,
  radiusMiles?: number,
  daysBack?: number,
): Promise<CrimeResponse> {
  const { data } = await client.get<CrimeResponse>("/api/crime", {
    params: {
      lat,
      lon,
      ...(radiusMiles !== undefined && { radius_miles: radiusMiles }),
      ...(daysBack !== undefined && { days_back: daysBack }),
    },
  });
  return data;
}

export async function getPois(
  lat: number,
  lon: number,
  radiusMiles?: number,
): Promise<PoisResponse> {
  const { data } = await client.get<PoisResponse>("/api/pois", {
    params: { lat, lon, ...(radiusMiles !== undefined && { radius_miles: radiusMiles }) },
  });
  return data;
}

export async function getGreenspace(
  lat: number,
  lon: number,
  radiusMiles?: number,
): Promise<GreenspaceResponse> {
  const { data } = await client.get<GreenspaceResponse>("/api/greenspace", {
    params: { lat, lon, ...(radiusMiles !== undefined && { radius_miles: radiusMiles }) },
  });
  return data;
}

export async function getUtilities(
  lat: number,
  lon: number,
  radiusMiles?: number,
): Promise<UtilitiesResponse> {
  const { data } = await client.get<UtilitiesResponse>("/api/utilities", {
    params: { lat, lon, ...(radiusMiles !== undefined && { radius_miles: radiusMiles }) },
  });
  return data;
}

export async function getComparables(
  lat: number,
  lon: number,
  beds: number,
  sqft: number,
  radius?: number,
): Promise<ComparableProperty[]> {
  const { data } = await client.get<ComparableProperty[]>("/api/comparables", {
    params: {
      lat,
      lon,
      beds,
      sqft,
      ...(radius !== undefined && { radius_miles: radius }),
    },
  });
  return data;
}

export async function getFeatureImportance(propertyId: number): Promise<FeatureAttribution[]> {
  const { data } = await client.get<FeatureAttribution[]>(`/api/forecast/importance/${propertyId}`);
  return data;
}
