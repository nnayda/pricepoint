import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import SignUpPage from "../SignUpPage";

const mockRegister = vi.fn();
const mockAuth = {
  user: null as { id: number; email: string; display_name: string | null } | null,
  isAuthenticated: false,
  isLoading: false,
  error: null as string | null,
  login: vi.fn(),
  register: mockRegister,
  logout: vi.fn(),
  refreshAuth: vi.fn(),
};

vi.mock("../../contexts/AuthContext", () => ({
  useAuth: () => mockAuth,
}));

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/signup"]}>
      <SignUpPage />
    </MemoryRouter>,
  );
}

describe("SignUpPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAuth.user = null;
    mockAuth.isAuthenticated = false;
    mockAuth.error = null;
    mockRegister.mockResolvedValue(undefined);
  });

  it("renders the create account heading", () => {
    renderPage();
    expect(screen.getByRole("heading", { name: "Create Account" })).toBeInTheDocument();
  });

  it("renders all form fields", () => {
    renderPage();
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByLabelText("Display Name")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
    expect(screen.getByLabelText("Confirm Password")).toBeInTheDocument();
  });

  it("renders a link to sign in page", () => {
    renderPage();
    const link = screen.getByRole("link", { name: "Sign In" });
    expect(link).toHaveAttribute("href", "/signin");
  });

  it("calls register on valid submission", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText("Email"), "new@example.com");
    await user.type(screen.getByLabelText("Display Name"), "New User");
    await user.type(screen.getByLabelText("Password"), "password123");
    await user.type(screen.getByLabelText("Confirm Password"), "password123");
    await user.click(screen.getByRole("button", { name: "Create Account" }));

    await waitFor(() => {
      expect(mockRegister).toHaveBeenCalledWith("new@example.com", "password123", "New User");
    });
  });

  it("shows error when passwords do not match", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText("Email"), "new@example.com");
    await user.type(screen.getByLabelText("Password"), "password123");
    await user.type(screen.getByLabelText("Confirm Password"), "different456");
    await user.click(screen.getByRole("button", { name: "Create Account" }));

    expect(screen.getByRole("alert")).toHaveTextContent("Passwords do not match");
    expect(mockRegister).not.toHaveBeenCalled();
  });

  it("shows error when password is too short", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText("Email"), "new@example.com");
    await user.type(screen.getByLabelText("Password"), "short");
    await user.type(screen.getByLabelText("Confirm Password"), "short");
    await user.click(screen.getByRole("button", { name: "Create Account" }));

    expect(screen.getByRole("alert")).toHaveTextContent("at least 8 characters");
    expect(mockRegister).not.toHaveBeenCalled();
  });

  it("displays server error on registration failure", async () => {
    mockRegister.mockRejectedValue(new Error("An account with this email already exists"));
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText("Email"), "existing@example.com");
    await user.type(screen.getByLabelText("Password"), "password123");
    await user.type(screen.getByLabelText("Confirm Password"), "password123");
    await user.click(screen.getByRole("button", { name: "Create Account" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("already exists");
    });
  });

  it("shows loading state while submitting", async () => {
    let resolveRegister: () => void;
    mockRegister.mockReturnValue(
      new Promise<void>((resolve) => {
        resolveRegister = resolve;
      }),
    );
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText("Email"), "new@example.com");
    await user.type(screen.getByLabelText("Password"), "password123");
    await user.type(screen.getByLabelText("Confirm Password"), "password123");
    await user.click(screen.getByRole("button", { name: "Create Account" }));

    expect(screen.getByRole("button", { name: "Creating account..." })).toBeDisabled();

    resolveRegister!();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Create Account" })).not.toBeDisabled();
    });
  });
});
