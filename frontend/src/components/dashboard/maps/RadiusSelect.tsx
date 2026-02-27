import type { MapRadius } from "../../../hooks/useMapRadius";

const OPTIONS: MapRadius[] = [5, 10, 25, 50];

interface RadiusSelectProps {
  value: MapRadius;
  onChange: (r: MapRadius) => void;
}

function RadiusSelect({ value, onChange }: RadiusSelectProps) {
  return (
    <div className="flex gap-1 rounded-[var(--radius-db-xs)] bg-[var(--color-db-surface-alt)] p-0.5">
      {OPTIONS.map((r) => (
        <button
          key={r}
          type="button"
          onClick={() => onChange(r)}
          className={`rounded px-2 py-1 text-xs font-medium transition-colors ${
            value === r
              ? "bg-[var(--color-db-accent)] text-white"
              : "text-[var(--color-db-text-tertiary)] hover:text-[var(--color-db-text-secondary)]"
          }`}
        >
          {r} mi
        </button>
      ))}
    </div>
  );
}

export default RadiusSelect;
