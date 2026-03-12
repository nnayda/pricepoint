import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import UploadPage from "../UploadPage";

const mockUseAuth = vi.fn();
vi.mock("../../contexts/AuthContext", () => ({
  useAuth: () => mockUseAuth(),
}));

vi.mock("../../components/dashboard/DashboardNav", () => ({
  default: () => <nav data-testid="dashboard-nav" />,
}));

const mockUpload = vi.fn();
vi.mock("../../services/upload", () => ({
  uploadRedfinFiles: (...args: unknown[]) => mockUpload(...args),
}));

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/upload"]}>
      <UploadPage />
    </MemoryRouter>,
  );
}

function createFile(name: string, size = 1024): File {
  const content = new Array(size).fill("a").join("");
  return new File([content], name, { type: "text/html" });
}

describe("UploadPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth.mockReturnValue({
      user: { email: "test@test.com", display_name: "Test" },
      isAuthenticated: true,
      isLoading: false,
    });
  });

  it("redirects unauthenticated users", () => {
    mockUseAuth.mockReturnValue({
      user: null,
      isAuthenticated: false,
      isLoading: false,
    });
    renderPage();
    expect(screen.queryByText("Upload Redfin Listings")).not.toBeInTheDocument();
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

  it("renders the upload page for authenticated users", () => {
    renderPage();
    expect(screen.getByText("Upload Redfin Listings")).toBeInTheDocument();
    expect(screen.getByTestId("drop-zone")).toBeInTheDocument();
    expect(screen.getByTestId("dashboard-nav")).toBeInTheDocument();
  });

  it("selects files via the file input", () => {
    renderPage();
    const input = screen.getByTestId("file-input") as HTMLInputElement;
    const file = createFile("listing.html");
    fireEvent.change(input, { target: { files: [file] } });
    expect(screen.getByText("listing.html")).toBeInTheDocument();
  });

  it("filters out non-html files", () => {
    renderPage();
    const input = screen.getByTestId("file-input") as HTMLInputElement;
    const htmlFile = createFile("listing.html");
    const pdfFile = new File(["data"], "listing.pdf", { type: "application/pdf" });
    fireEvent.change(input, { target: { files: [htmlFile, pdfFile] } });
    expect(screen.getByText("listing.html")).toBeInTheDocument();
    expect(screen.queryByText("listing.pdf")).not.toBeInTheDocument();
  });

  it("deduplicates files by name", () => {
    renderPage();
    const input = screen.getByTestId("file-input") as HTMLInputElement;
    const file1 = createFile("listing.html");
    const file2 = createFile("listing.html");
    fireEvent.change(input, { target: { files: [file1] } });
    fireEvent.change(input, { target: { files: [file2] } });
    const items = screen.getAllByText("listing.html");
    expect(items).toHaveLength(1);
  });

  it("removes a file from the list", () => {
    renderPage();
    const input = screen.getByTestId("file-input") as HTMLInputElement;
    fireEvent.change(input, { target: { files: [createFile("listing.html")] } });
    expect(screen.getByText("listing.html")).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText("Remove listing.html"));
    expect(screen.queryByText("listing.html")).not.toBeInTheDocument();
  });

  it("upload button is disabled when no files selected", () => {
    renderPage();
    const btn = screen.getByRole("button", { name: /upload/i });
    expect(btn).toBeDisabled();
  });

  it("uploads files and shows success", async () => {
    mockUpload.mockResolvedValue({ saved: ["listing.html"], errors: [] });
    renderPage();
    const input = screen.getByTestId("file-input") as HTMLInputElement;
    fireEvent.change(input, { target: { files: [createFile("listing.html")] } });
    fireEvent.click(screen.getByRole("button", { name: /upload 1 file$/i }));
    await waitFor(() => {
      expect(screen.getByText("1 file uploaded successfully")).toBeInTheDocument();
    });
    expect(
      screen.getByText("Files saved. They will be processed on the next scheduled run."),
    ).toBeInTheDocument();
    expect(mockUpload).toHaveBeenCalledTimes(1);
  });

  it("shows error on upload failure", async () => {
    mockUpload.mockRejectedValue(new Error("Network error"));
    renderPage();
    const input = screen.getByTestId("file-input") as HTMLInputElement;
    fireEvent.change(input, { target: { files: [createFile("listing.html")] } });
    fireEvent.click(screen.getByRole("button", { name: /upload 1 file$/i }));
    await waitFor(() => {
      expect(screen.getByText("Upload failed. Please try again.")).toBeInTheDocument();
    });
  });

  it("shows server-side errors from response", async () => {
    mockUpload.mockResolvedValue({
      saved: [],
      errors: ["bad.html: only .html files are accepted"],
    });
    renderPage();
    const input = screen.getByTestId("file-input") as HTMLInputElement;
    fireEvent.change(input, { target: { files: [createFile("listing.html")] } });
    fireEvent.click(screen.getByRole("button", { name: /upload 1 file$/i }));
    await waitFor(() => {
      expect(screen.getByText("Some files had errors")).toBeInTheDocument();
    });
  });

  it("handles drag and drop", () => {
    renderPage();
    const zone = screen.getByTestId("drop-zone");
    const file = createFile("dropped.html");
    fireEvent.dragOver(zone);
    fireEvent.drop(zone, { dataTransfer: { files: [file] } });
    expect(screen.getByText("dropped.html")).toBeInTheDocument();
  });

  it("shows file sizes", () => {
    renderPage();
    const input = screen.getByTestId("file-input") as HTMLInputElement;
    fireEvent.change(input, { target: { files: [createFile("listing.html", 2048)] } });
    expect(screen.getByText("2.0 KB")).toBeInTheDocument();
  });
});
