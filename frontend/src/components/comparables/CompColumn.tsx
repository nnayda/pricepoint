import { Link } from "react-router-dom";
import type { CompPropertyDetail, CompFeatureGroup } from "../../types";
import CompFeatureSection from "./CompFeatureSection";

interface CompColumnProps {
  property: CompPropertyDetail;
  isSubject?: boolean;
  subjectProperty?: CompPropertyDetail;
  /** Union of all feature keys per category, for row alignment */
  allKeysByCategory?: Record<string, string[]>;
  /** Union of all risk names across properties, for row alignment */
  allRiskNames?: string[];
  /** Union of all nuisance names across properties, for row alignment */
  allNuisanceNames?: string[];
  /** Which categories are expanded (synced across columns) */
  expandedCategories?: Set<string>;
  /** Toggle a category's expanded state */
  onToggleCategory?: (category: string) => void;
}

function formatPrice(val: number | null): string {
  if (val === null) return "—";
  return `$${val.toLocaleString()}`;
}

function formatPriceDiff(
  compPrice: number | null,
  subjectListingPrice: number | null,
): string | null {
  if (compPrice === null || subjectListingPrice === null) return null;
  const diff = compPrice - subjectListingPrice;
  const sign = diff >= 0 ? "+" : "";
  return `${sign}$${Math.abs(diff).toLocaleString()}`;
}

function ScoreBadge({ label, score }: { label: string; score: number | null }) {
  if (score === null) return null;
  const color =
    score >= 7
      ? "bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300"
      : score >= 4
        ? "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300"
        : "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300";
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold ${color}`}
    >
      {label}: {score}/10
    </span>
  );
}

function SeverityDot({ severity }: { severity: string }) {
  const color =
    severity === "Concern"
      ? "bg-red-500"
      : severity === "Caution"
        ? "bg-amber-500"
        : "bg-green-500";
  return <span className={`inline-block h-2 w-2 shrink-0 rounded-full ${color}`} />;
}

function CompColumn({
  property: prop,
  isSubject,
  subjectProperty,
  allKeysByCategory,
  allRiskNames,
  allNuisanceNames,
  expandedCategories,
  onToggleCategory,
}: CompColumnProps) {
  const subjectGroups: Record<string, CompFeatureGroup> = {};
  if (subjectProperty) {
    for (const g of subjectProperty.feature_groups) {
      subjectGroups[g.category] = g;
    }
  }

  // Price diff between this comp's sold price and the subject's listing price
  const priceDiffLabel =
    !isSubject && subjectProperty
      ? formatPriceDiff(prop.sold_price, subjectProperty.listing_price)
      : null;

  // For subject show listing price; for comps show sold price
  const displayPrice = isSubject ? prop.listing_price : prop.sold_price;
  const priceLabel = isSubject ? "List" : "Sold";

  return (
    <div
      className={`flex min-w-[260px] flex-col overflow-hidden rounded-[var(--radius-db-lg)] border shadow-[var(--shadow-db-card)] ${
        isSubject
          ? "border-[var(--color-db-accent)] bg-[var(--color-db-accent)]/5"
          : "border-[var(--color-db-border-subtle)] bg-[var(--color-db-surface)]"
      }`}
    >
      {/* Photo */}
      {prop.photos.length > 0 ? (
        <img src={prop.photos[0]} alt={prop.address} className="h-40 w-full object-cover" />
      ) : (
        <div className="flex h-40 items-center justify-center bg-[var(--color-db-surface-alt)] text-sm text-[var(--color-db-text-secondary)]">
          No photo
        </div>
      )}

      {/* Header */}
      <div className="border-b border-[var(--color-db-border-subtle)] px-3 py-2">
        <div className="flex items-center gap-2">
          {isSubject && (
            <span className="rounded bg-[var(--color-db-accent)] px-1.5 py-0.5 text-[10px] font-bold text-white">
              SUBJECT
            </span>
          )}
          {prop.similarity_distance !== null && !isSubject && (
            <span className="rounded bg-indigo-100 px-1.5 py-0.5 text-[10px] font-bold text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300">
              Sim: {prop.similarity_distance.toFixed(2)}
            </span>
          )}
          {priceDiffLabel && (
            <span
              className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${
                priceDiffLabel.startsWith("+")
                  ? "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300"
                  : "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300"
              }`}
            >
              {priceDiffLabel}
            </span>
          )}
        </div>
        <p className="mt-1 text-sm font-semibold text-[var(--color-db-text)] leading-tight">
          {prop.address}
        </p>
        <p className="text-xs text-[var(--color-db-text-secondary)]">
          {prop.city}, {prop.state} {prop.zip_code}
        </p>
        {!isSubject && (
          <Link
            to={`/property/${encodeURIComponent(prop.address)}?lat=${prop.lat}&lon=${prop.lon}`}
            className="mt-1.5 inline-flex items-center gap-1 text-[11px] font-medium text-[var(--color-db-accent)] hover:underline"
          >
            View property
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 16 16"
              fill="currentColor"
              className="h-3 w-3"
            >
              <path
                fillRule="evenodd"
                d="M4.22 11.78a.75.75 0 0 1 0-1.06L9.44 5.5H5.75a.75.75 0 0 1 0-1.5h5.5a.75.75 0 0 1 .75.75v5.5a.75.75 0 0 1-1.5 0V6.56l-5.22 5.22a.75.75 0 0 1-1.06 0Z"
                clipRule="evenodd"
              />
            </svg>
          </Link>
        )}
      </div>

      {/* Key Facts — fixed rows so columns align */}
      <div className="grid grid-cols-2 gap-x-4 border-b border-[var(--color-db-border-subtle)] px-3 py-2 text-xs">
        <div className="py-0.5">
          <span className="text-[var(--color-db-text-secondary)]">{priceLabel} </span>
          <span className="font-semibold text-[var(--color-db-text)]">
            {formatPrice(displayPrice)}
          </span>
        </div>
        <div className="py-0.5">
          <span className="text-[var(--color-db-text-secondary)]">$/sqft </span>
          <span className="font-semibold text-[var(--color-db-text)]">
            {prop.price_per_sqft ? `$${prop.price_per_sqft.toFixed(0)}` : "—"}
          </span>
        </div>
        <div className="py-0.5">
          <span className="text-[var(--color-db-text-secondary)]">Beds </span>
          <span className="font-semibold text-[var(--color-db-text)]">{prop.beds}</span>
        </div>
        <div className="py-0.5">
          <span className="text-[var(--color-db-text-secondary)]">Baths </span>
          <span className="font-semibold text-[var(--color-db-text)]">{prop.baths}</span>
        </div>
        <div className="py-0.5">
          <span className="text-[var(--color-db-text-secondary)]">Sqft </span>
          <span className="font-semibold text-[var(--color-db-text)]">
            {prop.sqft?.toLocaleString() ?? "—"}
          </span>
        </div>
        <div className="py-0.5">
          <span className="text-[var(--color-db-text-secondary)]">Lot </span>
          <span className="font-semibold text-[var(--color-db-text)]">
            {prop.lot_size ? `${prop.lot_size.toFixed(2)} ac` : "—"}
          </span>
        </div>
        <div className="py-0.5">
          <span className="text-[var(--color-db-text-secondary)]">Year </span>
          <span className="font-semibold text-[var(--color-db-text)]">
            {prop.year_built ?? "—"}
          </span>
        </div>
        <div className="py-0.5">
          <span className="text-[var(--color-db-text-secondary)]">Garage </span>
          <span className="font-semibold text-[var(--color-db-text)]">{prop.garage_spaces}</span>
        </div>
        <div className="col-span-2 py-0.5">
          <span className="text-[var(--color-db-text-secondary)]">Sold </span>
          <span className="font-semibold text-[var(--color-db-text)]">{prop.sold_date ?? "—"}</span>
        </div>
      </div>

      {/* Scores */}
      <div className="flex flex-wrap gap-1.5 border-b border-[var(--color-db-border-subtle)] px-3 py-2">
        <ScoreBadge label="Desc" score={prop.description_score} />
        <ScoreBadge label="Photo" score={prop.photo_score} />
      </div>

      {/* Nuisances */}
      {(allNuisanceNames ?? prop.nuisances.map((n) => n.name)).length > 0 && (
        <div className="border-b border-[var(--color-db-border-subtle)] px-3 py-2">
          <p className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-[var(--color-db-text-secondary)]">
            Nuisances
          </p>
          {(allNuisanceNames ?? prop.nuisances.map((n) => n.name)).map((name) => {
            const item = prop.nuisances.find((n) => n.name === name);
            return (
              <div key={name} className="flex items-center gap-1.5 py-0.5 text-[11px]">
                {item ? (
                  <>
                    <SeverityDot severity={item.severity} />
                    <span className="truncate text-[var(--color-db-text)]">{item.name}</span>
                    <span className="ml-auto shrink-0 text-[var(--color-db-text-secondary)]">
                      {item.distance_miles} mi
                    </span>
                  </>
                ) : (
                  <span className="invisible">
                    <span className="inline-block h-2 w-2 shrink-0" />
                    <span className="truncate">{name}</span>
                  </span>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Risks */}
      {(allRiskNames ?? prop.risks.map((r) => r.name)).length > 0 && (
        <div className="border-b border-[var(--color-db-border-subtle)] px-3 py-2">
          <p className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-[var(--color-db-text-secondary)]">
            Risks
          </p>
          {(allRiskNames ?? prop.risks.map((r) => r.name)).map((name) => {
            const item = prop.risks.find((r) => r.name === name);
            return (
              <div key={name} className="flex items-center gap-1.5 py-0.5 text-[11px]">
                {item ? (
                  <>
                    <SeverityDot severity={item.severity} />
                    <span className="truncate text-[var(--color-db-text)]">{item.name}</span>
                    <span className="ml-auto shrink-0 text-[var(--color-db-text-secondary)]">
                      {item.distance_miles} mi
                    </span>
                  </>
                ) : (
                  <span className="invisible">
                    <span className="inline-block h-2 w-2 shrink-0" />
                    <span className="truncate">{name}</span>
                  </span>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Feature Sections */}
      <div className="flex-1 overflow-y-auto">
        {prop.feature_groups.map((group) => (
          <CompFeatureSection
            key={group.category}
            group={group}
            subjectGroup={isSubject ? undefined : subjectGroups[group.category]}
            allKeys={allKeysByCategory?.[group.category]}
            expanded={expandedCategories?.has(group.category) ?? true}
            onToggle={() => onToggleCategory?.(group.category)}
          />
        ))}
      </div>
    </div>
  );
}

export default CompColumn;
