import { describe, it, expect } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import FeatureCatalogTable from "../FeatureCatalogTable";
import type { FeatureCatalogEntry } from "../../../types";

const FEATURES: FeatureCatalogEntry[] = [
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
    name: "has_garage",
    category: "Parking",
    sql_type: "Boolean",
    source: "property_details",
    derivation: "parse_has_garage()",
    example: "true",
    default: "false",
  },
];

const CATEGORIES = ["Core Stats", "Parking"];

describe("FeatureCatalogTable", () => {
  it("renders all features", () => {
    render(<FeatureCatalogTable features={FEATURES} categories={CATEGORIES} />);
    expect(screen.getByText("sqft")).toBeInTheDocument();
    expect(screen.getByText("has_garage")).toBeInTheDocument();
  });

  it("renders search input", () => {
    render(<FeatureCatalogTable features={FEATURES} categories={CATEGORIES} />);
    expect(screen.getByPlaceholderText("Search features...")).toBeInTheDocument();
  });

  it("filters by search text", async () => {
    render(<FeatureCatalogTable features={FEATURES} categories={CATEGORIES} />);
    fireEvent.change(screen.getByPlaceholderText("Search features..."), {
      target: { value: "garage" },
    });
    await waitFor(() => {
      expect(screen.getByText("has_garage")).toBeInTheDocument();
    });
    expect(screen.queryByText("sqft")).not.toBeInTheDocument();
  });

  it("renders category filter chips", () => {
    render(<FeatureCatalogTable features={FEATURES} categories={CATEGORIES} />);
    expect(screen.getByText(/^All/)).toBeInTheDocument();
    // Category names appear both as chips and in table cells
    const coreStatsElements = screen.getAllByText("Core Stats");
    expect(coreStatsElements.length).toBeGreaterThanOrEqual(1);
    const parkingElements = screen.getAllByText("Parking");
    expect(parkingElements.length).toBeGreaterThanOrEqual(1);
  });

  it("filters by category when chip clicked", async () => {
    render(<FeatureCatalogTable features={FEATURES} categories={CATEGORIES} />);
    // Use role selector to target the chip button, not the table cell
    const parkingChip = screen.getByRole("button", { name: "Parking" });
    fireEvent.click(parkingChip);
    await waitFor(() => {
      expect(screen.getByText("has_garage")).toBeInTheDocument();
    });
    // sqft feature name button should not be present
    expect(screen.queryByRole("button", { name: "sqft" })).not.toBeInTheDocument();
  });

  it("expands row to show derivation details", () => {
    render(<FeatureCatalogTable features={FEATURES} categories={CATEGORIES} />);
    fireEvent.click(screen.getByText("sqft"));
    expect(screen.getByText(/parse_sqft/)).toBeInTheDocument();
    expect(screen.getByText("2450")).toBeInTheDocument();
  });

  it("shows no results message when search has no matches", async () => {
    render(<FeatureCatalogTable features={FEATURES} categories={CATEGORIES} />);
    fireEvent.change(screen.getByPlaceholderText("Search features..."), {
      target: { value: "zzzzz" },
    });
    await waitFor(() => {
      expect(screen.getByText(/no features match/i)).toBeInTheDocument();
    });
  });
});
