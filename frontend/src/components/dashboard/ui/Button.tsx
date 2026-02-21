import type { ButtonHTMLAttributes } from "react";

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
type ButtonSize = "sm" | "default" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
}

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    "bg-[var(--color-db-accent)] text-white hover:bg-[var(--color-db-accent-hover)] active:brightness-90",
  secondary:
    "border border-[var(--th-border,var(--color-db-border))] bg-[var(--th-bg-surface-alt,var(--color-db-surface-alt))] text-[var(--th-text-secondary,var(--color-db-text-secondary))] hover:bg-[var(--th-bg-surface-hover,var(--color-db-surface-hover))]",
  ghost:
    "text-[var(--th-text-secondary,var(--color-db-text-secondary))] hover:bg-[var(--th-bg-surface-alt,var(--color-db-surface-alt))] hover:text-[var(--th-text-primary,var(--color-db-text-primary))]",
  danger:
    "bg-[var(--color-db-red)] text-white hover:brightness-110 active:brightness-90",
};

const sizeClasses: Record<ButtonSize, string> = {
  sm: "h-7 px-2.5 text-xs gap-1.5",
  default: "h-[34px] px-3.5 text-sm gap-2",
  lg: "h-10 px-5 text-sm gap-2",
};

function Button({
  variant = "primary",
  size = "default",
  className = "",
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      className={`inline-flex items-center justify-center rounded-[var(--radius-db-sm)] font-medium transition-colors focus-visible:outline-none ${variantClasses[variant]} ${sizeClasses[size]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

export default Button;
