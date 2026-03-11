import { useState } from "react";
import type { DashboardData } from "../../../types";
import DashboardCard from "../DashboardCard";
import CollapsibleSection from "../ui/CollapsibleSection";

interface PropertyDetailsTabProps {
  data: DashboardData;
}

function PropertyDetailsTab({ data }: PropertyDetailsTabProps) {
  const { property_details, model_features } = data;
  const [showModelFeatures, setShowModelFeatures] = useState(false);

  return (
    <div className="flex flex-col gap-4">
      {/* Property Detail Sections */}
      <DashboardCard padding={false}>
        {property_details.map((section) => (
          <CollapsibleSection key={section.label} title={section.label}>
            <div className="space-y-0">
              {section.items.map((item) => (
                <div
                  key={item.key}
                  className="flex items-center justify-between border-b border-[var(--color-db-border-subtle)] py-2.5 last:border-b-0"
                >
                  <span className="text-xs text-[var(--color-db-text-tertiary)]">{item.key}</span>
                  <span className="font-db-mono text-xs font-medium text-[var(--color-db-text-primary)]">
                    {item.value}
                  </span>
                </div>
              ))}
            </div>
          </CollapsibleSection>
        ))}
      </DashboardCard>

      {/* Model Features */}
      <DashboardCard padding={false}>
        <button
          type="button"
          onClick={() => setShowModelFeatures(!showModelFeatures)}
          className="flex w-full items-center justify-between px-5 py-3.5 text-left transition-colors hover:bg-[var(--color-db-surface-hover)]"
        >
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-[var(--color-db-text-primary)]">
              Engineered Model Features
            </span>
            <span className="rounded-full bg-[var(--color-db-accent-muted)] px-2 py-0.5 text-[10px] font-semibold text-[var(--color-db-accent)]">
              ML
            </span>
          </div>
          <svg
            className={`h-4 w-4 text-[var(--color-db-text-tertiary)] transition-transform ${showModelFeatures ? "rotate-180" : ""}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        </button>
        {showModelFeatures && (
          <div className="border-t border-[var(--color-db-border-subtle)] px-5 py-3">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-[var(--color-db-border-subtle)]">
                    <th className="py-2 pr-4 font-medium text-[var(--color-db-text-tertiary)]">
                      Feature
                    </th>
                    <th className="py-2 pr-4 font-medium text-[var(--color-db-text-tertiary)]">
                      Raw Value
                    </th>
                    <th className="py-2 pr-4 font-medium text-[var(--color-db-text-tertiary)]">
                      Engineered
                    </th>
                    <th className="py-2 font-medium text-[var(--color-db-text-tertiary)]">
                      Source
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {model_features.map((f) => (
                    <tr
                      key={f.feature_name}
                      className="border-b border-[var(--color-db-border-subtle)] last:border-b-0"
                    >
                      <td className="font-db-mono py-2 pr-4 font-medium text-[var(--color-db-text-primary)]">
                        {f.feature_name}
                      </td>
                      <td className="py-2 pr-4 text-[var(--color-db-text-secondary)]">
                        {f.raw_value}
                      </td>
                      <td className="font-db-mono py-2 pr-4 text-[var(--color-db-text-secondary)]">
                        {f.engineered_value}
                      </td>
                      <td className="py-2 text-[var(--color-db-text-muted)]">{f.source}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </DashboardCard>

      {/* Data Source Provenance */}
      <DashboardCard>
        <h3 className="mb-3 text-sm font-semibold text-[var(--color-db-text-primary)]">
          Data Source Provenance
        </h3>
        <div className="space-y-2">
          {[
            { source: "Redfin", updated: "Feb 18, 2026", fields: 24 },
            { source: "Wake County Tax Records", updated: "Jan 2026", fields: 8 },
            { source: "Police Incidents API", updated: "Feb 15, 2026", fields: 12 },
            { source: "NCES School Directory", updated: "2025-2026", fields: 15 },
            { source: "OpenStreetMap", updated: "Feb 2026", fields: 18 },
            { source: "TIGER/Line Census", updated: "2024", fields: 6 },
          ].map((s) => (
            <div
              key={s.source}
              className="flex items-center justify-between rounded-[var(--radius-db-xs)] bg-[var(--color-db-surface-alt)] px-4 py-2.5"
            >
              <span className="text-xs font-medium text-[var(--color-db-text-primary)]">
                {s.source}
              </span>
              <div className="flex gap-4 text-[11px] text-[var(--color-db-text-muted)]">
                <span>{s.fields} fields</span>
                <span>Updated: {s.updated}</span>
              </div>
            </div>
          ))}
        </div>
      </DashboardCard>
    </div>
  );
}

export default PropertyDetailsTab;
