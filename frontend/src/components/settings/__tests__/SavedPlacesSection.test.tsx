import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import SavedPlacesSection from "../SavedPlacesSection";
import type { SavedPoiResponse } from "../../../types";

vi.mock("../../../hooks/useSavedPois", () => ({
  usePoiAutocomplete: () => ({ results: [], isLoading: false }),
}));

const basePoi: SavedPoiResponse = {
  id: 1,
  match_type: "brand",
  match_value: "Costco",
  display_name: "Costco",
  category: "store",
  user_category: null,
  marker_color: null,
  marker_image_url: null,
  created_at: "2025-06-01T00:00:00Z",
};

const coloredPoi: SavedPoiResponse = {
  ...basePoi,
  id: 2,
  display_name: "Trader Joe's",
  match_value: "Trader Joe's",
  marker_color: "#10B981",
  user_category: "Groceries",
  marker_image_url: "https://example.com/logo.png",
};

describe("SavedPlacesSection", () => {
  const onAdd = vi.fn().mockResolvedValue(undefined);
  const onRemove = vi.fn().mockResolvedValue(undefined);
  const onUpdate = vi.fn().mockResolvedValue(undefined);

  it("renders saved POIs with names", () => {
    render(
      <SavedPlacesSection
        pois={[basePoi, coloredPoi]}
        onAdd={onAdd}
        onRemove={onRemove}
        onUpdate={onUpdate}
      />,
    );
    expect(screen.getByText("Costco")).toBeInTheDocument();
    expect(screen.getByText("Trader Joe's")).toBeInTheDocument();
  });

  it("renders color picker swatch", () => {
    render(
      <SavedPlacesSection pois={[basePoi]} onAdd={onAdd} onRemove={onRemove} onUpdate={onUpdate} />,
    );
    const swatch = screen.getByLabelText("Pick marker color");
    expect(swatch).toBeInTheDocument();
  });

  it("color picker opens and selecting calls onUpdate", () => {
    render(
      <SavedPlacesSection pois={[basePoi]} onAdd={onAdd} onRemove={onRemove} onUpdate={onUpdate} />,
    );
    const swatch = screen.getByLabelText("Pick marker color");
    fireEvent.click(swatch);
    // Should show palette — pick a color
    const colorButton = screen.getByLabelText("Color #EF4444");
    fireEvent.click(colorButton);
    expect(onUpdate).toHaveBeenCalledWith(1, { marker_color: "#EF4444" });
  });

  it("shows + Logo button and opens image URL input on click", () => {
    render(
      <SavedPlacesSection pois={[basePoi]} onAdd={onAdd} onRemove={onRemove} onUpdate={onUpdate} />,
    );
    const logoBtn = screen.getByText("+ Logo");
    fireEvent.click(logoBtn);
    const input = screen.getByPlaceholderText("https://logo.url/img.png");
    expect(input).toBeInTheDocument();
  });

  it("shows logo preview when marker_image_url is set", () => {
    render(
      <SavedPlacesSection
        pois={[coloredPoi]}
        onAdd={onAdd}
        onRemove={onRemove}
        onUpdate={onUpdate}
      />,
    );
    expect(screen.getByText("Logo")).toBeInTheDocument();
  });

  it("renders category group input", () => {
    render(
      <SavedPlacesSection pois={[basePoi]} onAdd={onAdd} onRemove={onRemove} onUpdate={onUpdate} />,
    );
    expect(screen.getByText("Group:")).toBeInTheDocument();
  });

  it("category input blur calls onUpdate", () => {
    render(
      <SavedPlacesSection pois={[basePoi]} onAdd={onAdd} onRemove={onRemove} onUpdate={onUpdate} />,
    );
    const catInput = screen.getByPlaceholderText("Default");
    fireEvent.change(catInput, { target: { value: "Groceries" } });
    fireEvent.blur(catInput);
    expect(onUpdate).toHaveBeenCalledWith(1, { user_category: "Groceries" });
  });

  it("remove button calls onRemove", async () => {
    render(
      <SavedPlacesSection pois={[basePoi]} onAdd={onAdd} onRemove={onRemove} onUpdate={onUpdate} />,
    );
    const removeBtn = screen.getByLabelText("Remove Costco");
    fireEvent.click(removeBtn);
    expect(onRemove).toHaveBeenCalledWith(1);
  });

  it("does not show customization row when onUpdate is not provided", () => {
    render(<SavedPlacesSection pois={[basePoi]} onAdd={onAdd} onRemove={onRemove} />);
    expect(screen.queryByText("Group:")).not.toBeInTheDocument();
  });
});
