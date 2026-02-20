import type { DashboardData } from "../../../types";
import DashboardCard from "../DashboardCard";
import DashboardMap from "../maps/DashboardMap";
import { AlertTriangleIcon } from "../ui/Icons";

interface NegativePoisTabProps {
  data: DashboardData;
}

const severityStyles: Record<string, { bg: string; text: string; border: string }> = {
  Safe: {
    bg: "var(--color-db-green-muted)",
    text: "var(--color-db-green)",
    border: "var(--color-db-green)",
  },
  Caution: {
    bg: "var(--color-db-yellow-muted)",
    text: "var(--color-db-yellow)",
    border: "var(--color-db-yellow)",
  },
  Concern: {
    bg: "var(--color-db-red-muted)",
    text: "var(--color-db-red)",
    border: "var(--color-db-red)",
  },
};

const severityMapColors: Record<string, string> = {
  Safe: "#34D399",
  Caution: "#FBBF24",
  Concern: "#F87171",
};

function NegativePoisTab({ data }: NegativePoisTabProps) {
  const { negative_pois, property } = data;

  const markers = negative_pois.map((n) => ({
    lat: n.lat,
    lon: n.lon,
    label: `${n.name} (${n.severity})`,
    color: severityMapColors[n.severity],
  }));

  return (
    <div className="flex flex-col gap-4">
      {/* Summary */}
      <DashboardCard>
        <div className="flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-[var(--color-db-yellow-muted)]">
            <AlertTriangleIcon size={20} className="text-[var(--color-db-yellow)]" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-[var(--color-db-text-primary)]">
              {negative_pois.length} Negative POIs Detected
            </h3>
            <p className="text-xs text-[var(--color-db-text-tertiary)]">
              Auto-detected potential nuisance sources near property
            </p>
          </div>
        </div>
      </DashboardCard>

      {/* Cards + Map side by side */}
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="flex flex-col gap-3">
          {negative_pois.map((n) => {
            const style = severityStyles[n.severity];
            return (
              <DashboardCard key={n.id}>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <h4 className="text-sm font-semibold text-[var(--color-db-text-primary)]">
                        {n.name}
                      </h4>
                      <span
                        className="rounded-full border px-2 py-0.5 text-[10px] font-semibold"
                        style={{
                          backgroundColor: style.bg,
                          color: style.text,
                          borderColor: `${style.border}40`,
                        }}
                      >
                        {n.severity}
                      </span>
                    </div>
                    <p className="mt-0.5 text-xs text-[var(--color-db-text-muted)]">{n.type}</p>
                    <p className="mt-1.5 text-xs text-[var(--color-db-text-tertiary)]">
                      {n.detail}
                    </p>
                  </div>
                  <span
                    className="shrink-0 text-xs text-[var(--color-db-text-tertiary)]"
                    style={{ fontFamily: "var(--font-db-mono)" }}
                  >
                    {n.distance_miles} mi
                  </span>
                </div>
              </DashboardCard>
            );
          })}
        </div>

        <DashboardCard>
          <h3 className="mb-3 text-sm font-semibold text-[var(--color-db-text-primary)]">
            Negative POI Map
          </h3>
          <DashboardMap
            center={[property.lat, property.lon]}
            zoom={13}
            markers={[
              { lat: property.lat, lon: property.lon, label: "Property", color: "#6366F1" },
              ...markers,
            ]}
            height="320px"
          />
        </DashboardCard>
      </div>
    </div>
  );
}

export default NegativePoisTab;
