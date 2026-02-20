interface StatusBadgeProps {
  status: "For Sale" | "Pending" | "Sold";
}

const statusStyles: Record<string, string> = {
  "For Sale":
    "bg-[var(--color-db-green-muted)] text-[var(--color-db-green)] border-[var(--color-db-green)]",
  Pending:
    "bg-[var(--color-db-yellow-muted)] text-[var(--color-db-yellow)] border-[var(--color-db-yellow)]",
  Sold: "bg-[var(--color-db-red-muted)] text-[var(--color-db-red)] border-[var(--color-db-red)]",
};

function StatusBadge({ status }: StatusBadgeProps) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold ${statusStyles[status]}`}
      style={{ fontFamily: "var(--font-db-sans)" }}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {status}
    </span>
  );
}

export default StatusBadge;
