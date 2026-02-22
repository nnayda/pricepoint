import axios from "axios";
import type {
  DataRequestCreate,
  DataRequestResponse,
  PropertyResponse,
  SchoolNearby,
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
): Promise<SchoolNearby[]> {
  const { data } = await client.get<SchoolNearby[]>("/api/schools/nearby", {
    params: { lat, lon, radius_miles: radiusMiles, limit },
  });
  return data;
}

export async function submitDataRequest(request: DataRequestCreate): Promise<DataRequestResponse> {
  const { data } = await client.post<DataRequestResponse>("/api/data-requests", request);
  return data;
}
