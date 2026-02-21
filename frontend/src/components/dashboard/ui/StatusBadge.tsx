import Badge from "./Badge";

interface StatusBadgeProps {
  status: "For Sale" | "Pending" | "Sold";
}

const statusVariant: Record<string, "success" | "warning" | "danger"> = {
  "For Sale": "success",
  Pending: "warning",
  Sold: "danger",
};

function StatusBadge({ status }: StatusBadgeProps) {
  return (
    <Badge variant={statusVariant[status]} dot>
      {status}
    </Badge>
  );
}

export default StatusBadge;
