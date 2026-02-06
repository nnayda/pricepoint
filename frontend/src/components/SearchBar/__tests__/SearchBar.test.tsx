import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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

  it("renders an input with the default placeholder", () => {
    render(<SearchBar onSelect={vi.fn()} />);
    expect(screen.getByPlaceholderText("Search for an address...")).toBeInTheDocument();
  });

  it("renders with a custom placeholder", () => {
    render(<SearchBar onSelect={vi.fn()} placeholder="Find a property" />);
    expect(screen.getByPlaceholderText("Find a property")).toBeInTheDocument();
  });

  it("has proper combobox accessibility attributes", () => {
    render(<SearchBar onSelect={vi.fn()} />);
    const input = screen.getByRole("combobox");
    expect(input).toHaveAttribute("aria-autocomplete", "list");
    expect(input).toHaveAttribute("aria-expanded", "false");
    expect(input).toHaveAttribute("aria-label", "Search address");
  });

  it("does not show dropdown for queries shorter than 3 characters", async () => {
    const user = userEvent.setup();
    render(<SearchBar onSelect={vi.fn()} />);
    const input = screen.getByRole("combobox");

    await user.type(input, "ab");

    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  it("shows dropdown with results after typing", async () => {
    mockUseGeocode.mockReturnValue({ results: mockResults, loading: false, error: null });
    const user = userEvent.setup();

    render(<SearchBar onSelect={vi.fn()} />);
    const input = screen.getByRole("combobox");

    await user.type(input, "123 Main");

    expect(screen.getByRole("listbox")).toBeInTheDocument();
    expect(screen.getByText("123 Main St, Philadelphia, PA")).toBeInTheDocument();
    expect(screen.getByText("123 Main St, Springfield, IL")).toBeInTheDocument();
  });

  it("shows loading spinner while fetching", async () => {
    mockUseGeocode.mockReturnValue({ results: [], loading: true, error: null });
    const user = userEvent.setup();

    render(<SearchBar onSelect={vi.fn()} />);
    const input = screen.getByRole("combobox");

    await user.type(input, "123 Main");

    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("calls onSelect when a result is clicked", async () => {
    mockUseGeocode.mockReturnValue({ results: mockResults, loading: false, error: null });
    const handleSelect = vi.fn();
    const user = userEvent.setup();

    render(<SearchBar onSelect={handleSelect} />);
    const input = screen.getByRole("combobox");

    await user.type(input, "123 Main");

    const option = screen.getByText("123 Main St, Philadelphia, PA");
    await user.click(option);

    expect(handleSelect).toHaveBeenCalledWith(mockResults[0]);
  });

  it("fills the input with the selected result display name", async () => {
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

  it("navigates results with arrow keys and selects with Enter", async () => {
    mockUseGeocode.mockReturnValue({ results: mockResults, loading: false, error: null });
    const handleSelect = vi.fn();
    const user = userEvent.setup();

    render(<SearchBar onSelect={handleSelect} />);
    const input = screen.getByRole("combobox");

    await user.type(input, "123 Main");
    expect(screen.getByRole("listbox")).toBeInTheDocument();

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

    await user.keyboard("{Enter}");
    expect(handleSelect).toHaveBeenCalledWith(mockResults[1]);
  });

  it("closes dropdown on Escape", async () => {
    mockUseGeocode.mockReturnValue({ results: mockResults, loading: false, error: null });
    const user = userEvent.setup();

    render(<SearchBar onSelect={vi.fn()} />);
    const input = screen.getByRole("combobox");

    await user.type(input, "123 Main");
    expect(screen.getByRole("listbox")).toBeInTheDocument();

    await user.keyboard("{Escape}");
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

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

  it("shows error message when geocode fails", async () => {
    mockUseGeocode.mockReturnValue({ results: [], loading: false, error: "Network error" });
    const user = userEvent.setup();

    render(<SearchBar onSelect={vi.fn()} />);
    const input = screen.getByRole("combobox");

    await user.type(input, "123 Main");

    expect(screen.getByRole("alert")).toHaveTextContent("Network error");
  });

  it("does not navigate past the last result with ArrowDown", async () => {
    mockUseGeocode.mockReturnValue({ results: mockResults, loading: false, error: null });
    const user = userEvent.setup();

    render(<SearchBar onSelect={vi.fn()} />);
    const input = screen.getByRole("combobox");

    await user.type(input, "123 Main");
    expect(screen.getByRole("listbox")).toBeInTheDocument();

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
    expect(screen.getByRole("listbox")).toBeInTheDocument();

    await user.keyboard("{ArrowUp}");
    const options = screen.getAllByRole("option");
    options.forEach((option) => {
      expect(option).toHaveAttribute("aria-selected", "false");
    });
  });

  it("renders a search icon", () => {
    render(<SearchBar onSelect={vi.fn()} />);
    const svg = document.querySelector("svg");
    expect(svg).toBeInTheDocument();
    expect(svg).toHaveAttribute("aria-hidden", "true");
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

  it("sets aria-expanded to true when dropdown is open", async () => {
    mockUseGeocode.mockReturnValue({ results: mockResults, loading: false, error: null });
    const user = userEvent.setup();

    render(<SearchBar onSelect={vi.fn()} />);
    const input = screen.getByRole("combobox");

    await user.type(input, "123 Main");
    expect(input).toHaveAttribute("aria-expanded", "true");
  });

  it("shows searching text while loading with no results", async () => {
    mockUseGeocode.mockReturnValue({ results: [], loading: true, error: null });
    const user = userEvent.setup();

    render(<SearchBar onSelect={vi.fn()} />);
    const input = screen.getByRole("combobox");

    await user.type(input, "123 Main");

    expect(screen.getByText("Searching...")).toBeInTheDocument();
  });
});
