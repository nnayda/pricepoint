import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import MapTabBar from "../MapTabBar";
import type { MapTab } from "../../../types";

const ALL_TABS: MapTab[] = ["crime-density", "crime-incidents", "pois", "greenspace", "utilities"];

describe("MapTabBar mobile", () => {
  it("tab bar container has overflow-x-auto class", () => {
    render(<MapTabBar tabs={ALL_TABS} activeTab="crime-density" onTabChange={vi.fn()} />);
    const tablist = screen.getByRole("tablist");
    expect(tablist.className).toContain("overflow-x-auto");
  });

  it("all tabs are rendered", () => {
    render(<MapTabBar tabs={ALL_TABS} activeTab="crime-density" onTabChange={vi.fn()} />);
    const tabs = screen.getAllByRole("tab");
    expect(tabs).toHaveLength(5);
  });

  it("each tab has flex-shrink-0 class", () => {
    render(<MapTabBar tabs={ALL_TABS} activeTab="crime-density" onTabChange={vi.fn()} />);
    const tabs = screen.getAllByRole("tab");
    tabs.forEach((tab) => {
      expect(tab.className).toContain("flex-shrink-0");
    });
  });

  it("tabs have short labels for mobile (sm:hidden spans)", () => {
    render(<MapTabBar tabs={ALL_TABS} activeTab="crime-density" onTabChange={vi.fn()} />);
    // Each tab should have two spans: one with sm:hidden (short) and one with hidden sm:inline (full)
    const tabs = screen.getAllByRole("tab");
    tabs.forEach((tab) => {
      const spans = tab.querySelectorAll("span");
      expect(spans).toHaveLength(2);
      expect(spans[0].className).toContain("sm:inline");
      expect(spans[1].className).toContain("sm:hidden");
    });
  });
});
