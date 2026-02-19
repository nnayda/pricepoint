import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import ImageGallery from "../ImageGallery";

const mockImages = [
  { url: "/images/front.jpg", alt: "Front view" },
  { url: "/images/kitchen.jpg", alt: "Kitchen" },
  { url: "/images/bedroom.jpg", alt: "Bedroom" },
  { url: "/images/backyard.jpg", alt: "Backyard" },
  { url: "/images/bathroom.jpg", alt: "Bathroom" },
];

describe("ImageGallery", () => {
  it("renders with images", () => {
    const onClose = vi.fn();
    render(<ImageGallery images={mockImages} onClose={onClose} />);
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("1 / 5")).toBeInTheDocument();
    // Main image and thumbnail both render with same alt
    const frontImages = screen.getAllByAltText("Front view");
    expect(frontImages.length).toBeGreaterThanOrEqual(1);
  });

  it("shows correct initial image based on initialIndex", () => {
    const onClose = vi.fn();
    render(<ImageGallery images={mockImages} initialIndex={2} onClose={onClose} />);
    expect(screen.getByText("3 / 5")).toBeInTheDocument();
    // The main image should be the bedroom (index 2)
    const bedroomImages = screen.getAllByAltText("Bedroom");
    const mainImg = bedroomImages.find((img) => img.classList.contains("max-h-[70vh]"));
    expect(mainImg).toHaveAttribute("src", "/images/bedroom.jpg");
  });

  it("navigates to next image when next button is clicked", () => {
    const onClose = vi.fn();
    render(<ImageGallery images={mockImages} onClose={onClose} />);
    fireEvent.click(screen.getByLabelText("Next image"));
    expect(screen.getByText("2 / 5")).toBeInTheDocument();
  });

  it("navigates to previous image when previous button is clicked", () => {
    const onClose = vi.fn();
    render(<ImageGallery images={mockImages} initialIndex={2} onClose={onClose} />);
    fireEvent.click(screen.getByLabelText("Previous image"));
    expect(screen.getByText("2 / 5")).toBeInTheDocument();
  });

  it("navigates with keyboard arrow keys", () => {
    const onClose = vi.fn();
    render(<ImageGallery images={mockImages} onClose={onClose} />);
    expect(screen.getByText("1 / 5")).toBeInTheDocument();

    fireEvent.keyDown(document, { key: "ArrowRight" });
    expect(screen.getByText("2 / 5")).toBeInTheDocument();

    fireEvent.keyDown(document, { key: "ArrowLeft" });
    expect(screen.getByText("1 / 5")).toBeInTheDocument();
  });

  it("closes gallery on Escape key", () => {
    const onClose = vi.fn();
    render(<ImageGallery images={mockImages} onClose={onClose} />);
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("closes gallery when clicking the overlay backdrop", () => {
    const onClose = vi.fn();
    render(<ImageGallery images={mockImages} onClose={onClose} />);
    const overlay = screen.getByRole("dialog");
    fireEvent.click(overlay);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("navigates to specific image when thumbnail is clicked", () => {
    const onClose = vi.fn();
    render(<ImageGallery images={mockImages} onClose={onClose} />);
    const thumbnails = screen.getAllByRole("tab");
    fireEvent.click(thumbnails[3]);
    expect(screen.getByText("4 / 5")).toBeInTheDocument();
  });

  it("returns null for empty images array", () => {
    const onClose = vi.fn();
    const { container } = render(<ImageGallery images={[]} onClose={onClose} />);
    expect(container.innerHTML).toBe("");
  });

  it("wraps from last image to first on next", () => {
    const onClose = vi.fn();
    render(<ImageGallery images={mockImages} initialIndex={4} onClose={onClose} />);
    expect(screen.getByText("5 / 5")).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText("Next image"));
    expect(screen.getByText("1 / 5")).toBeInTheDocument();
  });

  it("wraps from first image to last on previous", () => {
    const onClose = vi.fn();
    render(<ImageGallery images={mockImages} initialIndex={0} onClose={onClose} />);
    expect(screen.getByText("1 / 5")).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText("Previous image"));
    expect(screen.getByText("5 / 5")).toBeInTheDocument();
  });

  it("has proper aria labels for accessibility", () => {
    const onClose = vi.fn();
    render(<ImageGallery images={mockImages} onClose={onClose} />);
    expect(screen.getByLabelText("Image gallery")).toBeInTheDocument();
    expect(screen.getByLabelText("Close gallery")).toBeInTheDocument();
    expect(screen.getByLabelText("Next image")).toBeInTheDocument();
    expect(screen.getByLabelText("Previous image")).toBeInTheDocument();
    expect(screen.getByLabelText("Image thumbnails")).toBeInTheDocument();
  });

  it("applies lazy loading to distant thumbnails", () => {
    const onClose = vi.fn();
    render(<ImageGallery images={mockImages} onClose={onClose} />);
    // Thumbnails far from current (index 0) should be lazy loaded
    const allThumbnails = screen.getAllByRole("tab");
    // The last thumbnail image (index 4, distance > 2 from 0) should be lazy
    const lastThumbImg = allThumbnails[4].querySelector("img");
    expect(lastThumbImg).toHaveAttribute("loading", "lazy");
    // Nearby thumbnail (index 1) should be eager
    const nearbyThumbImg = allThumbnails[1].querySelector("img");
    expect(nearbyThumbImg).toHaveAttribute("loading", "eager");
  });
});
