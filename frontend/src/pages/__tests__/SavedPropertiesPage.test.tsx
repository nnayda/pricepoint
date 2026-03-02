import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import SavedPropertiesPage from "../SavedPropertiesPage";

const mockUseAuth = vi.fn();
vi.mock("../../contexts/AuthContext", () => ({
  useAuth: () => mockUseAuth(),
}));

vi.mock("../../components/dashboard/DashboardNav", () => ({
  default: () => <nav data-testid="dashboard-nav" />,
}));

const mockUseSavedProperties = vi.fn();
vi.mock("../../hooks/useSavedProperties", () => ({
  useSavedProperties: (...args: unknown[]) => mockUseSavedProperties(...args),
}));

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

function makeSaved(id: number, address: string) {
  return {
    id,
    listing_id: id * 10,
    notes: null,
    created_at: "2025-06-01T12:00:00Z",
    listing_address: address,
    city: "Cary",
    state: "NC",
    zip_code: "27513",
    listing_status: "Sold",
    listing_price: 350000,
    sold_price: 345000,
    num_beds: 3,
    num_baths: 2.5,
    sqft: 1800,
    year_built: 2005,
    photo_url: "/api/photos/photos/abc.jpg",
    lat: 35.79,
    lon: -78.78,
  };
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/saved"]}>
      <SavedPropertiesPage />
    </MemoryRouter>,
  );
}

describe("SavedPropertiesPage", () => {
  const mockRemove = vi.fn();
  const mockRefetch = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth.mockReturnValue({
      user: { email: "test@test.com", display_name: "Test" },
      isAuthenticated: true,
      isLoading: false,
    });
    mockUseSavedProperties.mockReturnValue({
      properties: [],
      isLoading: false,
      error: null,
      remove: mockRemove,
      refetch: mockRefetch,
    });
  });

  it("redirects unauthenticated users", () => {
    mockUseAuth.mockReturnValue({
      user: null,
      isAuthenticated: false,
      isLoading: false,
    });
    renderPage();
    expect(screen.queryByText("Saved Properties")).not.toBeInTheDocument();
  });

  it("returns null while loading auth", () => {
    mockUseAuth.mockReturnValue({
      user: null,
      isAuthenticated: false,
      isLoading: true,
    });
    const { container } = renderPage();
    expect(container.innerHTML).toBe("");
  });

  it("shows loading spinner", () => {
    mockUseSavedProperties.mockReturnValue({
      properties: [],
      isLoading: true,
      error: null,
      remove: mockRemove,
      refetch: mockRefetch,
    });
    renderPage();
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("shows empty state", () => {
    renderPage();
    expect(screen.getByText("No saved properties")).toBeInTheDocument();
    expect(screen.getByText("Search properties")).toBeInTheDocument();
  });

  it("renders property cards", () => {
    mockUseSavedProperties.mockReturnValue({
      properties: [makeSaved(1, "123 Main St"), makeSaved(2, "456 Oak Ave")],
      isLoading: false,
      error: null,
      remove: mockRemove,
      refetch: mockRefetch,
    });
    renderPage();
    expect(screen.getByText("123 Main St")).toBeInTheDocument();
    expect(screen.getByText("456 Oak Ave")).toBeInTheDocument();
    expect(screen.getAllByTestId("property-card")).toHaveLength(2);
  });

  it("navigates on card click", () => {
    mockUseSavedProperties.mockReturnValue({
      properties: [makeSaved(1, "123 Main St")],
      isLoading: false,
      error: null,
      remove: mockRemove,
      refetch: mockRefetch,
    });
    renderPage();
    fireEvent.click(screen.getByTestId("property-card"));
    expect(mockNavigate).toHaveBeenCalledWith("/property/123%20Main%20St?lat=35.79&lon=-78.78");
  });

  it("calls remove on delete button click", async () => {
    mockRemove.mockResolvedValue(undefined);
    mockUseSavedProperties.mockReturnValue({
      properties: [makeSaved(1, "123 Main St")],
      isLoading: false,
      error: null,
      remove: mockRemove,
      refetch: mockRefetch,
    });
    renderPage();
    fireEvent.click(screen.getByLabelText("Remove 123 Main St"));
    await waitFor(() => {
      expect(mockRemove).toHaveBeenCalledWith(1);
    });
  });

  it("shows error state", () => {
    mockUseSavedProperties.mockReturnValue({
      properties: [],
      isLoading: false,
      error: "Failed to load saved properties.",
      remove: mockRemove,
      refetch: mockRefetch,
    });
    renderPage();
    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText("Failed to load saved properties.")).toBeInTheDocument();
  });

  it("shows price and stats on card", () => {
    mockUseSavedProperties.mockReturnValue({
      properties: [makeSaved(1, "123 Main St")],
      isLoading: false,
      error: null,
      remove: mockRemove,
      refetch: mockRefetch,
    });
    renderPage();
    expect(screen.getByText("$345,000")).toBeInTheDocument();
    expect(screen.getByText("3 bd")).toBeInTheDocument();
    expect(screen.getByText("2.5 ba")).toBeInTheDocument();
    expect(screen.getByText("1,800 sqft")).toBeInTheDocument();
    expect(screen.getByText("Built 2005")).toBeInTheDocument();
  });

  it("shows dashboard nav", () => {
    renderPage();
    expect(screen.getByTestId("dashboard-nav")).toBeInTheDocument();
  });
});
