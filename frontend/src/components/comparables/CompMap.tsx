import type { CompPropertyDetail } from "../../types";
import DashboardMap from "../dashboard/maps/DashboardMap";

interface CompMapProps {
  subject: CompPropertyDetail;
  comparables: CompPropertyDetail[];
}

function CompMap({ subject, comparables }: CompMapProps) {
  const markers = [
    {
      id: `subject-${subject.listing_id}`,
      lat: subject.lat,
      lon: subject.lon,
      label: subject.address,
      type: "property" as const,
      color: "var(--color-db-accent)",
      popupContent: `<strong>${subject.address}</strong><br/>Subject property`,
    },
    ...comparables.map((comp, i) => ({
      id: `comp-${comp.listing_id}`,
      lat: comp.lat,
      lon: comp.lon,
      label: comp.address,
      type: "generic" as const,
      color: "#6366f1",
      popupContent: `<strong>#${i + 1} ${comp.address}</strong><br/>$${comp.sold_price?.toLocaleString() ?? "N/A"}`,
    })),
  ];

  return (
    <div className="overflow-hidden rounded-[var(--radius-db-lg)] border border-[var(--color-db-border-subtle)] bg-[var(--color-db-surface)] shadow-[var(--shadow-db-card)]">
      <DashboardMap
        center={[subject.lat, subject.lon]}
        zoom={13}
        markers={markers}
        height="250px"
        minHeight="200px"
      />
    </div>
  );
}

export default CompMap;
