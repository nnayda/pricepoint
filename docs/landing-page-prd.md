## PricePoint Landing Page — Content & Section Recommendations

### 1. Navigation Bar
Minimal and clean — this is not the dashboard nav. It should contain only:
- Logo / wordmark (left)
- Sign In and Get Started / Sign Up buttons (right)

No distractions. The page has one job.

---

### 2. Hero Section

This is the most important section and should occupy the full viewport on load. Everything the user needs to understand PricePoint and take the first action should be visible without scrolling.

**Headline:** One punchy line that leads with the buyer's problem, not the product's features. Something like:
> *"Know what a home is really worth before you buy."*

**Sub-headline:** One to two sentences expanding on the value proposition — mention the ML model and the breadth of data it draws on. e.g., *"PricePoint combines listing data, crime statistics, school ratings, neighborhood demographics, and economic indicators into a single AI-powered property analysis."*

**Search bar:** Large, prominent, centered — the visual centerpiece of the hero. Slightly wider than typical inputs, with address autocomplete. A clear CTA label inside or beside it: *"Search any address"* or *"Analyze a property."*

**Social proof anchor:** Directly below the search bar, a single low-friction trust line — e.g., *"Analyzing properties across 48 states · 2M+ listings indexed"* — gives hesitant users a reason to trust the search before they commit.

**Background:** A subtle animated or static visual — either a muted map/satellite texture, a blurred property image, or an abstract data visualization — that communicates "real estate intelligence" without being literal or stock-photo-generic. Avoid the cliché smiling-couple-in-front-of-house imagery entirely.

---

### 3. Feature Showcase — "What PricePoint Analyzes"

Directly below the hero, before any sign-up ask. The user who just scrolled past the search bar is curious but not yet convinced — show them what they get.

**Format:** A horizontal row of 3–4 icon cards (on desktop), stacking vertically on mobile. Each card has an icon, a short label, and one sentence of description. Keep it scannable — this is not a features list, it's a promise.

Recommended cards:

| Card | Label | Description |
|---|---|---|
| 📊 | AI Valuation Model | See what the home is actually worth, with confidence intervals and full model explainability. |
| 🗺 | Crime & Safety | Crime density maps, incident breakdowns, and z-score comparisons to county averages. |
| 🏫 | Schools & Demographics | Assigned school ratings, district boundaries, income distribution, and population trends. |
| 🌿 | Neighborhood Quality | Greenspace coverage, points of interest, noise exposure, and environmental risk scores. |

---

### 4. Product Preview / Dashboard Screenshot

A high-fidelity screenshot or interactive mockup of the actual dashboard — specifically the Valuation tab, since that's the flagship differentiator. This should feel like a window into the product, not a marketing illustration.

**Annotate 3–4 key elements** with small floating callout labels pointing to:
- The Estimate Range Bar ("AI-predicted value with confidence interval")
- The SHAP Waterfall Chart ("See exactly what's driving the estimate")
- The Risk score cards ("Six risk categories, instantly scored")
- The Mortgage Calculator ("Model your monthly payment in real time")

If feasible, make this section **interactive** — let the user hover over or click parts of the mockup to see a brief description of that feature. This is more engaging than a static image and helps technical-leaning buyers understand the depth of the tool before signing up.

---

### 5. Data Sources — Trust Section

This directly addresses the "building trust with data sources" priority. Buyers are skeptical — they've been burned by Zestimate-style black boxes. Showing your sources is a meaningful differentiator.

**Format:** A clean strip or grid of source logos or named badges with a brief label under each. Examples:

- **Redfin** — Listing & sale data
- **County Assessors** — Tax assessments & property records
- **U.S. Census Bureau (ACS)** — Demographics & income
- **FRED / Federal Reserve** — Mortgage rate data
- **Local Police APIs** — Crime incident data
- **GreatSchools** — School ratings
- **USGS / FEMA** — Flood & earthquake risk
- **EPA** — Environmental hazard data

Above or below the logos, a short line of copy that frames *why* this matters: *"Every estimate is built on primary sources — not aggregated third-party feeds."*

---

### 6. How It Works

A brief 3-step explainer for users who want to understand the process before committing. Keep it visual and short — this is not a technical whitepaper.

**Step 1 — Search a property:** Enter any residential address in the US.
**Step 2 — We analyze the data:** Our ML pipeline pulls listing data, geospatial signals, and economic indicators in real time.
**Step 3 — Make a confident decision:** Review the valuation estimate, risk scores, and neighborhood deep-dive before you make an offer.

Format as a horizontal numbered flow on desktop, vertical stack on mobile. Icons or simple illustrations for each step.

---

### 7. Conversion / Sign-Up Section

The explicit sign-up ask. This comes *after* the user has seen what the product does and why the data is trustworthy — they're now in the best mental state to convert.

**Headline:** Something low-pressure and outcome-focused — *"Start your analysis free"* or *"Search your first property — no credit card required."*

**Form:** Keep it minimal. Email + password, or a "Continue with Google" single button. The fewer fields, the higher the conversion rate. Don't ask for name, phone number, or any housing preferences at sign-up — collect those progressively inside the product.

**If access model is undecided:** Use a soft CTA for now — *"Join the waitlist"* or *"Get early access"* — with just an email field. This lets you start building an audience before the product is fully ready and avoids committing to a pricing model prematurely.

Below the form, a brief 1-line reassurance: *"No spam. No obligation. Cancel anytime."* — or equivalent.

---

### 8. Footer

Lean and functional:
- Logo + one-line product description
- Links: About, Privacy Policy, Terms of Service, Contact
- Theme toggle (carry the dark/light preference from the dashboard)
- Copyright line

No excessive footer columns — this is a focused product, not a content site.

---

## Section Order Summary

```
1. Nav Bar
2. Hero  ← Full viewport, search bar is the star
3. Feature Cards  ← What you get
4. Dashboard Preview  ← See it in action
5. Data Sources  ← Why you can trust it
6. How It Works  ← How it works in 3 steps
7. Sign-Up CTA  ← Convert
8. Footer
```

## A Few Design Notes Specific to the Landing Page

**Scroll depth matters:** The search bar in the hero should be repeated or kept accessible as a sticky element after the user scrolls past it — either in the nav bar or as a floating button. Users who scroll to learn more should always be one click away from actually using the product.

**Animate sparingly:** A subtle entrance animation on the hero text and search bar (staggered fade-up, ~200ms delay between elements) gives the page a polished feel without distracting from the search CTA. The dashboard preview section benefits from a scroll-triggered reveal.

**Dark mode by default:** Given the dashboard is dark-first, the landing page should match. A jarring light-to-dark transition when a user clicks into the app breaks the experience. The landing page footer or nav can offer the theme toggle for users who prefer light.

**Don't gate the search:** If technically feasible, allow unauthenticated users to enter an address and see a preview or teaser of the analysis before hitting a sign-up wall. This "aha moment first, account second" pattern dramatically improves conversion — the user has already seen value before you ask anything of them.