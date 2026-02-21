interface MonoValueProps {
  value: string | number;
  className?: string;
  size?: "sm" | "md" | "lg" | "xl";
}

const sizeClasses = {
  sm: "text-xs",
  md: "text-sm",
  lg: "text-lg",
  xl: "text-[28px]",
};

function MonoValue({ value, className = "", size = "md" }: MonoValueProps) {
  return (
    <span
      className={`font-db-mono font-medium tracking-tight text-[var(--color-db-text-primary)] ${sizeClasses[size]} ${className}`}
    >
      {value}
    </span>
  );
}

export default MonoValue;
