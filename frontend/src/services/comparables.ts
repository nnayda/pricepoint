import axios from "axios";
import type { ComparablesResponse, ComparablesSearchCriteria } from "../types";

const client = axios.create({
  baseURL: "/",
  headers: { "Content-Type": "application/json" },
});

export async function getComparables(
  lat: number,
  lon: number,
  address: string,
  criteria: ComparablesSearchCriteria,
): Promise<ComparablesResponse> {
  const { data } = await client.get<ComparablesResponse>("/api/comparables/search", {
    params: {
      lat,
      lon,
      address,
      time_period_months: criteria.time_period_months,
      distance_miles: criteria.distance_miles,
      same_schools: criteria.same_schools,
      sqft_pct: criteria.sqft_pct,
      lot_pct: criteria.lot_pct,
      same_beds: criteria.same_beds,
      same_baths: criteria.same_baths,
      year_built_diff: criteria.year_built_diff,
    },
  });
  return data;
}
