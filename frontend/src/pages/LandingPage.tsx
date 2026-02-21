import { useNavigate } from "react-router-dom";
import { useEffect, useRef } from "react";
import SearchBar from "../components/SearchBar/SearchBar";
import { startViewTransition } from "../utils/viewTransition";
import type { GeocodeResult } from "../types";

/* ── Inline SVG Icons ── */

function ChartIcon() {
  return (
    <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
    </svg>
  );
}

function ShieldIcon() {
  return (
    <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
    </svg>
  );
}

function AcademicCapIcon() {
  return (
    <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M4.26 10.147a60.436 60.436 0 00-.491 6.347A48.627 48.627 0 0112 20.904a48.627 48.627 0 018.232-4.41 60.46 60.46 0 00-.491-6.347m-15.482 0a50.57 50.57 0 00-2.658-.813A59.905 59.905 0 0112 3.493a59.902 59.902 0 0110.399 5.84c-.896.248-1.783.52-2.658.814m-15.482 0A50.697 50.697 0 0112 13.489a50.702 50.702 0 017.74-3.342M6.75 15a.75.75 0 100-1.5.75.75 0 000 1.5zm0 0v-3.675A55.378 55.378 0 0112 8.443m-7.007 11.55A5.981 5.981 0 006.75 15.75v-1.5" />
    </svg>
  );
}

function TreeIcon() {
  return (
    <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 21v-6m0 0l-3-3m3 3l3-3m-3-3V3m0 0L9 6m3-3l3 3M5.25 16.5c-1.5 0-2.25-.75-2.25-2.25S5.25 9 7.5 9c0-2.25 1.5-4.5 4.5-4.5s4.5 2.25 4.5 4.5c2.25 0 3.75 2.25 3.75 5.25S19.5 16.5 18.75 16.5" />
    </svg>
  );
}

function SearchIcon({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
    </svg>
  );
}

function CpuIcon() {
  return (
    <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 3v1.5M4.5 8.25H3m18 0h-1.5M4.5 12H3m18 0h-1.5m-15 3.75H3m18 0h-1.5M8.25 19.5V21M12 3v1.5m0 15V21m3.75-18v1.5m0 15V21m-9-1.5h10.5a2.25 2.25 0 002.25-2.25V6.75a2.25 2.25 0 00-2.25-2.25H6.75A2.25 2.25 0 004.5 6.75v10.5a2.25 2.25 0 002.25 2.25z" />
    </svg>
  );
}

function CheckCircleIcon() {
  return (
    <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  );
}

function ArrowRightIcon() {
  return (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
    </svg>
  );
}

/* ── Section: Landing Nav ── */

function LandingNav() {
  return (
    <nav
      className="landing-nav fixed top-0 right-0 left-0 z-50 flex h-16 items-center justify-between px-6 sm:px-8"
      style={{
        backgroundColor: "rgba(15, 17, 23, 0.85)",
        backdropFilter: "blur(16px)",
        WebkitBackdropFilter: "blur(16px)",
        borderBottom: "1px solid var(--color-db-border-subtle)",
      }}
    >
      <a href="/" className="flex items-center gap-2.5 text-[var(--color-db-text-primary)]">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--color-db-accent)]">
          <span className="text-sm font-bold text-white">P</span>
        </div>
        <span className="text-base font-semibold">PricePoint</span>
      </a>

      <div className="flex items-center gap-3">
        <a
          href="/login"
          className="hidden rounded-[var(--radius-db-sm)] px-4 py-2 text-sm font-medium text-[var(--color-db-text-secondary)] transition-colors hover:text-[var(--color-db-text-primary)] sm:inline-flex"
        >
          Sign In
        </a>
        <a
          href="/signup"
          className="inline-flex items-center gap-2 rounded-[var(--radius-db-sm)] bg-[var(--color-db-accent)] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[var(--color-db-accent-hover)]"
        >
          Get Started
        </a>
      </div>
    </nav>
  );
}

/* ── Section: Hero ── */

function HeroSection({ onSelect }: { onSelect: (r: GeocodeResult) => void }) {
  return (
    <section className="relative flex min-h-screen flex-col items-center justify-center px-4 pt-16">
      {/* Background grid effect */}
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage:
            "linear-gradient(var(--color-db-text-tertiary) 1px, transparent 1px), linear-gradient(90deg, var(--color-db-text-tertiary) 1px, transparent 1px)",
          backgroundSize: "60px 60px",
        }}
      />
      {/* Radial glow behind search */}
      <div
        className="pointer-events-none absolute top-1/3 left-1/2 h-[600px] w-[800px] -translate-x-1/2 -translate-y-1/2 rounded-full opacity-20"
        style={{
          background: "radial-gradient(ellipse, var(--color-db-accent) 0%, transparent 70%)",
        }}
      />

      <div className="landing-stagger relative z-10 flex w-full max-w-2xl flex-col items-center gap-8 text-center">
        <div className="flex flex-col gap-4">
          <h1 className="text-3xl font-bold tracking-tight text-[var(--color-db-text-primary)] sm:text-5xl sm:leading-[1.15]">
            Know what a home is
            <br />
            <span className="bg-gradient-to-r from-[var(--color-db-accent)] to-[var(--color-db-cyan)] bg-clip-text text-transparent">
              really worth
            </span>{" "}
            before you buy.
          </h1>
          <p className="mx-auto max-w-xl text-base leading-relaxed text-[var(--color-db-text-secondary)] sm:text-lg">
            PricePoint combines listing data, crime statistics, school ratings, neighborhood
            demographics, and economic indicators into a single AI-powered property analysis.
          </p>
        </div>

        <div className="w-full max-w-lg">
          <SearchBar onSelect={onSelect} placeholder="Search any address..." variant="landing" />
        </div>

        <p className="text-sm text-[var(--color-db-text-tertiary)]">
          Analyzing properties across 48 states &middot; 2M+ listings indexed
        </p>
      </div>
    </section>
  );
}

/* ── Section: Feature Showcase ── */

const features = [
  {
    icon: <ChartIcon />,
    label: "AI Valuation Model",
    description:
      "See what the home is actually worth, with confidence intervals and full model explainability.",
    color: "var(--color-db-accent)",
    bgColor: "var(--color-db-accent-muted)",
  },
  {
    icon: <ShieldIcon />,
    label: "Crime & Safety",
    description:
      "Crime density maps, incident breakdowns, and z-score comparisons to county averages.",
    color: "var(--color-db-red)",
    bgColor: "var(--color-db-red-muted)",
  },
  {
    icon: <AcademicCapIcon />,
    label: "Schools & Demographics",
    description:
      "Assigned school ratings, district boundaries, income distribution, and population trends.",
    color: "var(--color-db-cyan)",
    bgColor: "var(--color-db-cyan-muted)",
  },
  {
    icon: <TreeIcon />,
    label: "Neighborhood Quality",
    description:
      "Greenspace coverage, points of interest, noise exposure, and environmental risk scores.",
    color: "var(--color-db-green)",
    bgColor: "var(--color-db-green-muted)",
  },
];

function FeatureShowcase() {
  return (
    <section className="px-4 py-24 sm:px-8">
      <div className="mx-auto max-w-6xl">
        <div className="mb-12 text-center">
          <p className="mb-3 text-xs font-semibold uppercase tracking-[0.08em] text-[var(--color-db-accent)]">
            What PricePoint Analyzes
          </p>
          <h2 className="text-2xl font-bold text-[var(--color-db-text-primary)] sm:text-3xl">
            Every angle of a property, in one place
          </h2>
        </div>
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {features.map((f) => (
            <div
              key={f.label}
              className="landing-reveal group rounded-[var(--radius-db-md)] border border-[var(--color-db-border-subtle)] bg-[var(--color-db-surface)] p-6 transition-all duration-200 hover:border-[var(--color-db-border)] hover:shadow-[var(--shadow-db-glow)]"
            >
              <div
                className="mb-4 flex h-10 w-10 items-center justify-center rounded-[var(--radius-db-sm)]"
                style={{ backgroundColor: f.bgColor, color: f.color }}
              >
                {f.icon}
              </div>
              <h3 className="mb-2 text-sm font-semibold text-[var(--color-db-text-primary)]">
                {f.label}
              </h3>
              <p className="text-sm leading-relaxed text-[var(--color-db-text-secondary)]">
                {f.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ── Section: Dashboard Preview ── */

function DashboardPreview() {
  return (
    <section className="relative overflow-hidden px-4 py-24 sm:px-8">
      <div className="mx-auto max-w-6xl">
        <div className="mb-12 text-center">
          <p className="mb-3 text-xs font-semibold uppercase tracking-[0.08em] text-[var(--color-db-accent)]">
            Product Preview
          </p>
          <h2 className="text-2xl font-bold text-[var(--color-db-text-primary)] sm:text-3xl">
            Deep analysis at your fingertips
          </h2>
        </div>

        {/* Mockup container */}
        <div className="landing-reveal relative">
          <div className="rounded-[var(--radius-db-lg)] border border-[var(--color-db-border)] bg-[var(--color-db-surface)] p-1 shadow-[0_20px_60px_rgba(0,0,0,0.4)]">
            {/* Fake browser chrome */}
            <div className="flex items-center gap-2 rounded-t-[var(--radius-db-md)] bg-[var(--color-db-surface-alt)] px-4 py-3">
              <div className="flex gap-1.5">
                <div className="h-3 w-3 rounded-full bg-[#F87171] opacity-60" />
                <div className="h-3 w-3 rounded-full bg-[#FBBF24] opacity-60" />
                <div className="h-3 w-3 rounded-full bg-[#34D399] opacity-60" />
              </div>
              <div className="ml-4 flex flex-1 items-center gap-2 rounded-[var(--radius-db-xs)] border border-[var(--color-db-border)] bg-[var(--color-db-bg)] px-3 py-1.5">
                <svg className="h-3 w-3 text-[var(--color-db-text-muted)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
                <span className="text-xs text-[var(--color-db-text-muted)]">pricepoint.app/dashboard</span>
              </div>
            </div>

            {/* Dashboard content mockup */}
            <div className="relative overflow-hidden rounded-b-[var(--radius-db-md)] bg-[var(--color-db-bg)] p-6">
              <div className="flex gap-5">
                {/* Left panel mockup */}
                <div className="hidden w-[220px] shrink-0 flex-col gap-3 md:flex">
                  {/* Photo placeholder */}
                  <div className="aspect-[4/3] rounded-[var(--radius-db-sm)] bg-gradient-to-br from-[var(--color-db-surface-alt)] to-[var(--color-db-surface)]">
                    <div className="flex h-full items-center justify-center text-[var(--color-db-text-muted)]">
                      <svg className="h-8 w-8 opacity-40" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.41a2.25 2.25 0 013.182 0l2.909 2.91m-18 3.75h16.5a1.5 1.5 0 001.5-1.5V6a1.5 1.5 0 00-1.5-1.5H3.75A1.5 1.5 0 002.25 6v12a1.5 1.5 0 001.5 1.5zm10.5-11.25h.008v.008h-.008V8.25zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z" />
                      </svg>
                    </div>
                  </div>
                  {/* Price */}
                  <div className="rounded-[var(--radius-db-sm)] border border-[var(--color-db-border-subtle)] bg-[var(--color-db-surface)] p-3">
                    <div className="mb-1 flex items-center gap-2">
                      <span className="rounded-full bg-[var(--color-db-green-muted)] px-2 py-0.5 text-[10px] font-semibold text-[var(--color-db-green)]">
                        For Sale
                      </span>
                    </div>
                    <p className="text-lg font-bold text-[var(--color-db-text-primary)]" style={{ fontFamily: "var(--font-db-mono)" }}>
                      $485,000
                    </p>
                    <p className="text-xs text-[var(--color-db-text-tertiary)]">
                      3 bed &middot; 2 bath &middot; 2,150 sqft
                    </p>
                  </div>
                  {/* Stat rows */}
                  <div className="space-y-1.5">
                    {["Built 2018", "0.42 acres", "2-Car Garage"].map((s) => (
                      <div key={s} className="flex items-center gap-2 rounded-[var(--radius-db-xs)] bg-[var(--color-db-surface-alt)] px-3 py-2">
                        <div className="h-2 w-2 rounded-full bg-[var(--color-db-text-muted)]" />
                        <span className="text-xs text-[var(--color-db-text-secondary)]">{s}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Right panel mockup */}
                <div className="flex-1 space-y-4">
                  {/* Estimate Range Bar mockup */}
                  <div className="relative rounded-[var(--radius-db-sm)] border border-[var(--color-db-border-subtle)] bg-[var(--color-db-surface)] p-4">
                    <div className="mb-3 flex items-center justify-between">
                      <span className="text-xs font-semibold text-[var(--color-db-text-primary)]">Model Valuation Estimate</span>
                      <span className="rounded-full bg-[var(--color-db-green-muted)] px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-[var(--color-db-green)]">
                        Value
                      </span>
                    </div>
                    {/* Range bar */}
                    <div className="mb-2 flex items-center justify-between text-xs text-[var(--color-db-text-tertiary)]">
                      <span style={{ fontFamily: "var(--font-db-mono)" }}>$410K</span>
                      <span className="text-sm font-bold text-[var(--color-db-accent)]" style={{ fontFamily: "var(--font-db-mono)" }}>$462K</span>
                      <span style={{ fontFamily: "var(--font-db-mono)" }}>$520K</span>
                    </div>
                    <div className="relative h-3 overflow-hidden rounded-full bg-[var(--color-db-surface-alt)]">
                      <div className="absolute inset-y-0 left-[15%] right-[20%] rounded-full bg-gradient-to-r from-[var(--color-db-accent)] to-[var(--color-db-cyan)] opacity-40" />
                      <div className="absolute top-1/2 left-[45%] h-4 w-1 -translate-y-1/2 rounded-full bg-[var(--color-db-accent)]" />
                    </div>

                    {/* Annotation callout */}
                    <div className="absolute -right-2 -top-2 hidden items-center gap-2 rounded-full border border-[var(--color-db-accent)] bg-[var(--color-db-bg)] px-3 py-1.5 shadow-[var(--shadow-db-glow)] md:flex">
                      <div className="h-1.5 w-1.5 rounded-full bg-[var(--color-db-accent)]" />
                      <span className="text-[10px] font-medium text-[var(--color-db-accent)]">AI-predicted value</span>
                    </div>
                  </div>

                  {/* Two column charts */}
                  <div className="grid gap-4 md:grid-cols-2">
                    {/* SHAP waterfall mockup */}
                    <div className="relative rounded-[var(--radius-db-sm)] border border-[var(--color-db-border-subtle)] bg-[var(--color-db-surface)] p-4">
                      <span className="mb-3 block text-[10px] font-semibold uppercase tracking-wider text-[var(--color-db-text-primary)]">
                        Value Drivers (SHAP)
                      </span>
                      <div className="space-y-2">
                        {[
                          { label: "Square Footage", w: "75%", pos: true },
                          { label: "School Rating", w: "55%", pos: true },
                          { label: "Year Built", w: "40%", pos: true },
                          { label: "Crime Rate", w: "30%", pos: false },
                          { label: "Lot Size", w: "20%", pos: true },
                        ].map((bar) => (
                          <div key={bar.label} className="flex items-center gap-2">
                            <span className="w-20 text-[10px] text-[var(--color-db-text-tertiary)]">{bar.label}</span>
                            <div className="relative h-3 flex-1 overflow-hidden rounded-full bg-[var(--color-db-surface-alt)]">
                              <div
                                className="h-full rounded-full"
                                style={{
                                  width: bar.w,
                                  backgroundColor: bar.pos ? "var(--color-db-green)" : "var(--color-db-red)",
                                  opacity: 0.6,
                                }}
                              />
                            </div>
                          </div>
                        ))}
                      </div>
                      {/* Annotation */}
                      <div className="absolute -right-2 -bottom-2 hidden items-center gap-2 rounded-full border border-[var(--color-db-cyan)] bg-[var(--color-db-bg)] px-3 py-1.5 md:flex">
                        <div className="h-1.5 w-1.5 rounded-full bg-[var(--color-db-cyan)]" />
                        <span className="text-[10px] font-medium text-[var(--color-db-cyan)]">What drives the estimate</span>
                      </div>
                    </div>

                    {/* Risk scores mockup */}
                    <div className="relative rounded-[var(--radius-db-sm)] border border-[var(--color-db-border-subtle)] bg-[var(--color-db-surface)] p-4">
                      <span className="mb-3 block text-[10px] font-semibold uppercase tracking-wider text-[var(--color-db-text-primary)]">
                        Risk Assessment
                      </span>
                      <div className="grid grid-cols-2 gap-2">
                        {[
                          { label: "Flood", score: "Low", color: "var(--color-db-green)" },
                          { label: "Fire", score: "Low", color: "var(--color-db-green)" },
                          { label: "Crime", score: "Med", color: "var(--color-db-yellow)" },
                          { label: "Utility", score: "Low", color: "var(--color-db-green)" },
                          { label: "Quake", score: "Very Low", color: "var(--color-db-green)" },
                          { label: "Air", score: "Fair", color: "var(--color-db-yellow)" },
                        ].map((r) => (
                          <div key={r.label} className="flex items-center justify-between rounded-[var(--radius-db-xs)] bg-[var(--color-db-surface-alt)] px-2.5 py-2">
                            <span className="text-[10px] text-[var(--color-db-text-tertiary)]">{r.label}</span>
                            <span className="text-[10px] font-semibold" style={{ color: r.color }}>{r.score}</span>
                          </div>
                        ))}
                      </div>
                      {/* Annotation */}
                      <div className="absolute -left-2 -top-2 hidden items-center gap-2 rounded-full border border-[var(--color-db-yellow)] bg-[var(--color-db-bg)] px-3 py-1.5 md:flex">
                        <div className="h-1.5 w-1.5 rounded-full bg-[var(--color-db-yellow)]" />
                        <span className="text-[10px] font-medium text-[var(--color-db-yellow)]">Six risk categories</span>
                      </div>
                    </div>
                  </div>

                  {/* Mortgage calc mockup */}
                  <div className="relative rounded-[var(--radius-db-sm)] border border-[var(--color-db-border-subtle)] bg-[var(--color-db-surface)] p-4">
                    <span className="mb-3 block text-xs font-semibold text-[var(--color-db-text-primary)]">Mortgage Calculator</span>
                    <div className="flex items-center gap-6">
                      <div className="flex flex-1 flex-col gap-2">
                        {["Home Price", "Down Payment", "Interest Rate"].map((label) => (
                          <div key={label}>
                            <span className="text-[10px] text-[var(--color-db-text-tertiary)]">{label}</span>
                            <div className="mt-1 h-1.5 rounded-full bg-[var(--color-db-surface-alt)]">
                              <div className="h-full w-3/5 rounded-full bg-[var(--color-db-accent)] opacity-40" />
                            </div>
                          </div>
                        ))}
                      </div>
                      {/* Donut placeholder */}
                      <div className="hidden shrink-0 items-center justify-center sm:flex">
                        <div className="relative h-24 w-24">
                          <svg viewBox="0 0 36 36" className="h-full w-full -rotate-90">
                            <circle cx="18" cy="18" r="14" fill="none" stroke="var(--color-db-surface-alt)" strokeWidth="4" />
                            <circle cx="18" cy="18" r="14" fill="none" stroke="var(--color-db-accent)" strokeWidth="4" strokeDasharray="40 88" strokeLinecap="round" />
                            <circle cx="18" cy="18" r="14" fill="none" stroke="var(--color-db-cyan)" strokeWidth="4" strokeDasharray="20 88" strokeDashoffset="-40" strokeLinecap="round" />
                            <circle cx="18" cy="18" r="14" fill="none" stroke="var(--color-db-yellow)" strokeWidth="4" strokeDasharray="12 88" strokeDashoffset="-60" strokeLinecap="round" />
                            <circle cx="18" cy="18" r="14" fill="none" stroke="var(--color-db-green)" strokeWidth="4" strokeDasharray="8 88" strokeDashoffset="-72" strokeLinecap="round" />
                          </svg>
                          <div className="absolute inset-0 flex flex-col items-center justify-center">
                            <span className="text-[9px] text-[var(--color-db-text-tertiary)]">Monthly</span>
                            <span className="text-sm font-bold text-[var(--color-db-text-primary)]" style={{ fontFamily: "var(--font-db-mono)" }}>$2,847</span>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Annotation */}
                    <div className="absolute -right-2 -bottom-2 hidden items-center gap-2 rounded-full border border-[var(--color-db-green)] bg-[var(--color-db-bg)] px-3 py-1.5 md:flex">
                      <div className="h-1.5 w-1.5 rounded-full bg-[var(--color-db-green)]" />
                      <span className="text-[10px] font-medium text-[var(--color-db-green)]">Real-time mortgage modeling</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Gradient fade at bottom of preview */}
          <div
            className="pointer-events-none absolute right-0 bottom-0 left-0 h-32"
            style={{ background: "linear-gradient(to top, var(--color-db-bg), transparent)" }}
          />
        </div>
      </div>
    </section>
  );
}

/* ── Section: Data Sources ── */

const dataSources = [
  { name: "Redfin", desc: "Listing & sale data" },
  { name: "County Assessors", desc: "Tax assessments & property records" },
  { name: "U.S. Census (ACS)", desc: "Demographics & income" },
  { name: "FRED", desc: "Mortgage rate data" },
  { name: "Local Police APIs", desc: "Crime incident data" },
  { name: "GreatSchools", desc: "School ratings" },
  { name: "USGS / FEMA", desc: "Flood & earthquake risk" },
  { name: "EPA", desc: "Environmental hazard data" },
];

function DataSourcesSection() {
  return (
    <section className="px-4 py-24 sm:px-8">
      <div className="mx-auto max-w-5xl">
        <div className="mb-12 text-center">
          <p className="mb-3 text-xs font-semibold uppercase tracking-[0.08em] text-[var(--color-db-accent)]">
            Data Sources
          </p>
          <h2 className="mb-4 text-2xl font-bold text-[var(--color-db-text-primary)] sm:text-3xl">
            Built on primary sources, not black boxes
          </h2>
          <p className="mx-auto max-w-xl text-sm leading-relaxed text-[var(--color-db-text-secondary)]">
            Every estimate is built on primary sources — not aggregated third-party feeds.
          </p>
        </div>
        <div className="landing-reveal grid grid-cols-2 gap-3 sm:grid-cols-4">
          {dataSources.map((src) => (
            <div
              key={src.name}
              className="flex flex-col items-center gap-1.5 rounded-[var(--radius-db-md)] border border-[var(--color-db-border-subtle)] bg-[var(--color-db-surface)] p-4 text-center transition-colors hover:border-[var(--color-db-border)]"
            >
              <span className="text-sm font-semibold text-[var(--color-db-text-primary)]">
                {src.name}
              </span>
              <span className="text-xs text-[var(--color-db-text-tertiary)]">{src.desc}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ── Section: How It Works ── */

const steps = [
  {
    num: "01",
    icon: <SearchIcon className="h-6 w-6" />,
    title: "Search a property",
    desc: "Enter any residential address in the US.",
    color: "var(--color-db-accent)",
    bgColor: "var(--color-db-accent-muted)",
  },
  {
    num: "02",
    icon: <CpuIcon />,
    title: "We analyze the data",
    desc: "Our ML pipeline pulls listing data, geospatial signals, and economic indicators in real time.",
    color: "var(--color-db-cyan)",
    bgColor: "var(--color-db-cyan-muted)",
  },
  {
    num: "03",
    icon: <CheckCircleIcon />,
    title: "Make a confident decision",
    desc: "Review the valuation estimate, risk scores, and neighborhood deep-dive before you make an offer.",
    color: "var(--color-db-green)",
    bgColor: "var(--color-db-green-muted)",
  },
];

function HowItWorksSection() {
  return (
    <section className="px-4 py-24 sm:px-8">
      <div className="mx-auto max-w-5xl">
        <div className="mb-12 text-center">
          <p className="mb-3 text-xs font-semibold uppercase tracking-[0.08em] text-[var(--color-db-accent)]">
            How It Works
          </p>
          <h2 className="text-2xl font-bold text-[var(--color-db-text-primary)] sm:text-3xl">
            Three steps to clarity
          </h2>
        </div>
        <div className="landing-reveal grid gap-6 sm:grid-cols-3">
          {steps.map((step) => (
            <div key={step.num} className="flex flex-col items-center gap-4 text-center">
              <div className="relative">
                <div
                  className="flex h-14 w-14 items-center justify-center rounded-full"
                  style={{ backgroundColor: step.bgColor, color: step.color }}
                >
                  {step.icon}
                </div>
                <span
                  className="absolute -top-1 -right-1 flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold text-white"
                  style={{ backgroundColor: step.color }}
                >
                  {step.num.slice(-1)}
                </span>
              </div>
              <h3 className="text-sm font-semibold text-[var(--color-db-text-primary)]">
                {step.title}
              </h3>
              <p className="max-w-xs text-sm leading-relaxed text-[var(--color-db-text-secondary)]">
                {step.desc}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ── Section: Sign-Up CTA ── */

function SignUpSection() {
  return (
    <section className="px-4 py-24 sm:px-8">
      <div className="mx-auto max-w-xl text-center">
        <div className="landing-reveal rounded-[var(--radius-db-lg)] border border-[var(--color-db-border)] bg-[var(--color-db-surface)] p-8 sm:p-12">
          <h2 className="mb-3 text-2xl font-bold text-[var(--color-db-text-primary)] sm:text-3xl">
            Start your analysis free
          </h2>
          <p className="mb-8 text-sm text-[var(--color-db-text-secondary)]">
            Search your first property — no credit card required.
          </p>
          <form
            onSubmit={(e) => e.preventDefault()}
            className="flex flex-col gap-3 sm:flex-row"
          >
            <input
              type="email"
              placeholder="Enter your email"
              aria-label="Email address"
              className="flex-1 rounded-[var(--radius-db-sm)] border border-[var(--color-db-border)] bg-[var(--color-db-surface-alt)] px-4 py-3 text-sm text-[var(--color-db-text-primary)] outline-none transition-colors placeholder:text-[var(--color-db-text-muted)] focus:border-[var(--color-db-accent)]"
            />
            <button
              type="submit"
              className="inline-flex items-center justify-center gap-2 rounded-[var(--radius-db-sm)] bg-[var(--color-db-accent)] px-6 py-3 text-sm font-medium text-white transition-colors hover:bg-[var(--color-db-accent-hover)]"
            >
              Get Early Access
              <ArrowRightIcon />
            </button>
          </form>
          <p className="mt-4 text-xs text-[var(--color-db-text-muted)]">
            No spam. No obligation. Cancel anytime.
          </p>
        </div>
      </div>
    </section>
  );
}

/* ── Section: Footer ── */

function LandingFooter() {
  return (
    <footer className="border-t border-[var(--color-db-border-subtle)] px-4 py-8 sm:px-8">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-6 sm:flex-row">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2 text-[var(--color-db-text-primary)]">
            <div className="flex h-6 w-6 items-center justify-center rounded-md bg-[var(--color-db-accent)]">
              <span className="text-[10px] font-bold text-white">P</span>
            </div>
            <span className="text-sm font-semibold">PricePoint</span>
          </div>
          <span className="hidden text-xs text-[var(--color-db-text-muted)] sm:inline">
            AI-powered property intelligence
          </span>
        </div>
        <div className="flex flex-wrap items-center justify-center gap-6">
          {["About", "Privacy Policy", "Terms of Service", "Contact"].map((link) => (
            <a
              key={link}
              href={`/${link.toLowerCase().replace(/\s+/g, "-")}`}
              className="text-xs text-[var(--color-db-text-tertiary)] transition-colors hover:text-[var(--color-db-text-secondary)]"
            >
              {link}
            </a>
          ))}
        </div>
        <p className="text-xs text-[var(--color-db-text-muted)]">
          &copy; {new Date().getFullYear()} PricePoint
        </p>
      </div>
    </footer>
  );
}

/* ── Main Page Component ── */

function LandingPage() {
  const navigate = useNavigate();
  const mainRef = useRef<HTMLDivElement>(null);

  function handleSelect(result: GeocodeResult) {
    const url = `/results?address=${encodeURIComponent(result.display_name)}&lat=${result.lat}&lon=${result.lon}`;
    startViewTransition(() => {
      navigate(url);
    });
  }

  /* Scroll-triggered reveal for .landing-reveal elements */
  useEffect(() => {
    const root = mainRef.current;
    if (!root || typeof IntersectionObserver === "undefined") return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.15 },
    );

    const revealElements = root.querySelectorAll(".landing-reveal");
    revealElements.forEach((el) => observer.observe(el));

    return () => observer.disconnect();
  }, []);

  return (
    <div
      ref={mainRef}
      className="min-h-screen bg-[var(--color-db-bg)]"
      style={{ fontFamily: "var(--font-db-sans)" }}
    >
      <LandingNav />
      <HeroSection onSelect={handleSelect} />
      <FeatureShowcase />
      <DashboardPreview />
      <DataSourcesSection />
      <HowItWorksSection />
      <SignUpSection />
      <LandingFooter />
    </div>
  );
}

export default LandingPage;
