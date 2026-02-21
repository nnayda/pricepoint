import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import SignInPage from "../SignInPage";

const mockLogin = vi.fn();
const mockAuth = {
  user: null as { id: number; email: string; display_name: string | null } | null,
  isAuthenticated: false,
  isLoading: false,
  error: null as string | null,
  login: mockLogin,
  register: vi.fn(),
  logout: vi.fn(),
  refreshAuth: vi.fn(),
};

vi.mock("../../contexts/AuthContext", () => ({
  useAuth: () => mockAuth,
}));

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/signin"]}>
      <SignInPage />
    </MemoryRouter>,
  );
}

describe("SignInPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAuth.user = null;
    mockAuth.isAuthenticated = false;
    mockAuth.error = null;
    mockLogin.mockResolvedValue(undefined);
  });

  it("renders the sign in heading", () => {
    renderPage();
    expect(screen.getByRole("heading", { name: "Sign In" })).toBeInTheDocument();
  });

  it("renders email and password fields", () => {
    renderPage();
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
  });

  it("renders a submit button", () => {
    renderPage();
    expect(screen.getByRole("button", { name: "Sign In" })).toBeInTheDocument();
  });

  it("renders a link to sign up page", () => {
    renderPage();
    const link = screen.getByRole("link", { name: "Sign Up" });
    expect(link).toHaveAttribute("href", "/signup");
  });

  it("calls login on form submission", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText("Email"), "test@example.com");
    await user.type(screen.getByLabelText("Password"), "password123");
    await user.click(screen.getByRole("button", { name: "Sign In" }));

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith("test@example.com", "password123");
    });
  });

  it("displays error message on login failure", async () => {
    mockLogin.mockRejectedValue(new Error("Invalid email or password"));
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText("Email"), "test@example.com");
    await user.type(screen.getByLabelText("Password"), "wrong");
    await user.click(screen.getByRole("button", { name: "Sign In" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Invalid email or password");
    });
  });

  it("shows loading state while submitting", async () => {
    let resolveLogin: () => void;
    mockLogin.mockReturnValue(
      new Promise<void>((resolve) => {
        resolveLogin = resolve;
      }),
    );
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText("Email"), "test@example.com");
    await user.type(screen.getByLabelText("Password"), "password123");
    await user.click(screen.getByRole("button", { name: "Sign In" }));

    expect(screen.getByRole("button", { name: "Signing in..." })).toBeDisabled();

    resolveLogin!();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Sign In" })).not.toBeDisabled();
    });
  });
});
