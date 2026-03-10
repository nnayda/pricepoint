import axios from "axios";
import type { PoiAutocompleteResponse, SavedPoiNearbyResponse, SavedPoiResponse } from "../types";

const client = axios.create({
  baseURL: "/",
  headers: { "Content-Type": "application/json" },
});

function authHeaders(token: string) {
  return { Authorization: `Bearer ${token}` };
}

export async function autocompletePoIs(
  query: string,
  limit = 10,
): Promise<PoiAutocompleteResponse> {
  const { data } = await client.get<PoiAutocompleteResponse>("/api/pois/autocomplete", {
    params: { q: query, limit },
  });
  return data;
}

export async function getSavedPois(token: string): Promise<SavedPoiResponse[]> {
  const { data } = await client.get<SavedPoiResponse[]>("/api/saved-pois", {
    headers: authHeaders(token),
  });
  return data;
}

export async function createSavedPoi(
  token: string,
  body: {
    match_type: string;
    match_value: string;
    display_name: string;
    category?: string | null;
    user_category?: string | null;
    marker_color?: string | null;
    marker_image_url?: string | null;
  },
): Promise<SavedPoiResponse> {
  const { data } = await client.post<SavedPoiResponse>("/api/saved-pois", body, {
    headers: authHeaders(token),
  });
  return data;
}

export async function updateSavedPoi(
  token: string,
  id: number,
  body: {
    user_category?: string | null;
    marker_color?: string | null;
    marker_image_url?: string | null;
  },
): Promise<SavedPoiResponse> {
  const { data } = await client.patch<SavedPoiResponse>(`/api/saved-pois/${id}`, body, {
    headers: authHeaders(token),
  });
  return data;
}

export async function deleteSavedPoi(token: string, id: number): Promise<void> {
  await client.delete(`/api/saved-pois/${id}`, {
    headers: authHeaders(token),
  });
}

export async function getSavedPoisNearby(
  token: string,
  lat: number,
  lon: number,
  radiusMiles = 10,
): Promise<SavedPoiNearbyResponse> {
  const { data } = await client.get<SavedPoiNearbyResponse>("/api/pois/saved-nearby", {
    params: { lat, lon, radius_miles: radiusMiles },
    headers: authHeaders(token),
  });
  return data;
}
