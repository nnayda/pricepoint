import type { DashboardProperty, DashboardValuation } from "../../../types";
import DashboardCard from "../DashboardCard";
import StatusBadge from "../ui/StatusBadge";
import MonoValue from "../ui/MonoValue";
import { BedIcon, BathIcon, RulerIcon, CalendarIcon, LandPlotIcon, GarageIcon } from "../ui/Icons";
import { getDomColor } from "../../../utils/chartTokens";

interface KeyFactsCardProps {
  property: DashboardProperty;
  valuation: DashboardValuation;
}

function fmt(n: number): string {
  return n.toLocaleString("en-US");
}

function fmtUsd(n: number): string {
  return "$" + n.toLocaleString("en-US");
}

function fmtDuration(days: number): string {
  if (days < 60) return `${days}d`;
  if (days < 365) {
    const months = Math.round(days / 30);
    return `${months}mo`;
  }
  const years = Math.round((days / 365) * 10) / 10;
  return years % 1 === 0 ? `${years}yr` : `${years}yr`;
}

function daysSince(dateStr: string): number {
  const diff = Date.now() - new Date(dateStr).getTime();
  return Math.max(0, Math.floor(diff / 86_400_000));
}

function KeyFactsCard({ property, valuation }: KeyFactsCardProps) {
  const isSold = property.listing_status === "Sold";
  const badgeDays =
    isSold && property.sold_date ? daysSince(property.sold_date) : property.days_on_market;
  const badgeLabel = isSold
    ? `${fmtDuration(badgeDays)} since sold`
    : `${fmtDuration(badgeDays)} on market`;
  const domColor = getDomColor(badgeDays);
  const lotAcres = (property.lot_size_sqft / 43560).toFixed(2);

  return (
    <DashboardCard>
      <div className="flex flex-col gap-4">
        {/* Status + Price */}
        <div className="flex items-start justify-between">
          <div className="flex flex-col gap-1">
            <div className="w-fit">
              <StatusBadge status={property.listing_status} />
            </div>
            <div className="flex items-baseline gap-2">
              <MonoValue value={fmtUsd(valuation.listed_price)} size="xl" />
              <span className="text-xs text-[var(--color-db-text-tertiary)]">
                <span className="font-db-mono">${valuation.price_per_sqft}</span>
                /sqft
              </span>
            </div>
          </div>
          <div
            className="rounded-[var(--radius-db-xs)] px-2.5 py-1 text-xs font-medium"
            style={{ backgroundColor: domColor.bg, color: domColor.text }}
          >
            {badgeLabel}
          </div>
        </div>

        {/* Address */}
        <div>
          <h1 className="text-base font-semibold text-[var(--color-db-text-primary)]">
            {property.address}
          </h1>
          <p className="text-sm text-[var(--color-db-text-secondary)]">
            {property.city}, {property.state} {property.zip_code}
          </p>
        </div>

        {/* Stats grid */}
        <div className="grid grid-cols-2 gap-2">
          <div className="flex items-center gap-2.5 rounded-[var(--radius-db-xs)] bg-[var(--color-db-surface-alt)] px-3 py-2.5">
            <BedIcon size={16} className="shrink-0 text-[var(--color-db-text-muted)]" />
            <div className="flex flex-col">
              <span className="text-[10px] leading-tight text-[var(--color-db-text-muted)]">
                Beds
              </span>
              <MonoValue value={property.bedrooms} size="md" />
            </div>
          </div>
          <div className="flex items-center gap-2.5 rounded-[var(--radius-db-xs)] bg-[var(--color-db-surface-alt)] px-3 py-2.5">
            <BathIcon size={16} className="shrink-0 text-[var(--color-db-text-muted)]" />
            <div className="flex flex-col">
              <span className="text-[10px] leading-tight text-[var(--color-db-text-muted)]">
                Baths
              </span>
              <MonoValue value={property.bathrooms} size="md" />
            </div>
          </div>
          <div className="flex items-center gap-2.5 rounded-[var(--radius-db-xs)] bg-[var(--color-db-surface-alt)] px-3 py-2.5">
            <RulerIcon size={16} className="shrink-0 text-[var(--color-db-text-muted)]" />
            <div className="flex flex-col">
              <span className="text-[10px] leading-tight text-[var(--color-db-text-muted)]">
                Sqft
              </span>
              <MonoValue value={fmt(property.sqft)} size="md" />
            </div>
          </div>
          <div className="flex items-center gap-2.5 rounded-[var(--radius-db-xs)] bg-[var(--color-db-surface-alt)] px-3 py-2.5">
            <LandPlotIcon size={16} className="shrink-0 text-[var(--color-db-text-muted)]" />
            <div className="flex flex-col">
              <span className="text-[10px] leading-tight text-[var(--color-db-text-muted)]">
                Lot Acres
              </span>
              <MonoValue value={lotAcres} size="md" />
            </div>
          </div>
          <div className="flex items-center gap-2.5 rounded-[var(--radius-db-xs)] bg-[var(--color-db-surface-alt)] px-3 py-2.5">
            <CalendarIcon size={16} className="shrink-0 text-[var(--color-db-text-muted)]" />
            <div className="flex flex-col">
              <span className="text-[10px] leading-tight text-[var(--color-db-text-muted)]">
                Built
              </span>
              <MonoValue value={property.year_built} size="md" />
            </div>
          </div>
          <div className="flex items-center gap-2.5 rounded-[var(--radius-db-xs)] bg-[var(--color-db-surface-alt)] px-3 py-2.5">
            <GarageIcon size={16} className="shrink-0 text-[var(--color-db-text-muted)]" />
            <div className="flex flex-col">
              <span className="text-[10px] leading-tight text-[var(--color-db-text-muted)]">
                Garage
              </span>
              <MonoValue value={`${property.garage_spaces}-Car`} size="md" />
            </div>
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex gap-2">
          <button
            type="button"
            aria-label="Save listing"
            className="flex flex-1 items-center justify-center gap-2 rounded-[var(--radius-db-sm)] bg-[var(--color-db-accent)] px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-[var(--color-db-accent-hover)]"
          >
            <svg
              className="h-4 w-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"
              />
            </svg>
            Save
          </button>
          <button
            type="button"
            aria-label="Share property"
            className="flex items-center justify-center rounded-[var(--radius-db-sm)] border border-[var(--color-db-border)] bg-[var(--color-db-surface-alt)] px-3 py-2.5 text-[var(--color-db-text-secondary)] transition-colors hover:bg-[var(--color-db-surface-hover)]"
          >
            <svg
              className="h-4 w-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z"
              />
            </svg>
          </button>
          <button
            type="button"
            aria-label="Open in external source"
            className="flex items-center justify-center rounded-[var(--radius-db-sm)] border border-[var(--color-db-border)] bg-[var(--color-db-surface-alt)] px-3 py-2.5 text-[var(--color-db-text-secondary)] transition-colors hover:bg-[var(--color-db-surface-hover)]"
          >
            <svg
              className="h-4 w-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"
              />
            </svg>
          </button>
        </div>
      </div>
    </DashboardCard>
  );
}

export default KeyFactsCard;
