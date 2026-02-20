interface StatChipProps {
  label: string;
  value: string | number;
  delta?: number;
  compact?: boolean;
}

function StatChip({ label, value, delta, compact = false }: StatChipProps) {
  return (
    <div
      className={`flex flex-col gap-0.5 rounded-[var(--radius-db-sm)] bg-[var(--color-db-surface-alt)] ${compact ? "px-3 py-2" : "px-4 py-3"}`}
    >
      <span
        className="text-[10px] font-medium uppercase tracking-wider text-[var(--color-db-text-tertiary)]"
        style={{ fontFamily: "var(--font-db-sans)" }}
      >
        {label}
      </span>
      <div className="flex items-baseline gap-1.5">
        <span
          className="text-sm font-semibold text-[var(--color-db-text-primary)]"
          style={{ fontFamily: "var(--font-db-mono)" }}
        >
          {value}
        </span>
        {delta !== undefined && (
          <span
            className={`text-[10px] font-medium ${delta >= 0 ? "text-[var(--color-db-green)]" : "text-[var(--color-db-red)]"}`}
          >
            {delta >= 0 ? "+" : ""}
            {delta}%
          </span>
        )}
      </div>
    </div>
  );
}

export default StatChip;
