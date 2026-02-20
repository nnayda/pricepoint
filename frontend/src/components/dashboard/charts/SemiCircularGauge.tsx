interface SemiCircularGaugeProps {
  value: number;
  max?: number;
  label: string;
  color?: string;
  size?: number;
}

function SemiCircularGauge({
  value,
  max = 100,
  label,
  color = "var(--color-db-accent)",
  size = 160,
}: SemiCircularGaugeProps) {
  const pct = Math.min(value / max, 1);
  const r = (size - 20) / 2;
  const cx = size / 2;
  const cy = size / 2 + 10;

  // Semicircle arc from 180° to 0° (left to right)
  const arcLength = Math.PI * r;
  const dashOffset = arcLength * (1 - pct);

  const startX = cx - r;
  const startY = cy;
  const endX = cx + r;
  const endY = cy;

  const pathD = `M ${startX} ${startY} A ${r} ${r} 0 0 1 ${endX} ${endY}`;

  return (
    <div className="flex flex-col items-center">
      <svg width={size} height={size / 2 + 20} viewBox={`0 0 ${size} ${size / 2 + 20}`}>
        {/* Background arc */}
        <path
          d={pathD}
          fill="none"
          stroke="var(--color-db-surface-alt)"
          strokeWidth={10}
          strokeLinecap="round"
        />
        {/* Value arc */}
        <path
          d={pathD}
          fill="none"
          stroke={color}
          strokeWidth={10}
          strokeLinecap="round"
          strokeDasharray={arcLength}
          strokeDashoffset={dashOffset}
          style={{ transition: "stroke-dashoffset 0.8s ease" }}
        />
        {/* Center value */}
        <text
          x={cx}
          y={cy - 10}
          textAnchor="middle"
          fill="var(--color-db-text-primary)"
          fontSize={size / 5}
          fontWeight={700}
          fontFamily="var(--font-db-mono)"
        >
          {Math.round(value)}
        </text>
      </svg>
      <span className="mt-1 text-xs font-medium text-[var(--color-db-text-secondary)]">{label}</span>
    </div>
  );
}

export default SemiCircularGauge;
