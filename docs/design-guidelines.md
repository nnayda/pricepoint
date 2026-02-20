# Design Guidelines
## Property Intelligence Dashboard

**Version 1.0** · Last Updated: February 2026

---

## 1. Vision & Design Philosophy

This application is a high-density data dashboard where users make one of the most significant financial decisions of their lives. The design must balance information richness with visual calm — every pixel should earn its place without overwhelming the user.

**Core Principles:**

- **Intentional minimalism** — reduce noise so signal is clear. Every UI element must justify its presence.
- **Fatigue-aware design** — users will spend extended sessions on this page. Color, contrast, and spacing choices must reduce cognitive and eye strain.
- **Trustworthy & precise** — the product deals with real estate data, crime statistics, and financial analysis. The UI should convey reliability, not playfulness.
- **Fluid interactivity** — transitions and micro-interactions should feel smooth and considered, never jarring.
- **Hierarchy at every level** — from page layout to individual cards, information should be effortlessly scannable.

---

## 2. Color System

### 2.1 Dark Mode (Default)

Dark mode is the primary experience. Backgrounds use near-black with subtle blue-gray undertones (not pure black, which creates harsh contrast).

| Token | Hex | Usage |
|---|---|---|
| `bg-base` | `#0F1117` | App root background |
| `bg-surface` | `#161B27` | Cards, panels, sidebars |
| `bg-elevated` | `#1C2333` | Modals, dropdowns, popovers |
| `bg-subtle` | `#222840` | Hover states, selected rows |
| `bg-muted` | `#2A3050` | Dividers, inactive tabs |
| `border-default` | `#2E3553` | Card borders, input borders |
| `border-subtle` | `#222840` | Internal section dividers |

**Text:**

| Token | Hex | Usage |
|---|---|---|
| `text-primary` | `#E8ECF4` | Headings, primary content |
| `text-secondary` | `#9BA3BF` | Labels, metadata, supporting copy |
| `text-tertiary` | `#5C6480` | Placeholders, disabled states |
| `text-inverse` | `#0F1117` | Text on light accent backgrounds |

### 2.2 Light Mode

Light mode uses warm off-whites rather than pure white to avoid harsh glare.

| Token | Hex | Usage |
|---|---|---|
| `bg-base` | `#F5F6FA` | App root background |
| `bg-surface` | `#FFFFFF` | Cards, panels |
| `bg-elevated` | `#FFFFFF` | Modals, dropdowns |
| `bg-subtle` | `#EEF0F7` | Hover states, selected rows |
| `bg-muted` | `#E4E7F1` | Dividers, inactive tabs |
| `border-default` | `#D4D8E8` | Card borders, input borders |
| `border-subtle` | `#EAECF5` | Internal section dividers |

**Text:**

| Token | Hex | Usage |
|---|---|---|
| `text-primary` | `#111827` | Headings, primary content |
| `text-secondary` | `#4B5575` | Labels, metadata |
| `text-tertiary` | `#9BA3BF` | Placeholders, disabled states |

### 2.3 Brand & Accent Colors

Accent colors are used sparingly — for calls to action, active states, and key data callouts. They must read clearly on both dark and light surfaces.

| Token | Hex | Usage |
|---|---|---|
| `accent-primary` | `#5B7FFF` | Primary CTA buttons, active nav, links |
| `accent-primary-hover` | `#7395FF` | Hover state of primary accent |
| `accent-primary-subtle` | `#1E2D6B` (dark) / `#EEF1FF` (light) | Accent background tints |
| `accent-secondary` | `#8B5CF6` | Secondary highlights, badges |

### 2.4 Semantic / Data Colors

Used consistently across charts, maps, and data callouts. These must be distinguishable for common forms of color blindness — prefer shapes/icons as a secondary encoding layer.

| Token | Hex | Meaning |
|---|---|---|
| `semantic-success` | `#34D399` | Positive indicators (price drop, safe area) |
| `semantic-warning` | `#FBBF24` | Moderate concern (medium crime rate) |
| `semantic-danger` | `#F87171` | High concern (high crime, price increase) |
| `semantic-info` | `#60A5FA` | Neutral informational callouts |
| `semantic-neutral` | `#9BA3BF` | No data / unknown |

**Crime Heat Scale** (map overlays):

```
Low  ────────────────────────── High
#34D399  →  #FBBF24  →  #FB923C  →  #F87171
```

---

## 3. Typography

### 3.1 Type Scale

**Primary Font:** [Inter](https://fonts.google.com/specimen/Inter) — clean, highly legible at small sizes, excellent numerics.  
**Monospace Font:** [JetBrains Mono](https://fonts.google.com/specimen/JetBrains+Mono) — for price figures, coordinates, IDs, and data values where alignment matters.

| Scale | Size | Weight | Line Height | Usage |
|---|---|---|---|---|
| `display` | 28px | 600 | 1.2 | Page titles, hero values |
| `heading-lg` | 20px | 600 | 1.3 | Section headings |
| `heading-md` | 16px | 600 | 1.35 | Card titles |
| `heading-sm` | 14px | 600 | 1.4 | Sub-section labels |
| `body-lg` | 16px | 400 | 1.6 | Primary body content |
| `body-md` | 14px | 400 | 1.6 | Default body, card content |
| `body-sm` | 13px | 400 | 1.55 | Supporting text, captions |
| `label` | 12px | 500 | 1.4 | Data labels, badge text, table headers |
| `micro` | 11px | 400 | 1.4 | Timestamps, fine print |
| `mono-lg` | 18px | 500 | 1.3 | Price display, key metrics |
| `mono-md` | 14px | 400 | 1.5 | Table data values, coordinates |

### 3.2 Typography Rules

- Never go below 11px for any rendered text.
- Use letter-spacing of `0.01em` to `0.03em` on labels and uppercase text to improve readability.
- All-caps should be limited to category labels and table headers — use `font-size: 11px; letter-spacing: 0.06em; font-weight: 600`.
- Price and key numeric values should always use the monospace font family for alignment and clarity.
- Limit line length to 65–80 characters for any paragraph-length content.

---

## 4. Spacing & Layout

### 4.1 Spacing Scale

Use a base-4 spacing system. All spacing values are multiples of 4px.

| Token | Value | Usage |
|---|---|---|
| `space-1` | 4px | Micro gaps, icon padding |
| `space-2` | 8px | Tight internal padding |
| `space-3` | 12px | Component internal padding |
| `space-4` | 16px | Default component padding |
| `space-5` | 20px | Card padding |
| `space-6` | 24px | Section gaps |
| `space-8` | 32px | Large section separation |
| `space-10` | 40px | Page-level section gaps |
| `space-12` | 48px | Hero/display-level spacing |

### 4.2 Grid System

The dashboard uses a 12-column grid with responsive breakpoints.

| Breakpoint | Columns | Gutter | Margin |
|---|---|---|---|
| Mobile (<768px) | 4 | 16px | 16px |
| Tablet (768–1280px) | 8 | 20px | 24px |
| Desktop (1280–1600px) | 12 | 24px | 32px |
| Wide (>1600px) | 12 | 24px | 48px |

### 4.3 Page Layout

```
┌─────────────────────────────────────────────────────┐
│  Top Navigation Bar (64px)                          │
├──────────────┬──────────────────────────────────────┤
│              │                                       │
│  Left Sidebar│   Main Content Area                  │
│  (280px)     │   (fluid)                            │
│              │                                       │
│  Listing     │  ┌──────────┐  ┌──────────────────┐  │
│  List /      │  │ Map View │  │ Analysis Panel   │  │
│  Filters     │  │          │  │                  │  │
│              │  └──────────┘  └──────────────────┘  │
│              │  ┌─────────────────────────────────┐  │
│              │  │ Data Cards Row                  │  │
│              │  └─────────────────────────────────┘  │
└──────────────┴──────────────────────────────────────┘
```

The left sidebar should be collapsible to a 64px icon rail to maximize content space during deep analysis sessions.

---

## 5. Component Library

### 5.1 Cards

Cards are the primary container unit for all dashboard content.

**Base Card:**
- Background: `bg-surface`
- Border: `1px solid border-default`
- Border-radius: `12px`
- Padding: `space-5` (20px)
- Box-shadow (dark): `0 1px 3px rgba(0,0,0,0.3), 0 0 0 1px rgba(255,255,255,0.04)`
- Box-shadow (light): `0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)`

**Stat Card (for key metrics like price, crime score, walk score):**
- Same base styles + larger metric value using `mono-lg` scale
- Subtle left border accent (`3px solid accent-primary`) for active/highlighted stats
- Micro-label above the value in `label` scale, `text-tertiary`

**Listing Card (in sidebar list):**
- Compact variant: 72px height, image thumbnail on left, key data on right
- Selected state: `bg-subtle` background, `accent-primary` left border
- Hover: `bg-subtle` background with smooth transition

### 5.2 Buttons

| Variant | Background | Text | Border | Usage |
|---|---|---|---|---|
| Primary | `accent-primary` | White | None | Main CTA (Save Listing, Start Analysis) |
| Secondary | `bg-elevated` | `text-primary` | `border-default` | Secondary actions |
| Ghost | Transparent | `text-secondary` | None | Tertiary actions, icon buttons |
| Danger | `semantic-danger` at 15% opacity | `semantic-danger` | `semantic-danger` at 30% | Destructive actions |

**Sizes:**
- Large: `height: 40px`, `padding: 0 20px`, `font-size: 14px`, `border-radius: 8px`
- Default: `height: 34px`, `padding: 0 16px`, `font-size: 13px`, `border-radius: 7px`
- Small: `height: 28px`, `padding: 0 12px`, `font-size: 12px`, `border-radius: 6px`

All buttons use `font-weight: 500` and `transition: all 120ms ease`.

### 5.3 Form Elements

**Inputs & Selects:**
- Height: 36px
- Background: `bg-elevated`
- Border: `1px solid border-default`
- Border-radius: 8px
- Padding: `0 12px`
- Focus ring: `2px solid accent-primary` with `box-shadow: 0 0 0 4px accent-primary-subtle`
- Placeholder text: `text-tertiary`

**Range Sliders (for price range, crime filters):**
- Track: `bg-muted`, height 4px, border-radius 99px
- Fill: `accent-primary`
- Thumb: 16px circle, `bg-surface`, border `2px solid accent-primary`

**Toggle / Switch:**
- Off: `bg-muted`
- On: `accent-primary`
- Knob: white circle, with spring-like transition

### 5.4 Badges & Tags

Small inline indicators for property tags, crime categories, zone types, etc.

- Border-radius: 99px (fully rounded)
- Padding: `2px 8px`
- Font: `label` scale
- Variants use the semantic color palette at 15% background opacity with corresponding text color at full opacity

### 5.5 Navigation

**Top Bar (64px):**
- Background: `bg-surface` with `border-bottom: 1px solid border-subtle`
- Subtle backdrop blur: `backdrop-filter: blur(12px)` with semi-transparent background for a frosted-glass effect
- Contains: Logo/wordmark, global search, mode toggle (dark/light), user menu

**Left Sidebar:**
- Background: `bg-base`
- `border-right: 1px solid border-subtle`
- Active nav item: `bg-subtle` background, `accent-primary` left indicator bar (2px)
- Nav icons: 20px, `text-tertiary` default, `text-primary` on active/hover

### 5.6 Data Tables

Used for listing comparisons and detailed data views.

- Header row: `bg-subtle`, `label` typography, `text-tertiary`, `letter-spacing: 0.04em`
- Body rows: alternating `bg-surface` / `bg-base` for stripe (or borderless with `border-bottom: 1px solid border-subtle`)
- Row hover: `bg-subtle`
- Numeric columns: right-aligned, `mono-md` font
- Text columns: left-aligned, `body-md` font
- Sticky header on scroll

### 5.7 Tooltips & Popovers

- Background: `bg-elevated` (dark) / `#1C2333` in light mode (dark tooltip for contrast)
- Border: `1px solid border-default`
- Border-radius: 8px
- Padding: `8px 12px`
- Box-shadow: `0 8px 24px rgba(0,0,0,0.3)`
- Max-width: 280px
- Enter/exit: fade + 4px translate, 150ms ease

---

## 6. Map Design

The map is a centerpiece component and needs careful treatment to integrate with the dark/light theme.

### 6.1 Map Style

- **Dark mode:** Use a custom Mapbox or MapLibre style based on a near-black theme (e.g., Mapbox `dark-v11` as a base, customized to match `bg-base`). Reduce label density to only show what's contextually relevant.
- **Light mode:** A muted, low-saturation style (Mapbox `light-v11` base). Avoid the default which is too colorful and competes with data overlays.
- Road lines, building footprints, and labels should be subtle — the data overlays (crime, POIs) should be the visual priority.

### 6.2 Map Layers & Overlays

**Crime Incidents:**
- Render as clustered circles at zoom-out, individual markers at zoom-in
- Color-coded by severity using the semantic danger scale
- Cluster bubbles show count with size proportional to density
- Individual markers: 8px circles with a subtle white ring and drop-shadow

**Points of Interest:**
- Parks/trails: `#34D399` markers with a tree or trail icon
- Schools: `#60A5FA` markers
- Transit: `#FBBF24` markers
- Shopping/amenities: `#9BA3BF` markers
- All POI markers: 28px touch target, with custom monochrome icon inside a circular chip

**Selected Listing:**
- Bold pin marker in `accent-primary`
- Subtle pulsing ring animation on the selected listing's map pin

**Heatmap Mode:**
- Toggle between pin view and heatmap view for crime density
- Heatmap uses the crime heat scale defined in Section 2.4 with 60% global opacity so map context remains readable

### 6.3 Map Controls

- Zoom controls, compass, and style toggle positioned bottom-right
- Layer control panel (toggle crime, POIs, transit, etc.) as a compact floating card bottom-left
- All map control elements use `bg-elevated` with `border: 1px solid border-default` and `border-radius: 8px`

---

## 7. Data Visualization

Charts and visual analytics components should feel native to the dashboard, not like embedded third-party widgets.

### 7.1 Chart Principles

- Use a charting library that allows full style control (Recharts, Nivo, or D3-based).
- Remove chart junk: no unnecessary gridlines, drop shadows on bars, or 3D effects.
- Grid lines: `border-subtle` color, dashed, very low opacity (20–30%).
- Axes: `text-tertiary`, `label` typography.
- Tooltips: match the tooltip component spec in Section 5.7.

### 7.2 Chart Types & Usage

| Chart Type | Usage |
|---|---|
| Line chart | Price history over time, market trend |
| Bar chart (horizontal) | Comparative scores (walk score, transit score) |
| Sparklines | Compact trend indicators in listing cards |
| Donut chart | Crime category breakdown |
| Area chart | Neighborhood price trends |
| Scatter plot | Price vs. square footage comparisons |

### 7.3 Chart Colors

Use the semantic palette for categorical data. For multi-series charts use this ordered palette to ensure contrast:

`#5B7FFF` → `#34D399` → `#FBBF24` → `#F87171` → `#A78BFA` → `#60A5FA`

---

## 8. Motion & Animation

Animation should feel purposeful and quick — it aids comprehension and feels premium, but never causes delay.

### 8.1 Timing & Easing

| Type | Duration | Easing | Usage |
|---|---|---|---|
| Micro | 80–120ms | `ease-out` | Button hover, input focus |
| Standard | 150–200ms | `cubic-bezier(0.16, 1, 0.3, 1)` | Dropdown open, tooltip appear |
| Expand | 250–300ms | `cubic-bezier(0.16, 1, 0.3, 1)` | Panel expand, modal open |
| Page transition | 200ms | `ease-in-out` | Route/view changes |

### 8.2 Animation Patterns

- **Fade + scale:** Modals and popovers enter at `scale(0.97)` → `scale(1)` with opacity 0 → 1.
- **Fade + translate:** Tooltips and dropdowns slide 4–6px from their origin point.
- **Skeleton loading:** Use animated gradient sweeps (shimmer) on `bg-muted` blocks while data loads. Never use spinners for content areas — they increase perceived wait time.
- **Data updates:** When chart data refreshes, animate value changes with a 300ms tween, not a snap.
- **Map flyTo:** Use smooth map camera animations when focusing on a new listing (300–500ms).
- **Respect `prefers-reduced-motion`:** All animations must be disabled or reduced to simple fades when this media query is active.

---

## 9. Iconography

- **Library:** [Lucide Icons](https://lucide.dev/) — clean, consistent, open-source. Supplement with custom icons for real estate-specific concepts (property types, map layer controls).
- **Sizes:** 16px (inline/compact), 20px (default UI), 24px (featured/navigation)
- **Stroke width:** 1.5px for all icons (do not mix stroke weights)
- **Color:** Inherit `currentColor` by default; apply semantic colors for status indicators
- **Interactive icons:** Must have a visible hover state — wrap in a ghost button or apply a hover background

---

## 10. Accessibility

- **Contrast minimums:** WCAG AA for all body text (4.5:1), WCAG AA for large text and UI components (3:1). Aim for AAA (7:1) on primary text.
- **Focus indicators:** All interactive elements must have a clearly visible focus ring. Use `box-shadow: 0 0 0 2px accent-primary, 0 0 0 4px accent-primary-subtle` — never remove outlines without replacing them.
- **Keyboard navigation:** Full tab-through support for the listing list, filters, map controls, and analysis panels.
- **Screen reader support:** All icons used as interactive elements must have `aria-label`. Data visualizations must have accessible text alternatives.
- **Color as a supplement:** Never use color as the sole encoding for meaning (crime severity, map layers). Always pair with an icon, label, or pattern.
- **Touch targets:** Minimum 44×44px for all interactive elements on mobile/tablet.

---

## 11. Dark/Light Mode Toggle

- The user's system preference (`prefers-color-scheme`) should be the default on first load.
- The toggle should be immediately accessible in the top navigation bar.
- Mode switching should be instant (no flash) — apply the theme class to `<html>` or `<body>` and use CSS custom properties (variables) for all color tokens.
- Persist the user's choice to `localStorage`.
- All color tokens should be defined as CSS custom properties in a `:root` (light) and `[data-theme="dark"]` selector pattern, or equivalent in a CSS-in-JS system.

---

## 12. Loading & Empty States

### Loading States

- Use skeleton screens for all content areas — mimic the shape and size of the content that will appear.
- Skeletons use `bg-muted` with an animated shimmer gradient.
- For inline data (a single value updating), use a subtle opacity pulse rather than a full skeleton.

### Empty States

- When a search or filter returns no results: centered illustration (simple, geometric, monochrome), a clear heading, and a single call-to-action.
- Avoid generic empty states — tailor copy to the specific context (e.g., "No listings match your filters" with a "Clear filters" button).
- Empty state containers should use `bg-subtle` and a dashed `border-default` border to distinguish them from loaded content areas.

### Error States

- Inline errors (form validation): `semantic-danger` text below the field, paired with a small icon.
- Component-level errors (failed to load data): Contained error card within the component boundary, with a retry action.
- Never show raw error messages or stack traces to users.

---

## 13. Design Tokens Summary

Implement all values above as design tokens in your chosen system (CSS custom properties, Tailwind theme config, Style Dictionary, etc.). Token naming should follow the pattern:

```
{category}-{variant}-{state}
e.g.: bg-surface, text-secondary, border-default, accent-primary-hover
```

This ensures design decisions are centralized, making light/dark mode switching and future theme updates a single-source change rather than a hunt through the codebase.

---

*These guidelines are a living document. Update as the product evolves and user feedback surfaces new needs.*
