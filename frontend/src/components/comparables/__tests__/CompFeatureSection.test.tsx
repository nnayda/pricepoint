import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
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

  it("is expanded by default", () => {
    render(<CompFeatureSection group={group} />);
    expect(screen.getByText("property age")).toBeInTheDocument();
    expect(screen.getByText("20")).toBeInTheDocument();
    expect(screen.getByText("1.50")).toBeInTheDocument();
    expect(screen.getByText("Yes")).toBeInTheDocument();
  });

  it("hides features when expanded is false", () => {
    render(<CompFeatureSection group={group} expanded={false} />);
    expect(screen.queryByText("property age")).not.toBeInTheDocument();
  });

  it("calls onToggle when header is clicked", () => {
    const onToggle = vi.fn();
    render(<CompFeatureSection group={group} onToggle={onToggle} />);
    fireEvent.click(screen.getByText("Core Stats"));
    expect(onToggle).toHaveBeenCalledTimes(1);
  });

  it("formats null values as dash", () => {
    const nullGroup = {
      category: "Test",
      features: { some_feature: null },
    };
    render(<CompFeatureSection group={nullGroup} />);
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("renders aligned rows from allKeys including missing features", () => {
    const sparseGroup = {
      category: "Test",
      features: { feature_a: 10 },
    };
    render(
      <CompFeatureSection
        group={sparseGroup}
        allKeys={["feature_a", "feature_b"]}
      />,
    );
    expect(screen.getByText("feature a")).toBeInTheDocument();
    expect(screen.getByText("feature b")).toBeInTheDocument();
    // feature_b missing → shows dash
    expect(screen.getByText("—")).toBeInTheDocument();
  });
});
