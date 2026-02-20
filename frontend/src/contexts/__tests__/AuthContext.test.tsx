import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AuthProvider, useAuth } from "../AuthContext";

const mockLoginUser = vi.fn();
const mockRegisterUser = vi.fn();
const mockGetCurrentUser = vi.fn();

vi.mock("../../services/auth", () => ({
  loginUser: (...args: unknown[]) => mockLoginUser(...args),
  registerUser: (...args: unknown[]) => mockRegisterUser(...args),
  getCurrentUser: (...args: unknown[]) => mockGetCurrentUser(...args),
}));

function TestConsumer() {
  const { user, isAuthenticated, isLoading, error, login, register, logout } = useAuth();
  return (
    <div>
      <span data-testid="loading">{String(isLoading)}</span>
      <span data-testid="authenticated">{String(isAuthenticated)}</span>
      <span data-testid="user">{user ? user.display_name : "none"}</span>
      <span data-testid="error">{error ?? "none"}</span>
      <button onClick={() => login("test@example.com", "password123").catch(() => {})}>
        Login
      </button>
      <button
        onClick={() => register("test@example.com", "password123", "Test User").catch(() => {})}
      >
        Register
      </button>
      <button onClick={logout}>Logout</button>
    </div>
  );
}

function renderWithProvider() {
  return render(
    <AuthProvider>
      <TestConsumer />
    </AuthProvider>,
  );
}

describe("AuthContext", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetCurrentUser.mockRejectedValue(new Error("No token"));
  });

  it("provides isAuthenticated=false initially", async () => {
    renderWithProvider();
    await waitFor(() => {
      expect(screen.getByTestId("loading").textContent).toBe("false");
    });
    expect(screen.getByTestId("authenticated").textContent).toBe("false");
    expect(screen.getByTestId("user").textContent).toBe("none");
  });

  it("login sets user and isAuthenticated", async () => {
    mockLoginUser.mockResolvedValue({
      access_token: "tok123",
      token_type: "bearer",
      user: { id: 1, email: "test@example.com", display_name: "Test User" },
    });

    const user = userEvent.setup();
    renderWithProvider();

    await waitFor(() => {
      expect(screen.getByTestId("loading").textContent).toBe("false");
    });

    await user.click(screen.getByText("Login"));

    await waitFor(() => {
      expect(screen.getByTestId("authenticated").textContent).toBe("true");
    });
    expect(screen.getByTestId("user").textContent).toBe("Test User");
    expect(mockLoginUser).toHaveBeenCalledWith("test@example.com", "password123");
  });

  it("logout clears user", async () => {
    mockLoginUser.mockResolvedValue({
      access_token: "tok123",
      token_type: "bearer",
      user: { id: 1, email: "test@example.com", display_name: "Test User" },
    });

    const user = userEvent.setup();
    renderWithProvider();

    await waitFor(() => {
      expect(screen.getByTestId("loading").textContent).toBe("false");
    });

    await user.click(screen.getByText("Login"));
    await waitFor(() => {
      expect(screen.getByTestId("authenticated").textContent).toBe("true");
    });

    await user.click(screen.getByText("Logout"));
    expect(screen.getByTestId("authenticated").textContent).toBe("false");
    expect(screen.getByTestId("user").textContent).toBe("none");
  });

  it("register sets user", async () => {
    mockRegisterUser.mockResolvedValue({
      access_token: "tok456",
      token_type: "bearer",
      user: { id: 2, email: "test@example.com", display_name: "Test User" },
    });

    const user = userEvent.setup();
    renderWithProvider();

    await waitFor(() => {
      expect(screen.getByTestId("loading").textContent).toBe("false");
    });

    await user.click(screen.getByText("Register"));

    await waitFor(() => {
      expect(screen.getByTestId("authenticated").textContent).toBe("true");
    });
    expect(screen.getByTestId("user").textContent).toBe("Test User");
    expect(mockRegisterUser).toHaveBeenCalledWith("test@example.com", "password123", "Test User");
  });

  it("sets error on failed login", async () => {
    mockLoginUser.mockRejectedValue(new Error("Invalid credentials"));

    const user = userEvent.setup();
    renderWithProvider();

    await waitFor(() => {
      expect(screen.getByTestId("loading").textContent).toBe("false");
    });

    await user.click(screen.getByText("Login"));

    await waitFor(() => {
      expect(screen.getByTestId("error").textContent).toBe("Invalid credentials");
    });
    expect(screen.getByTestId("authenticated").textContent).toBe("false");
  });

  it("sets error on failed register", async () => {
    mockRegisterUser.mockRejectedValue(new Error("Email already exists"));

    const user = userEvent.setup();
    renderWithProvider();

    await waitFor(() => {
      expect(screen.getByTestId("loading").textContent).toBe("false");
    });

    await user.click(screen.getByText("Register"));

    await waitFor(() => {
      expect(screen.getByTestId("error").textContent).toBe("Email already exists");
    });
  });

  it("refreshAuth restores session from token", async () => {
    mockGetCurrentUser.mockResolvedValue({
      id: 1,
      email: "test@example.com",
      display_name: "Restored User",
    });

    // We need to first login to set a token, then refreshAuth will work
    mockLoginUser.mockResolvedValue({
      access_token: "tok-session",
      token_type: "bearer",
      user: { id: 1, email: "test@example.com", display_name: "Test User" },
    });

    const user = userEvent.setup();

    function TestWithRefresh() {
      const auth = useAuth();
      return (
        <div>
          <span data-testid="user-name">{auth.user ? auth.user.display_name : "none"}</span>
          <button onClick={() => auth.login("test@example.com", "pass").catch(() => {})}>
            Login
          </button>
          <button onClick={() => auth.refreshAuth()}>Refresh</button>
        </div>
      );
    }

    render(
      <AuthProvider>
        <TestWithRefresh />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("user-name").textContent).toBe("none");
    });

    await user.click(screen.getByText("Login"));
    await waitFor(() => {
      expect(screen.getByTestId("user-name").textContent).toBe("Test User");
    });

    await user.click(screen.getByText("Refresh"));
    await waitFor(() => {
      expect(screen.getByTestId("user-name").textContent).toBe("Restored User");
    });
  });

  it("throws when useAuth is used outside AuthProvider", () => {
    // Suppress console.error for this test
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(() => render(<TestConsumer />)).toThrow("useAuth must be used within an AuthProvider");
    spy.mockRestore();
  });
});
