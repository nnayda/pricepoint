import { useCallback, useMemo, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import type { ComparablesSearchCriteria } from "../types";
import { useComparables } from "../hooks/useComparables";
import DashboardNav from "../components/dashboard/DashboardNav";
import CompSidebar from "../components/comparables/CompSidebar";
import CompColumn from "../components/comparables/CompColumn";
import CompMap from "../components/comparables/CompMap";

const DEFAULT_CRITERIA: ComparablesSearchCriteria = {
  time_period_months: 3,
  distance_miles: 1,
  same_schools: true,
  sqft_pct: 10,
  lot_pct: 10,
  same_beds: true,
  same_baths: true,
  year_built_diff: 10,
};

function ComparablesPage() {
  const { address } = useParams<{ address: string }>();
  const [searchParams] = useSearchParams();
  const lat = searchParams.get("lat") ? Number(searchParams.get("lat")) : null;
  const lon = searchParams.get("lon") ? Number(searchParams.get("lon")) : null;

  const [criteria, setCriteria] = useState<ComparablesSearchCriteria>(DEFAULT_CRITERIA);

  const criteriaKey = JSON.stringify(criteria);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const stableCriteria = useMemo(() => criteria, [criteriaKey]);

  const { data, loading, error, search } = useComparables(
    lat,
    lon,
    address ?? null,
    stableCriteria,
  );

  // --- Synced expand/collapse state across all columns ---
  // Collect all unique categories from every property
  const allCategories = useMemo(() => {
    if (!data) return [] as string[];
    const cats = new Set<string>();
    for (const g of data.subject.feature_groups) cats.add(g.category);
    for (const comp of data.comparables) {
      for (const g of comp.feature_groups) cats.add(g.category);
    }
    return Array.from(cats);
  }, [data]);

  // All categories expanded by default
  const [expandedCategories, setExpandedCategories] = useState<Set<string> | null>(null);
  const effectiveExpanded = useMemo(() => {
    if (expandedCategories !== null) return expandedCategories;
    return new Set(allCategories);
  }, [expandedCategories, allCategories]);

  const toggleCategory = useCallback(
    (category: string) => {
      setExpandedCategories((prev) => {
        const next = new Set(prev ?? allCategories);
        if (next.has(category)) {
          next.delete(category);
        } else {
          next.add(category);
        }
        return next;
      });
    },
    [allCategories],
  );

  // --- Compute union of feature keys per category for row alignment ---
  const allKeysByCategory = useMemo(() => {
    if (!data) return {} as Record<string, string[]>;
    const map: Record<string, Set<string>> = {};
    const allProps = [data.subject, ...data.comparables];
    for (const prop of allProps) {
      for (const g of prop.feature_groups) {
        if (!map[g.category]) map[g.category] = new Set();
        for (const key of Object.keys(g.features)) {
          map[g.category].add(key);
        }
      }
    }
    const result: Record<string, string[]> = {};
    for (const [cat, keys] of Object.entries(map)) {
      result[cat] = Array.from(keys);
    }
    return result;
  }, [data]);

  return (
    <div className="min-h-screen bg-[var(--th-bg-base)] font-db-sans">
      <DashboardNav />

      <div className="mx-auto max-w-[1680px] px-4 py-6">
        {/* Page header */}
        <div className="mb-4">
          <h1 className="text-lg font-bold text-[var(--color-db-text)]">Comparable Properties</h1>
          <p className="text-sm text-[var(--color-db-text-secondary)]">
            {address ? decodeURIComponent(address) : "Unknown address"}
          </p>
        </div>

        {error && (
          <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-800 dark:bg-red-950/30 dark:text-red-300">
            {error}
          </div>
        )}

        {/* Top bar: search criteria + map side by side, equal height */}
        {data && (
          <div className="mb-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
            <CompSidebar
              criteria={criteria}
              onChange={setCriteria}
              onSearch={search}
              loading={loading}
              totalCandidates={data.total_candidates ?? null}
            />
            <div className="h-[250px]">
              <CompMap subject={data.subject} comparables={data.comparables} />
            </div>
          </div>
        )}

        {/* Sidebar shown before data loads too */}
        {!data && !loading && !error && (
          <CompSidebar
            criteria={criteria}
            onChange={setCriteria}
            onSearch={search}
            loading={loading}
            totalCandidates={null}
          />
        )}

        {loading && !data && (
          <div className="flex items-center justify-center py-20">
            <div
              className="h-8 w-8 animate-spin rounded-full border-4 border-[var(--color-db-accent)] border-t-transparent"
              role="status"
            >
              <span className="sr-only">Loading comparables...</span>
            </div>
          </div>
        )}

        {/* Property columns — full width */}
        {data && (
          <div className="flex gap-4 overflow-x-auto pb-4">
            <div className="shrink-0" style={{ minWidth: 280, maxWidth: 320 }}>
              <CompColumn
                property={data.subject}
                isSubject
                allKeysByCategory={allKeysByCategory}
                expandedCategories={effectiveExpanded}
                onToggleCategory={toggleCategory}
              />
            </div>
            {data.comparables.map((comp) => (
              <div
                key={comp.listing_id}
                className="shrink-0"
                style={{ minWidth: 280, maxWidth: 320 }}
              >
                <CompColumn
                  property={comp}
                  subjectProperty={data.subject}
                  allKeysByCategory={allKeysByCategory}
                  expandedCategories={effectiveExpanded}
                  onToggleCategory={toggleCategory}
                />
              </div>
            ))}
            {data.comparables.length === 0 && !loading && (
              <div className="flex flex-1 items-center justify-center py-12 text-sm text-[var(--color-db-text-secondary)]">
                No comparable properties found. Try adjusting your search criteria.
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default ComparablesPage;
