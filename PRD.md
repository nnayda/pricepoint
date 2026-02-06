# PricePoint Frontend PRD — Phase 1: Landing Page, Nav Bar & Design System

## Context

The PricePoint frontend is a minimal React 18 + TypeScript app with inline styles, no CSS framework, and two basic pages (Dashboard with a map, Forecast with a text input). The UI does not reflect the "Soft Minimalism" design vision defined in `frontend_design.md`. This phase establishes the design system foundation and builds the first user-facing experience: a sleek landing page with address autocomplete search and a floating glassmorphism navigation bar.

**Phase 2** (documented at bottom, not built now) will add a rich property results page with forecast data, map layers, comparables, and additional data points.

---

## Phase 1 Scope

### 1. Tailwind CSS + Design System Setup

**New dependencies** (dev): `tailwindcss`, `postcss`, `autoprefixer`

**Files:**

| Action | File |
|--------|------|
| NEW | `frontend/postcss.config.js` — PostCSS config with tailwindcss + autoprefixer |
| NEW | `frontend/tailwind.config.ts` — All design tokens from `frontend_design.md` |
| NEW | `frontend/src/index.css` — Tailwind directives + base body styles |
| MODIFY | `frontend/index.html` — Add Plus Jakarta Sans (Google Fonts), update title to "PricePoint" |
| MODIFY | `frontend/src/main.tsx` — Add `import "./index.css"` |

**Design tokens in `tailwind.config.ts`:**

| Category | Token | Value |
|----------|-------|-------|
| Surface | `bg-main` | `#F2F4F7` |
| Surface | `bg-card` | `#FFFFFF` |
| Brand | `brand-blue` | `#4F46E5` |
| Status | `status-rented` / `status-maint` / `status-vacant` | `#FF5C8E` / `#47D1A0` / `#C4C4C4` |
| Text | `text-pri` / `text-sec` | `#1A1A1A` / `#71717A` |
| Radius | `lg` / `md` / `pill` | `32px` / `20px` / `9999px` |
| Shadow | `soft` | `0px 20px 50px rgba(0,0,0,0.04)` |
| Font | `sans` | Plus Jakarta Sans, Inter, system-ui |
| Type | `display-h1` / `heading-h2` / `body-main` / `metadata` | 36px Bold / 20px Semi / 16px Medium / 12px Regular |

---

### 2. Nominatim Geocoding Integration

**Files:**

| Action | File |
|--------|------|
| MODIFY | `frontend/src/types/index.ts` — Add `NominatimResult` interface |
| NEW | `frontend/src/services/nominatim.ts` — Axios client for Nominatim `/search` endpoint |
| NEW | `frontend/src/hooks/useDebounce.ts` — Generic value-based debounce hook |
| NEW | `frontend/src/hooks/useNominatimSearch.ts` — Composes debounce + Nominatim with race-condition safety |

**Key behavior:**
- Separate Axios instance (external API, not the backend proxy)
- `countrycodes=us`, `limit=5`, `format=json`
- 300ms debounce to respect Nominatim's 1 req/sec policy
- Race-condition guard via request counter ref (stale responses discarded)
- `User-Agent: PricePoint/0.1.0` header per Nominatim usage policy

---

### 3. Shared SearchBar Component

**File:** NEW `frontend/src/components/SearchBar/SearchBar.tsx`

**Props:**

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `variant` | `"hero" \| "compact"` | `"hero"` | Hero = large centered (landing), Compact = small (nav bar) |
| `onSelect` | `(result: NominatimResult) => void` | `undefined` | Override default navigation |

**Behavior:**
- Uses `useNominatimSearch` hook for autocomplete
- Dropdown appears with up to 5 address suggestions
- On selection: navigates to `/results?lat=...&lon=...&address=...` (default) or calls `onSelect`
- Loading spinner while fetching
- "No results found" and error states
- **Accessibility:** `role="combobox"`, `aria-expanded`, `aria-activedescendant`, `role="listbox"` + `role="option"`, full keyboard nav (ArrowUp/Down, Enter, Escape)

**Variant styling:**
- Hero: `max-w-2xl`, `px-6 py-4`, `rounded-pill`, `shadow-soft`
- Compact: `max-w-md`, `px-4 py-2`, `text-sm`, `bg-white/70`

---

### 4. Landing Page

**File:** NEW `frontend/src/pages/LandingPage.tsx`

**Route:** `/`

- Full viewport centered layout (`min-h-screen`, `flex`, `items-center`, `justify-center`)
- "PricePoint" brand heading (`text-display-h1`)
- Subtitle: "Residential home value forecasting" (`text-body-main`, `text-text-sec`)
- `<SearchBar variant="hero" />` below
- No navigation bar on this page (Google-style minimal)

---

### 5. Navigation Bar

**File:** NEW `frontend/src/components/NavBar/NavBar.tsx`

- Fixed, horizontally centered, floating pill shape (`rounded-pill`)
- Glassmorphism: `bg-white/70` + `backdrop-blur-xl`
- `shadow-soft`, `z-50`, `top-4`
- Left: "PricePoint" home link (`<Link to="/">`)
- Right: `<SearchBar variant="compact" />`

---

### 6. AppLayout Rewrite

**File:** MODIFY `frontend/src/components/Layout/AppLayout.tsx`

- Replace all inline styles with Tailwind classes
- Use `useLocation()` to detect landing page (`pathname === "/"`)
- Hide NavBar on landing page, show it everywhere else
- `pt-24` padding on non-landing pages for NavBar clearance

---

### 7. Routing Updates

**File:** MODIFY `frontend/src/App.tsx`

| Route | Component | Nav Bar |
|-------|-----------|---------|
| `/` | `LandingPage` | Hidden |
| `/results` | `ResultsPage` (placeholder) | Visible |
| `/forecast` | `ForecastPage` (existing, unchanged) | Visible |
| `/dashboard` | Redirect to `/` | — |

**File:** NEW `frontend/src/pages/ResultsPage.tsx` — Placeholder that reads `address`, `lat`, `lon` from URL search params. Phase 2 will build this out fully.

---

### 8. Transition Strategy

- **Preserved unchanged:** `MapView.tsx`, `PropertyCard.tsx`, `ForecastPage.tsx` — inline styles coexist with Tailwind
- **Deprecated (not deleted):** `DashboardPage.tsx` — no longer routed, kept for reference
- **Zero breaking changes:** `/forecast` route continues to work

---

## Implementation Order

1. Install Tailwind + PostCSS + Autoprefixer (`npm install -D`)
2. Create `postcss.config.js` and `tailwind.config.ts` (design tokens)
3. Create `src/index.css`, update `index.html` (fonts), update `main.tsx` (import CSS)
4. Add `NominatimResult` type, create `services/nominatim.ts`
5. Create `hooks/useDebounce.ts` and `hooks/useNominatimSearch.ts`
6. Create `components/SearchBar/SearchBar.tsx`
7. Create `pages/LandingPage.tsx`
8. Create `components/NavBar/NavBar.tsx`
9. Rewrite `components/Layout/AppLayout.tsx`
10. Create `pages/ResultsPage.tsx` (placeholder)
11. Update `App.tsx` (routing)
12. Write tests for all new files
13. Run `npm run build`, `npm run lint`, `npm run test` to verify

---

## Tests

New test files following existing patterns (vitest + @testing-library/react, `vi.mock()`, `MemoryRouter`):

- `hooks/__tests__/useDebounce.test.ts` — Timer-based behavior
- `hooks/__tests__/useNominatimSearch.test.ts` — Mocked Nominatim, debounce, race conditions
- `services/__tests__/nominatim.test.ts` — Axios mock, param verification
- `components/SearchBar/__tests__/SearchBar.test.tsx` — Variants, autocomplete, keyboard nav, a11y
- `pages/__tests__/LandingPage.test.tsx` — Renders brand + search bar
- `components/NavBar/__tests__/NavBar.test.tsx` — Home link, compact search
- `pages/__tests__/ResultsPage.test.tsx` — URL param display

---

## Verification

1. `npm run build` — no TypeScript or build errors
2. `npm run lint` — ESLint + Prettier pass
3. `npm run test` — all existing + new tests pass
4. Manual: Landing page at `/` shows centered "PricePoint" + large search bar, no nav bar
5. Manual: Typing an address shows Nominatim autocomplete after 300ms
6. Manual: Selecting a result navigates to `/results?lat=...&lon=...&address=...`
7. Manual: Results page shows floating pill nav bar with compact search + home link
8. Manual: `/forecast` still works unchanged
9. Manual: Glassmorphism blur works when scrolling content behind nav

---

## Phase 2 (Future — Not Built Now)

Full property results page at `/results` with:

- **Property details:** Photo, bedrooms/bathrooms, sqft, acreage, description
- **Forecast card:** Predicted value, confidence interval, model version (redesigned with soft minimalism)
- **Interactive map** with switchable layers:
  - POI proximity
  - Crime kernel density heatmaps
  - Crime incident pins
  - Greenspace overlay
- **Comparable properties** nearby
- **School ratings & proximity**
- **Mortgage estimate calculator** (using FRED mortgage rates from existing data pipeline)
- **Walk/transit score**
- **Flood zone / natural hazard risk**
- **Price history / appreciation trends**
- **Tax information**
- **Neighborhood demographics**
