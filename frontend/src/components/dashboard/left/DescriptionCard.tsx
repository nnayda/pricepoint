import { useState } from "react";
import type { DashboardProperty, ListingQualityScore } from "../../../types";
import DashboardCard from "../DashboardCard";
import { SparklesIcon } from "../ui/Icons";

interface DescriptionCardProps {
  property: DashboardProperty;
  listingQuality?: ListingQualityScore;
}

function DescriptionCard({ property, listingQuality }: DescriptionCardProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <DashboardCard>
      <div className="flex flex-col gap-3">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h2
            className="text-base font-semibold text-[var(--color-db-text-primary)]"
            style={{ fontFamily: "var(--font-db-sans)" }}
          >
            About this Property
          </h2>
          {listingQuality && (
            <span className="rounded-full bg-[var(--color-db-accent-muted)] px-2.5 py-0.5 text-[11px] font-medium text-[var(--color-db-accent-hover)]">
              Description Score: {listingQuality.description_score}
            </span>
          )}
        </div>

        {/* AI Summary */}
        <div className="flex items-start gap-2">
          <div className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded bg-[var(--color-db-accent-muted)]">
            <SparklesIcon size={12} className="text-[var(--color-db-accent)]" />
          </div>
          <p className="text-sm leading-relaxed text-[var(--color-db-text-secondary)]">
            {property.ai_summary}
          </p>
        </div>

        {/* Feature Tags */}
        <div className="flex flex-wrap gap-1.5">
          {property.highlights.map((tag) => (
            <span
              key={tag}
              className="rounded-full border border-[var(--color-db-border)] bg-[var(--color-db-surface-alt)] px-2.5 py-1 text-[11px] font-medium text-[var(--color-db-text-secondary)]"
            >
              {tag}
            </span>
          ))}
        </div>

        {/* Full description toggle */}
        <div>
          <p
            className={`text-sm leading-relaxed text-[var(--color-db-text-tertiary)] ${!expanded ? "line-clamp-3" : ""}`}
          >
            {property.description}
          </p>
          <button
            type="button"
            onClick={() => setExpanded(!expanded)}
            className="mt-1 text-xs font-medium text-[var(--color-db-accent)] hover:text-[var(--color-db-accent-hover)]"
          >
            {expanded ? "Show less" : "Read more"}
          </button>
        </div>
      </div>
    </DashboardCard>
  );
}

export default DescriptionCard;
