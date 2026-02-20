import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import RecentlyViewed from "../RecentlyViewed";
import type { RecentlyViewedItem } from "../../../types";

const mockItems: RecentlyViewedItem[] = [
  {
    address: "123 Main St, Raleigh, NC",
    lat: 35.8,
    lon: -78.6,
    price: 450000,
    viewedAt: new Date().toISOString(),
  },
  {
    address: "456 Oak Ave, Durham, NC",
    lat: 35.9,
    lon: -78.9,
    viewedAt: new Date(Date.now() - 3_600_000).toISOString(),
  },
];

const mockClear = vi.fn();

vi.mock("../../../hooks/useRecentlyViewed", () => ({
  useRecentlyViewed: vi.fn(() => ({
    recentlyViewed: [],
    addRecentlyViewed: vi.fn(),
    clearRecentlyViewed: mockClear,
  })),
}));

import { useRecentlyViewed } from "../../../hooks/useRecentlyViewed";
const mockUseRecentlyViewed = vi.mocked(useRecentlyViewed);

function renderComponent() {
  return render(
    <MemoryRouter>
      <RecentlyViewed />
    </MemoryRouter>,
  );
}

function setItems(items: RecentlyViewedItem[]) {
  mockUseRecentlyViewed.mockReturnValue({
    recentlyViewed: items,
    addRecentlyViewed: vi.fn(),
    clearRecentlyViewed: mockClear,
  });
}

beforeEach(() => {
  vi.clearAllMocks();
  mockUseRecentlyViewed.mockReturnValue({
    recentlyViewed: [],
    addRecentlyViewed: vi.fn(),
    clearRecentlyViewed: mockClear,
  });
});

describe("RecentlyViewed", () => {
  it("returns null when no history exists", () => {
    const { container } = renderComponent();
    expect(container.innerHTML).toBe("");
  });

  it("renders cards when history exists", () => {
    setItems(mockItems);
    renderComponent();
    expect(screen.getByTestId("recently-viewed")).toBeInTheDocument();
    const links = screen.getAllByRole("link");
    expect(links).toHaveLength(2);
  });

  it("shows addresses on cards", () => {
    setItems(mockItems);
    renderComponent();
    expect(screen.getByText("123 Main St, Raleigh, NC")).toBeInTheDocument();
    expect(screen.getByText("456 Oak Ave, Durham, NC")).toBeInTheDocument();
  });

  it("shows price when available", () => {
    setItems(mockItems);
    renderComponent();
    expect(screen.getByText("$450,000")).toBeInTheDocument();
  });

  it("shows Clear History button", () => {
    setItems(mockItems);
    renderComponent();
    expect(screen.getByText("Clear History")).toBeInTheDocument();
  });

  it("calls clearRecentlyViewed when Clear History is clicked", async () => {
    setItems(mockItems);
    renderComponent();
    const user = userEvent.setup();
    await user.click(screen.getByText("Clear History"));
    expect(mockClear).toHaveBeenCalledOnce();
  });
});
