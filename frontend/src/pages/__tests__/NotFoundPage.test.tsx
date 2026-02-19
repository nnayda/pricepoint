import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import NotFoundPage from "../NotFoundPage";

function renderNotFoundPage() {
  return render(
    <MemoryRouter>
      <NotFoundPage />
    </MemoryRouter>,
  );
}

describe("NotFoundPage", () => {
  it("renders 404 heading", () => {
    renderNotFoundPage();
    expect(screen.getByText("404")).toBeInTheDocument();
  });

  it("renders Page Not Found message", () => {
    renderNotFoundPage();
    expect(screen.getByText("Page Not Found")).toBeInTheDocument();
  });

  it("renders explanation text", () => {
    renderNotFoundPage();
    expect(screen.getByText(/does not exist or has been moved/i)).toBeInTheDocument();
  });

  it("has a Back to Home link", () => {
    renderNotFoundPage();
    const link = screen.getByRole("link", { name: /back to home/i });
    expect(link).toBeInTheDocument();
  });

  it("Back to Home link points to /", () => {
    renderNotFoundPage();
    const link = screen.getByRole("link", { name: /back to home/i });
    expect(link).toHaveAttribute("href", "/");
  });
});
