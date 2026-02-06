# PricePoint Phase 1 PRD — Landing Page, Nav Bar & Design System

## Context

The PricePoint frontend is a minimal React 18 + TypeScript app with inline styles, no CSS framework, and two basic pages. This phase establishes the "Soft Minimalism" design system and builds the first user-facing experience: a landing page with address autocomplete search and a floating glassmorphism navigation bar. It also adds a backend geocoding endpoint with Valkey caching.

## Design Decisions

| Topic | Decision |
|-------|----------|
| Tailwind | **v4** — CSS-first (`@import "tailwindcss"` + `@theme`), `@tailwindcss/vite` plugin, no JS config |
| Geocoding | **Backend proxy** — FastAPI `GET /api/geocode?q=...` → Nominatim |
| Caching | **Valkey** — Docker service + `redis[hiredis]` Python dep + 24h TTL |
| Mobile | **Basic responsive** — Tailwind breakpoints, stack on small screens |
| Old code | **Delete unused** — Remove `DashboardPage.tsx`, keep MapView/PropertyCard |
| Results page | **Styled placeholder** — Address card + dynamic Leaflet map at searched coords |
| Animations | **CSS-only micro-interactions** — dropdown fade, hover effects, nav scroll, View Transitions API |
| Glassmorphism | **With `@supports` fallback** — solid bg where `backdrop-filter` unsupported |
| Fonts | **Self-hosted** Plus Jakarta Sans woff2, no Google Fonts CDN |
| Tests | **Comprehensive** — vitest-axe for a11y, full keyboard nav, race conditions, edge cases |

---

## Sprint Tasks

### [ ] PP-001: Valkey Docker Service
> Add Valkey (Redis-compatible) to the infrastructure stack.

- [x] Add `valkey` service to `docker-compose.yml` (`valkey/valkey:8-alpine`, port 6379, profile `infra`, healthcheck)
- [x] Add `valkeydata:` named volume
- [x] Add `VALKEY_URL=redis://valkey:6379/0` to `.env.example` and `.env`

**Files:** `docker-compose.yml`, `.env.example`, `.env`
**Verify:** `docker compose --profile infra config` validates without errors

---

### [ ] PP-002: Backend Valkey Integration
> Wire Valkey into the FastAPI application with graceful degradation.

- [x] Add `redis[hiredis]>=5.0,<6` to `pyproject.toml` dependencies
- [x] Run `uv sync` to update lockfile
- [x] Add `valkey_url: str | None = None` to `Settings` class in `src/pricepoint/config/settings.py`
- [x] Add async `get_valkey()` dependency to `src/pricepoint/api/dependencies.py` (reads from `app.state.valkey_pool`, yields `None` when unavailable)
- [x] Update `lifespan()` in `src/pricepoint/api/main.py` to init/close Valkey connection pool on `app.state`

**Files:** `pyproject.toml`, `src/pricepoint/config/settings.py`, `src/pricepoint/api/dependencies.py`, `src/pricepoint/api/main.py`
**Verify:** `uv run python -c "import redis; print(redis.__version__)"` succeeds; app starts without Valkey (graceful `None`)

---

### [ ] PP-003: Backend Geocode Endpoint
> New `/api/geocode` endpoint proxying to Nominatim with Valkey caching.

- [x] Create `src/pricepoint/api/schemas/geocode.py` — `GeocodeResult` (display_name, lat, lon, place_id, osm_type, osm_id, boundingbox) and `GeocodeResponse` (results, cached)
- [x] Create `src/pricepoint/api/routes/geocode.py` — `GET /geocode` with params `q: str`, `limit: int = 5`
  - Cache key: `geocode:{normalized_q}:{limit}`, TTL 24h
  - Nominatim call via `httpx.AsyncClient`: `format=json`, `countrycodes=us`, `User-Agent: PricePoint/0.1.0`, 5s timeout
  - Graceful degradation: works without Valkey, handles Nominatim errors
- [x] Register `geocode.router` at `/api` prefix in `src/pricepoint/api/main.py`

**Files:** `src/pricepoint/api/schemas/geocode.py` (new), `src/pricepoint/api/routes/geocode.py` (new), `src/pricepoint/api/main.py`
**Verify:** `make lint` passes; `curl localhost:8000/api/geocode?q=raleigh` returns JSON results

---

### [ ] PP-004: Backend Geocode Tests
> Unit tests for the geocode endpoint covering cache hits, misses, and error scenarios.

- [x] Create `tests/unit/test_api/test_geocode.py`
  - `test_geocode_returns_results` — mock httpx, verify response shape
  - `test_geocode_empty_query` — returns empty results or 422
  - `test_geocode_short_query` — `q="a"` returns empty
  - `test_geocode_passes_params_to_nominatim` — verify countrycodes, limit, format
  - `test_geocode_nominatim_timeout` — graceful 502
  - `test_geocode_caches_results` — mock Valkey, verify cache write then cache read
  - `test_geocode_works_without_valkey` — None dependency, Nominatim still called
  - `test_geocode_limit_capped` — limit > 10 gets capped
- [x] Uses existing `client` fixture from `tests/conftest.py` + `app.dependency_overrides`

**Files:** `tests/unit/test_api/test_geocode.py` (new)
**Verify:** `make test-unit` — all pass including new tests

---

### [ ] PP-005: Tailwind v4 Setup
> Install Tailwind v4 with Vite plugin, replacing the need for PostCSS config.

- [x] `npm install tailwindcss @tailwindcss/vite` (NO postcss, NO autoprefixer, NO JS config file)
- [x] Add `import tailwindcss from "@tailwindcss/vite"` and `tailwindcss()` to plugins in `frontend/vite.config.ts`
- [x] Optionally add to `frontend/vitest.config.ts` plugins

**Files:** `frontend/package.json` (auto), `frontend/vite.config.ts`, `frontend/vitest.config.ts`
**Verify:** `cd frontend && npm run build` succeeds with Tailwind processing

---

### [ ] PP-006: Design System — Fonts, Tokens & Base CSS
> Self-hosted Plus Jakarta Sans, all design tokens via `@theme`, base styles, glassmorphism class, animation keyframes, View Transitions CSS.

- [x] Download Plus Jakarta Sans woff2 files (400, 500, 600, 700) to `frontend/src/assets/fonts/`
- [x] Create `frontend/src/index.css`:
  - `@import "tailwindcss"`
  - `@font-face` declarations (font-display: swap)
  - `@theme { }` block with all tokens: colors (`--color-bg-main #F2F4F7`, `--color-bg-card #FFFFFF`, `--color-brand-blue #4F46E5`, `--color-status-*`, `--color-text-pri #1A1A1A`, `--color-text-sec #71717A`), font (`--font-sans`), sizes (`--text-display-h1 2.25rem`, `--text-heading-h2 1.25rem`, `--text-body-main 1rem`, `--text-metadata 0.75rem`), radius (`--radius-lg 32px`, `--radius-md 20px`, `--radius-pill 9999px`), shadow (`--shadow-soft`)
  - Base `body` styles
  - `.glass` class with `@supports(backdrop-filter)` fallback
  - `@keyframes dropdown-enter` (fade + slide)
  - Hover utilities (`.btn-primary`, `.link-hover`)
  - View Transitions CSS (`::view-transition-old/new(root)` 200ms ease)
- [x] Add `import "./index.css"` to `frontend/src/main.tsx` (before App import)
- [x] Update `<title>` to "PricePoint" in `frontend/index.html`

**Files:** `frontend/src/assets/fonts/*.woff2` (4 new), `frontend/src/index.css` (new), `frontend/src/main.tsx`, `frontend/index.html`
**Verify:** `npm run build` succeeds; browser shows Plus Jakarta Sans font; Network tab has no Google Fonts requests

---

### [ ] PP-007: Frontend Types & Utilities
> Add geocode types and View Transitions utility.

- [x] Add `GeocodeResult` and `GeocodeResponse` interfaces to `frontend/src/types/index.ts`
- [x] Create `frontend/src/types/view-transitions.d.ts` — type declaration for `document.startViewTransition`
- [x] Create `frontend/src/utils/viewTransition.ts` — `startViewTransition()` wrapper with progressive enhancement fallback

**Files:** `frontend/src/types/index.ts`, `frontend/src/types/view-transitions.d.ts` (new), `frontend/src/utils/viewTransition.ts` (new)
**Verify:** `npm run build` — no TypeScript errors

---

### [ ] PP-008: Geocode Service & Hooks
> Frontend API client for geocoding and debounced search hook with race-condition safety.

- [x] Create `frontend/src/services/geocode.ts` — Axios client calling `GET /api/geocode` with `q` and `limit` params (follows pattern of existing `frontend/src/services/api.ts`)
- [x] Create `frontend/src/hooks/useDebounce.ts` — generic value debounce with `setTimeout`/`clearTimeout`
- [x] Create `frontend/src/hooks/useGeocode.ts`:
  - Composes `useDebounce` (300ms) + `getGeocode` service
  - Race-condition guard via `useRef` request counter
  - Min 3 chars before searching
  - Returns `{ results, loading, error }`

**Files:** `frontend/src/services/geocode.ts` (new), `frontend/src/hooks/useDebounce.ts` (new), `frontend/src/hooks/useGeocode.ts` (new)
**Verify:** `npm run build` — no errors

---

### [ ] PP-009: SearchBar Component
> Shared autocomplete search bar with hero and compact variants, full keyboard nav, and accessibility.

- [x] Create `frontend/src/components/SearchBar/SearchBar.tsx`
  - Props: `variant: "hero" | "compact"` (default hero), `onSelect?: (result: GeocodeResult) => void`
  - Uses `useGeocode` hook for autocomplete (up to 5 results)
  - Hero variant: `max-w-2xl px-6 py-4 rounded-pill shadow-soft bg-bg-card`
  - Compact variant: `max-w-md px-4 py-2 text-sm bg-white/70`, responsive `max-w-[200px] sm:max-w-xs md:max-w-md`
  - Selection: navigates to `/results?lat=...&lon=...&address=...` using `startViewTransition()` wrapper, or calls `onSelect`
  - A11y: `role="combobox"`, `aria-expanded`, `aria-activedescendant`, `role="listbox"` + `role="option"`
  - Keyboard: ArrowUp/Down, Enter, Escape
  - States: loading spinner, "No results found", error display
  - Dropdown uses `search-dropdown` CSS class for animation

**Files:** `frontend/src/components/SearchBar/SearchBar.tsx` (new)
**Verify:** Renders in isolation; typing shows autocomplete; keyboard nav works; screen reader announces correctly

---

### [ ] PP-010: NavBar Component
> Floating glassmorphism navigation bar with scroll-based opacity change.

- [x] Create `frontend/src/components/NavBar/NavBar.tsx`
  - Fixed floating pill: `glass fixed top-4 left-1/2 -translate-x-1/2 z-50 rounded-pill shadow-soft`
  - Left: "PricePoint" `<Link to="/">` with hover transition
  - Right: `<SearchBar variant="compact" />`
  - `useEffect` scroll listener: `scrolled` state increases opacity (`bg-white/80`) and adds `shadow-soft` vs `bg-white/50 shadow-none`
  - `aria-label="Main navigation"`
  - Responsive: `gap-2 sm:gap-4`, `px-3 sm:px-6`

**Files:** `frontend/src/components/NavBar/NavBar.tsx` (new)
**Verify:** Nav bar floats, blur works, opacity changes on scroll, compact search functional

---

### [ ] PP-011: Landing Page
> Google-style minimal landing page with centered branding and hero search.

- [x] Create `frontend/src/pages/LandingPage.tsx`
  - `min-h-screen flex flex-col items-center justify-center px-4`
  - "PricePoint" heading: `text-2xl sm:text-display-h1 font-bold tracking-tight`
  - Subtitle: "Residential home value forecasting" (`text-text-sec`)
  - `<SearchBar variant="hero" />`
  - No NavBar (handled by AppLayout conditional)

**Files:** `frontend/src/pages/LandingPage.tsx` (new)
**Verify:** `/` shows centered heading + subtitle + large search bar; no nav bar visible

---

### [ ] PP-012: Results Page Placeholder
> Styled placeholder with address card and dynamic map.

- [x] Create `frontend/src/pages/ResultsPage.tsx`
  - Reads `address`, `lat`, `lon` from `useSearchParams()`
  - Address card: `bg-bg-card rounded-md shadow-soft p-6` with heading + "More details coming soon"
  - Dynamic map: `<MapView center={[lat, lon]} zoom={15} />` (existing component)
  - Graceful fallback when no coordinates
  - Responsive: `max-w-4xl mx-auto px-4 py-8`

**Files:** `frontend/src/pages/ResultsPage.tsx` (new)
**Verify:** Navigating from search shows address + map centered on location

---

### [ ] PP-013: Routing & Layout Rewrite
> Update routing to use new pages, rewrite AppLayout with Tailwind, add View Transitions.

- [x] Rewrite `frontend/src/components/Layout/AppLayout.tsx`:
  - Replace all inline styles with Tailwind classes
  - `useLocation()` to detect `/` — hide NavBar, skip padding on landing page
  - Non-landing: render `<NavBar />` + `pt-24` on main content
- [x] Rewrite `frontend/src/App.tsx`:
  - `/` → `LandingPage`
  - `/results` → `ResultsPage`
  - `/forecast` → `ForecastPage` (unchanged)
  - `/dashboard` → `<Navigate to="/" replace />`
  - `*` → `<Navigate to="/" replace />`
  - Remove `DashboardPage` import

**Files:** `frontend/src/components/Layout/AppLayout.tsx`, `frontend/src/App.tsx`
**Verify:** All routes work; NavBar hidden on `/`, visible elsewhere; `/dashboard` redirects; `/forecast` unchanged

---

### [ ] PP-014: Cleanup — Delete Unused Code
> Remove unreachable DashboardPage.

- [x] Delete `frontend/src/pages/DashboardPage.tsx`
- [x] Verify no remaining imports (`grep -r "DashboardPage" frontend/src/`)
- [x] Keep: MapView, PropertyCard, ForecastPage, all existing tests

**Files:** `frontend/src/pages/DashboardPage.tsx` (delete)
**Verify:** `npm run build` — no broken imports; `npm test` — existing tests still pass

---

### [ ] PP-015: Frontend Tests
> Comprehensive test suite with vitest-axe accessibility checks for all new code.

- [x] `npm install -D vitest-axe`
- [x] Update `frontend/src/test/setup.ts` — add `import "vitest-axe/extend-expect"`
- [x] Create `frontend/src/hooks/__tests__/useDebounce.test.ts` — timer behavior, reset on change, custom delay
- [x] Create `frontend/src/hooks/__tests__/useGeocode.test.ts` — debounce integration, race conditions, error state, min 3 chars, loading state
- [x] Create `frontend/src/services/__tests__/geocode.test.ts` — axios mock, param verification, default/custom limit
- [x] Create `frontend/src/components/SearchBar/__tests__/SearchBar.test.tsx` — both variants, autocomplete flow, keyboard nav (ArrowUp/Down/Enter/Escape), onSelect callback, default navigation, loading/empty/error states, a11y roles (combobox/listbox/option), vitest-axe no violations
- [x] Create `frontend/src/pages/__tests__/LandingPage.test.tsx` — heading, subtitle, hero SearchBar, axe check
- [x] Create `frontend/src/components/NavBar/__tests__/NavBar.test.tsx` — home link href, compact SearchBar, nav landmark, axe check
- [x] Create `frontend/src/pages/__tests__/ResultsPage.test.tsx` — URL param display, dynamic map render, missing params fallback, axe check (uses `MemoryRouter` with `initialEntries`)

**Files:** `frontend/src/test/setup.ts`, 7 new test files
**Verify:** `npm test` — all tests pass (existing + new); no accessibility violations

---

### [ ] PP-016: Final Verification & Lint
> End-to-end verification of the entire phase.

- [x] `cd frontend && npm run build` — no TypeScript or build errors
- [x] `cd frontend && npm run lint && npm run format:check` — ESLint + Prettier pass
- [x] `cd frontend && npm test` — all tests pass
- [x] `make lint` — Ruff passes on backend
- [x] `make test-unit` — backend unit tests pass
- [x] `uv run mypy src/pricepoint/` — no type errors
- [x] Manual: `/` shows centered "PricePoint" + hero search, no nav
- [x] Manual: Type address → autocomplete via backend → select → `/results` with page cross-fade
- [x] Manual: Results page has styled card + dynamic map + glassmorphism nav bar
- [x] Manual: Nav scroll increases opacity/shadow
- [x] Manual: `/forecast` still works; `/dashboard` redirects to `/`
- [x] Manual: Mobile (375px width) — nav and search usable
- [x] Manual: Network tab — no Google Fonts requests

---

## Dependency Graph

```
PP-001 → PP-002 → PP-003 → PP-004
PP-005 → PP-006 → PP-007 → PP-008 → PP-009 → PP-010
                                          ↓
                                       PP-011
                                       PP-012
                                          ↓
                                       PP-013 → PP-014 → PP-015 → PP-016
```

Backend (PP-001–004) and frontend foundation (PP-005–006) can proceed in parallel.
