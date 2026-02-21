import {
  getGradeLabel,
  getGaugeColor,
  COLOR_RED,
  COLOR_AMBER,
  COLOR_BLUE,
  COLOR_GREEN,
} from "../../../utils/chartTokens";

interface SemiCircularGaugeProps {
  value: number;
  max?: number;
  label: string;
  color?: string;
  size?: number;
  suffix?: string;
  showGrade?: boolean;
}

function SemiCircularGauge({
  value,
  max = 100,
  label,
  color,
  size = 160,
  suffix = "",
  showGrade = true,
}: SemiCircularGaugeProps) {
  const pct = Math.min(value / max, 1);
  const r = (size - 20) / 2;
  const cx = size / 2;
  const cy = size / 2 + 10;

  // Semicircle arc from 180deg to 0deg (left to right)
  const arcLength = Math.PI * r;
  const dashOffset = arcLength * (1 - pct);

  const startX = cx - r;
  const startY = cy;
  const endX = cx + r;
  const endY = cy;

  const pathD = `M ${startX} ${startY} A ${r} ${r} 0 0 1 ${endX} ${endY}`;

  const gradientId = `gauge-gradient-${label.replace(/\s+/g, "-").toLowerCase()}`;
  const resolvedColor = color || getGaugeColor(pct);
  const grade = getGradeLabel(value);

  return (
    <div className="flex flex-col items-center">
      <svg width={size} height={size / 2 + 20} viewBox={`0 0 ${size} ${size / 2 + 20}`}>
        <defs>
          <linearGradient id={gradientId} x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor={COLOR_RED} />
            <stop offset="40%" stopColor={COLOR_AMBER} />
            <stop offset="70%" stopColor={COLOR_BLUE} />
            <stop offset="100%" stopColor={COLOR_GREEN} />
          </linearGradient>
        </defs>
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
          stroke={color ? resolvedColor : `url(#${gradientId})`}
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
          {Math.round(value)}{suffix}
        </text>
      </svg>
      {showGrade && (
        <span
          className="text-xs font-semibold"
          style={{ color: grade.color }}
        >
          {grade.text}
        </span>
      )}
      <span className="mt-0.5 text-xs font-medium text-[var(--color-db-text-secondary)]">{label}</span>
    </div>
  );
}

export default SemiCircularGauge;
