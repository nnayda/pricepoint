import axios from "axios";

const client = axios.create({
  baseURL: "/",
  headers: { "Content-Type": "application/json" },
});

export interface SavedPropertyResponse {
  id: number;
  listing_id: number;
  notes: string | null;
  created_at: string;
  listing_address: string | null;
  city: string | null;
  state: string | null;
  zip_code: string | null;
  listing_status: string | null;
  listing_price: number | null;
  sold_price: number | null;
  num_beds: number | null;
  num_baths: number | null;
  sqft: number | null;
  year_built: number | null;
  photo_url: string | null;
  lat: number | null;
  lon: number | null;
}

function authHeaders(token: string) {
  return { Authorization: `Bearer ${token}` };
}

export async function getSavedProperties(token: string): Promise<SavedPropertyResponse[]> {
  const { data } = await client.get<SavedPropertyResponse[]>("/api/saved", {
    headers: authHeaders(token),
  });
  return data;
}

export async function saveProperty(
  token: string,
  listingId: number,
  notes?: string,
): Promise<SavedPropertyResponse> {
  const { data } = await client.post<SavedPropertyResponse>(
    "/api/saved",
    { listing_id: listingId, notes: notes ?? null },
    { headers: authHeaders(token) },
  );
  return data;
}

export async function deleteSavedProperty(token: string, savedId: number): Promise<void> {
  await client.delete(`/api/saved/${savedId}`, {
    headers: authHeaders(token),
  });
}
