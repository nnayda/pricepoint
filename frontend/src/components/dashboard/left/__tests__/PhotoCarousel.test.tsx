import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import PhotoCarousel from "../PhotoCarousel";

const TEST_IMAGES = [
  "https://example.com/photo1.jpg",
  "https://example.com/photo2.jpg",
  "https://example.com/photo3.jpg",
];

describe("PhotoCarousel", () => {
  beforeEach(() => {
    document.body.style.overflow = "";
  });

  afterEach(() => {
    document.body.style.overflow = "";
  });

  it("renders the carousel with images", () => {
    render(<PhotoCarousel images={TEST_IMAGES} />);
    expect(screen.getByAltText("Property photo 1 of 3")).toBeInTheDocument();
    expect(screen.getByText("1 / 3")).toBeInTheDocument();
  });

  it("navigates to next and previous photos", () => {
    render(<PhotoCarousel images={TEST_IMAGES} />);
    fireEvent.click(screen.getByLabelText("Next photo"));
    expect(screen.getByAltText("Property photo 2 of 3")).toBeInTheDocument();
    expect(screen.getByText("2 / 3")).toBeInTheDocument();

    fireEvent.click(screen.getByLabelText("Previous photo"));
    expect(screen.getByAltText("Property photo 1 of 3")).toBeInTheDocument();
  });

  it("wraps around when navigating past the last image", () => {
    render(<PhotoCarousel images={TEST_IMAGES} />);
    fireEvent.click(screen.getByLabelText("Next photo"));
    fireEvent.click(screen.getByLabelText("Next photo"));
    fireEvent.click(screen.getByLabelText("Next photo"));
    expect(screen.getByAltText("Property photo 1 of 3")).toBeInTheDocument();
  });

  it("wraps around when navigating before the first image", () => {
    render(<PhotoCarousel images={TEST_IMAGES} />);
    fireEvent.click(screen.getByLabelText("Previous photo"));
    expect(screen.getByAltText("Property photo 3 of 3")).toBeInTheDocument();
  });

  it("opens fullscreen overlay on button click", () => {
    render(<PhotoCarousel images={TEST_IMAGES} />);
    fireEvent.click(screen.getByLabelText("Open fullscreen gallery"));
    expect(screen.getByLabelText("Close fullscreen")).toBeInTheDocument();
    expect(screen.getByText(/Press Esc to close/)).toBeInTheDocument();
  });

  it("sets body overflow to hidden when fullscreen is open", () => {
    render(<PhotoCarousel images={TEST_IMAGES} />);
    expect(document.body.style.overflow).toBe("");

    fireEvent.click(screen.getByLabelText("Open fullscreen gallery"));
    expect(document.body.style.overflow).toBe("hidden");
  });

  it("restores body overflow when fullscreen is closed", () => {
    render(<PhotoCarousel images={TEST_IMAGES} />);
    fireEvent.click(screen.getByLabelText("Open fullscreen gallery"));
    expect(document.body.style.overflow).toBe("hidden");

    fireEvent.click(screen.getByLabelText("Close fullscreen"));
    expect(document.body.style.overflow).toBe("");
  });

  it("closes fullscreen on Escape key", () => {
    render(<PhotoCarousel images={TEST_IMAGES} />);
    fireEvent.click(screen.getByLabelText("Open fullscreen gallery"));
    expect(screen.getByLabelText("Close fullscreen")).toBeInTheDocument();

    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByLabelText("Close fullscreen")).not.toBeInTheDocument();
    expect(document.body.style.overflow).toBe("");
  });

  it("closes fullscreen when clicking the backdrop", () => {
    render(<PhotoCarousel images={TEST_IMAGES} />);
    fireEvent.click(screen.getByLabelText("Open fullscreen gallery"));

    // Click the backdrop (the fixed overlay div)
    const backdrop = screen.getByText(/Press Esc to close/).closest(".fixed") as HTMLElement;
    fireEvent.click(backdrop);
    expect(screen.queryByLabelText("Close fullscreen")).not.toBeInTheDocument();
  });

  it("renders fullscreen overlay with z-index 10000", () => {
    render(<PhotoCarousel images={TEST_IMAGES} />);
    fireEvent.click(screen.getByLabelText("Open fullscreen gallery"));

    const overlay = screen.getByText(/Press Esc to close/).closest(".fixed") as HTMLElement;
    expect(overlay.style.zIndex).toBe("10000");
  });

  it("navigates photos with arrow keys in fullscreen", () => {
    render(<PhotoCarousel images={TEST_IMAGES} />);
    fireEvent.click(screen.getByLabelText("Open fullscreen gallery"));

    fireEvent.keyDown(document, { key: "ArrowRight" });
    expect(screen.getByAltText("Photo 2 of 3")).toBeInTheDocument();

    fireEvent.keyDown(document, { key: "ArrowLeft" });
    expect(screen.getByAltText("Photo 1 of 3")).toBeInTheDocument();
  });

  it("restores body overflow on unmount while fullscreen", () => {
    const { unmount } = render(<PhotoCarousel images={TEST_IMAGES} />);
    fireEvent.click(screen.getByLabelText("Open fullscreen gallery"));
    expect(document.body.style.overflow).toBe("hidden");

    unmount();
    expect(document.body.style.overflow).toBe("");
  });

  it("renders dot indicators for each image", () => {
    render(<PhotoCarousel images={TEST_IMAGES} />);
    for (let i = 0; i < TEST_IMAGES.length; i++) {
      expect(
        screen.getByLabelText(`Go to photo ${i + 1} of ${TEST_IMAGES.length}`),
      ).toBeInTheDocument();
    }
  });

  it("navigates to specific photo via dot indicator", () => {
    render(<PhotoCarousel images={TEST_IMAGES} />);
    fireEvent.click(screen.getByLabelText("Go to photo 3 of 3"));
    expect(screen.getByAltText("Property photo 3 of 3")).toBeInTheDocument();
  });
});
