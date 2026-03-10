import type { ComparablesSearchCriteria } from "../../types";

interface CompSidebarProps {
  criteria: ComparablesSearchCriteria;
  onChange: (criteria: ComparablesSearchCriteria) => void;
  onSearch: () => void;
  loading: boolean;
  totalCandidates: number | null;
}

function RadioGroup<T extends string | number>({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: { value: T; label: string }[];
  value: T;
  onChange: (v: T) => void;
}) {
  return (
    <div>
      <p className="mb-1.5 text-xs font-semibold text-[var(--color-db-text-secondary)]">{label}</p>
      <div className="flex flex-wrap gap-1.5">
        {options.map((opt) => (
          <button
            key={String(opt.value)}
            type="button"
            onClick={() => onChange(opt.value)}
            className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
              value === opt.value
                ? "bg-[var(--color-db-accent)] text-white"
                : "bg-[var(--color-db-surface-alt)] text-[var(--color-db-text-secondary)] hover:bg-[var(--color-db-border-subtle)]"
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  );
}

function Toggle({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <label className="flex cursor-pointer items-center justify-between py-1">
      <span className="text-xs text-[var(--color-db-text)]">{label}</span>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={`relative inline-flex h-5 w-9 shrink-0 rounded-full transition-colors ${
          checked ? "bg-[var(--color-db-accent)]" : "bg-[var(--color-db-border-subtle)]"
        }`}
      >
        <span
          className={`inline-block h-4 w-4 translate-y-0.5 rounded-full bg-white shadow transition-transform ${
            checked ? "translate-x-4" : "translate-x-0.5"
          }`}
        />
      </button>
    </label>
  );
}

function RangeSlider({
  label,
  value,
  onChange,
  min,
  max,
  suffix,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  min: number;
  max: number;
  suffix: string;
}) {
  return (
    <div>
      <div className="flex items-center justify-between">
        <span className="text-xs text-[var(--color-db-text-secondary)]">{label}</span>
        <span className="text-xs font-semibold text-[var(--color-db-text)]">
          {value}
          {suffix}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="mt-1 w-full accent-[var(--color-db-accent)]"
      />
    </div>
  );
}

function CompSidebar({ criteria, onChange, onSearch, loading, totalCandidates }: CompSidebarProps) {
  function update(patch: Partial<ComparablesSearchCriteria>) {
    onChange({ ...criteria, ...patch });
  }

  return (
    <aside className="scrollbar-none flex w-full shrink-0 flex-col gap-4 rounded-[var(--radius-db-lg)] border border-[var(--color-db-border-subtle)] bg-[var(--color-db-surface)] p-4 shadow-[var(--shadow-db-card)] lg:sticky lg:top-20 lg:h-[calc(100vh-6rem)] lg:w-[280px] lg:overflow-y-auto">
      <h2 className="text-sm font-bold text-[var(--color-db-text)]">Search Criteria</h2>

      <RadioGroup
        label="Time Period"
        options={[
          { value: 3, label: "3 mo" },
          { value: 6, label: "6 mo" },
          { value: 9, label: "9 mo" },
          { value: 12, label: "12 mo" },
        ]}
        value={criteria.time_period_months}
        onChange={(v) => update({ time_period_months: v as 3 | 6 | 9 | 12 })}
      />

      <RadioGroup
        label="Distance"
        options={[
          { value: 0.5, label: "0.5 mi" },
          { value: 1, label: "1 mi" },
          { value: 2, label: "2 mi" },
          { value: 5, label: "5 mi" },
        ]}
        value={criteria.distance_miles}
        onChange={(v) => update({ distance_miles: v as 0.5 | 1 | 2 | 5 })}
      />

      <div className="space-y-1">
        <Toggle
          label="Same school district"
          checked={criteria.same_schools}
          onChange={(v) => update({ same_schools: v })}
        />
        <Toggle
          label="Same bedrooms"
          checked={criteria.same_beds}
          onChange={(v) => update({ same_beds: v })}
        />
        <Toggle
          label="Same bathrooms"
          checked={criteria.same_baths}
          onChange={(v) => update({ same_baths: v })}
        />
      </div>

      <RangeSlider
        label="Sqft tolerance"
        value={criteria.sqft_pct}
        onChange={(v) => update({ sqft_pct: v })}
        min={0}
        max={40}
        suffix="%"
      />

      <RangeSlider
        label="Lot size tolerance"
        value={criteria.lot_pct}
        onChange={(v) => update({ lot_pct: v })}
        min={0}
        max={40}
        suffix="%"
      />

      <RangeSlider
        label="Year built range"
        value={criteria.year_built_diff}
        onChange={(v) => update({ year_built_diff: v })}
        min={0}
        max={20}
        suffix=" yrs"
      />

      <button
        type="button"
        onClick={onSearch}
        disabled={loading}
        className="w-full rounded-lg bg-[var(--color-db-accent)] py-2.5 text-sm font-semibold text-white transition-colors hover:bg-[var(--color-db-accent-hover)] disabled:opacity-50"
      >
        {loading ? "Searching..." : "Search"}
      </button>

      {totalCandidates !== null && (
        <p className="text-center text-xs text-[var(--color-db-text-secondary)]">
          {totalCandidates} candidate{totalCandidates !== 1 ? "s" : ""} found
        </p>
      )}
    </aside>
  );
}

export default CompSidebar;
