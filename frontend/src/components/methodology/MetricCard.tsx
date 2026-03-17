interface MetricCardProps {
  name: string;
  value: number | null;
  format: "currency" | "percentage" | "number";
  subtitle?: string;
}

function formatValue(value: number | null, format: MetricCardProps["format"]): string {
  if (value == null) return "N/A";
  switch (format) {
    case "currency":
      return `$${value.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
    case "percentage":
      return `${(value * 100).toFixed(2)}%`;
    case "number":
      return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
  }
}

function MetricCard({ name, value, format, subtitle }: MetricCardProps) {
  return (
    <div
      className="rounded-[var(--radius-db-md)] border border-[var(--th-border-subtle)] p-4"
      style={{ backgroundColor: "var(--th-bg-surface)" }}
    >
      <p className="text-xs font-medium text-[var(--color-db-text-tertiary)]">{name}</p>
      <p className="mt-1 text-xl font-semibold text-[var(--color-db-text-primary)]">
        {formatValue(value, format)}
      </p>
      {subtitle && (
        <p className="mt-0.5 text-xs text-[var(--color-db-text-secondary)]">{subtitle}</p>
      )}
    </div>
  );
}

export default MetricCard;
