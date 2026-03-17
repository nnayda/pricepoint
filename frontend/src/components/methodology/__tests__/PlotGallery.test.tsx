import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import PlotGallery from "../PlotGallery";

describe("PlotGallery", () => {
  it("renders nothing when plots is empty", () => {
    const { container } = render(<PlotGallery plots={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders images for each plot", () => {
    const plots = [
      { path: "plots/a.png", title: "Plot A" },
      { path: "plots/b.png", title: "Plot B" },
    ];
    render(<PlotGallery plots={plots} />);
    const images = screen.getAllByRole("img");
    expect(images).toHaveLength(2);
    expect(images[0]).toHaveAttribute("alt", "Plot A");
    expect(images[1]).toHaveAttribute("alt", "Plot B");
  });

  it("uses correct artifact URLs", () => {
    const plots = [{ path: "plots/test.png", title: "Test" }];
    render(<PlotGallery plots={plots} />);
    const img = screen.getByRole("img");
    expect(img).toHaveAttribute("src", "/api/model/artifact/plots/test.png");
  });

  it("images have lazy loading", () => {
    const plots = [{ path: "plots/test.png", title: "Test" }];
    render(<PlotGallery plots={plots} />);
    const img = screen.getByRole("img");
    expect(img).toHaveAttribute("loading", "lazy");
  });
});
