import type { ReactNode } from "react";

type HeadingTag = "h2" | "h3" | "h4";
type HeadingVariant = "default" | "uppercase";

interface SectionHeadingProps {
  as?: HeadingTag;
  variant?: HeadingVariant;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}

const variantClasses: Record<HeadingVariant, string> = {
  default: "text-sm font-semibold text-[var(--th-text-primary,var(--color-db-text-primary))]",
  uppercase:
    "text-xs font-semibold uppercase tracking-wider text-[var(--th-text-primary,var(--color-db-text-primary))]",
};

function SectionHeading({
  as: Tag = "h3",
  variant = "default",
  action,
  children,
  className = "",
}: SectionHeadingProps) {
  if (action) {
    return (
      <div className={`flex items-center justify-between ${className}`}>
        <Tag className={variantClasses[variant]}>{children}</Tag>
        {action}
      </div>
    );
  }

  return <Tag className={`${variantClasses[variant]} ${className}`}>{children}</Tag>;
}

export default SectionHeading;
