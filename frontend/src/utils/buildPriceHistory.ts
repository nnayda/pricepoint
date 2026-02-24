import type {
  NeighborhoodMedianPoint,
  PriceHistoryPoint,
  SaleHistoryEntry,
  TaxHistoryEntry,
} from "../types";

/**
 * Build a unified price history array from sale events, tax assessments,
 * and neighborhood median data.
 *
 * - Sale events are placed at their exact month with `sale_price` / `sale_event`.
 * - The property `price` is only set on sale-event points; the chart uses
 *   `connectNulls` + `type="monotone"` to draw a smooth curve between them.
 * - Tax assessments are mapped to "YYYY-07" (mid-year proxy).
 * - Neighborhood medians are merged by month key.
 */
export function buildPriceHistory(
  saleHistory: SaleHistoryEntry[],
  taxHistory: TaxHistoryEntry[],
  neighborhoodMedians: NeighborhoodMedianPoint[],
): PriceHistoryPoint[] {
  const monthMap = new Map<string, PriceHistoryPoint>();

  function getOrCreate(key: string): PriceHistoryPoint {
    let pt = monthMap.get(key);
    if (!pt) {
      pt = { date: key };
      monthMap.set(key, pt);
    }
    return pt;
  }

  // Parse sale events into sorted (date, price, event) tuples
  const sales = saleHistory
    .filter((s) => s.date && s.price > 0)
    .map((s) => {
      const d = new Date(s.date);
      const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
      return { key, price: s.price, event: s.event_type };
    })
    .sort((a, b) => a.key.localeCompare(b.key));

  // Place sale events — only these get a `price` value
  for (const s of sales) {
    const pt = getOrCreate(s.key);
    pt.sale_price = s.price;
    pt.sale_event = s.event;
    pt.price = s.price;
  }

  // Tax assessments → mid-year
  for (const t of taxHistory) {
    if (t.assessed_value > 0) {
      const key = `${t.year}-07`;
      const pt = getOrCreate(key);
      pt.tax_assessed = t.assessed_value;
    }
  }

  // Neighborhood medians
  for (const m of neighborhoodMedians) {
    const pt = getOrCreate(m.date);
    pt.neighborhood_median = m.median_value;
  }

  // Sort all points by date
  return Array.from(monthMap.values()).sort((a, b) => a.date.localeCompare(b.date));
}
