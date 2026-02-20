interface DashboardCardProps {
  children: React.ReactNode;
  className?: string;
  padding?: boolean;
}

function DashboardCard({ children, className = "", padding = true }: DashboardCardProps) {
  return (
    <div
      className={`rounded-[var(--radius-db-md)] border border-[var(--color-db-border-subtle)] bg-[var(--color-db-surface)] shadow-[var(--shadow-db-card)] ${padding ? "p-5" : ""} ${className}`}
    >
      {children}
    </div>
  );
}

export default DashboardCard;
