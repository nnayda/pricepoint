import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import AuthModal from "../AuthModal";

const mockLogin = vi.fn();
const mockRegister = vi.fn();
const mockLogout = vi.fn();

vi.mock("../../../contexts/AuthContext", () => ({
  useAuth: () => ({
    user: null,
    isAuthenticated: false,
    isLoading: false,
    error: mockError,
    login: mockLogin,
    register: mockRegister,
    logout: mockLogout,
    refreshAuth: vi.fn(),
  }),
}));

let mockError: string | null = null;

describe("AuthModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockError = null;
  });

  it("renders nothing when closed", () => {
    const { container } = render(<AuthModal isOpen={false} onClose={vi.fn()} />);
    expect(container.innerHTML).toBe("");
  });

  it("shows sign in form when open", () => {
    render(<AuthModal isOpen={true} onClose={vi.fn()} />);
    expect(screen.getByRole("form", { name: "Sign in form" })).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
    const signInButtons = screen.getAllByRole("button", { name: "Sign In" });
    expect(signInButtons.length).toBeGreaterThanOrEqual(1);
  });

  it("shows register form on tab switch", async () => {
    const user = userEvent.setup();
    render(<AuthModal isOpen={true} onClose={vi.fn()} />);

    await user.click(screen.getByRole("button", { name: "Register" }));

    expect(screen.getByRole("form", { name: "Register form" })).toBeInTheDocument();
    expect(screen.getByLabelText("Display Name")).toBeInTheDocument();
    expect(screen.getByLabelText("Confirm Password")).toBeInTheDocument();
  });

  it("submit calls login with email and password", async () => {
    mockLogin.mockResolvedValue(undefined);
    const onClose = vi.fn();
    const user = userEvent.setup();

    render(<AuthModal isOpen={true} onClose={onClose} />);

    await user.type(screen.getByLabelText("Email"), "test@example.com");
    await user.type(screen.getByLabelText("Password"), "password123");
    const submitButtons = screen.getAllByRole("button", { name: "Sign In" });
    await user.click(submitButtons[submitButtons.length - 1]);

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith("test@example.com", "password123");
    });
    expect(onClose).toHaveBeenCalled();
  });

  it("displays error message from auth context", () => {
    mockError = "Invalid credentials";
    render(<AuthModal isOpen={true} onClose={vi.fn()} />);

    expect(screen.getByRole("alert")).toHaveTextContent("Invalid credentials");
  });

  it("shows password mismatch error on register", async () => {
    const user = userEvent.setup();
    render(<AuthModal isOpen={true} onClose={vi.fn()} />);

    await user.click(screen.getByRole("button", { name: "Register" }));

    await user.type(screen.getByLabelText("Email"), "test@example.com");
    await user.type(screen.getByLabelText("Display Name"), "Test User");
    await user.type(screen.getByLabelText("Password"), "password123");
    await user.type(screen.getByLabelText("Confirm Password"), "different");
    await user.click(screen.getByRole("button", { name: "Create Account" }));

    expect(screen.getByRole("alert")).toHaveTextContent("Passwords do not match");
    expect(mockRegister).not.toHaveBeenCalled();
  });

  it("submit calls register with correct args", async () => {
    mockRegister.mockResolvedValue(undefined);
    const onClose = vi.fn();
    const user = userEvent.setup();

    render(<AuthModal isOpen={true} onClose={onClose} />);

    await user.click(screen.getByRole("button", { name: "Register" }));

    await user.type(screen.getByLabelText("Email"), "new@example.com");
    await user.type(screen.getByLabelText("Display Name"), "New User");
    await user.type(screen.getByLabelText("Password"), "securepass");
    await user.type(screen.getByLabelText("Confirm Password"), "securepass");
    await user.click(screen.getByRole("button", { name: "Create Account" }));

    await waitFor(() => {
      expect(mockRegister).toHaveBeenCalledWith("new@example.com", "securepass", "New User");
    });
    expect(onClose).toHaveBeenCalled();
  });

  it("closes modal when clicking overlay", async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();
    render(<AuthModal isOpen={true} onClose={onClose} />);

    const overlay = screen.getByTestId("auth-modal-overlay");
    await user.click(overlay);

    expect(onClose).toHaveBeenCalled();
  });
});
