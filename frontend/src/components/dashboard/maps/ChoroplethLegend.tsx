import type { LegendConfig } from "../../../utils/choroplethColors";

interface ChoroplethLegendProps {
  config: LegendConfig;
}

export default function ChoroplethLegend({ config }: ChoroplethLegendProps) {
  return (
    <div
      className="absolute bottom-3 left-3 z-[1000] rounded-lg px-3 py-2"
      style={{
        backgroundColor: "rgba(15, 23, 42, 0.85)",
        backdropFilter: "blur(8px)",
      }}
    >
      <div className="mb-1.5 text-[10px] font-semibold text-slate-300">{config.title}</div>
      {config.type === "categorical" ? (
        <div className="flex flex-col gap-1">
          {config.colors.map((color, i) => (
            <div key={config.labels[i]} className="flex items-center gap-1.5">
              <span
                className="h-2.5 w-2.5 rounded-full"
                style={{ backgroundColor: color }}
              />
              <span className="text-[10px] text-slate-400">{config.labels[i]}</span>
            </div>
          ))}
        </div>
      ) : (
        <div className="flex flex-col gap-1">
          <div
            className="h-2 w-28 rounded-sm"
            style={{
              background: `linear-gradient(to right, ${config.colors.join(", ")})`,
            }}
          />
          <div className="flex justify-between text-[9px] text-slate-400">
            {config.labels.map((label) => (
              <span key={label}>{label}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
