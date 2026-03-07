import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import KeyFactsCard from "../KeyFactsCard";
import type { DashboardProperty, DashboardValuation } from "../../../../types";

const property: DashboardProperty = {
  address: "123 Main St",
  city: "Cary",
  state: "NC",
  zip_code: "27513",
  neighborhood: "Test",
  lat: 35.79,
  lon: -78.78,
  bedrooms: 4,
  bathrooms: 3,
  sqft: 2500,
  lot_size_sqft: 10000,
  year_built: 2005,
  property_type: "Single Family",
  stories: 2,
  garage_spaces: 2,
  description: "A nice house",
  ai_summary: "",
  highlights: [],
  images: [],
  listing_status: "For Sale",
  days_on_market: 10,
  mls_number: "MLS123",
  listed_date: "2025-01-01",
};

const valuation: DashboardValuation = {
  listed_price: 450000,
  predicted_value: 440000,
  confidence_low: 420000,
  confidence_high: 460000,
  redfin_estimate: 445000,
  tax_assessment: 400000,
  price_per_sqft: 180,
  model_version: "v1",
  prediction_date: "2025-01-01",
  verdict: "Fair",
  verdict_detail: "Fair price",
};

describe("KeyFactsCard save button", () => {
  it("renders Save text when not saved", () => {
    render(
      <KeyFactsCard
        property={property}
        valuation={valuation}
        listingId={42}
        isSaved={false}
        isSaveLoading={false}
        onSaveToggle={() => {}}
      />,
    );
    expect(screen.getByRole("button", { name: "Save listing" })).toHaveTextContent("Save");
  });

  it("renders Saved text when saved", () => {
    render(
      <KeyFactsCard
        property={property}
        valuation={valuation}
        listingId={42}
        isSaved={true}
        isSaveLoading={false}
        onSaveToggle={() => {}}
      />,
    );
    const btn = screen.getByRole("button", { name: "Unsave listing" });
    expect(btn).toHaveTextContent("Saved");
  });

  it("renders Saving... text when loading", () => {
    render(
      <KeyFactsCard
        property={property}
        valuation={valuation}
        listingId={42}
        isSaved={false}
        isSaveLoading={true}
        onSaveToggle={() => {}}
      />,
    );
    expect(screen.getByRole("button", { name: "Save listing" })).toHaveTextContent("Saving...");
  });

  it("disables button when loading", () => {
    render(
      <KeyFactsCard
        property={property}
        valuation={valuation}
        listingId={42}
        isSaved={false}
        isSaveLoading={true}
        onSaveToggle={() => {}}
      />,
    );
    expect(screen.getByRole("button", { name: "Save listing" })).toBeDisabled();
  });

  it("disables button when listingId is null", () => {
    render(
      <KeyFactsCard
        property={property}
        valuation={valuation}
        listingId={null}
        isSaved={false}
        isSaveLoading={false}
        onSaveToggle={() => {}}
      />,
    );
    expect(screen.getByRole("button", { name: "Save listing" })).toBeDisabled();
  });

  it("calls onSaveToggle when clicked", () => {
    const toggle = vi.fn();
    render(
      <KeyFactsCard
        property={property}
        valuation={valuation}
        listingId={42}
        isSaved={false}
        isSaveLoading={false}
        onSaveToggle={toggle}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Save listing" }));
    expect(toggle).toHaveBeenCalledTimes(1);
  });

  it("fills heart SVG when saved", () => {
    render(
      <KeyFactsCard
        property={property}
        valuation={valuation}
        listingId={42}
        isSaved={true}
        isSaveLoading={false}
        onSaveToggle={() => {}}
      />,
    );
    const btn = screen.getByRole("button", { name: "Unsave listing" });
    const svg = btn.querySelector("svg");
    expect(svg?.getAttribute("fill")).toBe("currentColor");
  });

  it("heart SVG has no fill when not saved", () => {
    render(
      <KeyFactsCard
        property={property}
        valuation={valuation}
        listingId={42}
        isSaved={false}
        isSaveLoading={false}
        onSaveToggle={() => {}}
      />,
    );
    const btn = screen.getByRole("button", { name: "Save listing" });
    const svg = btn.querySelector("svg");
    expect(svg?.getAttribute("fill")).toBe("none");
  });
});

describe("KeyFactsCard share button", () => {
  it("copies URL to clipboard when navigator.share is unavailable", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText }, share: undefined });

    render(
      <KeyFactsCard
        property={property}
        valuation={valuation}
        listingId={42}
        isSaved={false}
        isSaveLoading={false}
        onSaveToggle={() => {}}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Share property" }));

    await waitFor(() => {
      expect(writeText).toHaveBeenCalledWith(window.location.href);
    });
    expect(screen.getByText("Link copied!")).toBeInTheDocument();
  });

  it("uses navigator.share when available", async () => {
    const shareFn = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { share: shareFn });

    render(
      <KeyFactsCard
        property={property}
        valuation={valuation}
        listingId={42}
        isSaved={false}
        isSaveLoading={false}
        onSaveToggle={() => {}}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Share property" }));

    await waitFor(() => {
      expect(shareFn).toHaveBeenCalledWith(
        expect.objectContaining({
          url: window.location.href,
          title: "123 Main St — Cary, NC 27513",
        }),
      );
    });

    // Clean up
    Object.assign(navigator, { share: undefined });
  });
});

describe("KeyFactsCard Redfin link", () => {
  it("renders View on Redfin link when redfin_url is set", () => {
    const withUrl = { ...property, redfin_url: "https://www.redfin.com/NC/Cary/123/home/456" };
    render(
      <KeyFactsCard
        property={withUrl}
        valuation={valuation}
        listingId={42}
        isSaved={false}
        isSaveLoading={false}
        onSaveToggle={() => {}}
      />,
    );
    const link = screen.getByRole("link", { name: "View on Redfin" });
    expect(link).toHaveAttribute("href", "https://www.redfin.com/NC/Cary/123/home/456");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("does not render Redfin link when redfin_url is absent", () => {
    render(
      <KeyFactsCard
        property={property}
        valuation={valuation}
        listingId={42}
        isSaved={false}
        isSaveLoading={false}
        onSaveToggle={() => {}}
      />,
    );
    expect(screen.queryByRole("link", { name: "View on Redfin" })).not.toBeInTheDocument();
  });
});
