import { describe, expect, it } from "vitest";
import { buildPriceHistory } from "../buildPriceHistory";
import type { NeighborhoodMedianPoint, SaleHistoryEntry, TaxHistoryEntry } from "../../types";

describe("buildPriceHistory", () => {
  it("returns empty array when all inputs are empty", () => {
    expect(buildPriceHistory([], [], [])).toEqual([]);
  });

  it("builds points from sale history only", () => {
    const sales: SaleHistoryEntry[] = [
      { date: "2022-01-15", price: 300000, event_type: "Sold" },
      { date: "2023-06-20", price: 350000, event_type: "Sold" },
    ];
    const result = buildPriceHistory(sales, [], []);

    expect(result.length).toBe(2);
    expect(result[0]).toMatchObject({
      date: "2022-01",
      price: 300000,
      sale_price: 300000,
      sale_event: "Sold",
    });
    expect(result[1]).toMatchObject({
      date: "2023-06",
      price: 350000,
      sale_price: 350000,
    });
  });

  it("builds points from tax history only", () => {
    const taxes: TaxHistoryEntry[] = [
      { year: 2022, assessed_value: 280000, tax_amount: 3500 },
      { year: 2023, assessed_value: 310000, tax_amount: 3800 },
    ];
    const result = buildPriceHistory([], taxes, []);

    expect(result.length).toBe(2);
    expect(result[0]).toMatchObject({ date: "2022-07", tax_assessed: 280000 });
    expect(result[1]).toMatchObject({ date: "2023-07", tax_assessed: 310000 });
  });

  it("builds points from neighborhood medians only", () => {
    const medians: NeighborhoodMedianPoint[] = [
      { date: "2022-06", median_value: 340000 },
      { date: "2022-12", median_value: 360000 },
    ];
    const result = buildPriceHistory([], [], medians);

    expect(result.length).toBe(2);
    expect(result[0]).toMatchObject({ date: "2022-06", neighborhood_median: 340000 });
    expect(result[1]).toMatchObject({ date: "2022-12", neighborhood_median: 360000 });
  });

  it("merges all three sources and sorts by date", () => {
    const sales: SaleHistoryEntry[] = [{ date: "2022-06-15", price: 400000, event_type: "Sold" }];
    const taxes: TaxHistoryEntry[] = [{ year: 2022, assessed_value: 380000, tax_amount: 4000 }];
    const medians: NeighborhoodMedianPoint[] = [{ date: "2022-06", median_value: 390000 }];

    const result = buildPriceHistory(sales, taxes, medians);

    // Two points: 2022-06 (sale + median) and 2022-07 (tax only, no price)
    expect(result.length).toBe(2);
    expect(result[0].date).toBe("2022-06");
    expect(result[0].sale_price).toBe(400000);
    expect(result[0].neighborhood_median).toBe(390000);
    expect(result[1].date).toBe("2022-07");
    expect(result[1].tax_assessed).toBe(380000);
    expect(result[1].price).toBeUndefined();
  });

  it("does not set price on non-sale points", () => {
    const sales: SaleHistoryEntry[] = [
      { date: "2022-01-15", price: 300000, event_type: "Sold" },
      { date: "2023-01-15", price: 360000, event_type: "Sold" },
    ];
    const medians: NeighborhoodMedianPoint[] = [{ date: "2022-07", median_value: 340000 }];

    const result = buildPriceHistory(sales, [], medians);
    // 2022-07 has neighborhood_median only — price should be undefined
    const midPoint = result.find((p) => p.date === "2022-07");
    expect(midPoint).toBeDefined();
    expect(midPoint!.price).toBeUndefined();
    expect(midPoint!.neighborhood_median).toBe(340000);
  });

  it("skips sale entries with zero price", () => {
    const sales: SaleHistoryEntry[] = [
      { date: "2022-01-15", price: 0, event_type: "Listed" },
      { date: "2022-06-15", price: 300000, event_type: "Sold" },
    ];
    const result = buildPriceHistory(sales, [], []);
    expect(result.length).toBe(1);
    expect(result[0].sale_price).toBe(300000);
  });

  it("skips tax entries with zero assessed value", () => {
    const taxes: TaxHistoryEntry[] = [
      { year: 2022, assessed_value: 0, tax_amount: 0 },
      { year: 2023, assessed_value: 310000, tax_amount: 3800 },
    ];
    const result = buildPriceHistory([], taxes, []);
    expect(result.length).toBe(1);
    expect(result[0].tax_assessed).toBe(310000);
  });
});
