interface DashboardCardProps {
  children: React.ReactNode;
  className?: string;
  padding?: boolean;
}

function DashboardCard({ children, className = "", padding = true }: DashboardCardProps) {
  return (
    <div
      className={`rounded-[var(--radius-db-md)] border border-[var(--th-border-subtle)] bg-[var(--th-bg-surface)] shadow-[var(--th-shadow-card)] ${padding ? "p-5" : ""} ${className}`}
    >
      {children}
    </div>
  );
}

export default DashboardCard;
