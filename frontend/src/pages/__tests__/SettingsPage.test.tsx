import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "vitest-axe";
import SettingsPage from "../SettingsPage";
import type { PoiPreference, MortgageDefaults } from "../../types";

const mockTogglePoi = vi.fn();
const mockToggleCategory = vi.fn();
const mockAddCustomPoi = vi.fn();
const mockRemoveCustomPoi = vi.fn();
const mockUpdateDefaults = vi.fn();

const defaultPreferences: PoiPreference[] = [
  { id: "p1", name: "Walmart", category: "Grocery", enabled: true },
  { id: "p2", name: "Trader Joe's", category: "Grocery", enabled: true },
  { id: "p3", name: "CVS", category: "Pharmacy", enabled: false },
  { id: "p4", name: "My Custom POI", category: "Retail", enabled: true, isCustom: true },
];

const defaultMortgage: MortgageDefaults = {
  downPaymentPercent: 20,
  interestRate: 6.5,
  loanTermYears: 30,
  annualInsurance: 1200,
};

vi.mock("../../hooks/usePoiPreferences", () => ({
  usePoiPreferences: () => ({
    preferences: defaultPreferences,
    togglePoi: mockTogglePoi,
    toggleCategory: mockToggleCategory,
    addCustomPoi: mockAddCustomPoi,
    removeCustomPoi: mockRemoveCustomPoi,
  }),
}));

vi.mock("../../hooks/useMortgageDefaults", () => ({
  useMortgageDefaults: () => ({
    defaults: defaultMortgage,
    updateDefaults: mockUpdateDefaults,
  }),
}));

describe("SettingsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // -- Headings --

  it("renders the page heading", () => {
    render(<SettingsPage />);
    expect(screen.getByText("Settings")).toBeInTheDocument();
  });

  it("renders POI preferences section", () => {
    render(<SettingsPage />);
    expect(screen.getByLabelText("POI preferences")).toBeInTheDocument();
    expect(screen.getByText("POI Preferences")).toBeInTheDocument();
  });

  it("renders mortgage defaults section", () => {
    render(<SettingsPage />);
    expect(screen.getByLabelText("Mortgage defaults")).toBeInTheDocument();
    expect(screen.getByText("Mortgage Defaults")).toBeInTheDocument();
  });

  // -- POI toggles --

  it("renders individual POI toggles", () => {
    render(<SettingsPage />);
    expect(screen.getByLabelText("Toggle Walmart")).toBeInTheDocument();
    expect(screen.getByLabelText("Toggle CVS")).toBeInTheDocument();
  });

  it("renders category toggles", () => {
    render(<SettingsPage />);
    expect(screen.getByLabelText("Toggle all Grocery")).toBeInTheDocument();
    expect(screen.getByLabelText("Toggle all Pharmacy")).toBeInTheDocument();
  });

  it("calls togglePoi when an individual toggle is clicked", async () => {
    const user = userEvent.setup();
    render(<SettingsPage />);
    await user.click(screen.getByLabelText("Toggle Walmart"));
    expect(mockTogglePoi).toHaveBeenCalledWith("p1");
  });

  it("calls toggleCategory when a category toggle is clicked", async () => {
    const user = userEvent.setup();
    render(<SettingsPage />);
    await user.click(screen.getByLabelText("Toggle all Grocery"));
    expect(mockToggleCategory).toHaveBeenCalledWith("Grocery");
  });

  it("shows enabled state for enabled POIs", () => {
    render(<SettingsPage />);
    const walmartToggle = screen.getByLabelText("Toggle Walmart");
    expect(walmartToggle).toHaveAttribute("aria-checked", "true");
  });

  it("shows disabled state for disabled POIs", () => {
    render(<SettingsPage />);
    const cvsToggle = screen.getByLabelText("Toggle CVS");
    expect(cvsToggle).toHaveAttribute("aria-checked", "false");
  });

  // -- Custom POI --

  it("renders remove button for custom POIs", () => {
    render(<SettingsPage />);
    expect(screen.getByLabelText("Remove My Custom POI")).toBeInTheDocument();
  });

  it("does not render remove button for default POIs", () => {
    render(<SettingsPage />);
    expect(screen.queryByLabelText("Remove Walmart")).not.toBeInTheDocument();
  });

  it("calls removeCustomPoi when remove button is clicked", async () => {
    const user = userEvent.setup();
    render(<SettingsPage />);
    await user.click(screen.getByLabelText("Remove My Custom POI"));
    expect(mockRemoveCustomPoi).toHaveBeenCalledWith("p4");
  });

  it("calls addCustomPoi on form submit", async () => {
    const user = userEvent.setup();
    render(<SettingsPage />);

    const nameInput = screen.getByLabelText("Name");
    await user.type(nameInput, "Aldi");
    await user.click(screen.getByText("Add"));

    expect(mockAddCustomPoi).toHaveBeenCalledWith("Aldi", "Grocery");
  });

  it("does not add POI with empty name", async () => {
    const user = userEvent.setup();
    render(<SettingsPage />);

    await user.click(screen.getByText("Add"));
    expect(mockAddCustomPoi).not.toHaveBeenCalled();
  });

  it("clears name input after adding POI", async () => {
    const user = userEvent.setup();
    render(<SettingsPage />);

    const nameInput = screen.getByLabelText("Name");
    await user.type(nameInput, "Aldi");
    await user.click(screen.getByText("Add"));

    expect(nameInput).toHaveValue("");
  });

  it("allows selecting a different category for new POI", async () => {
    const user = userEvent.setup();
    render(<SettingsPage />);

    await user.selectOptions(screen.getByLabelText("Category"), "Restaurant");
    await user.type(screen.getByLabelText("Name"), "Chipotle");
    await user.click(screen.getByText("Add"));

    expect(mockAddCustomPoi).toHaveBeenCalledWith("Chipotle", "Restaurant");
  });

  // -- Mortgage defaults --

  it("renders mortgage default inputs", () => {
    render(<SettingsPage />);
    expect(screen.getByLabelText("Down Payment %")).toBeInTheDocument();
    expect(screen.getByLabelText("Interest Rate %")).toBeInTheDocument();
    expect(screen.getByLabelText("Loan Term (years)")).toBeInTheDocument();
    expect(screen.getByLabelText("Annual Insurance ($)")).toBeInTheDocument();
  });

  it("shows current default values in inputs", () => {
    render(<SettingsPage />);
    expect(screen.getByLabelText("Down Payment %")).toHaveValue(20);
    expect(screen.getByLabelText("Interest Rate %")).toHaveValue(6.5);
    expect(screen.getByLabelText("Loan Term (years)")).toHaveValue(30);
    expect(screen.getByLabelText("Annual Insurance ($)")).toHaveValue(1200);
  });

  it("calls updateDefaults when a mortgage input changes", async () => {
    const user = userEvent.setup();
    render(<SettingsPage />);

    const downPayment = screen.getByLabelText("Down Payment %");
    await user.clear(downPayment);
    await user.type(downPayment, "15");

    expect(mockUpdateDefaults).toHaveBeenCalled();
  });

  // -- Accessibility --

  it("has no accessibility violations", async () => {
    const { container } = render(<SettingsPage />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
