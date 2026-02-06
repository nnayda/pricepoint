import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
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

describe("SectionSidebar", () => {
  it("renders the navigation", () => {
    render(<SectionSidebar sections={sections} />);
    expect(screen.getByLabelText("Page sections")).toBeInTheDocument();
  });

  it("renders links for each section", () => {
    render(<SectionSidebar sections={sections} />);
    expect(screen.getByLabelText("Header")).toBeInTheDocument();
    expect(screen.getByLabelText("Valuation")).toBeInTheDocument();
    expect(screen.getByLabelText("Description")).toBeInTheDocument();
  });

  it("renders section icons", () => {
    render(<SectionSidebar sections={sections} />);
    expect(screen.getByText("H")).toBeInTheDocument();
    expect(screen.getByText("V")).toBeInTheDocument();
    expect(screen.getByText("D")).toBeInTheDocument();
  });

  it("links have correct href anchors", () => {
    render(<SectionSidebar sections={sections} />);
    const headerLink = screen.getByLabelText("Header");
    expect(headerLink).toHaveAttribute("href", "#section-1");
    const valuationLink = screen.getByLabelText("Valuation");
    expect(valuationLink).toHaveAttribute("href", "#section-2");
  });

  it("active section link is styled differently", () => {
    render(<SectionSidebar sections={sections} />);
    const activeLink = screen.getByLabelText("Header");
    expect(activeLink.className).toContain("bg-brand-blue");
  });

  it("non-active section links are not styled as active", () => {
    render(<SectionSidebar sections={sections} />);
    const inactiveLink = screen.getByLabelText("Valuation");
    expect(inactiveLink.className).not.toContain("bg-brand-blue");
  });

  it("has no accessibility violations", async () => {
    const { container } = render(<SectionSidebar sections={sections} />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
