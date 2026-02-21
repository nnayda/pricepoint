import axios from "axios";
import type { DataRequestCreate, DataRequestResponse, PropertyResponse } from "../types";

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

export async function submitDataRequest(
  request: DataRequestCreate,
): Promise<DataRequestResponse> {
  const { data } = await client.post<DataRequestResponse>("/api/data-requests", request);
  return data;
}
