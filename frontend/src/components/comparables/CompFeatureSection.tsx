import type { CompFeatureGroup } from "../../types";

interface CompFeatureSectionProps {
  group: CompFeatureGroup;
  subjectGroup?: CompFeatureGroup;
  /** All feature keys across every column for this category, to keep rows aligned */
  allKeys?: string[];
  expanded?: boolean;
  onToggle?: () => void;
}

function formatValue(val: number | string | boolean | null): string {
  if (val === null || val === undefined) return "—";
  if (typeof val === "boolean") return val ? "Yes" : "No";
  if (typeof val === "number") {
    if (Number.isInteger(val)) return val.toLocaleString();
    return val.toFixed(2);
  }
  return String(val);
}

function diffClass(
  key: string,
  val: number | string | boolean | null,
  subjectVal: number | string | boolean | null,
): string {
  if (val === null || subjectVal === null) return "";
  if (typeof val !== "number" || typeof subjectVal !== "number") return "";
  if (subjectVal === 0) return "";

  const pctDiff = ((val - subjectVal) / Math.abs(subjectVal)) * 100;

  // For "negative" features (risks, costs), invert the color logic
  const negativeFeatures = [
    "flood_score",
    "fire_score",
    "association_fee",
    "property_age",
    "no_heating",
    "no_cooling",
    "is_septic",
    "is_well_water",
  ];
  const isNegative = negativeFeatures.includes(key);

  if (Math.abs(pctDiff) < 5) return "";

  if (isNegative) {
    return pctDiff > 0 ? "bg-red-50 dark:bg-red-950/30" : "bg-green-50 dark:bg-green-950/30";
  }
  return pctDiff > 0 ? "bg-green-50 dark:bg-green-950/30" : "bg-red-50 dark:bg-red-950/30";
}

function CompFeatureSection({
  group,
  subjectGroup,
  allKeys,
  expanded = true,
  onToggle,
}: CompFeatureSectionProps) {
  // Use allKeys (union of keys across columns) to keep rows aligned; fall back to own keys
  const keys = allKeys ?? Object.keys(group.features);

  return (
    <div className="border-t border-[var(--color-db-border-subtle)]">
      <button
        type="button"
        onClick={onToggle}
        className="flex w-full items-center justify-between px-3 py-2 text-left text-xs font-semibold text-[var(--color-db-text-secondary)] hover:bg-[var(--color-db-surface-alt)]"
      >
        <span>{group.category}</span>
        <svg
          className={`h-3.5 w-3.5 transition-transform ${expanded ? "rotate-180" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {expanded && (
        <div className="px-3 pb-2">
          {keys.map((key) => {
            const val = group.features[key] ?? null;
            const subjectVal = subjectGroup?.features[key] ?? null;
            const highlight = subjectGroup ? diffClass(key, val, subjectVal) : "";
            return (
              <div
                key={key}
                className={`flex items-center justify-between rounded px-1.5 py-0.5 text-[11px] ${highlight}`}
              >
                <span className="truncate text-[var(--color-db-text-secondary)]">
                  {key.replace(/_/g, " ")}
                </span>
                <span className="ml-2 shrink-0 font-medium text-[var(--color-db-text)]">
                  {formatValue(val)}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default CompFeatureSection;
