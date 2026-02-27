import axios from "axios";
import type {
  DataRequestCreate,
  DataRequestResponse,
  DemographicsApiResponse,
  GreenspaceResponse,
  NeighborhoodValuationHistory,
  NuisanceSourcesResponse,
  PoisSearchResponse,
  PropertyResponse,
  RisksApiResponse,
  SchoolsNearbyResponse,
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

export async function getSchoolsNearby(
  lat: number,
  lon: number,
  radiusMiles: number = 10,
  limit: number = 20,
): Promise<SchoolsNearbyResponse> {
  const { data } = await client.get<SchoolsNearbyResponse>("/api/schools/nearby", {
    params: { lat, lon, radius_miles: radiusMiles, limit },
  });
  return data;
}

export async function getDemographics(lat: number, lon: number): Promise<DemographicsApiResponse> {
  const { data } = await client.get<DemographicsApiResponse>("/api/demographics", {
    params: { lat, lon },
  });
  return data;
}

export async function getDemographicsChoropleth(
  context: string,
  swLat: number,
  swLon: number,
  neLat: number,
  neLon: number,
  homeLat?: number,
  homeLon?: number,
): Promise<GeoJSON.Feature[]> {
  const { data } = await client.get<GeoJSON.Feature[]>("/api/demographics/choropleth", {
    params: {
      context,
      sw_lat: swLat,
      sw_lon: swLon,
      ne_lat: neLat,
      ne_lon: neLon,
      ...(homeLat != null && homeLon != null ? { home_lat: homeLat, home_lon: homeLon } : {}),
    },
  });
  return data;
}

export interface NeighborhoodValuation {
  tract_geoid: string;
  median_value: number | null;
  max_value: number | null;
  sample_size: number;
}

export async function getNeighborhoodValuation(
  lat: number,
  lon: number,
): Promise<NeighborhoodValuation> {
  const { data } = await client.get<NeighborhoodValuation>("/api/neighborhood/valuation", {
    params: { lat, lon },
  });
  return data;
}

export async function getNeighborhoodValuationHistory(
  lat: number,
  lon: number,
): Promise<NeighborhoodValuationHistory> {
  const { data } = await client.get<NeighborhoodValuationHistory>(
    "/api/neighborhood/valuation/history",
    { params: { lat, lon } },
  );
  return data;
}

export async function searchPois(
  lat: number,
  lon: number,
  query: string,
  radiusMiles: number = 5,
  limit: number = 20,
): Promise<PoisSearchResponse> {
  const { data } = await client.get<PoisSearchResponse>("/api/pois/search", {
    params: { lat, lon, query, radius_miles: radiusMiles, limit },
  });
  return data;
}

export interface NoiseResponse {
  type: string;
  features: {
    type: string;
    geometry: object;
    properties: {
      noise_band: string;
      noise_min_db: number;
      noise_max_db: number | null;
      source_layer: string;
      area_sq_m: number | null;
    };
  }[];
}

export async function getNoiseData(
  lat: number,
  lon: number,
  radiusMiles: number = 2,
): Promise<NoiseResponse> {
  const { data } = await client.get<NoiseResponse>("/api/nuisances/noise", {
    params: { lat, lon, radius_miles: radiusMiles },
  });
  return data;
}

export async function getNuisanceSources(
  lat: number,
  lon: number,
): Promise<NuisanceSourcesResponse> {
  const { data } = await client.get<NuisanceSourcesResponse>("/api/nuisances/sources", {
    params: { lat, lon },
  });
  return data;
}

export async function getNuisanceGeometries(
  lat: number,
  lon: number,
  radiusMiles: number = 2,
): Promise<GeoJSON.FeatureCollection> {
  const { data } = await client.get<GeoJSON.FeatureCollection>("/api/nuisances/geometries", {
    params: { lat, lon, radius_miles: radiusMiles },
  });
  return data;
}

export async function getRisksData(
  lat: number,
  lon: number,
  radiusMiles: number = 3,
): Promise<RisksApiResponse> {
  const { data } = await client.get<RisksApiResponse>("/api/risks", {
    params: { lat, lon, radius_miles: radiusMiles },
  });
  return data;
}

export async function getGreenspace(
  lat: number,
  lon: number,
  radiusMiles: number = 7,
): Promise<GreenspaceResponse> {
  const { data } = await client.get<GreenspaceResponse>("/api/greenspace", {
    params: { lat, lon, radius_miles: radiusMiles },
  });
  return data;
}

export async function submitDataRequest(request: DataRequestCreate): Promise<DataRequestResponse> {
  const { data } = await client.post<DataRequestResponse>("/api/data-requests", request);
  return data;
}
