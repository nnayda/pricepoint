import { describe, it, expect, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { axe } from "vitest-axe";
import SectionSidebar from "../SectionSidebar";

// Mock useActiveSection
vi.mock("../../../hooks/useActiveSection", () => ({
  useActiveSection: vi.fn(() => "section-1"),
}));

const sections = [
  { id: "section-1", icon: "H", tooltip: "Header" },
  { id: "section-2", icon: "V", tooltip: "Valuation" },
  { id: "section-3", icon: "D", tooltip: "Description" },
];

/** Helper to query within the desktop sidebar nav. */
function getDesktopNav() {
  return screen.getByLabelText("Page sections");
}

describe("SectionSidebar", () => {
  it("renders the desktop navigation", () => {
    render(<SectionSidebar sections={sections} />);
    expect(getDesktopNav()).toBeInTheDocument();
  });

  it("renders the mobile navigation", () => {
    render(<SectionSidebar sections={sections} />);
    expect(screen.getByLabelText("Page sections mobile")).toBeInTheDocument();
  });

  it("renders links for each section", () => {
    render(<SectionSidebar sections={sections} />);
    const nav = getDesktopNav();
    expect(within(nav).getByLabelText("Header")).toBeInTheDocument();
    expect(within(nav).getByLabelText("Valuation")).toBeInTheDocument();
    expect(within(nav).getByLabelText("Description")).toBeInTheDocument();
  });

  it("renders section icons", () => {
    render(<SectionSidebar sections={sections} />);
    const nav = getDesktopNav();
    expect(within(nav).getByText("H")).toBeInTheDocument();
    expect(within(nav).getByText("V")).toBeInTheDocument();
    expect(within(nav).getByText("D")).toBeInTheDocument();
  });

  it("links have correct href anchors", () => {
    render(<SectionSidebar sections={sections} />);
    const nav = getDesktopNav();
    const headerLink = within(nav).getByLabelText("Header");
    expect(headerLink).toHaveAttribute("href", "#section-1");
    const valuationLink = within(nav).getByLabelText("Valuation");
    expect(valuationLink).toHaveAttribute("href", "#section-2");
  });

  it("active section link is styled differently", () => {
    render(<SectionSidebar sections={sections} />);
    const nav = getDesktopNav();
    const activeLink = within(nav).getByLabelText("Header");
    expect(activeLink.className).toContain("bg-brand-blue");
  });

  it("non-active section links are not styled as active", () => {
    render(<SectionSidebar sections={sections} />);
    const nav = getDesktopNav();
    const inactiveLink = within(nav).getByLabelText("Valuation");
    expect(inactiveLink.className).not.toContain("bg-brand-blue");
  });

  it("has no accessibility violations", async () => {
    const { container } = render(<SectionSidebar sections={sections} />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
