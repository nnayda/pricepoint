import { describe, it, expect } from "vitest";
import type { GeocodeResult, GeocodeResponse } from "../index";

describe("GeocodeResult", () => {
  it("holds a single geocoding result", () => {
    const result: GeocodeResult = {
      display_name: "123 Main St, Cary, NC 27513",
      lat: 35.7915,
      lon: -78.7811,
      place_id: 12345,
      osm_type: "way",
      osm_id: 67890,
      boundingbox: [35.79, 35.8, -78.79, -78.77],
    };

    expect(result.display_name).toBe("123 Main St, Cary, NC 27513");
    expect(result.lat).toBe(35.7915);
    expect(result.lon).toBe(-78.7811);
    expect(result.place_id).toBe(12345);
    expect(result.osm_type).toBe("way");
    expect(result.osm_id).toBe(67890);
    expect(result.boundingbox).toEqual([35.79, 35.8, -78.79, -78.77]);
  });
});

describe("GeocodeResponse", () => {
  it("holds a list of results and cached flag", () => {
    const response: GeocodeResponse = {
      results: [
        {
          display_name: "123 Main St, Cary, NC 27513",
          lat: 35.7915,
          lon: -78.7811,
          place_id: 12345,
          osm_type: "way",
          osm_id: 67890,
          boundingbox: [35.79, 35.8, -78.79, -78.77],
        },
      ],
      cached: false,
    };

    expect(response.results).toHaveLength(1);
    expect(response.cached).toBe(false);
  });

  it("supports empty results", () => {
    const response: GeocodeResponse = {
      results: [],
      cached: true,
    };

    expect(response.results).toHaveLength(0);
    expect(response.cached).toBe(true);
  });

  it("supports multiple results", () => {
    const response: GeocodeResponse = {
      results: [
        {
          display_name: "123 Main St, Cary, NC",
          lat: 35.79,
          lon: -78.78,
          place_id: 1,
          osm_type: "way",
          osm_id: 100,
          boundingbox: [35.78, 35.8, -78.79, -78.77],
        },
        {
          display_name: "123 Main St, Raleigh, NC",
          lat: 35.82,
          lon: -78.64,
          place_id: 2,
          osm_type: "node",
          osm_id: 200,
          boundingbox: [35.81, 35.83, -78.65, -78.63],
        },
      ],
      cached: false,
    };

    expect(response.results).toHaveLength(2);
    expect(response.results[0].display_name).toContain("Cary");
    expect(response.results[1].display_name).toContain("Raleigh");
  });
});
