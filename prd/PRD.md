# PRD: Phase 2 — Property Results Page

## Context

Phase 1 established the landing page, design system, geocoding search, and a minimal results page showing a predicted value + map marker. Phase 2 builds the **core product page** — a comprehensive property details view that gives users everything they need to evaluate a home purchase: valuation comparison, neighborhood data, school quality, climate risks, financial tools, and interactive map overlays.

The frontend is the primary deliverable. All backend endpoints are **stubbed with realistic mock data** so the UI can be fully developed and tested end-to-end without real data pipelines.

---

## 1. Page Layout & Sections

The results page (`/results?address=...&lat=...&lon=...`) is a single scrollable page with all sections visible. A **sticky icon sidebar** on desktop (hidden on mobile) enables quick section navigation.

### 1.1 Section Navigation Sidebar
- **Desktop only**: thin left sidebar with icon buttons, each linking to a section anchor
- **Icons + tooltips**: house, dollar, book, list, chart, cloud, calculator, map icons — tooltip text shown on hover
- **Scroll-aware**: active icon highlights based on current scroll position
- **Mobile**: hidden — users scroll naturally

### 1.2 Property Header (Compact)
- Small thumbnail image (or placeholder icon if no image) — not a hero layout
- Full address as page title, city/state/zip below
- Key stats row: bedrooms, bathrooms, sqft, lot size, year built, property type
- Focus on data density over visual impact (images are placeholder stubs for now)

### 1.3 Value Comparison
- **Listed price** (or last sold price if not currently listed) — label indicates which
- **Predicted value** from ML model, with confidence interval range
- **Both badge + bar**: horizontal bar chart comparing listed vs predicted values side-by-side, with a colored pill badge summarizing the delta (e.g., "$12K below listed" in green, "$8K above listed" in red)
- Model version + prediction date metadata (small text)

### 1.4 Property Description
- **Highlights**: 3-5 bullet-point selling features (e.g., "Updated kitchen", "Hardwood floors throughout")
- **Full text**: complete paragraph description below the highlights

### 1.5 School Data
- Text list only (no inline map)
- Each entry: school name, type (Elementary/Middle/High), **numeric badge** (colored circle with rating number: green 7-10, yellow 4-6, red 1-3), distance in miles, drive time, walk time (if walkable)

### 1.6 Detailed Property Info
- **All sections expanded by default** (no collapsing)
- Three sub-sections:
  - **Interior**: flooring, appliances, heating, cooling, fireplace, basement
  - **Exterior**: roof, siding, foundation, parking, pool, fence
  - **Financial**: HOA monthly, annual tax, tax year, assessed value

### 1.7 Sale & Tax History Chart
- Recharts combined chart: sale prices (line with dots) + tax assessments (area fill) over time
- **20-year range** of stub data (2005-2025): ~4-5 sale events + 20 tax assessment entries
- Tooltip with date + dollar values on hover
- Currency-formatted Y-axis

### 1.8 Climate Risks
- **Score only**: flood and fire risk labels (Minimal/Low/Moderate/High/Severe) with colored score bar (1-10)
- Color-coded by severity (green → yellow → red)
- Compact — no explanatory text

### 1.9 Mortgage Payment Calculator
- **Sliders + synced text inputs** for: home price (pre-filled from listed/predicted), down payment %, interest rate, loan term
- Pre-filled from property data: annual tax, HOA
- **Real-time updates**: donut chart and numbers update instantly as sliders move (no debouncing — useMemo keeps computation cheap)
- Donut chart showing monthly breakdown: principal, interest, tax, insurance, HOA
- Total monthly payment prominently displayed
- **Gear icon** linking to `/settings` to configure default slider values
- Default values for interest rate, down payment %, insurance are loaded from user's saved settings (localStorage)

### 1.10 Interactive Map with Tab Overlays
- Map centered on property with a **distinct home icon** pin (house-shaped, visually different from data overlay pins)
- Tab bar above the map switches between 5 data views
- Metrics panel **below the map**, content changes per active tab
- **Error handling per tab**: if an overlay endpoint fails, show an error message with a retry button within the map area for that tab
- Map layers are lazy-loaded (fetched on first tab activation) and cached in component state

| Tab | Overlay | Metrics Below Map |
|-----|---------|-------------------|
| **Crime Density** | Kernel density heatmap (**standard blue-to-red gradient**) | Total incidents in 1-mi radius, crime rate per 1K people, z-score vs sample mean, trend |
| **Crime Incidents** | Individual pins with popups (date, type, description) | Same metrics as density tab |
| **Points of Interest** | **Color-coded pins per category** (e.g., blue=grocery, green=retail, red=pharmacy, etc.) with popups showing name, distance, drive time. Gear icon linking to /settings for POI preferences | Category breakdown, nearest of each type |
| **Greenspace** | Green pins for parks/trails with acreage in popup | Parks within 1 mi, nearest park distance, green acres in 1 mi, z-score |
| **Utilities** | Gray pins for nuisance infrastructure (railroads, powerlines, highways) | Nearest highway/railroad/powerline distances, nuisance score (1-10) |

### 1.11 Loading State
- **Skeleton screens**: gray placeholder blocks mimicking the page layout (skeleton cards for each section) while property data loads
- Map overlay tabs show individual loading spinners when their data is being fetched

### 1.12 Re-search Behavior
- When searching for a new address from the NavBar, use a **full page transition** (existing view transition pattern). Fresh page load — no in-place update complexity.

---

## 2. Settings Page (`/settings`)

A unified settings page with two sections, accessible from the **NavBar** (settings icon) and from gear icons within the results page (on POI tab and mortgage calculator).

### 2.1 POI Preferences
- **Default POI list**: pre-populated by category (Grocery: Costco, Trader Joe's, Whole Foods, Publix; Retail: Target, Walmart; Pharmacy: CVS, Walgreens; etc.)
- **Toggle POIs**: enable/disable individual POIs or entire categories
- **Add custom POIs**: user can add a POI by name and category
- **Remove custom POIs**: delete user-added entries (defaults can only be toggled off)
- **Persistence**: localStorage

### 2.2 Mortgage Defaults
- Configurable default values for: down payment %, interest rate, loan term (years), annual home insurance
- These values pre-fill the mortgage calculator on every property page
- **Persistence**: localStorage

### 2.3 Implementation
- **Route**: `/settings` added to `App.tsx`
- **Page**: `src/pages/SettingsPage.tsx` — two sections, no tabs needed
- **Hook**: `src/hooks/usePoiPreferences.ts` — localStorage CRUD for POI preferences
- **Hook**: `src/hooks/useMortgageDefaults.ts` — localStorage read/write for mortgage defaults
- **NavBar**: add settings gear icon to NavBar component
- **Integration**: PropertyMap's POI layer reads from `usePoiPreferences` to filter; MortgageCalculator reads from `useMortgageDefaults` for initial values

---

## 3. Backend API Endpoints (All Stubbed)

All endpoints return hardcoded realistic data for a Cary, NC area property. The `address` param is echoed back in the response.

### 3.1 GET `/api/property`

**Params**: `lat: float`, `lon: float`, `address: str`

**Response** (`PropertyResponse`):
```
{
  property: { address, city, state, zip_code, lat, lon, bedrooms, bathrooms, sqft,
              lot_size_sqft, year_built, property_type, stories, garage_spaces,
              description, highlights: string[],
              images: [{ url, alt, is_primary }] },
  valuation: { listed_price?, last_sold_price?, last_sold_date?, predicted_value,
               confidence_interval_low, confidence_interval_high, model_version,
               prediction_date },
  interior:  { flooring[], appliances[], heating, cooling, fireplace, basement? },
  exterior:  { roof, siding, foundation, parking, pool, fence },
  financial: { hoa_monthly?, tax_annual, tax_year, assessed_value },
  schools:   [{ name, school_type, rating, distance_miles, drive_minutes, walk_minutes? }],
  sale_history: [{ date, price, event_type }],   // 20 years of data
  tax_history:  [{ year, assessed_value, tax_amount }],  // 20 years of data
  climate_risk: { flood_risk, flood_score, fire_risk, fire_score }
}
```

**Files**: `api/schemas/property.py`, `api/routes/property.py`

### 3.2 GET `/api/crime`

**Params**: `lat: float`, `lon: float`, `radius_miles: float = 1.0`

**Response** (`CrimeResponse`):
```
{
  heatmap:   [{ lat, lon, intensity }],       // ~80 points
  incidents: [{ id, incident_type, category, date, lat, lon, description? }],  // ~25 incidents
  metrics:   { total_incidents_1mi, incidents_per_1000_people, crime_z_score, trend }
}
```

**Files**: `api/schemas/crime.py`, `api/routes/crime.py`

### 3.3 GET `/api/pois`

**Params**: `lat: float`, `lon: float`, `radius_miles: float = 3.0`

**Response** (`PoisResponse`):
```
{
  pois: [{ id, name, category, lat, lon, distance_miles, drive_minutes }]  // ~15 POIs
}
```

**Files**: `api/schemas/pois.py`, `api/routes/pois.py`

### 3.4 GET `/api/greenspace`

**Params**: `lat: float`, `lon: float`, `radius_miles: float = 2.0`

**Response** (`GreenspaceResponse`):
```
{
  features: [{ id, name, feature_type, lat, lon, distance_miles, acreage? }],
  metrics:  { parks_within_1mi, nearest_park_miles, total_green_acres_1mi, greenspace_z_score }
}
```

**Files**: `api/schemas/greenspace.py`, `api/routes/greenspace.py`

### 3.5 GET `/api/utilities`

**Params**: `lat: float`, `lon: float`, `radius_miles: float = 1.0`

**Response** (`UtilitiesResponse`):
```
{
  features: [{ id, name, feature_type, lat, lon, distance_miles }],
  metrics:  { nearest_highway_miles, nearest_railroad_miles, nearest_powerline_miles, nuisance_score }
}
```

**Files**: `api/schemas/utilities.py`, `api/routes/utilities.py`

**Registration**: All 5 routers added to `src/pricepoint/api/main.py` with `/api` prefix.

---

## 4. Frontend Architecture

### 4.1 New Components

```
src/components/
  SectionSidebar/SectionSidebar.tsx          — Sticky icon sidebar (desktop nav)
  PropertyHeader/PropertyHeader.tsx          — Compact: thumbnail + address + stats
  ValueSection/ValueSection.tsx              — Listed vs predicted: badge + bar chart
  PropertyDescription/PropertyDescription.tsx — Highlights bullets + full text
  SchoolsSection/SchoolsSection.tsx          — School list with numeric rating badges
  PropertyDetailsSection/PropertyDetailsSection.tsx — Interior/exterior/financial (all expanded)
  SaleTaxHistoryChart/SaleTaxHistoryChart.tsx — Recharts 20-year combined chart
  ClimateRiskSection/ClimateRiskSection.tsx   — Score-only flood/fire indicators
  MortgageCalculator/MortgageCalculator.tsx   — Sliders + text inputs + real-time donut chart
  SkeletonResultsPage/SkeletonResultsPage.tsx — Skeleton loading state
  PropertyMap/PropertyMap.tsx                — Map container + tab management + error states
  PropertyMap/MapTabBar.tsx                  — Tab bar for map overlays
  PropertyMap/layers/CrimeHeatmapLayer.tsx   — leaflet.heat (blue-to-red gradient)
  PropertyMap/layers/CrimeIncidentsLayer.tsx — Incident marker pins
  PropertyMap/layers/PoisLayer.tsx           — Color-coded POI pins per category
  PropertyMap/layers/GreenspaceLayer.tsx     — Green park/trail pins
  PropertyMap/layers/UtilitiesLayer.tsx      — Gray infrastructure pins
```

Each component has a `__tests__/` directory with vitest + React Testing Library + vitest-axe tests.

### 4.2 New Services & Hooks

```
src/services/property.ts          — getProperty, getCrime, getPois, getGreenspace, getUtilities
src/hooks/usePropertyData.ts      — Wraps useApi(getProperty), auto-fetches on lat/lon/address
src/hooks/useMortgageCalculator.ts — Pure computation (amortization formula), real-time via useMemo
src/hooks/useMortgageDefaults.ts  — localStorage read/write for mortgage default values
src/hooks/usePoiPreferences.ts    — localStorage CRUD for POI preferences + default list
src/hooks/useActiveSection.ts     — IntersectionObserver to track which section is in view (for sidebar)
```

### 4.3 New Types

All added to `src/types/index.ts`:
- `PropertyResponse` (with nested: `PropertyDetails`, `ValuationData`, `InteriorFeatures`, `ExteriorFeatures`, `FinancialDetails`, `SchoolNearby`, `SaleHistoryEntry`, `TaxHistoryEntry`, `ClimateRisk`)
- `CrimeResponse`, `CrimeHeatmapPoint`, `CrimeIncident`, `CrimeMetrics`
- `PoisResponse`, `PointOfInterest`
- `GreenspaceResponse`, `GreenspaceFeature`, `GreenspaceMetrics`
- `UtilitiesResponse`, `UtilityFeature`, `UtilitiesMetrics`
- `MapTab`
- `MortgageInputs`, `MortgageBreakdown`
- `PoiPreference`
- `MortgageDefaults`

### 4.4 New Dependencies

| Package | Purpose |
|---------|---------|
| `recharts` | Sale/tax history chart + mortgage donut chart |
| `leaflet.heat` | Crime density heatmap layer |
| `react-leaflet-cluster` | Marker clustering for incident/POI pins |

Plus a custom `src/types/leaflet-heat.d.ts` type declaration.

### 4.5 State Management

No Redux or Context needed. Data flows:
- `ResultsPage` fetches property data via `usePropertyData` hook, passes down as props
- Each map layer fetches its own data via `useApi` on first tab activation (lazy)
- `MortgageCalculator` manages local input state + reads defaults from `useMortgageDefaults` + computes via `useMortgageCalculator`
- POI layer reads from `usePoiPreferences` to filter displayed pins
- `SectionSidebar` uses `useActiveSection` (IntersectionObserver) for scroll-aware highlighting

### 4.6 Routing Changes

| Route | Component | Notes |
|-------|-----------|-------|
| `/results` | `ResultsPage` | **Rewritten** — same URL params, new data source (`getProperty` instead of `postForecast`) |
| `/settings` | `SettingsPage` | **New** — POI preferences + mortgage defaults |

Existing routes (`/`, `/forecast`) unchanged. NavBar gets a settings gear icon.

---

## 5. Implementation Order

### Phase A: Data Contracts
1. Create all 5 Pydantic schema files (`api/schemas/property.py`, `crime.py`, `pois.py`, `greenspace.py`, `utilities.py`)
2. Create all 5 route files with stub data (`api/routes/property.py`, etc.)
3. Register routes in `api/main.py`
4. Backend unit tests for all 5 endpoints
5. Add all TypeScript types to `frontend/src/types/index.ts`
6. Create `frontend/src/services/property.ts` with 5 API functions
7. Create `usePropertyData` and `useMortgageCalculator` hooks + tests

### Phase B: Map Infrastructure + Dependencies
1. Install npm dependencies (`recharts`, `leaflet.heat`, `react-leaflet-cluster`)
2. Create `leaflet-heat.d.ts` type declaration
3. Build `PropertyMap` + `MapTabBar` components (with error state per tab + retry)
4. Build all 5 map layer components (heatmap: blue-to-red; POIs: color-per-category; property: home icon)
5. Map component tests

### Phase C: Section Components (parallelizable)
1. `PropertyHeader` (compact layout, thumbnail) + tests
2. `ValueSection` (badge + bar comparison) + tests
3. `PropertyDescription` (highlights + full text) + tests
4. `SchoolsSection` (numeric rating badges) + tests
5. `PropertyDetailsSection` (all expanded) + tests
6. `SaleTaxHistoryChart` (20-year Recharts chart) + tests
7. `ClimateRiskSection` (score-only bars) + tests
8. `MortgageCalculator` (sliders + real-time donut) + tests
9. `SkeletonResultsPage` (skeleton loading state) + tests
10. `SectionSidebar` (sticky icons + tooltips + IntersectionObserver) + tests

### Phase D: Settings Page
1. Create `usePoiPreferences` hook (localStorage + defaults) + tests
2. Create `useMortgageDefaults` hook (localStorage + defaults) + tests
3. Build `SettingsPage` (POI section + mortgage section) + tests
4. Add `/settings` route to `App.tsx`
5. Add settings gear icon to `NavBar`
6. Wire `PoisLayer` to read from `usePoiPreferences` for filtering
7. Wire `MortgageCalculator` to read from `useMortgageDefaults` for initial values

### Phase E: Page Assembly & Verification
1. Rewrite `ResultsPage` to compose all section components + sidebar + skeleton loading
2. Update `ResultsPage` tests
3. Full test suite pass (`npx vitest run`, `make test`)
4. Lint clean (`make frontend-lint`, `make lint`)
5. Build succeeds (`npm run build`)

---

## 6. Key Files to Modify

| File | Change |
|------|--------|
| `src/pricepoint/api/main.py` | Register 5 new routers |
| `frontend/src/types/index.ts` | Add all new TypeScript interfaces |
| `frontend/src/pages/ResultsPage.tsx` | Complete rewrite as section orchestrator |
| `frontend/src/App.tsx` | Add `/settings` route, lazy-load `SettingsPage` |
| `frontend/src/components/NavBar/NavBar.tsx` | Add settings gear icon |
| `frontend/package.json` | Add `recharts`, `leaflet.heat`, `react-leaflet-cluster` |

**Existing code to reuse**:
- `src/hooks/useApi.ts` — generic API fetch hook (all new service calls use this)
- `src/hooks/useDebounce.ts` — if needed for any input debouncing
- `src/utils/viewTransition.ts` — for page transitions
- `src/services/api.ts` — axios client pattern to follow for `property.ts`
- Design system tokens in `src/index.css` — all new components use existing tokens

---

## 7. Out of Scope (Future Phases)

- Real backend data integration (all endpoints return stubs)
- Property image fetching from real sources (placeholder URLs)
- User accounts / auth / saved properties
- Mobile-native optimizations beyond responsive Tailwind
- Print/export views
- Additional map tabs (e.g., schools on map)

---

## 8. Verification Plan

### Backend
- `make test` — pytest passes for all new endpoint unit tests
- `make lint` — ruff check + format check passes

### Frontend
- `cd frontend && npx vitest run` — all component + hook + page tests pass
- `make frontend-lint` — ESLint + Prettier clean
- `cd frontend && npm run build` — TypeScript + production build succeeds
- Manual: `npm run dev` → navigate to `/results?address=123+Main+St&lat=35.73&lon=-78.78` → verify:
  - Skeleton loading appears then sections populate
  - All 9 sections render with stub data
  - Map tabs switch, heatmap renders, POI pins are color-coded
  - Mortgage sliders update donut chart in real-time
  - Sticky sidebar highlights correct section on scroll
  - `/settings` page loads, POI toggles and mortgage defaults persist in localStorage
  - Settings gear icon visible in NavBar

### Accessibility
- vitest-axe assertions in every component test
- Keyboard navigation: map tabs, calculator inputs, settings toggles
- ARIA labels on all interactive elements
- Tooltips on sidebar icons

---

## 9. Design Guidelines

All components follow the Phase 1 design system:
- **Cards**: `rounded-lg bg-bg-card/80 shadow-soft backdrop-blur-md p-5 sm:p-8`
- **Headings**: `text-text-pri font-bold`
- **Secondary text**: `text-text-sec font-medium`
- **Accent color**: `text-brand-blue` / `bg-brand-blue`
- **Positive indicators**: `text-status-maint` (#47d1a0 green)
- **Negative indicators**: `text-status-rented` (#ff5c8e pink)
- **Spacing**: `gap-grid` (24px) between sections
- **Responsive**: mobile-first, `sm:` breakpoint for desktop
- **Font**: Plus Jakarta Sans (400/500/600/700)
- **Map heatmap**: standard blue → yellow → red gradient
- **POI pin colors**: distinct per category (grocery=blue, retail=green, pharmacy=red, etc.)
- **Property pin**: distinct home icon, visually different from data pins
- **School ratings**: colored numeric badge (green 7-10, yellow 4-6, red 1-3)
