import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "vitest-axe";
import SearchBar from "../SearchBar";
import type { GeocodeResult } from "../../../types";

const mockResults: GeocodeResult[] = [
  {
    display_name: "123 Main St, Philadelphia, PA",
    lat: 39.9526,
    lon: -75.1652,
    place_id: 1001,
    osm_type: "way",
    osm_id: 5001,
    boundingbox: [39.95, 39.96, -75.17, -75.16],
  },
  {
    display_name: "123 Main St, Springfield, IL",
    lat: 39.7817,
    lon: -89.6501,
    place_id: 1002,
    osm_type: "way",
    osm_id: 5002,
    boundingbox: [39.78, 39.79, -89.66, -89.64],
  },
];

const mockUseGeocode = vi.fn(() => ({
  results: [] as GeocodeResult[],
  loading: false,
  error: null as string | null,
}));

vi.mock("../../../hooks/useGeocode", () => ({
  useGeocode: (...args: unknown[]) => mockUseGeocode(...(args as [])),
}));

describe("SearchBar", () => {
  beforeEach(() => {
    mockUseGeocode.mockReturnValue({ results: [], loading: false, error: null });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // -- Variants --

  describe("variants", () => {
    it("renders with the default placeholder", () => {
      render(<SearchBar onSelect={vi.fn()} />);
      expect(screen.getByPlaceholderText("Search for an address...")).toBeInTheDocument();
    });

    it("renders with a custom placeholder", () => {
      render(<SearchBar onSelect={vi.fn()} placeholder="Find a property" />);
      expect(screen.getByPlaceholderText("Find a property")).toBeInTheDocument();
    });

    it("renders a search icon with aria-hidden", () => {
      render(<SearchBar onSelect={vi.fn()} />);
      const svg = document.querySelector("svg");
      expect(svg).toBeInTheDocument();
      expect(svg).toHaveAttribute("aria-hidden", "true");
    });
  });

  // -- Autocomplete flow --

  describe("autocomplete flow", () => {
    it("does not show dropdown for queries shorter than 3 characters", async () => {
      const user = userEvent.setup();
      render(<SearchBar onSelect={vi.fn()} />);
      const input = screen.getByRole("combobox");

      await user.type(input, "ab");

      expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    });

    it("shows dropdown with results after typing 3+ characters", async () => {
      mockUseGeocode.mockReturnValue({ results: mockResults, loading: false, error: null });
      const user = userEvent.setup();

      render(<SearchBar onSelect={vi.fn()} />);
      const input = screen.getByRole("combobox");

      await user.type(input, "123 Main");

      expect(screen.getByRole("listbox")).toBeInTheDocument();
      expect(screen.getByText("123 Main St, Philadelphia, PA")).toBeInTheDocument();
      expect(screen.getByText("123 Main St, Springfield, IL")).toBeInTheDocument();
    });

    it("fills the input with the selected result display name and closes dropdown", async () => {
      mockUseGeocode.mockReturnValue({ results: mockResults, loading: false, error: null });
      const user = userEvent.setup();

      render(<SearchBar onSelect={vi.fn()} />);
      const input = screen.getByRole("combobox");

      await user.type(input, "123 Main");

      const option = screen.getByText("123 Main St, Philadelphia, PA");
      await user.click(option);

      expect(input).toHaveValue("123 Main St, Philadelphia, PA");
      expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    });

    it("reopens dropdown on focus when results exist", async () => {
      mockUseGeocode.mockReturnValue({ results: mockResults, loading: false, error: null });
      const user = userEvent.setup();

      render(
        <div>
          <button>Other</button>
          <SearchBar onSelect={vi.fn()} />
        </div>,
      );
      const input = screen.getByRole("combobox");

      await user.type(input, "123 Main");
      expect(screen.getByRole("listbox")).toBeInTheDocument();

      await user.click(screen.getByText("Other"));
      expect(screen.queryByRole("listbox")).not.toBeInTheDocument();

      await user.click(input);
      expect(screen.getByRole("listbox")).toBeInTheDocument();
    });

    it("highlights option on mouse enter", async () => {
      mockUseGeocode.mockReturnValue({ results: mockResults, loading: false, error: null });
      const user = userEvent.setup();

      render(<SearchBar onSelect={vi.fn()} />);
      const input = screen.getByRole("combobox");

      await user.type(input, "123 Main");

      const secondOption = screen.getByRole("option", { name: "123 Main St, Springfield, IL" });
      await user.hover(secondOption);

      expect(secondOption).toHaveAttribute("aria-selected", "true");
    });
  });

  // -- Keyboard navigation --

  describe("keyboard navigation", () => {
    it("navigates down through results with ArrowDown", async () => {
      mockUseGeocode.mockReturnValue({ results: mockResults, loading: false, error: null });
      const user = userEvent.setup();

      render(<SearchBar onSelect={vi.fn()} />);
      const input = screen.getByRole("combobox");

      await user.type(input, "123 Main");

      await user.keyboard("{ArrowDown}");
      expect(screen.getByRole("option", { name: "123 Main St, Philadelphia, PA" })).toHaveAttribute(
        "aria-selected",
        "true",
      );

      await user.keyboard("{ArrowDown}");
      expect(screen.getByRole("option", { name: "123 Main St, Springfield, IL" })).toHaveAttribute(
        "aria-selected",
        "true",
      );
    });

    it("navigates up through results with ArrowUp", async () => {
      mockUseGeocode.mockReturnValue({ results: mockResults, loading: false, error: null });
      const user = userEvent.setup();

      render(<SearchBar onSelect={vi.fn()} />);
      const input = screen.getByRole("combobox");

      await user.type(input, "123 Main");

      // Move down to second item
      await user.keyboard("{ArrowDown}{ArrowDown}");
      expect(screen.getByRole("option", { name: "123 Main St, Springfield, IL" })).toHaveAttribute(
        "aria-selected",
        "true",
      );

      // Move back up to first
      await user.keyboard("{ArrowUp}");
      expect(screen.getByRole("option", { name: "123 Main St, Philadelphia, PA" })).toHaveAttribute(
        "aria-selected",
        "true",
      );
    });

    it("selects active result with Enter", async () => {
      mockUseGeocode.mockReturnValue({ results: mockResults, loading: false, error: null });
      const handleSelect = vi.fn();
      const user = userEvent.setup();

      render(<SearchBar onSelect={handleSelect} />);
      const input = screen.getByRole("combobox");

      await user.type(input, "123 Main");
      await user.keyboard("{ArrowDown}");
      await user.keyboard("{Enter}");

      expect(handleSelect).toHaveBeenCalledWith(mockResults[0]);
    });

    it("auto-selects first result on Enter when no result is highlighted", async () => {
      mockUseGeocode.mockReturnValue({ results: mockResults, loading: false, error: null });
      const handleSelect = vi.fn();
      const user = userEvent.setup();

      render(<SearchBar onSelect={handleSelect} />);
      const input = screen.getByRole("combobox");

      await user.type(input, "123 Main");
      // Press Enter without navigating to any option
      await user.keyboard("{Enter}");

      expect(handleSelect).toHaveBeenCalledWith(mockResults[0]);
    });

    it("closes dropdown and blurs input on Escape", async () => {
      mockUseGeocode.mockReturnValue({ results: mockResults, loading: false, error: null });
      const user = userEvent.setup();

      render(<SearchBar onSelect={vi.fn()} />);
      const input = screen.getByRole("combobox");

      await user.type(input, "123 Main");
      expect(screen.getByRole("listbox")).toBeInTheDocument();

      await user.keyboard("{Escape}");
      expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
      expect(input).not.toHaveFocus();
    });

    it("does not navigate past the last result with ArrowDown", async () => {
      mockUseGeocode.mockReturnValue({ results: mockResults, loading: false, error: null });
      const user = userEvent.setup();

      render(<SearchBar onSelect={vi.fn()} />);
      const input = screen.getByRole("combobox");

      await user.type(input, "123 Main");

      // Press ArrowDown 3 times (more than number of results)
      await user.keyboard("{ArrowDown}{ArrowDown}{ArrowDown}");
      expect(screen.getByRole("option", { name: "123 Main St, Springfield, IL" })).toHaveAttribute(
        "aria-selected",
        "true",
      );
    });

    it("does not navigate before index -1 with ArrowUp", async () => {
      mockUseGeocode.mockReturnValue({ results: mockResults, loading: false, error: null });
      const user = userEvent.setup();

      render(<SearchBar onSelect={vi.fn()} />);
      const input = screen.getByRole("combobox");

      await user.type(input, "123 Main");

      // ArrowUp when already at -1 should keep all unselected
      await user.keyboard("{ArrowUp}");
      const options = screen.getAllByRole("option");
      options.forEach((option) => {
        expect(option).toHaveAttribute("aria-selected", "false");
      });
    });

    it("ArrowUp from first item deselects all options", async () => {
      mockUseGeocode.mockReturnValue({ results: mockResults, loading: false, error: null });
      const user = userEvent.setup();

      render(<SearchBar onSelect={vi.fn()} />);
      const input = screen.getByRole("combobox");

      await user.type(input, "123 Main");

      // Move down to first, then back up
      await user.keyboard("{ArrowDown}");
      expect(screen.getByRole("option", { name: "123 Main St, Philadelphia, PA" })).toHaveAttribute(
        "aria-selected",
        "true",
      );

      await user.keyboard("{ArrowUp}");
      const options = screen.getAllByRole("option");
      options.forEach((option) => {
        expect(option).toHaveAttribute("aria-selected", "false");
      });
    });
  });

  // -- Enter key submission --

  describe("Enter key submission", () => {
    it("selects highlighted result on Enter", async () => {
      mockUseGeocode.mockReturnValue({ results: mockResults, loading: false, error: null });
      const handleSelect = vi.fn();
      const user = userEvent.setup();

      render(<SearchBar onSelect={handleSelect} />);
      const input = screen.getByRole("combobox");

      await user.type(input, "123 Main");
      await user.keyboard("{ArrowDown}{ArrowDown}{Enter}");

      expect(handleSelect).toHaveBeenCalledWith(mockResults[1]);
    });

    it("auto-selects first result on Enter when dropdown is closed but results exist", async () => {
      mockUseGeocode.mockReturnValue({ results: mockResults, loading: false, error: null });
      const handleSelect = vi.fn();
      const user = userEvent.setup();

      render(
        <div>
          <button>Outside</button>
          <SearchBar onSelect={handleSelect} />
        </div>,
      );
      const input = screen.getByRole("combobox");

      await user.type(input, "123 Main");
      // Close dropdown by clicking outside
      await user.click(screen.getByText("Outside"));
      expect(screen.queryByRole("listbox")).not.toBeInTheDocument();

      // Focus input and press Enter
      await user.click(input);
      await user.keyboard("{Enter}");

      expect(handleSelect).toHaveBeenCalledWith(mockResults[0]);
    });

    it("shows not-found error on Enter with no results", async () => {
      mockUseGeocode.mockReturnValue({ results: [], loading: false, error: null });
      const handleSelect = vi.fn();
      const user = userEvent.setup();

      render(<SearchBar onSelect={handleSelect} />);
      const input = screen.getByRole("combobox");

      await user.type(input, "xyznonexistent");
      await user.keyboard("{Enter}");

      expect(handleSelect).not.toHaveBeenCalled();
      expect(screen.getByRole("alert")).toHaveTextContent(
        "Address not found. Try a different search.",
      );
    });

    it("does not show not-found error on Enter with query shorter than 3 characters", async () => {
      mockUseGeocode.mockReturnValue({ results: [], loading: false, error: null });
      const user = userEvent.setup();

      render(<SearchBar onSelect={vi.fn()} />);
      const input = screen.getByRole("combobox");

      await user.type(input, "ab");
      await user.keyboard("{Enter}");

      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    });

    it("does not show not-found error on Enter while loading", async () => {
      mockUseGeocode.mockReturnValue({ results: [], loading: true, error: null });
      const user = userEvent.setup();

      render(<SearchBar onSelect={vi.fn()} />);
      const input = screen.getByRole("combobox");

      await user.type(input, "123 Main");
      await user.keyboard("{Enter}");

      expect(
        screen.queryByText("Address not found. Try a different search."),
      ).not.toBeInTheDocument();
    });

    it("clears not-found error when user types again", async () => {
      mockUseGeocode.mockReturnValue({ results: [], loading: false, error: null });
      const user = userEvent.setup();

      render(<SearchBar onSelect={vi.fn()} />);
      const input = screen.getByRole("combobox");

      await user.type(input, "xyznonexistent");
      await user.keyboard("{Enter}");
      expect(screen.getByRole("alert")).toBeInTheDocument();

      await user.type(input, "a");
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    });

    it("clears not-found error when new results arrive", async () => {
      mockUseGeocode.mockReturnValue({ results: [], loading: false, error: null });
      const user = userEvent.setup();

      const { rerender } = render(<SearchBar onSelect={vi.fn()} />);
      const input = screen.getByRole("combobox");

      await user.type(input, "xyznonexistent");
      await user.keyboard("{Enter}");
      expect(screen.getByRole("alert")).toBeInTheDocument();

      // Simulate new results arriving
      mockUseGeocode.mockReturnValue({ results: mockResults, loading: false, error: null });
      rerender(<SearchBar onSelect={vi.fn()} />);

      expect(
        screen.queryByText("Address not found. Try a different search."),
      ).not.toBeInTheDocument();
    });
  });

  // -- onSelect callback --

  describe("onSelect callback", () => {
    it("calls onSelect with the correct result when clicked", async () => {
      mockUseGeocode.mockReturnValue({ results: mockResults, loading: false, error: null });
      const handleSelect = vi.fn();
      const user = userEvent.setup();

      render(<SearchBar onSelect={handleSelect} />);
      const input = screen.getByRole("combobox");

      await user.type(input, "123 Main");

      await user.click(screen.getByText("123 Main St, Philadelphia, PA"));
      expect(handleSelect).toHaveBeenCalledWith(mockResults[0]);
    });

    it("calls onSelect with the correct result via keyboard", async () => {
      mockUseGeocode.mockReturnValue({ results: mockResults, loading: false, error: null });
      const handleSelect = vi.fn();
      const user = userEvent.setup();

      render(<SearchBar onSelect={handleSelect} />);
      const input = screen.getByRole("combobox");

      await user.type(input, "123 Main");
      await user.keyboard("{ArrowDown}{ArrowDown}{Enter}");

      expect(handleSelect).toHaveBeenCalledWith(mockResults[1]);
    });
  });

  // -- Default navigation (click outside) --

  describe("click outside", () => {
    it("closes dropdown when clicking outside", async () => {
      mockUseGeocode.mockReturnValue({ results: mockResults, loading: false, error: null });
      const user = userEvent.setup();

      render(
        <div>
          <button>Outside</button>
          <SearchBar onSelect={vi.fn()} />
        </div>,
      );
      const input = screen.getByRole("combobox");

      await user.type(input, "123 Main");
      expect(screen.getByRole("listbox")).toBeInTheDocument();

      await user.click(screen.getByText("Outside"));
      expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    });
  });

  // -- Loading / empty / error states --

  describe("loading, empty, and error states", () => {
    it("shows loading spinner while fetching", async () => {
      mockUseGeocode.mockReturnValue({ results: [], loading: true, error: null });
      const user = userEvent.setup();

      render(<SearchBar onSelect={vi.fn()} />);
      const input = screen.getByRole("combobox");

      await user.type(input, "123 Main");

      expect(screen.getByRole("status")).toBeInTheDocument();
      expect(screen.getByRole("status")).toHaveAttribute("aria-label", "Loading results");
    });

    it("shows 'Searching...' text while loading with no results", async () => {
      mockUseGeocode.mockReturnValue({ results: [], loading: true, error: null });
      const user = userEvent.setup();

      render(<SearchBar onSelect={vi.fn()} />);
      const input = screen.getByRole("combobox");

      await user.type(input, "123 Main");

      expect(screen.getByText("Searching...")).toBeInTheDocument();
    });

    it("does not show dropdown when no results and not loading", async () => {
      mockUseGeocode.mockReturnValue({ results: [], loading: false, error: null });
      const user = userEvent.setup();

      render(<SearchBar onSelect={vi.fn()} />);
      const input = screen.getByRole("combobox");

      await user.type(input, "123 Main");

      expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    });

    it("shows error message when geocode fails", async () => {
      mockUseGeocode.mockReturnValue({ results: [], loading: false, error: "Network error" });
      const user = userEvent.setup();

      render(<SearchBar onSelect={vi.fn()} />);
      const input = screen.getByRole("combobox");

      await user.type(input, "123 Main");

      expect(screen.getByRole("alert")).toHaveTextContent("Network error");
    });
  });

  // -- A11y roles and attributes --

  describe("a11y roles and attributes", () => {
    it("input has combobox role with correct ARIA attributes", () => {
      render(<SearchBar onSelect={vi.fn()} />);
      const input = screen.getByRole("combobox");
      expect(input).toHaveAttribute("aria-autocomplete", "list");
      expect(input).toHaveAttribute("aria-expanded", "false");
      expect(input).toHaveAttribute("aria-label", "Search address");
      expect(input).toHaveAttribute("aria-controls", "searchbar-listbox");
    });

    it("sets aria-expanded to true when dropdown is open", async () => {
      mockUseGeocode.mockReturnValue({ results: mockResults, loading: false, error: null });
      const user = userEvent.setup();

      render(<SearchBar onSelect={vi.fn()} />);
      const input = screen.getByRole("combobox");

      await user.type(input, "123 Main");
      expect(input).toHaveAttribute("aria-expanded", "true");
    });

    it("listbox has correct role and label", async () => {
      mockUseGeocode.mockReturnValue({ results: mockResults, loading: false, error: null });
      const user = userEvent.setup();

      render(<SearchBar onSelect={vi.fn()} />);
      const input = screen.getByRole("combobox");

      await user.type(input, "123 Main");

      const listbox = screen.getByRole("listbox");
      expect(listbox).toHaveAttribute("aria-label", "Address suggestions");
      expect(listbox).toHaveAttribute("id", "searchbar-listbox");
    });

    it("options have correct role and aria-selected", async () => {
      mockUseGeocode.mockReturnValue({ results: mockResults, loading: false, error: null });
      const user = userEvent.setup();

      render(<SearchBar onSelect={vi.fn()} />);
      const input = screen.getByRole("combobox");

      await user.type(input, "123 Main");

      const options = screen.getAllByRole("option");
      expect(options).toHaveLength(2);
      options.forEach((option) => {
        expect(option).toHaveAttribute("aria-selected", "false");
      });
    });

    it("updates aria-activedescendant during keyboard navigation", async () => {
      mockUseGeocode.mockReturnValue({ results: mockResults, loading: false, error: null });
      const user = userEvent.setup();

      render(<SearchBar onSelect={vi.fn()} />);
      const input = screen.getByRole("combobox");

      await user.type(input, "123 Main");
      expect(input).not.toHaveAttribute("aria-activedescendant");

      await user.keyboard("{ArrowDown}");
      expect(input).toHaveAttribute("aria-activedescendant", "searchbar-option-0");

      await user.keyboard("{ArrowDown}");
      expect(input).toHaveAttribute("aria-activedescendant", "searchbar-option-1");
    });
  });

  // -- Mobile responsiveness --

  describe("mobile responsiveness", () => {
    it("uses responsive input padding", () => {
      render(<SearchBar onSelect={vi.fn()} />);
      const input = screen.getByRole("combobox");
      expect(input.className).toContain("py-2.5");
      expect(input.className).toContain("sm:py-3");
      expect(input.className).toContain("pl-10");
      expect(input.className).toContain("sm:pl-11");
    });

    it("uses responsive text size on input", () => {
      render(<SearchBar onSelect={vi.fn()} />);
      const input = screen.getByRole("combobox");
      expect(input.className).toContain("text-sm");
      expect(input.className).toContain("sm:text-base");
    });

    it("uses responsive search icon positioning", () => {
      render(<SearchBar onSelect={vi.fn()} />);
      const svg = document.querySelector("svg");
      expect(svg?.getAttribute("class")).toContain("left-3");
      expect(svg?.getAttribute("class")).toContain("sm:left-4");
    });
  });

  // -- vitest-axe accessibility --

  describe("accessibility (axe)", () => {
    it("has no a11y violations in default state", async () => {
      const { container } = render(<SearchBar onSelect={vi.fn()} />);
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("has no a11y violations with dropdown open", async () => {
      mockUseGeocode.mockReturnValue({ results: mockResults, loading: false, error: null });
      const user = userEvent.setup();

      const { container } = render(<SearchBar onSelect={vi.fn()} />);
      const input = screen.getByRole("combobox");
      await user.type(input, "123 Main");

      expect(screen.getByRole("listbox")).toBeInTheDocument();

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("has no a11y violations in loading state", async () => {
      mockUseGeocode.mockReturnValue({ results: [], loading: true, error: null });
      const user = userEvent.setup();

      const { container } = render(<SearchBar onSelect={vi.fn()} />);
      const input = screen.getByRole("combobox");
      await user.type(input, "123 Main");

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("has no a11y violations in error state", async () => {
      mockUseGeocode.mockReturnValue({ results: [], loading: false, error: "Network error" });
      const user = userEvent.setup();

      const { container } = render(<SearchBar onSelect={vi.fn()} />);
      const input = screen.getByRole("combobox");
      await user.type(input, "123 Main");

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("has no a11y violations in not-found state", async () => {
      mockUseGeocode.mockReturnValue({ results: [], loading: false, error: null });
      const user = userEvent.setup();

      const { container } = render(<SearchBar onSelect={vi.fn()} />);
      const input = screen.getByRole("combobox");
      await user.type(input, "xyznonexistent");
      await user.keyboard("{Enter}");

      expect(screen.getByRole("alert")).toBeInTheDocument();
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });
});
