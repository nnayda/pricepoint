import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { ThemeProvider } from "../../contexts/ThemeContext";
import { AuthProvider } from "../../contexts/AuthContext";
import ModelMethodologyPage from "../ModelMethodologyPage";
import type { FeatureCatalogResponse, ModelMethodologyResponse } from "../../types";

// Mock the hook
const mockUseModelMethodology = vi.fn();
vi.mock("../../hooks/useModelMethodology", () => ({
  useModelMethodology: () => mockUseModelMethodology(),
}));

const MOCK_METHODOLOGY: ModelMethodologyResponse = {
  metadata: {
    model_name: "pricepoint-home-value",
    model_version: "5",
    run_id: "run123",
    training_date: "2024-01-15T10:30:00Z",
    n_features: 94,
    n_training_samples: 1200,
    algorithm: "reg:squarederror",
    hyperparameters: { n_estimators: 500, max_depth: 6 },
  },
  metrics: {
    mae: 25000,
    rmse: 35000,
    mape: 8.5,
    r2: 0.92,
    median_ae: 18000,
    mae_mean: 26000,
    mae_std: 2000,
    rmse_mean: 36000,
    rmse_std: 3000,
    r2_mean: 0.91,
    r2_std: 0.02,
    data_n_rows: 1500,
    data_n_features: 94,
    data_target_mean: 350000,
    data_target_median: 300000,
    data_target_std: 150000,
  },
  feature_importance: [
    { feature: "sqft", gain: 0.15 },
    { feature: "year_built", gain: 0.08 },
  ],
  available_plots: ["plots/actual_vs_predicted.png", "plots/residuals_vs_predicted.png"],
  available_eda_plots: ["eda/eda_pairwise_target.png"],
};

const MOCK_CATALOG: FeatureCatalogResponse = {
  features: [
    {
      name: "sqft",
      category: "Core Stats",
      sql_type: "Integer",
      source: "staging",
      derivation: "parse_sqft()",
      example: "2450",
      default: "NULL",
    },
    {
      name: "year_built",
      category: "Core Stats",
      sql_type: "Integer",
      source: "staging",
      derivation: "parse_year_built()",
      example: "1998",
      default: "NULL",
    },
    {
      name: "has_garage",
      category: "Parking",
      sql_type: "Boolean",
      source: "property_details",
      derivation: "parse_has_garage()",
      example: "true",
      default: "false",
    },
  ],
  categories: ["Core Stats", "Parking"],
};

function renderPage() {
  return render(
    <MemoryRouter>
      <ThemeProvider>
        <AuthProvider>
          <ModelMethodologyPage />
        </AuthProvider>
      </ThemeProvider>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("ModelMethodologyPage", () => {
  it("renders loading skeleton when data is loading", () => {
    mockUseModelMethodology.mockReturnValue({
      methodology: null,
      featureCatalog: null,
      loading: true,
      error: null,
    });
    renderPage();
    expect(screen.getByTestId("methodology-loading")).toBeInTheDocument();
  });

  it("renders error state when API returns error", () => {
    mockUseModelMethodology.mockReturnValue({
      methodology: null,
      featureCatalog: null,
      loading: false,
      error: "Network Error",
    });
    renderPage();
    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText(/unable to load/i)).toBeInTheDocument();
    expect(screen.getByText("Network Error")).toBeInTheDocument();
  });

  it("renders no-model state when methodology is null", () => {
    mockUseModelMethodology.mockReturnValue({
      methodology: null,
      featureCatalog: null,
      loading: false,
      error: null,
    });
    renderPage();
    expect(screen.getByText(/no model available/i)).toBeInTheDocument();
  });

  it("renders all three section headings on success", () => {
    mockUseModelMethodology.mockReturnValue({
      methodology: MOCK_METHODOLOGY,
      featureCatalog: MOCK_CATALOG,
      loading: false,
      error: null,
    });
    renderPage();
    expect(screen.getByText("Model Design")).toBeInTheDocument();
    expect(screen.getByText("Model Fit")).toBeInTheDocument();
    expect(screen.getByText("Feature Analysis")).toBeInTheDocument();
  });

  it("renders metric cards with correct formatted values", () => {
    mockUseModelMethodology.mockReturnValue({
      methodology: MOCK_METHODOLOGY,
      featureCatalog: MOCK_CATALOG,
      loading: false,
      error: null,
    });
    renderPage();
    // MAE should be currency formatted
    expect(screen.getByText("$25,000")).toBeInTheDocument();
    // RMSE
    expect(screen.getByText("$35,000")).toBeInTheDocument();
    // R-squared
    expect(screen.getByText("0.92")).toBeInTheDocument();
  });

  it("renders plot images with correct src URLs", () => {
    mockUseModelMethodology.mockReturnValue({
      methodology: MOCK_METHODOLOGY,
      featureCatalog: MOCK_CATALOG,
      loading: false,
      error: null,
    });
    renderPage();
    const images = screen.getAllByRole("img");
    const plotSrcs = images.map((img) => img.getAttribute("src"));
    expect(plotSrcs).toContain("/api/model/artifact/plots/actual_vs_predicted.png");
    expect(plotSrcs).toContain("/api/model/artifact/plots/residuals_vs_predicted.png");
  });

  it("renders model version badge", () => {
    mockUseModelMethodology.mockReturnValue({
      methodology: MOCK_METHODOLOGY,
      featureCatalog: MOCK_CATALOG,
      loading: false,
      error: null,
    });
    renderPage();
    expect(screen.getByText("v5")).toBeInTheDocument();
  });

  it("renders feature importance bars", () => {
    mockUseModelMethodology.mockReturnValue({
      methodology: MOCK_METHODOLOGY,
      featureCatalog: MOCK_CATALOG,
      loading: false,
      error: null,
    });
    renderPage();
    // "sqft" appears in both feature importance and catalog, so use getAllByText
    expect(screen.getAllByText("sqft").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("year_built").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Top Feature Importances (by Gain)")).toBeInTheDocument();
  });

  it("renders feature catalog table", () => {
    mockUseModelMethodology.mockReturnValue({
      methodology: MOCK_METHODOLOGY,
      featureCatalog: MOCK_CATALOG,
      loading: false,
      error: null,
    });
    renderPage();
    expect(screen.getByText("Feature Catalog (3 features)")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Search features...")).toBeInTheDocument();
  });

  it("feature table search filters results", async () => {
    mockUseModelMethodology.mockReturnValue({
      methodology: MOCK_METHODOLOGY,
      featureCatalog: MOCK_CATALOG,
      loading: false,
      error: null,
    });
    renderPage();

    const searchInput = screen.getByPlaceholderText("Search features...");
    fireEvent.change(searchInput, { target: { value: "garage" } });

    await waitFor(() => {
      // "has_garage" should be visible
      expect(screen.getByText("has_garage")).toBeInTheDocument();
    });

    // sqft and year_built should not be visible in the table
    const featureButtons = screen.getAllByRole("button");
    const featureNames = featureButtons.map((b) => b.textContent);
    expect(featureNames).not.toContain("sqft");
  });

  it("feature table category filter works", async () => {
    mockUseModelMethodology.mockReturnValue({
      methodology: MOCK_METHODOLOGY,
      featureCatalog: MOCK_CATALOG,
      loading: false,
      error: null,
    });
    renderPage();

    // Click the "Parking" chip
    const parkingChip = screen.getByRole("button", { name: /^Parking$/i });
    fireEvent.click(parkingChip);

    await waitFor(() => {
      expect(screen.getByText("has_garage")).toBeInTheDocument();
    });

    // Check that Core Stats features are filtered out
    const allButtons = screen.getAllByRole("button");
    const buttonTexts = allButtons.map((b) => b.textContent);
    // sqft should not appear as a clickable feature name (it could still be in other text)
    expect(buttonTexts).not.toContain("sqft");
  });

  it("has proper heading hierarchy", () => {
    mockUseModelMethodology.mockReturnValue({
      methodology: MOCK_METHODOLOGY,
      featureCatalog: MOCK_CATALOG,
      loading: false,
      error: null,
    });
    renderPage();
    const h1 = screen.getByRole("heading", { level: 1 });
    expect(h1).toHaveTextContent("Model Methodology");
    const h2s = screen.getAllByRole("heading", { level: 2 });
    expect(h2s.length).toBeGreaterThanOrEqual(3);
  });

  it("plot images have alt text", () => {
    mockUseModelMethodology.mockReturnValue({
      methodology: MOCK_METHODOLOGY,
      featureCatalog: MOCK_CATALOG,
      loading: false,
      error: null,
    });
    renderPage();
    const images = screen.getAllByRole("img");
    images.forEach((img) => {
      expect(img).toHaveAttribute("alt");
      expect(img.getAttribute("alt")).not.toBe("");
    });
  });

  it("renders hyperparameters table", () => {
    mockUseModelMethodology.mockReturnValue({
      methodology: MOCK_METHODOLOGY,
      featureCatalog: MOCK_CATALOG,
      loading: false,
      error: null,
    });
    renderPage();
    expect(screen.getByText("n_estimators")).toBeInTheDocument();
    expect(screen.getByText("500")).toBeInTheDocument();
    expect(screen.getByText("max_depth")).toBeInTheDocument();
    expect(screen.getByText("6")).toBeInTheDocument();
  });

  it("renders CV metrics section", () => {
    mockUseModelMethodology.mockReturnValue({
      methodology: MOCK_METHODOLOGY,
      featureCatalog: MOCK_CATALOG,
      loading: false,
      error: null,
    });
    renderPage();
    expect(screen.getByText("Cross-Validation (5-fold)")).toBeInTheDocument();
    expect(screen.getByText("CV MAE")).toBeInTheDocument();
  });
});
