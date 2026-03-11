import type { ReactNode } from "react";

type BadgeVariant = "success" | "warning" | "danger" | "info" | "neutral" | "accent";

interface BadgeProps {
  variant?: BadgeVariant;
  dot?: boolean;
  children: ReactNode;
  className?: string;
}

const variantClasses: Record<BadgeVariant, string> = {
  success:
    "bg-[var(--color-db-green-muted)] text-[var(--color-db-green)] border-[var(--color-db-green)]",
  warning:
    "bg-[var(--color-db-yellow-muted)] text-[var(--color-db-yellow)] border-[var(--color-db-yellow)]",
  danger: "bg-[var(--color-db-red-muted)] text-[var(--color-db-red)] border-[var(--color-db-red)]",
  info: "bg-[var(--color-db-cyan-muted)] text-[var(--color-db-cyan)] border-[var(--color-db-cyan)]",
  neutral:
    "bg-[var(--th-bg-surface-alt,var(--color-db-surface-alt))] text-[var(--th-text-secondary,var(--color-db-text-secondary))] border-[var(--th-border,var(--color-db-border))]",
  accent:
    "bg-[var(--color-db-accent-muted)] text-[var(--color-db-accent)] border-[var(--color-db-accent)]",
};

function Badge({ variant = "neutral", dot = false, children, className = "" }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold ${variantClasses[variant]} ${className}`}
    >
      {dot && <span className="h-1.5 w-1.5 rounded-full bg-current" />}
      {children}
    </span>
  );
}

export default Badge;
