import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import DataRequestBanner from "../DataRequestBanner";

const mockSubmitDataRequest = vi.fn();

vi.mock("../../services/property", () => ({
  submitDataRequest: (...args: unknown[]) => mockSubmitDataRequest(...args),
}));

describe("DataRequestBanner", () => {
  const defaultProps = {
    address: "123 Main St, Raleigh, NC",
    lat: 35.5,
    lon: -78.7,
    onDismiss: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the not-in-database message", () => {
    render(<DataRequestBanner {...defaultProps} />);
    expect(screen.getByText(/isn't in our database yet/)).toBeInTheDocument();
  });

  it("has an alert role for accessibility", () => {
    render(<DataRequestBanner {...defaultProps} />);
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });

  it("shows 'Request data collection' link initially", () => {
    render(<DataRequestBanner {...defaultProps} />);
    expect(screen.getByText("Request data collection")).toBeInTheDocument();
  });

  it("expands to show email form when 'Request data collection' is clicked", () => {
    render(<DataRequestBanner {...defaultProps} />);
    fireEvent.click(screen.getByText("Request data collection"));
    expect(screen.getByPlaceholderText("you@example.com")).toBeInTheDocument();
    expect(screen.getByText("Submit Request")).toBeInTheDocument();
  });

  it("calls onDismiss when dismiss button is clicked", () => {
    render(<DataRequestBanner {...defaultProps} />);
    fireEvent.click(screen.getByLabelText("Dismiss banner"));
    expect(defaultProps.onDismiss).toHaveBeenCalledTimes(1);
  });

  it("submits data request with address, lat, lon", async () => {
    mockSubmitDataRequest.mockResolvedValue({});
    render(<DataRequestBanner {...defaultProps} />);

    fireEvent.click(screen.getByText("Request data collection"));
    fireEvent.click(screen.getByText("Submit Request"));

    await waitFor(() => {
      expect(mockSubmitDataRequest).toHaveBeenCalledWith({
        address: "123 Main St, Raleigh, NC",
        lat: 35.5,
        lon: -78.7,
        email: undefined,
      });
    });
  });

  it("submits data request with email when provided", async () => {
    mockSubmitDataRequest.mockResolvedValue({});
    render(<DataRequestBanner {...defaultProps} />);

    fireEvent.click(screen.getByText("Request data collection"));
    fireEvent.change(screen.getByPlaceholderText("you@example.com"), {
      target: { value: "test@example.com" },
    });
    fireEvent.click(screen.getByText("Submit Request"));

    await waitFor(() => {
      expect(mockSubmitDataRequest).toHaveBeenCalledWith(
        expect.objectContaining({ email: "test@example.com" }),
      );
    });
  });

  it("shows success message after submission", async () => {
    mockSubmitDataRequest.mockResolvedValue({});
    render(<DataRequestBanner {...defaultProps} />);

    fireEvent.click(screen.getByText("Request data collection"));
    fireEvent.click(screen.getByText("Submit Request"));

    await waitFor(() => {
      expect(screen.getByText(/Request submitted/)).toBeInTheDocument();
    });
  });

  it("shows error message when submission fails", async () => {
    mockSubmitDataRequest.mockRejectedValue(new Error("network error"));
    render(<DataRequestBanner {...defaultProps} />);

    fireEvent.click(screen.getByText("Request data collection"));
    fireEvent.click(screen.getByText("Submit Request"));

    await waitFor(() => {
      expect(screen.getByText("Failed to submit request. Please try again.")).toBeInTheDocument();
    });
  });

  it("collapses form when Cancel is clicked", () => {
    render(<DataRequestBanner {...defaultProps} />);

    fireEvent.click(screen.getByText("Request data collection"));
    expect(screen.getByPlaceholderText("you@example.com")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Cancel"));
    expect(screen.queryByPlaceholderText("you@example.com")).not.toBeInTheDocument();
  });

  it("disables submit button while submitting", async () => {
    let resolveSubmit: () => void;
    mockSubmitDataRequest.mockImplementation(
      () =>
        new Promise<void>((resolve) => {
          resolveSubmit = resolve;
        }),
    );
    render(<DataRequestBanner {...defaultProps} />);

    fireEvent.click(screen.getByText("Request data collection"));
    fireEvent.click(screen.getByText("Submit Request"));

    expect(screen.getByText("Submitting...")).toBeDisabled();

    resolveSubmit!();
    await waitFor(() => {
      expect(screen.getByText(/Request submitted/)).toBeInTheDocument();
    });
  });
});
