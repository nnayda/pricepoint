import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import FeatureImportance from "../FeatureImportance";
import type { FeatureAttribution } from "../../../types";

const mockAttributions: FeatureAttribution[] = [
  { feature: "sqft", display_name: "Square Footage", impact_dollars: 18200 },
  { feature: "beds", display_name: "Bedrooms", impact_dollars: 12000 },
  { feature: "crime_score", display_name: "Crime Score", impact_dollars: -7500 },
  { feature: "school_rating", display_name: "School Rating", impact_dollars: 9500 },
  { feature: "age", display_name: "Home Age", impact_dollars: -3200 },
];

describe("FeatureImportance", () => {
  it("renders feature attributions", () => {
    render(<FeatureImportance attributions={mockAttributions} />);
    expect(screen.getByTestId("feature-importance")).toBeInTheDocument();
  });

  it("shows empty state when no attributions provided", () => {
    render(<FeatureImportance attributions={[]} />);
    expect(screen.getByTestId("feature-importance-empty")).toBeInTheDocument();
    expect(screen.getByText("No feature attributions available")).toBeInTheDocument();
  });

  it("displays feature display names", () => {
    render(<FeatureImportance attributions={mockAttributions} />);
    expect(screen.getByText("Square Footage")).toBeInTheDocument();
    expect(screen.getByText("Bedrooms")).toBeInTheDocument();
    expect(screen.getByText("Crime Score")).toBeInTheDocument();
  });

  it("shows positive values with + prefix and green styling", () => {
    render(<FeatureImportance attributions={mockAttributions} />);
    expect(screen.getByText("+$18,200")).toBeInTheDocument();
    expect(screen.getByText("+$12,000")).toBeInTheDocument();
  });

  it("shows negative values with - prefix and red styling", () => {
    render(<FeatureImportance attributions={mockAttributions} />);
    expect(screen.getByText("-$7,500")).toBeInTheDocument();
    expect(screen.getByText("-$3,200")).toBeInTheDocument();
  });

  it("renders green bars for positive impacts", () => {
    render(<FeatureImportance attributions={mockAttributions} />);
    expect(screen.getByTestId("bar-positive-sqft")).toBeInTheDocument();
    expect(screen.getByTestId("bar-positive-beds")).toBeInTheDocument();
  });

  it("renders red bars for negative impacts", () => {
    render(<FeatureImportance attributions={mockAttributions} />);
    expect(screen.getByTestId("bar-negative-crime_score")).toBeInTheDocument();
    expect(screen.getByTestId("bar-negative-age")).toBeInTheDocument();
  });

  it("sorts by absolute impact descending", () => {
    render(<FeatureImportance attributions={mockAttributions} />);
    const items = screen.getAllByRole("listitem");
    // Order: sqft(18200), beds(12000), school(9500), crime(-7500), age(-3200)
    expect(items[0]).toHaveTextContent("Square Footage");
    expect(items[1]).toHaveTextContent("Bedrooms");
    expect(items[2]).toHaveTextContent("School Rating");
    expect(items[3]).toHaveTextContent("Crime Score");
    expect(items[4]).toHaveTextContent("Home Age");
  });

  it("limits to top 10 features", () => {
    const manyAttrs: FeatureAttribution[] = Array.from({ length: 15 }, (_, i) => ({
      feature: `feat_${i}`,
      display_name: `Feature ${i}`,
      impact_dollars: (15 - i) * 1000,
    }));
    render(<FeatureImportance attributions={manyAttrs} />);
    const items = screen.getAllByRole("listitem");
    expect(items).toHaveLength(10);
  });
});
