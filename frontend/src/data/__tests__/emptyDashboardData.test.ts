import { describe, it, expect } from "vitest";
import { buildEmptyDashboardData } from "../emptyDashboardData";

describe("buildEmptyDashboardData", () => {
  it("sets address, lat, lon from arguments", () => {
    const data = buildEmptyDashboardData("123 Main St", 35.5, -78.7);
    expect(data.property.address).toBe("123 Main St");
    expect(data.property.lat).toBe(35.5);
    expect(data.property.lon).toBe(-78.7);
  });

  it("zeroes out numeric property fields", () => {
    const data = buildEmptyDashboardData("123 Main St", 35.5, -78.7);
    expect(data.property.bedrooms).toBe(0);
    expect(data.property.bathrooms).toBe(0);
    expect(data.property.sqft).toBe(0);
    expect(data.property.year_built).toBe(0);
  });

  it("returns empty arrays for listing-dependent data", () => {
    const data = buildEmptyDashboardData("123 Main St", 35.5, -78.7);
    expect(data.shap_features).toEqual([]);
    expect(data.price_history).toEqual([]);
    expect(data.property_details).toEqual([]);
    expect(data.model_features).toEqual([]);
    expect(data.property.images).toEqual([]);
    expect(data.property.highlights).toEqual([]);
  });

  it("provides zeroed valuation with 'No Data' verdict", () => {
    const data = buildEmptyDashboardData("123 Main St", 35.5, -78.7);
    expect(data.valuation.listed_price).toBe(0);
    expect(data.valuation.predicted_value).toBeUndefined();
    expect(data.valuation.confidence_low).toBeUndefined();
    expect(data.valuation.confidence_high).toBeUndefined();
    expect(data.valuation.model_version).toBeUndefined();
    expect(data.valuation.prediction_date).toBeUndefined();
    expect(data.valuation.verdict).toBe("No Data");
  });

  it("includes empty demographic contexts for all geography levels", () => {
    const data = buildEmptyDashboardData("123 Main St", 35.5, -78.7);
    expect(data.demographics.contexts).toBeDefined();
    expect(data.demographics.contexts.subdivision.population).toBe(0);
    expect(data.demographics.contexts.block_group.population).toBe(0);
    expect(data.demographics.contexts.neighborhood.population).toBe(0);
    expect(data.demographics.contexts.town.population).toBe(0);
    expect(data.demographics.contexts.county.population).toBe(0);
  });

  it("provides reasonable mortgage defaults", () => {
    const data = buildEmptyDashboardData("123 Main St", 35.5, -78.7);
    expect(data.mortgage_defaults.down_payment_pct).toBe(20);
    expect(data.mortgage_defaults.loan_term_years).toBe(30);
    expect(data.mortgage_defaults.interest_rate).toBe(6.75);
  });
});
