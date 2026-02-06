import type { ClimateRisk } from "../../types";

interface ClimateRiskSectionProps {
  climateRisk: ClimateRisk;
}

function scoreColor(score: number): string {
  if (score <= 3) return "bg-status-maint";
  if (score <= 6) return "bg-yellow-400";
  return "bg-status-rented";
}

function RiskBar({ label, risk, score }: { label: string; risk: string; score: number }) {
  return (
    <div>
      <div className="flex items-center justify-between">
        <p className="text-sm font-bold text-text-pri">{label}</p>
        <span className="text-xs font-medium text-text-sec">{risk}</span>
      </div>
      <div
        className="mt-1 flex gap-1"
        role="meter"
        aria-label={`${label} score`}
        aria-valuenow={score}
        aria-valuemin={1}
        aria-valuemax={10}
      >
        {Array.from({ length: 10 }, (_, i) => (
          <div
            key={i}
            className={`h-3 flex-1 rounded-sm ${i < score ? scoreColor(score) : "bg-bg-main"}`}
          />
        ))}
      </div>
      <p className="mt-0.5 text-right text-xs text-text-sec">{score}/10</p>
    </div>
  );
}

function ClimateRiskSection({ climateRisk }: ClimateRiskSectionProps) {
  return (
    <section
      aria-label="Climate risk"
      className="rounded-lg bg-bg-card/80 p-5 shadow-soft backdrop-blur-md sm:p-8"
    >
      <h2 className="text-lg font-bold text-text-pri">Climate Risk</h2>
      <div className="mt-4 space-y-4">
        <RiskBar label="Flood Risk" risk={climateRisk.flood_risk} score={climateRisk.flood_score} />
        <RiskBar label="Fire Risk" risk={climateRisk.fire_risk} score={climateRisk.fire_score} />
      </div>
    </section>
  );
}

export default ClimateRiskSection;
