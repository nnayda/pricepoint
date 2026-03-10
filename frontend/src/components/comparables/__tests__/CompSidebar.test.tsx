import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import CompSidebar from "../CompSidebar";
import type { ComparablesSearchCriteria } from "../../../types";

const DEFAULT_CRITERIA: ComparablesSearchCriteria = {
  time_period_months: 3,
  distance_miles: 1,
  same_schools: true,
  sqft_pct: 10,
  lot_pct: 10,
  same_beds: true,
  same_baths: true,
  year_built_diff: 10,
};

describe("CompSidebar", () => {
  it("renders search criteria form", () => {
    render(
      <CompSidebar
        criteria={DEFAULT_CRITERIA}
        onChange={vi.fn()}
        onSearch={vi.fn()}
        loading={false}
        totalCandidates={null}
      />,
    );
    expect(screen.getByText("Search Criteria")).toBeInTheDocument();
    expect(screen.getByText("Search")).toBeInTheDocument();
  });

  it("shows loading state on button", () => {
    render(
      <CompSidebar
        criteria={DEFAULT_CRITERIA}
        onChange={vi.fn()}
        onSearch={vi.fn()}
        loading={true}
        totalCandidates={null}
      />,
    );
    expect(screen.getByText("Searching...")).toBeInTheDocument();
  });

  it("displays total candidates count", () => {
    render(
      <CompSidebar
        criteria={DEFAULT_CRITERIA}
        onChange={vi.fn()}
        onSearch={vi.fn()}
        loading={false}
        totalCandidates={42}
      />,
    );
    expect(screen.getByText("42 candidates found")).toBeInTheDocument();
  });

  it("calls onSearch when button clicked", () => {
    const onSearch = vi.fn();
    render(
      <CompSidebar
        criteria={DEFAULT_CRITERIA}
        onChange={onSearch}
        onSearch={onSearch}
        loading={false}
        totalCandidates={null}
      />,
    );
    fireEvent.click(screen.getByText("Search"));
    expect(onSearch).toHaveBeenCalled();
  });

  it("calls onChange when time period is selected", () => {
    const onChange = vi.fn();
    render(
      <CompSidebar
        criteria={DEFAULT_CRITERIA}
        onChange={onChange}
        onSearch={vi.fn()}
        loading={false}
        totalCandidates={null}
      />,
    );
    fireEvent.click(screen.getByText("6 mo"));
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ time_period_months: 6 }));
  });

  it("renders toggle switches", () => {
    render(
      <CompSidebar
        criteria={DEFAULT_CRITERIA}
        onChange={vi.fn()}
        onSearch={vi.fn()}
        loading={false}
        totalCandidates={null}
      />,
    );
    expect(screen.getByText("Same school district")).toBeInTheDocument();
    expect(screen.getByText("Same bedrooms")).toBeInTheDocument();
    expect(screen.getByText("Same bathrooms")).toBeInTheDocument();
  });

  it("displays 'No limit' when slider is at max", () => {
    const maxCriteria: ComparablesSearchCriteria = {
      ...DEFAULT_CRITERIA,
      sqft_pct: 40,
      lot_pct: 40,
      year_built_diff: 20,
    };
    render(
      <CompSidebar
        criteria={maxCriteria}
        onChange={vi.fn()}
        onSearch={vi.fn()}
        loading={false}
        totalCandidates={null}
      />,
    );
    const noLimitElements = screen.getAllByText("No limit");
    expect(noLimitElements).toHaveLength(3);
  });

  it("renders range sliders", () => {
    render(
      <CompSidebar
        criteria={DEFAULT_CRITERIA}
        onChange={vi.fn()}
        onSearch={vi.fn()}
        loading={false}
        totalCandidates={null}
      />,
    );
    expect(screen.getByText("Sqft tolerance")).toBeInTheDocument();
    expect(screen.getByText("Lot size tolerance")).toBeInTheDocument();
    expect(screen.getByText("Year built range")).toBeInTheDocument();
  });
});
