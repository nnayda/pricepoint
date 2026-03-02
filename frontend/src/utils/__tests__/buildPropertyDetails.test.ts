import { describe, it, expect } from "vitest";
import { buildPropertyDetails } from "../buildPropertyDetails";
import type { PropertyResponse } from "../../types";

function makeResponse(overrides: Partial<PropertyResponse> = {}): PropertyResponse {
  return {
    property: {
      address: "100 Main St",
      city: "Cary",
      state: "NC",
      zip_code: "27513",
      lat: 35.79,
      lon: -78.78,
      bedrooms: 4,
      bathrooms: 3,
      sqft: 2800,
      lot_size_sqft: 10000,
      year_built: 2005,
      property_type: "Single Family",
      stories: 2,
      garage_spaces: 2,
      description: "Nice house",
      highlights: [],
      images: [],
      listing_status: "FOR SALE",
      days_on_market: 15,
      listed_date: "2025-01-01",
      ...overrides.property,
    },
    valuation: {
      listed_price: 500000,
      ...overrides.valuation,
    },
    interior: {
      flooring: ["Hardwood", "Tile"],
      appliances: ["Dishwasher", "Microwave"],
      heating: "Forced Air",
      cooling: "Central Air",
      fireplace: true,
      basement: "Finished",
      laundry: "In Unit",
      ...overrides.interior,
    },
    exterior: {
      roof: "Shingle",
      siding: "Vinyl",
      foundation: "Slab",
      parking: "2-Car Garage",
      pool: false,
      fence: "Wood",
      lot_features: "Cul-de-sac",
      ...overrides.exterior,
    },
    financial: {
      hoa_monthly: 85,
      tax_annual: 4200,
      tax_year: 2024,
      assessed_value: 410000,
      ...overrides.financial,
    },
    utilities: {
      water: "City Water",
      sewer: "Public Sewer",
      electric: "Duke Energy",
      ...overrides.utilities,
    },
    schools: [],
    sale_history: [],
    tax_history: [],
    climate_risk: { flood_risk: "Low", flood_score: 1, fire_risk: "Low", fire_score: 1 },
    ...overrides,
  };
}

describe("buildPropertyDetails", () => {
  it("produces correct sections from a populated response", () => {
    const sections = buildPropertyDetails(makeResponse());
    const labels = sections.map((s) => s.label);
    expect(labels).toEqual([
      "Interior",
      "Exterior",
      "Utilities",
      "HOA & Financial",
      "Listing Information",
    ]);
  });

  it("populates interior section items correctly", () => {
    const sections = buildPropertyDetails(makeResponse());
    const interior = sections.find((s) => s.label === "Interior")!;
    expect(interior.items.find((i) => i.key === "Flooring")?.value).toBe("Hardwood, Tile");
    expect(interior.items.find((i) => i.key === "Appliances")?.value).toBe("Dishwasher, Microwave");
    expect(interior.items.find((i) => i.key === "Heating")?.value).toBe("Forced Air");
    expect(interior.items.find((i) => i.key === "Fireplace")?.value).toBe("Yes");
    expect(interior.items.find((i) => i.key === "Basement")?.value).toBe("Finished");
    expect(interior.items.find((i) => i.key === "Laundry")?.value).toBe("In Unit");
  });

  it("populates exterior section items correctly", () => {
    const sections = buildPropertyDetails(makeResponse());
    const exterior = sections.find((s) => s.label === "Exterior")!;
    expect(exterior.items.find((i) => i.key === "Roof")?.value).toBe("Shingle");
    expect(exterior.items.find((i) => i.key === "Pool")?.value).toBe("No");
    expect(exterior.items.find((i) => i.key === "Fence")?.value).toBe("Wood");
    expect(exterior.items.find((i) => i.key === "Lot Features")?.value).toBe("Cul-de-sac");
  });

  it("populates utilities section", () => {
    const sections = buildPropertyDetails(makeResponse());
    const utils = sections.find((s) => s.label === "Utilities")!;
    expect(utils.items).toHaveLength(3);
    expect(utils.items.find((i) => i.key === "Water")?.value).toBe("City Water");
  });

  it("formats currency correctly in financial section", () => {
    const sections = buildPropertyDetails(makeResponse());
    const fin = sections.find((s) => s.label === "HOA & Financial")!;
    expect(fin.items.find((i) => i.key === "HOA (Monthly)")?.value).toBe("$85");
    expect(fin.items.find((i) => i.key === "Annual Tax")?.value).toBe("$4,200");
    expect(fin.items.find((i) => i.key === "Assessed Value")?.value).toBe("$410,000");
  });

  it("omits items with 'Unknown' values", () => {
    const sections = buildPropertyDetails(
      makeResponse({
        interior: {
          flooring: [],
          appliances: [],
          heating: "Unknown",
          cooling: "Unknown",
          fireplace: false,
        },
        exterior: {
          roof: "Unknown",
          siding: "Unknown",
          foundation: "Unknown",
          parking: "None",
          pool: false,
          fence: "None",
        },
      }),
    );
    const interior = sections.find((s) => s.label === "Interior");
    if (interior) {
      expect(interior.items.find((i) => i.key === "Heating")).toBeUndefined();
      expect(interior.items.find((i) => i.key === "Cooling")).toBeUndefined();
    }
    const exterior = sections.find((s) => s.label === "Exterior");
    if (exterior) {
      expect(exterior.items.find((i) => i.key === "Roof")).toBeUndefined();
      expect(exterior.items.find((i) => i.key === "Parking")).toBeUndefined();
      expect(exterior.items.find((i) => i.key === "Fence")).toBeUndefined();
    }
  });

  it("only has boolean items when all text data is unknown/empty", () => {
    const sections = buildPropertyDetails(
      makeResponse({
        property: {
          address: "",
          city: "",
          state: "",
          zip_code: "",
          lat: 0,
          lon: 0,
          bedrooms: 0,
          bathrooms: 0,
          sqft: 0,
          lot_size_sqft: 0,
          year_built: 0,
          property_type: "",
          stories: 0,
          garage_spaces: 0,
          description: "",
          highlights: [],
          images: [],
        },
        interior: {
          flooring: [],
          appliances: [],
          heating: "Unknown",
          cooling: "Unknown",
          fireplace: false,
        },
        exterior: {
          roof: "Unknown",
          siding: "Unknown",
          foundation: "Unknown",
          parking: "None",
          pool: false,
          fence: "None",
        },
        financial: {
          hoa_monthly: 0,
          tax_annual: 0,
          tax_year: 0,
          assessed_value: 0,
        },
        utilities: undefined,
      }),
    );
    // Interior/Exterior still have boolean items (Fireplace/Pool)
    expect(sections).toHaveLength(2);
    const interior = sections.find((s) => s.label === "Interior")!;
    expect(interior.items).toHaveLength(1);
    expect(interior.items[0].key).toBe("Fireplace");
    const exterior = sections.find((s) => s.label === "Exterior")!;
    expect(exterior.items).toHaveLength(1);
    expect(exterior.items[0].key).toBe("Pool");
  });

  it("excludes utilities section when not present", () => {
    const sections = buildPropertyDetails(makeResponse({ utilities: undefined }));
    expect(sections.find((s) => s.label === "Utilities")).toBeUndefined();
  });

  it("includes listing information from property details", () => {
    const sections = buildPropertyDetails(makeResponse());
    const listing = sections.find((s) => s.label === "Listing Information")!;
    expect(listing.items.find((i) => i.key === "Status")?.value).toBe("FOR SALE");
    expect(listing.items.find((i) => i.key === "Year Built")?.value).toBe("2005");
    expect(listing.items.find((i) => i.key === "Garage Spaces")?.value).toBe("2");
  });
});
