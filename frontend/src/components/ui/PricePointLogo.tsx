interface PricePointLogoProps {
  variant?: "icon" | "compact" | "footer";
  size?: number;
  className?: string;
}

const ICON_SIZES = {
  icon: { width: 36, height: 47 },
  compact: { width: 28, height: 36 },
  footer: { width: 20, height: 26 },
};

const TEXT_SIZES = {
  compact: "text-base font-semibold",
  footer: "text-sm font-semibold",
};

function LogoIcon({ size, id }: { size: { width: number; height: number }; id: string }) {
  return (
    <svg
      width={size.width}
      height={size.height}
      viewBox="0 0 100 130"
      fill="none"
      aria-hidden="true"
    >
      <defs>
        <linearGradient id={`${id}-pinG`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#7B9BFF" />
          <stop offset="100%" stopColor="#3A5FD0" />
        </linearGradient>
        <linearGradient id={`${id}-pS`} x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="transparent" />
          <stop offset="55%" stopColor="transparent" />
          <stop offset="100%" stopColor="rgba(0,0,0,0.22)" />
        </linearGradient>
        <linearGradient id={`${id}-houseG`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#FFFFFF" />
          <stop offset="100%" stopColor="#C8D4FF" />
        </linearGradient>
        <radialGradient id={`${id}-cg`} cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#A0BFFF" />
          <stop offset="100%" stopColor="#3A5FFF" stopOpacity="0" />
        </radialGradient>
        <filter id={`${id}-ng`} x="-100%" y="-100%" width="300%" height="300%">
          <feGaussianBlur stdDeviation="2.5" result="b" />
          <feMerge>
            <feMergeNode in="b" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
        <filter id={`${id}-ds`} x="-15%" y="-5%" width="130%" height="120%">
          <feDropShadow dx="0" dy="6" stdDeviation="6" floodColor="#1A3080" floodOpacity="0.5" />
        </filter>
        <filter id={`${id}-tg`} x="-30%" y="-30%" width="160%" height="160%">
          <feGaussianBlur stdDeviation="1.8" result="b" />
          <feMerge>
            <feMergeNode in="b" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
        <clipPath id={`${id}-cc`}>
          <circle cx="50" cy="46" r="34" />
        </clipPath>
      </defs>
      <path
        d="M50 3 C27.4 3 9 21.4 9 44 C9 66.6 50 127 50 127 C50 127 91 66.6 91 44 C91 21.4 72.6 3 50 3 Z"
        fill={`url(#${id}-pinG)`}
        filter={`url(#${id}-ds)`}
      />
      <path
        d="M50 3 C27.4 3 9 21.4 9 44 C9 66.6 50 127 50 127 C50 127 91 66.6 91 44 C91 21.4 72.6 3 50 3 Z"
        fill={`url(#${id}-pS)`}
      />
      <circle cx="50" cy="46" r="34" fill="#0A0D18" />
      <g clipPath={`url(#${id}-cc)`}>
        <rect x="62" y="20" width="6" height="12" rx="1" fill={`url(#${id}-houseG)`} />
        <path
          d="M24,70 L24,40 L50,18 L76,40 L76,70"
          fill="none"
          stroke={`url(#${id}-houseG)`}
          strokeWidth="4.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </g>
      <g clipPath={`url(#${id}-cc)`} opacity="0.75">
        <polyline
          points="50,48 50,37 44,31"
          fill="none"
          stroke={`url(#${id}-houseG)`}
          strokeWidth="0.9"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <polyline
          points="50,48 50,37 58,37"
          fill="none"
          stroke={`url(#${id}-houseG)`}
          strokeWidth="0.9"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <polyline
          points="50,48 59,48 69,65"
          fill="none"
          stroke={`url(#${id}-houseG)`}
          strokeWidth="0.9"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <polyline
          points="50,48 50,62 40,72"
          fill="none"
          stroke={`url(#${id}-houseG)`}
          strokeWidth="0.9"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <polyline
          points="50,48 36,48 31,44"
          fill="none"
          stroke={`url(#${id}-houseG)`}
          strokeWidth="0.9"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <circle cx="44" cy="31" r="2" fill={`url(#${id}-houseG)`} />
        <circle cx="58" cy="37" r="2" fill={`url(#${id}-houseG)`} />
        <circle cx="69" cy="65" r="2" fill={`url(#${id}-houseG)`} />
        <circle cx="40" cy="72" r="2" fill={`url(#${id}-houseG)`} />
        <circle cx="31" cy="44" r="2" fill={`url(#${id}-houseG)`} />
      </g>
      <g clipPath={`url(#${id}-cc)`} filter={`url(#${id}-tg)`}>
        <polyline
          points="20,70 30,55 40,66 50,48 60,60 64,51"
          fill="none"
          stroke="#7EB5FF"
          strokeWidth="3"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <polygon points="69,40 59,49 66,47 69,53" fill="#7EB5FF" />
      </g>
      <circle cx="50" cy="48" r="8" fill={`url(#${id}-cg)`} filter={`url(#${id}-ng)`} />
      <circle cx="50" cy="48" r="3.5" fill="white" opacity="0.95" />
    </svg>
  );
}

function PricePointLogo({ variant = "compact", className = "" }: PricePointLogoProps) {
  const iconSize = ICON_SIZES[variant];
  const id = `pp-${variant}`;

  if (variant === "icon") {
    return (
      <span className={`inline-flex items-center ${className}`}>
        <LogoIcon size={iconSize} id={id} />
      </span>
    );
  }

  const textClass = TEXT_SIZES[variant];

  return (
    <span className={`inline-flex items-center gap-2 ${className}`}>
      <LogoIcon size={iconSize} id={id} />
      <span className={textClass}>
        Price
        <span className="bg-gradient-to-r from-[#5B7FFF] to-[#8B5CF6] bg-clip-text text-transparent">
          Point
        </span>
      </span>
    </span>
  );
}

export default PricePointLogo;
