import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import CompFeatureSection from "../CompFeatureSection";

describe("CompFeatureSection", () => {
  const group = {
    category: "Core Stats",
    features: {
      property_age: 20,
      bed_bath_ratio: 1.5,
      has_garage: true,
    },
  };

  it("renders category name", () => {
    render(<CompFeatureSection group={group} />);
    expect(screen.getByText("Core Stats")).toBeInTheDocument();
  });

  it("is collapsed by default", () => {
    render(<CompFeatureSection group={group} />);
    expect(screen.queryByText("property age")).not.toBeInTheDocument();
  });

  it("expands on click to show features", () => {
    render(<CompFeatureSection group={group} />);
    fireEvent.click(screen.getByText("Core Stats"));
    expect(screen.getByText("property age")).toBeInTheDocument();
    expect(screen.getByText("20")).toBeInTheDocument();
    expect(screen.getByText("1.50")).toBeInTheDocument();
    expect(screen.getByText("Yes")).toBeInTheDocument();
  });

  it("collapses again on second click", () => {
    render(<CompFeatureSection group={group} />);
    const btn = screen.getByText("Core Stats");
    fireEvent.click(btn);
    expect(screen.getByText("property age")).toBeInTheDocument();
    fireEvent.click(btn);
    expect(screen.queryByText("property age")).not.toBeInTheDocument();
  });

  it("formats null values as dash", () => {
    const nullGroup = {
      category: "Test",
      features: { some_feature: null },
    };
    render(<CompFeatureSection group={nullGroup} />);
    fireEvent.click(screen.getByText("Test"));
    expect(screen.getByText("—")).toBeInTheDocument();
  });
});
