import { useState } from "react";
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from "recharts";
import { useMortgageCalculator } from "../../hooks/useMortgageCalculator";
import { useMortgageDefaults } from "../../hooks/useMortgageDefaults";
import type { MortgageInputs } from "../../types";

interface MortgageCalculatorProps {
  listedPrice: number;
  annualTax: number;
  monthlyHoa: number;
}

const currency = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

const COLORS = ["#4f46e5", "#ff5c8e", "#47d1a0", "#fbbf24", "#c4c4c4"];

function MortgageCalculator({ listedPrice, annualTax, monthlyHoa }: MortgageCalculatorProps) {
  const { defaults } = useMortgageDefaults();

  const [inputs, setInputs] = useState<MortgageInputs>({
    homePrice: listedPrice,
    downPaymentPercent: defaults.downPaymentPercent,
    interestRate: defaults.interestRate,
    loanTermYears: defaults.loanTermYears,
    annualTax,
    annualInsurance: defaults.annualInsurance,
    monthlyHoa,
  });

  const breakdown = useMortgageCalculator(inputs);

  const chartData = [
    { name: "Principal", value: breakdown.principal },
    { name: "Interest", value: breakdown.interest },
    { name: "Tax", value: breakdown.tax },
    { name: "Insurance", value: breakdown.insurance },
    { name: "HOA", value: breakdown.hoa },
  ].filter((d) => d.value > 0);

  function update(field: keyof MortgageInputs, value: number) {
    setInputs((prev) => ({ ...prev, [field]: value }));
  }

  return (
    <section
      aria-label="Mortgage calculator"
      className="rounded-lg bg-bg-card/80 p-5 shadow-soft backdrop-blur-md sm:p-8"
    >
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold text-text-pri">Mortgage Calculator</h2>
        <a
          href="/settings"
          aria-label="Mortgage settings"
          className="text-text-sec hover:text-brand-blue"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="h-5 w-5"
            viewBox="0 0 20 20"
            fill="currentColor"
            aria-hidden="true"
          >
            <path
              fillRule="evenodd"
              d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z"
              clipRule="evenodd"
            />
          </svg>
        </a>
      </div>

      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <div className="space-y-4">
          <SliderInput
            label="Home Price"
            value={inputs.homePrice}
            min={50000}
            max={2000000}
            step={5000}
            format={(v) => currency.format(v)}
            onChange={(v) => update("homePrice", v)}
          />
          <SliderInput
            label="Down Payment"
            value={inputs.downPaymentPercent}
            min={0}
            max={100}
            step={1}
            suffix="%"
            onChange={(v) => update("downPaymentPercent", v)}
          />
          <SliderInput
            label="Interest Rate"
            value={inputs.interestRate}
            min={0}
            max={15}
            step={0.125}
            suffix="%"
            onChange={(v) => update("interestRate", v)}
          />
          <SliderInput
            label="Loan Term"
            value={inputs.loanTermYears}
            min={10}
            max={30}
            step={5}
            suffix=" yrs"
            onChange={(v) => update("loanTermYears", v)}
          />
        </div>

        <div className="flex flex-col items-center justify-center">
          <p className="text-sm font-medium text-text-sec">Monthly Payment</p>
          <p className="text-3xl font-bold text-brand-blue">{currency.format(breakdown.total)}</p>
          <div className="mt-2" style={{ width: 200, height: 200 }}>
            <ResponsiveContainer>
              <PieChart>
                <Pie
                  data={chartData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={80}
                >
                  {chartData.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(value) => currency.format(Number(value ?? 0))} />
                <Legend iconSize={8} wrapperStyle={{ fontSize: 11 }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </section>
  );
}

interface SliderInputProps {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  suffix?: string;
  format?: (v: number) => string;
  onChange: (v: number) => void;
}

function SliderInput({ label, value, min, max, step, suffix, format, onChange }: SliderInputProps) {
  const displayValue = format ? format(value) : `${value}${suffix ?? ""}`;
  return (
    <div>
      <div className="flex items-center justify-between">
        <label className="text-xs font-medium text-text-sec">{label}</label>
        <span className="text-sm font-bold text-text-pri">{displayValue}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="mt-1 w-full accent-brand-blue"
        aria-label={label}
      />
    </div>
  );
}

export default MortgageCalculator;
