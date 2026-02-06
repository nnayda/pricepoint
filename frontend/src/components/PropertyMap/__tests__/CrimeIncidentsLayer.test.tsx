import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import CrimeIncidentsLayer from "../layers/CrimeIncidentsLayer";
import type { CrimeIncident } from "../../../types";

vi.mock("react-leaflet", () => ({
  Marker: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="marker">{children}</div>
  ),
  Popup: ({ children }: { children: React.ReactNode }) => <div data-testid="popup">{children}</div>,
}));

vi.mock("react-leaflet-cluster", () => ({
  default: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="cluster-group">{children}</div>
  ),
}));

const mockIncidents: CrimeIncident[] = [
  {
    id: "cr-1",
    incident_type: "Burglary",
    category: "Property",
    date: "2024-12-01",
    lat: 35.78,
    lon: -78.64,
    description: "Break-in reported",
  },
  {
    id: "cr-2",
    incident_type: "Assault",
    category: "Violent",
    date: "2024-12-05",
    lat: 35.79,
    lon: -78.65,
  },
];

describe("CrimeIncidentsLayer", () => {
  it("renders a cluster group", () => {
    render(<CrimeIncidentsLayer data={mockIncidents} />);
    expect(screen.getByTestId("cluster-group")).toBeInTheDocument();
  });

  it("renders a marker for each incident", () => {
    render(<CrimeIncidentsLayer data={mockIncidents} />);
    const markers = screen.getAllByTestId("marker");
    expect(markers).toHaveLength(2);
  });

  it("renders incident type in popup", () => {
    render(<CrimeIncidentsLayer data={mockIncidents} />);
    expect(screen.getByText("Burglary")).toBeInTheDocument();
    expect(screen.getByText("Assault")).toBeInTheDocument();
  });

  it("renders incident category in popup", () => {
    render(<CrimeIncidentsLayer data={mockIncidents} />);
    expect(screen.getByText("Property")).toBeInTheDocument();
    expect(screen.getByText("Violent")).toBeInTheDocument();
  });

  it("renders incident date in popup", () => {
    render(<CrimeIncidentsLayer data={mockIncidents} />);
    expect(screen.getByText("2024-12-01")).toBeInTheDocument();
  });

  it("renders description when present", () => {
    render(<CrimeIncidentsLayer data={mockIncidents} />);
    expect(screen.getByText("Break-in reported")).toBeInTheDocument();
  });

  it("does not render description when absent", () => {
    render(<CrimeIncidentsLayer data={mockIncidents} />);
    // Second incident has no description — only one description paragraph exists
    const popups = screen.getAllByTestId("popup");
    // The second popup (Assault) has no description
    expect(popups[1].textContent).not.toContain("Break-in");
  });

  it("returns null when data is empty", () => {
    const { container } = render(<CrimeIncidentsLayer data={[]} />);
    expect(container.innerHTML).toBe("");
  });
});
