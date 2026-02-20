# PricePoint — Dashboard Design Specification

**Version 1.0** · February 2026  
*To be read alongside the PricePoint Design Guidelines document.*

---

## Table of Contents

1. [Global Layout](#1-global-layout)
2. [Navigation Bar](#2-navigation-bar)
3. [Left Column — Sticky Property Cards](#3-left-column--sticky-property-cards)
4. [Tabbed Details Section](#4-tabbed-details-section)
   - [Valuation](#tab-valuation)
   - [Risks](#tab-risks)
   - [Demographics](#tab-demographics)
   - [Schools](#tab-schools)
   - [Points of Interest](#tab-points-of-interest)
   - [Negative Points of Interest](#tab-negative-points-of-interest)
   - [Greenspace](#tab-greenspace)
   - [Property Details](#tab-property-details)
5. [Global Features](#5-global-features)

---

## 1. Global Layout

The dashboard is built around a **two-column sticky layout**:

- **Left column (320px fixed):** Contains the property photos, key facts, and description. This column is sticky and does not scroll with the main content — it serves as a persistent anchor while the user explores tabs.
- **Right column (fluid):** The tabbed content area, taking up the remaining viewport width.

A **collapsed sidebar mode** should be available via a toggle that reduces the left column to a 64px icon rail, maximizing the analysis area for power users.

**Responsive behavior:** Below 1280px, collapse the left column into a horizontal top summary strip (photos hidden, key facts shown inline) and allow the tabbed area to go full-width.

---

## 2. Navigation Bar

**Height:** 64px  
**Background:** `bg-surface` with `border-bottom: 1px solid border-subtle` and `backdrop-filter: blur(12px)` for a frosted-glass effect.

### Left
Logo and "PricePoint" wordmark. Clicking navigates home and clears the active listing.

### Center
Global search box with property address autocomplete. This is the primary entry point and should be prominently sized. Placeholder text: *"Search an address..."*

### Right (left to right)
- **Upload** — icon button that opens a modal for uploading listing data (CSV, JSON)
- **Comparison mode toggle** — lets the user pin up to 3 properties for side-by-side analysis. When active, an icon badge displays the count of pinned properties (e.g., "2")
- **Saved listings** — icon button that opens a slide-in drawer showing bookmarked properties
- **Theme toggle** — dark/light mode switch
- **User avatar menu** — sign in, logout, settings

### Property Breadcrumb Strip
A slim contextual sub-nav (36px height) displayed directly below the main navigation bar whenever a property is actively loaded. Format: `City › Neighborhood › Street Address`. This persists across all tabs and provides a geographic anchor without consuming card space.

---

## 3. Left Column — Sticky Property Cards

### 3.1 Property Photos Card

- Full-width image carousel with `border-radius: 12px` on the top corners to match the card spec
- Left/right arrow navigation buttons overlaid on image edges; dot position indicators below
- **Photo count badge** (e.g., "1 / 12") in the top-right corner of the image
- **Fullscreen button** in the top-left corner, opening a lightbox gallery modal
- **AI Photo Score badge** in the card header (e.g., "Photo Score: 82") — always visible; clicking it deep-links to the Photo Score section in the Valuation tab
- Lazy-load all images; display a shimmer skeleton placeholder while loading

### 3.2 Property Key Facts Card

**Card header:** A color-coded status badge (green for "For Sale", amber for "Pending", gray for "Sold") alongside the listing or sold price displayed in `mono-lg` typography. Price per square foot is shown immediately below the price in `text-secondary` — e.g., *"$312 / sq ft"*.

**Address** displayed in `heading-md` below the price.

**Key stats grid:** Two-column grid of icon + value pairs:

| Stat | Stat |
|---|---|
| Beds | Baths |
| Sq Ft | Lot Acres |
| Year Built | Property Type |
| Garage / Parking | Heating Type |
| Cooling Type | — |

**Days on Market (DOM):** Shown as a callout chip below the grid — e.g., *"Listed 23 days ago"*. Color-coded: green for fewer than 30 days, amber for 30–90 days, red for more than 90 days.

**Quick action row:** Three icon buttons anchored to the bottom of the card:
- Bookmark / save listing
- Share (copy link to clipboard)
- Open in external source — Redfin, Zillow, etc. (opens in new tab)

### 3.3 Property Description Card

**Header:** "About this Property" with an **AI Description Score chip** in the top-right (e.g., "Description Score: 74"). Clicking this chip deep-links to the Description Score section in the Valuation tab.

The card leads with a 2–3 sentence **AI-generated summary** of the property in `body-md`. The raw MLS listing description is available beneath a "Show full listing description" disclosure toggle.

**Key features tag strip:** Structured amenities extracted from the listing description displayed as small rounded tags (e.g., "Hardwood Floors", "Updated Kitchen", "Fireplace", "Pool"). These are quick-scannable and appear between the AI summary and the disclosure.

---

## 4. Tabbed Details Section

**Tab bar:** Horizontally scrollable tab list with `space-5` padding. The active tab uses an `accent-primary` bottom border indicator and `text-primary`. Inactive tabs use `text-tertiary`. Left and right arrow keys on the keyboard navigate between tabs.

**Tab order (left to right):**
Valuation → Risks → Demographics → Schools → Points of Interest → Negative POIs → Greenspace → Property Details

**Tab status indicators:** Small colored dot indicators appear on tab labels when data warrants attention — for example, a red dot on "Risks" if any risk score exceeds 7, or an amber dot on "Valuation" if the model's confidence interval is unusually wide. These give users a signal to explore each tab without requiring them to visit all tabs sequentially.

---

### Tab: Valuation

#### Model Estimate

The primary valuation visual is a horizontal **Estimate Range Bar** — a single chart showing all key value references simultaneously:

```
|-------|==========[      ]==========|-------|
  Tax      95% CI    Model    95% CI    List
  Asmt     Low       Est      High      Price
```

The bar is color-coded using semantic colors: green if the listing price falls within the model's confidence interval (fairly priced), amber if slightly outside, red if significantly above the estimated range.

Below the bar, three labeled data chips display:
- **Tax Assessment** — assessed value + delta vs. listing price
- **Model Estimate** — predicted value in `mono-lg`, plus a confidence label ("High confidence" / "Moderate confidence") derived from the width of the CI
- **Listing Price** — listing or sold price + delta vs. model estimate

A **valuation verdict** is shown as a prominent one-line callout directly below the chips, using semantic color — e.g., *"Priced 8% above estimated value"* or *"Potential value opportunity — listed below model estimate."*

#### Price History Chart

A line chart with time on the X axis and price on the Y axis. Three series are overlaid on a single chart:
- **Listing price events** — discrete dots for each time the property was listed or sold
- **Assessment history** — dashed line from county assessor records
- **Model backtest** — shaded area showing what the model would have predicted historically

A toggle above the chart allows the user to overlay the **neighborhood median price trend line** for market context (distinguishing a property-specific price move from a broader market shift). Clicking any event point on the chart shows a popover with the event date, price, and data source.

#### Model Explainability — SHAP Waterfall Chart

A horizontal waterfall chart showing the top 10 features by absolute SHAP contribution. The chart reads left to right: base value → each feature pushes the bar right (positive, `semantic-success`) or left (negative, `semantic-danger`) → final predicted value.

Each row displays: feature name, the value used in the model, and the SHAP contribution amount.

A **"What does this mean?"** disclosure below the chart provides a plain-language explanation of SHAP values for non-technical users.

A **feature category grouping toggle** allows switching between "individual features" (default) and "grouped by category" (Location, Condition, Size, Crime, Schools) for a higher-level view of what's driving the estimate.

#### AI Listing Quality

A two-column section displaying the Photo Score and Description Score side by side. Each score card contains:
- A **semi-circular gauge** (0–100) with a color gradient from `semantic-danger` at 0 through `semantic-warning` to `semantic-success` at 100
- The numeric score in `mono-lg` centered inside the gauge arc
- A grade label below the gauge (e.g., "Good", "Fair", "Poor")
- Two columns of tag chips below: **Positive signals** (green) and **Negative signals** (red), each with a brief explanatory phrase

A third combined **Listing Health Score** synthesizes photo score, description score, days on market, and price-drop history into a single 0–100 indicator displayed at the top of the section.

#### Mortgage Payment Calculator

**Layout:** Controls on the left, donut chart on the right.

**Controls:**
- Home Price — pre-filled from listing price, editable
- Down Payment — range slider + text input; displays both the dollar amount and percentage simultaneously
- Interest Rate — range slider + text input; pre-filled from the latest FRED 30-year fixed mortgage rate
- Loan Term — segmented control: 15yr / 20yr / 30yr
- Property Tax Rate — editable, pre-filled from county assessment data
- Monthly HOA Fee — editable field, pre-filled if available from listing
- Annual Home Insurance — editable field with a sensible default estimate

**Donut chart:** A semi-circle donut breaking the monthly payment into segments: Principal, Interest, Tax, Insurance, PMI, and HOA. Hovering a segment shows the dollar amount.

**Affordability callout:** Below the calculator, display *"Recommended annual income to afford this home"* based on the 28% front-end ratio rule. Color-code relative to the area's median household income (sourced from Demographics data).

**Amortization table:** A "View amortization schedule" disclosure that expands a year-by-year table showing outstanding balance, cumulative principal paid, cumulative interest paid, and equity percentage.

---

### Tab: Risks

#### Risk Overview

A **Risk Summary Card Grid** (2×3 layout) displays one card per risk category. Each card contains:
- Category icon + name
- Risk level label: Low / Moderate / High / Severe
- A horizontal colored bar using the semantic color scale
- Numeric score (1–10)
- A one-sentence plain-language summary (e.g., *"This area falls within a 100-year flood zone."*)

Risk categories:
1. Flood Risk
2. Fire Risk
3. Crime Risk
4. Utility Risk
5. Earthquake Risk — sourced from USGS hazard data
6. Air Quality / Environmental Risk — sourced from EPA AQI data and proximity to Superfund sites or industrial zones

An **Overall Risk Score** — a weighted composite of all six categories — is displayed as a prominent callout card at the top of the tab, before the individual category grid.

#### Crime Map

A full-width map with two display modes toggled via a segmented control above the map:

**Density mode:** Heatmap or choropleth overlay representing crime density. A color scale legend is anchored to the bottom-left of the map as a floating card. The subject property is always shown as a distinct `accent-primary` pin.

**Incidents mode:** Clustered circle markers. Clicking a cluster zooms the map in to reveal individual incidents. Clicking an individual incident marker shows a popover with: incident type, category, date/time, and distance from the subject property.

In both modes, a **radius ring** is drawn on the map corresponding to the active radius filter selection, so users can visually understand the geographic scope of the displayed statistics.

#### Crime Statistics

A row of three **Stat Cards** displays:
- **Crime Z-Score** — standardized crime rate within the selected radius compared to the county average, with a directional label (e.g., "1.4σ above county average")
- **Growth Rate** — whether crime incidents are trending up or down in the area, shown with a trend arrow and percentage
- **Incident Count** — total number of incidents in the selected area and time period

Below the stat cards, a **horizontal bar chart sorted by incident count** breaks down crime by type. To the right of each bar, a small 12-month sparkline shows the trend for that crime type.

A **comparative context table** below the chart shows: property area vs. city average vs. county average, for both total incidents and the rate per 1,000 residents.

#### Filters

A compact filter bar sits directly above the crime statistics section and controls both the map and statistics:

- **Time frame:** Past 30 Days / Past Year / Past 5 Years (segmented pill control)
- **Radius:** 0.5 mi / 1 mi / 5 mi (segmented pill control)

---

### Tab: Demographics

A **geography level selector** is displayed prominently at the top of the tab as a segmented control: Neighborhood / Census Block Group / Census Tract. An info icon (ℹ) with a tooltip explains the difference between each level for users unfamiliar with census geographies.

#### Race / Ethnicity
A **donut chart** with a labeled legend showing the racial and ethnic makeup of the selected area. Slices representing less than 3% of the population are grouped into an "Other" segment. Percentages are displayed on each slice or in the legend.

#### Age Distribution
A grouped bar chart of the resident age distribution. The county median age is overlaid as a vertical reference line. Bars are color-coded by life stage: Children (0–17), Young Adults (18–34), Middle Age (35–54), Older Adults (55+).

#### Sex Distribution
A horizontal two-bar chart or split donut showing the male/female percentage breakdown. Clean and precise — communicates the same information as a pictorial chart without ambiguity.

#### Income
- **Median household income** shown as the primary metric in `mono-lg`, with the county median shown below in `text-secondary` as a comparison reference
- **Supporting chips:** % of households below the poverty line, and % of households earning more than $100K annually
- **Income distribution histogram:** A bar chart showing the distribution of household income brackets for the selected area, with the county distribution overlaid in a muted color for direct comparison

#### Home Ownership
An **angular gauge** with a needle indicator showing the owner-occupied vs. renter-occupied split. Supporting stats below the gauge:
- **Vacancy Rate** — a high vacancy rate can signal neighborhood decline or heavy investor activity
- **Median Length of Residence** — longer average tenure indicates neighborhood stability

#### Population Trends
A small area chart showing population change over a 10-year period for the selected geography. Declining population is a key long-term risk signal for buyers.

---

### Tab: Schools

#### School List

Schools are displayed as **compact cards**, clearly separated into two sections: **Assigned Schools** (the schools this address is zoned for) and **Nearby Schools**.

Each card includes:
- Color-coded rating badge: green for 7–10, amber for 4–6, red for 1–3
- School name in `heading-sm`
- Type: Public / Private / Charter
- Grades served (e.g., K–5, 6–8, 9–12)
- Distance + driving time + walking time
- Student-teacher ratio
- Test score state percentile
- Enrollment size

#### Schools Map

A map displaying the subject property and nearby schools as markers, color-coded by level: Elementary (blue), Middle (green), High School (orange).

When a school marker is hovered or clicked, a route line is drawn on the map from the property to that school, showing the driving or walking path.

A **school district boundary overlay** toggle displays the district boundary polygons on the map (where data is available). This is critical — a buyer's assigned district does not always match the geographically closest school.

---

### Tab: Points of Interest

#### POI Score Summary
A summary callout at the top of the tab — e.g., *"8 of your 12 saved POIs are within a 10-minute drive"* — provides an instant read without requiring the user to scan the full list.

#### POI List
Categories are displayed as a **collapsible accordion**. The collapsed state for each category shows: category name, nearest POI distance, and the count of saved POIs in that category. Expanding a category reveals the full list of individual POIs with name and distance.

#### POI Map
A full-width map displaying the subject property and all saved POIs as markers. Each category uses a distinct icon and color combination, with a mini-legend card floating in a corner of the map. Clicking a marker shows a popover with the POI name, category, address, and distance from the property.

An **isochrone overlay toggle** allows the user to display drive-time or walk-time reachability zones (5-min / 10-min / 15-min) on the map. This shows what is reachable within a given time — significantly more actionable than straight-line distance.

---

### Tab: Negative Points of Interest

#### Auto-Detected Negatives

The system automatically calculates the distance from the subject property to the following known negative features:
- Major roads and highways
- Railroads
- High-voltage utility lines
- Industrial and manufacturing zones
- Superfund / EPA hazardous waste sites
- Landfills and waste transfer facilities
- Airports (including flight path noise contour mapping)
- Power plants
- Cell towers

In addition, users can add custom negative POIs that they personally want to avoid.

#### Distance Threshold Indicators

Each negative POI shows a visual indicator — Safe / Caution / Concern — based on configurable distance thresholds. Default thresholds are pre-set by category (e.g., highway: Concern < 0.1mi, Caution 0.1–0.3mi, Safe > 0.3mi) and can be adjusted in user Settings.

#### Noise Exposure
Where proximity to a highway, railroad, or airport is detected, show an estimated noise exposure indicator (Low / Moderate / High, or a dB range estimate) based on known noise contour datasets.

#### Negative POI Map
Same behavior as the POI map — markers colored by category, click for details, mini-legend floating card. The subject property is always displayed as a distinct pin.

---

### Tab: Greenspace

#### Greenspace Score
A **semi-circular gauge** (0–100, matching the AI Listing Quality style) at the top of the tab displays a composite Greenspace Score synthesizing: % area greenspace, walking time to the nearest park, trail density, and the greenspace z-score vs. county average. A grade label and one-sentence context summary appear below the gauge.

#### Key Statistics

Displayed as a row of stat cards:
- Walking time to nearest park / trail
- Number of parks within 1 mile
- Total trail miles within 2 miles
- % area greenspace (census tract)
- Greenspace z-score vs. county average
- Tree canopy coverage %
- Nearest dog park — name and walking time

#### Greenspace Map

A map displaying the subject property alongside:
- Park and greenspace polygons (filled)
- Trail and path polylines
- Tree canopy coverage as an optional green-tinted layer
- Bodies of water (lakes, rivers, ponds)
- Bike lanes and multi-use paths

---

### Tab: Property Details

#### Section 1: Listing Details

All structured MLS / Redfin listing fields displayed in a clean two-column definition list (label left, value right). Fields are grouped into collapsible sub-sections:
- **Interior** — rooms, finishes, flooring, appliances, fireplace
- **Exterior** — lot details, garage, pool, outbuildings, fencing
- **Utilities** — HVAC system, water source, sewer, electrical
- **HOA** — monthly fee, HOA name, rules and restrictions, amenities
- **Listing Info** — MLS ID, list date, days on market history, listing agent, brokerage

#### Section 2: County Assessment Record

Sourced from the county assessor:
- Assessed land value
- Assessed improvement value
- Total assessed value
- Last assessment date
- Annual property tax amount
- Monthly property tax equivalent
- Effective tax rate
- Parcel ID / APN

#### Section 3: Engineered Model Features

A structured table of the features computed for the ML valuation model. Collapsed by default. Columns: Feature Name, Value Used, Description.

| Feature | Value | Description |
|---|---|---|
| crime_zscore_1mi | 1.43 | Standardized crime rate within 1 mile vs. county |
| school_avg_rating | 7.2 | Average rating of assigned schools |
| park_walk_min | 8 | Walking minutes to nearest park |
| ... | ... | ... |

Each row includes an ℹ tooltip explaining how the feature is computed and why it matters to the model. This section is intended for power users and analysts.

#### Data Source Provenance

A collapsible panel at the bottom of the tab listing every data source used for this property, the specific dataset or API queried, and the date that source was last refreshed. This builds user trust and allows buyers to verify data currency before making a decision.

| Source | Dataset | Last Refreshed |
|---|---|---|
| Redfin | Listing data | Feb 14, 2026 |
| County Assessor | Property assessment | Jan 1, 2026 |
| U.S. Census Bureau | ACS 5-Year Estimates | Oct 2025 |
| FRED | 30-Year Mortgage Rate | Feb 18, 2026 |
| Police Incident API | Crime incidents | Feb 17, 2026 |

---

## 5. Global Features

### Comparison Mode

When the user has 2–3 properties pinned via the nav bar comparison toggle, a **Comparison View** is accessible. Properties are displayed side by side in columns using the same section and metric structure as the standard property view. Values that are better than the average across the compared properties receive a subtle green background tint; worse values receive a red tint. This allows rapid identification of trade-offs between properties.

### Property Report Export

A "Export Report" button — accessible from the navigation bar or from the property actions — generates a downloadable PDF summarizing: key property facts, valuation model output and confidence interval, risk scores, school ratings, and neighborhood highlights. The report is formatted for sharing with a partner, real estate agent, or financial advisor.

### Data Freshness Indicators

Any metric or stat sourced from data older than 30 days displays a small amber clock icon (⏱) with a tooltip on hover indicating the exact data age. This is especially critical for crime statistics, market pricing, and mortgage rates, which can change rapidly.

### Onboarding & Empty States

**No property loaded:** A centered empty state with a large search bar and a 2–3 sentence explanation of what PricePoint does and what data it draws on. Include 2–3 example address chips to demonstrate the search experience.

**Tab data unavailable:** When data for a specific tab cannot be retrieved for the current property, display a clearly styled empty state card within the tab content area. Explain concisely what is missing and why — e.g., *"Crime incident data is not yet available for this county. We're working on expanding coverage."* Never display a blank or broken layout.

**Loading states:** All tab content areas use shimmer skeleton screens while data is being fetched — sized and shaped to approximate the content that will appear. Avoid full-page spinners; partial progressive loading is preferred so users can begin reading available data immediately.

---

*PricePoint Dashboard Design Specification — v1.0*  
*Maintained by the PricePoint Product & Design team.*
