import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "vitest-axe";
import MapTabBar from "../MapTabBar";
import type { MapTab } from "../../../types";

const ALL_TABS: MapTab[] = ["crime-density", "crime-incidents", "pois", "greenspace", "utilities"];

describe("MapTabBar", () => {
  it("renders a tablist", () => {
    render(<MapTabBar tabs={ALL_TABS} activeTab="crime-density" onTabChange={vi.fn()} />);
    expect(screen.getByRole("tablist", { name: "Map layers" })).toBeInTheDocument();
  });

  it("renders a tab for each entry", () => {
    render(<MapTabBar tabs={ALL_TABS} activeTab="crime-density" onTabChange={vi.fn()} />);
    const tabs = screen.getAllByRole("tab");
    expect(tabs).toHaveLength(5);
  });

  it("renders human-readable labels", () => {
    render(<MapTabBar tabs={ALL_TABS} activeTab="crime-density" onTabChange={vi.fn()} />);
    expect(screen.getByText("Crime Density")).toBeInTheDocument();
    expect(screen.getByText("Crime Incidents")).toBeInTheDocument();
    expect(screen.getByText("Points of Interest")).toBeInTheDocument();
    expect(screen.getByText("Greenspace")).toBeInTheDocument();
    expect(screen.getByText("Utilities")).toBeInTheDocument();
  });

  it("marks the active tab with aria-selected=true", () => {
    render(<MapTabBar tabs={ALL_TABS} activeTab="pois" onTabChange={vi.fn()} />);
    const poisTab = screen.getByText("Points of Interest");
    expect(poisTab).toHaveAttribute("aria-selected", "true");
  });

  it("marks non-active tabs with aria-selected=false", () => {
    render(<MapTabBar tabs={ALL_TABS} activeTab="pois" onTabChange={vi.fn()} />);
    const crimeTab = screen.getByText("Crime Density");
    expect(crimeTab).toHaveAttribute("aria-selected", "false");
  });

  it("active tab has brand-blue styling", () => {
    render(<MapTabBar tabs={ALL_TABS} activeTab="greenspace" onTabChange={vi.fn()} />);
    const tab = screen.getByText("Greenspace");
    expect(tab.className).toContain("bg-brand-blue");
  });

  it("inactive tab does not have brand-blue styling", () => {
    render(<MapTabBar tabs={ALL_TABS} activeTab="greenspace" onTabChange={vi.fn()} />);
    const tab = screen.getByText("Utilities");
    expect(tab.className).not.toContain("bg-brand-blue");
  });

  it("calls onTabChange when a tab is clicked", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<MapTabBar tabs={ALL_TABS} activeTab="crime-density" onTabChange={onChange} />);

    await user.click(screen.getByText("Greenspace"));
    expect(onChange).toHaveBeenCalledWith("greenspace");
  });

  it("sets aria-controls to the panel id", () => {
    render(<MapTabBar tabs={ALL_TABS} activeTab="crime-density" onTabChange={vi.fn()} />);
    const tab = screen.getByText("Crime Density");
    expect(tab).toHaveAttribute("aria-controls", "map-panel-crime-density");
  });

  it("renders subset of tabs when fewer are passed", () => {
    const subset: MapTab[] = ["pois", "utilities"];
    render(<MapTabBar tabs={subset} activeTab="pois" onTabChange={vi.fn()} />);
    const tabs = screen.getAllByRole("tab");
    expect(tabs).toHaveLength(2);
  });

  it("has no accessibility violations", async () => {
    // Add panel elements that aria-controls references
    ALL_TABS.forEach((tab) => {
      const panel = document.createElement("div");
      panel.id = `map-panel-${tab}`;
      document.body.appendChild(panel);
    });

    const { container } = render(
      <MapTabBar tabs={ALL_TABS} activeTab="crime-density" onTabChange={vi.fn()} />,
    );
    const results = await axe(container);

    // Clean up panel elements
    ALL_TABS.forEach((tab) => {
      const panel = document.getElementById(`map-panel-${tab}`);
      if (panel) document.body.removeChild(panel);
    });

    expect(results).toHaveNoViolations();
  });
});
